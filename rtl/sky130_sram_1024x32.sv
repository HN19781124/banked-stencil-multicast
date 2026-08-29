`timescale 1ns/1ps

// Open implementation of one 32-bit x 1024-word bank using two
// VLSIDA/OpenRAM 32-bit x 512-word macros. Port 1 is deliberately disabled so
// the externally visible storage remains single-port.
module sky130_sram_1024x32 (
    input  wire        clk_i,
    input  wire        enable_i,
    input  wire        write_i,
    input  wire [9:0]  address_i,
    input  wire [31:0] write_data_i,
    output wire [31:0] read_data_o
);
    wire lower_selected = enable_i && !address_i[9];
    wire upper_selected = enable_i && address_i[9];
    wire [31:0] lower_read_data;
    wire [31:0] upper_read_data;
    wire [31:0] unused_lower_port1;
    wire [31:0] unused_upper_port1;
    reg read_half_q;

    always @(posedge clk_i) begin
        if (enable_i && !write_i) begin
            read_half_q <= address_i[9];
        end
    end

    sky130_sram_2kbyte_1rw1r_32x512_8 lower_macro (
        .clk0(clk_i),
        .csb0(!lower_selected),
        .web0(!write_i),
        .wmask0(4'b1111),
        .addr0(address_i[8:0]),
        .din0(write_data_i),
        .dout0(lower_read_data),
        .clk1(clk_i),
        .csb1(1'b1),
        .addr1(9'b0),
        .dout1(unused_lower_port1)
    );

    sky130_sram_2kbyte_1rw1r_32x512_8 upper_macro (
        .clk0(clk_i),
        .csb0(!upper_selected),
        .web0(!write_i),
        .wmask0(4'b1111),
        .addr0(address_i[8:0]),
        .din0(write_data_i),
        .dout0(upper_read_data),
        .clk1(clk_i),
        .csb1(1'b1),
        .addr1(9'b0),
        .dout1(unused_upper_port1)
    );

    assign read_data_o = read_half_q ? upper_read_data : lower_read_data;
endmodule
