`timescale 1ns/1ps
module posted_cache_tb;
    logic clk = 0, reset = 1, cpu_reset = 1, bus_lock = 0, stall = 0;
    always #10 clk = ~clk;
    localparam integer CODE_BUFFER_LINES = 512, POSTED_WRITES = 1;
    integer p03_enable = 1, data_buffer_enable = 1;
    logic [1:0] driver_owner = 0;
    wire [3:0] owner_accept, owner_ready;
    wire [15:0] cpu_data, dma_data, loader_data;
    integer checks = 0, cycles = 0, stores = 0;
    logic at_valid = 0, at_command = 0, at_write = 0, at_code = 0;
    wire at_accept, at_ready, at_read_valid, bridge_error;
    logic [23:0] at_address = 0;
    // This reduced harness bypasses spk286_at_machine. Supply its BIOS alias
    // mapping explicitly; the physical SDRAM owner no longer masks addresses.
    wire [24:0] mapped_at_address = at_address[23:16] == 8'hFF
        ? {9'h00F, at_address[15:0]} : {1'b0, at_address};
    logic [1:0] at_lanes = 3;
    logic [15:0] at_out = 0; wire [15:0] at_in;
    logic [3:0] at_class = 5;

    wire backend_valid, backend_command, backend_write, backend_refresh;
    wire backend_code, backend_accept, backend_ready, backend_read_valid;
    wire [1:0] backend_owner;
    wire [24:0] backend_address;
    wire [1:0] backend_lanes;
    wire [15:0] backend_out, backend_in;
    wire [3:0] backend_class;
    wire port_error, owner_error, physical_idle;

    wire p03_out_valid, p03_out_command;
    wire [1:0] p03_out_owner;
    wire p03_out_write, p03_out_refresh, p03_out_code, p03_out_burst;
    wire [3:0] p03_out_class;
    wire [24:0] p03_out_address;
    wire [1:0] p03_out_lanes;
    wire [15:0] p03_out_data;
    wire p03_in_accept, p03_in_ready, p03_in_read_valid;
    wire [15:0] p03_in_data;
    wire p03_out_accept, p03_out_ready, p03_out_read_valid;
    wire [15:0] p03_out_read_data;
    wire physical_accept, physical_ready, physical_read_valid;
    wire [15:0] physical_read_data;
    wire [31:0] p03_hits, p03_misses, p03_fills, p03_physical_reads;
    wire [31:0] p03_invalidations;
    wire memory_out_valid, memory_out_command, memory_out_write, memory_out_refresh;
    wire memory_out_code, memory_out_burst, memory_out_accept, memory_out_ready;
    wire memory_out_read_valid;
    wire [1:0] memory_out_owner, memory_out_lanes;
    wire [3:0] memory_out_class;
    wire [24:0] memory_out_address;
    wire [15:0] memory_out_data, memory_out_read_data;
    wire [31:0] data_buffer_hits, data_buffer_misses, data_buffer_fills, data_buffer_updates;
    wire posted_pending, posted_idle, posted_error;
    wire posted_out_valid, posted_out_command, posted_out_write, posted_out_refresh;
    wire posted_out_code, posted_out_burst;
    wire [1:0] posted_out_owner, posted_out_lanes;
    wire [3:0] posted_out_class;
    wire [24:0] posted_out_address;
    wire [15:0] posted_out_data;
    wire [31:0] posted_count, drained_count, posted_stalls;

    wire [12:0] dram_address;
    wire dram_cke, dram_cs, dram_ras, dram_cas, dram_we, dram_oe;
    wire [1:0] dram_ba, dram_dqm, dq_valid;
    wire [15:0] dram_in, dram_out;
    wire integer dram_reads, dram_writes;

    spk286_at_mister_memory_port memory_port (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset),
        .cpu_valid(at_valid && driver_owner == 0), .cpu_command_valid(at_command),
        .cpu_write(at_write), .cpu_code_fetch(at_code),
        .cpu_cycle_class(at_class), .cpu_address(mapped_at_address),
        .cpu_byte_enable(at_lanes), .cpu_data_out(at_out),
        .cpu_accept(owner_accept[0]), .cpu_ready(owner_ready[0]),
        .cpu_read_data(cpu_data), .cpu_read_data_valid(at_read_valid),
        .loader_valid(at_valid && driver_owner == 3), .loader_write(at_write), .loader_address(at_address),
        .loader_byte_enable(at_lanes), .loader_data_out(at_out),
        .loader_accept(owner_accept[3]), .loader_ready(owner_ready[3]), .loader_read_data(loader_data),
        .dma_valid(at_valid && driver_owner == 1), .dma_write(at_write), .dma_address(mapped_at_address),
        .dma_byte_enable(at_lanes), .dma_data_out(at_out),
        .dma_accept(owner_accept[1]), .dma_ready(owner_ready[1]), .dma_read_data(dma_data),
        .refresh_valid(at_valid && driver_owner == 2), .refresh_address(at_address),
        .refresh_accept(owner_accept[2]), .refresh_ready(owner_ready[2]),
        .backend_valid(backend_valid), .backend_command_valid(backend_command),
        .backend_owner(backend_owner), .backend_write(backend_write),
        .backend_refresh(backend_refresh), .backend_code_fetch(backend_code),
        .backend_cycle_class(backend_class), .backend_address(backend_address),
        .backend_byte_enable(backend_lanes), .backend_data_out(backend_out),
        .backend_accept(p03_in_accept), .backend_ready(p03_in_ready),
        .backend_read_data(p03_in_data),
        .backend_read_data_valid(p03_in_read_valid),
        .protocol_error(port_error)
    );

`ifdef PCAT_CODE_BUFFER_EXPERIMENT
    spk286_at_multiline_code_buffer_model #(.ENABLE(1'b1)) p03_buffer (
`else
    spk286_at_sdram_read_buffer #(.ENABLE(1'b1), .LINE_COUNT(CODE_BUFFER_LINES)) p03_buffer (
`endif
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset),
        .enable(p03_enable != 0),
        .in_valid(backend_valid), .in_command_valid(backend_command),
        .in_owner(backend_owner), .in_write(backend_write),
        .in_refresh(backend_refresh), .in_code_fetch(backend_code),
        .in_cycle_class(backend_class), .in_address(backend_address),
        .in_byte_enable(backend_lanes), .in_data_out(backend_out),
        .in_accept(p03_in_accept), .in_ready(p03_in_ready),
        .in_read_data(p03_in_data), .in_read_data_valid(p03_in_read_valid),
        .out_valid(p03_out_valid), .out_command_valid(p03_out_command),
        .out_owner(p03_out_owner), .out_write(p03_out_write),
        .out_refresh(p03_out_refresh), .out_code_fetch(p03_out_code),
        .out_burst(p03_out_burst), .out_cycle_class(p03_out_class),
        .out_address(p03_out_address), .out_byte_enable(p03_out_lanes),
        .out_data_out(p03_out_data), .out_accept(p03_out_accept),
        .out_ready(p03_out_ready), .out_read_data(p03_out_read_data),
        .out_read_data_valid(p03_out_read_valid),
        .debug_hit_count(p03_hits), .debug_miss_count(p03_misses),
        .debug_fill_count(p03_fills),
        .debug_physical_read_count(p03_physical_reads),
        .debug_invalidation_count(p03_invalidations)
    );

    spk286_at_sdram_data_buffer data_buffer (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset), .enable(data_buffer_enable != 0),
        .in_valid(p03_out_valid), .in_command_valid(p03_out_command),
        .in_owner(p03_out_owner), .in_write(p03_out_write), .in_refresh(p03_out_refresh),
        .in_code_fetch(p03_out_code), .in_burst(p03_out_burst), .in_cycle_class(p03_out_class),
        .in_address(p03_out_address), .in_byte_enable(p03_out_lanes), .in_data_out(p03_out_data),
        .in_accept(p03_out_accept), .in_ready(p03_out_ready), .in_read_data(p03_out_read_data),
        .in_read_data_valid(p03_out_read_valid),
        .out_valid(memory_out_valid), .out_command_valid(memory_out_command),
        .out_owner(memory_out_owner), .out_write(memory_out_write), .out_refresh(memory_out_refresh),
        .out_code_fetch(memory_out_code), .out_burst(memory_out_burst), .out_cycle_class(memory_out_class),
        .out_address(memory_out_address), .out_byte_enable(memory_out_lanes), .out_data_out(memory_out_data),
        .out_accept(memory_out_accept), .out_ready(memory_out_ready), .out_read_data(memory_out_read_data),
        .out_read_data_valid(memory_out_read_valid), .debug_hit_count(data_buffer_hits),
        .debug_miss_count(data_buffer_misses), .debug_fill_count(data_buffer_fills),
        .debug_write_update_count(data_buffer_updates), .debug_state()
    );

    spk286_at_posted_write_buffer #(.ENABLE(POSTED_WRITES != 0)) posted_buffer (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset), .cpu_lock(bus_lock),
        .in_valid(memory_out_valid), .in_command_valid(memory_out_command),
        .in_owner(memory_out_owner), .in_write(memory_out_write),
        .in_refresh(memory_out_refresh), .in_code_fetch(memory_out_code),
        .in_burst(memory_out_burst), .in_cycle_class(memory_out_class),
        .in_address(memory_out_address), .in_byte_enable(memory_out_lanes),
        .in_data_out(memory_out_data), .in_accept(memory_out_accept),
        .in_ready(memory_out_ready), .in_read_data(memory_out_read_data),
        .in_read_data_valid(memory_out_read_valid),
        .out_valid(posted_out_valid), .out_command_valid(posted_out_command),
        .out_owner(posted_out_owner), .out_write(posted_out_write),
        .out_refresh(posted_out_refresh), .out_code_fetch(posted_out_code),
        .out_burst(posted_out_burst), .out_cycle_class(posted_out_class),
        .out_address(posted_out_address), .out_byte_enable(posted_out_lanes),
        .out_data_out(posted_out_data), .out_accept(physical_accept),
        .out_ready(physical_ready), .out_read_data(physical_read_data),
        .out_read_data_valid(physical_read_valid),
        .pending_write(posted_pending), .idle(posted_idle), .protocol_error(posted_error),
        .debug_post_count(posted_count), .debug_drain_count(drained_count),
        .debug_stall_count(posted_stalls)
    );

    spk286_at_mister_sdram_owner #(.SDRAM_INIT_WAIT(16'd8)) owner (
        .clk(clk), .reset(reset), .request_valid(posted_out_valid && !stall),
        .request_command_valid(posted_out_command && !stall),
        .request_owner_refresh(posted_out_refresh), .request_write(posted_out_write),
        .request_code_fetch(posted_out_code), .request_burst(posted_out_burst),
        .request_cycle_class(posted_out_class), .request_address(posted_out_address),
        .request_byte_enable(posted_out_lanes), .request_data_out(posted_out_data),
        .request_accept(physical_accept), .request_ready(physical_ready),
        .request_read_data(physical_read_data),
        .request_read_data_valid(physical_read_valid),
        .physical_idle(physical_idle), .protocol_error(owner_error),
        .sdram_address(dram_address), .sdram_cke(dram_cke),
        .sdram_cs(dram_cs), .sdram_ras(dram_ras), .sdram_cas(dram_cas),
        .sdram_we(dram_we), .sdram_ba(dram_ba), .sdram_dq_in(dram_in),
        .sdram_dq_out(dram_out), .sdram_dq_io(dram_oe),
        .sdram_ldqm(dram_dqm[0]), .sdram_udqm(dram_dqm[1])
    );

    spk286_sdram_pin_model pins (
        .clk(clk), .reset(reset), .address(dram_address), .cke(dram_cke),
        .cs_n(dram_cs), .ras_n(dram_ras), .cas_n(dram_cas), .we_n(dram_we),
        .ba(dram_ba), .dq_from_controller(dram_out),
        .controller_dq_oe(!dram_oe), .dqm(dram_dqm),
        .dq_to_controller(dram_in), .dq_valid(dq_valid),
        .read_count(dram_reads), .write_count(dram_writes)
    );


    assign at_accept = owner_accept[driver_owner];
    assign at_ready = owner_ready[driver_owner];
    assign at_in = driver_owner == 1 ? dma_data : driver_owner == 3 ? loader_data : cpu_data;
    task automatic check(input logic condition, input string message);
        checks++;
        if (!condition) $fatal(1, "POSTED_CACHE check %0d: %s", checks, message);
    endtask
    task automatic admit(input logic [1:0] initiator, input logic write_cycle,
                         input logic fetch, input logic [23:0] addr,
                         input logic [1:0] bytes, input logic [15:0] value);
        integer guard;
        @(negedge clk);
        driver_owner = initiator; at_valid = 1; at_command = 1;
        at_write = write_cycle; at_code = fetch; at_address = addr;
        at_lanes = bytes; at_out = value; at_class = write_cycle ? 6 : fetch ? 13 : 5;
        #1; guard = 0;
        while (!at_accept && guard < 400) begin @(negedge clk); #1; guard++; end
        check(at_accept && !at_ready, "accepted exactly before completion");
        @(posedge clk); #1;
        at_valid = 0; at_command = 0; at_address = 24'hffffff; at_lanes = 0; at_out = 16'hdead;
    endtask
    task automatic response(input logic read_cycle, input logic [15:0] expected = 0);
        integer guard;
        guard = 0;
        while (!at_ready && guard < 400) begin @(negedge clk); #1; guard++; end
        check(at_ready, "logical response deadline");
        if (read_cycle) check(at_in == expected, "read observes the latest retained/physical value");
        @(posedge clk); #1;
    endtask
    task automatic put(input logic [1:0] initiator, input logic [23:0] addr,
                       input logic [1:0] bytes, input logic [15:0] value);
        admit(initiator, 1, 0, addr, bytes, value); response(0); stores++;
    endtask
    task automatic get(input logic [1:0] initiator, input logic fetch,
                       input logic [23:0] addr, input logic [15:0] expected);
        admit(initiator, 0, fetch, addr, 3, 0); response(1, expected);
    endtask
    task automatic drain;
        integer guard;
        guard = 0;
        while ((!posted_idle || !physical_idle) && guard < 400) begin @(negedge clk); #1; guard++; end
        check(posted_idle && physical_idle, "posted drain deadline");
    endtask
    always @(posedge clk) begin
        cycles++;
        if (cycles > 10000) $fatal(1, "POSTED_CACHE timeout");
        if (!reset && (port_error || owner_error || posted_error)) $fatal(1, "POSTED_CACHE protocol error");
    end
    initial begin
        pins.mem['h1000] = 16'habcd;
        for (integer i = 0; i < 4; i++) pins.mem['h2000+i] = 16'h4100 + 16'(i);
        repeat (3) @(negedge clk); reset = 0; wait(physical_idle);
        @(negedge clk); cpu_reset = 0;
        get(0, 0, 24'h2000, 16'habcd);
        get(0, 1, 24'h4000, 16'h4100);
        // Retain without physical admission. Both caches must continue hits.
        stall = 1;
        put(0, 24'h2001, 2'b10, 16'h1200);
        check(posted_pending && pins.mem['h1000] == 16'habcd, "ACK precedes physical write");
        get(0, 0, 24'h2000, 16'h12cd);
        get(0, 1, 24'h4000, 16'h4100);
        check(posted_pending && data_buffer_updates == 1 && p03_hits > 0,
              "updated data and unrelated code hit while a store is pending");
        // DMA read must wait even if the CPU data cache contains its word.
        fork
            begin
                @(negedge clk); driver_owner = 1; at_valid = 1; at_command = 1;
                at_write = 0; at_code = 0; at_class = 5; at_address = 24'h2000; at_lanes = 3;
                repeat (8) begin @(negedge clk); #1; check(!at_ready, "DMA cannot pass pending write"); end
                while (!at_accept) begin @(negedge clk); #1; end
                @(posedge clk); #1; at_valid = 0; at_command = 0;
                response(1, 16'h12cd);
            end
            begin repeat (12) @(negedge clk); stall = 0; end
        join
        drain();
        check(pins.mem['h1000] == 16'h12cd, "masked store physically drains");

        // A code-line write invalidates before early ACK; a later fetch stalls
        // until drain and fills from physical memory rather than stale code.
        stall = 1;
        put(0, 24'h4001, 2'b10, 16'h9200);
        check(posted_pending && p03_invalidations == 1, "code invalidation precedes later fetch");
        admit(0, 0, 1, 24'h4000, 3, 0);
        repeat (8) begin @(negedge clk); #1; check(!at_ready, "conflicting code miss waits for drain"); end
        stall = 0; response(1, 16'h9200); drain();

        // Warm data gets flushed by a CPU reset after local capture but before
        // the early completion edge. The lower retained write is irrevocable.
        get(0, 0, 24'h2000, 16'h12cd);
        stall = 1;
        admit(0, 1, 0, 24'h2000, 3, 16'h7788); stores++;
        cpu_reset = 1;
        repeat (4) begin @(negedge clk); #1; check(posted_pending && !at_ready, "CPU reset suppresses response, keeps store"); end
        cpu_reset = 0;
        admit(0, 0, 0, 24'h2000, 3, 0);
        repeat (5) begin @(negedge clk); #1; check(!at_ready, "new CPU fetch cannot inherit old completion"); end
        stall = 0; response(1, 16'h7788); drain();
        // Non-CPU cache-coherent writers do not acknowledge early.
        put(1, 24'h2000, 3, 16'h1122); drain(); get(0, 0, 24'h2000, 16'h1122);
        put(3, 24'h2001, 2'b10, 16'h3300); drain(); get(0, 0, 24'h2000, 16'h3322);
        // Odd word represented as two canonical lane writes; repeated same
        // address stores must never be merged or suppressed.
        put(0, 24'h2001, 2'b10, 16'h4400);
        put(0, 24'h2002, 2'b01, 16'h0055);
        get(0, 0, 24'h2000, 16'h4422); get(0, 0, 24'h2002, 16'h0055); drain();
        for (integer i = 0; i < 16; i++) put(0, 24'h2000, 3, 16'h6000 + 16'(i));
        get(0, 0, 24'h2000, 16'h600f); drain();
        // Three tags mapping to one set exercise replacement after posting.
        for (integer i = 0; i < 3; i++) begin
            put(0, 24'h3000 + 24'(i*512), 3, 16'h8000 + 16'(i));
            get(0, 0, 24'h3000 + 24'(i*512), 16'h8000 + 16'(i));
        end
        for (integer i = 0; i < 3; i++) get(0, 0, 24'h3000 + 24'(i*512), 16'h8000 + 16'(i));
        drain();
        check(dram_writes == stores && posted_count == drained_count, "all writers physically complete exactly once");
        $display("AT_POSTED_CACHE_PASS checks=%0d stores=%0d posted=%0d drained=%0d cycles=%0d",
                 checks, stores, posted_count, drained_count, cycles);
        $finish;
    end

endmodule
