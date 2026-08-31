`timescale 1ns/1ps

module axis_fifo #(
    parameter integer DATA_WIDTH = 128,
    parameter integer KEEP_WIDTH = DATA_WIDTH / 8,
    parameter integer USER_WIDTH = 8,
    parameter integer DEPTH = 16,
    parameter integer POINTER_WIDTH = (DEPTH <= 2) ? 1 : $clog2(DEPTH)
) (
    input  wire                      clk_i,
    input  wire                      reset_n_i,
    input  wire                      clear_i,
    input  wire [DATA_WIDTH - 1:0]   s_axis_tdata_i,
    input  wire [KEEP_WIDTH - 1:0]   s_axis_tkeep_i,
    input  wire                      s_axis_tvalid_i,
    output wire                      s_axis_tready_o,
    input  wire                      s_axis_tlast_i,
    input  wire [USER_WIDTH - 1:0]   s_axis_tuser_i,
    output wire [DATA_WIDTH - 1:0]   m_axis_tdata_o,
    output wire [KEEP_WIDTH - 1:0]   m_axis_tkeep_o,
    output wire                      m_axis_tvalid_o,
    input  wire                      m_axis_tready_i,
    output wire                      m_axis_tlast_o,
    output wire [USER_WIDTH - 1:0]   m_axis_tuser_o,
    output wire [POINTER_WIDTH:0]    occupancy_o
);
    localparam integer ENTRY_WIDTH = DATA_WIDTH + KEEP_WIDTH + 1 + USER_WIDTH;

    reg [ENTRY_WIDTH - 1:0] memory [0:DEPTH - 1];
    reg [POINTER_WIDTH - 1:0] write_pointer_q;
    reg [POINTER_WIDTH - 1:0] read_pointer_q;
    reg [POINTER_WIDTH:0] count_q;
    wire push;
    wire pop;

    assign s_axis_tready_o = count_q < DEPTH;
    assign m_axis_tvalid_o = count_q != 0;
    assign push = s_axis_tvalid_i && s_axis_tready_o;
    assign pop = m_axis_tvalid_o && m_axis_tready_i;
    assign {
        m_axis_tuser_o,
        m_axis_tlast_o,
        m_axis_tkeep_o,
        m_axis_tdata_o
    } = memory[read_pointer_q];
    assign occupancy_o = count_q;

    always @(posedge clk_i or negedge reset_n_i) begin
        if (!reset_n_i) begin
            write_pointer_q <= 0;
            read_pointer_q <= 0;
            count_q <= 0;
        end else if (clear_i) begin
            write_pointer_q <= 0;
            read_pointer_q <= 0;
            count_q <= 0;
        end else begin
            if (push) begin
                memory[write_pointer_q] <= {
                    s_axis_tuser_i,
                    s_axis_tlast_i,
                    s_axis_tkeep_i,
                    s_axis_tdata_i
                };
                if (write_pointer_q == DEPTH - 1) begin
                    write_pointer_q <= 0;
                end else begin
                    write_pointer_q <= write_pointer_q + 1'b1;
                end
            end
            if (pop) begin
                if (read_pointer_q == DEPTH - 1) begin
                    read_pointer_q <= 0;
                end else begin
                    read_pointer_q <= read_pointer_q + 1'b1;
                end
            end
            case ({push, pop})
                2'b10: count_q <= count_q + 1'b1;
                2'b01: count_q <= count_q - 1'b1;
                default: count_q <= count_q;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (DEPTH < 1) begin
            $fatal(1, "axis_fifo DEPTH must be positive");
        end
    end

    // Simulation-time safety checks for the ready/valid FIFO contract.  These
    // checks do not claim an external DMA protocol or CDC proof; they guard the
    // local synchronous FIFO boundary used by the reference engine.
    always @(posedge clk_i) begin
        if (reset_n_i) begin
            assert (count_q <= DEPTH)
                else $fatal(1, "axis_fifo occupancy overflow: %0d", count_q);
            if (push) begin
                assert (count_q < DEPTH)
                    else $fatal(1, "axis_fifo push accepted while full");
            end
            if (pop) begin
                assert (count_q > 0)
                    else $fatal(1, "axis_fifo pop accepted while empty");
            end
        end
    end
`endif
endmodule
