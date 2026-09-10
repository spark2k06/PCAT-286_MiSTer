`timescale 1ns/1ps

// Bring-up tracer for an externally supplied 64 KiB F0000h system ROM.
// This is a CPU/bridge smoke model, not a replacement for the full chipset.
module spk286_external_rom_smoke_tb;
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

    logic [7:0] rom [0:65535];
    logic [7:0] ram [0:1048575];
    logic [7:0] xt_data_in;
    logic xt_valid;
    logic [19:0] xt_address;
    logic [7:0] xt_data_out;
    logic [2:0] xt_status;
    logic xt_write, xt_io, xt_inta, xt_code, xt_byte_high;
    logic xt_memory_projection, xt_lock_n, xt_accepted;
    logic bridge_idle, protocol_error;
    logic [7:0] port_3da = 8'd0;
    logic [2:0] phase = 3'd0;
    logic cpu_ce_posedge = 1'b0;
    logic cpu_ce_negedge = 1'b0;
    integer accepted_beats = 0;
    integer io_reads = 0;
    integer io_writes = 0;
    integer port80_writes = 0;
    integer code_fetches = 0;
    logic saw_native_reset_fetch = 1'b0;
    logic saw_low_code_fetch = 1'b0;
    integer loaded_bytes;
    integer rom_file;
    reg [8*512-1:0] rom_path;

    wire enable_io_command;
    wire advanced_io_write_command_n;
    wire io_write_command_n;
    wire io_read_command_n;
    wire interrupt_acknowledge_n;
    wire enable_memory_command;
    wire advanced_memory_write_command_n;
    wire memory_write_command_n;
    wire memory_read_command_n;
    wire direction_transmit_or_receive_n;
    wire data_enable;
    wire master_cascade_enable;
    wire peripheral_data_enable_n;
    wire address_latch_enable;
    wire [2:0] processor_status = xt_valid ? xt_status : 3'b111;
    wire xt_cycle_active = ~advanced_io_write_command_n |
                           ~io_read_command_n |
                           ~interrupt_acknowledge_n |
                           ~advanced_memory_write_command_n |
                           ~memory_read_command_n;
    wire ready_dma;
    wire xt_ready;

    always_ff @(posedge clk) begin
        if (reset) begin
            phase <= 3'd0;
            cpu_ce_posedge <= 1'b0;
            cpu_ce_negedge <= 1'b0;
        end else begin
            cpu_ce_posedge <= (phase == 3'd0);
            cpu_ce_negedge <= (phase == 3'd4);
            phase <= phase + 3'd1;
        end
    end

    initial begin
        if (!$value$plusargs("ROM=%s", rom_path))
            $fatal(1, "use +ROM=<64-KiB-file>");
        rom_file = $fopen(rom_path, "rb");
        if (rom_file == 0)
            $fatal(1, "cannot open ROM: %0s", rom_path);
        loaded_bytes = $fread(rom, rom_file, 0, 65536);
        $fclose(rom_file);
        if (loaded_bytes != 65536)
            $fatal(1, "ROM must be exactly/readably 65536 bytes, got %0d", loaded_bytes);
        $display("EXTERNAL_ROM_LOAD path=%0s bytes=%0d reset=%02h%02h%02h%02h%02h",
                 rom_path, loaded_bytes,
                 rom[16'hfff0], rom[16'hfff1], rom[16'hfff2],
                 rom[16'hfff3], rom[16'hfff4]);
    end

    always_comb begin
        if (xt_inta)
            xt_data_in = 8'hff;
        else if (xt_io) begin
            case (xt_address[15:0])
                16'h0061: xt_data_in = 8'h00;
                16'h03ba, 16'h03da: xt_data_in = port_3da;
                default: xt_data_in = 8'hff;
            endcase
        end else if (xt_address >= 20'hf0000)
            xt_data_in = rom[xt_address[15:0]];
        else
            xt_data_in = ram[xt_address];
    end

    always_ff @(posedge clk) begin
        if (!reset && cpu_bus_valid && (cpu_bus_status == 4'hd) &&
            (cpu_address == 24'hfffff0))
            saw_native_reset_fetch <= 1'b1;
        if (!reset && cpu_ready && cpu_bus_valid &&
            (cpu_bus_status == 4'hd) && (cpu_address[23:20] == 4'h0))
            saw_low_code_fetch <= 1'b1;

        if (!reset && xt_accepted) begin
            accepted_beats <= accepted_beats + 1;
            if (xt_code)
                code_fetches <= code_fetches + 1;
            if (xt_io) begin
                if (xt_write) begin
                    io_writes <= io_writes + 1;
                    if (xt_address[15:0] == 16'h0080) begin
                        port80_writes <= port80_writes + 1;
                        $display("EXTERNAL_ROM_PORT80 index=%0d data=%02h cs_ip=%04h:%04h cycle=%0d",
                                 port80_writes, xt_data_out, debug_cs, debug_ip,
                                 accepted_beats);
                    end
                end else begin
                    io_reads <= io_reads + 1;
                    if ((xt_address[15:0] == 16'h03ba) ||
                        (xt_address[15:0] == 16'h03da))
                        port_3da <= port_3da ^ 8'h08;
                end
            end else if (xt_write && (xt_address < 20'hf0000)) begin
                ram[xt_address] <= xt_data_out;
            end
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
        .xt_start(cpu_ce_posedge), .xt_sample(cpu_ce_posedge),
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

    KF8288 controller (
        .clock(clk), .cpu_ce_posedge(cpu_ce_posedge),
        .cpu_ce_negedge(cpu_ce_negedge), .reset(reset),
        .address_enable_n(1'b0), .command_enable(1'b1),
        .io_bus_mode(1'b0), .processor_status(processor_status),
        .enable_io_command(enable_io_command),
        .advanced_io_write_command_n(advanced_io_write_command_n),
        .io_write_command_n(io_write_command_n),
        .io_read_command_n(io_read_command_n),
        .interrupt_acknowledge_n(interrupt_acknowledge_n),
        .enable_memory_command(enable_memory_command),
        .advanced_memory_write_command_n(advanced_memory_write_command_n),
        .memory_write_command_n(memory_write_command_n),
        .memory_read_command_n(memory_read_command_n),
        .direction_transmit_or_receive_n(direction_transmit_or_receive_n),
        .data_enable(data_enable),
        .master_cascade_enable(master_cascade_enable),
        .peripheral_data_enable_n(peripheral_data_enable_n),
        .address_latch_enable(address_latch_enable)
    );

    READY ready_logic (
        .clock(clk), .cpu_ce_posedge(cpu_ce_posedge),
        .cpu_ce_negedge(cpu_ce_negedge), .reset(reset),
        .processor_ready(xt_ready), .dma_ready(ready_dma),
        .dma_wait_n(1'b1), .io_channel_ready(1'b1),
        .io_read_n(io_read_command_n),
        .io_write_n(advanced_io_write_command_n),
        .memory_read_n(memory_read_command_n),
        .memory_write_n(advanced_memory_write_command_n),
        .dma0_acknowledge_n(1'b1), .address_enable_n(1'b0),
        .clk_select(2'b00)
    );

    initial begin : run
        integer cycles;
        integer max_cycles;
        integer minimum_beats;
        max_cycles = 2000000;
        minimum_beats = 128;
        if (!$value$plusargs("MAX_CYCLES=%d", max_cycles))
            max_cycles = 2000000;
        if (!$value$plusargs("MIN_BEATS=%d", minimum_beats))
            minimum_beats = 128;
        repeat (6) @(posedge clk);
        reset = 1'b0;
        for (cycles = 0; cycles < max_cycles; cycles = cycles + 1) begin
            @(negedge clk);
            if (control_error || unsupported_opcode || microcode_fault ||
                operand_blocked || shutdown || protocol_error) begin
                $fatal(1, "EXTERNAL_ROM_FAULT cycle=%0d cs_ip=%04h:%04h opcode=%02h micro_pc=%03h control=%b unsupported=%b microcode=%b operand=%b shutdown=%b bridge=%b",
                       cycles, debug_cs, debug_ip, debug_opcode, debug_micro_pc,
                       control_error, unsupported_opcode, microcode_fault,
                       operand_blocked, shutdown, protocol_error);
            end
            if (halted) begin
                $fatal(1, "EXTERNAL_ROM_HALT cycle=%0d cs_ip=%04h:%04h opcode=%02h port80=%0d beats=%0d",
                       cycles, debug_cs, debug_ip, debug_opcode,
                       port80_writes, accepted_beats);
            end
            if (saw_native_reset_fetch && saw_low_code_fetch &&
                (accepted_beats >= minimum_beats) && (code_fetches != 0)) begin
                $display("EXTERNAL_ROM_BOUNDARY_PASS cs_ip=%04h:%04h opcode=%02h port80=%0d beats=%0d code=%0d io_r=%0d io_w=%0d",
                         debug_cs, debug_ip, debug_opcode, port80_writes,
                         accepted_beats, code_fetches, io_reads, io_writes);
                $finish;
            end
        end
        $fatal(1, "EXTERNAL_ROM_WATCHDOG native=%b low=%b beats=%0d required=%0d",
               saw_native_reset_fetch, saw_low_code_fetch,
               accepted_beats, minimum_beats);
    end
endmodule
