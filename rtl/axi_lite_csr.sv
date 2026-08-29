`timescale 1ns/1ps

module axi_lite_csr (
    input  wire         clk_i,
    input  wire         reset_n_i,
    input  wire [7:0]   s_axi_awaddr_i,
    input  wire         s_axi_awvalid_i,
    output wire         s_axi_awready_o,
    input  wire [31:0]  s_axi_wdata_i,
    input  wire [3:0]   s_axi_wstrb_i,
    input  wire         s_axi_wvalid_i,
    output wire         s_axi_wready_o,
    output reg  [1:0]   s_axi_bresp_o,
    output reg          s_axi_bvalid_o,
    input  wire         s_axi_bready_i,
    input  wire [7:0]   s_axi_araddr_i,
    input  wire         s_axi_arvalid_i,
    output wire         s_axi_arready_o,
    output reg  [31:0]  s_axi_rdata_o,
    output reg  [1:0]   s_axi_rresp_o,
    output reg          s_axi_rvalid_o,
    input  wire         s_axi_rready_i,
    input  wire         busy_i,
    input  wire         done_pulse_i,
    input  wire         error_pulse_i,
    input  wire [7:0]   error_code_i,
    input  wire [3:0]   fp_flags_i,
    input  wire         mbist_done_i,
    input  wire         mbist_pass_i,
    input  wire [3:0]   mbist_fail_bank_i,
    input  wire [9:0]   mbist_fail_address_i,
    output reg          start_pulse_o,
    output reg          abort_pulse_o,
    output reg          soft_reset_pulse_o,
    output reg          mbist_start_pulse_o,
    output reg  [31:0]  logical_width_o,
    output reg  [31:0]  height_o,
    output reg  [31:0]  padded_width_o,
    output reg  [31:0]  row_stride_bytes_o,
    output reg  [95:0]  coefficients_o,
    output reg  [15:0]  transaction_id_o,
    output wire         irq_o
);
    localparam [1:0] AXI_OKAY = 2'b00;
    localparam [1:0] AXI_SLVERR = 2'b10;
    localparam [1:0] AXI_DECERR = 2'b11;

    reg aw_pending_q;
    reg [7:0] aw_address_q;
    reg w_pending_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strobe_q;
    reg irq_global_enable_q;
    reg [3:0] irq_enable_q;
    reg [3:0] irq_status_q;
    reg [3:0] fp_status_q;
    reg done_q;
    reg error_q;
    reg [7:0] error_code_q;
    reg mbist_done_q;
    reg mbist_pass_q;
    reg [3:0] mbist_fail_bank_q;
    reg [9:0] mbist_fail_address_q;
    reg [31:0] merged_data;
    reg [31:0] read_data;
    reg [1:0] read_response;
    reg [1:0] write_response;
    reg local_error;
    reg [7:0] local_error_code;

    wire accept_aw;
    wire accept_w;
    wire have_aw;
    wire have_w;
    wire write_commit;
    wire [7:0] selected_write_address;
    wire [31:0] selected_write_data;
    wire [3:0] selected_write_strobe;
    wire configuration_valid;

    function automatic [31:0] merge_strobes;
        input [31:0] previous;
        input [31:0] update;
        input [3:0] strobes;
        integer byte_index;
        begin
            merge_strobes = previous;
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1) begin
                if (strobes[byte_index]) begin
                    merge_strobes[(byte_index * 8) +: 8] =
                        update[(byte_index * 8) +: 8];
                end
            end
        end
    endfunction

    assign s_axi_awready_o = !aw_pending_q && !s_axi_bvalid_o;
    assign s_axi_wready_o = !w_pending_q && !s_axi_bvalid_o;
    assign s_axi_arready_o = !s_axi_rvalid_o;
    assign accept_aw = s_axi_awvalid_i && s_axi_awready_o;
    assign accept_w = s_axi_wvalid_i && s_axi_wready_o;
    assign have_aw = aw_pending_q || accept_aw;
    assign have_w = w_pending_q || accept_w;
    assign write_commit = have_aw && have_w && !s_axi_bvalid_o;
    assign selected_write_address = aw_pending_q ? aw_address_q : s_axi_awaddr_i;
    assign selected_write_data = w_pending_q ? w_data_q : s_axi_wdata_i;
    assign selected_write_strobe = w_pending_q ? w_strobe_q : s_axi_wstrb_i;
    assign configuration_valid =
        (logical_width_o >= 1)
        && (height_o >= 1)
        && (padded_width_o >= 12)
        && ((padded_width_o % 12) == 0)
        && (row_stride_bytes_o >= (padded_width_o * 4))
        && ((height_o * (padded_width_o / 12)) <= 512)
        && (padded_width_o >= ((((logical_width_o + 3) / 4) * 4) + 2));
    assign irq_o = irq_global_enable_q && |(irq_enable_q & irq_status_q);

    always @* begin
        read_data = 0;
        read_response = AXI_OKAY;
        case (s_axi_araddr_i)
            8'h00: read_data = 32'h4e423201;
            8'h04: read_data = 32'h00010000;
            8'h08: read_data = {23'b0, irq_global_enable_q, 8'b0};
            8'h0c: read_data = {
                27'b0,
                mbist_done_q,
                error_q,
                done_q,
                busy_i,
                !busy_i
            };
            8'h10: read_data = logical_width_o;
            8'h14: read_data = height_o;
            8'h18: read_data = padded_width_o;
            8'h1c: read_data = row_stride_bytes_o;
            8'h20: read_data = coefficients_o[31:0];
            8'h24: read_data = coefficients_o[63:32];
            8'h28: read_data = coefficients_o[95:64];
            8'h2c: read_data = {28'b0, irq_enable_q};
            8'h30: read_data = {28'b0, irq_status_q};
            8'h34: read_data = {28'b0, fp_status_q};
            8'h38: read_data = {24'b0, error_code_q};
            8'h3c: read_data = {16'b0, transaction_id_o};
            8'h40: read_data = 0;
            8'h44: read_data = {
                23'b0,
                mbist_fail_bank_q,
                mbist_done_q && !mbist_pass_q,
                mbist_pass_q,
                mbist_done_q
            };
            8'h48: read_data = {22'b0, mbist_fail_address_q};
            default: begin
                read_data = 0;
                read_response = AXI_DECERR;
            end
        endcase
    end

    always @(posedge clk_i or negedge reset_n_i) begin
        if (!reset_n_i) begin
            aw_pending_q <= 0;
            aw_address_q <= 0;
            w_pending_q <= 0;
            w_data_q <= 0;
            w_strobe_q <= 0;
            s_axi_bresp_o <= AXI_OKAY;
            s_axi_bvalid_o <= 0;
            s_axi_rdata_o <= 0;
            s_axi_rresp_o <= AXI_OKAY;
            s_axi_rvalid_o <= 0;
            irq_global_enable_q <= 0;
            irq_enable_q <= 0;
            irq_status_q <= 0;
            fp_status_q <= 0;
            done_q <= 0;
            error_q <= 0;
            error_code_q <= 0;
            mbist_done_q <= 0;
            mbist_pass_q <= 0;
            mbist_fail_bank_q <= 0;
            mbist_fail_address_q <= 0;
            start_pulse_o <= 0;
            abort_pulse_o <= 0;
            soft_reset_pulse_o <= 0;
            mbist_start_pulse_o <= 0;
            logical_width_o <= 4;
            height_o <= 1;
            padded_width_o <= 12;
            row_stride_bytes_o <= 48;
            coefficients_o <= 0;
            transaction_id_o <= 0;
        end else begin
            start_pulse_o <= 0;
            abort_pulse_o <= 0;
            soft_reset_pulse_o <= 0;
            mbist_start_pulse_o <= 0;
            local_error = 0;
            local_error_code = 0;

            if (s_axi_bvalid_o && s_axi_bready_i) begin
                s_axi_bvalid_o <= 0;
            end
            if (s_axi_rvalid_o && s_axi_rready_i) begin
                s_axi_rvalid_o <= 0;
            end

            if (accept_aw) begin
                aw_pending_q <= 1;
                aw_address_q <= s_axi_awaddr_i;
            end
            if (accept_w) begin
                w_pending_q <= 1;
                w_data_q <= s_axi_wdata_i;
                w_strobe_q <= s_axi_wstrb_i;
            end

            if (write_commit) begin
                aw_pending_q <= 0;
                w_pending_q <= 0;
                s_axi_bvalid_o <= 1;
                write_response = AXI_OKAY;
                case (selected_write_address)
                    8'h08: begin
                        merged_data = merge_strobes(
                            {23'b0, irq_global_enable_q, 8'b0},
                            selected_write_data,
                            selected_write_strobe
                        );
                        irq_global_enable_q <= merged_data[8];
                        if (merged_data[2]) begin
                            soft_reset_pulse_o <= 1;
                        end
                        if (merged_data[1]) begin
                            abort_pulse_o <= 1;
                        end
                        if (merged_data[0]) begin
                            if (busy_i || !configuration_valid) begin
                                write_response = AXI_SLVERR;
                                local_error = 1;
                                local_error_code = 1;
                            end else begin
                                start_pulse_o <= 1;
                                done_q <= 0;
                                error_q <= 0;
                                error_code_q <= 0;
                            end
                        end
                    end
                    8'h10: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                        end else begin
                            logical_width_o <= merge_strobes(
                                logical_width_o,
                                selected_write_data,
                                selected_write_strobe
                            );
                        end
                    end
                    8'h14: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                        end else begin
                            height_o <= merge_strobes(
                                height_o,
                                selected_write_data,
                                selected_write_strobe
                            );
                        end
                    end
                    8'h18: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                        end else begin
                            padded_width_o <= merge_strobes(
                                padded_width_o,
                                selected_write_data,
                                selected_write_strobe
                            );
                        end
                    end
                    8'h1c: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                        end else begin
                            row_stride_bytes_o <= merge_strobes(
                                row_stride_bytes_o,
                                selected_write_data,
                                selected_write_strobe
                            );
                        end
                    end
                    8'h20, 8'h24, 8'h28: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                            local_error = 1;
                            local_error_code = 6;
                        end else if (selected_write_address == 8'h20) begin
                            coefficients_o[31:0] <= merge_strobes(
                                coefficients_o[31:0], selected_write_data, selected_write_strobe
                            );
                        end else if (selected_write_address == 8'h24) begin
                            coefficients_o[63:32] <= merge_strobes(
                                coefficients_o[63:32], selected_write_data, selected_write_strobe
                            );
                        end else begin
                            coefficients_o[95:64] <= merge_strobes(
                                coefficients_o[95:64], selected_write_data, selected_write_strobe
                            );
                        end
                    end
                    8'h2c: irq_enable_q <= merge_strobes(
                        {28'b0, irq_enable_q}, selected_write_data, selected_write_strobe
                    );
                    8'h30: begin
                        merged_data = merge_strobes(
                            0, selected_write_data, selected_write_strobe
                        );
                        irq_status_q <= irq_status_q & ~merged_data[3:0];
                    end
                    8'h34: begin
                        merged_data = merge_strobes(
                            0, selected_write_data, selected_write_strobe
                        );
                        fp_status_q <= fp_status_q & ~merged_data[3:0];
                    end
                    8'h3c: begin
                        if (busy_i) begin
                            write_response = AXI_SLVERR;
                        end else begin
                            merged_data = merge_strobes(
                                {16'b0, transaction_id_o},
                                selected_write_data,
                                selected_write_strobe
                            );
                            transaction_id_o <= merged_data[15:0];
                        end
                    end
                    8'h40: begin
                        merged_data = merge_strobes(0, selected_write_data, selected_write_strobe);
                        if (merged_data[0]) begin
                            if (busy_i) begin
                                write_response = AXI_SLVERR;
                            end else begin
                                mbist_start_pulse_o <= 1;
                                mbist_done_q <= 0;
                                mbist_pass_q <= 0;
                                mbist_fail_bank_q <= 0;
                                mbist_fail_address_q <= 0;
                            end
                        end
                    end
                    8'h00, 8'h04, 8'h0c, 8'h38, 8'h44, 8'h48:
                        write_response = AXI_SLVERR;
                    default: write_response = AXI_DECERR;
                endcase
                s_axi_bresp_o <= write_response;
            end

            if (s_axi_arvalid_i && s_axi_arready_o) begin
                s_axi_rdata_o <= read_data;
                s_axi_rresp_o <= read_response;
                s_axi_rvalid_o <= 1;
            end

            if (done_pulse_i) begin
                done_q <= 1;
                irq_status_q[0] <= 1;
            end
            if (error_pulse_i || local_error) begin
                error_q <= 1;
                irq_status_q[1] <= 1;
                if (!error_q) begin
                    error_code_q <= local_error ? local_error_code : error_code_i;
                end
            end
            if (mbist_done_i) begin
                irq_status_q[2] <= 1;
                mbist_done_q <= 1;
                mbist_pass_q <= mbist_pass_i;
                mbist_fail_bank_q <= mbist_fail_bank_i;
                mbist_fail_address_q <= mbist_fail_address_i;
            end
            if (fp_flags_i != 0) begin
                fp_status_q <= fp_status_q | fp_flags_i;
                irq_status_q[3] <= 1;
            end
            if (soft_reset_pulse_o) begin
                irq_status_q <= 0;
                fp_status_q <= 0;
                done_q <= 0;
                error_q <= 0;
                error_code_q <= 0;
                mbist_done_q <= 0;
                mbist_pass_q <= 0;
                mbist_fail_bank_q <= 0;
                mbist_fail_address_q <= 0;
            end
        end
    end
endmodule
