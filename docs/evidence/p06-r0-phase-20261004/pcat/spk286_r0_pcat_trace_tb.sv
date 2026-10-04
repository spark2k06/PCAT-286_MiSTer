`timescale 1ns/1ps

`ifndef ENABLE_MIDI
`define ENABLE_MIDI 0
`endif

// Composed CPU-to-AT boundary test.  The memory model is intentionally small:
// it provides the externally loaded 64 KiB system ROM, sparse conventional
// memory and the same handshake used by a future MiSTer SDRAM owner.
module spk286_r0_pcat_trace_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    logic cpu_local_reset = 1'b0;
    integer selected_cpu_profile = 0;
    logic [2:0] applied_cpu_profile;
    wire cpu_profile_pending;
    always #10 clk = ~clk;
    logic clk_video = 1'b0;
    always #17.45 clk_video = ~clk_video;

    logic execute_enable = 1'b1;
    logic counter_clock_limited = 1'b0;
    logic counter_clock_real;
    logic counter_clock_fast = 1'b0;
    logic counter_clock;
    logic full_pit = 1'b0;
    logic fast_pit = 1'b0;
    logic refresh_enable = 1'b1;
    logic pit_clock_active = 1'b0;
    integer pit_clock_rising_edges = 0;
    always_ff @(posedge clk) begin
        if (reset) begin
            counter_clock_limited <= 1'b0;
            pit_clock_active <= 1'b0;
            pit_clock_rising_edges <= 0;
        end else if (!pit_clock_active) begin
            counter_clock_limited <= 1'b0;
        end else if (pit_clock_rising_edges < 32) begin
            counter_clock_limited <= ~counter_clock_limited;
            if (!counter_clock_limited)
                pit_clock_rising_edges <= pit_clock_rising_edges + 1;
        end else begin
            counter_clock_limited <= 1'b0;
        end
    end

    always_ff @(posedge clk) begin
        if (reset)
            counter_clock_fast <= 1'b0;
        else if (full_pit)
            counter_clock_fast <= ~counter_clock_fast;
        else
            counter_clock_fast <= 1'b0;
    end

    assign counter_clock = full_pit ?
                           (fast_pit ? counter_clock_fast : counter_clock_real) :
                           counter_clock_limited;
    spk286_at_pit_clock pit_clock_model(
        .clk(clk), .reset(reset), .counter_clock(counter_clock_real));

    logic keyboard_byte_valid = 1'b0;
    logic [7:0] keyboard_byte = 8'h00;
    logic periodic_tick = 1'b0;
    logic second_tick = 1'b0;
    logic parity_event = 1'b0;
    logic channel_check_event = 1'b0;
    logic external_nmi_event = 1'b0;

    wire memory_request_valid;
    wire memory_command_valid;
    wire memory_write;
    wire memory_code_fetch;
    wire [3:0] memory_cycle_class;
    wire [24:0] memory_address;
    wire [1:0] memory_byte_enable;
    wire [15:0] memory_data_out;
    wire memory_accept;
    wire memory_ready;
    logic [15:0] memory_read_data;
    wire memory_read_data_valid;

    wire dma_memory_valid;
    wire dma_memory_write;
    wire dma_memory_read;
    wire [24:0] dma_memory_address;
    wire [1:0] dma_memory_byte_enable;
    wire [15:0] dma_memory_data_out;
    wire dma_memory_accept;
    wire dma_memory_ready;
    logic [15:0] dma_memory_data_in;

    wire refresh_memory_valid;
    wire [23:0] refresh_memory_address;
    wire refresh_memory_accept;
    wire refresh_memory_ready;

    wire        backend_valid;
    wire        backend_command_valid;
    wire [1:0]  backend_owner;
    wire        backend_write;
    wire        backend_refresh;
    wire        backend_code_fetch;
    wire [3:0]  backend_cycle_class;
    wire [24:0] backend_address;
    wire [1:0]  backend_byte_enable;
    wire [15:0] backend_data_out;
    wire        backend_accept;
    wire        backend_ready;
    logic [15:0] backend_read_data;
    wire        backend_read_data_valid;
    wire        memory_port_protocol_error;
    wire        sdram_owner_protocol_error;

    wire [12:0] sdram_address;
    wire        sdram_cke;
    wire        sdram_cs;
    wire        sdram_ras;
    wire        sdram_cas;
    wire        sdram_we;
    wire [1:0]  sdram_ba;
    logic [15:0] sdram_dq_in;
    wire [15:0] sdram_dq_out;
    wire        sdram_dq_io;
    wire        sdram_ldqm;
    wire        sdram_udqm;

    wire keyboard_output_valid;
    wire [7:0] keyboard_output_byte;
    wire a20_enable;
    wire cpu_reset_request;
    wire intr;
    wire nmi;
    wire [15:0] irq_request;
    wire nmi_mask;
    wire [3:0] selected_device;
    wire unmapped_request;
    wire ata_selected;
    wire floppy_selected;
    wire video_io_selected;
    wire video_memory_selected;
    wire cpu_hold_request;
    wire cpu_hlda;
    wire bus_owner_valid;
    wire [2:0] bus_owner;
    wire dma_grant;
    wire refresh_grant;
    wire bridge_idle;
    wire cpu_ready;
    wire [23:0] cpu_address;
    wire [15:0] cpu_data_out;
    wire [15:0] cpu_data_in;
    wire cpu_data_oe;
    wire cpu_bus_valid;
    wire cpu_bus_write;
    wire cpu_bus_bhe_n;
    wire [3:0] cpu_bus_status;
    wire cpu_bus_lock;
    wire cpu_halted;
    wire cpu_shutdown;
    wire cpu_fault;
    wire [7:0] debug_event_vector;
    wire [7:0] debug_opcode;
    wire [15:0] debug_cs;
    wire [15:0] debug_ip;
    wire [3:0] debug_bus_state;
    wire [15:0] refresh_count;
    wire [15:0] dma_side_effect_count;
    wire [15:0] device_side_effect_count;
    wire protocol_error;

    logic [7:0] rom [0:65535];
    // The IBM 5170 POST probes conventional memory well beyond the first
    // few KiB.  Model the installed 512 KiB as contiguous RAM; the old
    // sparse windows made the BIOS's first-64-KiB test fail by construction.
    logic [7:0] base_ram [0:524287];
    integer index;
    integer rom_file;
    integer loaded_bytes;
    reg [8*512-1:0] rom_path;
    logic runtime_mpu_enable = `ENABLE_MIDI;
    logic runtime_midi_rx = 1'b1;
    logic runtime_mpu_test;
    logic runtime_mpu_switched = 1'b0;
    logic mpu_rx_started = 1'b0;
    logic [7:0] trace_last_8042_status = 8'h00;
    logic [15:0] trace_last_8042_ip = 16'h0000;
    logic trace_last_8042_valid = 1'b0;

    task automatic send_midi_test_byte(input logic [7:0] data);
        integer bit_index;
        begin
            @(negedge clk);
            runtime_midi_rx = 1'b0;
            repeat (8) @(posedge clk);
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                runtime_midi_rx = data[bit_index];
                repeat (16) @(posedge clk);
            end
            runtime_midi_rx = 1'b1;
            repeat (16) @(posedge clk);
        end
    endtask

    always @(posedge clk) begin
        if (!reset && $test$plusargs("MPU_RX_TEST") && !mpu_rx_started &&
            cpu_ready && cpu_bus_valid && cpu_bus_write &&
            (cpu_bus_status == 4'hA) && (cpu_address[15:0] == 16'h0331) &&
            ((cpu_data_out[7:0] == 8'h3f) ||
             (cpu_data_out[15:8] == 8'h3f))) begin
            mpu_rx_started = 1'b1;
            fork
                send_midi_test_byte(8'h55);
            join_none
        end
    end

    integer accepted_memory_beats = 0;
    integer accepted_io_writes = 0;
    integer refresh_beats = 0;
    integer irq0_edges = 0;
    integer port80_writes = 0;
    integer port81_writes = 0;
    integer pit_data_writes = 0;
    integer first_bios_read_count = 0;
    logic [7:0] last_post_code = 8'h00;
    logic [7:0] port80_sequence [0:3];
    logic saw_native_reset_fetch = 1'b0;
    logic saw_native_reset_response = 1'b0;
    logic saw_native_reset_data = 1'b0;
    logic saw_low_rom_fetch = 1'b0;

    function automatic logic [7:0] memory_read_byte(input logic [24:0] address);
        begin
            if ((address >= 25'h00F0000) && (address <= 25'h00FFFFF))
                memory_read_byte = rom[address[15:0]];
            else if (address < 24'h080000)
                memory_read_byte = base_ram[address[18:0]];
            else
                memory_read_byte = 8'h00;
        end
    endfunction

    task automatic write_memory_byte(input logic [24:0] address,
                                     input logic [7:0] value);
        begin
            if (address < 24'h080000)
                base_ram[address[18:0]] <= value;
        end
    endtask

    // Behavioural SDRAM model for the production KFSDRAM owner.  The model
    // uses the logical AT byte map while observing ACT/READ/WRITE commands and
    // DQM on the physical pins.  The production owner maps the logical byte
    // address to a physical SDRAM word with A >> 1, so reconstruct the even
    // byte address at this pin-level boundary.
    logic [12:0] sdram_active_row = 13'h0000;
    logic [1:0]  sdram_active_bank = 2'b00;
    logic [15:0] sdram_read_data_d1 = 16'h0000;
    logic [15:0] sdram_read_data_d2 = 16'h0000;
    wire sdram_command_active = !sdram_cs && !sdram_ras &&
                                 sdram_cas && sdram_we;
    wire sdram_command_read = !sdram_cs && sdram_ras &&
                              !sdram_cas && sdram_we;
    wire sdram_command_write = !sdram_cs && sdram_ras &&
                               !sdram_cas && !sdram_we;
    wire [23:0] sdram_command_address =
        {sdram_active_bank, sdram_active_row, sdram_address[8:0]};
    wire [23:0] sdram_command_byte_address =
        {sdram_command_address[22:0], 1'b0};

    always_ff @(posedge clk) begin
        if (reset) begin
            sdram_active_row <= 13'h0000;
            sdram_active_bank <= 2'b00;
            sdram_read_data_d1 <= 16'h0000;
            sdram_read_data_d2 <= 16'h0000;
        end else begin
            if (sdram_command_active) begin
                sdram_active_row <= sdram_address;
                sdram_active_bank <= sdram_ba;
            end
            if (sdram_command_read) begin
                sdram_read_data_d1 <= {
                    memory_read_byte(sdram_command_byte_address + 24'd1),
                    memory_read_byte(sdram_command_byte_address)
                };
            end
            sdram_read_data_d2 <= sdram_read_data_d1;
            if (sdram_command_write) begin
                if (!sdram_ldqm)
                    write_memory_byte(sdram_command_byte_address,
                                      sdram_dq_out[7:0]);
                if (!sdram_udqm)
                    write_memory_byte(sdram_command_byte_address + 24'd1,
                                      sdram_dq_out[15:8]);
            end
        end
    end

    assign sdram_dq_in = sdram_read_data_d2;

    always_ff @(posedge clk) begin
        if (reset) begin
            accepted_memory_beats <= 0;
            accepted_io_writes <= 0;
            refresh_beats <= 0;
            irq0_edges <= 0;
            port80_writes <= 0;
            port81_writes <= 0;
            pit_data_writes <= 0;
            saw_native_reset_fetch <= 1'b0;
            saw_native_reset_response <= 1'b0;
            saw_native_reset_data <= 1'b0;
            saw_low_rom_fetch <= 1'b0;
            first_bios_read_count <= 0;
        end else begin
            if (backend_accept && (backend_owner == 2'd0)) begin
                accepted_memory_beats <= accepted_memory_beats + 1;
                if (backend_address == 25'h00FFFF0 &&
                    dut.at_memory_address == 24'hFFFFF0)
                    saw_native_reset_fetch <= 1'b1;
                if ((backend_address >= 24'h0F0000) &&
                    (backend_address <= 24'h0FFFFF))
                    saw_low_rom_fetch <= 1'b1;
            end

            // Capture the first returned CPU reads, not only accepted
            // commands.  This makes the test fail if the SDRAM address is
            // right but the returned word/lane/valid timing is wrong.
            if (backend_ready && (backend_owner == 2'd0) && !backend_write &&
                (first_bios_read_count < 32)) begin
                if (first_bios_read_count == 0)
                    $display("AT_FIRST_READ addr=%06h be=%b data=%04h valid=%b",
                             backend_address, backend_byte_enable,
                             backend_read_data, backend_read_data_valid);
                first_bios_read_count <= first_bios_read_count + 1;
                if (backend_address == 25'h00FFFF0 &&
                    dut.at_memory_address == 24'hFFFFF0) begin
                    saw_native_reset_response <= 1'b1;
                    if (backend_read_data_valid &&
                        (((backend_byte_enable == 2'b01) &&
                          (backend_read_data[7:0] == rom[16'hFFF0])) ||
                         ((backend_byte_enable == 2'b10) &&
                          (backend_read_data[15:8] == rom[16'hFFF0])) ||
                         ((backend_byte_enable == 2'b11) &&
                          (backend_read_data == {rom[16'hFFF1], rom[16'hFFF0]}))))
                        saw_native_reset_data <= 1'b1;
                end
            end

            if (backend_accept && (backend_owner == 2'd2))
                refresh_beats <= refresh_beats + 1;
            if (irq_request[0] && !intr)
                irq0_edges <= irq0_edges + 1;

            if (cpu_ready && cpu_bus_valid && cpu_bus_write &&
                (cpu_bus_status == 4'hA)) begin
                if ($test$plusargs("TRACE_8042") &&
                    ((cpu_address[15:0] == 16'h0060) ||
                     (cpu_address[15:0] == 16'h0064)))
                    $display("TRACE_8042 cs:ip=%04h:%04h W port=%04h data=%04h status=%02h a20=%b",
                             debug_cs, debug_ip, cpu_address[15:0], cpu_data_out,
                             dut.u_devices.u_8042.current_read_data,
                             a20_enable);
                accepted_io_writes <= accepted_io_writes + 1;
                if (cpu_address[15:0] == 16'h0080) begin
                    last_post_code <= cpu_data_out[7:0];
                    if ($test$plusargs("TRACE_POST") && port80_writes < 64)
                        $display("TRACE_POST t=%0t cs:ip=%04h:%04h code=%02h",
                                 $time, debug_cs, debug_ip, cpu_data_out[7:0]);
                    if (port80_writes < 4)
                        port80_sequence[port80_writes] <= cpu_data_out[7:0];
                    port80_writes <= port80_writes + 1;
                end
                if (cpu_address[15:0] == 16'h0081)
                    port81_writes <= port81_writes + 1;
                if (cpu_address[15:0] == 16'h0040) begin
                    pit_data_writes <= pit_data_writes + 1;
                    if (pit_data_writes == 1)
                        pit_clock_active <= 1'b1;
                end
            end
            if ($test$plusargs("TRACE_8042") && cpu_ready && cpu_bus_valid &&
                !cpu_bus_write && (cpu_bus_status == 4'h9) &&
                (cpu_address[15:0] == 16'h0060))
                $display("TRACE_8042 cs:ip=%04h:%04h R port=%04h data=%04h status=%02h a20=%b",
                         debug_cs, debug_ip, cpu_address[15:0], cpu_data_in,
                         dut.u_devices.u_8042.current_read_data,
                         a20_enable);
            if ($test$plusargs("TRACE_8042") && cpu_ready && cpu_bus_valid &&
                !cpu_bus_write && (cpu_bus_status == 4'h9) &&
                (cpu_address[15:0] == 16'h0064) &&
                (!trace_last_8042_valid ||
                 (cpu_data_in[7:0] != trace_last_8042_status) ||
                 (debug_ip != trace_last_8042_ip))) begin
                $display("TRACE_8042 cs:ip=%04h:%04h R port=%04h data=%04h status=%02h a20=%b",
                         debug_cs, debug_ip, cpu_address[15:0], cpu_data_in,
                         dut.u_devices.u_8042.current_read_data,
                         a20_enable);
                trace_last_8042_status <= cpu_data_in[7:0];
                trace_last_8042_ip <= debug_ip;
                trace_last_8042_valid <= 1'b1;
            end
        end
    end

    initial begin
        if (!$value$plusargs("ROM=%s", rom_path))
            rom_path = "tests/firmware/pcat286_event_diag.rom";
        rom_file = $fopen(rom_path, "rb");
        if (rom_file == 0)
            $fatal(1, "cannot open AT system ROM: %0s", rom_path);
        loaded_bytes = $fread(rom, rom_file, 0, 65536);
        $fclose(rom_file);
        if (loaded_bytes != 65536)
            $fatal(1, "AT system ROM must be exactly 65536 bytes, got %0d",
                   loaded_bytes);
        for (index = 0; index < 524288; index = index + 1)
            base_ram[index] = 8'h00;
        for (index = 0; index < 4; index = index + 1)
            port80_sequence[index] = 8'h00;
    end

    // Exercise the real machine through the same serialized memory boundary
    // that the future MiSTer SDRAM/HPS owner will use.
    spk286_at_mister_memory_port memory_port (
        .clk(clk), .reset(reset),
        .cancel_cpu(cpu_reset_request),
        .cpu_valid(memory_request_valid),
        .cpu_command_valid(memory_command_valid),
        .cpu_write(memory_write),
        .cpu_code_fetch(memory_code_fetch),
        .cpu_cycle_class(memory_cycle_class),
        .cpu_address(memory_address),
        .cpu_byte_enable(memory_byte_enable),
        .cpu_data_out(memory_data_out),
        .cpu_accept(memory_accept), .cpu_ready(memory_ready),
        .cpu_read_data(memory_read_data),
        .cpu_read_data_valid(memory_read_data_valid),
        .loader_valid(1'b0), .loader_write(1'b0),
        .loader_address(24'h000000), .loader_byte_enable(2'b00),
        .loader_data_out(16'h0000), .loader_accept(), .loader_ready(),
        .loader_read_data(),
        .dma_valid(dma_memory_valid), .dma_write(dma_memory_write),
        .dma_address(dma_memory_address),
        .dma_byte_enable(dma_memory_byte_enable),
        .dma_data_out(dma_memory_data_out),
        .dma_accept(dma_memory_accept), .dma_ready(dma_memory_ready),
        .dma_read_data(dma_memory_data_in),
        .refresh_valid(refresh_memory_valid),
        .refresh_address(refresh_memory_address),
        .refresh_accept(refresh_memory_accept),
        .refresh_ready(refresh_memory_ready),
        .backend_valid(backend_valid),
        .backend_command_valid(backend_command_valid),
        .backend_owner(backend_owner), .backend_write(backend_write),
        .backend_refresh(backend_refresh),
        .backend_code_fetch(backend_code_fetch),
        .backend_cycle_class(backend_cycle_class),
        .backend_address(backend_address),
        .backend_byte_enable(backend_byte_enable),
        .backend_data_out(backend_data_out),
        .backend_accept(backend_accept), .backend_ready(backend_ready),
        .backend_read_data(backend_read_data),
        .backend_read_data_valid(backend_read_data_valid),
        .protocol_error(memory_port_protocol_error)
    );

    wire physical_idle;
    wire        p03_out_valid;
    wire        p03_out_command_valid;
    wire [1:0]  p03_out_owner;
    wire        p03_out_write;
    wire        p03_out_refresh;
    wire        p03_out_code_fetch;
    wire        p03_out_burst;
    wire [3:0]  p03_out_cycle_class;
    wire [24:0] p03_out_address;
    wire [1:0]  p03_out_byte_enable;
    wire [15:0] p03_out_data_out;
    wire        p03_in_accept;
    wire        p03_in_ready;
    wire [15:0] p03_in_read_data;
    wire        p03_in_read_data_valid;
    wire        p03_out_accept;
    wire        p03_out_ready;
    wire [15:0] p03_out_read_data;
    wire        p03_out_read_data_valid;
    wire [31:0] p03_hit_count;
    wire [31:0] p03_miss_count;
    wire [31:0] p03_fill_count;
    wire [31:0] p03_physical_read_count;
    wire [31:0] p03_invalidation_count;
    wire [4:0]  p03_debug_state;

    // Keep the existing logical-backend debug names pointed at the response
    // seen by the memory port. The physical owner handshake is intentionally
    // private to the P03 fill/bypass state machine.
    assign backend_accept          = p03_in_accept;
    assign backend_ready           = p03_in_ready;
    assign backend_read_data       = p03_in_read_data;
    assign backend_read_data_valid = p03_in_read_data_valid;

    // P03 is placed below the single-owner memory port. The port still
    // serializes CPU, DMA, loader and refresh ownership; the buffer can
    // therefore invalidate one line on every accepted write without adding
    // a second coherence arbiter.
    spk286_at_sdram_read_buffer #(
        .ENABLE(1'b1), .LINE_COUNT(512)
    ) u_at_sdram_read_buffer (
        .clk                     (clk),
        .reset                   (reset),
        .cancel_cpu              (cpu_reset_request),
        .enable                  (1'b1),
        .in_valid                (backend_valid),
        .in_command_valid        (backend_command_valid),
        .in_owner                (backend_owner),
        .in_write                (backend_write),
        .in_refresh              (backend_refresh),
        .in_code_fetch           (backend_code_fetch),
        .in_cycle_class          (backend_cycle_class),
        .in_address              (backend_address),
        .in_byte_enable          (backend_byte_enable),
        .in_data_out             (backend_data_out),
        .in_accept               (p03_in_accept),
        .in_ready                (p03_in_ready),
        .in_read_data            (p03_in_read_data),
        .in_read_data_valid      (p03_in_read_data_valid),
        .out_valid               (p03_out_valid),
        .out_command_valid       (p03_out_command_valid),
        .out_owner               (p03_out_owner),
        .out_write               (p03_out_write),
        .out_refresh             (p03_out_refresh),
        .out_code_fetch          (p03_out_code_fetch),
        .out_burst               (p03_out_burst),
        .out_cycle_class         (p03_out_cycle_class),
        .out_address             (p03_out_address),
        .out_byte_enable         (p03_out_byte_enable),
        .out_data_out            (p03_out_data_out),
        .out_accept              (p03_out_accept),
        .out_ready               (p03_out_ready),
        .out_read_data           (p03_out_read_data),
        .out_read_data_valid     (p03_out_read_data_valid),
        .debug_hit_count         (p03_hit_count),
        .debug_miss_count        (p03_miss_count),
        .debug_fill_count        (p03_fill_count),
        .debug_physical_read_count(p03_physical_read_count),
        .debug_invalidation_count(p03_invalidation_count),
        .debug_state             (p03_debug_state)
    );

    wire [7:0]  sdram_owner_debug_state;
    wire        ram_out_valid, ram_out_command, ram_out_write, ram_out_refresh;
    wire        ram_out_code, ram_out_burst, ram_out_accept, ram_out_ready;
    wire        ram_out_read_valid;
    wire [1:0]  ram_out_owner, ram_out_lanes;
    wire [3:0]  ram_out_class;
    wire [24:0] ram_out_address;
    wire [15:0] ram_out_data, ram_out_read_data;
    localparam logic RAM_READ_BUFFER_ENABLED = 1'b1;
    // Both buffers observe canonical addresses and every accepted CPU/DMA/HPS
    // write. RAM data hits do not change physical write completion or P03's
    // instruction-line invalidation. SDRAM remains the final memory owner.
    spk286_at_sdram_data_buffer #(.ENABLE(RAM_READ_BUFFER_ENABLED)) u_at_ram_read_buffer (
        .clk(clk), .reset(reset),
        .cancel_cpu(cpu_reset_request), .enable(1'b1),
        .in_valid(p03_out_valid), .in_command_valid(p03_out_command_valid),
        .in_owner(p03_out_owner), .in_write(p03_out_write),
        .in_refresh(p03_out_refresh), .in_code_fetch(p03_out_code_fetch),
        .in_burst(p03_out_burst), .in_cycle_class(p03_out_cycle_class),
        .in_address(p03_out_address), .in_byte_enable(p03_out_byte_enable),
        .in_data_out(p03_out_data_out), .in_accept(p03_out_accept),
        .in_ready(p03_out_ready), .in_read_data(p03_out_read_data),
        .in_read_data_valid(p03_out_read_data_valid),
        .out_valid(ram_out_valid), .out_command_valid(ram_out_command),
        .out_owner(ram_out_owner), .out_write(ram_out_write),
        .out_refresh(ram_out_refresh), .out_code_fetch(ram_out_code),
        .out_burst(ram_out_burst), .out_cycle_class(ram_out_class),
        .out_address(ram_out_address), .out_byte_enable(ram_out_lanes),
        .out_data_out(ram_out_data), .out_accept(ram_out_accept),
        .out_ready(ram_out_ready), .out_read_data(ram_out_read_data),
        .out_read_data_valid(ram_out_read_valid),
        .debug_hit_count(), .debug_miss_count(), .debug_fill_count(),
        .debug_write_update_count(), .debug_state()
    );
    // One ordinary CPU store may complete logically after retention. Both
    // coherent buffers have observed it before another hit can complete. Any
    // access reaching SDRAM waits for drain; the bridge fences I/O/LOCK/DMA.
    wire at_posted_write_pending, posted_buffer_idle, posted_buffer_error;
    wire physical_owner_idle;
    wire posted_out_valid, posted_out_command, posted_out_write, posted_out_refresh;
    wire posted_out_code, posted_out_burst;
    wire [1:0] posted_out_owner, posted_out_lanes;
    wire [3:0] posted_out_class;
    wire [24:0] posted_out_address;
    wire [15:0] posted_out_data;
    spk286_at_posted_write_buffer u_at_posted_write_buffer (
        .clk(clk), .reset(reset),
        .cancel_cpu(cpu_reset_request), .cpu_lock(cpu_bus_lock),
        .in_valid(ram_out_valid), .in_command_valid(ram_out_command),
        .in_owner(ram_out_owner), .in_write(ram_out_write), .in_refresh(ram_out_refresh),
        .in_code_fetch(ram_out_code), .in_burst(ram_out_burst), .in_cycle_class(ram_out_class),
        .in_address(ram_out_address), .in_byte_enable(ram_out_lanes), .in_data_out(ram_out_data),
        .in_accept(ram_out_accept), .in_ready(ram_out_ready), .in_read_data(ram_out_read_data),
        .in_read_data_valid(ram_out_read_valid),
        .out_valid(posted_out_valid), .out_command_valid(posted_out_command),
        .out_owner(posted_out_owner), .out_write(posted_out_write), .out_refresh(posted_out_refresh),
        .out_code_fetch(posted_out_code), .out_burst(posted_out_burst), .out_cycle_class(posted_out_class),
        .out_address(posted_out_address), .out_byte_enable(posted_out_lanes), .out_data_out(posted_out_data),
        .out_accept(physical_accept), .out_ready(physical_ready), .out_read_data(physical_read_data),
        .out_read_data_valid(physical_read_data_valid),
        .pending_write(at_posted_write_pending), .idle(posted_buffer_idle), .protocol_error(posted_buffer_error),
        .debug_post_count(), .debug_drain_count(), .debug_stall_count()
    );
    wire physical_accept, physical_ready, physical_read_data_valid;
    wire [15:0] physical_read_data;
    // Phase/frequency changes require both the queue and physical owner idle.
    assign physical_idle = physical_owner_idle && posted_buffer_idle;
    spk286_at_mister_sdram_owner #(.SDRAM_INIT_WAIT(16'd32)) u_at_sdram_owner (
        .clk                    (clk),
        .reset                  (reset),
        .request_valid          (posted_out_valid),
        .request_command_valid  (posted_out_command),
        .request_owner_refresh  (posted_out_refresh),
        .request_write          (posted_out_write),
        .request_code_fetch     (posted_out_code),
        .request_burst          (posted_out_burst),
        .request_cycle_class    (posted_out_class),
        .request_address        (posted_out_address),
        .request_byte_enable    (posted_out_lanes),
        .request_data_out       (posted_out_data),
        .request_accept         (physical_accept),
        .request_ready          (physical_ready),
        .request_read_data      (physical_read_data),
        .request_read_data_valid(physical_read_data_valid),
        .physical_idle          (physical_owner_idle),
        .debug_state            (sdram_owner_debug_state),
        .protocol_error         (sdram_owner_protocol_error),
        .sdram_address           (sdram_address),
        .sdram_cke               (sdram_cke),
        .sdram_cs                (sdram_cs),
        .sdram_ras               (sdram_ras),
        .sdram_cas               (sdram_cas),
        .sdram_we                (sdram_we),
        .sdram_ba                (sdram_ba),
        .sdram_dq_in             (sdram_dq_in),
        .sdram_dq_out            (sdram_dq_out),
        .sdram_dq_io             (sdram_dq_io),
        .sdram_ldqm              (sdram_ldqm),
        .sdram_udqm              (sdram_udqm)
    );

    spk286_at_machine dut (
        .clk(clk), .clk_cpu(clk), .cpu_sample_edge(1'b1), .reset(reset), .video_reset(reset),
        .cpu_reset(reset | cpu_local_reset), .clk_video(clk_video), .splashscreen(1'b0),
        .cpu_speed_requested(3'(selected_cpu_profile)),
        .cpu_speed_active(applied_cpu_profile), .cpu_speed_pending(cpu_profile_pending),
        .ega_monitor_profile(2'b00),
        .installed_ram_size_osd(3'd0),
        .at286ctl_eff_mpu401(runtime_mpu_enable),
        .midi_baudce(1'b1), .uart_baudce(1'b1), .midi_rx(runtime_midi_rx),
        .uart1_rx(1'b1),
        .uart2_rx(1'b1), .uart2_cts_n(1'b1), .uart2_dsr_n(1'b1),
        .uart2_dcd_n(1'b1),
        .execute_enable(execute_enable),
        .counter_clock(counter_clock), .refresh_enable(refresh_enable),
        .mgmt_address(16'h0000), .mgmt_writedata(16'h0000),
        .mgmt_write(1'b0), .mgmt_read(1'b0), .mgmt_readdata(),
        .floppy_write_protect(2'b00), .floppy_present(), .floppy_request(),
        .keyboard_byte_valid(keyboard_byte_valid), .keyboard_byte(keyboard_byte),
        .periodic_tick(periodic_tick), .second_tick(second_tick),
        .parity_event(parity_event), .channel_check_event(channel_check_event),
        .external_nmi_event(external_nmi_event),
        .memory_request_valid(memory_request_valid),
        .memory_command_valid(memory_command_valid),
        .memory_write(memory_write), .memory_code_fetch(memory_code_fetch),
        .memory_cycle_class(memory_cycle_class), .memory_address(memory_address),
        .memory_byte_enable(memory_byte_enable), .memory_data_out(memory_data_out),
        .memory_drain_pending(at_posted_write_pending),
        .memory_accept(memory_accept), .memory_ready(memory_ready),
        .memory_read_data(memory_read_data),
        .memory_read_data_valid(memory_read_data_valid),
        .dma_memory_valid(dma_memory_valid), .dma_memory_write(dma_memory_write),
        .dma_memory_read(dma_memory_read),
        .dma_memory_address(dma_memory_address),
        .dma_memory_byte_enable(dma_memory_byte_enable),
        .dma_memory_data_out(dma_memory_data_out),
        .dma_memory_accept(dma_memory_accept), .dma_memory_ready(dma_memory_ready),
        .dma_memory_data_in(dma_memory_data_in),
        .refresh_memory_valid(refresh_memory_valid),
        .refresh_memory_address(refresh_memory_address),
        .refresh_memory_accept(refresh_memory_accept),
        .refresh_memory_ready(refresh_memory_ready),
        .keyboard_output_valid(keyboard_output_valid),
        .keyboard_output_byte(keyboard_output_byte), .a20_enable(a20_enable),
        .cpu_reset_request(cpu_reset_request), .intr(intr), .nmi(nmi),
        .irq_request(irq_request), .nmi_mask(nmi_mask),
        .selected_device(selected_device), .unmapped_request(unmapped_request),
        .ata_selected(ata_selected), .floppy_selected(floppy_selected),
        .video_io_selected(video_io_selected),
        .video_memory_selected(video_memory_selected),
        .cpu_hold_request(cpu_hold_request), .cpu_hlda(cpu_hlda),
        .bus_owner_valid(bus_owner_valid), .bus_owner(bus_owner),
        .dma_grant(dma_grant), .refresh_grant(refresh_grant),
        .bridge_idle(bridge_idle), .cpu_ready(cpu_ready),
        .cpu_address(cpu_address), .cpu_data_out(cpu_data_out),
        .cpu_data_in(cpu_data_in), .cpu_data_oe(cpu_data_oe),
        .cpu_bus_valid(cpu_bus_valid), .cpu_bus_write(cpu_bus_write),
        .cpu_bus_bhe_n(cpu_bus_bhe_n), .cpu_bus_status(cpu_bus_status),
        .cpu_bus_lock(cpu_bus_lock), .cpu_halted(cpu_halted),
        .cpu_shutdown(cpu_shutdown), .cpu_fault(cpu_fault),
        .debug_event_vector(debug_event_vector), .debug_opcode(debug_opcode),
        .debug_cs(debug_cs), .debug_ip(debug_ip),
        .debug_gpr(debug_gpr),
        .debug_bus_state(debug_bus_state), .refresh_count(refresh_count),
        .dma_side_effect_count(dma_side_effect_count),
        .device_side_effect_count(device_side_effect_count),
        .protocol_error(protocol_error)
    );


    wire [127:0] debug_gpr;
    integer iterations, kernel_ip, kernel_length, trace_fd, backend_fd;
    integer cycle = 0, first_edge = -1, last_edge = -1, loops_retired = 0;
    integer kernel_retirements = 0, kernel_extensions = 0;
    logic in_kernel = 0;
    string trace_path, backend_path, ram_path, kind;
    always @(posedge clk) begin : observer
        integer expected_ax;
        if (!reset) begin
            cycle = cycle + 1;
            if (backend_fd != 0)
                $fdisplay(backend_fd,"%0d,%0d,%0d,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
                    cycle,backend_valid,backend_command_valid,backend_code_fetch,backend_address,
                    backend_accept,backend_ready,cpu_ready,refresh_grant,cpu_hold_request,
                    p03_debug_state,p03_hit_count,p03_miss_count,physical_accept,
                    posted_out_address,physical_ready,physical_read_data_valid,
                    sdram_command_read,dut.u_bridge.timing_deadline_miss,
                    dut.u_bridge.state_q,dut.u_bridge.timing_active_q,
                    dut.u_bridge.timing_tc_q,dut.u_bridge.timing_admission_window_q,
                    dut.timing_cpu_boundary,dut.u_cpu.cpu.fetch.active_q,
                    dut.u_cpu.cpu.fetch.response_fire);

            if (dut.u_cpu.cpu.opcode_start && debug_cs == 16'h106E &&
                debug_ip == 16'(kernel_ip) && first_edge < 0) begin
                first_edge = cycle;
                in_kernel = 1;
            end
            if (in_kernel && dut.u_cpu.cpu.profile_retire_fire) begin
                kernel_retirements = kernel_retirements + 1;
                if (dut.u_cpu.cpu.profile_implementation_extension)
                    kernel_extensions = kernel_extensions + 1;
                if (dut.u_cpu.cpu.opcode_q == 8'hE2) begin
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
                    cycle, applied_cpu_profile, dut.timing_cpu_boundary, in_kernel, debug_cs, debug_ip,
                    dut.u_cpu.cpu.opcode_q, dut.u_cpu.cpu.queue_consume_data,
                    dut.u_cpu.cpu.opcode_start, dut.u_cpu.cpu.profile_start_interval,
                    dut.u_cpu.cpu.profile_start_body, dut.u_cpu.cpu.profile_metadata_valid,
                    dut.u_cpu.cpu.profile_metadata_clocks, dut.u_cpu.cpu.profile_body_active,
                    dut.u_cpu.cpu.profile_head_permit, dut.u_cpu.cpu.profile_deadline_ready,
                    dut.u_cpu.cpu.raw_retired, dut.u_cpu.cpu.profile_retire_pending,
                    dut.u_cpu.cpu.profile_retire_fire, dut.u_cpu.cpu.profile_elapsed,
                    dut.u_cpu.cpu.profile_scheduled, dut.u_cpu.cpu.profile_implementation_extension,
                    dut.u_cpu.cpu.queue_count, dut.u_cpu.cpu.queue_consume_valid,
                    dut.u_cpu.cpu.queue_consume_ready, cpu_bus_valid, cpu_bus_status, cpu_address,
                    cpu_bus_write, cpu_ready, dut.u_cpu.cpu.fetch_bus_valid,
                    dut.u_cpu.cpu.fetch_bus_ready, dut.u_cpu.cpu.fetch_response_valid,
                    dut.u_cpu.cpu.fetch_response_ready, dut.u_cpu.cpu.timing_prefetch_response_accept,
                    debug_gpr);
            if (cpu_shutdown || cpu_fault || protocol_error || memory_port_protocol_error || sdram_owner_protocol_error || posted_buffer_error)
                $fatal(1, "Production CPU rejected original R0/baseline program");
            if (cpu_halted && physical_idle) begin
                if (kernel_retirements != iterations * (kind == "r0" ? 5 : 1) ||
                    debug_gpr[79:64] !== 16'hFF00)
                    $fatal(1, "Kernel work or stack mismatch");
                if (first_edge < 0 || last_edge < 0 || loops_retired != iterations)
                    $fatal(1, "Kernel did not execute complete fixed work");
                expected_ax = kind == "r0" ?
                    (16'h1234 + iterations * 16'h5678 + iterations * (iterations - 1) / 2) & 65535 : 16'h1234;
                if (debug_gpr[15:0] !== 16'(expected_ax) || debug_gpr[31:16] !== 0 ||
                    debug_gpr[47:32] !== 16'h9ABC ||
                    debug_gpr[63:48] !== 16'(16'h5678 + (kind == "r0" ? iterations : 0)) ||
                    debug_gpr[127:112] !== 16'hDEF0)
                    $fatal(1, "Original kernel architectural signature failed");
                $display("P06_R0_PCAT_PASS profile=%0d kind=%s iterations=%0d start=%0d end=%0d fabric_clocks=%0d instructions=%0d extensions=%0d kernel_ip=%04h kernel_length=%0d", applied_cpu_profile, kind, iterations, first_edge, last_edge, last_edge-first_edge, kernel_retirements, kernel_extensions, 16'(kernel_ip), kernel_length);
                $display("P06_PCAT_CACHE hits=%0d misses=%0d fills=%0d physical_reads=%0d",
                         p03_hit_count,p03_miss_count,p03_fill_count,p03_physical_read_count);
                $fclose(trace_fd); $fclose(backend_fd); $finish;
            end
            if (cycle > 500000) $fatal(1, "Bounded PCAT watchdog");
        end
    end


    initial begin : trace_run
        if (!$value$plusargs("CPU_PROFILE=%d", selected_cpu_profile) ||
            !$value$plusargs("LOOPS=%d", iterations) ||
            !$value$plusargs("KERNEL_IP=%d", kernel_ip) ||
            !$value$plusargs("KERNEL_LENGTH=%d", kernel_length) ||
            !$value$plusargs("KIND=%s", kind) ||
            !$value$plusargs("RAM=%s", ram_path) ||
            !$value$plusargs("TRACE=%s", trace_path) ||
            !$value$plusargs("BACKEND_TRACE=%s", backend_path)) $fatal(1,"Missing arguments");
        if ((selected_cpu_profile != 6 && selected_cpu_profile != 7) ||
            (iterations != 32 && iterations != 256) ||
            (kind != "baseline" && kind != "r0")) $fatal(1,"Out-of-scope run");
        // PIT/AT refresh is intentionally unprogrammed; owner SDRAM refresh
        // stays active. This isolates the CPU + common-clock memory chain.
        refresh_enable = 0;
        #1; $readmemh(ram_path,base_ram);
        trace_fd = $fopen(trace_path,"w");
        backend_fd = $fopen(backend_path,"w");
        if (!trace_fd || !backend_fd) $fatal(1,"Cannot open trace files");
        $fdisplay(trace_fd,"edge,profile,cpu_boundary,in_kernel,cs,ip,opcode,queue_byte,opcode_start,start_interval,start_body,metadata_valid,metadata_clocks,body_active,head_permit,deadline_ready,raw_retired,retire_pending,retire_fire,elapsed,scheduled,implementation_extension,queue_count,consume_valid,consume_ready,bus_valid,bus_status,address,write,ready,fetch_valid,fetch_ready,fetch_response_valid,fetch_response_ready,refill_accept,gpr");
        $fdisplay(backend_fd,"edge,valid,command,code,address,accept,ready,cpu_ready,refresh_grant,cpu_hold,p03_state,p03_hits,p03_misses,physical_accept,physical_address,physical_ready,physical_read_valid,sdram_read,bridge_deadline_miss,bridge_state,timing_active,timing_tc,admission_window,cpu_boundary,fetch_active,fetch_response_fire");
        repeat(8) @(negedge clk);
        reset = 0;
        #1;
        if (applied_cpu_profile !== 3'(selected_cpu_profile) || cpu_profile_pending)
            $fatal(1,"Profile not applied through reset");
    end
    initial begin #11_000_000; $fatal(1,"PCAT trace timeout"); end
endmodule
