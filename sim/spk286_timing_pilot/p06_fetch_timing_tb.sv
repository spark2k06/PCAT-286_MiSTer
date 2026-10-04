`timescale 1ns/1ps
// Real production fetch + six-byte queue, selected private temporal hooks.
module p06_fetch_timing_tb;
    logic clk = 0, reset = 1, ready = 0, restart = 0, suspend = 1;
    logic [15:0] data_in = 0, restart_ip = 16'h0100;
    logic [23:0] code_base = 0;
    logic [15:0] code_limit = 16'hffff;
    logic wrap_ip = 1, request = 0, response_ready;
    wire request_ready, response_valid, blocked, bus_valid, bus_bhe_n;
    wire [15:0] response_data, response_ip;
    wire [1:0] response_count;
    wire [16:0] cursor;
    wire [23:0] address;
    wire p06_cpu_boundary, phase_enable, phase_two;
    logic p06_board_ready = 1;
    wire p06_admission_enable;
    wire queue_valid, queue_fill_ready;
    wire [7:0] queue_data;
    wire [3:0] queue_count;
    logic queue_consume = 0;
    p06_clock clock_policy (.clk(clk), .reset(reset), .phase_enable(phase_enable),
        .phase_two(phase_two), .cpu_enable(p06_cpu_boundary));
    spk286_fetch #(.P06_FETCH_TIMING(1'b1)) dut (.*);
    spk286_prefetch_queue queue (.clk(clk), .reset(reset), .flush(restart),
        .fill_valid(response_valid && consumer_enabled), .fill_data(response_data), .fill_count(response_count),
        .fill_ready(queue_fill_ready), .consume_valid(queue_valid), .consume_data(queue_data),
        .consume_ready(queue_consume), .count(queue_count));
    logic consumer_enabled = 1;
    assign response_ready = consumer_enabled && queue_fill_ready;
    wire queue_fill = response_valid && response_ready;
    wire [4:0] projected_count = {1'b0, queue_count} +
        (queue_fill ? {3'd0, response_count} : 5'd0) - 5'(queue_valid && queue_consume);
    assign p06_admission_enable = projected_count <= 5'd4;
    integer fabric_age = 0, cpu_clocks = 0, starts = 0, captures = 0, publishes = 0;
    integer begin_clock = 0, physical_age = 0, waits = 0, delay = 0;
    integer external_waits = 0, misses = 0, bytes = 0, case_id = 0;
    integer checks = 0, cases = 0, peak_reserved = 0, off_boundary = 0;
    integer reserved, summary_fd, trace_fd, expected_ip = 0, first_pub_clock;
    logic [23:0] held_address;
    logic held_bhe;
    bit pending_physical = 0;
    string trace_path, summary_path;

    function automatic [7:0] pattern(input logic [23:0] a);
        pattern = a[7:0] ^ 8'h5a;
    endfunction
    function automatic bit next_boundary;
        next_boundary = !reset && (3*(fabric_age+1)/25 != 3*fabric_age/25);
    endfunction

    task automatic tick;
        bit boundary, start_event, capture_event, publication, logical_complete;
        integer next_clock;
        logic [15:0] expected_data;
        begin
            #8;
            boundary = next_boundary();
            next_clock = cpu_clocks + int'(boundary);
            if (p06_cpu_boundary !== boundary) $fatal(1, "clock differs from rational oracle");
            p06_board_ready = next_clock >= begin_clock+2+waits;
            // One READY pulse; poison outside capture. Delay -1 is exact Tc capture.
            ready = bus_valid && (delay == -1 ? (boundary && next_clock >= begin_clock+2+waits) :
                                                physical_age >= delay);
            data_in = ready ? {pattern({address[23:1],1'b1}), pattern({address[23:1],1'b0})} : 16'hBAD0;
            #1; // Settle READY/data/board combinational logic before observation.
            start_event = dut.p06_issue;
            capture_event = dut.p06_capture;
            logical_complete = dut.p06_complete;
            publication = response_valid && response_ready;
            if (!reset) begin
                checks = checks + 1;
                if (pending_physical && bus_valid && (address !== held_address || bus_bhe_n !== held_bhe))
                    $fatal(1, "physical metadata changed before READY case=%0d", case_id);
                if (bus_valid) begin
                    if (!pending_physical) begin held_address = address; held_bhe = bus_bhe_n; end
                    pending_physical = 1;
                end
                if (capture_event) begin
                    captures = captures + 1; pending_physical = 0;
                    if (!boundary) off_boundary = off_boundary + 1;
                end
                if (dut.p06_historical.external_wait) external_waits = external_waits + 1;
                if (dut.p06_historical.deadline_miss) misses = misses + 1;
                if (logical_complete && (!boundary || next_clock-begin_clock < 2+waits))
                    $fatal(1, "logical fetch completed before Tc deadline");
                if (publication) begin
                    if (!logical_complete && dut.p06_historical.state_q != 3)
                        $fatal(1, "publication before logical Tc");
                    expected_data = response_count == 2 ?
                        {pattern(code_base+{8'd0,response_ip}+24'd1), pattern(code_base+{8'd0,response_ip})} :
                        {8'd0,pattern(code_base+{8'd0,response_ip})};
                    if (response_data !== expected_data || (response_count != 1 && response_count != 2))
                        $fatal(1, "stale or wrong-lane fetch publication data=%h expected=%h", response_data, expected_data);
                    publishes = publishes + 1;
                    if (publishes == 1) first_pub_clock = next_clock;
                end
                if (queue_valid && queue_consume && !restart) begin
                    if (queue_data !== pattern(code_base+{8'd0,16'(expected_ip)}))
                        $fatal(1, "queue byte order corrupt ip=%h data=%h", 16'(expected_ip), queue_data);
                    expected_ip = (expected_ip+1) & 65535; bytes = bytes + 1;
                end
                if (start_event) begin
                    if (!boundary) $fatal(1, "fetch issued outside CPU boundary");
                    begin_clock = next_clock; starts = starts + 1; physical_age = 0;
                end else if (bus_valid) physical_age = physical_age + 1;
                $fwrite(trace_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%04h,%04h,%0d,%0d,%0d\n",
                    case_id, fabric_age+1, next_clock, boundary, start_event, capture_event,
                    logical_complete, publication, queue_count, dut.p06_historical.state_q,
                    ready, restart, address, bus_bhe_n, response_ip, response_data,
                    response_count, external_waits, misses);
            end
            #1; clk = 1; #10; clk = 0;
            if (reset) begin fabric_age = 0; cpu_clocks = 0; pending_physical = 0; end
            else begin
                fabric_age = fabric_age + 1; cpu_clocks = next_clock;
                reserved = (dut.p06_historical.state_q == 1 || dut.p06_historical.state_q == 2) ?
                    int'(dut.request_count_q) : (dut.raw_response_valid ? int'(dut.raw_response_count) : 0);
                if (int'(queue_count)+reserved > 6) $fatal(1, "queue plus reserved bytes exceed six");
                if (int'(queue_count)+reserved > peak_reserved) peak_reserved = int'(queue_count)+reserved;
            end
        end
    endtask

    task automatic setup(input integer ws, latency, odd);
        begin
            reset = 1; restart = 0; suspend = 1; request = 0; queue_consume = 0;
            consumer_enabled = 1; tick(); reset = 0;
            code_base = 0; code_limit = 16'hffff; wrap_ip = 1;
            starts = 0; captures = 0; publishes = 0; external_waits = 0; misses = 0;
            bytes = 0; physical_age = 0; begin_clock = 0; first_pub_clock = 0;
            waits = ws; delay = latency; peak_reserved = 0;
            restart_ip = 16'h0100 + 16'(odd); expected_ip = int'(restart_ip);
            restart = 1; tick(); restart = 0; suspend = 0; request = 1;
        end
    endtask
    task automatic receipt(input integer kind);
        begin
            $fwrite(summary_fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",
                case_id, kind, waits, delay, starts, captures, publishes, bytes, external_waits, misses, peak_reserved);
            cases = cases + 1; case_id = case_id + 1;
        end
    endtask

    initial begin
        if (!$value$plusargs("trace=%s", trace_path) || !$value$plusargs("summary=%s", summary_path))
            $fatal(1, "required trace/summary paths missing");
        trace_fd = $fopen(trace_path,"w"); summary_fd = $fopen(summary_path,"w");
        $fwrite(trace_fd,"case,fabric_edge,cpu_clock,boundary,start,capture,complete,publish,queue,state,ready,restart,address,bhe_n,ip,data,count,external_waits,misses\n");
        $fwrite(summary_fd,"case,kind,waits,delay,starts,captures,publishes,bytes,external_waits,misses,peak_reserved\n");
        // Timed refill, including late data and capture exactly at Tc.
        for (integer ws = 0; ws < 3; ws = ws + 1)
            for (integer d = 0; d < 48; d = d + 1)
                for (integer odd = 0; odd < 2; odd = odd + 1) begin
                    // Every fabric offset 0..45, exact Tc, and very late READY.
                    setup(ws, d < 46 ? d : d == 46 ? -1 : 80, odd);
                    queue_consume = 1;
                    while (bytes < 16 && fabric_age < 2000) tick();
                    if (bytes < 16 || captures < publishes || ((d < 13 || d == 46) && misses != 0) ||
                        (d == 47 && misses == 0)) $fatal(1,"refill scenario did not meet expected dependency class");
                    receipt(0);
                end
        // Exact capacity: filling from four to six cannot reserve a fourth word.
        setup(0,0,0);
        while (queue_count != 6 && fabric_age < 300) tick();
        if (queue_count != 6 || starts != 3 || captures != 3 || publishes != 3)
            $fatal(1,"capacity did not stop at three words");
        repeat (50) tick();
        if (starts != 3 || bus_valid || dut.raw_response_valid) $fatal(1,"hidden prefetch beyond six bytes");
        queue_consume = 1; while (bytes < 16 && fabric_age < 800) tick();
        if (bytes < 16) $fatal(1,"capacity did not resume"); receipt(1);
        // Logical result stays stable while the consumer refuses it after Tc.
        setup(0,0,1); consumer_enabled = 0;
        while (dut.p06_historical.state_q != 3 && fabric_age < 200) tick();
        if (dut.p06_historical.state_q != 3) $fatal(1,"publication backpressure not reached");
        repeat (31) tick();
        if (starts != 1 || captures != 1 || publishes != 0 || !response_valid)
            $fatal(1,"backpressure lost or duplicated retained result");
        consumer_enabled = 1; queue_consume = 1;
        while (bytes < 8 && fabric_age < 600) tick(); receipt(2);
        // Redirect while physical read waits, or after early capture before Tc.
        for (integer captured = 0; captured < 4; captured = captured + 1) begin
            setup(0,captured == 0 ? 80 : captured == 2 ? -1 : 0,0);
            if (captured == 3) begin
                consumer_enabled = 0;
                while (dut.p06_historical.state_q != 3) tick();
            end else if (captured == 2) begin
                while (!bus_valid || !(next_boundary() && cpu_clocks+1 >= begin_clock+2)) tick();
            end else if (captured == 1) while (!dut.raw_response_valid) tick();
            else while (!bus_valid) tick();
            request = 0; restart = 1; restart_ip = 16'h0301; expected_ip = int'(16'h0301);
            tick(); restart = 0; request = 1; queue_consume = 1; consumer_enabled = 1;
            while (bytes < 8 && fabric_age < 1000) tick();
            if (bytes < 8 || captures < publishes+1) $fatal(1,"redirect did not discard exactly one old response");
            receipt(3);
        end
        // Reset after physical retention but before logical publication.
        setup(0,0,0); while (!dut.raw_response_valid) tick();
        reset = 1; tick(); reset = 0;
        if (bus_valid || response_valid || dut.raw_response_valid || queue_count != 0 ||
            dut.p06_historical.state_q != 0) $fatal(1,"reset retained an old logical response");
        restart = 1; restart_ip = 16'h0401; expected_ip = int'(restart_ip);
        tick(); restart = 0; queue_consume = 1;
        while (bytes < 8 && fabric_age < 700) tick();
        if (bytes < 8) $fatal(1,"reset did not resume new stream"); receipt(4);
        // End-of-segment byte and logical blocking preserve the one final byte.
        setup(0,0,0); code_limit = 16'h0100; queue_consume = 1;
        while (bytes < 1 && fabric_age < 300) tick();
        repeat (40) tick();
        if (bytes != 1 || starts != 1 || publishes != 1 || !blocked || bus_valid)
            $fatal(1,"segment limit failed final byte/blocking"); receipt(5);
        // Real-mode FFFF wraps the logical IP; protected mode would block.
        setup(0,0,0); restart_ip = 16'hffff; expected_ip = int'(restart_ip);
        restart = 1; tick(); restart = 0; queue_consume = 1;
        while (bytes < 8 && fabric_age < 600) tick();
        if (bytes < 8 || blocked) $fatal(1,"real-mode fetch did not wrap"); receipt(6);
        $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_FETCH_TIMING_PASS cases=%0d checks=%0d off_boundary_captures=%0d",cases,checks,off_boundary);
        $finish;
    end
endmodule
