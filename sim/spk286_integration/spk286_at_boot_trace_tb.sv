`timescale 1ns/1ps
module spk286_at_boot_trace_tb;
    logic clk=0, reset=1;
    logic cpu_valid=0, cpu_write=0, cpu_ready=0, cpu_halted=0;
    logic [3:0] cpu_status=4'hF;
    logic [23:0] cpu_address=0, cpu_cs_base=24'hFF0000;
    logic [15:0] cpu_data_in=0, cpu_cs=16'hF000, cpu_ip=16'hFFF0;
    logic [7:0] cpu_opcode=0;
    logic backend_valid=0, backend_command_valid=0, backend_code=0;
    logic backend_write=0, backend_accept=0, backend_ready=0;
    logic backend_read_valid=0;
    logic [23:0] backend_address=0, kf_address=0;
    logic [1:0] backend_byte_enable=0, sdram_dqm=0;
    logic [15:0] backend_read_data=0, kf_data=0;
    logic kf_read_request=0, kf_read_flag=0, sdram_read_command=0;
    logic [3:0] owner_state=0;
    logic [4:0] select_index=0;
    logic select_detail=0;
    wire [127:0] selected_words;
    wire selected_valid, full, capture_pending;
    wire [5:0] capture_count;
    integer cycles=0, start_cycle=0, first_sample_wait=0, expected_wait=0;
    logic [127:0] saved_address_view;
    always #5 clk=~clk;
    spk286_at_boot_trace dut (.*);

    task automatic tick;
        begin
            @(posedge clk); #1;
            cycles=cycles+1;
        end
    endtask

    task automatic begin_fetch(input logic [23:0] address);
        begin
            cpu_valid=1;
            cpu_status=4'hD;
            cpu_address=address;
            cpu_opcode=0;
            start_cycle=cycles+1;
            tick();
            if (!full && !capture_pending)
                $fatal(1,"CPU code request did not arm trace");
            repeat (2) tick();
        end
    endtask

    task automatic memory_beat(input logic [23:0] address,
                               input logic [1:0] be,
                               input logic [15:0] raw_data,
                               input logic first);
        begin
            backend_valid=1;
            backend_command_valid=1;
            backend_code=1;
            backend_accept=1;
            backend_address=address;
            backend_byte_enable=be;
            kf_address=24'h07FFF8;
            kf_read_request=1;
            tick();
            backend_command_valid=0;
            backend_accept=0;
            kf_read_request=0;
            sdram_read_command=1;
            sdram_dqm=0;
            tick();
            sdram_read_command=0;
            repeat (2) tick();
            kf_read_flag=1;
            kf_data=raw_data;
            owner_state=4'h8;
            if (first) first_sample_wait=cycles+1-start_cycle;
            tick();
            kf_read_flag=0;
            backend_read_data=raw_data;
            backend_read_valid=1;
            // A data-valid pulse alone is not CPU READY and must not commit.
            tick();
            backend_ready=1;
            tick();
            backend_valid=0;
            backend_code=0;
            backend_ready=0;
            backend_read_valid=0;
            tick();
        end
    endtask

    task automatic complete_fetch;
        begin
            cpu_data_in=16'h12EA;
            cpu_opcode=8'hEA;
            cpu_ready=1;
            expected_wait=cycles+1-start_cycle;
            tick();
            cpu_ready=0;
            cpu_valid=0;
            cpu_status=4'hF;
            tick();
        end
    endtask

    initial begin
        tick(); tick(); reset=0; tick();
        if (selected_valid || selected_words != 0)
            $fatal(1,"unwritten RAM was exposed after reset");

        begin_fetch(24'hFFFFF0);
        if (!selected_valid || selected_words[23:0] != 24'hFFFFF0 ||
            selected_words[63] || capture_count != 0)
            $fatal(1,"pending first fetch is not observable before READY");
        memory_beat(24'hFFFFF0,2'b01,16'h34EA,1'b1);
        memory_beat(24'hFFFFF1,2'b10,16'h12AD,1'b0);
        if (capture_count != 0)
            $fatal(1,"backend completion committed before CPU READY");
        complete_fetch();
        tick();
        if (capture_count != 1 || !selected_valid || capture_pending)
            $fatal(1,"first CPU completion not recorded exactly once");
        if (selected_words[31:0] !== 32'h8DFFFFF0 ||
            selected_words[63:32] !== 32'hFA07FFF8 ||
            selected_words[95:64] !== 32'hF000FFF0 ||
            selected_words[127:112] !== 16'h12EA ||
            selected_words[111:96] !== 16'(expected_wait))
            $fatal(1,"address view mismatch %h wait=%0d",selected_words,expected_wait);
        saved_address_view=selected_words;
        select_detail=1; tick();
        if (selected_words[31:0] !== 32'h00FF0000 ||
            selected_words[63:32] !== 32'h34EA12AD ||
            selected_words[95:64] !== 32'hFFFFF068 ||
            selected_words[127:112] !== 16'h00EA ||
            selected_words[111:96] !== 16'(first_sample_wait))
            $fatal(1,"data view mismatch %h first_wait=%0d",selected_words,first_sample_wait);

        // An ordinary memory transaction does not consume a code-trace slot.
        cpu_valid=1; cpu_status=4'h5; tick();
        cpu_ready=1; tick();
        cpu_ready=0; cpu_valid=0; tick();
        if (capture_count != 1)
            $fatal(1,"non-code access was traced");

        // Fill and saturate without wrapping over the reset-vector record.
        for (integer index=1; index<34; index=index+1) begin
            begin_fetch(24'h0F0000+24'(index));
            complete_fetch();
        end
        select_detail=0; select_index=0; tick(); tick();
        if (!full || capture_count != 32 || selected_words !== saved_address_view)
            $fatal(1,"trace did not freeze its first 32 records");

        reset=1; tick(); reset=0; tick();
        if (capture_count != 0 || selected_valid || selected_words != 0)
            $fatal(1,"reset did not invalidate trace");
        begin_fetch(24'hFFFFF0);
        reset=1; tick(); reset=0; cpu_valid=0; tick();
        if (capture_count != 0 || capture_pending)
            $fatal(1,"reset did not discard partial request");
        $display("AT_BOOT_TRACE_PASS entries=32 first_address=fffff0 kf_word=07fff8 cpu_data=12ea");
        $finish;
    end
endmodule
