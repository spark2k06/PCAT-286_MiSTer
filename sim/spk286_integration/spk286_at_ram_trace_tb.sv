`timescale 1ns/1ps
module spk286_at_ram_trace_tb;
    logic clk=0, reset=1, cpu_reset=0, retired=0;
    always #10 clk=~clk;
    logic [15:0] instruction_ip=0, cpu_cs=16'hF000, cpu_flags=16'h46;
    logic [23:0] cpu_cs_base=24'h0F0000;
    logic [7:0] cpu_opcode=0;
    logic [127:0] cpu_gpr=0;
    logic [63:0] cpu_segments=0;
    logic [95:0] cpu_segment_bases=0;
    logic cpu_valid=0, cpu_ready=0, cpu_write=0, cpu_bhe_n=0;
    logic [3:0] cpu_status=5;
    logic [23:0] cpu_address=1;
    logic [15:0] cpu_data_in=16'hFE00;
    logic backend_accept=0, backend_ready=0, backend_read_valid=0;
    logic backend_code=0, backend_write=0;
    logic [1:0] backend_owner=0, backend_be=2'b10;
    logic [23:0] backend_address=1;
    logic [15:0] backend_data_in=16'hFEFF, backend_data_out=0;
    logic [23:0] kf_address=0;
    logic [15:0] kf_data=16'hFEFF;
    logic kf_read_request=0, kf_read_flag=0, sdram_read_command=0;
    logic [3:0] owner_state=4'b1000;
    logic [1:0] sdram_dqm=0, select_page=0;
    wire [127:0] selected_words;
    wire captured, armed;
    wire [15:0] comparisons;
    logic [511:0] saved;
    spk286_at_ram_trace dut(.*);
    task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
    task retire(input [15:0] ip, input [7:0] op);
        begin instruction_ip=ip; cpu_opcode=op; retired=1; tick(); retired=0; tick(); end
    endtask
    task boot;
        begin reset=1; tick(); reset=0; tick(); retire(16'h9F14,8'hFC); end
    endtask
    initial begin
        tick(); reset=0;
        retire(16'h9F37,8'h3A);
        if(armed || captured || comparisons!=0) $fatal(1,"unarmed comparison captured");
        cpu_cs=16'h1234; retire(16'h9F14,8'hFC);
        if(armed) $fatal(1,"wrong ROM armed");
        cpu_cs=16'hF000; retire(16'h9F14,8'hFC);
        backend_accept=1; kf_read_request=1; tick(); backend_accept=0; kf_read_request=0;
        sdram_read_command=1; tick(); sdram_read_command=0;
        kf_read_flag=1; tick(); kf_read_flag=0;
        backend_ready=1; backend_read_valid=1; tick(); backend_ready=0; backend_read_valid=0;
        cpu_valid=1; cpu_ready=1; tick(); cpu_valid=0; cpu_ready=0;
        cpu_gpr[8 +: 8]=8'hFF; cpu_gpr[48 +: 8]=8'hFE; cpu_gpr[112 +: 16]=2;
        cpu_flags=16'h2; retire(16'h9F37,8'h3A);
        if(!captured || !armed || comparisons!=1 || selected_words[31:0]!==32'hC1FFFEFE)
            $fatal(1,"comparison capture %h",selected_words);
        if(dut.frozen_q[128 +: 24]!==24'd1 || dut.frozen_q[160 +: 24]!==24'd1 ||
           dut.frozen_q[192 +: 24]!==24'd0 || dut.frozen_q[272 +: 16]!==16'hFEFF)
            $fatal(1,"read chain capture");
        saved=dut.frozen_q;
        // Prefetch, later comparisons and CPU-only reset cannot erase a fault.
        cpu_reset=1; tick(); cpu_reset=0; cpu_gpr=0; retire(16'h9F37,8'h3A);
        if(dut.frozen_q!==saved || !captured) $fatal(1,"first fault not retained");
        for(integer i=0;i<4;i=i+1) begin
            select_page=2'(i); tick();
            if(selected_words!==saved[i*128 +: 128]) $fatal(1,"page mismatch");
        end
        boot(); cpu_flags=16'h46; retire(16'h9F37,8'h3A);
        if(captured || comparisons!=1) $fatal(1,"good comparison false positive");
        retire(16'h9F3B,8'h33);
        if(!captured || dut.frozen_q[31:24]!==8'hC2) $fatal(1,"bad branch missing");
        boot(); retire(16'h9F37,8'h3A); retire(16'h9F4D,8'hE4);
        if(!captured || dut.frozen_q[31:24]!==8'hC3) $fatal(1,"parity path missing");
        reset=1; tick();
        if(captured || armed || comparisons!=0 || selected_words!=0) $fatal(1,"core reset failed");
        $display("AT_RAM_TRACE_PASS compare_bus_lanes_retention_branch_parity_pages");
        $finish;
    end
endmodule
