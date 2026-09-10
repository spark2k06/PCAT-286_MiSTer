`timescale 1ns/1ps

module spk286_diagnostic_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;

    logic cpu_ready;
    logic [15:0] cpu_data_in;
    logic [23:0] cpu_address;
    logic [15:0] cpu_data_out;
    logic cpu_data_oe, cpu_bus_valid, cpu_bus_write, cpu_bus_bhe_n;
    logic [3:0] cpu_bus_status;
    logic cpu_bus_lock, cpu_hlda;
    logic halted, shutdown, control_error, unsupported_opcode;
    logic microcode_fault, operand_blocked, event_completed;
    logic [7:0] debug_event_vector, debug_opcode;
    logic [2:0] debug_event_kind;
    logic [15:0] debug_cs, debug_ip, debug_flags;
    logic [23:0] debug_cs_base;
    logic [127:0] debug_gpr;
    logic [11:0] debug_micro_pc;
    logic [3:0] debug_bus_state;

    logic xt_cycle_active;
    logic xt_ready = 1'b0;
    logic [7:0] xt_data_in;
    logic xt_valid;
    logic [19:0] xt_address;
    logic [7:0] xt_data_out;
    logic [2:0] xt_status;
    logic xt_write, xt_io, xt_inta, xt_code, xt_byte_high;
    logic xt_memory_projection, xt_lock_n, xt_accepted;
    logic bridge_idle, protocol_error;

    // A tag/value store models the small set of RAM bytes touched by the ROM.
    // This keeps the whole-CPU bench portable without expanding a 1 MiB array
    // into simulator logic. Unwritten locations read as zero.
    logic [19:0] ram_tag [0:255];
    logic [7:0] ram_value [0:255];
    logic ram_valid [0:255];
    logic [7:0] milestones [0:15];
    logic backend_active = 1'b0;
    integer wait_remaining = 0;
    integer accepted_beats = 0;
    integer memory_write_beats = 0;
    integer io_read_beats = 0;
    integer io_write_beats = 0;
    integer rom_write_attempts = 0;
    integer milestone_count = 0;
    integer failure_count = 0;
    logic [7:0] failure_code = 8'd0;
    logic saw_native_reset = 1'b0;
    logic saw_reset_projection = 1'b0;
    logic saw_far_target = 1'b0;
    logic saw_cs_reload = 1'b0;

    integer index;
    integer next_ram_slot = 0;
    integer write_index;
    integer selected_slot;
    always #5 clk = ~clk;
    assign xt_cycle_active = xt_valid;

`include "tests/firmware/pcat286_diag_rom_case.svh"

    function automatic logic [7:0] sparse_ram_read(input logic [19:0] address);
        integer read_index;
        begin
            sparse_ram_read = 8'h00;
            for (read_index = 0; read_index < 256; read_index = read_index + 1)
                if (ram_valid[read_index] && (ram_tag[read_index] == address))
                    sparse_ram_read = ram_value[read_index];
        end
    endfunction

    initial begin
        for (index = 0; index < 256; index = index + 1) begin
            ram_valid[index] = 1'b0;
            ram_tag[index] = 20'd0;
            ram_value[index] = 8'd0;
        end
        for (index = 0; index < 16; index = index + 1)
            milestones[index] = 8'h00;
        ram_valid[0] = 1'b1;
        ram_tag[0] = 20'h104f0;
        ram_value[0] = 8'haa;
        ram_valid[1] = 1'b1;
        ram_tag[1] = 20'h10510;
        ram_value[1] = 8'h55;
        next_ram_slot = 2;
    end

    always_comb begin
        if (xt_inta)
            xt_data_in = 8'hff;
        else if (xt_io)
            xt_data_in = (xt_address[15:0] == 16'h0060) ? 8'ha6 : 8'hff;
        else if (xt_address >= 20'hf0000)
            xt_data_in = diagnostic_rom_read(xt_address[15:0]);
        else
            xt_data_in = sparse_ram_read(xt_address);
    end

    // Deterministic 0..2-cycle waits. A side effect occurs only on the one
    // accepted cycle, even though READY remains asserted until the bridge exits.
    always_ff @(posedge clk) begin
        if (reset) begin
            backend_active <= 1'b0;
            wait_remaining <= 0;
            xt_ready <= 1'b0;
        end else if (!xt_valid) begin
            backend_active <= 1'b0;
            wait_remaining <= 0;
            xt_ready <= 1'b0;
        end else if (!backend_active) begin
            backend_active <= 1'b1;
            wait_remaining <= (xt_address[1:0] + accepted_beats) % 3;
            xt_ready <= 1'b0;
        end else if (wait_remaining != 0) begin
            wait_remaining <= wait_remaining - 1;
            xt_ready <= 1'b0;
        end else begin
            xt_ready <= 1'b1;
        end

        if (!reset && xt_accepted) begin
            accepted_beats <= accepted_beats + 1;
            if (xt_inta) begin
                // No INTA is expected until the event-focused I4 diagnostic.
            end else if (xt_io) begin
                if (xt_write) begin
                    io_write_beats <= io_write_beats + 1;
                    if (xt_address[15:0] == 16'h0080) begin
                        if (milestone_count < 16)
                            milestones[milestone_count] <= xt_data_out;
                        milestone_count <= milestone_count + 1;
                    end else if (xt_address[15:0] == 16'h0081) begin
                        failure_code <= xt_data_out;
                        failure_count <= failure_count + 1;
                    end
                end else begin
                    io_read_beats <= io_read_beats + 1;
                end
            end else if (xt_write) begin
                memory_write_beats <= memory_write_beats + 1;
                if (xt_address >= 20'hf0000)
                    rom_write_attempts <= rom_write_attempts + 1;
                else begin
                    selected_slot = -1;
                    for (write_index = 0; write_index < 256; write_index = write_index + 1)
                        if (ram_valid[write_index] &&
                            (ram_tag[write_index] == xt_address))
                            selected_slot = write_index;
                    if (selected_slot >= 0) begin
                        ram_value[selected_slot] <= xt_data_out;
                    end else if (next_ram_slot < 256) begin
                        ram_valid[next_ram_slot] <= 1'b1;
                        ram_tag[next_ram_slot] <= xt_address;
                        ram_value[next_ram_slot] <= xt_data_out;
                        next_ram_slot <= next_ram_slot + 1;
                    end else begin
                        $fatal(1, "sparse RAM capacity exceeded");
                    end
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!reset) begin
            if (!saw_native_reset && cpu_bus_valid) begin
                saw_native_reset <= (cpu_address == 24'hfffff0) &&
                                    (cpu_bus_status == 4'hd) &&
                                    (debug_cs == 16'hf000) &&
                                    (debug_cs_base == 24'hff0000) &&
                                    (debug_ip == 16'hfff0);
            end
            if (xt_valid && xt_code && (xt_address == 20'hffff0) &&
                xt_memory_projection)
                saw_reset_projection <= 1'b1;
            if (cpu_bus_valid && (cpu_bus_status == 4'hd) &&
                (cpu_address == 24'h0f0000))
                saw_far_target <= 1'b1;
            if ((debug_cs == 16'hf000) &&
                (debug_cs_base == 24'h0f0000) && (debug_ip < 16'h0100))
                saw_cs_reload <= 1'b1;
        end
    end

    spk286_machine_cpu cpu (
        .clk(clk), .reset(reset), .execute_enable(1'b1),
        .ready(cpu_ready), .data_in(cpu_data_in),
        .intr(1'b0), .nmi(1'b0), .hold_request(1'b0),
        .address(cpu_address), .data_out(cpu_data_out),
        .data_oe(cpu_data_oe), .bus_valid(cpu_bus_valid),
        .bus_write(cpu_bus_write), .bus_bhe_n(cpu_bus_bhe_n),
        .bus_status(cpu_bus_status), .bus_lock(cpu_bus_lock), .hlda(cpu_hlda),
        .halted(halted), .shutdown(shutdown),
        .control_error(control_error), .unsupported_opcode(unsupported_opcode),
        .microcode_fault(microcode_fault), .operand_blocked(operand_blocked),
        .event_completed(event_completed),
        .debug_event_vector(debug_event_vector), .debug_event_kind(debug_event_kind),
        .debug_opcode(debug_opcode), .debug_cs(debug_cs),
        .debug_cs_base(debug_cs_base), .debug_ip(debug_ip),
        .debug_flags(debug_flags), .debug_gpr(debug_gpr),
        .debug_micro_pc(debug_micro_pc), .debug_bus_state(debug_bus_state)
    );

    spk286_xt_bridge bridge (
        .clk(clk), .reset(reset),
        .cpu_bus_valid(cpu_bus_valid), .cpu_address(cpu_address),
        .cpu_data_out(cpu_data_out), .cpu_data_oe(cpu_data_oe),
        .cpu_bus_write(cpu_bus_write), .cpu_bus_bhe_n(cpu_bus_bhe_n),
        .cpu_bus_status(cpu_bus_status), .cpu_bus_lock(cpu_bus_lock),
        .cpu_ready(cpu_ready), .cpu_data_in(cpu_data_in),
        .xt_start(1'b1), .xt_sample(1'b1),
        .xt_cycle_active(xt_cycle_active),
        .xt_ready(xt_ready), .xt_data_in(xt_data_in),
        .xt_valid(xt_valid), .xt_address(xt_address),
        .xt_data_out(xt_data_out), .xt_status(xt_status),
        .xt_write(xt_write), .xt_io(xt_io), .xt_inta(xt_inta),
        .xt_code(xt_code), .xt_byte_high(xt_byte_high),
        .xt_memory_projection(xt_memory_projection), .xt_lock_n(xt_lock_n),
        .xt_accepted(xt_accepted),
        .bridge_idle(bridge_idle), .protocol_error(protocol_error)
    );

    initial begin : test
        integer cycles;
        repeat (6) @(posedge clk);
        reset = 1'b0;

        for (cycles = 0; cycles < 500000; cycles = cycles + 1) begin
            @(negedge clk);
            if (control_error || unsupported_opcode || microcode_fault ||
                operand_blocked || shutdown || protocol_error)
                $fatal(1,
                    "CPU/bridge diagnostic error cycle=%0d ip=%h opcode=%h micro_pc=%h flags=%h",
                    cycles, debug_ip, debug_opcode, debug_micro_pc, debug_flags);
            if (failure_count != 0)
                $fatal(1, "diagnostic failure code=%h ip=%h", failure_code, debug_ip);
            if (halted && milestone_count < 6)
                $fatal(1, "HLT without complete signature ip=%h milestones=%0d", debug_ip, milestone_count);
            if (halted && milestone_count == 6)
                cycles = 500000;
        end

        if (!halted || milestone_count != 6)
            $fatal(1, "diagnostic deadline expired ip=%h milestones=%0d beats=%0d", debug_ip, milestone_count, accepted_beats);
        if (milestones[0] !== 8'h10 || milestones[1] !== 8'h20 ||
            milestones[2] !== 8'h30 || milestones[3] !== 8'h40 ||
            milestones[4] !== 8'h50 || milestones[5] !== 8'h86)
            $fatal(1, "wrong diagnostic milestone sequence");
        if ({sparse_ram_read(20'h10501), sparse_ram_read(20'h10500)} !== 16'h2860 ||
            {sparse_ram_read(20'h10503), sparse_ram_read(20'h10502)} !== 16'h5a3c)
            $fatal(1, "memory signature mismatch");
        if (sparse_ram_read(20'h104f0) !== 8'haa ||
            sparse_ram_read(20'h10510) !== 8'h55)
            $fatal(1, "signature guard region changed");
        if ({sparse_ram_read(20'h10321), sparse_ram_read(20'h10320)} !== 16'h1234 ||
            {sparse_ram_read(20'h10323), sparse_ram_read(20'h10322)} !== 16'habcd)
            $fatal(1, "REP MOVSB transform mismatch");
        if ({sparse_ram_read(20'h1fee1), sparse_ram_read(20'h1fee0)} !== 16'hcafe)
            $fatal(1, "stack guard mismatch");
        if (diagnostic_rom_read(16'h8000) !== 8'hff || rom_write_attempts != 1)
            $fatal(1, "ROM protection was not exercised exactly once");
        if (!saw_native_reset || !saw_reset_projection ||
            !saw_far_target || !saw_cs_reload)
            $fatal(1, "reset/far-transfer observations incomplete native=%b projection=%b target=%b reload=%b",
                   saw_native_reset, saw_reset_projection, saw_far_target, saw_cs_reload);
        if (io_read_beats != 1 || io_write_beats != 6)
            $fatal(1, "I/O transaction counts mismatch reads=%0d writes=%0d", io_read_beats, io_write_beats);

        $display("I3_DIAGNOSTIC_PASS beats=%0d memory_writes=%0d io_reads=%0d io_writes=%0d rom_blocked=%0d",
                 accepted_beats, memory_write_beats, io_read_beats,
                 io_write_beats, rom_write_attempts);
        $finish;
    end
endmodule
