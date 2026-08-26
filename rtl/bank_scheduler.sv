`timescale 1ns/1ps

// Executable steady-state scheduler for the 12-bank reference configuration.
module bank_scheduler (
    input  logic [1:0] cycle_mod3_i,
    input  logic [2:0] row_mod6_i,
    input  logic       read_buffer_i,
    output logic [23:0] read_banks_o,
    output logic [15:0] write_banks_o,
    output logic        conflict_o
);
    logic [5:0] unphased_sum;
    logic [3:0] unphased_base;
    logic [3:0] read_base;
    logic [3:0] write_base;
    integer read_index;
    integer write_index;

    function automatic logic [3:0] reduce_mod12(input logic [5:0] value);
        begin
            if (value >= 24) begin
                reduce_mod12 = value - 24;
            end else if (value >= 12) begin
                reduce_mod12 = value - 12;
            end else begin
                reduce_mod12 = value[3:0];
            end
        end
    endfunction

    function automatic logic [3:0] add_mod12(
        input logic [3:0] base,
        input logic [3:0] offset
    );
        logic [4:0] sum;
        begin
            sum = base + offset;
            add_mod12 = (sum >= 12) ? sum - 12 : sum[3:0];
        end
    endfunction

    always @* begin
        // Buffer A has phase 0 and buffer B has phase 6. The write buffer is
        // always the opposite of the read buffer.
        unphased_sum = {2'b00, cycle_mod3_i, 2'b00}
            + {2'b00, row_mod6_i, 1'b0};
        unphased_base = reduce_mod12(unphased_sum);
        read_base = read_buffer_i ? add_mod12(unphased_base, 4'd6) : unphased_base;
        write_base = read_buffer_i ? unphased_base : add_mod12(unphased_base, 4'd6);

        read_banks_o[3:0] = read_base;
        read_banks_o[7:4] = add_mod12(read_base, 4'd1);
        read_banks_o[11:8] = add_mod12(read_base, 4'd2);
        read_banks_o[15:12] = add_mod12(read_base, 4'd3);
        read_banks_o[19:16] = add_mod12(read_base, 4'd4);
        read_banks_o[23:20] = add_mod12(read_base, 4'd5);
        write_banks_o[3:0] = write_base;
        write_banks_o[7:4] = add_mod12(write_base, 4'd1);
        write_banks_o[11:8] = add_mod12(write_base, 4'd2);
        write_banks_o[15:12] = add_mod12(write_base, 4'd3);
        conflict_o = 1'b0;

        for (read_index = 0; read_index < 6; read_index = read_index + 1) begin
            for (write_index = 0; write_index < 4; write_index = write_index + 1) begin
                if (read_banks_o[read_index * 4 +: 4]
                        == write_banks_o[write_index * 4 +: 4]) begin
                    conflict_o = 1'b1;
                end
            end
        end
    end
endmodule
