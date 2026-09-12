`timescale 1ns/1ps
module spk286_at_fault_trace_tb;
    logic clk=0, reset=1;
    always #5 clk=~clk;
    logic [18:0] sources=0;
    logic [15:0] cpu_cs=16'hf000,cpu_ip=16'hfff0;
    logic [23:0] cpu_address=24'hfffff0;
    logic [7:0] cpu_opcode=8'hea;
    logic [12:0] bus_flags=13'h1555;
    wire captured;
    wire [127:0] words;
    spk286_at_fault_trace dut(.*);
    logic [95:0] saved;
    initial begin
        repeat(3) @(negedge clk); reset=0;
        repeat(20) @(negedge clk);
        if(captured || words!==0) $fatal(1,"fault capture before error");
        sources=19'h120;
        @(negedge clk);
        if(!captured || words[31:0]!==32'h120 || words[63:32]!==32'hf000fff0 ||
           words[95:64]!==32'heafffff0 || words[127:115]!==bus_flags)
            $fatal(1,"first fault metadata mismatch %h",words);
        saved=words[95:0]; sources=19'h60000; cpu_ip=16'h1234; cpu_address=0;
        bus_flags=0;
        repeat(4) @(negedge clk);
        if(words[95:0]!==saved || words[114:96]!==sources || words[127:115]!==13'h1555)
            $fatal(1,"first fault overwritten or live sources stale");
        reset=1; @(negedge clk); sources=0; reset=0;
        @(negedge clk);
        if(captured || words!==0) $fatal(1,"fault reset failed");
        $display("AT_FAULT_TRACE_PASS"); $finish;
    end
endmodule
