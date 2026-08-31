`timescale 1ns/1ps

module tb_banked_stencil_engine;
    localparam integer LOGICAL_WIDTH = 17;
    localparam integer HEIGHT = 3;
    localparam integer PADDED_WIDTH = 24;
    localparam integer INPUT_BEATS = 18;
    localparam integer OUTPUT_BEATS = 15;
    localparam [95:0] COEFFICIENTS = {
        32'hb4004000,
        32'h3800bc00,
        32'h34003800
    };

    reg clk;
    reg reset_n;
    reg start;
    reg abort_request;
    reg soft_reset;
    reg mbist_start;
    reg [127:0] input_data;
    reg [15:0] input_keep;
    reg input_valid;
    wire input_ready;
    reg input_last;
    reg [7:0] input_user;
    wire [127:0] output_data;
    wire [15:0] output_keep;
    wire output_valid;
    reg output_ready;
    wire output_last;
    wire [23:0] output_user;
    wire busy;
    wire done_pulse;
    wire error_pulse;
    wire [7:0] error_code;
    wire [3:0] fp_flags_pulse;
    wire mbist_done;
    wire mbist_pass;
    wire [3:0] mbist_fail_bank;
    wire [9:0] mbist_fail_address;

    reg [127:0] input_memory [0:INPUT_BEATS - 1];
    reg [127:0] expected_memory [0:OUTPUT_BEATS - 1];
    reg [3:0] expected_flags_memory [0:OUTPUT_BEATS - 1];
    integer send_index;
    integer receive_index;
    integer cycle_count;
    integer done_count;
    integer error_count;
    integer input_load_check_count;
    reg drive_enabled;
    reg [31:0] lfsr;
    reg output_stalled_q;
    reg [127:0] stalled_data_q;
    reg [15:0] stalled_keep_q;
    reg stalled_last_q;
    reg [23:0] stalled_user_q;
    reg [3:0] expected_mask;
    reg [15:0] expected_keep;

    banked_stencil_engine device_under_test (
        .clk_i(clk),
        .reset_n_i(reset_n),
        .start_i(start),
        .abort_i(abort_request),
        .soft_reset_i(soft_reset),
        .mbist_start_i(mbist_start),
        .logical_width_i(LOGICAL_WIDTH),
        .height_i(HEIGHT),
        .padded_width_i(PADDED_WIDTH),
        .coefficients_i(COEFFICIENTS),
        .transaction_id_i(16'hbeef),
        .s_axis_tdata_i(input_data),
        .s_axis_tkeep_i(input_keep),
        .s_axis_tvalid_i(input_valid),
        .s_axis_tready_o(input_ready),
        .s_axis_tlast_i(input_last),
        .s_axis_tuser_i(input_user),
        .m_axis_tdata_o(output_data),
        .m_axis_tkeep_o(output_keep),
        .m_axis_tvalid_o(output_valid),
        .m_axis_tready_i(output_ready),
        .m_axis_tlast_o(output_last),
        .m_axis_tuser_o(output_user),
        .busy_o(busy),
        .done_pulse_o(done_pulse),
        .error_pulse_o(error_pulse),
        .error_code_o(error_code),
        .fp_flags_pulse_o(fp_flags_pulse),
        .mbist_done_o(mbist_done),
        .mbist_pass_o(mbist_pass),
        .mbist_fail_bank_o(mbist_fail_bank),
        .mbist_fail_address_o(mbist_fail_address)
    );

    always #5 clk = ~clk;

    always @(negedge clk) begin
        if (!reset_n) begin
            input_valid = 0;
            output_ready = 0;
        end else begin
            lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            output_ready = lfsr[0] | lfsr[4];
            if (drive_enabled && !input_valid && (send_index < INPUT_BEATS)
                    && (lfsr[2] | lfsr[6])) begin
                input_data = input_memory[send_index];
                input_keep = 16'hffff;
                input_last = (send_index == INPUT_BEATS - 1);
                input_user = ((send_index % (PADDED_WIDTH / 4)) == 0)
                    ? 8'h01 : 8'h00;
                input_valid = 1;
            end
        end
    end

    always @(posedge clk) begin
        if (!reset_n) begin
            done_count = 0;
            error_count = 0;
            output_stalled_q = 0;
        end else begin
            cycle_count = cycle_count + 1;
            if (done_pulse) done_count = done_count + 1;
            if (error_pulse) error_count = error_count + 1;

            if ((device_under_test.state_q == 3'd1)
                    && device_under_test.input_fifo_valid
                    && device_under_test.input_fifo_ready) begin
                input_load_check_count = input_load_check_count + 1;
            end

            if (output_stalled_q && (!output_valid
                    || output_data !== stalled_data_q
                    || output_keep !== stalled_keep_q
                    || output_last !== stalled_last_q
                    || output_user !== stalled_user_q)) begin
                $fatal(1, "integrated output changed while stalled");
            end
            output_stalled_q = output_valid && !output_ready;
            stalled_data_q = output_data;
            stalled_keep_q = output_keep;
            stalled_last_q = output_last;
            stalled_user_q = output_user;

            if (input_valid && input_ready) begin
                send_index = send_index + 1;
                input_valid <= 0;
            end
            if (output_valid && output_ready) begin
                expected_mask = ((receive_index % 5) == 4)
                    ? 4'b0001 : 4'b1111;
                expected_keep = (expected_mask == 4'b0001)
                    ? 16'h000f : 16'hffff;
                if (output_data !== expected_memory[receive_index]) begin
                    $fatal(
                        1,
                        "engine result mismatch beat=%0d expected=%h actual=%h",
                        receive_index,
                        expected_memory[receive_index],
                        output_data
                    );
                end
                if (output_keep !== expected_keep) begin
                    $fatal(1, "engine keep mismatch beat=%0d", receive_index);
                end
                if (output_user[23:8] !== 16'hbeef
                        || output_user[7:4] !== expected_flags_memory[receive_index]
                        || output_user[3:0] !== expected_mask) begin
                    $fatal(
                        1,
                        "engine user mismatch beat=%0d expected_flags=%h actual=%h",
                        receive_index,
                        expected_flags_memory[receive_index],
                        output_user
                    );
                end
                if (output_last !== (receive_index == OUTPUT_BEATS - 1)) begin
                    $fatal(1, "engine last mismatch beat=%0d", receive_index);
                end
                receive_index = receive_index + 1;
            end
            if (cycle_count > 20000) $fatal(1, "integrated engine timeout");
        end
    end

    task automatic pulse_start;
        begin
            @(negedge clk);
            start = 1;
            @(negedge clk);
            start = 0;
        end
    endtask

    initial begin
        $readmemh("build/engine_input.mem", input_memory);
        $readmemh("build/engine_expected.mem", expected_memory);
        $readmemh("build/engine_flags.mem", expected_flags_memory);
        clk = 0;
        reset_n = 0;
        start = 0;
        abort_request = 0;
        soft_reset = 0;
        mbist_start = 0;
        input_data = 0;
        input_keep = 0;
        input_valid = 0;
        input_last = 0;
        input_user = 0;
        output_ready = 0;
        send_index = 0;
        receive_index = 0;
        cycle_count = 0;
        done_count = 0;
        error_count = 0;
        input_load_check_count = 0;
        drive_enabled = 0;
        lfsr = 32'h4e423202;
        output_stalled_q = 0;
        stalled_data_q = 0;
        stalled_keep_q = 0;
        stalled_last_q = 0;
        stalled_user_q = 0;
        expected_mask = 0;
        expected_keep = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;
        pulse_start();
        drive_enabled = 1;
        wait (receive_index == OUTPUT_BEATS);
        wait (done_count == 1);
        @(negedge clk);
        drive_enabled = 0;
        if (busy || error_count != 0 || send_index != INPUT_BEATS
                || input_load_check_count != INPUT_BEATS) begin
            $fatal(1, "integrated engine did not complete cleanly");
        end
        $display(
            "input load assertions: PASS (%0d beats, FIFO ready/valid boundary)",
            input_load_check_count
        );

        pulse_start();
        @(negedge clk);
        input_data = input_memory[0];
        input_keep = 16'hffff;
        input_last = 1;
        input_user = 0;
        input_valid = 1;
        while (!input_ready) @(negedge clk);
        @(posedge clk);
        @(negedge clk);
        input_valid = 0;
        wait (error_count == 1);
        if (error_code != 2 || busy) begin
            $fatal(1, "unexpected TLAST was not rejected safely");
        end

        $display("end-to-end banked stencil engine: PASS");
        $finish;
    end
endmodule
