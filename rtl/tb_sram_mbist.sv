`timescale 1ns/1ps

module tb_sram_mbist;
    localparam integer BANK_COUNT = 12;
    localparam integer ADDRESS_WIDTH = 10;
    localparam integer DEPTH = 1 << ADDRESS_WIDTH;

    reg clk;
    reg reset_n;
    reg start;
    wire memory_enable;
    wire memory_write;
    wire [3:0] memory_bank;
    wire [ADDRESS_WIDTH - 1:0] memory_address;
    wire [31:0] memory_write_data;
    wire [31:0] memory_read_data;
    wire busy;
    wire done;
    wire pass;
    wire [3:0] fail_bank;
    wire [ADDRESS_WIDTH - 1:0] fail_address;
    wire [(BANK_COUNT * 32) - 1:0] bank_read_data;
    reg inject_fault;
    integer done_count;
    integer cycles;

    genvar bank;
    generate
        for (bank = 0; bank < BANK_COUNT; bank = bank + 1) begin : banks
            single_port_sram #(
                .DATA_WIDTH(32),
                .ADDRESS_WIDTH(ADDRESS_WIDTH),
                .DEPTH(DEPTH)
            ) memory (
                .clk_i(clk),
                .enable_i(memory_enable && (memory_bank == bank)),
                .write_i(memory_write),
                .address_i(memory_address),
                .write_data_i(memory_write_data),
                .read_data_o(bank_read_data[(bank * 32) +: 32])
            );
        end
    endgenerate

    assign memory_read_data = bank_read_data[(memory_bank * 32) +: 32]
        ^ ((inject_fault && (memory_bank == 3) && (memory_address == 7))
            ? 32'h00000001 : 32'h00000000);

    sram_mbist #(
        .BANK_COUNT(BANK_COUNT),
        .ADDRESS_WIDTH(ADDRESS_WIDTH),
        .DATA_WIDTH(32),
        .DEPTH(DEPTH)
    ) device_under_test (
        .clk_i(clk),
        .reset_n_i(reset_n),
        .start_i(start),
        .memory_enable_o(memory_enable),
        .memory_write_o(memory_write),
        .memory_bank_o(memory_bank),
        .memory_address_o(memory_address),
        .memory_write_data_o(memory_write_data),
        .memory_read_data_i(memory_read_data),
        .busy_o(busy),
        .done_o(done),
        .pass_o(pass),
        .fail_bank_o(fail_bank),
        .fail_address_o(fail_address)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (reset_n) begin
            cycles = cycles + 1;
            if (done) done_count = done_count + 1;
            if (cycles > 400000) $fatal(1, "MBIST timeout");
        end
    end

    task automatic launch;
        begin
            @(negedge clk);
            start = 1;
            @(negedge clk);
            start = 0;
            wait (done);
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    initial begin
        clk = 0;
        reset_n = 0;
        start = 0;
        inject_fault = 0;
        done_count = 0;
        cycles = 0;
        repeat (3) @(posedge clk);
        @(negedge clk);
        reset_n = 1;

        launch();
        if (!pass) $fatal(1, "fault-free SRAM MBIST failed");
        if (done_count != 1) $fatal(1, "first MBIST completion missing");

        inject_fault = 1;
        launch();
        if (pass) $fatal(1, "injected SRAM fault was not detected");
        if (fail_bank != 3 || fail_address != 7) begin
            $fatal(
                1,
                "wrong MBIST failure location bank=%0d address=%0d",
                fail_bank,
                fail_address
            );
        end
        if (done_count != 2) $fatal(1, "second MBIST completion missing");

        $display("12-bank March C- SRAM MBIST: PASS");
        $finish;
    end
endmodule
