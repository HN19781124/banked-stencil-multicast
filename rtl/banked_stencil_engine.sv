`timescale 1ns/1ps

module banked_stencil_engine #(
    parameter integer BANK_COUNT = 12,
    parameter integer SRAM_ADDRESS_WIDTH = 10,
    parameter integer SRAM_DEPTH = 1 << SRAM_ADDRESS_WIDTH,
    parameter integer FIFO_DEPTH = 16
) (
    input  wire         clk_i,
    input  wire         reset_n_i,
    input  wire         start_i,
    input  wire         abort_i,
    input  wire         soft_reset_i,
    input  wire         mbist_start_i,
    input  wire [31:0]  logical_width_i,
    input  wire [31:0]  height_i,
    input  wire [31:0]  padded_width_i,
    input  wire [95:0]  coefficients_i,
    input  wire [15:0]  transaction_id_i,
    input  wire [127:0] s_axis_tdata_i,
    input  wire [15:0]  s_axis_tkeep_i,
    input  wire         s_axis_tvalid_i,
    output wire         s_axis_tready_o,
    input  wire         s_axis_tlast_i,
    input  wire [7:0]   s_axis_tuser_i,
    output wire [127:0] m_axis_tdata_o,
    output wire [15:0]  m_axis_tkeep_o,
    output wire         m_axis_tvalid_o,
    input  wire         m_axis_tready_i,
    output wire         m_axis_tlast_o,
    output wire [23:0]  m_axis_tuser_o,
    output wire         busy_o,
    output reg          done_pulse_o,
    output reg          error_pulse_o,
    output reg  [7:0]   error_code_o,
    output reg  [3:0]   fp_flags_pulse_o,
    output wire         mbist_done_o,
    output wire         mbist_pass_o,
    output wire [3:0]   mbist_fail_bank_o,
    output wire [9:0]   mbist_fail_address_o
);
    localparam [2:0] STATE_IDLE = 3'd0;
    localparam [2:0] STATE_LOAD = 3'd1;
    localparam [2:0] STATE_READ = 3'd2;
    localparam [2:0] STATE_CAPTURE = 3'd3;
    localparam [2:0] STATE_SUBMIT = 3'd4;
    localparam [2:0] STATE_WAIT_OUTPUT = 3'd5;

    reg [2:0] state_q;
    reg transaction_busy_q;
    reg clear_on_error_q;
    reg [31:0] logical_width_q;
    reg [31:0] height_q;
    reg [31:0] padded_width_q;
    reg [95:0] coefficients_q;
    reg [15:0] transaction_id_q;
    reg [31:0] load_row_q;
    reg [31:0] load_x_q;
    reg [31:0] compute_row_q;
    reg [31:0] issue_q;
    reg [23:0] read_banks_q;
    reg [191:0] unique_samples_q;
    reg [3:0] lane_mask_q;
    reg issue_last_q;

    wire datapath_clear;
    wire configuration_valid;
    wire input_allowed;
    wire [127:0] input_fifo_data;
    wire [15:0] input_fifo_keep;
    wire input_fifo_valid;
    wire input_fifo_ready;
    wire input_fifo_last;
    wire [7:0] input_fifo_user;
    wire [4:0] input_fifo_occupancy;
    wire input_fifo_source_ready;
    wire expected_input_last;

    wire [23:0] scheduler_read_banks;
    wire [15:0] scheduler_write_banks;
    wire scheduler_conflict;
    wire [1:0] scheduler_cycle_mod3;
    wire [2:0] scheduler_row_mod6;

    reg [BANK_COUNT - 1:0] memory_enable;
    reg [BANK_COUNT - 1:0] memory_write;
    reg [(BANK_COUNT * SRAM_ADDRESS_WIDTH) - 1:0] memory_address;
    reg [(BANK_COUNT * 32) - 1:0] memory_write_data;
    wire [(BANK_COUNT * 32) - 1:0] memory_read_data;

    wire mbist_busy;
    wire mbist_memory_enable;
    wire mbist_memory_write;
    wire [3:0] mbist_memory_bank;
    wire [SRAM_ADDRESS_WIDTH - 1:0] mbist_memory_address;
    wire [31:0] mbist_memory_write_data;
    wire [31:0] mbist_memory_read_data;

    wire [383:0] lane_samples;
    wire mac_input_ready;
    wire mac_output_valid;
    wire mac_output_ready;
    wire [127:0] mac_output_samples;
    wire [15:0] mac_output_lane_flags;
    wire [3:0] mac_output_lane_mask;
    wire [15:0] mac_output_transaction_id;
    wire mac_output_last;
    wire mac_busy;
    wire [3:0] mac_flag_union;
    wire [15:0] mac_output_keep;
    wire [23:0] mac_output_user;
    wire [4:0] output_fifo_occupancy;

    integer memory_slot;
    integer capture_slot;
    integer selected_bank;
    integer selected_address;
    integer remaining_lanes;

    assign datapath_clear = soft_reset_i || abort_i || clear_on_error_q;
    assign configuration_valid =
        (logical_width_i >= 1)
        && (height_i >= 1)
        && (padded_width_i >= 12)
        && ((padded_width_i % 12) == 0)
        && ((height_i * (padded_width_i / 12)) <= 512)
        && (padded_width_i >= ((((logical_width_i + 3) / 4) * 4) + 2));
    assign busy_o = transaction_busy_q || mbist_busy;
    assign input_allowed = transaction_busy_q && (state_q == STATE_LOAD);
    assign s_axis_tready_o = input_allowed && input_fifo_source_ready;
    assign input_fifo_ready = state_q == STATE_LOAD;
    assign expected_input_last =
        (load_row_q == (height_q - 1))
        && ((load_x_q + 4) >= padded_width_q);
    assign scheduler_cycle_mod3 = issue_q % 3;
    assign scheduler_row_mod6 = compute_row_q % 6;

    axis_fifo #(
        .DATA_WIDTH(128),
        .KEEP_WIDTH(16),
        .USER_WIDTH(8),
        .DEPTH(FIFO_DEPTH)
    ) input_fifo (
        .clk_i(clk_i),
        .reset_n_i(reset_n_i),
        .clear_i(datapath_clear),
        .s_axis_tdata_i(s_axis_tdata_i),
        .s_axis_tkeep_i(s_axis_tkeep_i),
        .s_axis_tvalid_i(s_axis_tvalid_i && input_allowed),
        .s_axis_tready_o(input_fifo_source_ready),
        .s_axis_tlast_i(s_axis_tlast_i),
        .s_axis_tuser_i(s_axis_tuser_i),
        .m_axis_tdata_o(input_fifo_data),
        .m_axis_tkeep_o(input_fifo_keep),
        .m_axis_tvalid_o(input_fifo_valid),
        .m_axis_tready_i(input_fifo_ready),
        .m_axis_tlast_o(input_fifo_last),
        .m_axis_tuser_o(input_fifo_user),
        .occupancy_o(input_fifo_occupancy)
    );

    bank_scheduler scheduler (
        .cycle_mod3_i(scheduler_cycle_mod3),
        .row_mod6_i(scheduler_row_mod6),
        .read_buffer_i(1'b0),
        .read_banks_o(scheduler_read_banks),
        .write_banks_o(scheduler_write_banks),
        .conflict_o(scheduler_conflict)
    );

    sram_mbist #(
        .BANK_COUNT(BANK_COUNT),
        .ADDRESS_WIDTH(SRAM_ADDRESS_WIDTH),
        .DATA_WIDTH(32),
        .DEPTH(SRAM_DEPTH)
    ) mbist (
        .clk_i(clk_i),
        .reset_n_i(reset_n_i),
        .start_i(mbist_start_i && !transaction_busy_q),
        .memory_enable_o(mbist_memory_enable),
        .memory_write_o(mbist_memory_write),
        .memory_bank_o(mbist_memory_bank),
        .memory_address_o(mbist_memory_address),
        .memory_write_data_o(mbist_memory_write_data),
        .memory_read_data_i(mbist_memory_read_data),
        .busy_o(mbist_busy),
        .done_o(mbist_done_o),
        .pass_o(mbist_pass_o),
        .fail_bank_o(mbist_fail_bank_o),
        .fail_address_o(mbist_fail_address_o)
    );

    assign mbist_memory_read_data = memory_read_data[
        (mbist_memory_bank * 32) +: 32
    ];

    always @* begin
        memory_enable = 0;
        memory_write = 0;
        memory_address = 0;
        memory_write_data = 0;
        selected_bank = 0;
        selected_address = 0;
        memory_slot = 0;

        if (mbist_busy) begin
            memory_enable[mbist_memory_bank] = mbist_memory_enable;
            memory_write[mbist_memory_bank] = mbist_memory_write;
            memory_address[
                (mbist_memory_bank * SRAM_ADDRESS_WIDTH) +: SRAM_ADDRESS_WIDTH
            ] = mbist_memory_address;
            memory_write_data[(mbist_memory_bank * 32) +: 32] =
                mbist_memory_write_data;
        end else if ((state_q == STATE_LOAD)
                && input_fifo_valid && input_fifo_ready) begin
            for (memory_slot = 0; memory_slot < 4; memory_slot = memory_slot + 1) begin
                selected_bank = (
                    load_x_q + memory_slot + (2 * load_row_q)
                ) % BANK_COUNT;
                selected_address =
                    (load_row_q * (padded_width_q / BANK_COUNT))
                    + ((load_x_q + memory_slot) / BANK_COUNT);
                memory_enable[selected_bank] = 1'b1;
                memory_write[selected_bank] = 1'b1;
                memory_address[
                    (selected_bank * SRAM_ADDRESS_WIDTH) +: SRAM_ADDRESS_WIDTH
                ] = selected_address[SRAM_ADDRESS_WIDTH - 1:0];
                memory_write_data[(selected_bank * 32) +: 32] =
                    input_fifo_data[(memory_slot * 32) +: 32];
            end
        end else if (state_q == STATE_READ) begin
            for (memory_slot = 0; memory_slot < 6; memory_slot = memory_slot + 1) begin
                selected_bank = scheduler_read_banks[(memory_slot * 4) +: 4];
                selected_address =
                    (compute_row_q * (padded_width_q / BANK_COUNT))
                    + (((issue_q * 4) + memory_slot) / BANK_COUNT);
                memory_enable[selected_bank] = 1'b1;
                memory_write[selected_bank] = 1'b0;
                memory_address[
                    (selected_bank * SRAM_ADDRESS_WIDTH) +: SRAM_ADDRESS_WIDTH
                ] = selected_address[SRAM_ADDRESS_WIDTH - 1:0];
            end
        end
    end

    genvar bank;
    generate
        for (bank = 0; bank < BANK_COUNT; bank = bank + 1) begin : memory_banks
`ifdef NEUMANN_SKY130_SRAM
            sky130_sram_1024x32 bank_memory (
                .clk_i(clk_i),
                .enable_i(memory_enable[bank]),
                .write_i(memory_write[bank]),
                .address_i(memory_address[
                    (bank * SRAM_ADDRESS_WIDTH) +: SRAM_ADDRESS_WIDTH
                ]),
                .write_data_i(memory_write_data[(bank * 32) +: 32]),
                .read_data_o(memory_read_data[(bank * 32) +: 32])
            );
`else
            single_port_sram #(
                .DATA_WIDTH(32),
                .ADDRESS_WIDTH(SRAM_ADDRESS_WIDTH),
                .DEPTH(SRAM_DEPTH)
            ) bank_memory (
                .clk_i(clk_i),
                .enable_i(memory_enable[bank]),
                .write_i(memory_write[bank]),
                .address_i(memory_address[
                    (bank * SRAM_ADDRESS_WIDTH) +: SRAM_ADDRESS_WIDTH
                ]),
                .write_data_i(memory_write_data[(bank * 32) +: 32]),
                .read_data_o(memory_read_data[(bank * 32) +: 32])
            );
`endif
        end
    endgenerate

`ifndef SYNTHESIS
    function automatic integer input_bank_index_for_assert;
        input integer x;
        input integer y;
        input integer slot;
        begin
            input_bank_index_for_assert =
                (x + slot + (2 * y)) % BANK_COUNT;
        end
    endfunction

    function automatic [BANK_COUNT - 1:0] input_write_mask_for_assert;
        input integer x;
        input integer y;
        integer slot;
        integer bank_index_value;
        begin
            input_write_mask_for_assert = {BANK_COUNT{1'b0}};
            for (slot = 0; slot < 4; slot = slot + 1) begin
                bank_index_value = input_bank_index_for_assert(x, y, slot);
                input_write_mask_for_assert[bank_index_value] = 1'b1;
            end
        end
    endfunction

    integer assert_input_slot_a;
    integer assert_input_slot_b;

    // The input-side proof is deliberately local to the synchronous FIFO
    // boundary: one accepted beat carries four adjacent samples and is drained
    // into four distinct banks in one STATE_LOAD cycle.
    always @(posedge clk_i) begin
        if (reset_n_i) begin
            assert (input_fifo_occupancy <= FIFO_DEPTH)
                else $fatal(1, "engine input FIFO occupancy overflow: %0d",
                    input_fifo_occupancy);

            if (s_axis_tvalid_i && input_allowed && input_fifo_source_ready) begin
                assert (input_fifo_occupancy < FIFO_DEPTH)
                    else $fatal(1, "engine input FIFO accepted a beat while full");
            end
            if (input_fifo_valid && input_fifo_ready) begin
                assert (input_fifo_occupancy > 0)
                    else $fatal(1, "engine input FIFO drained while empty");

                for (assert_input_slot_a = 0;
                        assert_input_slot_a < 4;
                        assert_input_slot_a = assert_input_slot_a + 1) begin
                    for (assert_input_slot_b = assert_input_slot_a + 1;
                            assert_input_slot_b < 4;
                            assert_input_slot_b = assert_input_slot_b + 1) begin
                        assert (
                            input_bank_index_for_assert(
                                load_x_q, load_row_q, assert_input_slot_a
                            ) != input_bank_index_for_assert(
                                load_x_q, load_row_q, assert_input_slot_b
                            )
                        ) else $fatal(
                            1,
                            "input bank collision row=%0d x=%0d slots=%0d,%0d",
                            load_row_q,
                            load_x_q,
                            assert_input_slot_a,
                            assert_input_slot_b
                        );
                    end
                end
                assert (
                    memory_enable === input_write_mask_for_assert(
                        load_x_q, load_row_q
                    )
                ) else $fatal(
                    1,
                    "input write-enable mask mismatch row=%0d x=%0d",
                    load_row_q,
                    load_x_q
                );
                assert (
                    memory_write === input_write_mask_for_assert(
                        load_x_q, load_row_q
                    )
                ) else $fatal(
                    1,
                    "input write mask mismatch row=%0d x=%0d",
                    load_row_q,
                    load_x_q
                );
            end
        end
    end
`endif

    stencil_multicast #(.DATA_WIDTH(32)) multicast (
        .unique_samples_i(unique_samples_q),
        .lane_samples_o(lane_samples)
    );

    complex_stencil_mac mac (
        .clk_i(clk_i),
        .reset_n_i(reset_n_i),
        .clear_i(datapath_clear),
        .in_valid_i(state_q == STATE_SUBMIT),
        .in_ready_o(mac_input_ready),
        .lane_samples_i(lane_samples),
        .coefficients_i(coefficients_q),
        .lane_mask_i(lane_mask_q),
        .transaction_id_i(transaction_id_q),
        .last_i(issue_last_q),
        .out_valid_o(mac_output_valid),
        .out_ready_i(mac_output_ready),
        .out_samples_o(mac_output_samples),
        .out_lane_flags_o(mac_output_lane_flags),
        .out_lane_mask_o(mac_output_lane_mask),
        .out_transaction_id_o(mac_output_transaction_id),
        .out_last_o(mac_output_last),
        .busy_o(mac_busy)
    );

    assign mac_flag_union =
        (mac_output_lane_mask[0] ? mac_output_lane_flags[3:0] : 4'b0)
        | (mac_output_lane_mask[1] ? mac_output_lane_flags[7:4] : 4'b0)
        | (mac_output_lane_mask[2] ? mac_output_lane_flags[11:8] : 4'b0)
        | (mac_output_lane_mask[3] ? mac_output_lane_flags[15:12] : 4'b0);
    assign mac_output_keep = {
        {4{mac_output_lane_mask[3]}},
        {4{mac_output_lane_mask[2]}},
        {4{mac_output_lane_mask[1]}},
        {4{mac_output_lane_mask[0]}}
    };
    assign mac_output_user = {
        mac_output_transaction_id,
        mac_flag_union,
        mac_output_lane_mask
    };

    axis_fifo #(
        .DATA_WIDTH(128),
        .KEEP_WIDTH(16),
        .USER_WIDTH(24),
        .DEPTH(FIFO_DEPTH)
    ) output_fifo (
        .clk_i(clk_i),
        .reset_n_i(reset_n_i),
        .clear_i(datapath_clear),
        .s_axis_tdata_i(mac_output_samples),
        .s_axis_tkeep_i(mac_output_keep),
        .s_axis_tvalid_i(mac_output_valid),
        .s_axis_tready_o(mac_output_ready),
        .s_axis_tlast_i(mac_output_last),
        .s_axis_tuser_i(mac_output_user),
        .m_axis_tdata_o(m_axis_tdata_o),
        .m_axis_tkeep_o(m_axis_tkeep_o),
        .m_axis_tvalid_o(m_axis_tvalid_o),
        .m_axis_tready_i(m_axis_tready_i),
        .m_axis_tlast_o(m_axis_tlast_o),
        .m_axis_tuser_o(m_axis_tuser_o),
        .occupancy_o(output_fifo_occupancy)
    );

    always @(posedge clk_i or negedge reset_n_i) begin
        if (!reset_n_i) begin
            state_q <= STATE_IDLE;
            transaction_busy_q <= 0;
            clear_on_error_q <= 0;
            logical_width_q <= 0;
            height_q <= 0;
            padded_width_q <= 0;
            coefficients_q <= 0;
            transaction_id_q <= 0;
            load_row_q <= 0;
            load_x_q <= 0;
            compute_row_q <= 0;
            issue_q <= 0;
            read_banks_q <= 0;
            unique_samples_q <= 0;
            lane_mask_q <= 0;
            issue_last_q <= 0;
            done_pulse_o <= 0;
            error_pulse_o <= 0;
            error_code_o <= 0;
            fp_flags_pulse_o <= 0;
        end else begin
            done_pulse_o <= 0;
            error_pulse_o <= 0;
            fp_flags_pulse_o <= 0;
            clear_on_error_q <= 0;

            if (soft_reset_i || abort_i) begin
                state_q <= STATE_IDLE;
                transaction_busy_q <= 0;
                load_row_q <= 0;
                load_x_q <= 0;
                compute_row_q <= 0;
                issue_q <= 0;
                error_code_o <= 0;
            end else begin
                if (start_i && (state_q == STATE_IDLE) && !mbist_busy) begin
                    if (!configuration_valid) begin
                        error_pulse_o <= 1;
                        error_code_o <= 1;
                    end else begin
                        state_q <= STATE_LOAD;
                        transaction_busy_q <= 1;
                        logical_width_q <= logical_width_i;
                        height_q <= height_i;
                        padded_width_q <= padded_width_i;
                        coefficients_q <= coefficients_i;
                        transaction_id_q <= transaction_id_i;
                        load_row_q <= 0;
                        load_x_q <= 0;
                        compute_row_q <= 0;
                        issue_q <= 0;
                        error_code_o <= 0;
                    end
                end

                if ((state_q == STATE_LOAD)
                        && input_fifo_valid && input_fifo_ready) begin
                    if (input_fifo_keep != 16'hffff
                            || (input_fifo_last != expected_input_last)) begin
                        state_q <= STATE_IDLE;
                        transaction_busy_q <= 0;
                        error_pulse_o <= 1;
                        error_code_o <= input_fifo_last ? 2 : 3;
                        clear_on_error_q <= 1;
                    end else if (expected_input_last) begin
                        state_q <= STATE_READ;
                        compute_row_q <= 0;
                        issue_q <= 0;
                    end else if ((load_x_q + 4) >= padded_width_q) begin
                        load_x_q <= 0;
                        load_row_q <= load_row_q + 1'b1;
                    end else begin
                        load_x_q <= load_x_q + 4;
                    end
                end

                if (state_q == STATE_READ) begin
                    if (scheduler_conflict) begin
                        state_q <= STATE_IDLE;
                        transaction_busy_q <= 0;
                        error_pulse_o <= 1;
                        error_code_o <= 4;
                        clear_on_error_q <= 1;
                    end else begin
                        read_banks_q <= scheduler_read_banks;
                        state_q <= STATE_CAPTURE;
                    end
                end

                if (state_q == STATE_CAPTURE) begin
                    for (capture_slot = 0; capture_slot < 6; capture_slot = capture_slot + 1) begin
                        unique_samples_q[(capture_slot * 32) +: 32] <=
                            memory_read_data[
                                (read_banks_q[(capture_slot * 4) +: 4] * 32) +: 32
                            ];
                    end
                    remaining_lanes = logical_width_q - (issue_q * 4);
                    if (remaining_lanes >= 4) begin
                        lane_mask_q <= 4'b1111;
                    end else begin
                        lane_mask_q <= (1 << remaining_lanes) - 1;
                    end
                    issue_last_q <=
                        (compute_row_q == (height_q - 1))
                        && (((issue_q + 1) * 4) >= logical_width_q);
                    state_q <= STATE_SUBMIT;
                end

                if ((state_q == STATE_SUBMIT) && mac_input_ready) begin
                    if (issue_last_q) begin
                        state_q <= STATE_WAIT_OUTPUT;
                    end else if (((issue_q + 1) * 4) >= logical_width_q) begin
                        issue_q <= 0;
                        compute_row_q <= compute_row_q + 1'b1;
                        state_q <= STATE_READ;
                    end else begin
                        issue_q <= issue_q + 1'b1;
                        state_q <= STATE_READ;
                    end
                end

                if (mac_output_valid && mac_output_ready) begin
                    fp_flags_pulse_o <= mac_flag_union;
                end

                if (m_axis_tvalid_o && m_axis_tready_i && m_axis_tlast_o) begin
                    state_q <= STATE_IDLE;
                    transaction_busy_q <= 0;
                    done_pulse_o <= 1;
                end
            end
        end
    end
endmodule
