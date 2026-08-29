`timescale 1ns/1ps

// Four-lane, three-tap complex MAC.  One tap is completed per cycle and each
// tap preserves the specified two-FMA order for real and imaginary components.
module complex_stencil_mac (
    input  wire         clk_i,
    input  wire         reset_n_i,
    input  wire         clear_i,
    input  wire         in_valid_i,
    output wire         in_ready_o,
    input  wire [383:0] lane_samples_i,
    input  wire [95:0]  coefficients_i,
    input  wire [3:0]   lane_mask_i,
    input  wire [15:0]  transaction_id_i,
    input  wire         last_i,
    output reg          out_valid_o,
    input  wire         out_ready_i,
    output reg  [127:0] out_samples_o,
    output reg  [15:0]  out_lane_flags_o,
    output reg  [3:0]   out_lane_mask_o,
    output reg  [15:0]  out_transaction_id_o,
    output reg          out_last_o,
    output reg          busy_o
);
    reg [383:0] lane_samples_q;
    reg [95:0] coefficients_q;
    reg [3:0] lane_mask_q;
    reg [15:0] transaction_id_q;
    reg last_q;
    reg [1:0] tap_q;
    reg [127:0] real_accumulators_q;
    reg [127:0] imaginary_accumulators_q;
    reg [15:0] accumulated_flags_q;

    wire output_slot_available;
    wire finishing;
    wire accepting;
    wire [127:0] next_real_accumulators;
    wire [127:0] next_imaginary_accumulators;
    wire [15:0] current_fma_flags;
    wire [127:0] converted_samples;
    wire [15:0] conversion_flags;
    wire [15:0] completed_flags;

    assign output_slot_available = !out_valid_o || out_ready_i;
    assign finishing = busy_o && (tap_q == 2) && output_slot_available;
    assign in_ready_o = output_slot_available && (!busy_o || finishing);
    assign accepting = in_valid_i && in_ready_o;
    assign completed_flags = accumulated_flags_q
        | current_fma_flags
        | conversion_flags;

    genvar lane;
    generate
        for (lane = 0; lane < 4; lane = lane + 1) begin : mac_lane
            wire [31:0] selected_sample;
            wire [31:0] selected_coefficient;
            wire [31:0] real_first;
            wire [31:0] real_second;
            wire [31:0] imaginary_first;
            wire [31:0] imaginary_second;
            wire [3:0] real_first_flags;
            wire [3:0] real_second_flags;
            wire [3:0] imaginary_first_flags;
            wire [3:0] imaginary_second_flags;
            wire [15:0] converted_real;
            wire [15:0] converted_imaginary;
            wire [3:0] converted_real_flags;
            wire [3:0] converted_imaginary_flags;

            assign selected_sample = lane_samples_q[
                ((lane * 3 + tap_q) * 32) +: 32
            ];
            assign selected_coefficient = coefficients_q[(tap_q * 32) +: 32];

            fp16_fma_accumulator real_positive (
                .multiplicand_i(selected_sample[15:0]),
                .multiplier_i(selected_coefficient[15:0]),
                .accumulator_i(real_accumulators_q[(lane * 32) +: 32]),
                .result_o(real_first),
                .flags_o(real_first_flags)
            );

            fp16_fma_accumulator real_negative (
                .multiplicand_i({
                    ~selected_sample[31], selected_sample[30:16]
                }),
                .multiplier_i(selected_coefficient[31:16]),
                .accumulator_i(real_first),
                .result_o(real_second),
                .flags_o(real_second_flags)
            );

            fp16_fma_accumulator imaginary_positive_a (
                .multiplicand_i(selected_sample[15:0]),
                .multiplier_i(selected_coefficient[31:16]),
                .accumulator_i(imaginary_accumulators_q[(lane * 32) +: 32]),
                .result_o(imaginary_first),
                .flags_o(imaginary_first_flags)
            );

            fp16_fma_accumulator imaginary_positive_b (
                .multiplicand_i(selected_sample[31:16]),
                .multiplier_i(selected_coefficient[15:0]),
                .accumulator_i(imaginary_first),
                .result_o(imaginary_second),
                .flags_o(imaginary_second_flags)
            );

            fp32_to_fp16_rne convert_real (
                .value_i(real_second),
                .value_o(converted_real),
                .flags_o(converted_real_flags)
            );

            fp32_to_fp16_rne convert_imaginary (
                .value_i(imaginary_second),
                .value_o(converted_imaginary),
                .flags_o(converted_imaginary_flags)
            );

            assign next_real_accumulators[(lane * 32) +: 32] = real_second;
            assign next_imaginary_accumulators[(lane * 32) +: 32] = imaginary_second;
            assign current_fma_flags[(lane * 4) +: 4] =
                real_first_flags
                | real_second_flags
                | imaginary_first_flags
                | imaginary_second_flags;
            assign converted_samples[(lane * 32) +: 32] = {
                converted_imaginary, converted_real
            };
            assign conversion_flags[(lane * 4) +: 4] =
                converted_real_flags | converted_imaginary_flags;
        end
    endgenerate

    always @(posedge clk_i or negedge reset_n_i) begin
        if (!reset_n_i) begin
            lane_samples_q <= 0;
            coefficients_q <= 0;
            lane_mask_q <= 0;
            transaction_id_q <= 0;
            last_q <= 0;
            tap_q <= 0;
            real_accumulators_q <= 0;
            imaginary_accumulators_q <= 0;
            accumulated_flags_q <= 0;
            out_valid_o <= 0;
            out_samples_o <= 0;
            out_lane_flags_o <= 0;
            out_lane_mask_o <= 0;
            out_transaction_id_o <= 0;
            out_last_o <= 0;
            busy_o <= 0;
        end else if (clear_i) begin
            lane_samples_q <= 0;
            coefficients_q <= 0;
            lane_mask_q <= 0;
            transaction_id_q <= 0;
            last_q <= 0;
            tap_q <= 0;
            real_accumulators_q <= 0;
            imaginary_accumulators_q <= 0;
            accumulated_flags_q <= 0;
            out_valid_o <= 0;
            out_samples_o <= 0;
            out_lane_flags_o <= 0;
            out_lane_mask_o <= 0;
            out_transaction_id_o <= 0;
            out_last_o <= 0;
            busy_o <= 0;
        end else begin
            if (out_valid_o && out_ready_i) begin
                out_valid_o <= 1'b0;
            end

            if (busy_o) begin
                if (tap_q < 2) begin
                    real_accumulators_q <= next_real_accumulators;
                    imaginary_accumulators_q <= next_imaginary_accumulators;
                    accumulated_flags_q <= accumulated_flags_q | current_fma_flags;
                    tap_q <= tap_q + 1'b1;
                end else if (output_slot_available) begin
                    out_samples_o <= converted_samples;
                    out_lane_flags_o <= completed_flags;
                    out_lane_mask_o <= lane_mask_q;
                    out_transaction_id_o <= transaction_id_q;
                    out_last_o <= last_q;
                    out_valid_o <= 1'b1;
                    busy_o <= 1'b0;
                end
            end

            if (accepting) begin
                lane_samples_q <= lane_samples_i;
                coefficients_q <= coefficients_i;
                lane_mask_q <= lane_mask_i;
                transaction_id_q <= transaction_id_i;
                last_q <= last_i;
                tap_q <= 0;
                real_accumulators_q <= 0;
                imaginary_accumulators_q <= 0;
                accumulated_flags_q <= 0;
                busy_o <= 1'b1;
            end
        end
    end
endmodule
