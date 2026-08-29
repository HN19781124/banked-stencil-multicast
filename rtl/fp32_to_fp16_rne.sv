`timescale 1ns/1ps

// IEEE-754 binary32 to binary16 conversion, roundTiesToEven.
module fp32_to_fp16_rne (
    input  wire [31:0] value_i,
    output reg  [15:0] value_o,
    output reg  [3:0]  flags_o
);
    reg sign;
    reg [7:0] exponent;
    reg [22:0] fraction;
    reg [23:0] significand;
    reg [10:0] retained;
    reg [11:0] rounded;
    reg guard_bit;
    reg sticky_bit;
    reg inexact;
    reg increment;
    integer unbiased_exponent;
    integer half_exponent;
    integer shift_amount;
    integer scan_index;

    always @* begin
        sign = value_i[31];
        exponent = value_i[30:23];
        fraction = value_i[22:0];
        significand = {1'b1, fraction};
        retained = 0;
        rounded = 0;
        guard_bit = 0;
        sticky_bit = 0;
        inexact = 0;
        increment = 0;
        unbiased_exponent = 0;
        half_exponent = 0;
        shift_amount = 0;
        scan_index = 0;
        value_o = {sign, 15'b0};
        flags_o = 4'b0000;

        if (exponent == 8'hff) begin
            if (fraction == 0) begin
                value_o = {sign, 5'h1f, 10'b0};
            end else begin
                value_o = 16'h7e00;
                flags_o[3] = !fraction[22];
            end
        end else if (exponent == 0) begin
            if (fraction != 0) begin
                flags_o[1] = 1'b1;
                flags_o[0] = 1'b1;
            end
        end else begin
            unbiased_exponent = exponent - 127;
            if (unbiased_exponent > 15) begin
                value_o = {sign, 5'h1f, 10'b0};
                flags_o[2] = 1'b1;
                flags_o[0] = 1'b1;
            end else if (unbiased_exponent >= -14) begin
                retained = significand >> 13;
                guard_bit = significand[12];
                sticky_bit = |significand[11:0];
                inexact = guard_bit | sticky_bit;
                increment = guard_bit && (sticky_bit || retained[0]);
                rounded = {1'b0, retained} + increment;
                half_exponent = unbiased_exponent + 15;
                if (rounded[11]) begin
                    retained = rounded[11:1];
                    half_exponent = half_exponent + 1;
                end else begin
                    retained = rounded[10:0];
                end
                if (half_exponent >= 31) begin
                    value_o = {sign, 5'h1f, 10'b0};
                    flags_o[2] = 1'b1;
                    flags_o[0] = 1'b1;
                end else begin
                    value_o = {sign, half_exponent[4:0], retained[9:0]};
                    flags_o[0] = inexact;
                end
            end else begin
                shift_amount = -unbiased_exponent - 1;
                if (shift_amount < 24) begin
                    retained = significand >> shift_amount;
                end else begin
                    retained = 0;
                end
                if ((shift_amount > 0) && (shift_amount <= 24)) begin
                    guard_bit = significand[shift_amount - 1];
                end
                sticky_bit = 1'b0;
                for (scan_index = 0; scan_index < 24; scan_index = scan_index + 1) begin
                    if (scan_index < (shift_amount - 1)) begin
                        sticky_bit = sticky_bit | significand[scan_index];
                    end
                end
                inexact = guard_bit | sticky_bit;
                increment = guard_bit && (sticky_bit || retained[0]);
                rounded = {1'b0, retained} + increment;
                if (rounded >= 12'd1024) begin
                    value_o = {sign, 5'b00001, 10'b0};
                end else begin
                    value_o = {sign, 5'b00000, rounded[9:0]};
                    flags_o[1] = inexact;
                end
                flags_o[0] = inexact;
            end
        end
    end
endmodule
