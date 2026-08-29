`timescale 1ns/1ps

module tb_banked_stencil_accelerator;
    localparam integer INPUT_BEATS = 18;
    localparam integer OUTPUT_BEATS = 15;
    localparam [1:0] AXI_OKAY = 2'b00;

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
    wire irq;

    reg [127:0] input_memory [0:INPUT_BEATS - 1];
    reg [127:0] expected_memory [0:OUTPUT_BEATS - 1];
    reg [3:0] expected_flags_memory [0:OUTPUT_BEATS - 1];
    integer send_index;
    integer receive_index;
    integer cycles;
    reg drive_enabled;
    reg [31:0] lfsr;
    reg [3:0] observed_flags;
    reg [3:0] expected_mask;
    reg [31:0] readback;
    reg stalled_q;
    reg [127:0] stalled_data_q;
    reg [15:0] stalled_keep_q;
    reg stalled_last_q;
    reg [23:0] stalled_user_q;

    banked_stencil_accelerator device_under_test (
        .core_clk_i(clk),
        .core_reset_n_i(reset_n),
        .s_axil_awaddr_i(awaddr),
        .s_axil_awvalid_i(awvalid),
        .s_axil_awready_o(awready),
        .s_axil_wdata_i(wdata),
        .s_axil_wstrb_i(wstrb),
        .s_axil_wvalid_i(wvalid),
        .s_axil_wready_o(wready),
        .s_axil_bresp_o(bresp),
        .s_axil_bvalid_o(bvalid),
        .s_axil_bready_i(bready),
        .s_axil_araddr_i(araddr),
        .s_axil_arvalid_i(arvalid),
        .s_axil_arready_o(arready),
        .s_axil_rdata_o(rdata),
        .s_axil_rresp_o(rresp),
        .s_axil_rvalid_o(rvalid),
        .s_axil_rready_i(rready),
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
        .irq_o(irq)
    );

    always #5 clk = ~clk;

    always @(negedge clk) begin
        if (!reset_n) begin
            input_valid = 0;
            output_ready = 0;
        end else begin
            lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            output_ready = lfsr[0] | lfsr[7];
            if (drive_enabled && !input_valid && (send_index < INPUT_BEATS)
                    && (lfsr[3] | lfsr[8])) begin
                input_data = input_memory[send_index];
                input_keep = 16'hffff;
                input_last = send_index == INPUT_BEATS - 1;
                input_user = ((send_index % 6) == 0) ? 8'h01 : 8'h00;
                input_valid = 1;
            end
        end
    end

    always @(posedge clk) begin
        if (reset_n) begin
            cycles = cycles + 1;
            if (stalled_q && (!output_valid
                    || output_data !== stalled_data_q
                    || output_keep !== stalled_keep_q
                    || output_last !== stalled_last_q
                    || output_user !== stalled_user_q)) begin
                $fatal(1, "top output changed while stalled");
            end
            stalled_q = output_valid && !output_ready;
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
                if (output_data !== expected_memory[receive_index]) begin
                    $fatal(1, "top data mismatch beat=%0d", receive_index);
                end
                if (output_keep !== ((expected_mask == 1)
                        ? 16'h000f : 16'hffff)) begin
                    $fatal(1, "top keep mismatch beat=%0d", receive_index);
                end
                if (output_user[23:8] !== 16'hbeef
                        || output_user[7:4] !== expected_flags_memory[receive_index]
                        || output_user[3:0] !== expected_mask) begin
                    $fatal(1, "top sideband mismatch beat=%0d", receive_index);
                end
                if (output_last !== (receive_index == OUTPUT_BEATS - 1)) begin
                    $fatal(1, "top last mismatch beat=%0d", receive_index);
                end
                observed_flags = observed_flags | output_user[7:4];
                receive_index = receive_index + 1;
            end
            if (cycles > 200000) $fatal(1, "top-level timeout");
        end
    end

    task automatic axi_write;
        input [7:0] address;
        input [31:0] data;
        begin
            @(negedge clk);
            awaddr = address;
            awvalid = 1;
            wdata = data;
            wstrb = 4'hf;
            wvalid = 1;
            while (!(awready && wready)) @(negedge clk);
            @(posedge clk);
            @(negedge clk);
            awvalid = 0;
            wvalid = 0;
            while (!bvalid) @(negedge clk);
            if (bresp !== AXI_OKAY) begin
                $fatal(1, "top CSR write failed address=%h response=%b", address, bresp);
            end
            bready = 1;
            @(posedge clk);
            @(negedge clk);
            bready = 0;
        end
    endtask

    task automatic axi_read;
        input [7:0] address;
        output [31:0] value;
        begin
            @(negedge clk);
            araddr = address;
            arvalid = 1;
            while (!arready) @(negedge clk);
            @(posedge clk);
            @(negedge clk);
            arvalid = 0;
            while (!rvalid) @(negedge clk);
            if (rresp !== AXI_OKAY) begin
                $fatal(1, "top CSR read failed address=%h response=%b", address, rresp);
            end
            value = rdata;
            rready = 1;
            @(posedge clk);
            @(negedge clk);
            rready = 0;
        end
    endtask

    initial begin
        $readmemh("build/engine_input.mem", input_memory);
        $readmemh("build/engine_expected.mem", expected_memory);
        $readmemh("build/engine_flags.mem", expected_flags_memory);
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
        input_data = 0;
        input_keep = 0;
        input_valid = 0;
        input_last = 0;
        input_user = 0;
        output_ready = 0;
        send_index = 0;
        receive_index = 0;
        cycles = 0;
        drive_enabled = 0;
        lfsr = 32'h4e423203;
        observed_flags = 0;
        expected_mask = 0;
        readback = 0;
        stalled_q = 0;
        stalled_data_q = 0;
        stalled_keep_q = 0;
        stalled_last_q = 0;
        stalled_user_q = 0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;
        repeat (4) @(posedge clk);

        axi_read(8'h00, readback);
        if (readback !== 32'h4e423201) $fatal(1, "top ID mismatch");
        axi_write(8'h10, 32'd17);
        axi_write(8'h14, 32'd3);
        axi_write(8'h18, 32'd24);
        axi_write(8'h1c, 32'd96);
        axi_write(8'h20, 32'h34003800);
        axi_write(8'h24, 32'h3800bc00);
        axi_write(8'h28, 32'hb4004000);
        axi_write(8'h3c, 32'h0000beef);
        axi_write(8'h2c, 32'h00000005);
        axi_write(8'h08, 32'h00000101);
        drive_enabled = 1;

        wait (receive_index == OUTPUT_BEATS);
        wait (irq);
        drive_enabled = 0;
        axi_read(8'h0c, readback);
        if (readback[3:0] !== 4'b0101) begin
            $fatal(1, "top completion status mismatch actual=%h", readback);
        end
        axi_read(8'h34, readback);
        if (readback[3:0] !== observed_flags) $fatal(1, "top FP sticky mismatch");

        axi_write(8'h30, 32'h0000000f);
        if (irq) $fatal(1, "IRQ W1C failed before MBIST");
        axi_write(8'h40, 32'h00000001);
        wait (irq);
        axi_read(8'h44, readback);
        if (readback[2:0] !== 3'b011) $fatal(1, "top MBIST status mismatch");

        $display("AXI-controlled full accelerator and MBIST: PASS");
        $finish;
    end
endmodule
