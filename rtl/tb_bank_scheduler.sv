`timescale 1ns/1ps

module tb_bank_scheduler;
    logic [1:0] cycle_mod3;
    logic [2:0] row_mod6;
    logic       read_buffer;
    logic [23:0] read_banks;
    logic [15:0] write_banks;
    logic        conflict;

    integer buffer_value;
    integer row_value;
    integer cycle_value;
    integer left_index;
    integer right_index;

    bank_scheduler dut (
        .cycle_mod3_i(cycle_mod3),
        .row_mod6_i(row_mod6),
        .read_buffer_i(read_buffer),
        .read_banks_o(read_banks),
        .write_banks_o(write_banks),
        .conflict_o(conflict)
    );

    initial begin
        for (buffer_value = 0; buffer_value < 2; buffer_value = buffer_value + 1) begin
            for (row_value = 0; row_value < 6; row_value = row_value + 1) begin
                for (cycle_value = 0; cycle_value < 3; cycle_value = cycle_value + 1) begin
                    read_buffer = buffer_value[0];
                    row_mod6 = row_value[2:0];
                    cycle_mod3 = cycle_value[1:0];
                    #1;

                    if (conflict !== 1'b0) begin
                        $fatal(1, "read/write conflict: buffer=%0d row=%0d cycle=%0d",
                            buffer_value, row_value, cycle_value);
                    end

                    for (left_index = 0; left_index < 6; left_index = left_index + 1) begin
                        for (right_index = left_index + 1; right_index < 6;
                                right_index = right_index + 1) begin
                            if (read_banks[left_index * 4 +: 4]
                                    == read_banks[right_index * 4 +: 4]) begin
                                $fatal(1, "duplicate read bank");
                            end
                        end
                    end

                    for (left_index = 0; left_index < 4; left_index = left_index + 1) begin
                        for (right_index = left_index + 1; right_index < 4;
                                right_index = right_index + 1) begin
                            if (write_banks[left_index * 4 +: 4]
                                    == write_banks[right_index * 4 +: 4]) begin
                                $fatal(1, "duplicate write bank");
                            end
                        end
                    end
                end
            end
        end

        $display("bank_scheduler RTL: PASS (36 periodic states)");
        $finish;
    end
endmodule
