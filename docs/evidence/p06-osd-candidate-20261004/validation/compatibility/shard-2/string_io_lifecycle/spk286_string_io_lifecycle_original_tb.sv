`timescale 1ns/1ps
module spk286_string_io_lifecycle_tb;
    `include "spk286_signals.svh"

    // PRE-edge physical command/input snapshot; POST-edge architectural state.
    // This observer cannot drive any CPU input or modify a fixture expectation.
    integer p06_observer_fd = 0, p06_observer_edge = 0;
    string p06_observer_path;
    logic [23:0] p06_pre_address;
    logic [15:0] p06_pre_data_out, p06_pre_data_in;
    logic [3:0] p06_pre_status;
    logic p06_pre_bus, p06_pre_write, p06_pre_bhe, p06_pre_lock, p06_pre_hlda;
    logic p06_pre_reset, p06_pre_execute, p06_pre_ready, p06_pre_intr, p06_pre_nmi;
    logic p06_pre_hold, p06_pre_redirect;
    // Uninitialized fixture memory has four states in Icarus and two states
    // in the other simulator. Canonicalize only the observed INPUT, never the stimulus or
    // any architectural output. Preserve every defined input bit.
    function automatic logic [15:0] p06_observed_input(input logic [15:0] value);
        for (integer bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
            p06_observed_input[bit_index] = value[bit_index] === 1'b1;
    endfunction
    function automatic logic [15:0] p06_input_unknown_mask(input logic [15:0] value);
        for (integer bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
            case (value[bit_index])
                1'b0, 1'b1: p06_input_unknown_mask[bit_index] = 1'b0;
                default: p06_input_unknown_mask[bit_index] = 1'b1;
            endcase
    endfunction
    initial begin
        if ($value$plusargs("profile_trace=%s", p06_observer_path)) begin
            p06_observer_fd = $fopen(p06_observer_path, "w");
            if (p06_observer_fd == 0) $fatal(1, "cannot open profile compatibility trace");
            $fdisplay(p06_observer_fd, "edge,reset,execute,ready,intr,nmi,hold,redirect,bus,address,status,write,bhe,dataout,datain,lock,hlda,gpr,flags,cs,csbase,ip,halted,shutdown,retired,event,eventkind,eventvector,nmi_pending,nmi_blocked,sti_shadow,unsupported,control_error,microcode_fault,operand_blocked,prefetch,micro_active,micro_pc,datain_two_state,datain_unknown_mask");
        end
    end
    always @(posedge clk) begin
        p06_observer_edge = p06_observer_edge + 1;
        p06_pre_reset = reset; p06_pre_execute = execute_enable;
        p06_pre_ready = ready; p06_pre_intr = intr; p06_pre_nmi = nmi;
        p06_pre_hold = hold_request; p06_pre_redirect = redirect;
        p06_pre_bus = bus_valid; p06_pre_address = address;
        p06_pre_status = bus_status; p06_pre_write = bus_write; p06_pre_bhe = bus_bhe_n;
        p06_pre_data_out = data_out; p06_pre_data_in = data_in;
        p06_pre_lock = bus_lock; p06_pre_hlda = hlda;
        #1;
        if (p06_observer_fd != 0)
            $fdisplay(p06_observer_fd, "%0d,%b,%b,%b,%b,%b,%b,%b,%b,%06h,%h,%b,%b,%04h,%04h,%b,%b,%032h,%04h,%04h,%06h,%04h,%b,%b,%b,%b,%0d,%0d,%b,%b,%b,%b,%b,%b,%b,%0d,%b,%03h,%04h,%04h",
                p06_observer_edge, p06_pre_reset, p06_pre_execute, p06_pre_ready,
                p06_pre_intr, p06_pre_nmi, p06_pre_hold, p06_pre_redirect,
                p06_pre_bus, p06_pre_address, p06_pre_status, p06_pre_write, p06_pre_bhe,
                p06_pre_data_out, p06_pre_data_in, p06_pre_lock, p06_pre_hlda,
                debug_gpr, debug_flags, debug_cs, debug_cs_base, debug_ip,
                halted, shutdown, instruction_retired, event_completed,
                debug_event_kind, debug_event_vector, debug_nmi_pending,
                debug_nmi_blocked, debug_sti_shadow, unsupported_opcode, control_error,
                microcode_fault, operand_blocked, debug_prefetch_count,
                debug_micro_active, debug_micro_pc,
                p06_observed_input(p06_pre_data_in), p06_input_unknown_mask(p06_pre_data_in));
    end
    final begin
        if (p06_observer_fd != 0) $fclose(p06_observer_fd);
    end

    logic [7:0] memory [0:65535];
    integer checks=0,cases=0,retired_count=0,deliveries=0,writes=0,reads=0,acks=0;
    integer timeout_count,waits=0,delay_length=0,entry_address,entry_length,next_ip;
    logic [127:0] initial_gpr,expected_gpr,saved_gpr;
    logic [63:0] expected_segments,saved_segments;
    logic [15:0] initial_flags,saved_flags,expected_flags;
    integer iteration_boundaries=0;
    integer port_requests=0,port_cycles=0,saved_requests=0,port_halves=1,expected_elements=0;
    logic port_odd,port_writing,port_word;
    logic [11:0] saved_pc;
    logic changing_input=0;
    logic [15:0] sample_word;
    // Advance stimulus only after accepted physical transfers. Both halves of
    // an odd word use the same sample; READY waits cannot consume a sample.
    function automatic logic [15:0] input_sample(input integer element);
        input_sample=16'h5AA5 ^ (16'h172D * 16'(element+1));
    endfunction
    spk286 dut (.*);
    task automatic check(input logic condition,input string message);
        checks++;
        if(condition!==1'b1)$fatal(1,"%s case=%0d CS:IP=%h:%h pc=%h SP=%h retired=%0d events=%0d writes=%0d reads=%0d",message,cases,debug_cs,debug_ip,debug_micro_pc,debug_gpr[79:64],retired_count,deliveries,writes,reads);
    endtask
    function automatic logic [15:0] word_at(input logic [15:0] offset);
        word_at={memory[offset+16'd1],memory[offset]};
    endfunction
    task automatic tick;
        #1;data_in=16'h0F0F;
        if(bus_valid && address<65536)data_in={memory[{address[15:1],1'b1}],memory[{address[15:1],1'b0}]};
        if(bus_valid && bus_status==0)data_in=16'h2323;
        if(bus_valid && bus_status==9)data_in=address[0]?16'h3400:port_odd?16'h0012:16'h1234;
        if(bus_valid && bus_status==9 && changing_input)begin
            sample_word=input_sample(port_cycles/port_halves);
            data_in=address[0]?{sample_word[7:0],8'hD3}:port_odd && port_word?{8'hC7,sample_word[15:8]}:sample_word;
        end
        #4;
        if(dut.memory_request && dut.memory_request_ready && dut.io_transfer && !reset)port_requests++;
        if(bus_valid && ready && !reset)begin
            if(bus_status==9 || bus_status==10)begin
                check(port_cycles<port_requests*port_halves,"port transaction requires one accepted logical request");
                check(bus_status==(port_writing?10:9) && bus_write==port_writing && data_oe==port_writing,"port lifetime direction and drive");
                check(address==24'h009ABC+24'(port_odd)+24'(port_halves==2?port_cycles%2:0),"port address retained through pause and odd halves");
                if(port_writing)begin
                    if(address[0])check(data_out[15:8]==8'h34,"odd output payload");
                    else begin
                        check(data_out[7:0]==(port_halves==2?8'h12:8'h34),"low output payload");
                        if(!bus_bhe_n)check(data_out[15:8]==8'h12,"high output payload");
                    end
                end
                port_cycles++;
            end
            if(bus_status==0)acks++;
            if(bus_status==5)reads++;
            if(bus_status==6)begin
                writes++;
                if(address[0])memory[address[15:0]]=data_out[15:8];
                else begin
                    memory[address[15:0]]=data_out[7:0];
                    if(!bus_bhe_n)memory[address[15:0]+16'd1]=data_out[15:8];
                end
            end
        end
        if (execute_enable && dut.repeat_stepped && !reset && !redirect) iteration_boundaries++;
        clk=1;#5;clk=0;#1;
        if(instruction_retired)retired_count++;
        if(event_completed)deliveries++;
        check(!microcode_fault && debug_prefetch_count<=6 && !shutdown,"string control and queue invariants");
    endtask
    task automatic service;
        ready=bus_valid && waits>=delay_length;
        if(bus_valid && !ready)waits++;else waits=0;
        tick();
    endtask
    task automatic expected_progress(input integer variant,input integer count);
        expected_elements=count;expected_gpr=initial_gpr;expected_gpr[31:16]=16'(3-count);
        if(variant%4>=2)expected_gpr[111:96]=16'h0400+16'(count*(1+variant%2));
        else expected_gpr[127:112]=16'h0500+16'(count*(1+variant%2));
        expected_flags=initial_flags;
    endtask
    task automatic setup(input integer variant,input logic [15:0] flags_value,input logic [15:0] sp);
        execute_enable=0;reset=1;ready=0;intr=0;nmi=0;hold_request=0;
        gpr_write_en=0;segment_load_en=0;flags_write_en=0;redirect=0;ip_write_en=0;waits=0;
        tick();reset=0;
        initial_gpr={16'h0500,16'h0400,16'h7000,sp,16'h1357,16'h9ABC,16'h0003,16'hA634};
        port_odd=variant>=4;port_writing=variant%4>=2;port_word=variant%2!=0;port_halves=port_odd && port_word?2:1;
        initial_gpr[47:32]=16'h9ABC+16'(port_odd);
        expected_segments=0;initial_flags=flags_value;
        for(integer regno=0;regno<8;regno++)begin gpr_write_en=1;gpr_write_index=3'(regno);gpr_write_data=initial_gpr[regno*16+:16];tick();end
        gpr_write_en=0;flags_write_en=1;flags_write_mask=16'hFFFF;flags_write_data=flags_value;tick();flags_write_en=0;
        segment_load_en=1;segment_load_index=1;segment_load_selector=0;
        redirect=1;ip_write_en=1;ip_write_data=16'h0100;tick();redirect=0;ip_write_en=0;segment_load_en=0;
        for(integer i=256;i<280;i++)memory[i]=8'h0F;
        for(integer i=8160;i<8210;i++)memory[i]=8'hA5;
        for(integer i=1024;i<1050;i++)memory[i]=variant%2==1 && i%2==1?8'h12:8'h34;
        for(integer i=1280;i<1306;i++)memory[i]=8'hA5;
        memory[256]=8'hF3;memory[257]=8'h3E;
        memory[258]=8'(108+variant%4);
        memory[259]=8'hF4;
        memory[2048]=8'hF7;memory[2049]=8'hD0;memory[2050]=8'hF4;
        for(integer v=0;v<14;v++)begin memory[v*4]=0;memory[v*4+1]=6;memory[v*4+2]=8'h40;memory[v*4+3]=0;end
        memory[140]=0;memory[141]=6;memory[142]=8'h40;memory[143]=0;memory[2560]=8'hCF;memory[2561]=8'hF4;
        entry_length=9; // Port capture, privilege check, then the iteration loop.
        case(variant%4)
            0:entry_address=int'(spk286_microcode_pkg::MC_ENTRY_STRING_INPUT_BYTE);
            1:entry_address=int'(spk286_microcode_pkg::MC_ENTRY_STRING_INPUT_WORD);
            2:entry_address=int'(spk286_microcode_pkg::MC_ENTRY_STRING_OUTPUT_BYTE);
            3:entry_address=int'(spk286_microcode_pkg::MC_ENTRY_STRING_OUTPUT_WORD);
        endcase
        expected_progress(variant,3);next_ip=32'h0103;
        retired_count=0;deliveries=0;writes=0;reads=0;acks=0;iteration_boundaries=0;port_requests=0;port_cycles=0;execute_enable=1;
    endtask
    task automatic reach(input integer variant,input integer step,input integer iteration);
        setup(variant,16'h08D7,16'h2000);timeout_count=0;
        while(!(debug_micro_active && int'(debug_micro_pc)==entry_address+step && (iteration==0 || iteration_boundaries==iteration)) && timeout_count<1000)begin service();timeout_count++;end
        check(timeout_count<1000 && retired_count==0 && deliveries==0,"reach string operation in initial or repeated iteration");ready=0;
    endtask
    task automatic verify_result(input integer variant);
        check(debug_ip==16'(next_ip) && debug_gpr==expected_gpr && debug_flags==expected_flags && debug_segment_selectors==expected_segments,"exact completed string state");
        check(port_requests==expected_elements && port_cycles==expected_elements*port_halves,"one irreversible port effect per completed element");
        if(variant%4<2)begin
            for(integer i=0;i<int'(expected_gpr[127:112])-1280;i++)check(memory[1280+i]==(variant%2==1 && i%2==1?8'h12:8'h34),"each completed element stored exactly once");
            check(memory[expected_gpr[127:112]]==8'hA5,"string does not write beyond final element");
        end
    endtask
    task automatic finish_normal(input integer variant,input integer retire_target,input integer delivery_target);
        timeout_count=0;
        while(retired_count<retire_target && timeout_count<1000)begin service();timeout_count++;check(!unsupported_opcode && !operand_blocked,"normal string continues through real dependencies");end
        check(retired_count==retire_target && deliveries==delivery_target,"one retirement for whole REP instruction");verify_result(variant);
    endtask
    task automatic wait_event(input integer target,input integer vector_value,input integer retired_value,input logic [15:0] frame_ip,input logic [15:0] frame_flags,input logic [15:0] sp);
        timeout_count=0;while(deliveries<target && timeout_count<1200)begin service();timeout_count++;end
        check(deliveries==target && int'(debug_event_vector)==vector_value && debug_ip==16'h0600 && debug_cs==16'h0040 && retired_count==retired_value,"iteration event identity and handler boundary");
        expected_gpr[79:64]=sp-6;
        check(debug_gpr==expected_gpr && debug_flags==(frame_flags & ~16'h0300),"iteration event preserves committed elements and remaining count");
        check(word_at(sp-6)==frame_ip && word_at(sp-4)==0 && word_at(sp-2)==frame_flags,"full unmasked REP event frame");
    endtask
    initial begin
        for(integer i=0;i<65536;i++)memory[i]=8'h0F;
        for(integer variant=0;variant<8;variant++)begin
            setup(variant,16'h08D7,16'h2000);
            for(integer iteration=0;iteration<2;iteration++)for(integer step=0;step<entry_length;step++)begin
                if(iteration==0 || (step>2 && step!=entry_length-1))begin
                delay_length=(step+variant)%3;reach(variant,step,iteration);
                saved_pc=debug_micro_pc;saved_gpr=debug_gpr;saved_segments=debug_segment_selectors;saved_flags=debug_flags;execute_enable=0;
                repeat(6)begin service();check(debug_micro_pc==saved_pc && debug_gpr==saved_gpr && debug_segment_selectors==saved_segments && debug_flags==saved_flags && retired_count==0 && deliveries==0,"pause at every string operation retains architecture");end
                execute_enable=1;finish_normal(variant,1,0);cases++;
                reach(variant,step,iteration);saved_gpr=debug_gpr;saved_segments=debug_segment_selectors;saved_flags=debug_flags;
                saved_requests=port_requests;redirect=1;ip_write_en=1;ip_write_data=16'h0800;tick();redirect=0;ip_write_en=0;
                check(!debug_micro_active && !dut.micro_executor.address_override,"cancel invalidates current string address");
                timeout_count=0;while(retired_count==0 && timeout_count<500)begin service();timeout_count++;end
                saved_gpr[15:0]=~saved_gpr[15:0];
                check(retired_count==1 && deliveries==0 && debug_ip==16'h0802 && debug_gpr==saved_gpr && debug_flags==saved_flags && debug_segment_selectors==saved_segments,"cancel preserves accepted effects and prevents late string commits");
                check(port_requests==saved_requests && port_cycles==saved_requests*port_halves,"cancel drains accepted port effects without replay");cases++;
                reach(variant,step,iteration);reset=1;ready=1;tick();
                check(!bus_valid && debug_gpr==0 && debug_flags==2 && debug_ip==16'hFFF0 && debug_cs_base==24'hFF0000 && !dut.micro_executor.address_override,"reset clears each string operation and address");
                reset=0;execute_enable=0;ready=0;tick();check(bus_valid && address==24'hFFFFF0 && bus_status==13,"native fetch resumes after string reset");cases++;
            end
            end
            for(integer event_kind=0;event_kind<3;event_kind++)begin
                delay_length=2;setup(variant,event_kind==2?16'h09D7:16'h0AD7,16'h2000);
                timeout_count=0;while(!((dut.string_request || dut.io_transfer) && bus_valid) && timeout_count<500)begin service();timeout_count++;end
                check(timeout_count<500,"event injected during element transfer");
                if(event_kind==0)nmi=1;if(event_kind==1)intr=1;
                expected_progress(variant,1);
                wait_event(1,event_kind==0?2:event_kind==1?35:1,0,16'h0100,expected_flags,16'h2000);
                check(acks==(event_kind==1?2:0),"INTR alone performs exactly two acknowledgements");
                nmi=0;intr=0;
                // A debugger can clear saved TF after inspecting the exact first
                // frame; IRET must then resume the two remaining elements once.
                if(event_kind==2)begin memory[8191]=memory[8191]&8'hFE;initial_flags=initial_flags & ~16'h0100;end
                expected_progress(variant,3);finish_normal(variant,2,1);
                check(writes==(variant%4<2?6:3) && reads==(variant%4<2?5:8),"IRET refetch does not duplicate completed memory elements");cases++;
            end
            // Every nonfinal TF frame restarts at the first prefix; the final
            // frame points past REP and only the completed macro retires.
            setup(variant,16'h09D7,16'h2000);
            for(integer element=1;element<=3;element++)begin
                expected_progress(variant,element);
                wait_event(element,1,element==3?3:element-1,element==3?16'h0103:16'h0100,expected_flags,16'h2000);
            end
            check(acks==0,"TF never acknowledges INTR");cases++;
            // Cancel a physically visible, READY-stalled port transfer. Its
            // accepted logical request must drain even after macro cancellation.
            delay_length=2;setup(variant,16'h08D7,16'h2000);
            timeout_count=0;while(!(bus_valid && (bus_status==9 || bus_status==10)) && timeout_count<500)begin service();timeout_count++;end
            check(timeout_count<500 && port_cycles==0 && port_requests==1,"reach accepted port before READY for cancellation");
            saved_requests=port_requests;saved_gpr=debug_gpr;saved_flags=debug_flags;ready=0;
            redirect=1;ip_write_en=1;ip_write_data=16'h0800;tick();redirect=0;ip_write_en=0;
            timeout_count=0;while(retired_count==0 && timeout_count<500)begin service();timeout_count++;end
            check(port_requests==saved_requests && port_cycles==saved_requests*port_halves,"cancel drains accepted port effects without replay");
            saved_gpr[15:0]=~saved_gpr[15:0];
            check(retired_count==1 && deliveries==0 && debug_ip==16'h0802 && debug_gpr==saved_gpr && debug_flags==saved_flags,"canceled in-flight I/O cannot commit a late architectural result");cases++;
            // HOLD waits for an already visible odd word to finish, then grants
            // ownership before a subsequent port request can be accepted.
            delay_length=2;setup(variant,16'h08D7,16'h2000);
            timeout_count=0;while(!(bus_valid && (bus_status==9 || bus_status==10)) && timeout_count<500)begin service();timeout_count++;end
            check(timeout_count<500 && port_cycles==0,"reach first port transfer for HOLD");hold_request=1;
            timeout_count=0;while(!hlda && timeout_count<500)begin service();timeout_count++;end
            check(hlda && port_cycles==port_halves && port_requests==1,"HOLD follows complete accepted port word");
            repeat(5)begin service();check(hlda && !bus_valid && port_cycles==port_halves,"HOLD prevents another port transfer");end
            hold_request=0;finish_normal(variant,1,0);cases++;
            // Explicit LOCK spans the complete REP including its port cycles.
            delay_length=1;setup(variant,16'h08D7,16'h2000);
            memory[256]=8'hF0;memory[257]=8'hF3;memory[258]=8'h3E;memory[259]=8'(108+variant%4);memory[260]=8'hF4;next_ip=32'h0104;
            timeout_count=0;while(!(bus_valid && (bus_status==9 || bus_status==10)) && timeout_count<500)begin service();timeout_count++;end
            check(timeout_count<500 && bus_lock,"locked first port transfer");hold_request=1;
            timeout_count=0;while(retired_count==0 && timeout_count<1000)begin check(!hlda && bus_lock,"LOCK excludes HOLD across complete repeated port instruction");service();timeout_count++;end
            check(retired_count==1,"locked repeated I/O completes despite HOLD");verify_result(variant);hold_request=0;cases++;
            // Initial zero count has no element access or comparison result.
            setup(variant,16'h08D7,16'h2000);execute_enable=0;gpr_write_en=1;gpr_write_index=1;gpr_write_data=0;tick();gpr_write_en=0;
            expected_progress(variant,0);expected_gpr[31:16]=0;execute_enable=1;finish_normal(variant,1,0);
            check(reads==0 && writes==0 && port_cycles==0 && port_requests==0,"zero count has no memory or port access");cases++;
        end
        check(cases==400,"complete string lifetime and event matrix, including the new privilege operation");
        // A constant port responder cannot detect reusing the first INS value
        // while still issuing every IOR. Exercise data changes at one port.
        changing_input=1;
        for(integer variant=0;variant<8;variant++)if(variant%4<2)begin
            for(integer backward=0;backward<2;backward++)for(integer delay=0;delay<3;delay++)begin
                delay_length=delay;
                setup(variant,16'h08D7 | (backward!=0?16'h0400:16'h0000),16'h2000);
                expected_gpr=initial_gpr;expected_gpr[31:16]=0;
                expected_gpr[127:112]=16'h0500+16'((backward!=0?-1:1)*3*(port_word?2:1));
                timeout_count=0;
                while(retired_count==0 && timeout_count<1500)begin service();timeout_count++;end
                check(retired_count==1 && deliveries==0 && port_requests==3 && port_cycles==3*port_halves,"exact count of repeated input transactions");
                check(debug_gpr==expected_gpr && debug_flags==initial_flags && debug_segment_selectors==expected_segments && debug_ip==16'h0103,"changing input preserves exact completed architectural state");
                for(integer element=0;element<3;element++)begin
                    sample_word=input_sample(element);
                    check(memory[1280+(backward!=0?-1:1)*element*(port_word?2:1)]==sample_word[7:0],"each repeated input commits its own accepted sample low byte");
                    if(port_word)check(memory[1281+(backward!=0?-1:1)*element*2]==sample_word[15:8],"each repeated input commits its own accepted sample high byte");
                end
                cases++;
            end
        end
        check(cases==424,"complete lifetime and changing input matrix");
        $display("STRING_IO_LIFECYCLE PASS: %0d pause/cancel/reset/iteration/event/resumption cases; %0d checks",cases,checks);$finish;
    end
endmodule
