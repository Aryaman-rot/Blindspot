`timescale 1ns / 1ps
// =============================================================================
// signal_proc.v  --  4-input Priority Encoder / Data-Bin Gate
//
// Inputs
//   input_interface : 0 = MEM path,  1 = Radar path
//   data_size       : 2-bit, values 0-3  (Python data_size - 1)
//   output_active   : 0 or 1
//   data_bin        : 14-bit, 0-10000
//
// Outputs
//   encoded_out  : 2'b01 = MEM active, 2'b10 = Radar active, 2'b00 = reset
//   overflow_flag: 1 when data_bin > 5000  (drives GROUP3 coverage)
// =============================================================================
module signal_proc (
    input        clk,
    input        rst_n,
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
            case (input_interface)
                1'b0:    encoded_out <= 2'b01;
                1'b1:    encoded_out <= 2'b10;
                default: encoded_out <= 2'b00;
            endcase
            overflow_flag <= (data_bin > 14'd5000) ? 1'b1 : 1'b0;
        end
    end

endmodule
