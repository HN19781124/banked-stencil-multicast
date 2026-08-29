`timescale 1ns/1ps

// Exact binary16 * binary16 + binary32 accumulator for the stencil MAC.
//
// The accumulator originates at zero and only receives binary16 products.
// Consequently every finite value is an integer multiple of 2^-48.  Keeping
// that complete fixed-point grid makes the operation genuinely fused while
// avoiding any dependency on host floating-point behavior.
module fp16_fma_accumulator (
    input  wire [15:0] multiplicand_i,
    input  wire [15:0] multiplier_i,
    input  wire [31:0] accumulator_i,
    output reg  [31:0] result_o,
    output reg  [3:0]  flags_o
);
    localparam integer EXACT_WIDTH = 88;

    reg sign_a;
    reg sign_b;
    reg sign_c;
    reg [4:0] exponent_a;
    reg [4:0] exponent_b;
    reg [7:0] exponent_c;
    reg [9:0] fraction_a;
    reg [9:0] fraction_b;
    reg [22:0] fraction_c;
    reg [10:0] significand_a;
    reg [10:0] significand_b;
    reg [23:0] significand_c;
    reg [21:0] product_significand;
    reg a_zero;
    reg b_zero;
    reg c_zero;
    reg a_infinity;
    reg b_infinity;
    reg c_infinity;
    reg a_nan;
    reg b_nan;
    reg c_nan;
    reg a_signaling_nan;
    reg b_signaling_nan;
    reg c_signaling_nan;
    reg product_sign;
    reg [EXACT_WIDTH - 1:0] product_magnitude;
    reg [EXACT_WIDTH - 1:0] accumulator_magnitude;
    reg signed [EXACT_WIDTH:0] signed_product;
    reg signed [EXACT_WIDTH:0] signed_accumulator;
    reg signed [EXACT_WIDTH:0] signed_sum;
    reg [EXACT_WIDTH:0] magnitude;
    reg result_sign;
    reg [23:0] retained;
    reg [24:0] rounded;
    reg guard_bit;
    reg sticky_bit;
    reg inexact;
    reg increment;
    reg [7:0] packed_exponent;
    integer scale_a;
    integer scale_b;
    integer scale_c;
    integer product_shift;
    integer accumulator_shift;
    integer leading_index;
    integer result_exponent;
    integer rounding_shift;
    integer scan_index;

    always @* begin
        sign_a = multiplicand_i[15];
        sign_b = multiplier_i[15];
        sign_c = accumulator_i[31];
        exponent_a = multiplicand_i[14:10];
        exponent_b = multiplier_i[14:10];
        exponent_c = accumulator_i[30:23];
        fraction_a = multiplicand_i[9:0];
        fraction_b = multiplier_i[9:0];
        fraction_c = accumulator_i[22:0];

        a_zero = (exponent_a == 0) && (fraction_a == 0);
        b_zero = (exponent_b == 0) && (fraction_b == 0);
        c_zero = (exponent_c == 0) && (fraction_c == 0);
        a_infinity = (exponent_a == 5'h1f) && (fraction_a == 0);
        b_infinity = (exponent_b == 5'h1f) && (fraction_b == 0);
        c_infinity = (exponent_c == 8'hff) && (fraction_c == 0);
        a_nan = (exponent_a == 5'h1f) && (fraction_a != 0);
        b_nan = (exponent_b == 5'h1f) && (fraction_b != 0);
        c_nan = (exponent_c == 8'hff) && (fraction_c != 0);
        a_signaling_nan = a_nan && !fraction_a[9];
        b_signaling_nan = b_nan && !fraction_b[9];
        c_signaling_nan = c_nan && !fraction_c[22];
        product_sign = sign_a ^ sign_b;

        significand_a = (exponent_a == 0)
            ? {1'b0, fraction_a}
            : {1'b1, fraction_a};
        significand_b = (exponent_b == 0)
            ? {1'b0, fraction_b}
            : {1'b1, fraction_b};
        significand_c = (exponent_c == 0)
            ? {1'b0, fraction_c}
            : {1'b1, fraction_c};
        scale_a = (exponent_a == 0) ? -24 : exponent_a - 25;
        scale_b = (exponent_b == 0) ? -24 : exponent_b - 25;
        scale_c = (exponent_c == 0) ? -149 : exponent_c - 150;

        result_o = 32'h00000000;
        flags_o = 4'b0000;
        product_significand = 0;
        product_magnitude = 0;
        accumulator_magnitude = 0;
        signed_product = 0;
        signed_accumulator = 0;
        signed_sum = 0;
        magnitude = 0;
        result_sign = 0;
        retained = 0;
        rounded = 0;
        guard_bit = 0;
        sticky_bit = 0;
        inexact = 0;
        increment = 0;
        packed_exponent = 0;
        product_shift = 0;
        accumulator_shift = 0;
        leading_index = -1;
        result_exponent = 0;
        rounding_shift = 0;
        scan_index = 0;

        if (a_nan || b_nan || c_nan) begin
            result_o = 32'h7fc00000;
            flags_o[3] = a_signaling_nan || b_signaling_nan || c_signaling_nan;
        end else if ((a_infinity || b_infinity) && (a_zero || b_zero)) begin
            result_o = 32'h7fc00000;
            flags_o[3] = 1'b1;
        end else if (a_infinity || b_infinity) begin
            if (c_infinity && (sign_c != product_sign)) begin
                result_o = 32'h7fc00000;
                flags_o[3] = 1'b1;
            end else begin
                result_o = {product_sign, 8'hff, 23'b0};
            end
        end else if (c_infinity) begin
            result_o = {sign_c, 8'hff, 23'b0};
        end else begin
            product_significand = significand_a * significand_b;
            product_shift = scale_a + scale_b + 48;
            product_magnitude = {{(EXACT_WIDTH - 22){1'b0}}, product_significand}
                << product_shift;

            accumulator_shift = scale_c + 48;
            if (accumulator_shift >= 0) begin
                accumulator_magnitude = {
                    {(EXACT_WIDTH - 24){1'b0}}, significand_c
                } << accumulator_shift;
            end else if (accumulator_shift > -24) begin
                accumulator_magnitude = significand_c >> -accumulator_shift;
            end else begin
                accumulator_magnitude = 0;
            end

            signed_product = product_sign
                ? -$signed({1'b0, product_magnitude})
                : $signed({1'b0, product_magnitude});
            signed_accumulator = sign_c
                ? -$signed({1'b0, accumulator_magnitude})
                : $signed({1'b0, accumulator_magnitude});
            signed_sum = signed_product + signed_accumulator;

            if (signed_sum < 0) begin
                result_sign = 1'b1;
                magnitude = -signed_sum;
            end else begin
                result_sign = 1'b0;
                magnitude = signed_sum;
            end

            if (magnitude == 0) begin
                if ((a_zero || b_zero) && c_zero
                        && (product_sign == sign_c)) begin
                    result_o = {product_sign, 31'b0};
                end else begin
                    result_o = 32'h00000000;
                end
            end else begin
                for (scan_index = 0; scan_index <= EXACT_WIDTH; scan_index = scan_index + 1) begin
                    if (magnitude[scan_index]) begin
                        leading_index = scan_index;
                    end
                end
                result_exponent = leading_index - 48;

                if (leading_index <= 23) begin
                    retained = magnitude[23:0] << (23 - leading_index);
                end else begin
                    rounding_shift = leading_index - 23;
                    retained = magnitude >> rounding_shift;
                    guard_bit = magnitude[rounding_shift - 1];
                    sticky_bit = 1'b0;
                    for (scan_index = 0; scan_index < EXACT_WIDTH; scan_index = scan_index + 1) begin
                        if (scan_index < (rounding_shift - 1)) begin
                            sticky_bit = sticky_bit | magnitude[scan_index];
                        end
                    end
                    inexact = guard_bit | sticky_bit;
                    increment = guard_bit && (sticky_bit || retained[0]);
                    rounded = {1'b0, retained} + increment;
                    if (rounded[24]) begin
                        retained = rounded[24:1];
                        result_exponent = result_exponent + 1;
                    end else begin
                        retained = rounded[23:0];
                    end
                end

                if (result_exponent > 127) begin
                    result_o = {result_sign, 8'hff, 23'b0};
                    flags_o[2] = 1'b1;
                    flags_o[0] = 1'b1;
                end else begin
                    packed_exponent = result_exponent + 127;
                    result_o = {
                        result_sign,
                        packed_exponent,
                        retained[22:0]
                    };
                    flags_o[0] = inexact;
                end
            end
        end
    end
endmodule
