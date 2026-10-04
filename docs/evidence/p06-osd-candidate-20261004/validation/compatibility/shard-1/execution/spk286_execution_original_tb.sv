`timescale 1ns/1ps

module spk286_execution_tb;
    `include "spk286_signals.svh"

    // PRE-edge physical command/input snapshot; POST-edge architectural state.
    // This observer cannot drive any CPU input or modify a fixture expectation.
    integer p06_observer_fd = 0, p06_observer_edge = 0;
    string p06_observer_path;
    logic [23:0] p06_pre_address;
    logic [15:0] p06_pre_data_out, p06_pre_data_in;
    logic [3:0] p06_pre_status;
    logic p06_pre_bus, p06_pre_write, p06_pre_bhe, p06_pre_lock, p06_pre_hlda;
    logic p06_pre_reset, p06_pre_execute, p06_pre_ready, p06_pre_intr, p06_pre_nmi;
    logic p06_pre_hold, p06_pre_redirect;
    // Uninitialized fixture memory has four states in Icarus and two states
    // in the other simulator. Canonicalize only the observed INPUT, never the stimulus or
    // any architectural output. Preserve every defined input bit.
    function automatic logic [15:0] p06_observed_input(input logic [15:0] value);
        for (integer bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
            p06_observed_input[bit_index] = value[bit_index] === 1'b1;
    endfunction
    function automatic logic [15:0] p06_input_unknown_mask(input logic [15:0] value);
        for (integer bit_index = 0; bit_index < 16; bit_index = bit_index + 1)
            case (value[bit_index])
                1'b0, 1'b1: p06_input_unknown_mask[bit_index] = 1'b0;
                default: p06_input_unknown_mask[bit_index] = 1'b1;
            endcase
    endfunction
    initial begin
        if ($value$plusargs("profile_trace=%s", p06_observer_path)) begin
            p06_observer_fd = $fopen(p06_observer_path, "w");
            if (p06_observer_fd == 0) $fatal(1, "cannot open profile compatibility trace");
            $fdisplay(p06_observer_fd, "edge,reset,execute,ready,intr,nmi,hold,redirect,bus,address,status,write,bhe,dataout,datain,lock,hlda,gpr,flags,cs,csbase,ip,halted,shutdown,retired,event,eventkind,eventvector,nmi_pending,nmi_blocked,sti_shadow,unsupported,control_error,microcode_fault,operand_blocked,prefetch,micro_active,micro_pc,datain_two_state,datain_unknown_mask");
        end
    end
    always @(posedge clk) begin
        p06_observer_edge = p06_observer_edge + 1;
        p06_pre_reset = reset; p06_pre_execute = execute_enable;
        p06_pre_ready = ready; p06_pre_intr = intr; p06_pre_nmi = nmi;
        p06_pre_hold = hold_request; p06_pre_redirect = redirect;
        p06_pre_bus = bus_valid; p06_pre_address = address;
        p06_pre_status = bus_status; p06_pre_write = bus_write; p06_pre_bhe = bus_bhe_n;
        p06_pre_data_out = data_out; p06_pre_data_in = data_in;
        p06_pre_lock = bus_lock; p06_pre_hlda = hlda;
        #1;
        if (p06_observer_fd != 0)
            $fdisplay(p06_observer_fd, "%0d,%b,%b,%b,%b,%b,%b,%b,%b,%06h,%h,%b,%b,%04h,%04h,%b,%b,%032h,%04h,%04h,%06h,%04h,%b,%b,%b,%b,%0d,%0d,%b,%b,%b,%b,%b,%b,%b,%0d,%b,%03h,%04h,%04h",
                p06_observer_edge, p06_pre_reset, p06_pre_execute, p06_pre_ready,
                p06_pre_intr, p06_pre_nmi, p06_pre_hold, p06_pre_redirect,
                p06_pre_bus, p06_pre_address, p06_pre_status, p06_pre_write, p06_pre_bhe,
                p06_pre_data_out, p06_pre_data_in, p06_pre_lock, p06_pre_hlda,
                debug_gpr, debug_flags, debug_cs, debug_cs_base, debug_ip,
                halted, shutdown, instruction_retired, event_completed,
                debug_event_kind, debug_event_vector, debug_nmi_pending,
                debug_nmi_blocked, debug_sti_shadow, unsupported_opcode, control_error,
                microcode_fault, operand_blocked, debug_prefetch_count,
                debug_micro_active, debug_micro_pc,
                p06_observed_input(p06_pre_data_in), p06_input_unknown_mask(p06_pre_data_in));
    end
    final begin
        if (p06_observer_fd != 0) $fclose(p06_observer_fd);
    end


    logic [7:0] memory [0:65535];
    logic bus_seen = 1'b0;
    logic [23:0] last_bus_address = 24'h000000;
    integer stall_remaining = 0;
    integer bus_transactions = 0;
    integer cycles = 0;
    logic single_done = 1'b0, multi_done = 1'b0;

    spk286 dut (.*);

    task automatic drive_bus_data;
        logic [23:0] aligned_address;
        begin
            data_in = 16'h0000;
            if (bus_valid) begin
                aligned_address = address & 24'hFFFFFE;
                if (aligned_address[23:16] == 8'h00)
                    data_in = {memory[aligned_address[15:0] + 16'd1],
                               memory[aligned_address[15:0]]};
            end
        end
    endtask

    task automatic tick;
        drive_bus_data();
        #5; clk = 1'b1; #5; clk = 1'b0; #1;
    endtask

    task automatic service_cycle;
        begin
            if (bus_valid) begin
                if (!bus_seen || address !== last_bus_address) begin
                    bus_seen = 1'b1;
                    last_bus_address = address;
                    bus_transactions = bus_transactions + 1;
                    // Every transaction gets a deterministic READY delay.
                    stall_remaining = (bus_transactions % 3) + 1;
                end
                if (stall_remaining != 0) begin
                    ready = 1'b0;
                    stall_remaining = stall_remaining - 1;
                end else begin
                    ready = 1'b1;
                end
            end else begin
                ready = 1'b0;
                bus_seen = 1'b0;
            end
            tick();
            if (!bus_valid) bus_seen = 1'b0;
        end
    endtask

    task automatic load_byte(input logic [15:0] address_value, input logic [7:0] value);
        memory[address_value] = value;
    endtask

    task automatic check_word(input logic [2:0] index,
                              input logic [15:0] expected,
                              input string name);
        if (debug_gpr[index * 16 +: 16] !== expected)
            $fatal(1, "%s got=%h expected=%h", name, debug_gpr[index * 16 +: 16], expected);
    endtask

    initial begin
        for (integer i = 0; i < 65536; i = i + 1) memory[i] = 8'h00;

        // First instruction proves a complete single MOV and leaves an old
        // stream byte behind for the redirect/flush check.
        load_byte(16'h0000, 8'hB8);
        load_byte(16'h0001, 8'h34);
        load_byte(16'h0002, 8'h12);
        load_byte(16'h0003, 8'h0F); // Unsupported if stale bytes escape a flush.

        // The redirected stream covers the remaining seven destination codes.
        load_byte(16'h0100, 8'hB9); load_byte(16'h0101, 8'h78); load_byte(16'h0102, 8'h56);
        load_byte(16'h0103, 8'hBA); load_byte(16'h0104, 8'hBC); load_byte(16'h0105, 8'h9A);
        load_byte(16'h0106, 8'hBB); load_byte(16'h0107, 8'hED); load_byte(16'h0108, 8'h0F);
        load_byte(16'h0109, 8'hBC); load_byte(16'h010A, 8'h00); load_byte(16'h010B, 8'h10);
        load_byte(16'h010C, 8'hBD); load_byte(16'h010D, 8'h00); load_byte(16'h010E, 8'h20);
        load_byte(16'h010F, 8'hBE); load_byte(16'h0110, 8'h00); load_byte(16'h0111, 8'h30);
        load_byte(16'h0112, 8'hBF); load_byte(16'h0113, 8'h00); load_byte(16'h0114, 8'h40);

        // Reset and initialize through the normal Phase 1 commit ports.
        tick();
        reset = 1'b0;
        for (integer i = 0; i < 8; i = i + 1) begin
            gpr_write_en = 1'b1;
            gpr_write_index = 3'(i);
            gpr_write_data = 16'hA000 + 16'(i);
            tick();
        end
        gpr_write_en = 1'b0;
        flags_write_en = 1'b1;
        flags_write_mask = 16'hFFFF;
        flags_write_data = 16'h0041;
        tick();
        flags_write_en = 1'b0;

        // Far restart is intentionally performed while the old reset fetch is
        // outstanding. Its response must be discarded before the new stream.
        segment_load_en = 1'b1;
        segment_load_index = 2'd1;
        segment_load_selector = 16'h0000;
        ip_write_en = 1'b1;
        ip_write_data = 16'h0000;
        redirect = 1'b1;
        #1;
        if (control_error !== 1'b0) $fatal(1, "initial program redirect rejected");
        tick();
        segment_load_en = 1'b0;
        ip_write_en = 1'b0;
        redirect = 1'b0;
        ready = 1'b1;
        tick();
        ready = 1'b0;
        tick();

        execute_enable = 1'b1;
        single_done = 1'b0;
        for (cycles = 0; cycles < 1200 && !single_done; cycles = cycles + 1) begin
            service_cycle();
            if (debug_ip === 16'h0003 && debug_gpr[15:0] === 16'h1234)
                single_done = 1'b1;
        end
        if (!single_done) $fatal(1, "single MOV did not complete");
        check_word(3'd0, 16'h1234, "AX after MOV");
        check_word(3'd1, 16'hA001, "CX before redirect");
        if (debug_ip !== 16'h0003 || debug_flags !== 16'h0043 || unsupported_opcode)
            $fatal(1, "single MOV architectural result IP=%h FLAGS=%h unsupported=%b",
                   debug_ip, debug_flags, unsupported_opcode);

        // Redirect with prefetched old bytes present. This must invalidate the
        // queue and restart the frontend at the new architectural IP.
        ip_write_en = 1'b1;
        ip_write_data = 16'h0100;
        redirect = 1'b1;
        #1;
        if (control_error !== 1'b0) $fatal(1, "near execution redirect rejected");
        tick();
        ip_write_en = 1'b0;
        redirect = 1'b0;

        multi_done = 1'b0;
        for (cycles = 0; cycles < 2400 && !multi_done; cycles = cycles + 1) begin
            service_cycle();
            if (debug_ip === 16'h0115 &&
                debug_gpr[15:0] === 16'h1234 &&
                debug_gpr[31:16] === 16'h5678 &&
                debug_gpr[47:32] === 16'h9ABC &&
                debug_gpr[63:48] === 16'h0FED &&
                debug_gpr[79:64] === 16'h1000 &&
                debug_gpr[95:80] === 16'h2000 &&
                debug_gpr[111:96] === 16'h3000 &&
                debug_gpr[127:112] === 16'h4000)
                multi_done = 1'b1;
        end
        if (!multi_done) $fatal(1, "multi-instruction MOV program did not complete");
        check_word(3'd0, 16'h1234, "AX final");
        check_word(3'd1, 16'h5678, "CX final");
        check_word(3'd2, 16'h9ABC, "DX final");
        check_word(3'd3, 16'h0FED, "BX final");
        check_word(3'd4, 16'h1000, "SP final");
        check_word(3'd5, 16'h2000, "BP final");
        check_word(3'd6, 16'h3000, "SI final");
        check_word(3'd7, 16'h4000, "DI final");
        if (debug_ip !== 16'h0115 || debug_flags !== 16'h0043 || unsupported_opcode)
            $fatal(1, "multi MOV architectural result IP=%h FLAGS=%h unsupported=%b",
                   debug_ip, debug_flags, unsupported_opcode);
        if (debug_prefetch_count > 4'd6)
            $fatal(1, "prefetch queue count overflow: %d", debug_prefetch_count);

        // An unsupported second byte of the 0F escape is an architectural #UD
        // event; the old local "unsupported opcode" latch must stay clear.
        ip_write_en = 1'b1;
        ip_write_data = 16'h0200;
        redirect = 1'b1;
        load_byte(16'h0200, 8'h0F);
        load_byte(16'h0201, 8'hFF);
        memory[24] = 8'h00; memory[25] = 8'h03; // vector 6 -> 0000:0300
        memory[26] = 8'h00; memory[27] = 8'h00;
        load_byte(16'h0300, 8'hCF);
        #1;
        tick();
        ip_write_en = 1'b0;
        redirect = 1'b0;
        for (cycles = 0; cycles < 600 && !event_completed; cycles = cycles + 1)
            service_cycle();
        if (!event_completed || debug_event_vector !== 8'd6 || unsupported_opcode ||
            debug_gpr[15:0] !== 16'h1234 || debug_flags !== 16'h0043)
            $fatal(1, "0F invalid form did not raise architectural #UD");

        $display("EXECUTION PASS: MOV single/multi-instruction, stalls, redirect flush and unsupported opcode; bus transactions=%0d",
                 bus_transactions);
        $finish;
    end
endmodule
