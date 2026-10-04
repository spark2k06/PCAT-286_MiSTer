`timescale 1ns/1ps
// Full CPU execution probe. The Python caller supplies independent vectors.
module p06_core_register_tb;
    wire p06_code_board_ready=clk, p06_data_board_ready=!clk;
    `include "spk286_signals.svh"
`ifdef P06_REGISTER_PILOT
    spk286 #(.P06_REGISTER_PILOT(1'b1)) dut (.*);
`else
    spk286 dut (.*);
`endif
    logic [7:0] memory [0:4095];
    logic [127:0] initial_gpr, expected_gpr, last_gpr;
    logic [15:0] initial_flags, expected_flags, flags_mask, last_flags;
    logic [31:0] code;
    integer vector_fd, trace_fd, summary_fd, scan, id, form, length, start_ip;
    integer ready_mode, cycle, started, start_edge, capture_edge, commit_edge, retire_edge;
    integer consumes, transfers, writes, checks = 0, cases = 0, timeout_count;
    string vectors_path, trace_path, summary_path;

    task automatic tick;
        bit start_event, capture_event, gpr_event, flags_event, consume_event;
        bit pending_event;
        integer ip_before;
        begin
            #9;
            data_in = 16'hffff;
            if (address < 4096)
                data_in = {memory[{address[11:1],1'b1}], memory[{address[11:1],1'b0}]};
            start_event = dut.opcode_start;
            capture_event = dut.micro_executor.register_capture || dut.micro_executor.immediate_capture;
            gpr_event = dut.effective_gpr_write_en && dut.commit_allowed;
            flags_event = dut.effective_flags_write_en && dut.commit_allowed;
            consume_event = dut.queue_consume_valid && dut.queue_consume_ready;
            pending_event = dut.micro_executor.register_pending_q;
            ip_before = int'(debug_ip);
            if (execute_enable) begin
                cycle = cycle + 1;
                if (start_event) begin started = started + 1; start_edge = cycle; end
                if (capture_event) capture_edge = cycle;
                if (gpr_event || flags_event) commit_edge = cycle;
                if (consume_event) consumes = consumes + 1;
                if (ready && bus_valid) begin
                    transfers = transfers + 1;
                    if (bus_write) writes = writes + 1;
                end
                if (gpr_event || flags_event) begin
                    if (!pending_event || !dut.operation_retire)
                        $fatal(1, "register commit was not fused with retirement id=%0d", id);
                end
            end
            #1; clk = 1; #10; clk = 0;
            if (execute_enable) begin
                checks = checks + 1;
                if (instruction_retired) retire_edge = cycle;
                if (microcode_fault || unsupported_opcode || shutdown || control_error)
                    $fatal(1, "CPU fault in qualified register case id=%0d ip=%h", id, debug_ip);
                if (!instruction_retired && (debug_gpr !== initial_gpr || debug_flags !== initial_flags))
                    $fatal(1, "architectural GPR/FLAGS changed before retirement id=%0d", id);
                $fwrite(trace_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%04h,%04h,%032h,%04h,%0d,%06h,%0d,%0d,%0d,%0d,%0d\n",
                    id, cycle, start_event, capture_event, pending_event, gpr_event,
                    flags_event, consume_event, instruction_retired, ip_before, debug_ip,
                    debug_micro_pc, debug_gpr, debug_flags, bus_valid, address,
                    ready, bus_write, bus_bhe_n, debug_prefetch_count, debug_micro_active);
            end
        end
    endtask

    task automatic setup;
        begin
            execute_enable = 0; reset = 1; ready = 0; intr = 0; nmi = 0; hold_request = 0;
            gpr_write_en = 0; flags_write_en = 0; redirect = 0; ip_write_en = 0;
            segment_load_en = 0; tick(); reset = 0;
            for (integer i = 0; i < 4096; i = i + 1) memory[i] = 8'hf4;
            for (integer i = 0; i < length; i = i + 1)
                memory[start_ip+i] = code[i*8 +: 8];
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
            last_gpr = initial_gpr; last_flags = initial_flags; execute_enable = 1;
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s", vectors_path) ||
            !$value$plusargs("trace=%s", trace_path) || !$value$plusargs("summary=%s", summary_path))
            $fatal(1, "required vectors/trace/summary paths missing");
        vector_fd = $fopen(vectors_path, "r"); trace_fd = $fopen(trace_path, "w");
        summary_fd = $fopen(summary_path, "w");
        if (vector_fd == 0 || trace_fd == 0 || summary_fd == 0) $fatal(1, "probe files unavailable");
        $fwrite(trace_fd, "id,fabric_edge,opcode_start,capture,pending,gpr_write,flags_write,consume,retired,ip_before,ip_after,micro_pc,gpr,flags,bus_valid,address,ready,write,bhe_n,queue,micro_active\n");
        $fwrite(summary_fd, "id,form,length,start_ip,ready_mode,start_edge,capture_edge,commit_edge,retire_edge,consumes,transfers,writes,gpr,flags,ip\n");
        while (!$feof(vector_fd)) begin
            scan = $fscanf(vector_fd, "%d %d %d %h %d %h %h %h %h %h %h\n",
                id, form, length, start_ip, ready_mode, code, initial_gpr,
                initial_flags, expected_gpr, expected_flags, flags_mask);
            if (scan != 11) $fatal(1, "invalid vector record fields=%0d", scan);
            setup(); timeout_count = 0;
            while (retire_edge == 0 && timeout_count < 600) begin
                ready = ready_mode == 0 || (cycle % 5 == id % 5);
                tick(); timeout_count = timeout_count + 1;
            end
            if (retire_edge == 0 || started != 1 || capture_edge == 0 || commit_edge != retire_edge ||
                debug_gpr !== expected_gpr || ((debug_flags ^ expected_flags) & flags_mask) != 0 ||
                debug_ip != 16'(start_ip+length) || consumes != length || writes != 0)
                $fatal(1, "probe result mismatch id=%0d start=%0d capture=%0d commit=%0d retire=%0d gpr=%h flags=%h ip=%h",
                    id, start_edge, capture_edge, commit_edge, retire_edge, debug_gpr, debug_flags, debug_ip);
            $fwrite(summary_fd, "%0d,%0d,%0d,%04h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h,%04h\n",
                id, form, length, 16'(start_ip), ready_mode, start_edge, capture_edge,
                commit_edge, retire_edge, consumes, transfers, writes, debug_gpr, debug_flags, debug_ip);
            execute_enable = 0; cases = cases + 1;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_CORE_REGISTER_PASS cases=%0d checks=%0d", cases, checks);
        $finish;
    end
endmodule
