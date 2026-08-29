`timescale 1ns/1ps

// Deterministic throughput/latency probe for the reference 12-bank engine.
// The data path is checked against the same vectors as the end-to-end test;
// only the AXI-stream traffic pattern changes between the two modes.
module tb_banked_stencil_performance;
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
    integer start_cycle;
    integer first_output_cycle;
    integer last_output_cycle;
    integer done_cycle;
    integer input_accept_count;
    integer output_accept_count;
    integer input_stall_count;
    integer output_stall_count;
    integer error_count;
    integer max_input_occupancy;
    integer max_output_occupancy;
    integer control_stage_cycles;
    integer load_stage_cycles;
    integer read_stage_cycles;
    integer capture_stage_cycles;
    integer submit_stage_cycles;
    integer wait_output_stage_cycles;
    integer mac_busy_cycles;
    integer read_issue_count;
    integer capture_count;
    integer mac_accept_count;
    integer mac_output_count;
    reg start_seen;
    reg first_output_seen;
    reg done_seen;
    reg drive_enabled;
    reg perf_stress;
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
            input_valid = 1'b0;
            output_ready = 1'b0;
        end else begin
            if (perf_stress) begin
                lfsr = {
                    lfsr[30:0],
                    lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]
                };
                output_ready = lfsr[0] | lfsr[4];
            end else begin
                output_ready = 1'b1;
            end
            if (drive_enabled && !input_valid && (send_index < INPUT_BEATS)
                    && (!perf_stress || (lfsr[2] | lfsr[6]))) begin
                input_data = input_memory[send_index];
                input_keep = 16'hffff;
                input_last = (send_index == INPUT_BEATS - 1);
                input_user = ((send_index % (PADDED_WIDTH / 4)) == 0)
                    ? 8'h01 : 8'h00;
                input_valid = 1'b1;
            end
        end
    end

    always @(posedge clk) begin
        if (!reset_n) begin
            cycle_count = 0;
            start_cycle = -1;
            first_output_cycle = -1;
            last_output_cycle = -1;
            done_cycle = -1;
            input_accept_count = 0;
            output_accept_count = 0;
            input_stall_count = 0;
            output_stall_count = 0;
            error_count = 0;
            max_input_occupancy = 0;
            max_output_occupancy = 0;
            control_stage_cycles = 0;
            load_stage_cycles = 0;
            read_stage_cycles = 0;
            capture_stage_cycles = 0;
            submit_stage_cycles = 0;
            wait_output_stage_cycles = 0;
            mac_busy_cycles = 0;
            read_issue_count = 0;
            capture_count = 0;
            mac_accept_count = 0;
            mac_output_count = 0;
            start_seen = 1'b0;
            first_output_seen = 1'b0;
            done_seen = 1'b0;
            output_stalled_q = 1'b0;
        end else begin
            cycle_count = cycle_count + 1;
            if (device_under_test.transaction_busy_q
                    || (device_under_test.state_q != 3'd0)) begin
                case (device_under_test.state_q)
                    3'd1: load_stage_cycles = load_stage_cycles + 1;
                    3'd2: read_stage_cycles = read_stage_cycles + 1;
                    3'd3: capture_stage_cycles = capture_stage_cycles + 1;
                    3'd4: submit_stage_cycles = submit_stage_cycles + 1;
                    3'd5: wait_output_stage_cycles = wait_output_stage_cycles + 1;
                    default: begin end
                endcase
            end
            if (device_under_test.mac_busy) begin
                mac_busy_cycles = mac_busy_cycles + 1;
            end
            if ((device_under_test.state_q == 3'd2)
                    && !device_under_test.scheduler_conflict) begin
                read_issue_count = read_issue_count + 1;
            end
            if (device_under_test.state_q == 3'd3) begin
                capture_count = capture_count + 1;
            end
            if ((device_under_test.state_q == 3'd4)
                    && device_under_test.mac_input_ready) begin
                mac_accept_count = mac_accept_count + 1;
            end
            if (device_under_test.mac_output_valid
                    && device_under_test.mac_output_ready) begin
                mac_output_count = mac_output_count + 1;
            end
            if (device_under_test.input_fifo_occupancy > max_input_occupancy) begin
                max_input_occupancy = device_under_test.input_fifo_occupancy;
            end
            if (device_under_test.output_fifo_occupancy > max_output_occupancy) begin
                max_output_occupancy = device_under_test.output_fifo_occupancy;
            end
            if (start && !start_seen) begin
                start_seen = 1'b1;
                start_cycle = cycle_count;
                control_stage_cycles = control_stage_cycles + 1;
            end
            if (input_valid && input_ready) begin
                input_accept_count = input_accept_count + 1;
                send_index = send_index + 1;
                input_valid = 1'b0;
            end else if (input_valid && !input_ready) begin
                input_stall_count = input_stall_count + 1;
            end
            if (output_valid && !output_ready) begin
                output_stall_count = output_stall_count + 1;
            end
            if (error_pulse) begin
                error_count = error_count + 1;
            end

            if (output_stalled_q && (!output_valid
                    || output_data !== stalled_data_q
                    || output_keep !== stalled_keep_q
                    || output_last !== stalled_last_q
                    || output_user !== stalled_user_q)) begin
                $fatal(1, "performance output changed while stalled");
            end
            output_stalled_q = output_valid && !output_ready;
            stalled_data_q = output_data;
            stalled_keep_q = output_keep;
            stalled_last_q = output_last;
            stalled_user_q = output_user;

            if (output_valid && output_ready) begin
                if (!first_output_seen) begin
                    first_output_seen = 1'b1;
                    first_output_cycle = cycle_count;
                end
                last_output_cycle = cycle_count;
                output_accept_count = output_accept_count + 1;
                expected_mask = ((receive_index % 5) == 4)
                    ? 4'b0001 : 4'b1111;
                expected_keep = (expected_mask == 4'b0001)
                    ? 16'h000f : 16'hffff;
                if (receive_index >= OUTPUT_BEATS
                        || output_data !== expected_memory[receive_index]) begin
                    $fatal(1, "performance result mismatch beat=%0d", receive_index);
                end
                if (output_keep !== expected_keep
                        || output_last !== (receive_index == OUTPUT_BEATS - 1)) begin
                    $fatal(1, "performance sideband mismatch beat=%0d", receive_index);
                end
                if (output_user[23:8] !== 16'hbeef
                        || output_user[7:4] !== expected_flags_memory[receive_index]
                        || output_user[3:0] !== expected_mask) begin
                    $fatal(1, "performance user mismatch beat=%0d", receive_index);
                end
                receive_index = receive_index + 1;
            end
            if (done_pulse && !done_seen) begin
                done_seen = 1'b1;
                done_cycle = cycle_count;
            end
            if (cycle_count > 20000) begin
                $fatal(1, "performance engine timeout");
            end
        end
    end

    task automatic pulse_start;
        begin
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
        end
    endtask

    initial begin
        perf_stress = $test$plusargs("PERF_STRESS");
        $readmemh("build/engine_input.mem", input_memory);
        $readmemh("build/engine_expected.mem", expected_memory);
        $readmemh("build/engine_flags.mem", expected_flags_memory);
        clk = 1'b0;
        reset_n = 1'b0;
        start = 1'b0;
        abort_request = 1'b0;
        soft_reset = 1'b0;
        mbist_start = 1'b0;
        input_data = 0;
        input_keep = 0;
        input_valid = 1'b0;
        input_last = 1'b0;
        input_user = 0;
        output_ready = 1'b0;
        send_index = 0;
        receive_index = 0;
        cycle_count = 0;
        start_cycle = -1;
        first_output_cycle = -1;
        last_output_cycle = -1;
        done_cycle = -1;
        input_accept_count = 0;
        output_accept_count = 0;
        input_stall_count = 0;
        output_stall_count = 0;
        error_count = 0;
        max_input_occupancy = 0;
        max_output_occupancy = 0;
        start_seen = 1'b0;
        first_output_seen = 1'b0;
        done_seen = 1'b0;
        drive_enabled = 1'b0;
        lfsr = 32'h4e423202;
        output_stalled_q = 1'b0;
        stalled_data_q = 0;
        stalled_keep_q = 0;
        stalled_last_q = 1'b0;
        stalled_user_q = 0;
        expected_mask = 0;
        expected_keep = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1'b1;
        pulse_start();
        drive_enabled = 1'b1;
        wait (done_seen);
        @(negedge clk);
        drive_enabled = 1'b0;
        if (busy || error_count != 0 || input_accept_count != INPUT_BEATS
                || output_accept_count != OUTPUT_BEATS
                || receive_index != OUTPUT_BEATS) begin
            $fatal(1, "performance transaction did not complete cleanly");
        end
        if (perf_stress) begin
            $display(
                "PERF mode=stress width=%0d height=%0d padded=%0d input_beats=%0d output_beats=%0d cycles=%0d start=%0d first_output=%0d last_output=%0d done=%0d input_accepts=%0d output_accepts=%0d input_stalls=%0d output_stalls=%0d errors=%0d input_max_occupancy=%0d output_max_occupancy=%0d",
                LOGICAL_WIDTH, HEIGHT, PADDED_WIDTH, INPUT_BEATS, OUTPUT_BEATS,
                cycle_count, start_cycle, first_output_cycle, last_output_cycle,
                done_cycle, input_accept_count, output_accept_count,
                input_stall_count, output_stall_count, error_count,
                max_input_occupancy, max_output_occupancy
            );
            $display(
                "STAGE mode=stress control_cycles=%0d load_cycles=%0d read_cycles=%0d capture_cycles=%0d submit_cycles=%0d wait_output_cycles=%0d mac_busy_cycles=%0d read_issues=%0d captures=%0d mac_accepts=%0d mac_outputs=%0d",
                control_stage_cycles, load_stage_cycles, read_stage_cycles,
                capture_stage_cycles, submit_stage_cycles, wait_output_stage_cycles,
                mac_busy_cycles, read_issue_count, capture_count, mac_accept_count,
                mac_output_count
            );
        end else begin
            $display(
                "PERF mode=nostall width=%0d height=%0d padded=%0d input_beats=%0d output_beats=%0d cycles=%0d start=%0d first_output=%0d last_output=%0d done=%0d input_accepts=%0d output_accepts=%0d input_stalls=%0d output_stalls=%0d errors=%0d input_max_occupancy=%0d output_max_occupancy=%0d",
                LOGICAL_WIDTH, HEIGHT, PADDED_WIDTH, INPUT_BEATS, OUTPUT_BEATS,
                cycle_count, start_cycle, first_output_cycle, last_output_cycle,
                done_cycle, input_accept_count, output_accept_count,
                input_stall_count, output_stall_count, error_count,
                max_input_occupancy, max_output_occupancy
            );
            $display(
                "STAGE mode=nostall control_cycles=%0d load_cycles=%0d read_cycles=%0d capture_cycles=%0d submit_cycles=%0d wait_output_cycles=%0d mac_busy_cycles=%0d read_issues=%0d captures=%0d mac_accepts=%0d mac_outputs=%0d",
                control_stage_cycles, load_stage_cycles, read_stage_cycles,
                capture_stage_cycles, submit_stage_cycles, wait_output_stage_cycles,
                mac_busy_cycles, read_issue_count, capture_count, mac_accept_count,
                mac_output_count
            );
        end
        $finish;
    end
endmodule
