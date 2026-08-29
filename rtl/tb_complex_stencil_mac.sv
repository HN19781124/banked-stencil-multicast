`timescale 1ns/1ps

module tb_complex_stencil_mac;
    localparam integer VECTOR_COUNT = 256;

    reg clk;
    reg reset_n;
    reg in_valid;
    wire in_ready;
    reg [191:0] unique_samples;
    wire [383:0] lane_samples;
    reg [95:0] coefficients;
    reg [3:0] lane_mask;
    reg [15:0] transaction_id;
    reg last;
    wire out_valid;
    reg out_ready;
    wire [127:0] out_samples;
    wire [15:0] out_lane_flags;
    wire [3:0] out_lane_mask;
    wire [15:0] out_transaction_id;
    wire out_last;
    wire busy;

    reg [191:0] unique_memory [0:VECTOR_COUNT - 1];
    reg [95:0] coefficient_memory [0:VECTOR_COUNT - 1];
    reg [127:0] expected_memory [0:VECTOR_COUNT - 1];
    reg [15:0] flag_memory [0:VECTOR_COUNT - 1];
    integer send_index;
    integer receive_index;
    integer cycle_count;
    reg [15:0] lfsr;

    stencil_multicast #(.DATA_WIDTH(32)) multicast (
        .unique_samples_i(unique_samples),
        .lane_samples_o(lane_samples)
    );

    complex_stencil_mac device_under_test (
        .clk_i(clk),
        .reset_n_i(reset_n),
        .clear_i(1'b0),
        .in_valid_i(in_valid),
        .in_ready_o(in_ready),
        .lane_samples_i(lane_samples),
        .coefficients_i(coefficients),
        .lane_mask_i(lane_mask),
        .transaction_id_i(transaction_id),
        .last_i(last),
        .out_valid_o(out_valid),
        .out_ready_i(out_ready),
        .out_samples_o(out_samples),
        .out_lane_flags_o(out_lane_flags),
        .out_lane_mask_o(out_lane_mask),
        .out_transaction_id_o(out_transaction_id),
        .out_last_o(out_last),
        .busy_o(busy)
    );

    always #5 clk = ~clk;

    always @(negedge clk) begin
        if (!reset_n) begin
            in_valid = 0;
            out_ready = 0;
        end else begin
            lfsr = {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
            out_ready = lfsr[0] | lfsr[3];
            if (!in_valid && (send_index < VECTOR_COUNT)) begin
                unique_samples = unique_memory[send_index];
                coefficients = coefficient_memory[send_index];
                lane_mask = (send_index == VECTOR_COUNT - 1) ? 4'b0011 : 4'b1111;
                transaction_id = send_index[15:0];
                last = (send_index == VECTOR_COUNT - 1);
                in_valid = 1;
            end
        end
    end

    always @(posedge clk) begin
        if (reset_n) begin
            cycle_count = cycle_count + 1;
            if (in_valid && in_ready) begin
                send_index = send_index + 1;
                in_valid <= 0;
            end
            if (out_valid && out_ready) begin
                if (out_samples !== expected_memory[receive_index]) begin
                    $fatal(
                        1,
                        "MAC result mismatch vector=%0d expected=%h actual=%h",
                        receive_index,
                        expected_memory[receive_index],
                        out_samples
                    );
                end
                if (out_lane_flags !== flag_memory[receive_index]) begin
                    $fatal(
                        1,
                        "MAC flag mismatch vector=%0d expected=%h actual=%h",
                        receive_index,
                        flag_memory[receive_index],
                        out_lane_flags
                    );
                end
                if (out_transaction_id !== receive_index[15:0]) begin
                    $fatal(1, "transaction ID order mismatch");
                end
                if (out_lane_mask !== ((receive_index == VECTOR_COUNT - 1)
                        ? 4'b0011 : 4'b1111)) begin
                    $fatal(1, "lane mask mismatch");
                end
                if (out_last !== (receive_index == VECTOR_COUNT - 1)) begin
                    $fatal(1, "last mismatch");
                end
                receive_index = receive_index + 1;
            end
            if (cycle_count > 20000) begin
                $fatal(1, "complex MAC timeout");
            end
        end
    end

    initial begin
        $readmemh("build/mac_unique.mem", unique_memory);
        $readmemh("build/mac_coefficients.mem", coefficient_memory);
        $readmemh("build/mac_expected.mem", expected_memory);
        $readmemh("build/mac_flags.mem", flag_memory);
        clk = 0;
        reset_n = 0;
        in_valid = 0;
        out_ready = 0;
        unique_samples = 0;
        coefficients = 0;
        lane_mask = 0;
        transaction_id = 0;
        last = 0;
        send_index = 0;
        receive_index = 0;
        cycle_count = 0;
        lfsr = 16'h1ace;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;
        wait (receive_index == VECTOR_COUNT);
        @(negedge clk);
        if (out_valid || busy) begin
            $fatal(1, "MAC did not return to idle");
        end
        $display("bit-exact complex stencil MAC: PASS (%0d vectors)", VECTOR_COUNT);
        $finish;
    end
endmodule
