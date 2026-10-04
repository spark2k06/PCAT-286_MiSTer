`timescale 1ns/1ps
module p06_core_memory_tb;
    `include "spk286_signals.svh"
    wire p06_code_board_ready=1,p06_data_board_ready=1;
    spk286 #(.P06_REGISTER_PILOT(1'b0),.P06_FETCH_PILOT(1'b1),.P06_MEMORY_PILOT(1'b1)) dut (.*);
    initial begin #20; $fatal(1,"missing configuration guard"); end
endmodule
