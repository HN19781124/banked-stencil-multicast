`timescale 1ns/1ps

// Route six unique SRAM samples into four overlapping three-sample windows.
module stencil_multicast #(
    parameter integer DATA_WIDTH = 32
) (
    input  wire [(6 * DATA_WIDTH) - 1:0] unique_samples_i,
    output wire [(12 * DATA_WIDTH) - 1:0] lane_samples_o
);
    genvar lane_index;
    genvar tap_index;

    generate
        for (lane_index = 0; lane_index < 4; lane_index = lane_index + 1) begin : lanes
            for (tap_index = 0; tap_index < 3; tap_index = tap_index + 1) begin : taps
                assign lane_samples_o[
                    ((lane_index * 3 + tap_index) * DATA_WIDTH) +: DATA_WIDTH
                ] = unique_samples_i[
                    ((lane_index + tap_index) * DATA_WIDTH) +: DATA_WIDTH
                ];
            end
        end
    endgenerate
endmodule
