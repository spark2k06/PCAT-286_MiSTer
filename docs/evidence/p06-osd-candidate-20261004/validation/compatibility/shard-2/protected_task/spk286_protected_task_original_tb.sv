`timescale 1ns/1ps

module spk286_protected_task_tb;
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
    integer cycles = 0;
    integer checks = 0;
    integer descriptor_trace_count = 0;
    integer tss_trace_count = 0;
    integer protected_fetch_trace_count = 0;

    spk286 dut (.*);

    task automatic check(input logic condition, input string message);
        begin
            checks = checks + 1;
            if (condition !== 1'b1)
                $fatal(1, "%s: CS=%h IP=%h TR=%h FLAGS=%h MSW=%h bus=%h",
                       message, debug_cs, debug_ip, debug_tr_selector, debug_flags,
                       debug_protected_msw, bus_status);
        end
    endtask

    task automatic write_word(input integer address, input logic [15:0] value);
        begin
            memory[address] = value[7:0];
            memory[address + 1] = value[15:8];
        end
    endtask

    task automatic write_descriptor(
        input integer address,
        input logic [23:0] base,
        input logic [15:0] limit,
        input logic [7:0] access
    );
        begin
            write_word(address, limit);
            write_word(address + 2, base[15:0]);
            memory[address + 4] = base[23:16];
            memory[address + 5] = access;
            memory[address + 6] = 8'h00;
            memory[address + 7] = 8'h00;
        end
    endtask

    task automatic tick;
        begin
            #1;
            ready = bus_valid && ((cycles % 4) != 1);
            data_in = 16'h0000;
            if (bus_valid && !bus_write) begin
                if (bus_status == 4'h0) data_in = 16'h0022;
                else if (address[0]) data_in = {memory[address[15:0]], 8'h00};
                else if (bus_bhe_n) data_in = {8'h00, memory[address[15:0]]};
                else data_in = {memory[address[15:0] + 16'd1], memory[address[15:0]]};
            end
            if (bus_valid && ready && bus_write && bus_status == 4'h6) begin
                if (address[0]) memory[address[15:0]] = data_out[15:8];
                else begin
                    memory[address[15:0]] = data_out[7:0];
                    if (!bus_bhe_n) memory[address[15:0] + 16'd1] = data_out[15:8];
                end
            end
            if (bus_valid && debug_bus_transaction == 4'h1) descriptor_trace_count = descriptor_trace_count + 1;
            if (bus_valid && debug_bus_transaction == 4'h2) tss_trace_count = tss_trace_count + 1;
            if (bus_valid && debug_bus_transaction == 4'h5) protected_fetch_trace_count = protected_fetch_trace_count + 1;
            #4; clk = 1'b1; #5; clk = 1'b0; #1;
            cycles = cycles + 1;
        end
    endtask

    task automatic far_restart(input logic [15:0] cs, input logic [15:0] ip);
        begin
            segment_load_en = 1'b1;
            segment_load_index = 2'd1;
            segment_load_selector = cs;
            ip_write_en = 1'b1;
            ip_write_data = ip;
            redirect = 1'b1;
            tick();
            segment_load_en = 1'b0;
            ip_write_en = 1'b0;
            redirect = 1'b0;
            tick();
        end
    endtask

    task automatic wait_until_task_loaded;
        integer deadline;
        begin
            deadline = 0;
            while ((debug_tr_selector != 16'h0020 || !debug_flags[14]) && deadline < 1200) begin
                tick();
                deadline = deadline + 1;
            end
            check(debug_tr_selector == 16'h0020 && debug_flags[14],
                  "direct TSS call commits target TR and nested-task flag");
        end
    endtask

    task automatic hold_during_task_switch;
        integer deadline;
        begin
            deadline = 0;
            while (!dut.task_service_busy && deadline < 1600) begin
                tick();
                deadline = deadline + 1;
            end
            check(dut.task_service_busy, "HOLD test reaches the serialized task service");

            hold_request = 1'b1;
            deadline = 0;
            while (!hlda && deadline < 1600) begin
                tick();
                deadline = deadline + 1;
            end
            check(hlda && !bus_valid, "HOLD is granted at a legal task-switch bus boundary");
            check(debug_tr_selector == 16'h0018 &&
                  (memory[16'h2025] == 8'h81 || memory[16'h2025] == 8'h83) &&
                  !debug_flags[14],
                  "HLDA holds the current task after the locked target BUSY commit");
            repeat (8) begin
                tick();
                if (!hlda) begin
                    check(bus_lock || dut.task_memory_lock,
                          "HOLD is only preempted by an active locked task-switch cycle");
                    deadline = 0;
                    while (!hlda && deadline < 1600) begin
                        tick();
                        deadline = deadline + 1;
                    end
                end
                check(hlda && !bus_valid && debug_tr_selector == 16'h0018 &&
                      (memory[16'h2025] == 8'h81 || memory[16'h2025] == 8'h83),
                      "task-switch state remains stable while HOLD is asserted");
            end
            hold_request = 1'b0;
            tick();
        end
    endtask

    initial begin
        for (integer i = 0; i < 65536; i = i + 1) memory[i] = 8'h00;

        // Real-mode setup: LGDT, LMSW, then enter the protected code segment.
        memory[16'h0000] = 8'h0F; memory[16'h0001] = 8'h01; memory[16'h0002] = 8'h16;
        memory[16'h0003] = 8'h00; memory[16'h0004] = 8'h03;
        memory[16'h0005] = 8'hB8; memory[16'h0006] = 8'h01; memory[16'h0007] = 8'h00;
        memory[16'h0008] = 8'h0F; memory[16'h0009] = 8'h01; memory[16'h000A] = 8'hF0;
        memory[16'h000B] = 8'hEA; memory[16'h000C] = 8'h00; memory[16'h000D] = 8'h01;
        memory[16'h000E] = 8'h10; memory[16'h000F] = 8'h00;

        // Protected current task: LTR 0018, then direct far CALL to TSS 0020.
        memory[16'h0100] = 8'hB8; memory[16'h0101] = 8'h18; memory[16'h0102] = 8'h00;
        memory[16'h0103] = 8'h0F; memory[16'h0104] = 8'h00; memory[16'h0105] = 8'hD8;
        memory[16'h0106] = 8'h9A; memory[16'h0107] = 8'h00; memory[16'h0108] = 8'h00;
        memory[16'h0109] = 8'h20; memory[16'h010A] = 8'h00;
        memory[16'h0200] = 8'hB8; memory[16'h0201] = 8'hEF; memory[16'h0202] = 8'hBE;
        memory[16'h0203] = 8'hF4;

        // GDT at 2000h: data, code, current available TSS and target available TSS.
        write_descriptor(32'h2000 + 32'd8 * 1, 24'h000000, 16'hFFFF, 8'h93);
        write_descriptor(32'h2000 + 32'd8 * 2, 24'h000000, 16'hFFFF, 8'h9A);
        write_descriptor(32'h2000 + 32'd8 * 3, 24'h004000, 16'h002B, 8'h81);
        write_descriptor(32'h2000 + 32'd8 * 4, 24'h005000, 16'h002B, 8'h81);
        write_word(32'h0300, 16'h0027);
        memory[16'h0302] = 8'h00; memory[16'h0303] = 8'h20; memory[16'h0304] = 8'h00;

        // Current TSS starts empty; target TSS supplies the complete incoming image.
        write_word(32'h5000 + 32'h000E, 16'h0200);
        write_word(32'h5000 + 32'h0010, 16'h0202);
        write_word(32'h5000 + 32'h0012, 16'hBEEF);
        write_word(32'h5000 + 32'h0022, 16'h0000); // ES
        write_word(32'h5000 + 32'h0024, 16'h0010); // CS
        write_word(32'h5000 + 32'h0026, 16'h0008); // SS
        write_word(32'h5000 + 32'h0028, 16'h0000); // DS
        write_word(32'h5000 + 32'h002A, 16'h0000); // null LDTR

        reset = 1'b1;
        execute_enable = 1'b0;
        tick();
        reset = 1'b0;
        execute_enable = 1'b1;
        far_restart(16'h0000, 16'h0000);

        hold_during_task_switch();
        wait_until_task_loaded();
        check(debug_protected_msw[3] && debug_protected_msw[0],
              "direct TSS task switch sets MSW.TS while preserving PE");
        check(memory[16'h2025] == 8'h83, "direct TSS call sets target descriptor busy");
        check(memory[16'h5000] == 8'h18,
              "direct TSS call writes the outgoing TR selector as backlink");
        check({memory[16'h400F], memory[16'h400E]} == 16'h010B,
              "direct TSS call writes the next protected IP to the outgoing TSS");
        check(debug_cs == 16'h0010 && debug_ip == 16'h0200,
              "direct TSS call redirects to the incoming task IP and CS");
        check(debug_gpr[15:0] == 16'hBEEF,
              "direct TSS call restores the incoming general-register image");
        $display("DIRECT_TSS_TRACE_COUNTS descriptor=%0d tss=%0d protected_fetch=%0d",
                 descriptor_trace_count, tss_trace_count, protected_fetch_trace_count);
        check(descriptor_trace_count != 0 && tss_trace_count != 0 && protected_fetch_trace_count != 0,
              "direct TSS trace metadata identifies descriptor, TSS and protected fetch transactions");

        while (!halted && cycles < 1600) tick();
        check(halted, "incoming task reaches its protected-mode handler");
        $display("PROTECTED_TASK PASS: %0d checks, cycles=%0d", checks, cycles);
        $finish;
    end
endmodule
