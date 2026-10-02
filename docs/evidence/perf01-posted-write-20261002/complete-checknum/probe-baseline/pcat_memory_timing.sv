`timescale 1ns/1ps
// Timing/control co-simulation only: guest values remain owned by 86Box.
// Constant SDRAM DQ cannot affect cache tags, arbitration or READY sequencing.
module pcat_memory_timing (
    input logic clk, reset, cpu_reset,
    input logic [23:0] address,
    input logic [24:0] mapped_at_address,
    input logic [15:0] data_out,
    input logic data_oe, bus_valid, bus_write, bus_bhe_n, bus_lock,
    input logic [3:0] bus_status,
    output wire ready,
    output wire [15:0] data_in,
    output wire protocol_error,
    output wire idle, pending_write,
    output wire [31:0] stat_posted_count, stat_drained_count, stat_posted_stalls,
    output wire owner_accept, owner_refresh,
    output wire [1:0] owner_kind,
    output wire [3:0] bridge_state,
    output wire [31:0] stat_p03_hits,
    output wire [31:0] stat_p03_misses,
    output wire [31:0] stat_p03_fills,
    output wire [31:0] stat_p03_invalidations,
    output wire [31:0] stat_data_buffer_hits,
    output wire [31:0] stat_data_buffer_misses,
    output wire [31:0] stat_data_buffer_fills,
    output wire [31:0] stat_data_buffer_updates
);

    integer p03_enable = 1;
    integer data_buffer_enable = 1;
    localparam integer CODE_BUFFER_LINES = 512;
    wire at_valid, at_command, at_write, at_code;
    wire at_accept, at_ready, at_read_valid, bridge_error;
    wire [23:0] at_address;
    wire [1:0] at_lanes;
    wire [15:0] at_out, at_in;
    wire [3:0] at_class;

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

    spk286_at_bus_bridge bridge (
        .clk(clk), .reset(cpu_reset), .cpu_sample_edge(1'b1),
        .cpu_bus_valid(bus_valid),
        .cpu_address(address), .cpu_data_out(data_out), .cpu_data_oe(data_oe),
        .cpu_bus_write(bus_write), .cpu_bus_bhe_n(bus_bhe_n),
        .cpu_bus_status(bus_status), .cpu_bus_lock(bus_lock),
        .memory_drain_pending(posted_pending),
        .cpu_memory_word_capable(1'b1),
        .cpu_io_word_capable(1'b0),
        .cpu_ready(ready), .cpu_data_in(data_in),
        .at_valid(at_valid), .at_command_valid(at_command),
        .at_cycle_class(at_class), .at_address(at_address),
        .at_byte_enable(at_lanes), .at_data_out(at_out), .at_write(at_write),
        .at_code_fetch(at_code), .at_accept(at_accept), .at_ready(at_ready),
        .at_read_data(at_in), .at_read_data_valid(at_read_valid),
        .protocol_error(bridge_error)
    );

    spk286_at_mister_memory_port memory_port (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset),
        .cpu_valid(at_valid), .cpu_command_valid(at_command),
        .cpu_write(at_write), .cpu_code_fetch(at_code),
        .cpu_cycle_class(at_class), .cpu_address(mapped_at_address),
        .cpu_byte_enable(at_lanes), .cpu_data_out(at_out),
        .cpu_accept(at_accept), .cpu_ready(at_ready),
        .cpu_read_data(at_in), .cpu_read_data_valid(at_read_valid),
        .loader_valid(1'b0), .loader_write(1'b0), .loader_address(24'd0),
        .loader_byte_enable(2'b00), .loader_data_out(16'd0),
        .loader_accept(), .loader_ready(), .loader_read_data(),
        .dma_valid(1'b0), .dma_write(1'b0), .dma_address(25'd0),
        .dma_byte_enable(2'b00), .dma_data_out(16'd0),
        .dma_accept(), .dma_ready(), .dma_read_data(),
        .refresh_valid(1'b0), .refresh_address(24'd0),
        .refresh_accept(), .refresh_ready(),
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

    spk286_at_posted_write_buffer #(.ENABLE(0)) posted_buffer (
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
        .clk(clk), .reset(reset), .request_valid(posted_out_valid),
        .request_command_valid(posted_out_command),
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


    assign pending_write = posted_pending;
    assign stat_posted_count = posted_count;
    assign stat_drained_count = drained_count;
    assign stat_posted_stalls = posted_stalls;
    assign dram_in = 16'd0;
    assign protocol_error = bridge_error || port_error || owner_error || posted_error;
    assign idle = bridge.bridge_idle && physical_idle && posted_idle;
    assign owner_accept = posted_out_valid && posted_out_command && physical_accept;
    assign owner_refresh = owner.kf_refresh_mode;
    assign owner_kind = posted_out_write ? 2'd2 : posted_out_code ? 2'd0 : 2'd1;
    assign bridge_state = bridge.debug_state;
    assign stat_p03_hits = p03_hits;
    assign stat_p03_misses = p03_misses;
    assign stat_p03_fills = p03_fills;
    assign stat_p03_invalidations = p03_invalidations;
    assign stat_data_buffer_hits = data_buffer_hits;
    assign stat_data_buffer_misses = data_buffer_misses;
    assign stat_data_buffer_fills = data_buffer_fills;
    assign stat_data_buffer_updates = data_buffer_updates;
endmodule
