`timescale 1ns/1ps

// Behavioral integration test.  The completed bank_scheduler is instantiated
// unchanged; this test surrounds it with 12 synchronous single-port banks and
// the 6-to-4x3 multicast wiring.
module tb_banked_stencil_path;
    localparam integer BANK_COUNT = 12;
    localparam integer DATA_WIDTH = 32;
    localparam integer ADDRESS_WIDTH = 8;
    localparam integer BANK_DEPTH = 256;
    localparam integer PADDED_WIDTH = 48;
    localparam integer BUFFER_A_BASE = 0;
    localparam integer BUFFER_B_BASE = 64;

    reg clk;
    reg reset_n;
    reg read_enable;
    reg write_enable;
    reg [1:0] cycle_mod3;
    reg [2:0] row_mod6;
    reg read_buffer;
    wire [23:0] read_banks;
    wire [15:0] write_banks;
    wire conflict;

    reg [(6 * ADDRESS_WIDTH) - 1:0] read_addresses;
    reg [(4 * ADDRESS_WIDTH) - 1:0] write_addresses;
    reg [(4 * DATA_WIDTH) - 1:0] write_data;
    reg [(6 * DATA_WIDTH) - 1:0] unique_samples_q;
    reg read_valid_q;
    wire [(12 * DATA_WIDTH) - 1:0] lane_samples;

    reg [DATA_WIDTH - 1:0] bank_memory [0:BANK_COUNT - 1][0:BANK_DEPTH - 1];
    integer read_port;
    integer write_port;

    bank_scheduler scheduler (
        .cycle_mod3_i(cycle_mod3),
        .row_mod6_i(row_mod6),
        .read_buffer_i(read_buffer),
        .read_banks_o(read_banks),
        .write_banks_o(write_banks),
        .conflict_o(conflict)
    );

    stencil_multicast #(
        .DATA_WIDTH(DATA_WIDTH)
    ) multicast (
        .unique_samples_i(unique_samples_q),
        .lane_samples_o(lane_samples)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (!reset_n) begin
            unique_samples_q <= 0;
            read_valid_q <= 0;
        end else begin
            read_valid_q <= read_enable;
            if (read_enable) begin
                for (read_port = 0; read_port < 6; read_port = read_port + 1) begin
                    unique_samples_q[(read_port * DATA_WIDTH) +: DATA_WIDTH] <=
                        bank_memory[
                            read_banks[(read_port * 4) +: 4]
                        ][
                            read_addresses[(read_port * ADDRESS_WIDTH) +: ADDRESS_WIDTH]
                        ];
                end
            end
            if (write_enable) begin
                for (write_port = 0; write_port < 4; write_port = write_port + 1) begin
                    bank_memory[
                        write_banks[(write_port * 4) +: 4]
                    ][
                        write_addresses[(write_port * ADDRESS_WIDTH) +: ADDRESS_WIDTH]
                    ] <= write_data[(write_port * DATA_WIDTH) +: DATA_WIDTH];
                end
            end
        end
    end

    function automatic [ADDRESS_WIDTH - 1:0] sample_address;
        input integer buffer_value;
        input integer row_value;
        input integer x_value;
        integer buffer_base;
        begin
            buffer_base = buffer_value ? BUFFER_B_BASE : BUFFER_A_BASE;
            sample_address = buffer_base
                + row_value * (PADDED_WIDTH / BANK_COUNT)
                + x_value / BANK_COUNT;
        end
    endfunction

    function automatic [DATA_WIDTH - 1:0] sample_token;
        input integer buffer_value;
        input integer row_value;
        input integer x_value;
        begin
            sample_token = 32'hc0000000
                | ((buffer_value & 1) << 28)
                | ((row_value & 8'hff) << 16)
                | (x_value & 16'hffff);
        end
    endfunction

    task automatic set_read_addresses;
        input integer buffer_value;
        input integer row_value;
        input integer cycle_value;
        integer slot;
        begin
            for (slot = 0; slot < 6; slot = slot + 1) begin
                read_addresses[(slot * ADDRESS_WIDTH) +: ADDRESS_WIDTH] =
                    sample_address(buffer_value, row_value, 4 * cycle_value + slot);
            end
        end
    endtask

    task automatic set_write_payload;
        input integer buffer_value;
        input integer row_value;
        input integer cycle_value;
        integer slot;
        begin
            for (slot = 0; slot < 4; slot = slot + 1) begin
                write_addresses[(slot * ADDRESS_WIDTH) +: ADDRESS_WIDTH] =
                    sample_address(buffer_value, row_value, 4 * cycle_value + slot);
                write_data[(slot * DATA_WIDTH) +: DATA_WIDTH] =
                    sample_token(buffer_value, row_value, 4 * cycle_value + slot);
            end
        end
    endtask

    task automatic check_lane_windows;
        input integer buffer_value;
        input integer row_value;
        input integer cycle_value;
        integer lane;
        integer tap;
        reg [DATA_WIDTH - 1:0] expected;
        reg [DATA_WIDTH - 1:0] actual;
        begin
            if (!read_valid_q) begin
                $fatal(1, "missing synchronous SRAM response");
            end
            for (lane = 0; lane < 4; lane = lane + 1) begin
                for (tap = 0; tap < 3; tap = tap + 1) begin
                    expected = sample_token(
                        buffer_value,
                        row_value,
                        4 * cycle_value + lane + tap
                    );
                    actual = lane_samples[
                        ((lane * 3 + tap) * DATA_WIDTH) +: DATA_WIDTH
                    ];
                    if (actual !== expected) begin
                        $fatal(
                            1,
                            "multicast mismatch buffer=%0d row=%0d cycle=%0d lane=%0d tap=%0d expected=%h actual=%h",
                            buffer_value,
                            row_value,
                            cycle_value,
                            lane,
                            tap,
                            expected,
                            actual
                        );
                    end
                end
            end
        end
    endtask

    task automatic fill_buffer;
        input integer target_buffer;
        input integer row_value;
        input integer cycle_count;
        integer cycle_value;
        begin
            for (cycle_value = 0; cycle_value < cycle_count; cycle_value = cycle_value + 1) begin
                @(negedge clk);
                read_enable = 0;
                write_enable = 1;
                read_buffer = (target_buffer == 0);
                row_mod6 = row_value % 6;
                cycle_mod3 = cycle_value % 3;
                set_write_payload(target_buffer, row_value, cycle_value);
                @(posedge clk);
                #1;
                if (conflict !== 1'b0) begin
                    $fatal(1, "conflict while filling buffer");
                end
            end
            @(negedge clk);
            write_enable = 0;
        end
    endtask

    task automatic stream_between_buffers;
        input integer source_buffer;
        input integer target_buffer;
        input integer row_value;
        input integer cycle_count;
        integer cycle_value;
        begin
            for (cycle_value = 0; cycle_value < cycle_count; cycle_value = cycle_value + 1) begin
                @(negedge clk);
                read_enable = 1;
                write_enable = 1;
                read_buffer = (source_buffer != 0);
                row_mod6 = row_value % 6;
                cycle_mod3 = cycle_value % 3;
                set_read_addresses(source_buffer, row_value, cycle_value);
                set_write_payload(target_buffer, row_value, cycle_value);
                @(posedge clk);
                #1;
                if (conflict !== 1'b0) begin
                    $fatal(1, "read/write bank conflict in integrated path");
                end
                check_lane_windows(source_buffer, row_value, cycle_value);
            end
            @(negedge clk);
            read_enable = 0;
            write_enable = 0;
        end
    endtask

    task automatic stream_read_only;
        input integer source_buffer;
        input integer row_value;
        input integer cycle_count;
        integer cycle_value;
        begin
            for (cycle_value = 0; cycle_value < cycle_count; cycle_value = cycle_value + 1) begin
                @(negedge clk);
                read_enable = 1;
                write_enable = 0;
                read_buffer = (source_buffer != 0);
                row_mod6 = row_value % 6;
                cycle_mod3 = cycle_value % 3;
                set_read_addresses(source_buffer, row_value, cycle_value);
                @(posedge clk);
                #1;
                check_lane_windows(source_buffer, row_value, cycle_value);
            end
            @(negedge clk);
            read_enable = 0;
        end
    endtask

    task automatic exercise_row;
        input integer row_value;
        begin
            // Eight four-output issues consume samples through x=33, so the
            // prefetch side must also write the following two Halo samples.
            fill_buffer(1, row_value, 9);
            stream_between_buffers(1, 0, row_value, 8);
            stream_between_buffers(0, 1, row_value, 7);
            stream_read_only(1, row_value, 6);
        end
    endtask

    initial begin
        clk = 0;
        reset_n = 0;
        read_enable = 0;
        write_enable = 0;
        cycle_mod3 = 0;
        row_mod6 = 0;
        read_buffer = 0;
        read_addresses = 0;
        write_addresses = 0;
        write_data = 0;

        repeat (2) @(posedge clk);
        @(negedge clk);
        reset_n = 1;

        exercise_row(0);
        exercise_row(5);

        $display("banked SRAM + multicast path: PASS");
        $finish;
    end
endmodule
