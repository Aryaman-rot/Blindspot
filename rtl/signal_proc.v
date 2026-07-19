`timescale 1ns / 1ps
// =============================================================================
// signal_proc.v  --  4-input Priority Encoder / Data-Bin Gate (with Bypass Mode)
//
// Inputs
//   data_mode       : 0 = Bypass (passthrough), 1 = Process (priority encode)
//   input_interface : 0 = MEM path,  1 = Radar path
//   data_size       : 2-bit, values 0-3  (Python data_size - 1)
//   output_active   : 0 or 1
//   data_bin        : 14-bit, 0-10000
//
// Outputs
//   encoded_out  : 2'b01 = MEM active, 2'b10 = Radar active, 2'b00 = reset/gated
//   overflow_flag: 1 when data_bin > 5000  (drives GROUP3 coverage)
// =============================================================================
module signal_proc (
    input        clk,
    input        rst_n,
    input        data_mode,       // NEW: 0 = Bypass, 1 = Process
    input        input_interface,
    input  [1:0] data_size,
    input        output_active,
    input [13:0] data_bin,
    output reg [1:0] encoded_out,
    output reg       overflow_flag
);

    always @(posedge clk) begin
        if (!rst_n) begin
            encoded_out   <= 2'b00;
            overflow_flag <= 1'b0;
        end else begin
            if (data_mode == 1'b0) begin
                // --- Bypass Mode ---
                // Direct routing based on input_interface
                encoded_out <= (input_interface == 1'b0) ? 2'b01 : 2'b10;
            end else begin
                // --- Process Mode ---
                // Gating Rule: if Radar (1), Python size 4 (2'd3), and output_active is 0,
                // gate/disable the output instead of routing to Radar (2'b10).
                if (input_interface == 1'b1 && data_size == 2'd3 && output_active == 1'b0) begin
                    encoded_out <= 2'b00;
                end else begin
                    encoded_out <= (input_interface == 1'b0) ? 2'b01 : 2'b10;
                end
            end

            // Overflow flag logic (applies to both modes)
            overflow_flag <= (data_bin > 14'd5000) ? 1'b1 : 1'b0;
        end
    end

endmodule
