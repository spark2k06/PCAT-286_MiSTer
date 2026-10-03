// Abstract caller/backend fixture, not an x86 executor or a full DOS run.
// Data issue at instruction start is an unvalidated scheduling assumption.
`timescale 1ns/1ps
module p06_timing_fixture_tb;
    logic clk = 0, reset = 1, cancel = 0;
    wire cpu_boundary, phase_enable, phase_two;
    p06_clock clock_policy (.clk, .reset, .phase_enable, .phase_two,
                            .cpu_enable(cpu_boundary));
    logic start_valid = 0;
    wire start_ready;
    logic [3:0] instruction_form = 8;
    wire retire_enable, dependency_blocked, consumer_blocked;
    wire metadata_qualified, metadata_error, timing_error, active;
    wire [5:0] minimum_clocks;
    wire [7:0] elapsed_clocks, scheduled_clocks;
    wire dependencies_ready;
    wire read_wait_event;
    p06_instruction_duration instruction_policy (
        .clk, .reset, .cancel, .cpu_boundary, .start_valid, .start_ready,
        .instruction_form, .real_mode(1'b1), .prefix_free(1'b1), .taken(1'b0),
        .branch_outcome_known(1'b1), .target_length_known(1'b0), .next_length(4'd0),
        .operand_odd(1'b0), .ea_base_index_disp(1'b0), .read_wait_event,
        // Functional work is mocked ready: this tests temporal/dependency gating.
        .functional_done(1'b1), .dependencies_ready, .retire_ready(1'b1),
        .retire_enable, .dependency_blocked, .consumer_blocked,
        .metadata_qualified, .metadata_error, .timing_error, .active,
        .minimum_clocks, .elapsed_clocks, .scheduled_clocks
    );
    logic request_valid = 0, command_accept = 0, completion_valid = 0;
    logic board_ready = 1, request_write = 0;
    logic [15:0] request_data = 0, completion_data = 0;
    wire request_ready, command_valid, command_write, command_lock;
    wire [23:0] command_address;
    wire [15:0] command_data, response_data;
    wire [1:0] command_lanes, logical_state;
    wire [3:0] command_class;
    wire completion_ready, response_valid, physical_capture, logical_complete;
    wire external_wait, deadline_miss, busy, draining, protocol_error;
    p06_bus_cycle bus_policy (
        .clk, .reset, .cancel, .cpu_boundary, .board_ready,
        .request_valid, .request_ready, .request_address(24'h1000), .request_data,
        .request_lanes(2'b11), .request_class(4'h1), .request_write, .request_lock(1'b0),
        .command_valid, .command_accept, .command_address, .command_data,
        .command_lanes, .command_class, .command_write, .command_lock,
        .completion_valid, .completion_ready, .completion_data,
        .response_valid, .response_ready(1'b1), .response_data,
        .physical_capture, .logical_complete, .external_wait, .deadline_miss,
        .busy, .draining, .protocol_error, .logical_state
    );

    integer cases = 0, ticks = 0, fabric = 0, cpu_count = 0;
    integer required_responses = 1, responses = 0, requests = 0, commands = 0;
    integer captures = 0, starts = 0, retires = 0, start_cpu = 0, retire_cpu = 0;
    integer request_edge = 0, backend_edge = 0, tc_samples = 0;
    integer read_waits = 0, writes = 0, misses = 0, dependency_blocks = 0;
    integer expected_minimum = 0;
    bit backend_busy = 0;
    logic [15:0] memory_value = 16'ha5c3;
    logic [15:0] backend_result = 0, published_operand = 0;
    integer published_count_q = 0;
    // The caller's retained state changes at the edge, independently of the
    // pre-edge observer. Otherwise counting this reply before the edge and
    // still seeing response_valid would count the same reply twice in RMW.
    always @(posedge clk) begin
        if (reset) published_count_q <= 0;
        else if (response_valid) published_count_q <= published_count_q + 1;
    end
    assign dependencies_ready = published_count_q >= required_responses ||
                                (response_valid && published_count_q + 1 == required_responses);
    assign read_wait_event = external_wait && !command_write;

    task automatic tick;
        bit permission;
        begin
            #9; ticks = ticks + 1;
            if (!reset) begin
                fabric = fabric + 1;
                if (cpu_boundary) cpu_count = cpu_count + 1;
                if (read_wait_event) read_waits = read_waits + 1;
                if (starts != 0) begin
                    permission = !cancel && cpu_boundary && dependencies_ready &&
                        cpu_count - start_cpu >= expected_minimum + read_waits;
                    if (retire_enable !== permission)
                        $fatal(1, "fixture premature retirement or extra duration form=%0d fabric=%0d age=%0d expected=%0d got=%0d responses=%0d valid=%0d deps=%0d budget=%0d elapsed=%0d error=%0d",
                            instruction_form, fabric, cpu_count - start_cpu, permission,
                            retire_enable, responses, response_valid, dependencies_ready,
                            scheduled_clocks, elapsed_clocks, timing_error);
                end
                if (start_valid && start_ready) begin
                    starts = starts + 1; start_cpu = cpu_count;
                end
                if (request_valid && request_ready) begin
                    requests = requests + 1; request_edge = fabric;
                end
                if (command_valid && command_accept) begin
                    if (backend_busy || command_address != 24'h1000 || command_lanes != 3 ||
                        command_class != 1 || command_lock)
                        $fatal(1, "fixture backend packet/ownership mismatch");
                    commands = commands + 1; backend_busy = 1; backend_edge = fabric;
                    backend_result = command_write ? 16'd0 : memory_value;
                    if (command_write) begin
                        writes = writes + 1; memory_value = command_data;
                    end
                end
                if (physical_capture) begin
                    if (!backend_busy) $fatal(1, "fixture capture without accepted command");
                    backend_busy = 0; captures = captures + 1;
                end
                if (cpu_boundary && logical_state == 2) tc_samples = tc_samples + 1;
                if (deadline_miss) misses = misses + 1;
                if (dependency_blocked) dependency_blocks = dependency_blocks + 1;
                if (response_valid) begin
                    if (responses == 0 && instruction_form != 9) begin
                        if (response_data != 16'ha5c3) $fatal(1, "fixture lost read data");
                        published_operand = response_data;
                    end
                    responses = responses + 1; tc_samples = 0;
                end
                if (retire_enable) begin
                    retires = retires + 1; retire_cpu = cpu_count;
                end
            end
            #1; clk = 1; #10; clk = 0;
        end
    endtask

    task automatic run_case(input integer form, board_waits, accept_delay, result_delay);
        integer next_edge, loops;
        begin
            reset = 1; cancel = 0; start_valid = 0; request_valid = 0;
            completion_valid = 0; command_accept = 0; tick(); reset = 0;
            fabric = 0; cpu_count = 0; starts = 0; retires = 0; responses = 0;
            requests = 0; commands = 0; captures = 0; writes = 0; tc_samples = 0;
            start_cpu = 0; retire_cpu = 0; read_waits = 0; misses = 0; dependency_blocks = 0;
            backend_busy = 0; memory_value = 16'ha5c3; published_operand = 0;
            instruction_form = 4'(form); required_responses = form == 11 ? 2 : 1;
            expected_minimum = form == 8 ? 5 : (form == 9 ? 3 : 7);
            request_write = form == 9; request_data = 16'h7788;
            start_valid = 1; request_valid = 1; loops = 0;
            while (retires == 0 && loops < 400) begin
                next_edge = fabric + 1;
                board_ready = tc_samples >= board_waits;
                command_accept = requests != 0 && next_edge >= request_edge + 1 + accept_delay;
                completion_valid = (command_valid && command_accept && result_delay == 0) ||
                    (backend_busy && next_edge == backend_edge + result_delay);
                completion_data = completion_valid ?
                    (backend_busy ? backend_result : (command_write ? 16'd0 : memory_value)) :
                    16'(next_edge); // poison outside the physical pulse
                if (form == 11 && requests == 1 && response_valid) begin
                    // Preview the second packet; the old read still owns its reply.
                    request_valid = 1; request_write = 1; request_data = response_data ^ 16'h55aa;
                end
                tick(); loops = loops + 1;
                if (starts != 0) start_valid = 0;
                if (requests != 0) request_valid = 0;
            end
            completion_valid = 0; command_accept = 0;
            if (retires != 1 || starts != 1 || responses != required_responses ||
                requests != required_responses || commands != required_responses ||
                captures != required_responses || backend_busy || busy || active || timing_error ||
                protocol_error || metadata_error || consumer_blocked)
                $fatal(1, "fixture completion/count mismatch form=%0d", form);
            if (read_waits != ((form == 9) ? 0 : board_waits))
                $fatal(1, "fixture doubled/omitted read waits");
            if ((form == 9 && (writes != 1 || memory_value != 16'h7788)) ||
                (form == 11 && (writes != 1 || memory_value != 16'hf069)) ||
                ((form == 8 || form == 10) && (writes != 0 || memory_value != 16'ha5c3)) ||
                (form != 9 && published_operand != 16'ha5c3))
                $fatal(1, "fixture physical effect or operand signature mismatch");
            cases = cases + 1;
            if (accept_delay == 0 && (result_delay == 0 || result_delay == 80))
                $display("P06_FIXTURE_TRACE form=%0d board_waits=%0d delay=%0d base=%0d read_waits=%0d elapsed=%0d misses=%0d dep_blocks=%0d commands=%0d writes=%0d",
                    form, board_waits, result_delay, expected_minimum, read_waits,
                    retire_cpu - start_cpu, misses, dependency_blocks, commands, writes);
        end
    endtask

    integer f, w, a, d;
    initial begin
        for (f = 8; f < 12; f = f + 1)
            for (w = 0; w < 3; w = w + 1)
                for (a = 0; a < 2; a = a + 1)
                    for (d = 0; d < 3; d = d + 1)
                        run_case(f, w, a * 4, d == 0 ? 0 : (d == 1 ? 13 : 80));
        $display("P06_FIXTURE_PASS coupled_cases=%0d fabric_ticks=%0d", cases, ticks);
        $finish;
    end
endmodule
