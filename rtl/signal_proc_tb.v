`timescale 1ns / 1ps
// =============================================================================
// signal_proc_tb.v  --  Batch testbench for signal_proc (5 inputs)
//
// Reads  : rtl/stimulus.csv  (written by Python before iverilog call)
//            format per row: data_mode,input_interface,data_size_adj,output_active,data_bin
//            (no header; data_size_adj = Python data_size - 1)
//
// Writes : rtl/sim_output.csv
//            header: encoded_out,overflow_flag
// =============================================================================
module signal_proc_tb;

    reg        clk;
    reg        rst_n;
    reg        data_mode;
    reg        input_interface;
    reg  [1:0] data_size;
    reg        output_active;
    reg [13:0] data_bin;
    wire [1:0] encoded_out;
    wire       overflow_flag;

    signal_proc dut (
        .clk            (clk),
        .rst_n          (rst_n),
        .data_mode      (data_mode),
        .input_interface(input_interface),
        .data_size      (data_size),
        .output_active  (output_active),
        .data_bin       (data_bin),
        .encoded_out    (encoded_out),
        .overflow_flag  (overflow_flag)
    );

    // 10 ns clock
    initial clk = 1'b0;
    always  #5  clk = ~clk;

    integer stim_fd, out_fd, r;
    integer mode_v, iface_v, ds_v, out_act_v, dbin_v;

    initial begin
        // Two-cycle synchronous reset
        rst_n           = 1'b0;
        data_mode       = 1'b0;
        input_interface = 1'b0;
        data_size       = 2'd0;
        output_active   = 1'b0;
        data_bin        = 14'd0;
        @(posedge clk); #1;
        @(posedge clk); #1;
        rst_n = 1'b1;

        stim_fd = $fopen("rtl/stimulus.csv", "r");
        out_fd  = $fopen("rtl/sim_output.csv", "w");
        $fdisplay(out_fd, "encoded_out,overflow_flag");

        r = $fscanf(stim_fd, " %d,%d,%d,%d,%d", mode_v, iface_v, ds_v, out_act_v, dbin_v);
        while (r == 5) begin
            data_mode       = mode_v[0];
            input_interface = iface_v[0];
            data_size       = ds_v[1:0];
            output_active   = out_act_v[0];
            data_bin        = dbin_v[13:0];

            @(posedge clk); #1;

            $fdisplay(out_fd, "%0d,%0d", encoded_out, overflow_flag);

            r = $fscanf(stim_fd, " %d,%d,%d,%d,%d", mode_v, iface_v, ds_v, out_act_v, dbin_v);
        end

        $fclose(stim_fd);
        $fclose(out_fd);
        $finish;
    end

endmodule
