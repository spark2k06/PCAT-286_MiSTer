`timescale 1ns/1ps

// Intel 80286 PRM 10.2.2, tables 10-1/10-2 and #NM B-2:
// ESC traps on EM || TS; WAIT traps on MP && TS, independent of PE/CPL.
// BUSY is inactive in the standalone no-NPX profile. No 80287 is modeled.
module spk286_npx_traps_tb;
    `include "spk286_signals.svh"
    spk286 dut (.*);
    logic [7:0] memory [0:65535];
    integer checks = 0, cases = 0, cycles = 0;
    integer events_seen, subject_retired, subject_reads, subject_writes, io_cycles;
    integer frame_writes;
    logic observe = 0, first_fault = 0;
    logic [15:0] fault_ip, fault_stream_ip, fault_flags, fault_cs, fault_sp;
    logic [127:0] fault_gpr;
    logic [63:0] fault_selectors;
    logic [7:0] first_vector;
    logic first_error_valid;
    logic [15:0] first_error;
    logic [15:0] caller_cs, caller_ss;
    logic [127:0] original_gpr;
    logic [63:0] original_selectors;
    logic [15:0] original_flags = 16'h0046;

    task automatic check(input logic condition, input string message);
        checks++;
        if (condition !== 1'b1)
            $fatal(1,"NPX_TRAPS %s case=%0d CS:IP=%h:%h MSW=%h opcode=%h event=%h/%h micro=%h",
                   message,cases,debug_cs,debug_ip,debug_protected_msw,debug_opcode,
                   debug_event_vector,debug_event_error_code,debug_micro_pc);
    endtask
    task automatic word_at(input integer addr, input logic [15:0] value);
        memory[addr] = value[7:0]; memory[addr+1] = value[15:8];
    endtask
    function automatic logic [15:0] read_word(input integer addr);
        return {memory[addr+1],memory[addr]};
    endfunction
    task automatic cache_at(input integer addr, input logic [23:0] base_addr,
                            input logic [7:0] access_byte, input logic [15:0] limit);
        word_at(addr,base_addr[15:0]); word_at(addr+2,{access_byte,base_addr[23:16]});
        word_at(addr+4,limit);
    endtask
    task automatic descriptor_at(input integer addr, input logic [7:0] access_byte);
        word_at(addr,16'hFFFF); word_at(addr+2,0);
        word_at(addr+4,{access_byte,8'd0}); word_at(addr+6,0);
    endtask
    task automatic tick;
        #1;
        ready = bus_valid && ((cycles % 5) != 1) && ((cycles % 5) != 2);
        data_in = 0;
        if (bus_valid && !bus_write) begin
            if (address[0]) data_in = {memory[address[15:0]],8'd0};
            else if (bus_bhe_n) data_in = {8'd0,memory[address[15:0]]};
            else data_in = {memory[address[15:0]+16'd1],memory[address[15:0]]};
        end
        if (observe && !reset) begin
            if (dut.fault_request && !first_fault) begin
                first_fault = 1;
                first_vector = debug_fault_vector; first_error = debug_fault_error_code;
                first_error_valid = dut.fault_error_valid;
                fault_ip = debug_instruction_ip; fault_flags = debug_flags;
                fault_stream_ip = debug_ip;
                fault_cs = debug_cs; fault_sp = debug_gpr[79:64];
                fault_gpr = debug_gpr; fault_selectors = debug_segment_selectors;
            end
            if (bus_valid && ready && (bus_status == 4'h9 || bus_status == 4'hA)) io_cycles++;
            if (bus_valid && ready && (bus_status == 4'h5 || bus_status == 4'h6)) begin
                if (debug_instruction_ip == 16'h0100 && !dut.event_active) begin
                    if (bus_write) subject_writes++; else subject_reads++;
                end
                if (bus_write && dut.event_active) frame_writes++;
            end
        end
        if (bus_valid && ready && bus_write && bus_status == 4'h6) begin
            if (address[0]) memory[address[15:0]] = data_out[15:8];
            else begin
                memory[address[15:0]] = data_out[7:0];
                if (!bus_bhe_n) memory[address[15:0]+16'd1] = data_out[15:8];
            end
        end
        #4; clk = 1; #5; clk = 0; #1;
        cycles++;
        if (observe) begin
            if (event_completed) events_seen++;
            if (instruction_retired) begin
                if (debug_instruction_ip == 16'h0100) subject_retired++;
            end
        end
    endtask

    // All fixture state enters through executable LOADALL, not force/release.
    // Protected #NM delivery uses a real same-level IDT gate and descriptor.
    task automatic setup(input logic pe, input logic [1:0] cpl,
                         input logic [2:0] control_bits,
                         input logic [7:0] op, input integer form,
                         input integer prefix_kind, input logic [1:0] policy,
                         output integer length);
        integer pos;
        logic [15:0] msw;
        reset = 1; execute_enable = 0; observe = 0;
        timing_policy_request = policy;
        intr = 0; nmi = 0; hold_request = 0;
        segment_load_en = 0; redirect = 0; ip_write_en = 0;
        repeat (4) tick();
        for (integer i = 'h800; i < 'h866; i++) memory[i] = 0;
        for (integer i = 'h100; i < 'h140; i++) memory[i] = 8'h90;
        caller_cs = pe ? (16'h0018 | {14'd0,cpl}) : 16'd0;
        caller_ss = pe ? (16'h0020 | {14'd0,cpl}) : 16'd0;
        msw = {12'd0,control_bits,pe};
        memory[0] = 8'h0F; memory[1] = 8'h05;
        word_at('h806,msw); word_at('h818,original_flags); word_at('h81A,'h100);
        word_at('h81E,caller_ss); word_at('h820,caller_ss);
        word_at('h822,caller_cs); word_at('h824,caller_ss);
        for (integer reg_index = 0; reg_index < 8; reg_index++)
            word_at('h826+2*reg_index,16'h6000+16'(reg_index));
        word_at('h82C,'h2000); // SP
        cache_at('h836,0,8'h93 | {1'b0,cpl,5'd0},'hFFFF);
        cache_at('h83C,0,8'h9B | {1'b0,cpl,5'd0},'hFFFF);
        cache_at('h842,0,8'h93 | {1'b0,cpl,5'd0},'hFFFF);
        cache_at('h848,0,8'h93 | {1'b0,cpl,5'd0},'hFFFF);
        cache_at('h84E,'h1000,0,'h0027); // GDTR
        cache_at('h85A,pe ? 24'h001400 : 24'd0,0,'h003F); // IDTR
        descriptor_at('h1018,8'h9B | {1'b0,cpl,5'd0});
        descriptor_at('h1020,8'h93 | {1'b0,cpl,5'd0});
        word_at('h1438,'h0300); word_at('h143A,caller_cs);
        word_at('h143C,'h8600); word_at('h143E,0);
        word_at('h001C,'h0300); word_at('h001E,0); // Real vector 7.
        memory['h300] = 8'h90;
        pos = 'h100;
        if (prefix_kind == 1) begin memory[pos] = 8'h2E; pos++; end
        if (prefix_kind == 2) begin
            memory[pos] = 8'hF3; memory[pos+1] = 8'h36; pos += 2;
        end
        memory[pos] = op; pos++;
        if (op != 8'h9B) begin
            case (form)
                0: begin memory[pos] = 8'hC0; pos++; end
                // Invalid word boundary stresses #NM priority only when EM/TS
                // demands #NM. Successful no-NPX syntax uses a valid pointer;
                // residual ESC boundary checking is tracked separately in H19.
                1: begin memory[pos] = 8'h06;
                    word_at(pos+1,(control_bits[2] || control_bits[1]) ? 'hFFFF : 'h4000);
                    pos += 3; end
                2: begin memory[pos] = 8'h46; memory[pos+1] = 8'h7F; pos += 2; end
                3: begin memory[pos] = 8'h06; word_at(pos+1,'h4000); pos += 3; end
            endcase
        end
        length = pos-'h100;
        memory[pos] = 8'hB8; word_at(pos+1,'hBEEF);
        for (integer i = 'h1FE0; i < 'h2000; i++) memory[i] = 8'hA5;
        events_seen = 0; subject_retired = 0; subject_reads = 0; subject_writes = 0;
        io_cycles = 0; frame_writes = 0; first_fault = 0;
        first_vector = 0; first_error = 0; first_error_valid = 0;
        reset = 0; segment_load_en = 1; segment_load_index = 1;
        segment_load_selector = 0; ip_write_en = 1; ip_write_data = 0; redirect = 1;
        tick(); segment_load_en = 0; ip_write_en = 0; redirect = 0; execute_enable = 1;
        begin : fixture_load
            integer deadline;
            deadline = 0;
            while (!(instruction_retired && debug_ip == 'h100) && deadline < 1500) begin
                tick(); deadline++;
            end
            check(deadline < 1500 && debug_protected_msw[3:0] == msw[3:0],"LOADALL fixture is complete");
        end
        original_gpr = debug_gpr; original_selectors = debug_segment_selectors;
        check(debug_timing_policy == (policy == 1 ? 0 : policy) &&
              debug_timing_policy_error == (policy == 1),
              "baseline/Max accepted; unsupported request 1 falls back to baseline with diagnostic");
        observe = 1;
    endtask

    task automatic run_case(input logic pe, input logic [1:0] cpl,
                            input logic [2:0] bits, input logic [7:0] op,
                            input integer form, input integer prefix_kind,
                            input logic [1:0] policy);
        integer deadline, length;
        logic expected_fault;
        string label;
        expected_fault = op == 8'h9B ? bits[2] && bits[0] : bits[2] || bits[1];
        label = $sformatf("PE=%b CPL=%d TS/EM/MP=%b opcode=%h form=%d prefix=%d policy=%d",
                          pe,cpl,bits,op,form,prefix_kind,policy);
        setup(pe,cpl,bits,op,form,prefix_kind,policy,length);
        deadline = 0;
        while (!event_completed && subject_retired == 0 && !unsupported_opcode &&
               !shutdown && deadline < 1200) begin tick(); deadline++; end
        check(!unsupported_opcode && !microcode_fault && !shutdown && deadline < 1200,
              {label," instruction completes or delivers #NM"});
        check(subject_reads == 0 && subject_writes == 0 && io_cycles == 0,
              {label," subject performs no operand or port access"});
        if (expected_fault) begin
            check(first_fault && first_vector == 7 && !first_error_valid &&
                  events_seen == 1 && debug_event_kind == 1 &&
                  debug_event_vector == 7 && !debug_event_error_valid,
                  {label," #NM has no error word"});
            check(subject_retired == 0 && fault_ip == 'h100 && fault_cs == caller_cs &&
                  fault_sp == 'h2000 && fault_flags == original_flags &&
                  fault_gpr == original_gpr && fault_selectors == original_selectors &&
                  fault_stream_ip == 16'('h101+prefix_kind),
                  {label," fault preserves source state and first prefix IP"});
            check(debug_cs == caller_cs && debug_ip == 'h300 && debug_gpr == original_gpr -
                  (128'h6 << 64) && debug_gpr[79:64] == 'h1FFA && frame_writes == 3 &&
                  read_word('h1FFA) == 'h100 && read_word('h1FFC) == caller_cs &&
                  read_word('h1FFE) == original_flags && read_word('h1FF8) == 'hA5A5,
                  {label," real handler frame contains only IP/CS/FLAGS"});
        end else begin
            check(!first_fault && events_seen == 0 && subject_retired == 1 &&
                  debug_ip == 16'('h100+length) && debug_gpr == original_gpr &&
                  debug_flags == original_flags && debug_segment_selectors == original_selectors,
                  {label," no-NPX instruction retires once with exact length and unchanged state"});
        end
        execute_enable = 0; observe = 0; cases++;
        if (cases % 1000 == 0) $display("NPX_TRAPS progress: %0d cases",cases);
    endtask

    task automatic recovery(input logic pe, input logic [7:0] op, input logic emulate,
                            input integer prefix_kind, input logic [1:0] policy);
        integer deadline, length;
        // Retry must target a valid memory pointer after CLTS clears TS.
        // Invalid-pointer priority is exercised separately by the truth matrix.
        setup(pe,0,emulate ? 3'b010 : (op == 8'h9B ? 3'b101 : 3'b100),op,3,prefix_kind,policy,length);
        if (emulate) begin
            // MOV BP,SP; ADD word [BP],instruction_length; IRET.
            // Only the saved IP is changed, as an emulation handler would do.
            memory['h300] = 8'h89; memory['h301] = 8'hE5;
            memory['h302] = 8'h83; memory['h303] = 8'h46;
            memory['h304] = 0; memory['h305] = 8'(length); memory['h306] = 8'hCF;
        end else begin
            memory['h300] = 8'h0F; memory['h301] = 8'h06; memory['h302] = 8'hCF;
        end
        deadline = 0;
        while (!(instruction_retired && debug_gpr[15:0] == 'hBEEF) &&
               !shutdown && !unsupported_opcode && deadline < 2000) begin tick(); deadline++; end
        check(deadline < 2000 && !shutdown && !unsupported_opcode && !microcode_fault &&
              events_seen == 1 && first_fault && first_vector == 7 && !first_error_valid,
              "recovery uses one #NM and reaches the follow-on instruction");
        check(subject_reads == 0 && subject_writes == 0 && io_cycles == 0 &&
              fault_ip == 'h100 && fault_gpr == original_gpr && fault_flags == original_flags,
              "recovery fault is restartable and does not access an operand");
        check(debug_gpr[79:64] == 'h2000 && debug_flags == original_flags &&
              debug_ip == 16'('h100+length+3) &&
              subject_retired == (emulate ? 0 : 1),
              "CLTS retries once; emulation advances the saved IP instead");
        check(debug_protected_msw[3:0] == (emulate ? (pe ? 4'h5 : 4'h4) :
              (op == 8'h9B ? (pe ? 4'h3 : 4'h2) : (pe ? 4'h1 : 4'h0))),
              "CLTS clears only TS; software emulation retains EM");
        execute_enable = 0; observe = 0; cases++;
    endtask

    task automatic pause_or_cancel(input logic pe, input logic [7:0] op,
                                   input logic cancel_subject, input logic [1:0] policy);
        integer deadline, length;
        logic [15:0] paused_ip;
        setup(pe,0,op == 8'h9B ? 3'b101 : 3'b010,op,1,2,policy,length);
        deadline = 0;
        while (!(debug_micro_active && debug_micro_instruction ==
                 (op == 8'h9B ? spk286_microcode_pkg::MC_CHECK_NPX_WAIT :
                                 spk286_microcode_pkg::MC_CHECK_NPX_ESC)) && deadline < 1200) begin
            tick(); deadline++;
        end
        check(deadline < 1200 && !first_fault,"pause reaches check before a clock accepts #NM");
        paused_ip = debug_ip;
        execute_enable = 0;
        repeat (8) tick();
        check(!first_fault && !dut.fault_request && events_seen == 0 && subject_retired == 0 &&
              debug_ip == paused_ip && debug_gpr == original_gpr && debug_flags == original_flags &&
              subject_reads == 0 && subject_writes == 0 && io_cycles == 0,
              "paused check has no fault, retirement, state write or operand/port request");
        if (cancel_subject) begin
            memory['h400] = 8'hB8; word_at('h401,'hBEEF);
            redirect = 1; ip_write_en = 1; ip_write_data = 'h400;
            tick(); redirect = 0; ip_write_en = 0;
        end
        execute_enable = 1;
        deadline = 0;
        while ((cancel_subject ? !(instruction_retired && debug_gpr[15:0] == 'hBEEF) :
                                 !event_completed) && !shutdown && !unsupported_opcode && deadline < 1200) begin
            tick(); deadline++;
        end
        check(deadline < 1200 && !shutdown && !unsupported_opcode && !microcode_fault,
              "resumed/canceled check reaches its architectural destination");
        if (cancel_subject)
            check(!first_fault && events_seen == 0 && subject_retired == 0 &&
                  debug_ip == 'h403 && debug_gpr[79:64] == 'h2000 && debug_flags == original_flags,
                  "redirect cancels old #NM and reaches the new stream without stale retirement");
        else
            check(first_fault && first_vector == 7 && !first_error_valid && events_seen == 1 &&
                  fault_ip == 'h100 && subject_retired == 0 && debug_ip == 'h300 &&
                  read_word('h1FFA) == 'h100 && frame_writes == 3,
                  "resume delivers exactly one restartable #NM");
        execute_enable = 0; observe = 0; cases++;
    endtask

    initial begin
        for (integer i = 0; i < 65536; i++) memory[i] = 0;
        if ($test$plusargs("wait_baseline")) begin
            run_case(0,0,0,8'h9B,0,0,0);
        end else if ($test$plusargs("lifecycle_only")) begin
            for (integer policy = 0; policy < 3; policy++)
                for (integer pe = 0; pe < 2; pe++)
                    for (integer cancel_subject = 0; cancel_subject < 2; cancel_subject++) begin
                        pause_or_cancel(1'(pe),8'hD8,1'(cancel_subject),2'(policy));
                        pause_or_cancel(1'(pe),8'h9B,1'(cancel_subject),2'(policy));
                    end
        end else begin
            // This first case rejects the historical EM-blind ESC passthrough.
            run_case(0,0,3'b010,8'hD8,0,0,0);
            for (integer policy = 0; policy < 3; policy++)
                for (integer ctx = 0; ctx < 5; ctx++)
                    for (integer bits = 0; bits < 8; bits++)
                        for (integer prefix_kind = 0; prefix_kind < 3; prefix_kind++) begin
                            run_case(ctx != 0,2'(ctx == 0 ? 0 : ctx-1),3'(bits),8'h9B,0,prefix_kind,2'(policy));
                            for (integer op = 'hD8; op <= 'hDF; op++)
                                for (integer form = 0; form < 3; form++)
                                    run_case(ctx != 0,2'(ctx == 0 ? 0 : ctx-1),3'(bits),8'(op),form,prefix_kind,2'(policy));
                        end
            for (integer policy = 0; policy < 3; policy++)
                for (integer pe = 0; pe < 2; pe++)
                    for (integer prefix_kind = 0; prefix_kind < 3; prefix_kind++) begin
                        recovery(1'(pe),8'hD8,0,prefix_kind,2'(policy));
                        recovery(1'(pe),8'h9B,0,prefix_kind,2'(policy));
                        recovery(1'(pe),8'hDF,1,prefix_kind,2'(policy));
                    end
            for (integer policy = 0; policy < 3; policy++)
                for (integer pe = 0; pe < 2; pe++)
                    for (integer cancel_subject = 0; cancel_subject < 2; cancel_subject++) begin
                        pause_or_cancel(1'(pe),8'hD8,1'(cancel_subject),2'(policy));
                        pause_or_cancel(1'(pe),8'h9B,1'(cancel_subject),2'(policy));
                    end
        end
        $display("NPX_TRAPS PASS: %0d checks / %0d cases",checks,cases);
        $finish;
    end
endmodule
