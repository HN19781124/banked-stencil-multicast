`timescale 1ns/1ps

module banked_stencil_accelerator (
    input  wire         core_clk_i,
    input  wire         core_reset_n_i,
    input  wire [7:0]   s_axil_awaddr_i,
    input  wire         s_axil_awvalid_i,
    output wire         s_axil_awready_o,
    input  wire [31:0]  s_axil_wdata_i,
    input  wire [3:0]   s_axil_wstrb_i,
    input  wire         s_axil_wvalid_i,
    output wire         s_axil_wready_o,
    output wire [1:0]   s_axil_bresp_o,
    output wire         s_axil_bvalid_o,
    input  wire         s_axil_bready_i,
    input  wire [7:0]   s_axil_araddr_i,
    input  wire         s_axil_arvalid_i,
    output wire         s_axil_arready_o,
    output wire [31:0]  s_axil_rdata_o,
    output wire [1:0]   s_axil_rresp_o,
    output wire         s_axil_rvalid_o,
    input  wire         s_axil_rready_i,
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
    output wire         irq_o
);
    wire internal_reset_n;
    wire start_pulse;
    wire abort_pulse;
    wire soft_reset_pulse;
    wire mbist_start_pulse;
    wire [31:0] logical_width;
    wire [31:0] height;
    wire [31:0] padded_width;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [31:0] row_stride_bytes;
    /* verilator lint_on UNUSEDSIGNAL */
    wire [95:0] coefficients;
    wire [15:0] transaction_id;
    wire engine_busy;
    wire engine_done_pulse;
    wire engine_error_pulse;
    wire [7:0] engine_error_code;
    wire [3:0] engine_fp_flags;
    wire mbist_done;
    wire mbist_pass;
    wire [3:0] mbist_fail_bank;
    wire [9:0] mbist_fail_address;

    reset_synchronizer reset_sync (
        .clk_i(core_clk_i),
        .async_reset_n_i(core_reset_n_i),
        .sync_reset_n_o(internal_reset_n)
    );

    axi_lite_csr csr (
        .clk_i(core_clk_i),
        .reset_n_i(internal_reset_n),
        .s_axi_awaddr_i(s_axil_awaddr_i),
        .s_axi_awvalid_i(s_axil_awvalid_i),
        .s_axi_awready_o(s_axil_awready_o),
        .s_axi_wdata_i(s_axil_wdata_i),
        .s_axi_wstrb_i(s_axil_wstrb_i),
        .s_axi_wvalid_i(s_axil_wvalid_i),
        .s_axi_wready_o(s_axil_wready_o),
        .s_axi_bresp_o(s_axil_bresp_o),
        .s_axi_bvalid_o(s_axil_bvalid_o),
        .s_axi_bready_i(s_axil_bready_i),
        .s_axi_araddr_i(s_axil_araddr_i),
        .s_axi_arvalid_i(s_axil_arvalid_i),
        .s_axi_arready_o(s_axil_arready_o),
        .s_axi_rdata_o(s_axil_rdata_o),
        .s_axi_rresp_o(s_axil_rresp_o),
        .s_axi_rvalid_o(s_axil_rvalid_o),
        .s_axi_rready_i(s_axil_rready_i),
        .busy_i(engine_busy),
        .done_pulse_i(engine_done_pulse),
        .error_pulse_i(engine_error_pulse),
        .error_code_i(engine_error_code),
        .fp_flags_i(engine_fp_flags),
        .mbist_done_i(mbist_done),
        .mbist_pass_i(mbist_pass),
        .mbist_fail_bank_i(mbist_fail_bank),
        .mbist_fail_address_i(mbist_fail_address),
        .start_pulse_o(start_pulse),
        .abort_pulse_o(abort_pulse),
        .soft_reset_pulse_o(soft_reset_pulse),
        .mbist_start_pulse_o(mbist_start_pulse),
        .logical_width_o(logical_width),
        .height_o(height),
        .padded_width_o(padded_width),
        .row_stride_bytes_o(row_stride_bytes),
        .coefficients_o(coefficients),
        .transaction_id_o(transaction_id),
        .irq_o(irq_o)
    );

    banked_stencil_engine engine (
        .clk_i(core_clk_i),
        .reset_n_i(internal_reset_n),
        .start_i(start_pulse),
        .abort_i(abort_pulse),
        .soft_reset_i(soft_reset_pulse),
        .mbist_start_i(mbist_start_pulse),
        .logical_width_i(logical_width),
        .height_i(height),
        .padded_width_i(padded_width),
        .coefficients_i(coefficients),
        .transaction_id_i(transaction_id),
        .s_axis_tdata_i(s_axis_tdata_i),
        .s_axis_tkeep_i(s_axis_tkeep_i),
        .s_axis_tvalid_i(s_axis_tvalid_i),
        .s_axis_tready_o(s_axis_tready_o),
        .s_axis_tlast_i(s_axis_tlast_i),
        .s_axis_tuser_i(s_axis_tuser_i),
        .m_axis_tdata_o(m_axis_tdata_o),
        .m_axis_tkeep_o(m_axis_tkeep_o),
        .m_axis_tvalid_o(m_axis_tvalid_o),
        .m_axis_tready_i(m_axis_tready_i),
        .m_axis_tlast_o(m_axis_tlast_o),
        .m_axis_tuser_o(m_axis_tuser_o),
        .busy_o(engine_busy),
        .done_pulse_o(engine_done_pulse),
        .error_pulse_o(engine_error_pulse),
        .error_code_o(engine_error_code),
        .fp_flags_pulse_o(engine_fp_flags),
        .mbist_done_o(mbist_done),
        .mbist_pass_o(mbist_pass),
        .mbist_fail_bank_o(mbist_fail_bank),
        .mbist_fail_address_o(mbist_fail_address)
    );
endmodule
