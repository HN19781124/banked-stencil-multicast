`timescale 1ns/1ps

// March C- equivalent test over independently selected single-port banks.
module sram_mbist #(
    parameter integer BANK_COUNT = 12,
    parameter integer ADDRESS_WIDTH = 10,
    parameter integer DATA_WIDTH = 32,
    parameter integer DEPTH = 1 << ADDRESS_WIDTH
) (
    input  wire                       clk_i,
    input  wire                       reset_n_i,
    input  wire                       start_i,
    output reg                        memory_enable_o,
    output reg                        memory_write_o,
    output reg  [3:0]                 memory_bank_o,
    output reg  [ADDRESS_WIDTH - 1:0] memory_address_o,
    output reg  [DATA_WIDTH - 1:0]    memory_write_data_o,
    input  wire [DATA_WIDTH - 1:0]    memory_read_data_i,
    output reg                        busy_o,
    output reg                        done_o,
    output reg                        pass_o,
    output reg  [3:0]                 fail_bank_o,
    output reg  [ADDRESS_WIDTH - 1:0] fail_address_o
);
    localparam [3:0] STATE_IDLE = 4'd0;
    localparam [3:0] STATE_UP_WRITE_ZERO = 4'd1;
    localparam [3:0] STATE_UP_READ_ZERO = 4'd2;
    localparam [3:0] STATE_UP_CHECK_ZERO_WRITE_ONE = 4'd3;
    localparam [3:0] STATE_UP_READ_ONE = 4'd4;
    localparam [3:0] STATE_UP_CHECK_ONE_WRITE_ZERO = 4'd5;
    localparam [3:0] STATE_DOWN_READ_ZERO = 4'd6;
    localparam [3:0] STATE_DOWN_CHECK_ZERO_WRITE_ONE = 4'd7;
    localparam [3:0] STATE_DOWN_READ_ONE = 4'd8;
    localparam [3:0] STATE_DOWN_CHECK_ONE_WRITE_ZERO = 4'd9;
    localparam [3:0] STATE_DOWN_READ_FINAL_ZERO = 4'd10;
    localparam [3:0] STATE_DOWN_CHECK_FINAL_ZERO = 4'd11;
    localparam [3:0] STATE_DONE = 4'd12;

    reg [3:0] state_q;
    reg failure_q;
    reg check_active;
    reg [DATA_WIDTH - 1:0] expected_read_data;
    wire mismatch;

    assign mismatch = check_active && (memory_read_data_i !== expected_read_data);

    always @* begin
        memory_enable_o = 0;
        memory_write_o = 0;
        memory_write_data_o = 0;
        check_active = 0;
        expected_read_data = 0;
        case (state_q)
            STATE_UP_WRITE_ZERO: begin
                memory_enable_o = 1;
                memory_write_o = 1;
                memory_write_data_o = {DATA_WIDTH{1'b0}};
            end
            STATE_UP_READ_ZERO,
            STATE_UP_READ_ONE,
            STATE_DOWN_READ_ZERO,
            STATE_DOWN_READ_ONE,
            STATE_DOWN_READ_FINAL_ZERO: begin
                memory_enable_o = 1;
                memory_write_o = 0;
            end
            STATE_UP_CHECK_ZERO_WRITE_ONE,
            STATE_DOWN_CHECK_ZERO_WRITE_ONE: begin
                check_active = 1;
                expected_read_data = {DATA_WIDTH{1'b0}};
                memory_enable_o = 1;
                memory_write_o = 1;
                memory_write_data_o = {DATA_WIDTH{1'b1}};
            end
            STATE_UP_CHECK_ONE_WRITE_ZERO,
            STATE_DOWN_CHECK_ONE_WRITE_ZERO: begin
                check_active = 1;
                expected_read_data = {DATA_WIDTH{1'b1}};
                memory_enable_o = 1;
                memory_write_o = 1;
                memory_write_data_o = {DATA_WIDTH{1'b0}};
            end
            STATE_DOWN_CHECK_FINAL_ZERO: begin
                check_active = 1;
                expected_read_data = {DATA_WIDTH{1'b0}};
            end
            default: begin
                memory_enable_o = 0;
            end
        endcase
    end

    always @(posedge clk_i or negedge reset_n_i) begin
        if (!reset_n_i) begin
            state_q <= STATE_IDLE;
            memory_bank_o <= 0;
            memory_address_o <= 0;
            busy_o <= 0;
            done_o <= 0;
            pass_o <= 0;
            failure_q <= 0;
            fail_bank_o <= 0;
            fail_address_o <= 0;
        end else begin
            done_o <= 0;
            if (mismatch && !failure_q) begin
                failure_q <= 1;
                fail_bank_o <= memory_bank_o;
                fail_address_o <= memory_address_o;
            end

            case (state_q)
                STATE_IDLE: begin
                    busy_o <= 0;
                    if (start_i) begin
                        state_q <= STATE_UP_WRITE_ZERO;
                        memory_bank_o <= 0;
                        memory_address_o <= 0;
                        busy_o <= 1;
                        pass_o <= 0;
                        failure_q <= 0;
                        fail_bank_o <= 0;
                        fail_address_o <= 0;
                    end
                end
                STATE_UP_WRITE_ZERO: begin
                    if (memory_address_o == DEPTH - 1) begin
                        memory_address_o <= 0;
                        state_q <= STATE_UP_READ_ZERO;
                    end else begin
                        memory_address_o <= memory_address_o + 1'b1;
                    end
                end
                STATE_UP_READ_ZERO:
                    state_q <= STATE_UP_CHECK_ZERO_WRITE_ONE;
                STATE_UP_CHECK_ZERO_WRITE_ONE: begin
                    if (memory_address_o == DEPTH - 1) begin
                        memory_address_o <= 0;
                        state_q <= STATE_UP_READ_ONE;
                    end else begin
                        memory_address_o <= memory_address_o + 1'b1;
                        state_q <= STATE_UP_READ_ZERO;
                    end
                end
                STATE_UP_READ_ONE:
                    state_q <= STATE_UP_CHECK_ONE_WRITE_ZERO;
                STATE_UP_CHECK_ONE_WRITE_ZERO: begin
                    if (memory_address_o == DEPTH - 1) begin
                        memory_address_o <= DEPTH - 1;
                        state_q <= STATE_DOWN_READ_ZERO;
                    end else begin
                        memory_address_o <= memory_address_o + 1'b1;
                        state_q <= STATE_UP_READ_ONE;
                    end
                end
                STATE_DOWN_READ_ZERO:
                    state_q <= STATE_DOWN_CHECK_ZERO_WRITE_ONE;
                STATE_DOWN_CHECK_ZERO_WRITE_ONE: begin
                    if (memory_address_o == 0) begin
                        memory_address_o <= DEPTH - 1;
                        state_q <= STATE_DOWN_READ_ONE;
                    end else begin
                        memory_address_o <= memory_address_o - 1'b1;
                        state_q <= STATE_DOWN_READ_ZERO;
                    end
                end
                STATE_DOWN_READ_ONE:
                    state_q <= STATE_DOWN_CHECK_ONE_WRITE_ZERO;
                STATE_DOWN_CHECK_ONE_WRITE_ZERO: begin
                    if (memory_address_o == 0) begin
                        memory_address_o <= DEPTH - 1;
                        state_q <= STATE_DOWN_READ_FINAL_ZERO;
                    end else begin
                        memory_address_o <= memory_address_o - 1'b1;
                        state_q <= STATE_DOWN_READ_ONE;
                    end
                end
                STATE_DOWN_READ_FINAL_ZERO:
                    state_q <= STATE_DOWN_CHECK_FINAL_ZERO;
                STATE_DOWN_CHECK_FINAL_ZERO: begin
                    if (memory_address_o == 0) begin
                        if (memory_bank_o == BANK_COUNT - 1) begin
                            state_q <= STATE_DONE;
                        end else begin
                            memory_bank_o <= memory_bank_o + 1'b1;
                            memory_address_o <= 0;
                            state_q <= STATE_UP_WRITE_ZERO;
                        end
                    end else begin
                        memory_address_o <= memory_address_o - 1'b1;
                        state_q <= STATE_DOWN_READ_FINAL_ZERO;
                    end
                end
                STATE_DONE: begin
                    busy_o <= 0;
                    done_o <= 1;
                    pass_o <= !(failure_q || mismatch);
                    state_q <= STATE_IDLE;
                end
                default: state_q <= STATE_IDLE;
            endcase
        end
    end
endmodule
