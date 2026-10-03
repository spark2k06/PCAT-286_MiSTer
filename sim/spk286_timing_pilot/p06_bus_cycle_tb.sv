`timescale 1ns/1ps
module p06_bus_cycle_tb;
    logic clk = 0, reset = 1, cancel = 0;
    wire phase_enable, phase_two, cpu_boundary;
    logic board_ready = 1, request_valid = 0, command_accept = 0;
    logic completion_valid = 0, response_ready = 1;
    logic [23:0] request_address = 0;
    logic [15:0] request_data = 0, completion_data = 0;
    logic [1:0] request_lanes = 0;
    logic [3:0] request_class = 0;
    logic request_write = 0, request_lock = 0;
    wire request_ready, command_valid, completion_ready, response_valid;
    wire [23:0] command_address;
    wire [15:0] command_data, response_data;
    wire [1:0] command_lanes, logical_state;
    wire [3:0] command_class;
    wire command_write, command_lock, physical_capture, logical_complete;
    wire external_wait, deadline_miss, busy, draining, protocol_error;
    p06_clock timing (.clk, .reset, .phase_enable, .phase_two,
                      .cpu_enable(cpu_boundary));
    p06_bus_cycle dut (.*);

    wire max_request_ready, max_command_valid, max_completion_ready;
    wire max_response_valid, max_capture, max_complete;
    wire [23:0] max_address;
    wire [15:0] max_data, max_response;
    wire [1:0] max_lanes, max_state;
    wire [3:0] max_class;
    wire max_write, max_lock, max_wait, max_miss, max_busy, max_drain, max_error;
    p06_bus_cycle #(.HISTORICAL(0)) maximum (
        .clk, .reset, .cancel, .cpu_boundary, .board_ready,
        .request_valid, .request_ready(max_request_ready), .request_address,
        .request_data, .request_lanes, .request_class, .request_write, .request_lock,
        .command_valid(max_command_valid), .command_accept,
        .command_address(max_address), .command_data(max_data),
        .command_lanes(max_lanes), .command_class(max_class),
        .command_write(max_write), .command_lock(max_lock), .completion_valid,
        .completion_ready(max_completion_ready), .completion_data,
        .response_valid(max_response_valid), .response_ready,
        .response_data(max_response), .physical_capture(max_capture),
        .logical_complete(max_complete), .external_wait(max_wait),
        .deadline_miss(max_miss), .busy(max_busy), .draining(max_drain),
        .protocol_error(max_error), .logical_state(max_state)
    );

    integer cases = 0, fabric = 0, cpu_count = 0, ticks = 0;
    integer requests = 0, commands = 0, captures = 0, completes = 0, replies = 0;
    integer request_edge = 0, command_edge = 0, capture_edge = 0;
    integer complete_edge = 0, request_cpu = 0, tc_samples = 0;
    integer waits_seen = 0, misses_seen = 0;
    integer planned_waits = 0;
    bit strict_transaction = 0;
    bit sample_edge_reported = 0;
    bit [24:0] capture_offsets = 0;
    logic [15:0] expected_result = 0;
    logic [47:0] expected_packet = 0;

    task automatic tick;
        integer earliest_cpu, expected_edge;
        begin
            #9;
            ticks = ticks + 1;
            if ({max_request_ready, max_command_valid, max_completion_ready,
                 max_response_valid, max_capture, max_complete} !==
                {(!reset && !cancel && command_accept),
                 (!reset && !cancel && request_valid),
                 (!reset && !cancel && response_ready),
                 (!reset && !cancel && completion_valid),
                 (!reset && !cancel && completion_valid && response_ready),
                 (!reset && !cancel && completion_valid && response_ready)})
                $fatal(1, "MAX handshake bypass mismatch");
            if ({max_address, max_data, max_lanes, max_class, max_write, max_lock}
                !== {request_address, request_data, request_lanes, request_class,
                     request_write, request_lock} || max_response !== completion_data)
                $fatal(1, "MAX payload bypass mismatch");
            if ({max_wait, max_miss, max_busy, max_drain, max_error, max_state} !== 7'd0)
                $fatal(1, "MAX timing state present");
            if (!reset) begin
                fabric = fabric + 1;
                if (cpu_boundary) cpu_count = cpu_count + 1;
                if (request_valid && request_ready) begin
                    requests = requests + 1;
                    request_edge = fabric;
                    request_cpu = cpu_count;
                end
                if (strict_transaction && command_valid &&
                    {command_address, command_data, command_lanes, command_class,
                     command_write, command_lock} !== expected_packet)
                    $fatal(1, "retained command metadata changed");
                if (command_valid && command_accept) begin
                    commands = commands + 1; command_edge = fabric;
                end
                if (physical_capture) begin
                    captures = captures + 1; capture_edge = fabric;
                    capture_offsets[fabric % 25] = 1;
                end
                if (cpu_boundary && logical_state == 2 && !cancel && !draining)
                    tc_samples = tc_samples + 1;
                if (external_wait) waits_seen = waits_seen + 1;
                if (deadline_miss) misses_seen = misses_seen + 1;
                if (external_wait && deadline_miss)
                    $fatal(1, "board wait and implementation miss conflated");
                if (logical_complete) begin
                    if (!cpu_boundary || cancel || !board_ready)
                        $fatal(1, "early logical completion");
                    if (strict_transaction) begin
                        earliest_cpu = request_cpu + 2 + planned_waits;
                        // Independent oracle: first eligible boundary at/after capture.
                        while ((25 * earliest_cpu + 2) / 3 < capture_edge)
                            earliest_cpu = earliest_cpu + 1;
                        expected_edge = (25 * earliest_cpu + 2) / 3;
                        if (capture_edge == 0 || fabric != expected_edge)
                            $fatal(1, "logical completion deadline: got %0d expected %0d",
                                   fabric, expected_edge);
                    end
                    completes = completes + 1; complete_edge = fabric;
                end
                if (response_valid) begin
                    if (strict_transaction && response_data !== expected_result)
                        $fatal(1, "lost or changed retained response");
                    if (response_ready) replies = replies + 1;
                end
            end
            #1; clk = 1; #10; clk = 0;
        end
    endtask

    task automatic restart;
        begin
            strict_transaction = 0;
            reset = 1; cancel = 0; request_valid = 0; command_accept = 0;
            completion_valid = 0; response_ready = 1; board_ready = 1;
            tick(); reset = 0;
            fabric = 0; cpu_count = 0; requests = 0; commands = 0;
            captures = 0; completes = 0; replies = 0;
            request_edge = 0; command_edge = 0; capture_edge = 0;
            complete_edge = 0; request_cpu = 0; tc_samples = 0;
            waits_seen = 0; misses_seen = 0;
        end
    endtask

    task automatic transaction(input integer delay_edges, accept_delay,
                               extra_waits, hold_reply);
        integer next_edge, loops;
        begin
            restart(); cases = cases + 1;
            planned_waits = extra_waits;
            request_address = 24'h123456 + 24'(cases);
            request_data = 16'h789a ^ 16'(cases);
            request_lanes = 2'(cases % 3 + 1);
            request_class = 4'(cases % 16);
            request_write = (cases % 2) != 0;
            request_lock = (cases % 3) == 0;
            expected_packet = {request_address, request_data, request_lanes,
                               request_class, request_write, request_lock};
            expected_result = 16'hcdef ^ 16'(cases);
            strict_transaction = 1;
            request_valid = 1; response_ready = hold_reply == 0;
            loops = 0;
            while (replies == 0 && loops < 160) begin
                next_edge = fabric + 1;
                command_accept = requests != 0 &&
                                 next_edge >= request_edge + 1 + accept_delay;
                completion_valid = (commands == 0 && command_valid &&
                                    command_accept && delay_edges == 0) ||
                                   (commands == 1 && captures == 0 &&
                                    next_edge == command_edge + delay_edges);
                completion_data = completion_valid ? expected_result : 16'(next_edge);
                board_ready = tc_samples >= extra_waits;
                if (complete_edge != 0 && next_edge >= complete_edge + hold_reply)
                    response_ready = 1;
                tick(); loops = loops + 1;
                if (requests == 1) begin
                    request_valid = 0;
                    // Poison the input immediately: only the retained packet may issue.
                    request_address = 0; request_data = 0; request_lanes = 0;
                    request_class = 0; request_write = 0; request_lock = 0;
                end
            end
            completion_valid = 0;
            if (requests != 1 || commands != 1 || captures != 1 ||
                completes != 1 || replies != 1 || busy || protocol_error)
                $fatal(1, "transaction count/drain mismatch case %0d", cases);
            if (waits_seen != extra_waits)
                $fatal(1, "external wait count mismatch");
            if ((misses_seen != 0) != (capture_edge >
                (25 * (request_cpu + 2 + extra_waits) + 2) / 3))
                $fatal(1, "implementation deadline classification mismatch");
            if ((delay_edges == 0 && accept_delay == 0 && hold_reply == 0) ||
                delay_edges == 80 || (!sample_edge_reported && capture_edge == complete_edge)) begin
                $display("P06_BUS_TRACE delay=%0d accept_delay=%0d board_waits=%0d request=%0d accept=%0d capture=%0d complete=%0d external_waits=%0d deadline_misses=%0d",
                    delay_edges, accept_delay, extra_waits, request_edge, command_edge,
                    capture_edge, complete_edge, waits_seen, misses_seen);
                if (capture_edge == complete_edge) sample_edge_reported = 1;
            end
            tick();
            if (replies != 1 || busy) $fatal(1, "duplicate logical reply");
            strict_transaction = 0;
        end
    endtask

    task automatic admit;
        begin
            request_valid = 1;
            while (requests == 0) tick();
            request_valid = 0;
        end
    endtask

    task automatic cancellation(input integer moment, input bit write_access);
        integer n;
        begin
            restart(); cases = cases + 1;
            request_write = write_access;
            request_address = 24'h112233; request_data = 16'h4455;
            admit();
            if (moment != 0) begin
                command_accept = 1; tick(); command_accept = 0;
            end
            if (moment == 2) begin
                completion_valid = 1; completion_data = 16'habcd;
            end
            cancel = 1; tick(); cancel = 0; completion_valid = 0;
            if (moment == 1) begin
                if (!draining || !busy) $fatal(1, "accepted access not draining");
                for (n = 0; n < 29; n = n + 1) begin
                    tick();
                    if (response_valid || command_valid || request_ready)
                        $fatal(1, "canceled access escaped before drain");
                end
                completion_valid = 1; completion_data = 16'habcd;
                tick(); completion_valid = 0;
            end
            tick();
            if (busy || draining || replies != 0 || completes != 0 || protocol_error ||
                commands != ((moment == 0) ? 0 : 1) ||
                captures != ((moment == 0) ? 0 : 1))
                $fatal(1, "cancel/drop/physical count mismatch");
        end
    endtask

    task automatic back_to_back(input bit identical);
        integer loops;
        begin
            restart(); cases = cases + 1;
            request_address = 24'haabbcc; request_data = 16'h7788;
            request_lanes = 2'b11; request_class = 4'h9;
            request_write = 1; request_lock = 1;
            admit(); command_accept = 1; completion_valid = 1;
            completion_data = 16'h1111; tick(); completion_valid = 0;
            request_address = identical ? 24'haabbcc : 24'haabbcd;
            request_data = 16'h7788;
            request_lanes = 2'b11; request_class = 4'h9;
            request_write = 1; request_lock = 1; request_valid = 1;
            loops = 0;
            while (completes == 0 && loops < 60) begin tick(); loops = loops + 1; end
            request_valid = 0;
            if (requests != 2 || replies != 1 || logical_state != 1 ||
                command_address != (identical ? 24'haabbcc : 24'haabbcd) || command_data != 16'h7788 ||
                !command_write || !command_lock)
                $fatal(1, "back-to-back new packet lost or mandatory Ti inserted");
            completion_valid = 1; completion_data = 16'h2222;
            tick(); completion_valid = 0;
            loops = 0;
            while (replies != 2 && loops < 60) begin tick(); loops = loops + 1; end
            if (requests != 2 || commands != 2 || captures != 2 || completes != 2 ||
                replies != 2 || busy || protocol_error)
                $fatal(1, "back-to-back counts mismatch");
        end
    endtask

    integer d, a, w, h, m, controls;
    initial begin
        for (d = 0; d < 25; d = d + 1)
            for (a = 0; a < 5; a = a + 1)
                for (w = 0; w < 3; w = w + 1)
                    for (h = 0; h < 2; h = h + 1)
                        transaction(d, a, w, h * 13);
        // Later physical responses explicitly force implementation extensions.
        transaction(80, 4, 0, 0);
        for (m = 0; m < 3; m = m + 1) begin
            cancellation(m, 0); cancellation(m, 1);
        end
        back_to_back(0); back_to_back(1);
        // Cancel on the first eligible Tc boundary: capture may drain, no publish.
        restart(); admit(); command_accept = 1; completion_valid = 1;
        tick(); completion_valid = 0;
        while (fabric < 24) tick();
        cancel = 1; tick(); cancel = 0; tick();
        if (completes != 0 || replies != 0 || busy || protocol_error)
            $fatal(1, "eligible-boundary cancel published a result");
        // Cancel an already published logical reply.
        restart(); response_ready = 0; admit(); command_accept = 1;
        completion_valid = 1; tick(); completion_valid = 0;
        while (completes == 0) tick();
        cancel = 1; tick(); cancel = 0; response_ready = 1; tick();
        if (busy || replies != 0 || protocol_error) $fatal(1, "published cancel failed");
        // Global reset is a joint backend reset; a later stale pulse is rejected.
        restart(); admit(); command_accept = 1; tick();
        reset = 1; tick(); reset = 0; completion_valid = 1; tick();
        completion_valid = 0;
        if (!protocol_error || captures != 0 || replies != 0 || busy)
            $fatal(1, "stale response after joint reset not detected");
        restart();
        // A duplicate physical completion is not a second accepted operation.
        admit(); command_accept = 1; completion_valid = 1; tick();
        tick(); completion_valid = 0;
        if (!protocol_error || captures != 1 || commands != 1)
            $fatal(1, "duplicate physical completion not detected");
        restart();
        // Exhaust all MAX control combinations independently of historical timing.
        for (controls = 0; controls < 64; controls = controls + 1) begin
            reset = (controls & 1) != 0; cancel = (controls & 2) != 0;
            request_valid = (controls & 4) != 0;
            command_accept = (controls & 8) != 0;
            completion_valid = (controls & 16) != 0;
            response_ready = (controls & 32) != 0;
            request_address = 24'(controls * 253); request_data = 16'(controls * 31);
            completion_data = 16'(controls * 71); tick();
        end
        if (capture_offsets !== 25'h1ffffff) $fatal(1, "capture phase sweep incomplete");
        $display("P06_BUS_PASS cases=%0d ticks=%0d capture_offsets=25 waits=0/1/2 late=80 MAX=64",
                 cases, ticks);
        $finish;
    end
endmodule
