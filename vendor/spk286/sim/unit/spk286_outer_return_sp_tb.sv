`timescale 1ns/1ps

module spk286_outer_return_sp_tb;
    `include "spk286_signals.svh"
    logic [7:0] memory [0:262143];
    integer cycles = 0, cases = 0, checks = 0, failures = 0;
    integer outer_writes = 0;
    spk286 dut (.*);

    task automatic tick;
        begin
            #1;
            ready = bus_valid && ((cycles % 4) != 1);
            data_in = 0;
            if (bus_valid && !bus_write) begin
                if (address[0]) data_in = {memory[address[17:0]], 8'h00};
                else if (bus_bhe_n) data_in = {8'h00, memory[address[17:0]]};
                else data_in = {memory[address[17:0]+18'd1], memory[address[17:0]]};
            end
            if (bus_valid && ready && bus_write && bus_status == 4'h6) begin
                if (address >= 24'h020000 && address <= 24'h02FFFF) outer_writes = outer_writes + 1;
                if (address[0]) memory[address[17:0]] = data_out[15:8];
                else begin
                    memory[address[17:0]] = data_out[7:0];
                    if (!bus_bhe_n) memory[address[17:0]+18'd1] = data_out[15:8];
                end
            end
            #4; clk = 1'b1; #5; clk = 1'b0; #1;
            cycles = cycles + 1;
        end
    endtask
    task automatic word_put(input integer addr, input logic [15:0] value);
        memory[addr] = value[7:0]; memory[addr+1] = value[15:8];
    endtask
    function automatic logic [15:0] word_at(input integer addr);
        word_at = {memory[addr+1], memory[addr]};
    endfunction
    task automatic cache(input integer addr, input logic [23:0] base_addr,
                         input logic [15:0] limit_value, input logic [7:0] access_byte);
        word_put(addr, base_addr[15:0]); word_put(addr+2, {access_byte, base_addr[23:16]});
        word_put(addr+4, limit_value);
    endtask
    task automatic descriptor(input integer addr, input logic [23:0] base_addr,
                              input logic [15:0] limit_value, input logic [7:0] access_byte);
        word_put(addr, limit_value); word_put(addr+2, base_addr[15:0]);
        word_put(addr+4, {access_byte, base_addr[23:16]}); word_put(addr+6, 0);
    endtask
    task automatic check(input logic condition, input string message);
        checks = checks + 1;
        if (condition !== 1'b1) begin
            failures = failures + 1;
            $display("OUTER_RETURN_SP FAIL: %s CS:IP=%h:%h SS:SP=%h:%h event=%h:%h",
                     message, debug_cs, debug_ip, debug_segment_selectors[47:32], debug_gpr[79:64],
                     debug_event_vector, debug_event_error_code);
        end
    endtask

    task automatic run_case(input integer form, input logic expand_down,
                            input integer boundary, input integer bad_ss,
                            input logic [1:0] policy);
        integer deadline, frame_sp_pos;
        logic [15:0] final_sp, saved_sp, push_offset, stack_limit, selector;
        logic [7:0] access_byte;
        logic push_valid;
        string label;
        begin
            reset = 1'b1; execute_enable = 1'b0; timing_policy_request = policy;
            repeat (4) tick();
            for (integer i = 0; i < 262144; i = i + 1) memory[i] = 0;
            outer_writes = 0;
            stack_limit = expand_down ? 16'hF7FF : 16'h07FF;
            case (boundary)
                0: final_sp = expand_down ? 16'h0000 : 16'h0800; // Empty stack, including OS/2.
                1: final_sp = expand_down ? 16'hF804 : 16'h07FE;
                2: final_sp = expand_down ? 16'hF7FE : 16'h0900;
                3: final_sp = expand_down ? 16'hFFFF : 16'h0000;
                4: final_sp = 16'h0002;
                5: final_sp = 16'hFFFE;
                default: final_sp = 16'h0001;
            endcase
            saved_sp = final_sp - (form == 1 ? 16'd4 : 16'd0);
            push_offset = final_sp - 16'd2;
            push_valid = expand_down ? (push_offset > stack_limit && push_offset != 16'hFFFF) :
                                      ({1'b0, push_offset} + 17'd1 <= {1'b0, stack_limit});
            selector = bad_ss == 4 ? 16'h0000 : 16'h0067;
            access_byte = bad_ss == 1 ? 8'h73 : bad_ss == 2 ? 8'h93 : bad_ss == 3 ? 8'hFB :
                          expand_down ? 8'hF7 : 8'hF3;
            label = $sformatf("form=%0d ED=%0d boundary=%0d badSS=%0d policy=%0d",
                              form, expand_down, boundary, bad_ss, policy);

            // Reproduce OS/2's CPL0 -> CPL3 RETF and LDT stack selector.
            // The hidden caches are initialized by LOADALL; no new-stack
            // memory access is needed to restore SS:SP.
            memory[0] = 8'h0F; memory[1] = 8'h05;
            word_put('h806, 16'h0001); word_put('h818, 16'h0246);
            word_put('h81A, 16'h0985); word_put('h81C, 16'h0028);
            word_put('h81E, 16'h0BF0); word_put('h820, 16'h0038);
            word_put('h822, 16'h0270); word_put('h824, 16'h0210);
            word_put('h82C, 16'hF8F2);
            cache('h836, 24'h000000, 16'h207F, 8'h93);
            cache('h83C, 24'h010000, 16'h819E, 8'h9B);
            cache('h842, 24'h000000, 16'hF4DF, 8'h97);
            cache('h848, 24'h000000, 16'h638F, 8'hF3);
            cache('h84E, 24'h002000, 16'h1AFF, 8'h00);
            cache('h854, 24'h004000, 16'h009F, 8'h82);
            cache('h85A, 24'h005000, 16'h03FF, 8'h00);
            cache('h860, 24'h000000, 16'h0000, 8'h00);
            descriptor('h33A0, 24'h010000, 16'h819E, 8'hFB);
            descriptor('h4060, 24'h020000, stack_limit, access_byte);
            memory['h10985] = form == 0 ? 8'hCB : form == 1 ? 8'hCA : 8'hCF;
            word_put('h10986, 16'h0004);
            word_put('hF8F2, 16'h32D0); word_put('hF8F4, 16'h13A3);
            if (form == 2) word_put('hF8F6, 16'h0246);
            frame_sp_pos = 'hF8F6 + (form == 1 ? 4 : form == 2 ? 2 : 0);
            word_put(frame_sp_pos, saved_sp); word_put(frame_sp_pos+2, selector);
            memory['h132D0] = 8'hB8; word_put('h132D1, 16'hBEEF);
            memory['h132D3] = 8'h50; // PUSH AX: actual access checks the restored stack.
            memory['h132D4] = 8'h59; // POP CX
            memory['h132D5] = 8'hB8; word_put('h132D6, 16'hCAFE);
            memory['h132D8] = 8'hEB; memory['h132D9] = 8'hFE;
            reset = 1'b0; segment_load_en = 1'b1; segment_load_index = 2'd1;
            segment_load_selector = 0; ip_write_en = 1'b1; ip_write_data = 0; redirect = 1'b1;
            tick(); segment_load_en = 1'b0; ip_write_en = 1'b0; redirect = 1'b0; execute_enable = 1'b1;
            deadline = 0;
            while (!shutdown && debug_timing_event_requests == 0 && debug_gpr[15:0] != 16'hBEEF && deadline < 2500) begin
                tick(); deadline = deadline + 1;
            end
            if (bad_ss != 0) begin
                check(debug_timing_event_requests == 1 && debug_event_vector == (bad_ss == 1 ? 8'd12 : 8'd13) &&
                      debug_event_error_code == (bad_ss == 4 ? 16'h0000 : 16'h0064),
                      {label, " invalid SS descriptor still rejects the return"});
                check(debug_cs == 16'h0270 && debug_segment_selectors[47:32] == 16'h0038 &&
                      debug_gpr[79:64] == 16'hF8F2 && outer_writes == 0,
                      {label, " descriptor fault preserves original context"});
            end else begin
                check(!shutdown && debug_timing_event_requests == 0 && debug_gpr[15:0] == 16'hBEEF &&
                      debug_cs == 16'h13A3 && debug_segment_selectors[47:32] == 16'h0067 &&
                      debug_gpr[79:64] == final_sp && debug_flags == 16'h0246,
                      {label, " return restores SP without dereferencing it"});
                check(outer_writes == 0 && word_at('hF8F2) == 16'h32D0 &&
                      word_at('hF8F4) == 16'h13A3 && word_at(frame_sp_pos) == saved_sp &&
                      word_at(frame_sp_pos+2) == selector,
                      {label, " return does not write the restored stack or source frame"});
                if (debug_timing_event_requests == 0) begin
                    deadline = 0;
                    while (!shutdown && debug_timing_event_requests == 0 && debug_gpr[15:0] != 16'hCAFE && deadline < 1200) begin
                        tick(); deadline = deadline + 1;
                    end
                    if (push_valid)
                        check(debug_timing_event_requests == 0 && debug_gpr[15:0] == 16'hCAFE &&
                              debug_gpr[31:16] == 16'hBEEF && debug_gpr[79:64] == final_sp &&
                              word_at('h20000 + int'(push_offset)) == 16'hBEEF && outer_writes > 0,
                              {label, " subsequent valid PUSH/POP uses the restored stack"});
                    else
                        check(debug_timing_event_requests == 1 && debug_event_vector == 8'd12 &&
                              debug_event_error_code == 0 && debug_instruction_ip == 16'h32D3 &&
                              debug_cs == 16'h13A3 && debug_gpr[79:64] == final_sp && outer_writes == 0,
                              {label, " subsequent invalid PUSH raises #SS(0), not RETF"});
                end
            end
            cases = cases + 1;
        end
    endtask

    initial begin
        for (integer policy = 0; policy < 3; policy = policy + 1)
            for (integer form = 0; form < 3; form = form + 1) begin
                for (integer ed = 0; ed < 2; ed = ed + 1)
                    for (integer boundary = 0; boundary < 7; boundary = boundary + 1)
                        run_case(form, 1'(ed), boundary, 0, 2'(policy));
                for (integer bad_ss = 1; bad_ss < 5; bad_ss = bad_ss + 1)
                    run_case(form, 0, 0, bad_ss, 2'(policy));
            end
        if (failures != 0) $fatal(1, "OUTER_RETURN_SP: %0d failures / %0d cases", failures, cases);
        $display("OUTER_RETURN_SP PASS: %0d checks / %0d cases", checks, cases);
        $finish;
    end
endmodule
