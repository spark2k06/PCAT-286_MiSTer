`timescale 1ns/1ps
module p06_core_iu_baseline_tb #(parameter bit OVERLAP = 1'b0);
    `include "spk286_signals.svh"
    spk286 #(.P06_REGISTER_PILOT(1'b1), .P06_FETCH_PILOT(1'b1), .P06_IU_PILOT(OVERLAP)) dut (.*);
    logic [7:0] memory [0:4095];
    logic [127:0] initial_gpr, expected_gpr [0:15], committed_gpr;
    logic [15:0] initial_flags, expected_flags [0:15], committed_flags;
    logic [31:0] codes [0:15];
    integer forms [0:15], lengths [0:15], ips [0:15], starts [0:15];
    integer vector_fd, trace_fd, summary_fd, scan, id, count, start_ip, ready_mode;
    integer cycle, fabric_age = 0, cpu_clocks = 0, started, completed, overlaps, transfers;
    integer mode = 0, cases = 0, total_overlaps = 0, reserved_bytes;
    bit warming = 0, warm = 1, aborted = 0, action_done = 0;
    string vectors_path, trace_path, summary_path;

    task automatic tick;
        bit boundary, start_event, commit_event, consume_event, relaunch;
        integer retiring, starting, gap, elapsed;
        begin
            #9;
            data_in = 16'hBAD0;
            if (ready && bus_valid && address < 4096)
                data_in = {memory[{address[11:1],1'b1}], memory[{address[11:1],1'b0}]};
            boundary = !reset && (3*(fabric_age+1)/25 != 3*fabric_age/25);
            if (dut.p06_register.cpu_boundary !== boundary) $fatal(1,"rational clock mismatch");
            if (reset) begin fabric_age = 0; cpu_clocks = 0; end
            else begin fabric_age++; if (boundary) cpu_clocks++; end
            start_event = dut.opcode_start;
            commit_event = (dut.effective_gpr_write_en || dut.effective_flags_write_en) && dut.commit_allowed;
            consume_event = dut.queue_consume_valid && dut.queue_consume_ready;
            relaunch = dut.p06_relaunch;
            retiring = completed; starting = started;
            if (execute_enable) begin
                cycle++;
                if (commit_event && (retiring >= started || retiring >= count || !boundary ||
                    !dut.operation_retire || !dut.p06_result_pending ||
                    cpu_clocks-starts[retiring] < (forms[retiring] < 3 ? 2 : 3)))
                    $fatal(1,"commit before old qualified deadline id=%0d",id);
                if (start_event) begin
                    if (!boundary || starting > count || (starting == count && mode != 9) ||
                        dut.p06_cursor_ip != 16'(ips[starting]))
                        $fatal(1,"new instruction started at wrong boundary/IP id=%0d",id);
                    starts[starting] = cpu_clocks; started++;
                end
                if (relaunch && (!OVERLAP || !start_event || !commit_event || !consume_event))
                    $fatal(1,"relaunch lacks old commit/new byte acceptance");
                if (ready && bus_valid) begin
                    transfers++;
                    if (bus_write || bus_status != 4'hD) $fatal(1,"untimed non-CODE bus access");
                end
            end
            #1; clk = 1; #10; clk = 0;
            if (execute_enable) begin
                reserved_bytes = (dut.fetch.p06_historical.state_q == 1 || dut.fetch.p06_historical.state_q == 2) ?
                    int'(dut.fetch.request_count_q) : (dut.fetch.raw_response_valid ? int'(dut.fetch.raw_response_count) : 0);
                if (int'(debug_prefetch_count)+reserved_bytes > 6) $fatal(1,"prefetch reservation overflow");
                if (instruction_retired) begin
                    if (!commit_event || !boundary || completed != retiring)
                        $fatal(1,"retirement without old commit");
                    if (debug_gpr !== expected_gpr[retiring] || debug_flags !== expected_flags[retiring] ||
                        debug_ip != 16'(ips[retiring]+lengths[retiring]))
                        $fatal(1,"stream architectural mismatch id=%0d instruction=%0d gpr=%h/%h flags=%h/%h ip=%h",id,retiring,
                            debug_gpr,expected_gpr[retiring],debug_flags,expected_flags[retiring],debug_ip);
                    if (relaunch && (!debug_micro_active || !dut.context_active || dut.instruction_bytes != 1 ||
                        dut.p06_result_pending || debug_instruction_ip != 16'(ips[starting])))
                        $fatal(1,"new lifetime did not replace old context/operands/IP");
                    committed_gpr = expected_gpr[retiring]; committed_flags = expected_flags[retiring];
                    elapsed = cpu_clocks-starts[retiring];
                    gap = retiring == 0 ? -1 : starts[retiring]-starts[retiring-1];
                    $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h\n",
                        id,retiring,forms[retiring],starts[retiring],cpu_clocks,elapsed,gap,relaunch,mode,debug_gpr,debug_flags);
                    completed++; if (relaunch) begin overlaps++; total_overlaps++; end
                end else if (commit_event) $fatal(1,"commit without retirement");
                if (!reset && !ip_write_en && !segment_load_en && !gpr_write_en && !flags_write_en &&
                    (debug_gpr !== committed_gpr || debug_flags !== committed_flags))
                    $fatal(1,"state changed outside qualified commit");
                if (microcode_fault || unsupported_opcode || shutdown ||
                    (control_error && !warming && mode != 2)) $fatal(1,"unexpected CPU fault id=%0d",id);
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%04h,%04h,%04h,%032h,%04h,%0d,%06h,%0d,%0d,%0d\n",
                    id,cycle,boundary,cpu_clocks,start_event,commit_event,relaunch,started,completed,
                    debug_ip,dut.p06_cursor_ip,debug_instruction_ip,debug_gpr,debug_flags,bus_valid,address,
                    ready,debug_prefetch_count,dut.p06_register.scope_error);
            end
        end
    endtask

    task automatic setup;
        integer cursor;
        begin
            execute_enable = 0; reset = 1; ready = 0; intr = 0; nmi = 0;
            redirect = 0; ip_write_en = 0; segment_load_en = 0;
            gpr_write_en = 0; flags_write_en = 0; tick(); reset = 0;
            for (integer i = 0; i < 4096; i++) memory[i] = 8'hF4;
            cursor = start_ip;
            for (integer j = 0; j < count; j++) begin
                ips[j] = cursor;
                for (integer b = 0; b < lengths[j]; b++) memory[cursor+b] = codes[j][b*8+:8];
                cursor += lengths[j]; starts[j] = -1;
            end
            ips[count] = cursor;
            if (mode == 8) memory[cursor] = 8'hF3;
            if (mode == 9) begin memory[cursor] = 8'h01; memory[cursor+1] = 8'h00; end
            for (integer r = 0; r < 8; r++) begin
                gpr_write_en = 1; gpr_write_index = 3'(r); gpr_write_data = initial_gpr[r*16+:16]; tick();
            end
            gpr_write_en = 0; flags_write_en = 1; flags_write_data = initial_flags; flags_write_mask = 16'hFFFF;
            tick(); flags_write_en = 0;
            segment_load_en = 1; segment_load_index = 1; segment_load_selector = 0;
            redirect = 1; ip_write_en = 1; ip_write_data = 16'(start_ip); tick();
            segment_load_en = 0; redirect = 0; ip_write_en = 0;
            cycle = 0; started = 0; completed = 0; overlaps = 0; transfers = 0; action_done = 0; aborted = 0;
            committed_gpr = initial_gpr; committed_flags = initial_flags;
            execute_enable = 1; ready = 1;
            if (warm) begin
                warming = 1; redirect = 1;
                while ((debug_prefetch_count < 5 || bus_valid || dut.fetch.raw_response_valid) && cycle < 300) tick();
                if (started != 0 || debug_prefetch_count < 5) $fatal(1,"warm prefill failed");
                warming = 0; redirect = 0; cycle = 0;
            end
        end
    endtask

    task automatic lifecycle;
        begin
            action_done = 1;
            if (mode == 1 || mode == 2) begin
                if (mode == 1) execute_enable = 0;
                else begin redirect = 1; ip_write_en = 0; end
                repeat (25) begin
                    tick();
                    if (instruction_retired || !dut.p06_result_pending || debug_gpr !== committed_gpr ||
                        debug_flags !== committed_flags || (mode == 2 && !control_error))
                        $fatal(1,"pause/controller error lost pending state");
                end
                execute_enable = 1; redirect = 0;
            end else if (mode == 3 || mode == 4 || mode == 14 || mode == 15) begin
                execute_enable = 0;
                if (mode == 3 || mode == 14) begin redirect = 1; ip_write_en = 1; ip_write_data = 16'h0500; end
                else reset = 1;
                tick();
                if (instruction_retired || dut.p06_result_pending || dut.p06_register.active || dut.context_active)
                    $fatal(1,"cancellation retained an old lifetime");
                if ((mode == 3 || mode == 14) && (debug_gpr !== committed_gpr || debug_flags !== committed_flags || debug_ip != 16'h0500))
                    $fatal(1,"redirect committed canceled instruction");
                reset = 0; redirect = 0; ip_write_en = 0;
                repeat (20) tick();
                if (instruction_retired) $fatal(1,"late retirement after cancellation");
                aborted = 1;
                $fwrite(summary_fd,"%0d,-1,-1,-1,-1,-1,-1,0,%0d,%032h,%04h\n",id,mode,debug_gpr,debug_flags);
            end else if (mode == 5 || mode == 11 || mode == 12) nmi = 1;
            else if (mode == 6 || mode == 13) intr = 1;
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s",vectors_path) || !$value$plusargs("trace=%s",trace_path) ||
            !$value$plusargs("summary=%s",summary_path)) $fatal(1,"required paths missing");
        if ($value$plusargs("mode=%d",mode)) begin end
        warm = !$test$plusargs("cold");
        vector_fd = $fopen(vectors_path,"r"); trace_fd = $fopen(trace_path,"w"); summary_fd = $fopen(summary_path,"w");
        $fwrite(trace_fd,"id,edge,boundary,cpu_clock,start,commit,relaunch,started,completed,ip,cursor,start_ip,gpr,flags,bus,address,ready,queue,scope\n");
        $fwrite(summary_fd,"id,instruction,form,start_clock,retire_clock,elapsed,start_delta,relaunch,mode,gpr,flags\n");
        while (!$feof(vector_fd)) begin
            scan = $fscanf(vector_fd,"%d %d %h %d %h %h\n",id,count,start_ip,ready_mode,initial_gpr,initial_flags);
            if (scan != 6 || count > 16 || count < 2) $fatal(1,"invalid stream header");
            for (integer j = 0; j < count; j++) begin
                scan = $fscanf(vector_fd,"%d %d %h %h %h\n",forms[j],lengths[j],codes[j],expected_gpr[j],expected_flags[j]);
                if (scan != 5) $fatal(1,"invalid independent oracle row");
            end
            // Event-mode vectors include IF/TF in the independent oracle.
            setup();
            while (completed < count && cycle < 2000 && !dut.p06_register.scope_error && !aborted) begin
                ready = ready_mode == 0 ? 1 : (ready_mode == 1 ? (cycle%3 != 1) : (cycle > 160));
                if (!action_done &&
                    (((mode >= 1 && mode <= 6) || mode == 13) && dut.p06_result_pending ||
                     (mode == 11 && dut.p06_register.permit && dut.p06_result_pending) ||
                     (mode == 12 && completed == 1) ||
                     ((mode == 14 || mode == 15) && completed == 1 && dut.p06_result_pending))) lifecycle();
                if (!aborted) tick();
            end
            if (mode == 5 || mode == 6 || mode == 7 || mode == 11 || mode == 12) begin
                while (!dut.p06_register.scope_error && cycle < 2000) tick();
                if (!dut.p06_register.scope_error || dut.p06_register.scope_reason != 4 ||
                    completed != (mode == 12 ? 2 : 1) || started != completed ||
                    !dut.event_active || dut.event_ip != 16'(ips[completed]) ||
                    debug_event_kind != (mode == 7 ? 3'd2 : mode == 6 ? 3'd4 : 3'd3))
                    $fatal(1,"event boundary/context mismatch id=%0d mode=%0d completed=%0d started=%0d event_ip=%h",id,mode,completed,started,dut.event_ip);
                execute_enable = 0;
                repeat (25) begin
                    tick();
                    if (debug_gpr !== committed_gpr || debug_flags !== committed_flags ||
                        (bus_valid && (bus_write || bus_status != 4'hD))) $fatal(1,"untimed event leaked work");
                end
            end else if (!aborted && completed != count)
                $fatal(1,"stream incomplete id=%0d mode=%0d started=%0d completed=%0d",id,mode,started,completed);
            if (mode == 8 || mode == 9 || mode == 10) begin
                repeat (60) tick();
                if (!dut.p06_register.scope_error || started != count+(mode == 9 ? 1 : 0) ||
                    completed != count || debug_gpr !== committed_gpr || debug_flags !== committed_flags)
                    $fatal(1,"unsupported suffix did not stop explicitly");
            end
            if (!warm || ready_mode == 2) begin end
            else if (OVERLAP && (mode == 0 || mode == 13) && count == 2 && forms[0] < 3 && forms[1] < 3 && overlaps != 1)
                $fatal(1,"warm RR handoff retained a needless dispatch gap");
            execute_enable = 0; cases++;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_IU_PASS cases=%0d overlaps=%0d mode=%0d",cases,total_overlaps,mode); $finish;
    end
endmodule
