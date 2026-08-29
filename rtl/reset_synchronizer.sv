`timescale 1ns/1ps

module reset_synchronizer (
    input  wire clk_i,
    input  wire async_reset_n_i,
    output wire sync_reset_n_o
);
    reg [1:0] synchronizer_q;

    always @(posedge clk_i or negedge async_reset_n_i) begin
        if (!async_reset_n_i) begin
            synchronizer_q <= 2'b00;
        end else begin
            synchronizer_q <= {synchronizer_q[0], 1'b1};
        end
    end

    assign sync_reset_n_o = synchronizer_q[1];
endmodule
