`timescale 1ns/1ps
module spk286_far_lifecycle_tb;
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
    logic [15:0] initial_flags,saved_flags;
    logic [11:0] saved_pc;
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
        #4;
        if(bus_valid && ready && !reset)begin
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
        clk=1;#5;clk=0;#1;
        if(instruction_retired)retired_count++;
        if(event_completed)deliveries++;
        check(!microcode_fault && debug_prefetch_count<=6 && !shutdown,"far control and queue invariants");
    endtask
    task automatic service;
        ready=bus_valid && waits>=delay_length;
        if(bus_valid && !ready)waits++;else waits=0;
        tick();
    endtask
    task automatic setup(input integer variant,input logic [15:0] flags_value,input logic [15:0] sp);
        execute_enable=0;reset=1;ready=0;intr=0;nmi=0;hold_request=0;
        gpr_write_en=0;segment_load_en=0;flags_write_en=0;redirect=0;ip_write_en=0;waits=0;
        tick();reset=0;
        initial_gpr={16'h3344,16'h1122,16'h7000,sp,16'h1357,16'h9ABC,16'h5678,16'h1234};
        expected_gpr=initial_gpr;expected_segments=0;initial_flags=flags_value;
        for(integer r=0;r<8;r++)begin gpr_write_en=1;gpr_write_index=3'(r);gpr_write_data=initial_gpr[r*16+:16];tick();end
        gpr_write_en=0;flags_write_en=1;flags_write_mask=16'hFFFF;flags_write_data=flags_value;tick();flags_write_en=0;
        segment_load_en=1;segment_load_index=1;segment_load_selector=0;
        redirect=1;ip_write_en=1;ip_write_data=16'h0100;tick();redirect=0;ip_write_en=0;segment_load_en=0;
        for(integer i=256;i<280;i++)memory[i]=8'h0F;
        for(integer i=8160;i<8210;i++)memory[i]=8'hA5;
        memory[256]=8'hF3;memory[257]=8'h26;
        memory[258]=variant==0?8'hC4:variant==1?8'hC5:variant==2?8'h9A:variant==3?8'hEA:variant==6?8'hCB:variant==7?8'hCA:8'hFF;
        memory[259]=variant==0?8'h1E:variant==1?8'h36:variant==4?8'h1E:variant==5?8'h2E:variant==7?8'h03:8'h00;
        memory[260]=variant==2 || variant==3?8'h02:8'h00;
        memory[261]=variant==2 || variant==3?8'h30:8'h04;
        memory[262]=0;
        memory[1024]=0;memory[1025]=2;memory[1026]=8'h30;memory[1027]=0;
        memory[1280]=8'h0F;
        memory[2048]=8'hF7;memory[2049]=8'hD0;memory[2050]=8'h0F;
        memory[2816]=8'hF7;memory[2817]=8'hD0;memory[2818]=8'h0F;
        for(integer v=0;v<14;v++)begin memory[v*4]=0;memory[v*4+1]=6;memory[v*4+2]=8'h40;memory[v*4+3]=0;end
        memory[140]=0;memory[141]=6;memory[142]=8'h40;memory[143]=0;memory[2560]=8'h0F;
        next_ip=variant<2?32'h00000106:32'h00000200;
        case(variant)
            0,1:begin
                entry_address=int'(spk286_microcode_pkg::MC_ENTRY_LOAD_POINTER);entry_length=10;
                if(variant==0)begin expected_gpr[63:48]=16'h0200;expected_segments[15:0]=16'h0030;end
                else begin expected_gpr[111:96]=16'h0200;expected_segments[63:48]=16'h0030;end
            end
            2:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_CALL_FAR_IMM);entry_length=11;expected_gpr[79:64]=sp-4;end
            3:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_JMP_FAR_IMM);entry_length=4;end
            4:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_CALL_FAR_RM);entry_length=14;expected_gpr[79:64]=sp-4;end
            5:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_JMP_FAR_RM);entry_length=7;end
            6:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_RET_FAR);entry_length=5;expected_gpr[79:64]=sp+4;end
            7:begin entry_address=int'(spk286_microcode_pkg::MC_ENTRY_RET_FAR_IMM);entry_length=8;expected_gpr[79:64]=sp+7;end
            default:$fatal(1,"unknown far instruction variant");
        endcase
        if(variant>=2)expected_segments[31:16]=16'h0030;
        if(variant>=6 && sp<16'hFFFD)begin memory[sp]=0;memory[sp+16'd1]=2;memory[sp+16'd2]=8'h30;memory[sp+16'd3]=0;end
        retired_count=0;deliveries=0;writes=0;reads=0;acks=0;execute_enable=1;
    endtask
    task automatic reach(input integer variant,input integer step);
        setup(variant,16'h0CD7,16'h2000);timeout_count=0;
        while(!(debug_micro_active && int'(debug_micro_pc)==entry_address+step) && timeout_count<400)begin service();timeout_count++;end
        check(timeout_count<400 && retired_count==0 && deliveries==0,"reach every far micro-operation");ready=0;
    endtask
    task automatic finish_normal(input logic redirected);
        timeout_count=0;
        while(retired_count==0 && timeout_count<400)begin service();timeout_count++;check(!unsupported_opcode && !operand_blocked,"far or redirected instruction executable");end
        check(retired_count==1 && deliveries==0,"one retirement without spurious event");
        if(redirected)begin
            saved_gpr[15:0]=~saved_gpr[15:0];
            check(debug_ip==16'h0802 && debug_gpr==saved_gpr && debug_flags==saved_flags && debug_segment_selectors==saved_segments,"redirect preserves accepted state and discards pending far results before NOT AX");
        end else check(debug_ip==16'(next_ip) && debug_gpr==expected_gpr && debug_flags==initial_flags && debug_segment_selectors==expected_segments,"exact far result and cache preservation");
    endtask
    task automatic finish_event(input integer vector_value,input logic fault,input logic [15:0] sp,input integer saved_ip,input logic [15:0] saved_cs);
        timeout_count=0;
        while(deliveries==0 && timeout_count<900)begin service();timeout_count++;end
        check(deliveries==1 && int'(debug_event_vector)==vector_value && debug_ip==16'h0600 && debug_cs==16'h0040 && retired_count==(fault?0:1),"far event identity, handler and retirement boundary");
        saved_gpr=fault?initial_gpr:expected_gpr;saved_gpr[79:64]=sp-6;
        check(debug_gpr==saved_gpr && debug_flags==(initial_flags & ~16'h0300),"far event preserves exact GPR and FLAGS state");
        check(word_at(sp-6)==16'(saved_ip) && word_at(sp-4)==saved_cs && word_at(sp-2)==initial_flags,"full unmasked far event frame uses committed CS:IP or first prefix");
        check(acks==(vector_value==35?2:0),"only INTR requests INTA");
    endtask
    initial begin
        for(integer i=0;i<65536;i++)memory[i]=8'h0F;
        for(integer variant=0;variant<8;variant++)begin
            setup(variant,16'h0CD7,16'h2000);
            for(integer step=0;step<entry_length;step++)begin
                delay_length=(step+variant)%3;reach(variant,step);
                saved_pc=debug_micro_pc;saved_gpr=debug_gpr;saved_segments=debug_segment_selectors;saved_flags=debug_flags;execute_enable=0;
                repeat(6)begin service();check(debug_micro_pc==saved_pc && debug_gpr==saved_gpr && debug_segment_selectors==saved_segments && debug_flags==saved_flags && retired_count==0 && deliveries==0,"pause retains architectural state at every far operation");end
                execute_enable=1;finish_normal(0);cases++;
                reach(variant,step);saved_gpr=debug_gpr;saved_segments=debug_segment_selectors;saved_flags=debug_flags;
                redirect=1;ip_write_en=1;ip_write_data=16'h0800;tick();redirect=0;ip_write_en=0;
                check(!debug_micro_active && !dut.micro_executor.auxiliary_valid_q && !dut.micro_executor.allocation_valid_q && !dut.micro_executor.address_override,"redirect clears saved far target, allocation and address ownership");
                finish_normal(1);cases++;
                reach(variant,step);reset=1;ready=1;tick();
                check(!bus_valid && debug_gpr==0 && debug_flags==2 && debug_ip==16'hFFF0 && debug_cs_base==24'hFF0000 && !dut.micro_executor.auxiliary_valid_q && !dut.micro_executor.allocation_valid_q,"reset abandons every far operation");
                reset=0;execute_enable=0;ready=0;tick();check(bus_valid && address==24'hFFFFF0 && bus_status==13,"native reset fetch after far cancellation");cases++;
            end
            for(integer event_kind=0;event_kind<3;event_kind++)begin
                setup(variant,event_kind==2?16'h0DD7:16'h0ED7,16'h2000);
                timeout_count=0;while(!(debug_micro_active && int'(debug_micro_pc)==entry_address+1) && timeout_count<400)begin service();timeout_count++;end
                check(timeout_count<400,"event injected while far instruction owns its operands");
                if(event_kind==0)nmi=1;
                if(event_kind==1)intr=1;
                finish_event(event_kind==0?2:event_kind==1?35:1,0,expected_gpr[79:64],next_ip,expected_segments[31:16]);cases++;
            end
        end
        // Memory-only forms fault at ModR/M; retained tail cannot execute.
        for(integer variant=0;variant<6;variant++)if(variant<2 || variant>=4)begin
            setup(variant,16'h0CD7,16'h2001);memory[259]=variant==4?8'hD8:variant==5?8'hE8:8'hC0;
            finish_event(6,1,16'h2001,32'h00000100,0);check(reads==2 && writes==6,"invalid far register form has only exception traffic");cases++;
            for(integer offset_choice=0;offset_choice<2;offset_choice++)begin
                setup(variant,16'h0CD7,16'h2000);memory[260]=offset_choice==0?8'hFD:8'hFF;memory[261]=8'hFF;
                finish_event(13,1,16'h2000,32'h00000100,0);check(reads==2 && writes==3,"whole pointer precheck precedes either source word");cases++;
            end
        end
        for(integer variant=6;variant<8;variant++)begin
            setup(variant,16'h0CD7,16'hFFFF);
            finish_event(13,1,16'hFFFF,32'h00000100,0);check(reads==2 && writes==6,"return precheck preserves original SP before odd exception frame");cases++;
        end
        for(integer variant=2;variant<4;variant++)begin
            setup(variant,16'h0CD7,16'h2000);
            for(integer p=0;p<6;p++)memory[256+p]=8'h26;
            memory[262]=variant==2?8'h9A:8'hEA;memory[263]=0;memory[264]=2;memory[265]=8'h30;memory[266]=0;
            finish_event(13,1,16'h2000,32'h00000100,0);check(reads==2 && writes==3,"byte eleven faults before far stack or context disposition");cases++;
        end
        check(cases==247,"complete far lifecycle matrix");
        $display("FAR_LIFECYCLE PASS: %0d pause/cancel/reset/event/fault cases; %0d checks",cases,checks);$finish;
    end
endmodule
