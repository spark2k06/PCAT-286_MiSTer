`timescale 1ns/1ps
module p06_instruction_duration_tb;
    logic clk = 0, reset = 1, cancel = 0;
    wire phase_enable, phase_two, cpu_boundary;
    logic start_valid = 0;
    wire start_ready;
    logic [3:0] instruction_form = 0, next_length = 0;
    logic real_mode = 1, prefix_free = 1, taken = 0, branch_outcome_known = 1;
    logic target_length_known = 1, operand_odd = 0, ea_base_index_disp = 0;
    logic read_wait_event = 0, functional_done = 1, dependencies_ready = 1, retire_ready = 1;
    wire retire_enable, dependency_blocked, consumer_blocked;
    wire metadata_qualified, metadata_error, timing_error, active;
    wire [5:0] minimum_clocks;
    wire [7:0] elapsed_clocks, scheduled_clocks;
    p06_clock timing (.clk, .reset, .phase_enable, .phase_two, .cpu_enable(cpu_boundary));
    p06_instruction_duration dut (.*);
    wire max_start, max_retire, max_dep, max_consumer, max_qualified, max_meta_error;
    wire max_error, max_active;
    wire [5:0] max_minimum;
    wire [7:0] max_elapsed, max_scheduled;
    p06_instruction_duration #(.HISTORICAL(0)) maximum (
        .clk, .reset, .cancel, .cpu_boundary, .start_valid, .start_ready(max_start),
        .instruction_form, .real_mode, .prefix_free, .taken, .branch_outcome_known,
        .target_length_known, .next_length, .operand_odd, .ea_base_index_disp,
        .read_wait_event, .functional_done, .dependencies_ready, .retire_ready,
        .retire_enable(max_retire), .dependency_blocked(max_dep),
        .consumer_blocked(max_consumer), .metadata_qualified(max_qualified),
        .metadata_error(max_meta_error), .timing_error(max_error), .active(max_active),
        .minimum_clocks(max_minimum), .elapsed_clocks(max_elapsed),
        .scheduled_clocks(max_scheduled)
    );
    integer metadata_checks = 0, duration_cases = 0, ticks = 0;
    integer fabric = 0, cpu_count = 0, starts = 0, retirements = 0;
    integer start_cpu = 0, retire_cpu = 0, waits = 0, dep_blocks = 0, consumer_blocks = 0;
    integer expected_budget = 0;
    bit observe_duration = 0;

    // Independent oracle transcribed from the qualified Intel rows; -1 rejects.
    // It does not inspect DUT internals or use DUT output as an expected budget.
    function automatic integer reference_cost;
        integer b, alignment;
        bit mem;
        begin
            b = -1; alignment = 0; mem = 0;
            case (instruction_form)
                0, 1, 2: b = 2;
                3, 4: b = 3;
                5: b = taken ? 7 : 3;
                6: b = 7;
                7: b = taken ? 8 : 4;
                8: begin b = 5; mem = 1; end
                9: begin b = 3; mem = 1; end
                10, 11: begin b = 7; mem = 1; end
                default: b = -1;
            endcase
            if (!real_mode || !prefix_free ||
                ((instruction_form == 5 || instruction_form == 7) && !branch_outcome_known) ||
                (!mem && (operand_odd || ea_base_index_disp)) ||
                (ea_base_index_disp && instruction_form != 10 && instruction_form != 11))
                b = -1;
            if (b >= 0 && (instruction_form == 6 || (instruction_form == 5 && taken))) begin
                if (!target_length_known || next_length == 0 || next_length > 6)
                    b = -1;
                else b = b + int'(next_length);
            end
            if (mem && operand_odd) alignment = instruction_form == 11 ? 4 : 2;
            reference_cost = b < 0 ? -1 : b + alignment + int'(mem && ea_base_index_disp);
        end
    endfunction

    task automatic check_metadata;
        integer cost;
        begin
            #1; cost = reference_cost(); metadata_checks = metadata_checks + 1;
            if (metadata_qualified !== (cost >= 0) ||
                minimum_clocks !== 6'((cost >= 0) ? cost : 0))
                $fatal(1, "Intel metadata mismatch form=%0d got=%0d expected=%0d",
                       instruction_form, minimum_clocks, cost);
        end
    endtask

    task automatic tick;
        bit expected_permission;
        integer instruction_age;
        begin
            #9; ticks = ticks + 1;
            if (max_start !== (!reset && !cancel) ||
                max_retire !== (!reset && !cancel && functional_done && dependencies_ready) ||
                !max_qualified || {max_dep, max_consumer, max_meta_error, max_error,
                max_active, max_minimum, max_elapsed, max_scheduled} !== 27'd0)
                $fatal(1, "MAX duration bypass mismatch");
            if (!reset) begin
                fabric = fabric + 1;
                if (cpu_boundary) cpu_count = cpu_count + 1;
                if (observe_duration && starts != 0 && read_wait_event && cpu_boundary)
                    waits = waits + 1;
                if (observe_duration && starts != 0) begin
                    instruction_age = cpu_count - start_cpu;
                    expected_permission = !cancel && cpu_boundary &&
                        instruction_age >= expected_budget + waits && functional_done && dependencies_ready;
                    if (retire_enable !== expected_permission)
                        $fatal(1, "instruction duration mismatch age=%0d base=%0d waits=%0d",
                               instruction_age, expected_budget, waits);
                end
                if (start_valid && start_ready) begin
                    starts = starts + 1; start_cpu = cpu_count;
                end
                if (dependency_blocked) dep_blocks = dep_blocks + 1;
                if (consumer_blocked) consumer_blocks = consumer_blocks + 1;
                if (retire_enable && retire_ready) begin
                    retirements = retirements + 1; retire_cpu = cpu_count;
                end
            end
            #1; clk = 1; #10; clk = 0;
        end
    endtask

    task automatic restart;
        begin
            observe_duration = 0; reset = 1; cancel = 0; start_valid = 0;
            read_wait_event = 0; functional_done = 1; dependencies_ready = 1;
            retire_ready = 1; real_mode = 1; prefix_free = 1; operand_odd = 0;
            ea_base_index_disp = 0; branch_outcome_known = 1; target_length_known = 1;
            tick(); reset = 0;
            fabric = 0; cpu_count = 0; starts = 0; retirements = 0;
            start_cpu = 0; retire_cpu = 0; waits = 0; dep_blocks = 0; consumer_blocks = 0;
        end
    endtask

    task automatic duration(input integer form, target_bytes, extra_read_waits,
                            late_result_edges, late_consumer_edges,
                            input bit branch_taken, odd, complex_ea);
        integer loops, next_edge, minimum_edge, result_edge, consumer_edge;
        begin
            restart(); duration_cases = duration_cases + 1;
            instruction_form = 4'(form); next_length = 4'(target_bytes); taken = branch_taken;
            operand_odd = odd; ea_base_index_disp = complex_ea;
            check_metadata(); expected_budget = reference_cost();
            if (expected_budget < 0) $fatal(1, "invalid duration case");
            start_valid = 1; observe_duration = 1; loops = 0;
            while (retirements == 0 && loops < 500) begin
                next_edge = fabric + 1;
                if (starts != 0) begin
                    read_wait_event = cpu_boundary && cpu_count - start_cpu < extra_read_waits;
                    minimum_edge = (25 * (start_cpu + expected_budget + extra_read_waits) + 2) / 3;
                    result_edge = minimum_edge + late_result_edges;
                    consumer_edge = result_edge + late_consumer_edges;
                    functional_done = next_edge >= result_edge;
                    dependencies_ready = next_edge >= result_edge;
                    retire_ready = next_edge >= consumer_edge;
                end
                tick(); loops = loops + 1;
                if (starts != 0) begin
                    start_valid = 0;
                    // Decode inputs may move on; active instruction metadata is retained.
                    instruction_form = 15; next_length = 0; operand_odd = 0; ea_base_index_disp = 0;
                end
            end
            observe_duration = 0; read_wait_event = 0;
            if (starts != 1 || retirements != 1 || active || timing_error ||
                waits != extra_read_waits || (dep_blocks != 0) != (late_result_edges > 0) ||
                (consumer_blocks != 0) != (late_consumer_edges > 0))
                $fatal(1, "duration/dependency count mismatch case=%0d", duration_cases);
            if (late_result_edges == 0 && late_consumer_edges == 0 &&
                retire_cpu - start_cpu != expected_budget + extra_read_waits)
                $fatal(1, "extra hidden duration delay");
            if (duration_cases < 6 || extra_read_waits == 2 || late_result_edges > 0)
                $display("P06_DURATION_TRACE form=%0d base=%0d read_waits=%0d elapsed=%0d dep_blocks=%0d consumer_blocks=%0d",
                    form, expected_budget, waits, retire_cpu - start_cpu, dep_blocks, consumer_blocks);
        end
    endtask

    task automatic admit(input integer form);
        integer n;
        begin
            instruction_form = 4'(form); start_valid = 1;
            for (n = 0; n < 9; n = n + 1) tick();
            start_valid = 0;
            if (starts != 1 || !active) $fatal(1, "duration admission failed");
        end
    endtask

    integer f, t, k, n, p, r, o, e, b, controls, q;
    initial begin
        // Exhaust metadata dimensions, including all unsupported form encodings.
        for (f = 0; f < 16; f = f + 1)
          for (t = 0; t < 2; t = t + 1)
           for (k = 0; k < 2; k = k + 1)
            for (n = 0; n < 8; n = n + 1)
             for (p = 0; p < 2; p = p + 1)
              for (r = 0; r < 2; r = r + 1)
               for (o = 0; o < 2; o = o + 1)
                for (e = 0; e < 2; e = e + 1)
                 for (b = 0; b < 2; b = b + 1) begin
                    instruction_form = 4'(f); taken = t != 0;
                    target_length_known = k != 0; next_length = 4'(n);
                    prefix_free = p != 0; real_mode = r != 0; operand_odd = o != 0;
                    ea_base_index_disp = e != 0; branch_outcome_known = b != 0;
                    check_metadata();
                 end
        for (f = 0; f < 12; f = f + 1) begin
            duration(f, 2, 0, 0, 0, 0, 0, 0);
            if (f == 5 || f == 6 || f == 7) begin
                for (n = 1; n <= 6; n = n + 1)
                    duration(f, n, 0, 0, 0, 1, 0, 0);
            end
            if (f >= 8) begin
                duration(f, 2, 0, 0, 0, 0, 1, f >= 10);
                if (f != 9) begin
                    duration(f, 2, 1, 0, 0, 0, 0, 0);
                    duration(f, 2, 2, 0, 0, 0, 1, f >= 10);
                end
            end
            duration(f, 2, 0, 13, 0, 0, 0, 0);
            duration(f, 2, 0, 0, 13, 0, 0, 0);
        end
        // Unsupported metadata cannot start with a silent zero-clock default.
        restart(); instruction_form = 15; start_valid = 1;
        while (fabric < 8) tick();
        #1;
        if (!metadata_error || start_ready) $fatal(1, "unsupported row was not rejected");
        tick(); if (active || starts != 0) $fatal(1, "unsupported row became active");
        // Consecutive starts may share an architectural completion boundary.
        restart(); admit(0); instruction_form = 3; start_valid = 1;
        while (retirements == 0) tick();
        start_valid = 0;
        if (starts != 2 || !active || elapsed_clocks != 0 || scheduled_clocks != 3)
            $fatal(1, "back-to-back instruction lost or mandatory bubble inserted");
        while (retirements < 2) tick();
        // Cancel at the eligible boundary suppresses publication and resets context.
        restart(); admit(0); while (fabric < 24) tick();
        cancel = 1; tick(); cancel = 0; tick();
        if (active || retirements != 0 || timing_error) $fatal(1, "duration cancellation failed");
        // Functional completion and data availability are independent dependencies.
        restart(); admit(0); functional_done = 0; dependencies_ready = 1;
        while (cpu_count < 5) tick();
        if (retirements != 0 || dep_blocks != 3 || timing_error)
            $fatal(1, "functional completion dependency bypassed");
        functional_done = 1; while (retirements == 0) tick();
        // Wait events must correspond to an active read and a logical boundary.
        restart(); admit(9); while (fabric < 16) tick();
        read_wait_event = 1; tick(); read_wait_event = 0;
        if (!timing_error || retire_enable) $fatal(1, "write/fetch wait accepted as a read wait");
        restart(); admit(8); read_wait_event = 1; tick(); read_wait_event = 0;
        if (!timing_error) $fatal(1, "off-boundary read wait accepted");
        // Bounded fixture rejects budget overflow rather than wrapping.
        restart(); admit(8); dependencies_ready = 0;
        while (!timing_error && cpu_count < 270) begin
            read_wait_event = cpu_boundary; tick();
        end
        read_wait_event = 0; dependencies_ready = 1; tick();
        if (!timing_error || scheduled_clocks != 255 || retirements != 0)
            $fatal(1, "budget overflow wrapped or committed");
        // Long functional stalls saturate elapsed time without wrapping.
        restart(); admit(0); dependencies_ready = 0;
        while (cpu_count < 300) tick();
        if (elapsed_clocks != 255 || timing_error) $fatal(1, "elapsed saturation failed");
        dependencies_ready = 1; while (retirements == 0) tick();
        // Exhaust independent functional-owner MAX inputs.
        for (controls = 0; controls < 64; controls = controls + 1) begin
            reset = (controls & 1) != 0; cancel = (controls & 2) != 0;
            start_valid = (controls & 4) != 0;
            functional_done = (controls & 8) != 0;
            dependencies_ready = (controls & 16) != 0;
            retire_ready = (controls & 32) != 0; tick();
        end
        q = metadata_checks;
        $display("P06_DURATION_PASS metadata=%0d duration_cases=%0d fabric_ticks=%0d MAX=64",
                 q, duration_cases, ticks);
        $finish;
    end
endmodule
