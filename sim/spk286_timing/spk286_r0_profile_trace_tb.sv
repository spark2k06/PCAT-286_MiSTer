`timescale 1ns/1ps
// Passive timing diagnosis: unmodified production CPU/profile, ideal RAM.
// The image retains the complete assembled T286REF segment and its kernels.
// A reset-vector jump and an executable bootstrap replace DOS initialization.
module spk286_r0_profile_trace_tb;
    logic clk = 0;
    always #10 clk = ~clk;
    logic reset = 1;
    logic [2:0] requested;
    wire [2:0] active;
    wire pending, historical, phase_enable, phase_two, cpu_boundary;
    wire [23:0] address;
    wire [15:0] data_out;
    logic [15:0] data_in;
    wire data_oe, bus_valid, bus_write, bus_bhe_n, bus_lock, hlda;
    wire [3:0] bus_status;
    wire halted, shutdown, control_error, unsupported_opcode, microcode_fault;
    wire operand_blocked, event_completed, retired;
    wire [15:0] debug_cs, debug_ip, debug_flags, instruction_ip;
    wire [127:0] debug_gpr;
    logic [7:0] code [0:65535];
    logic [7:0] low_ram [0:65535];
    integer profile_arg, iterations, kernel_ip, kernel_length, trace_fd;
    integer cycle = 0, first_edge = -1, last_edge = -1, loops_retired = 0;
    integer kernel_retirements = 0, kernel_extensions = 0;
    logic in_kernel = 0;
    string image_path, trace_path, kind;

    spk286_at_cpu_profile u_profile (
        .clk, .reset, .requested, .active, .pending, .historical,
        .phase_enable, .phase_two, .cpu_boundary
    );
    spk286_machine_cpu u_cpu (
        .clk, .reset, .execute_enable(!reset), .historical_enable(historical),
        .cpu_boundary, .timing_read_wait_event(1'b0), .ready(bus_valid), .data_in,
        .intr(1'b0), .nmi(1'b0), .hold_request(1'b0), .address, .data_out,
        .data_oe, .bus_valid, .bus_write, .bus_bhe_n, .bus_status, .bus_lock, .hlda,
        .halted, .shutdown, .control_error, .unsupported_opcode, .microcode_fault,
        .operand_blocked, .event_completed, .debug_event_vector(), .debug_event_kind(),
        .debug_opcode(), .debug_cs, .debug_cs_base(), .debug_ip, .debug_flags, .debug_gpr,
        .debug_segment_selectors(), .debug_instruction_retired(retired),
        .debug_instruction_ip(instruction_ip), .fetch_blocked(), .debug_fetch_cursor(),
        .debug_micro_pc(), .debug_micro_entry(), .debug_micro_instruction(),
        .debug_micro_active(), .debug_prefetch_count(), .debug_bus_state(), .debug_biu_detail()
    );

    function automatic logic [7:0] memory_byte(input logic [23:0] location);
        if (location >= 24'h0106E0 && location < 24'h0206E0)
            memory_byte = code[16'(location - 24'h0106E0)];
        else if (location < 24'h010000)
            memory_byte = low_ram[location[15:0]];
        else case (location)
            24'hFFFFF0: memory_byte = 8'hEA;
            24'hFFFFF1: memory_byte = 8'h40;
            24'hFFFFF2: memory_byte = 8'h00;
            24'hFFFFF3: memory_byte = 8'h6E;
            24'hFFFFF4: memory_byte = 8'h10;
            default: memory_byte = 8'hF4;
        endcase
    endfunction
    // Supply ideal READY data half a fabric period before the sampling edge.
    // Clocked peer avoids enumerating 128 KiB in Icarus's sensitivity list.
    always @(negedge clk)
        data_in = {memory_byte({address[23:1],1'b1}),
                   memory_byte({address[23:1],1'b0})};

    always @(posedge clk) begin : observer
        integer expected_ax;
        if (!reset) begin
            cycle = cycle + 1;
            if (bus_valid && bus_write && address < 24'h010000) begin
                if (!address[0]) low_ram[address[15:0]] <= data_out[7:0];
                if (!bus_bhe_n) low_ram[{address[15:1],1'b1}] <= data_out[15:8];
            end
            if (u_cpu.cpu.opcode_start && debug_cs == 16'h106E &&
                debug_ip == 16'(kernel_ip) && first_edge < 0) begin
                first_edge = cycle;
                in_kernel = 1;
            end
            if (in_kernel && u_cpu.cpu.profile_retire_fire) begin
                kernel_retirements = kernel_retirements + 1;
                if (u_cpu.cpu.profile_implementation_extension)
                    kernel_extensions = kernel_extensions + 1;
                if (u_cpu.cpu.opcode_q == 8'hE2) begin
                    loops_retired = loops_retired + 1;
                    if (loops_retired == iterations) begin
                        last_edge = cycle;
                        in_kernel = 0;
                    end
                end
            end
            // All values are sampled BEFORE the edge updates sequential state.
            if (trace_fd != 0)
                $fdisplay(trace_fd, "%0d,%0d,%0d,%0d,%04h,%04h,%02h,%02h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h",
                    cycle, active, cpu_boundary, in_kernel, debug_cs, debug_ip,
                    u_cpu.cpu.opcode_q, u_cpu.cpu.queue_consume_data,
                    u_cpu.cpu.opcode_start, u_cpu.cpu.profile_start_interval,
                    u_cpu.cpu.profile_start_body, u_cpu.cpu.profile_metadata_valid,
                    u_cpu.cpu.profile_metadata_clocks, u_cpu.cpu.profile_body_active,
                    u_cpu.cpu.profile_head_permit, u_cpu.cpu.profile_deadline_ready,
                    u_cpu.cpu.raw_retired, u_cpu.cpu.profile_retire_pending,
                    u_cpu.cpu.profile_retire_fire, u_cpu.cpu.profile_elapsed,
                    u_cpu.cpu.profile_scheduled, u_cpu.cpu.profile_implementation_extension,
                    u_cpu.cpu.queue_count, u_cpu.cpu.queue_consume_valid,
                    u_cpu.cpu.queue_consume_ready, bus_valid, bus_status, address,
                    bus_write, bus_valid, u_cpu.cpu.fetch_bus_valid,
                    u_cpu.cpu.fetch_bus_ready, u_cpu.cpu.fetch_response_valid,
                    u_cpu.cpu.fetch_response_ready, u_cpu.cpu.timing_prefetch_response_accept,
                    debug_gpr);
            if (shutdown || unsupported_opcode || microcode_fault || control_error)
                $fatal(1, "Production CPU rejected original R0/baseline program");
            if (halted) begin
                if (first_edge < 0 || last_edge < 0 || loops_retired != iterations)
                    $fatal(1, "Kernel did not execute complete fixed work");
                expected_ax = kind == "r0" ?
                    (16'h1234 + iterations * 16'h5678 + iterations * (iterations - 1) / 2) & 65535 : 16'h1234;
                if (debug_gpr[15:0] !== 16'(expected_ax) || debug_gpr[31:16] !== 0 ||
                    debug_gpr[47:32] !== 16'h9ABC ||
                    debug_gpr[63:48] !== 16'(16'h5678 + (kind == "r0" ? iterations : 0)) ||
                    debug_gpr[127:112] !== 16'hDEF0)
                    $fatal(1, "Original kernel architectural signature failed");
                $display("P06_R0_IDEAL_PASS profile=%0d kind=%s iterations=%0d start=%0d end=%0d fabric_clocks=%0d instructions=%0d extensions=%0d kernel_ip=%04h kernel_length=%0d", active, kind, iterations, first_edge, last_edge, last_edge-first_edge, kernel_retirements, kernel_extensions, 16'(kernel_ip), kernel_length);
                $fclose(trace_fd); $finish;
            end
            if (cycle > 500000) $fatal(1, "Bounded ideal-RAM watchdog");
        end
    end

    initial begin
        if (!$value$plusargs("PROFILE=%d", profile_arg) ||
            !$value$plusargs("LOOPS=%d", iterations) ||
            !$value$plusargs("KERNEL_IP=%d", kernel_ip) ||
            !$value$plusargs("KERNEL_LENGTH=%d", kernel_length) ||
            !$value$plusargs("KIND=%s", kind) ||
            !$value$plusargs("IMAGE=%s", image_path) ||
            !$value$plusargs("TRACE=%s", trace_path)) $fatal(1, "Missing trace arguments");
        if ((profile_arg != 6 && profile_arg != 7) ||
            (iterations != 32 && iterations != 256) || (kind != "r0" && kind != "baseline"))
            $fatal(1, "Out-of-scope trace arguments");
        requested = 3'(profile_arg);
        for (integer i = 0; i < 65536; i = i + 1) begin code[i] = 8'hF4; low_ram[i] = 0; end
        $readmemh(image_path, code);
        trace_fd = $fopen(trace_path, "w");
        if (trace_fd == 0) $fatal(1, "Cannot open trace");
        $fdisplay(trace_fd, "edge,profile,cpu_boundary,in_kernel,cs,ip,opcode,queue_byte,opcode_start,start_interval,start_body,metadata_valid,metadata_clocks,body_active,head_permit,deadline_ready,raw_retired,retire_pending,retire_fire,elapsed,scheduled,implementation_extension,queue_count,consume_valid,consume_ready,bus_valid,bus_status,address,write,ready,fetch_valid,fetch_ready,fetch_response_valid,fetch_response_ready,refill_accept,gpr");
        repeat(5) @(negedge clk);
        reset = 0;
    end
    initial begin #11_000_000; $fatal(1, "Ideal trace timeout"); end
endmodule
