`timescale 1ns/1ps
module p06_core_timed_fetch_tb;
    `include "spk286_signals.svh"
    spk286 #(.P06_REGISTER_PILOT(1'b1), .P06_FETCH_PILOT(1'b1), .P06_IU_PILOT(1'b1)) dut (.*);
    logic [7:0] memory [0:4095];
    logic [127:0] initial_gpr, expected_gpr;
    logic [15:0] initial_flags, expected_flags, flags_mask;
    logic [31:0] code;
    integer vector_fd, trace_fd, summary_fd, scan, id, form, length, start_ip;
    integer ready_mode, cycle, started, start_edge, capture_edge, commit_edge, retire_edge;
    integer consumes, transfers, writes, checks = 0, cases = 0, timeout_count;
    integer fabric_age = 0, cpu_clocks = 0, start_clock, retire_clock;
    integer action = 0, action_done, late_cases = 0, ready_captures = 0;
    bit warm_test = 0, warming = 0;
    integer reserved_bytes;
    bit scope_test = 0, protected_test = 0, stream_test = 0;
    integer previous_retire_clock = 0;
    string vectors_path, trace_path, summary_path;

    task automatic tick;
        bit start_event, capture_event, gpr_event, flags_event, consume_event;
        bit pending_event, boundary;
        begin
            #9;
            data_in = 16'hBAD0;
            if (ready && bus_valid && address < 4096)
                data_in = {memory[{address[11:1],1'b1}], memory[{address[11:1],1'b0}]};
            // Independent rational clock oracle: no use of the DUT accumulator.
            boundary = !reset && (3*(fabric_age+1)/25 != 3*fabric_age/25);
            start_event = dut.opcode_start;
            capture_event = dut.micro_executor.register_capture || dut.micro_executor.immediate_capture;
            gpr_event = dut.effective_gpr_write_en && dut.commit_allowed;
            flags_event = dut.effective_flags_write_en && dut.commit_allowed;
            consume_event = dut.queue_consume_valid && dut.queue_consume_ready;
            pending_event = dut.micro_executor.register_pending_q;
            if (dut.p06_register.cpu_boundary !== boundary)
                $fatal(1, "virtual boundary differs from rational oracle");
            if (reset) begin fabric_age = 0; cpu_clocks = 0; end
            else begin fabric_age = fabric_age + 1; if (boundary) cpu_clocks = cpu_clocks + 1; end
            if (execute_enable) begin
                cycle = cycle + 1;
                if (start_event) begin
                    if (!boundary) $fatal(1, "instruction started outside virtual boundary");
                    started = started + 1; start_edge = cycle; start_clock = cpu_clocks;
                end
                if (capture_event) capture_edge = cycle;
                if (gpr_event || flags_event) commit_edge = cycle;
                if (consume_event) consumes = consumes + 1;
                if (ready && bus_valid) begin
                    transfers = transfers + 1;
                    if (!boundary) ready_captures = ready_captures + 1;
                    if (bus_write) writes = writes + 1;
                end
                if (gpr_event || flags_event) begin
                    if (!pending_event || !dut.operation_retire || !boundary ||
                        cpu_clocks-start_clock < (form < 3 ? 2 : 3))
                        $fatal(1, "commit preceded qualified virtual deadline id=%0d", id);
                end
            end
            #1; clk = 1; #10; clk = 0;
            if (execute_enable) begin
                checks = checks + 1;
                reserved_bytes = (dut.fetch.p06_historical.state_q == 1 || dut.fetch.p06_historical.state_q == 2) ?
                    int'(dut.fetch.request_count_q) : (dut.fetch.raw_response_valid ? int'(dut.fetch.raw_response_count) : 0);
                if (int'(debug_prefetch_count)+reserved_bytes > 6)
                    $fatal(1, "full CPU prefetch plus reserved bytes exceed six");
                if (dut.p06_code_bus.scope_error) $fatal(1, "unqualified CODE pilot bus request");
                if (instruction_retired) begin
                    retire_edge = cycle; retire_clock = cpu_clocks;
                    if (!boundary) $fatal(1, "retirement outside virtual boundary");
                end
                if (microcode_fault || unsupported_opcode || shutdown ||
                    (control_error && !warming && !(action == 2 && redirect && !ip_write_en)))
                    $fatal(1, "CPU fault in pilot case id=%0d ip=%h", id, debug_ip);
                if (retire_edge == 0 && !instruction_retired &&
                    (debug_gpr !== initial_gpr || debug_flags !== initial_flags || debug_ip != 16'(start_ip)))
                    $fatal(1, "architectural state changed before retirement id=%0d", id);
                $fwrite(trace_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%04h,%04h,%04h,%032h,%04h,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d\n",
                    id, cycle, boundary, cpu_clocks, start_event, capture_event, pending_event,
                    gpr_event, flags_event, consume_event, debug_ip, dut.p06_cursor_ip,
                    debug_micro_pc, debug_gpr, debug_flags, bus_valid, address,
                    ready, bus_write, debug_prefetch_count, instruction_retired,
                    dut.p06_register.scope_error, dut.p06_register.scope_reason);
            end
        end
    endtask

    task automatic setup;
        begin
            execute_enable = 0; reset = 1; ready = 0; intr = 0; nmi = 0; hold_request = 0;
            gpr_write_en = 0; flags_write_en = 0; redirect = 0; ip_write_en = 0;
            segment_load_en = 0; tick(); reset = 0;
            for (integer i = 0; i < 4096; i = i + 1) memory[i] = 8'hf4;
            for (integer i = 0; i < length; i = i + 1) memory[start_ip+i] = code[i*8 +: 8];
            if (stream_test)
                for (integer k = 1; k < 4; k = k + 1)
                    for (integer i = 0; i < length; i = i + 1)
                        memory[start_ip+k*length+i] = code[i*8 +: 8];
            for (integer r = 0; r < 8; r = r + 1) begin
                gpr_write_en = 1; gpr_write_index = 3'(r);
                gpr_write_data = initial_gpr[r*16 +: 16]; tick();
            end
            gpr_write_en = 0; flags_write_en = 1; flags_write_data = initial_flags;
            flags_write_mask = 16'hffff; tick(); flags_write_en = 0;
            segment_load_en = 1; segment_load_index = 1; segment_load_selector = 0;
            redirect = 1; ip_write_en = 1; ip_write_data = 16'(start_ip); tick();
            segment_load_en = 0; redirect = 0; ip_write_en = 0;
            cycle = 0; started = 0; start_edge = 0; capture_edge = 0;
            commit_edge = 0; retire_edge = 0; consumes = 0; transfers = 0; writes = 0;
            start_clock = 0; retire_clock = 0; action_done = 0; execute_enable = 1;
        end
    endtask

    task automatic lifecycle;
        begin
            if (action == 1) begin
                execute_enable = 0;
                repeat (25) begin
                    tick();
                    if (instruction_retired || debug_gpr !== initial_gpr || debug_flags !== initial_flags ||
                        !dut.micro_executor.register_pending_q || debug_ip != 16'(start_ip))
                        $fatal(1, "pause did not retain architectural state");
                end
                execute_enable = 1;
            end else if (action == 2) begin
                // A malformed external controller transaction suppresses commit.
                redirect = 1; ip_write_en = 0;
                repeat (25) begin
                    tick();
                    if (!control_error || instruction_retired || debug_gpr !== initial_gpr ||
                        debug_flags !== initial_flags || !dut.micro_executor.register_pending_q)
                        $fatal(1, "control error lost retained result");
                end
                redirect = 0;
            end else if (action == 3) begin
                redirect = 1; ip_write_en = 1; ip_write_data = 16'h0500;
                execute_enable = 0; tick(); redirect = 0; ip_write_en = 0;
                if (instruction_retired || dut.micro_executor.register_pending_q ||
                    dut.p06_register.active || debug_ip != 16'h0500 ||
                    debug_gpr !== initial_gpr || debug_flags !== initial_flags)
                    $fatal(1, "redirect did not cancel pending timed commit");
            end else if (action == 4) begin
                execute_enable = 0; reset = 1; tick(); reset = 0;
                if (instruction_retired || dut.micro_executor.register_pending_q ||
                    dut.p06_register.active || dut.p06_register.scope_error)
                    $fatal(1, "reset did not cancel pending timing state");
            end else if (action == 5) begin
                nmi = 1; tick(); nmi = 0; tick();
                if (!debug_nmi_pending || dut.event_active || instruction_retired)
                    $fatal(1, "NMI was not retained until timed boundary");
            end
            action_done = 1;
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s", vectors_path) ||
            !$value$plusargs("trace=%s", trace_path) || !$value$plusargs("summary=%s", summary_path))
            $fatal(1, "required vectors/trace/summary paths missing");
        if ($value$plusargs("action=%d", action)) begin end
        warm_test = $test$plusargs("warm_test");
        scope_test = $test$plusargs("scope_test");
        protected_test = $test$plusargs("protected_test");
        stream_test = $test$plusargs("stream_test");
        vector_fd = $fopen(vectors_path, "r"); trace_fd = $fopen(trace_path, "w");
        summary_fd = $fopen(summary_path, "w");
        if (vector_fd == 0 || trace_fd == 0 || summary_fd == 0) $fatal(1, "probe files unavailable");
        $fwrite(trace_fd, "id,fabric_edge,boundary,cpu_clock,start,capture,pending,gpr_write,flags_write,consume,ip,cursor,micro_pc,gpr,flags,bus_valid,address,ready,write,queue,retired,scope_error,scope_reason\n");
        $fwrite(summary_fd, "id,form,ready_mode,start_edge,capture_edge,commit_edge,retire_edge,start_clock,retire_clock,elapsed,consumes,transfers,writes,gpr,flags,ip,scope_reason,action\n");
        while (!$feof(vector_fd)) begin
            scan = $fscanf(vector_fd, "%d %d %d %h %d %h %h %h %h %h %h\n",
                id, form, length, start_ip, ready_mode, code, initial_gpr,
                initial_flags, expected_gpr, expected_flags, flags_mask);
            if (scan != 11) $fatal(1, "invalid vector record fields=%0d", scan);
            if (stream_test && cases > 0) begin
                if (debug_gpr !== initial_gpr || debug_flags !== initial_flags || debug_ip != 16'(start_ip))
                    $fatal(1, "stream lost prior architectural state");
                previous_retire_clock = retire_clock;
                started = 0; capture_edge = 0; commit_edge = 0; retire_edge = 0;
                consumes = 0; transfers = 0; writes = 0; execute_enable = 1;
            end else begin
                setup();
                if (warm_test && !scope_test) begin
                    // Existing invalid-controller transaction holds EU, while
                    // the real fetch fills its six bytes. No forced queue state.
                    warming = 1; redirect = 1; ip_write_en = 0; ready = 1;
                    while ((debug_prefetch_count < 5 || bus_valid || dut.fetch.raw_response_valid) && cycle < 300) tick();
                    // An odd first fetch contributes one byte, then two words:
                    // five bytes are available; a further word would exceed six.
                    if (debug_prefetch_count < 5 || started != 0 || dut.fetch.raw_response_valid || bus_valid)
                        $fatal(1, "warm setup did not prefill bytes before dispatch");
                    redirect = 0; warming = 0;
                    cycle = 0; consumes = 0; transfers = 0; writes = 0;
                end
            end
            if (protected_test) force dut.protected_state.msw = 16'hFFF1;
            timeout_count = 0;
            while (retire_edge == 0 && timeout_count < 1500 &&
                !(scope_test && dut.p06_register.scope_error) &&
                !(action_done != 0 && (action == 3 || action == 4))) begin
                ready = ready_mode == 0 || (ready_mode == 1 ?
                    (cycle % 5 == id % 5) : (cycle % 101 == id % 7));
                tick(); timeout_count = timeout_count + 1;
                if (dut.micro_executor.register_pending_q && action != 0 && action_done == 0)
                    lifecycle();
            end
            if (scope_test) begin
                if (!dut.p06_register.scope_error || dut.p06_register.scope_reason != 3'(form) ||
                    retire_edge != 0 || commit_edge != 0 || writes != 0 || debug_ip != 16'(start_ip))
                    $fatal(1, "unqualified instruction did not stop explicitly id=%0d", id);
                repeat (20) tick();
            end else if (action != 3 && action != 4) begin
                if (retire_edge == 0 || started != 1 || capture_edge == 0 || commit_edge != retire_edge ||
                    debug_gpr !== expected_gpr || ((debug_flags ^ expected_flags) & flags_mask) != 0 ||
                    debug_ip != 16'(start_ip+length) || consumes != length || writes != 0 ||
                    dut.p06_register.active || dut.p06_register.scope_error)
                    $fatal(1, "timed result mismatch id=%0d gpr=%h flags=%h ip=%h", id, debug_gpr, debug_flags, debug_ip);
                if (warm_test && action == 0 && ready_mode < 2 && retire_clock-start_clock != (form < 3 ? 2 : 3))
                    $fatal(1, "unexpected implementation extension id=%0d clocks=%0d", id, retire_clock-start_clock);
                if (stream_test && cases > 0 && start_clock-previous_retire_clock < 1)
                    $fatal(1, "unaccounted dispatch gap in register stream");
                if (retire_clock-start_clock > (form < 3 ? 2 : 3)) late_cases = late_cases + 1;
                if (action == 5) begin
                    repeat (20) tick();
                    if (!dut.p06_register.scope_error || dut.p06_register.scope_reason != 4 ||
                        !dut.event_active || dut.event_ip != 16'(start_ip+length) || writes != 0 ||
                        debug_gpr !== expected_gpr || ((debug_flags ^ expected_flags) & flags_mask) != 0)
                        $fatal(1, "untimed NMI entry did not stop after the completed instruction");
                end
            end else if (action_done == 0) $fatal(1, "cancellation action not reached");
            $fwrite(summary_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h,%04h,%0d,%0d\n",
                id, form, ready_mode, start_edge, capture_edge, commit_edge, retire_edge,
                start_clock, retire_clock, retire_clock-start_clock, consumes, transfers, writes,
                debug_gpr, debug_flags, debug_ip, dut.p06_register.scope_reason, action);
            execute_enable = 0; cases = cases + 1;
            if (protected_test) release dut.protected_state.msw;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_TIMED_REGISTER_PASS cases=%0d checks=%0d extensions=%0d off_boundary_captures=%0d action=%0d scope=%0d",
            cases, checks, late_cases, ready_captures, action, scope_test);
        $finish;
    end
endmodule
