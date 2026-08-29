`timescale 1ns/1ps

module tb_axi_lite_csr;
    localparam [1:0] AXI_OKAY = 2'b00;
    localparam [1:0] AXI_SLVERR = 2'b10;
    localparam [1:0] AXI_DECERR = 2'b11;

    reg clk;
    reg reset_n;
    reg [7:0] awaddr;
    reg awvalid;
    wire awready;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    reg wvalid;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready;
    reg [7:0] araddr;
    reg arvalid;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready;
    reg busy;
    reg done_pulse;
    reg error_pulse;
    reg [7:0] error_code;
    reg [3:0] fp_flags;
    reg mbist_done;
    reg mbist_pass;
    reg [3:0] mbist_fail_bank;
    reg [9:0] mbist_fail_address;
    wire start_pulse;
    wire abort_pulse;
    wire soft_reset_pulse;
    wire mbist_start_pulse;
    wire [31:0] logical_width;
    wire [31:0] height;
    wire [31:0] padded_width;
    wire [31:0] row_stride_bytes;
    wire [95:0] coefficients;
    wire [15:0] transaction_id;
    wire irq;

    integer start_count;
    integer abort_count;
    integer soft_reset_count;
    integer mbist_start_count;
    reg b_stalled_q;
    reg [1:0] stalled_bresp_q;
    reg r_stalled_q;
    reg [31:0] stalled_rdata_q;
    reg [1:0] stalled_rresp_q;
    reg [31:0] readback;

    axi_lite_csr device_under_test (
        .clk_i(clk),
        .reset_n_i(reset_n),
        .s_axi_awaddr_i(awaddr),
        .s_axi_awvalid_i(awvalid),
        .s_axi_awready_o(awready),
        .s_axi_wdata_i(wdata),
        .s_axi_wstrb_i(wstrb),
        .s_axi_wvalid_i(wvalid),
        .s_axi_wready_o(wready),
        .s_axi_bresp_o(bresp),
        .s_axi_bvalid_o(bvalid),
        .s_axi_bready_i(bready),
        .s_axi_araddr_i(araddr),
        .s_axi_arvalid_i(arvalid),
        .s_axi_arready_o(arready),
        .s_axi_rdata_o(rdata),
        .s_axi_rresp_o(rresp),
        .s_axi_rvalid_o(rvalid),
        .s_axi_rready_i(rready),
        .busy_i(busy),
        .done_pulse_i(done_pulse),
        .error_pulse_i(error_pulse),
        .error_code_i(error_code),
        .fp_flags_i(fp_flags),
        .mbist_done_i(mbist_done),
        .mbist_pass_i(mbist_pass),
        .mbist_fail_bank_i(mbist_fail_bank),
        .mbist_fail_address_i(mbist_fail_address),
        .start_pulse_o(start_pulse),
        .abort_pulse_o(abort_pulse),
        .soft_reset_pulse_o(soft_reset_pulse),
        .mbist_start_pulse_o(mbist_start_pulse),
        .logical_width_o(logical_width),
        .height_o(height),
        .padded_width_o(padded_width),
        .row_stride_bytes_o(row_stride_bytes),
        .coefficients_o(coefficients),
        .transaction_id_o(transaction_id),
        .irq_o(irq)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!reset_n) begin
            start_count = 0;
            abort_count = 0;
            soft_reset_count = 0;
            mbist_start_count = 0;
            b_stalled_q = 0;
            r_stalled_q = 0;
        end else begin
            if (start_pulse) start_count = start_count + 1;
            if (abort_pulse) abort_count = abort_count + 1;
            if (soft_reset_pulse) soft_reset_count = soft_reset_count + 1;
            if (mbist_start_pulse) mbist_start_count = mbist_start_count + 1;

            if (b_stalled_q && (!bvalid || bresp !== stalled_bresp_q)) begin
                $fatal(1, "AXI-Lite B response changed while stalled");
            end
            b_stalled_q = bvalid && !bready;
            stalled_bresp_q = bresp;

            if (r_stalled_q && (!rvalid
                    || rdata !== stalled_rdata_q
                    || rresp !== stalled_rresp_q)) begin
                $fatal(1, "AXI-Lite R response changed while stalled");
            end
            r_stalled_q = rvalid && !rready;
            stalled_rdata_q = rdata;
            stalled_rresp_q = rresp;
        end
    end

    task automatic axi_write;
        input [7:0] address;
        input [31:0] data;
        input [3:0] strobes;
        input [1:0] expected_response;
        input integer channel_order;
        begin
            bready = 0;
            fork
                begin
                    if (channel_order == 2) repeat (2) @(negedge clk);
                    awaddr = address;
                    awvalid = 1;
                    @(posedge clk);
                    while (!awready) @(posedge clk);
                    @(negedge clk);
                    awvalid = 0;
                end
                begin
                    if (channel_order == 1) repeat (2) @(negedge clk);
                    wdata = data;
                    wstrb = strobes;
                    wvalid = 1;
                    @(posedge clk);
                    while (!wready) @(posedge clk);
                    @(negedge clk);
                    wvalid = 0;
                end
            join
            while (!bvalid) @(posedge clk);
            if (bresp !== expected_response) begin
                $fatal(
                    1,
                    "write response mismatch address=%h expected=%b actual=%b",
                    address,
                    expected_response,
                    bresp
                );
            end
            repeat (2) @(posedge clk);
            @(negedge clk);
            bready = 1;
            @(posedge clk);
            @(negedge clk);
            bready = 0;
        end
    endtask

    task automatic axi_read;
        input [7:0] address;
        input [1:0] expected_response;
        output [31:0] value;
        begin
            rready = 0;
            araddr = address;
            arvalid = 1;
            @(posedge clk);
            while (!arready) @(posedge clk);
            @(negedge clk);
            arvalid = 0;
            while (!rvalid) @(posedge clk);
            if (rresp !== expected_response) begin
                $fatal(
                    1,
                    "read response mismatch address=%h expected=%b actual=%b",
                    address,
                    expected_response,
                    rresp
                );
            end
            value = rdata;
            repeat (2) @(posedge clk);
            @(negedge clk);
            rready = 1;
            @(posedge clk);
            @(negedge clk);
            rready = 0;
        end
    endtask

    task automatic pulse_done;
        begin
            @(negedge clk);
            done_pulse = 1;
            @(negedge clk);
            done_pulse = 0;
        end
    endtask

    initial begin
        clk = 0;
        reset_n = 0;
        awaddr = 0;
        awvalid = 0;
        wdata = 0;
        wstrb = 0;
        wvalid = 0;
        bready = 0;
        araddr = 0;
        arvalid = 0;
        rready = 0;
        busy = 0;
        done_pulse = 0;
        error_pulse = 0;
        error_code = 0;
        fp_flags = 0;
        mbist_done = 0;
        mbist_pass = 0;
        mbist_fail_bank = 0;
        mbist_fail_address = 0;
        readback = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;

        axi_read(8'h00, AXI_OKAY, readback);
        if (readback !== 32'h4e423201) $fatal(1, "ID reset/read mismatch");
        axi_read(8'h0c, AXI_OKAY, readback);
        if (readback[1:0] !== 2'b01) $fatal(1, "STATUS reset mismatch");

        axi_write(8'h10, 32'd17, 4'hf, AXI_OKAY, 0);
        axi_write(8'h14, 32'd2, 4'hf, AXI_OKAY, 1);
        axi_write(8'h18, 32'd24, 4'hf, AXI_OKAY, 2);
        axi_write(8'h1c, 32'd96, 4'hf, AXI_OKAY, 0);
        axi_write(8'h20, 32'h3c000000, 4'hf, AXI_OKAY, 1);
        axi_write(8'h24, 32'h00003c00, 4'hf, AXI_OKAY, 2);
        axi_write(8'h28, 32'hbc003c00, 4'hf, AXI_OKAY, 0);
        axi_write(8'h3c, 32'h00001234, 4'hf, AXI_OKAY, 1);
        if (logical_width != 17 || height != 2 || padded_width != 24
                || row_stride_bytes != 96 || transaction_id != 16'h1234) begin
            $fatal(1, "configuration register write mismatch");
        end

        axi_write(8'h2c, 32'h0000000f, 4'hf, AXI_OKAY, 0);
        axi_write(8'h08, 32'h00000101, 4'hf, AXI_OKAY, 1);
        if (start_count != 1) $fatal(1, "START pulse missing");
        busy = 1;

        axi_write(8'h24, 32'hdeadbeef, 4'hf, AXI_SLVERR, 2);
        axi_read(8'h38, AXI_OKAY, readback);
        if (readback[7:0] != 8'd6) $fatal(1, "busy coefficient error missing");
        if (!irq) $fatal(1, "error IRQ missing");

        fp_flags = 4'b0101;
        @(negedge clk);
        fp_flags = 0;
        axi_read(8'h34, AXI_OKAY, readback);
        if (readback[3:0] != 4'b0101) $fatal(1, "FP sticky flags missing");
        axi_write(8'h34, 32'h00000001, 4'hf, AXI_OKAY, 0);
        axi_read(8'h34, AXI_OKAY, readback);
        if (readback[3:0] != 4'b0100) $fatal(1, "FP W1C failed");

        busy = 0;
        pulse_done();
        axi_read(8'h0c, AXI_OKAY, readback);
        if (!readback[2]) $fatal(1, "DONE sticky bit missing");

        axi_write(8'h40, 32'h00000001, 4'hf, AXI_OKAY, 1);
        if (mbist_start_count != 1) $fatal(1, "MBIST start pulse missing");
        mbist_pass = 1;
        mbist_done = 1;
        @(negedge clk);
        mbist_done = 0;
        axi_read(8'h44, AXI_OKAY, readback);
        if (readback[2:0] != 3'b011) $fatal(1, "MBIST status mismatch");

        axi_read(8'hf0, AXI_DECERR, readback);
        axi_write(8'hf0, 0, 4'hf, AXI_DECERR, 2);

        axi_write(8'h08, 32'h00000104, 4'hf, AXI_OKAY, 0);
        repeat (2) @(posedge clk);
        axi_write(8'h18, 32'd13, 4'hf, AXI_OKAY, 1);
        axi_write(8'h08, 32'h00000101, 4'hf, AXI_SLVERR, 2);
        if (start_count != 1) $fatal(1, "invalid START was accepted");
        axi_read(8'h38, AXI_OKAY, readback);
        if (readback[7:0] != 8'd1) $fatal(1, "configuration error missing");

        $display("AXI-Lite CSR protocol and register behavior: PASS");
        $finish;
    end
endmodule
