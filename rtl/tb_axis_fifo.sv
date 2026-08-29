`timescale 1ns/1ps

module tb_axis_fifo;
    localparam integer DEPTH = 16;
    localparam integer TRANSFERS = 1024;

    reg clk;
    reg reset_n;
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
    wire [7:0] output_user;
    wire [4:0] occupancy;

    integer sent;
    integer received;
    integer cycles;
    reg [31:0] lfsr;
    reg stalled_q;
    reg [127:0] stalled_data_q;
    reg [15:0] stalled_keep_q;
    reg stalled_last_q;
    reg [7:0] stalled_user_q;

    axis_fifo #(
        .DATA_WIDTH(128),
        .KEEP_WIDTH(16),
        .USER_WIDTH(8),
        .DEPTH(DEPTH)
    ) device_under_test (
        .clk_i(clk),
        .reset_n_i(reset_n),
        .clear_i(1'b0),
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
        .occupancy_o(occupancy)
    );

    function automatic [127:0] payload;
        input integer index;
        begin
            payload = {
                32'hd0000000 | index,
                32'hc0000000 | index,
                32'hb0000000 | index,
                32'ha0000000 | index
            };
        end
    endfunction

    always #5 clk = ~clk;

    always @(negedge clk) begin
        if (!reset_n) begin
            input_valid = 0;
            output_ready = 0;
        end else begin
            lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            output_ready = lfsr[0] | lfsr[5];
            if (!input_valid && (sent < TRANSFERS) && (lfsr[2] | lfsr[7])) begin
                input_data = payload(sent);
                input_keep = (sent == TRANSFERS - 1) ? 16'h00ff : 16'hffff;
                input_last = (sent == TRANSFERS - 1);
                input_user = sent[7:0] ^ 8'h5a;
                input_valid = 1;
            end
        end
    end

    always @(posedge clk) begin
        if (!reset_n) begin
            stalled_q = 0;
        end else begin
            cycles = cycles + 1;
            if (stalled_q) begin
                if (!output_valid
                        || output_data !== stalled_data_q
                        || output_keep !== stalled_keep_q
                        || output_last !== stalled_last_q
                        || output_user !== stalled_user_q) begin
                    $fatal(1, "AXI output changed while stalled");
                end
            end
            stalled_q = output_valid && !output_ready;
            stalled_data_q = output_data;
            stalled_keep_q = output_keep;
            stalled_last_q = output_last;
            stalled_user_q = output_user;

            if (input_valid && input_ready) begin
                sent = sent + 1;
                input_valid <= 0;
            end
            if (output_valid && output_ready) begin
                if (output_data !== payload(received)) begin
                    $fatal(1, "FIFO order/data mismatch at %0d", received);
                end
                if (output_keep !== ((received == TRANSFERS - 1)
                        ? 16'h00ff : 16'hffff)) begin
                    $fatal(1, "FIFO keep mismatch at %0d", received);
                end
                if (output_last !== (received == TRANSFERS - 1)) begin
                    $fatal(1, "FIFO last mismatch at %0d", received);
                end
                if (output_user !== (received[7:0] ^ 8'h5a)) begin
                    $fatal(1, "FIFO user mismatch at %0d", received);
                end
                received = received + 1;
            end
            if (occupancy > DEPTH) begin
                $fatal(1, "FIFO occupancy overflow");
            end
            if (cycles > 20000) begin
                $fatal(1, "FIFO timeout");
            end
        end
    end

    initial begin
        clk = 0;
        reset_n = 0;
        input_data = 0;
        input_keep = 0;
        input_valid = 0;
        input_last = 0;
        input_user = 0;
        output_ready = 0;
        sent = 0;
        received = 0;
        cycles = 0;
        lfsr = 32'h4e423201;
        stalled_q = 0;
        stalled_data_q = 0;
        stalled_keep_q = 0;
        stalled_last_q = 0;
        stalled_user_q = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;
        wait (received == TRANSFERS);
        @(negedge clk);
        if (occupancy != 0 || output_valid) begin
            $fatal(1, "FIFO did not drain");
        end
        $display("AXI FIFO randomized backpressure: PASS (%0d transfers)", TRANSFERS);
        $finish;
    end
endmodule
