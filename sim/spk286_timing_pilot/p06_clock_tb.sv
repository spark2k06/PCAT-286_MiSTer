`timescale 1ns/1ps
module p06_clock_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    wire phase_enable, phase_two, cpu_enable;
    wire max_phase_enable, max_phase_two, max_cpu_enable;
    integer fabric_edges = 0, phases = 0, cpu_edges = 0;
    integer previous_phase_count = 0, previous_cpu_count = 0;
    integer last_cpu_edge = 0;
    integer checks = 0;

    p06_clock dut (.*);
    p06_clock #(.HISTORICAL(1'b0)) maximum (
        .clk(clk), .reset(reset), .phase_enable(max_phase_enable),
        .phase_two(max_phase_two), .cpu_enable(max_cpu_enable)
    );

    task automatic step;
        integer expected_phase_count, expected_cpu_count, interval;
        begin
            #9;
            if (reset) begin
                if ({phase_enable, phase_two, cpu_enable, max_cpu_enable} !== 4'b0)
                    $fatal(1, "enable escaped reset");
                fabric_edges = 0; phases = 0; cpu_edges = 0;
                previous_phase_count = 0; previous_cpu_count = 0;
                last_cpu_edge = 0;
            end else begin
                fabric_edges = fabric_edges + 1;
                // Independent rational reference, not DUT accumulator state.
                expected_phase_count = (fabric_edges * 12) / 50;
                expected_cpu_count = (fabric_edges * 6) / 50;
                if (phase_enable !== (expected_phase_count != previous_phase_count) ||
                    cpu_enable !== (expected_cpu_count != previous_cpu_count) ||
                    phase_two !== cpu_enable)
                    $fatal(1, "rational enable mismatch at edge %0d", fabric_edges);
                if (phase_enable) begin
                    phases = phases + 1;
                    if (6 * fabric_edges - 25 * phases < 0 ||
                        6 * fabric_edges - 25 * phases >= 6)
                        $fatal(1, "phase quantization exceeded one fabric edge");
                end
                if (cpu_enable) begin
                    cpu_edges = cpu_edges + 1;
                    interval = fabric_edges - last_cpu_edge;
                    if (interval != ((cpu_edges % 3 == 1) ? 9 : 8))
                        $fatal(1, "processor interval mismatch");
                    if (3 * fabric_edges - 25 * cpu_edges < 0 ||
                        3 * fabric_edges - 25 * cpu_edges >= 3)
                        $fatal(1, "CPU quantization exceeded one fabric edge");
                    last_cpu_edge = fabric_edges;
                end
                previous_phase_count = expected_phase_count;
                previous_cpu_count = expected_cpu_count;
                if (max_cpu_enable !== 1'b1 || max_phase_enable !== 1'b0 ||
                    max_phase_two !== 1'b0)
                    $fatal(1, "MAX bypass changed");
                checks = checks + 1;
            end
            #1; clk = 1'b1;
            #10; clk = 1'b0;
        end
    endtask

    initial begin
        step(); reset = 1'b0;
        repeat (250000) step();
        if (phases != 60000 || cpu_edges != 30000)
            $fatal(1, "long-run clock count mismatch");
        $display("P06_CLOCK_LONG_RUN edges=%0d phases=%0d cpu=%0d", fabric_edges, phases, cpu_edges);
        // Reset at every point of the 25-edge repeating phase pattern.
        for (integer offset = 0; offset < 25; offset = offset + 1) begin
            reset = 1'b1; step(); reset = 1'b0;
            repeat (offset) step();
            reset = 1'b1; step(); reset = 1'b0;
            repeat (250) step();
            if (phases != 60 || cpu_edges != 30)
                $fatal(1, "restart phase mismatch at offset %0d", offset);
        end
        $display("P06_CLOCK_PASS checks=%0d reset_offsets=25", checks);
        $finish;
    end
endmodule
