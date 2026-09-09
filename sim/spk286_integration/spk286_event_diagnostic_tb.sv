`timescale 1ns/1ps

module spk286_event_diagnostic_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    always #5 clk = ~clk;

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

    wire execute_enable = 1'b1;
    logic nmi = 1'b0;
    logic xt_ready = 1'b0;
    logic [7:0] xt_data_in;
    logic xt_valid;
    logic [19:0] xt_address;
    logic [7:0] xt_data_out;
    logic [2:0] xt_status;
    logic xt_write, xt_io, xt_inta, xt_code, xt_byte_high;
    logic xt_memory_projection, xt_lock_n, bridge_idle, protocol_error;
    wire xt_cycle_active = xt_valid;

    logic [7:0] low_ram [0:4095];
    logic [7:0] data_ram [0:4095];
    logic [7:0] stack_ram [0:4095];
    integer index;

    logic [7:0] milestones [0:7];
    logic pic_write_port [0:7];
    logic [7:0] pic_write_data [0:7];
    integer milestone_count = 0;
    integer pic_write_count = 0;
    integer pit_write_count = 0;
    integer failure_count = 0;
    logic [7:0] failure_code = 8'd0;
    integer accepted_beats = 0;
    integer inta_count = 0;
    logic [7:0] second_inta_vector = 8'd0;
    integer locked_inta_beats = 0;
    integer locked_first_frame_beats = 0;
    logic waiting_for_first_frame = 1'b0;
    logic first_frame_complete = 1'b0;
    logic saw_intr_event = 1'b0;
    logic saw_nmi_event = 1'b0;
    logic [15:0] saved_intr_ip = 16'd0;
    logic [15:0] saved_intr_cs = 16'd0;
    logic [15:0] saved_intr_flags = 16'd0;

    logic backend_active = 1'b0;
    integer wait_remaining = 0;
    integer longest_wait = 0;
    integer current_wait = 0;

    logic [7:0] interrupt_request = 8'd0;
    logic pic_interrupt;
    logic [7:0] pic_data_out;
    logic pic_data_io;
    integer irq_state = 0;
    integer masked_wait = 0;
    logic nmi_sent = 1'b0;
    logic nmi_returned = 1'b0;

    wire pic_selected = xt_valid && xt_io && !xt_inta &&
                        ((xt_address[15:0] == 16'h0020) ||
                         (xt_address[15:0] == 16'h0021));
    wire pic_chip_select_n = ~pic_selected;
    wire pic_read_enable_n = ~(pic_selected && !xt_write);
    wire pic_write_enable_n = ~(pic_selected && xt_write);
    wire pic_inta_n = ~(xt_valid && xt_inta);

`include "tests/firmware/pcat286_event_diag_rom_case.svh"

    function automatic logic [7:0] sparse_ram_read(input logic [19:0] address);
        begin
            sparse_ram_read = 8'h00;
            if (address < 20'h01000)
                sparse_ram_read = low_ram[address[11:0]];
            else if (address >= 20'h10000 && address < 20'h11000)
                sparse_ram_read = data_ram[address[11:0]];
            else if (address >= 20'h1f000 && address < 20'h20000)
                sparse_ram_read = stack_ram[address[11:0]];
        end
    endfunction

    initial begin
        for (index = 0; index < 4096; index = index + 1) begin
            low_ram[index] = 8'd0;
            data_ram[index] = 8'd0;
            stack_ram[index] = 8'd0;
        end
        for (index = 0; index < 8; index = index + 1) begin
            milestones[index] = 8'd0;
            pic_write_port[index] = 1'b0;
            pic_write_data[index] = 8'd0;
        end
        // Guards surround the diagnostic data and the interrupt frame region.
        data_ram[12'h5fe] = 8'h3c;
        data_ram[12'h608] = 8'hc3;
        stack_ram[12'hef4] = 8'h5a;
        stack_ram[12'hf00] = 8'ha5;
    end

    always_comb begin
        if (xt_inta || (pic_selected && !xt_write))
            xt_data_in = pic_data_out;
        else if (xt_io)
            xt_data_in = 8'hff;
        else if (xt_address >= 20'hf0000)
            xt_data_in = event_rom_read(xt_address[15:0]);
        else
            xt_data_in = sparse_ram_read(xt_address);
    end

    // Each transfer is independently READY-qualified. The second INTA gets
    // the longest wait, proving that its vector is sampled only on completion.
    always_ff @(posedge clk) begin
        if (reset) begin
            backend_active <= 1'b0;
            wait_remaining <= 0;
            current_wait <= 0;
            longest_wait <= 0;
            xt_ready <= 1'b0;
        end else if (!xt_valid) begin
            backend_active <= 1'b0;
            wait_remaining <= 0;
            current_wait <= 0;
            xt_ready <= 1'b0;
        end else if (!backend_active) begin
            backend_active <= 1'b1;
            if (xt_inta)
                wait_remaining <= (inta_count == 0) ? 2 : 5;
            else
                wait_remaining <= accepted_beats & 1;
            current_wait <= 0;
            xt_ready <= 1'b0;
        end else if (wait_remaining != 0) begin
            wait_remaining <= wait_remaining - 1;
            current_wait <= current_wait + 1;
            xt_ready <= 1'b0;
        end else begin
            if (current_wait > longest_wait)
                longest_wait <= current_wait;
            xt_ready <= 1'b1;
        end
    end

    // Accepted bus effects are recorded independently of CPU debug state.
    always_ff @(posedge clk) begin
        if (!reset && xt_valid && xt_cycle_active && xt_ready) begin
            accepted_beats <= accepted_beats + 1;
            if (xt_inta) begin
`ifdef I4_PIC_MODEL
                $display("I4_TRACE INTA index=%0d data=%h lock_n=%b wait=%0d",
                         inta_count, xt_data_in, xt_lock_n, current_wait);
`else
                $display("I4_TRACE INTA index=%0d data=%h lock_n=%b wait=%0d irr=%h active=%h ack=%h",
                         inta_count, xt_data_in, xt_lock_n, current_wait,
                         pic.u_Interrupt_Request.interrupt_request_register,
                         pic.u_Priority_Resolver.interrupt,
                         pic.u_Control_Logic.acknowledge_interrupt);
`endif
                if (irq_state < 3)
                    $fatal(1, "masked/deasserted request produced INTA");
                inta_count <= inta_count + 1;
                if (!xt_lock_n)
                    locked_inta_beats <= locked_inta_beats + 1;
                if (inta_count == 1) begin
                    second_inta_vector <= xt_data_in;
                    waiting_for_first_frame <= 1'b1;
                end
            end else if (!xt_io && xt_write) begin
                if (xt_address < 20'h01000)
                    low_ram[xt_address[11:0]] <= xt_data_out;
                else if (xt_address >= 20'h10000 && xt_address < 20'h11000)
                    data_ram[xt_address[11:0]] <= xt_data_out;
                else if (xt_address >= 20'h1f000 && xt_address < 20'h20000)
                    stack_ram[xt_address[11:0]] <= xt_data_out;
                else
                    $fatal(1, "event diagnostic RAM address out of model range: %h", xt_address);

                if (waiting_for_first_frame && !first_frame_complete) begin
                    if (!xt_lock_n)
                        locked_first_frame_beats <= locked_first_frame_beats + 1;
                    if (locked_first_frame_beats == 1) begin
                        first_frame_complete <= 1'b1;
                        waiting_for_first_frame <= 1'b0;
                    end
                end
            end else if (xt_io && xt_write) begin
                if (xt_address[15:0] == 16'h0080) begin
                    if (milestone_count < 8)
                        milestones[milestone_count] <= xt_data_out;
                    milestone_count <= milestone_count + 1;
                end else if (xt_address[15:0] == 16'h0081) begin
                    failure_code <= xt_data_out;
                    failure_count <= failure_count + 1;
                end

                if ((xt_address[15:0] == 16'h0020) ||
                    (xt_address[15:0] == 16'h0021)) begin
                    if (pic_write_count < 8) begin
                        pic_write_port[pic_write_count] <= xt_address[0];
                        pic_write_data[pic_write_count] <= xt_data_out;
                    end
                    pic_write_count <= pic_write_count + 1;
                end
                if ((xt_address[15:0] == 16'h0040) ||
                    (xt_address[15:0] == 16'h0043))
                    pit_write_count <= pit_write_count + 1;
            end
        end

        if (!reset && event_completed) begin
            $display("I4_TRACE EVENT kind=%0d vector=%h cs=%h ip=%h",
                     debug_event_kind, debug_event_vector, debug_cs, debug_ip);
            if (debug_event_kind == 3'd4 && debug_event_vector == 8'h20) begin
                saw_intr_event <= 1'b1;
                saved_intr_ip <= {sparse_ram_read(20'h1fefb),
                                  sparse_ram_read(20'h1fefa)};
                saved_intr_cs <= {sparse_ram_read(20'h1fefd),
                                  sparse_ram_read(20'h1fefc)};
                saved_intr_flags <= {sparse_ram_read(20'h1feff),
                                     sparse_ram_read(20'h1fefe)};
            end
            if (debug_event_kind == 3'd3 && debug_event_vector == 8'h02)
                saw_nmi_event <= 1'b1;
        end
    end

    // First prove that masked IRQ1 cannot wake HLT. Then pulse IRQ0. Once the
    // normal diagnostic PASS is visible, inject a controlled NMI edge through
    // the verification-only CPU input and require a second IRET back to HLT.
    always_ff @(posedge clk) begin
        if (reset) begin
            interrupt_request <= 8'd0;
            irq_state <= 0;
            masked_wait <= 0;
            nmi <= 1'b0;
            nmi_sent <= 1'b0;
            nmi_returned <= 1'b0;
        end else begin
            nmi <= 1'b0;
            case (irq_state)
                0: if (halted && pit_write_count == 3 && milestone_count == 1) begin
`ifdef I4_PIC_MODEL
                    $display("I4_TRACE HLT model_pic");
`else
                    $display("I4_TRACE HLT pic_mask=%h pic_vector=%h",
                             pic.u_Control_Logic.interrupt_mask,
                             pic.u_Control_Logic.interrupt_vector_address);
`endif
                    interrupt_request <= 8'h02;
                    irq_state <= 1;
                end else interrupt_request <= 8'h00;
                1: begin
                    interrupt_request <= 8'h00;
                    masked_wait <= 20;
                    irq_state <= 2;
                end
                2: if (masked_wait != 0) begin
                    interrupt_request <= 8'h00;
                    masked_wait <= masked_wait - 1;
                    if (!halted || inta_count != 0)
                        $fatal(1, "masked IRQ1 woke the CPU");
                end else begin
`ifdef I4_PIC_MODEL
                    $display("I4_TRACE IRQ0 assert model_pic");
`else
                    $display("I4_TRACE IRQ0 assert low_latch=%h freeze=%b",
                             pic.u_Interrupt_Request.low_input_latch,
                             pic.u_Control_Logic.freeze);
`endif
                    interrupt_request <= 8'h01;
                    irq_state <= 3;
                end
                3: begin
                    interrupt_request <= 8'h01;
                    if (inta_count != 0)
                        irq_state <= 4;
                end
                default: interrupt_request <= 8'h00;
            endcase

            if (!nmi_sent && halted && milestone_count == 4 && saw_intr_event) begin
                nmi <= 1'b1;
                nmi_sent <= 1'b1;
            end
            if (nmi_sent && saw_nmi_event && halted && milestone_count == 5)
                nmi_returned <= 1'b1;
        end
    end

`ifdef I4_PIC_MODEL
    spk286_pic_model pic (
`else
    KF8259 pic (
`endif
        .clock(clk), .reset(reset),
        .chip_select_n(pic_chip_select_n),
        .read_enable_n(pic_read_enable_n),
        .write_enable_n(pic_write_enable_n),
        .address(xt_address[0]), .data_bus_in(xt_data_out),
        .data_bus_out(pic_data_out), .data_bus_io(pic_data_io),
        .cascade_in(3'b000), .cascade_out(), .cascade_io(),
        .slave_program_n(1'b1), .buffer_enable(),
        .slave_program_or_enable_buffer(),
        .interrupt_acknowledge_n(pic_inta_n),
        .interrupt_to_cpu(pic_interrupt),
        .interrupt_request(interrupt_request)
    );

    spk286_machine_cpu cpu (
        .clk(clk), .reset(reset), .execute_enable(execute_enable),
        .ready(cpu_ready), .data_in(cpu_data_in),
        .intr(pic_interrupt), .nmi(nmi), .hold_request(1'b0),
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
        .xt_start(1'b1), .xt_cycle_active(xt_cycle_active),
        .xt_ready(xt_ready), .xt_data_in(xt_data_in),
        .xt_valid(xt_valid), .xt_address(xt_address),
        .xt_data_out(xt_data_out), .xt_status(xt_status),
        .xt_write(xt_write), .xt_io(xt_io), .xt_inta(xt_inta),
        .xt_code(xt_code), .xt_byte_high(xt_byte_high),
        .xt_memory_projection(xt_memory_projection), .xt_lock_n(xt_lock_n),
        .bridge_idle(bridge_idle), .protocol_error(protocol_error)
    );

    initial begin : test
        integer cycles;
        repeat (6) @(posedge clk);
        reset = 1'b0;

        for (cycles = 0; cycles < 150000; cycles = cycles + 1) begin
            @(negedge clk);
            if (control_error || unsupported_opcode || microcode_fault ||
                operand_blocked || shutdown || protocol_error)
                $fatal(1,
                    "CPU/bridge event error cycle=%0d ip=%h opcode=%h micro_pc=%h flags=%h",
                    cycles, debug_ip, debug_opcode, debug_micro_pc, debug_flags);
            if (failure_count != 0)
                $fatal(1, "event diagnostic failure code=%h ip=%h", failure_code, debug_ip);
            if (nmi_returned)
                cycles = 150000;
        end

        if (!nmi_returned || !halted)
            $fatal(1, "event diagnostic deadline expired ip=%h milestones=%0d inta=%0d exec=%b halted=%b bus_valid=%b bridge_idle=%b micro_pc=%h bus_state=%h",
                   debug_ip, milestone_count, inta_count, execute_enable,
                   halted, cpu_bus_valid, bridge_idle, debug_micro_pc,
                   debug_bus_state);
        if (milestone_count != 5 || milestones[0] !== 8'h70 ||
            milestones[1] !== 8'h72 || milestones[2] !== 8'h71 ||
            milestones[3] !== 8'h86 || milestones[4] !== 8'h73)
            $fatal(1, "wrong event milestone sequence");
        if (pic_write_count != 5 ||
            pic_write_port[0] !== 1'b0 || pic_write_data[0] !== 8'h13 ||
            pic_write_port[1] !== 1'b1 || pic_write_data[1] !== 8'h20 ||
            pic_write_port[2] !== 1'b1 || pic_write_data[2] !== 8'h01 ||
            pic_write_port[3] !== 1'b1 || pic_write_data[3] !== 8'hfe ||
            pic_write_port[4] !== 1'b0 || pic_write_data[4] !== 8'h20)
            $fatal(1, "PIC programming/EOI sequence mismatch count=%0d", pic_write_count);
        if (pit_write_count != 3)
            $fatal(1, "PIT programming sequence count=%0d", pit_write_count);
        if (inta_count != 2 || second_inta_vector !== 8'h20)
            $fatal(1, "INTA count/vector mismatch count=%0d vector=%h", inta_count, second_inta_vector);
        if (locked_inta_beats != 2 || locked_first_frame_beats != 2)
            $fatal(1, "INTA/frame LOCK chain mismatch inta=%0d frame=%0d", locked_inta_beats, locked_first_frame_beats);
        if (!saw_intr_event || !saw_nmi_event || longest_wait < 5)
            $fatal(1, "event/lifecycle observations incomplete intr=%b nmi=%b wait=%0d",
                   saw_intr_event, saw_nmi_event, longest_wait);
        if ({sparse_ram_read(20'h10601), sparse_ram_read(20'h10600)} !== 16'ha55a ||
            {sparse_ram_read(20'h10605), sparse_ram_read(20'h10604)} !== 16'h2864 ||
            {sparse_ram_read(20'h10607), sparse_ram_read(20'h10606)} !== 16'h2bad)
            $fatal(1, "event memory signatures mismatch");
        if (sparse_ram_read(20'h105fe) !== 8'h3c ||
            sparse_ram_read(20'h10608) !== 8'hc3 ||
            sparse_ram_read(20'h1fef4) !== 8'h5a ||
            sparse_ram_read(20'h1ff00) !== 8'ha5)
            $fatal(1, "event/frame guard changed");
        if (saved_intr_cs !== 16'hf000 || saved_intr_ip !== 16'h005a ||
            ((saved_intr_flags & 16'h0200) == 16'h0000))
            $fatal(1, "saved interrupt frame mismatch");

        $display("I4_EVENT_DIAGNOSTIC_PASS beats=%0d pic_writes=%0d pit_writes=%0d inta=%0d vector=%h max_wait=%0d",
                 accepted_beats, pic_write_count, pit_write_count, inta_count,
                 second_inta_vector, longest_wait);
        $finish;
    end
endmodule
