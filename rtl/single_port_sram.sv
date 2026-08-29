`timescale 1ns/1ps

module single_port_sram #(
    parameter integer DATA_WIDTH = 32,
    parameter integer ADDRESS_WIDTH = 10,
    parameter integer DEPTH = 1 << ADDRESS_WIDTH
) (
    input  wire                       clk_i,
    input  wire                       enable_i,
    input  wire                       write_i,
    input  wire [ADDRESS_WIDTH - 1:0] address_i,
    input  wire [DATA_WIDTH - 1:0]    write_data_i,
    output reg  [DATA_WIDTH - 1:0]    read_data_o
);
    reg [DATA_WIDTH - 1:0] memory [0:DEPTH - 1];

    always @(posedge clk_i) begin
        if (enable_i) begin
            if (write_i) begin
                memory[address_i] <= write_data_i;
            end else begin
                read_data_o <= memory[address_i];
            end
        end
    end
endmodule
