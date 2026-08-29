`timescale 1ns/1ps

// Cycle-accurate simulation model for the OpenRAM macro interface. Physical
// implementation uses the pinned LEF/GDS/Liberty views, not this model.
module sky130_sram_2kbyte_1rw1r_32x512_8 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire [3:0]  wmask0,
    input  wire [8:0]  addr0,
    input  wire [31:0] din0,
    output reg  [31:0] dout0,
    input  wire        clk1,
    input  wire        csb1,
    input  wire [8:0]  addr1,
    output reg  [31:0] dout1
);
    reg [31:0] memory [0:511];

    always @(posedge clk0) begin
        if (!csb0) begin
            if (!web0) begin
                if (wmask0[0]) memory[addr0][7:0] <= din0[7:0];
                if (wmask0[1]) memory[addr0][15:8] <= din0[15:8];
                if (wmask0[2]) memory[addr0][23:16] <= din0[23:16];
                if (wmask0[3]) memory[addr0][31:24] <= din0[31:24];
            end else begin
                dout0 <= memory[addr0];
            end
        end
    end

    always @(posedge clk1) begin
        if (!csb1) begin
            dout1 <= memory[addr1];
        end
    end
endmodule
