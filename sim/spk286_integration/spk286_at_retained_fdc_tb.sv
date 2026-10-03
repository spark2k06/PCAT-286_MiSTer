`timescale 1ns/1ps
module spk286_at_retained_fdc_tb;
    logic  clk = 1'b0;
    logic  bridge_reset = 1'b1;
    logic  cpu_sample_edge = 1'b0;
    logic  cpu_bus_valid = 1'b0;
    logic [23:0] cpu_address = '0;
    logic [15:0] cpu_data_out = '0;
    logic  cpu_data_oe = 1'b0;
    logic  cpu_bus_write = 1'b0;
    logic  cpu_bus_bhe_n = 1'b1;
    logic [3:0] cpu_bus_status = '0;
    logic  cpu_bus_lock = 1'b0;
    logic  memory_drain_pending = 1'b0;
    logic  cpu_memory_word_capable = 1'b1;
    logic  cpu_io_word_capable = 1'b0;
    logic  fdc_reset = 1'b1;
    logic  fdc_dma_transfer_valid = 1'b0;
    logic  fdc_dma_transfer_complete = 1'b0;
    logic  fdc_dma_terminal_count = 1'b0;
    logic [2:0] fdc_dma_active_channel = '0;
    logic [15:0] fdc_dma_transfer_data_in = '0;
    logic [15:0] fdc_mgmt_address = '0;
    logic [15:0] fdc_mgmt_writedata = '0;
    logic  fdc_mgmt_write = 1'b0;
    logic  fdc_mgmt_read = 1'b0;
    logic [1:0] fdc_floppy_write_protect = '0;
    logic  feature_opl2 = 1'b1;
    logic  feature_cms = 1'b1;
    logic  feature_tandy = 1'b1;
    logic  feature_sb = 1'b1;
    logic  feature_midi = 1'b1;
    logic [1:0] at286ctl_eff_opl2 = '0;
    logic  at286ctl_eff_cms = 1'b1;
    logic  at286ctl_eff_tandy = 1'b1;
    logic  at286ctl_eff_sb = 1'b1;
    logic  at286ctl_eff_mpu401 = 1'b1;
    logic  ems_runtime_enabled = 1'b0;
    logic  a20_enable = 1'b1;
    logic  video_aperture_select = 1'b0;
    logic  cpu_grant = 1'b1;
    always #10 clk = ~clk;
    always @(negedge clk) cpu_sample_edge = ~cpu_sample_edge;
    integer cycle = 0; integer trace_gold; integer trace_gate;
    logic tracing = 0; string trace_path;
    integer cpu_transfers = 0; integer fdc_beats = 0;
    integer fdc_writes = 0; integer fdc_reads = 0;
    integer split_beats = 0; integer memory_beats = 0;
    integer ide_exclusions = 0; integer warm_resets = 0;
    integer fifo_reset_writes = 0;
    logic [15:0] last_read; logic [15:0] count_before;
    wire  cpu_ready_gold;
    wire [15:0] cpu_data_in_gold;
    wire  at_valid_gold;
    wire  at_command_valid_gold;
    wire [2:0] at_owner_gold;
    wire [3:0] at_cycle_class_gold;
    wire [23:0] at_address_gold;
    wire  at_a0_gold;
    wire  at_bhe_n_gold;
    wire [1:0] at_byte_enable_gold;
    wire [15:0] at_data_out_gold;
    wire  at_data_oe_gold;
    wire  at_write_gold;
    wire  at_io_gold;
    wire  at_inta_gold;
    wire  at_code_fetch_gold;
    wire  at_lock_gold;
    wire  at_accepted_gold;
    wire  at_completed_gold;
    wire  at_response_valid_gold;
    wire  bridge_idle_gold;
    wire [3:0] debug_state_gold;
    wire  bridge_protocol_error_gold;
    wire  fdc_request_accept_gold;
    wire  fdc_request_ready_gold;
    wire [15:0] fdc_request_read_data_gold;
    wire  fdc_request_read_data_valid_gold;
    wire  fdc_dma_transfer_accept_gold;
    wire  fdc_dma_transfer_ready_gold;
    wire [15:0] fdc_dma_transfer_data_out_gold;
    wire [7:0] fdc_dma_request_gold;
    wire  fdc_irq6_gold;
    wire [15:0] fdc_mgmt_readdata_gold;
    wire [1:0] fdc_floppy_present_gold;
    wire [1:0] fdc_floppy_request_gold;
    wire [15:0] fdc_side_effect_count_gold;
    wire [15:0] fdc_command_count_gold;
    wire  fdc_protocol_error_gold;
    wire  proof_core_dma_req_gold;
    wire [7:0] proof_core_dma_writedata_gold;
    wire  proof_core_irq_gold;
    wire [7:0] proof_core_io_readdata_gold;
    wire  proof_core_fdd0_inserted_gold;
    wire [15:0] proof_core_mgmt_readdata_gold;
    wire [1:0] proof_core_request_gold;
    wire  proof_route_exclusive_gold;
    wire memory_accept_gold = at_command_valid_gold && !at_io_gold && !at_inta_gold;
    wire sink_accept_gold = at_command_valid_gold && at_io_gold && (at_address_gold[15:0] == 16'h03F6);
    logic memory_ready_gold = 0; logic sink_ready_gold = 0;
    always @(posedge clk) begin
        if (bridge_reset) begin memory_ready_gold <= 0; sink_ready_gold <= 0; end
        else begin memory_ready_gold <= memory_accept_gold; sink_ready_gold <= sink_accept_gold; end
    end
    buffer_gold dut_gold(
        .clk(clk),
        .bridge_reset(bridge_reset),
        .cpu_sample_edge(cpu_sample_edge),
        .cpu_bus_valid(cpu_bus_valid),
        .cpu_address(cpu_address),
        .cpu_data_out(cpu_data_out),
        .cpu_data_oe(cpu_data_oe),
        .cpu_bus_write(cpu_bus_write),
        .cpu_bus_bhe_n(cpu_bus_bhe_n),
        .cpu_bus_status(cpu_bus_status),
        .cpu_bus_lock(cpu_bus_lock),
        .memory_drain_pending(memory_drain_pending),
        .cpu_memory_word_capable(cpu_memory_word_capable),
        .cpu_io_word_capable(cpu_io_word_capable),
        .cpu_ready(cpu_ready_gold),
        .cpu_data_in(cpu_data_in_gold),
        .at_valid(at_valid_gold),
        .at_command_valid(at_command_valid_gold),
        .at_owner(at_owner_gold),
        .at_cycle_class(at_cycle_class_gold),
        .at_address(at_address_gold),
        .at_a0(at_a0_gold),
        .at_bhe_n(at_bhe_n_gold),
        .at_byte_enable(at_byte_enable_gold),
        .at_data_out(at_data_out_gold),
        .at_data_oe(at_data_oe_gold),
        .at_write(at_write_gold),
        .at_io(at_io_gold),
        .at_inta(at_inta_gold),
        .at_code_fetch(at_code_fetch_gold),
        .at_lock(at_lock_gold),
        .at_accepted(at_accepted_gold),
        .at_completed(at_completed_gold),
        .at_response_valid(at_response_valid_gold),
        .at_accept(fdc_request_accept_gold || memory_accept_gold || sink_accept_gold),
        .at_ready(fdc_request_ready_gold || memory_ready_gold || sink_ready_gold),
        .at_read_data(fdc_request_read_data_valid_gold ? fdc_request_read_data_gold : memory_ready_gold ? 16'hA55A : 16'hFFFF),
        .at_read_data_valid(fdc_request_read_data_valid_gold || memory_ready_gold || sink_ready_gold),
        .bridge_idle(bridge_idle_gold),
        .debug_state(debug_state_gold),
        .bridge_protocol_error(bridge_protocol_error_gold),
        .fdc_reset(fdc_reset),
        .fdc_request_accept(fdc_request_accept_gold),
        .fdc_request_ready(fdc_request_ready_gold),
        .fdc_request_read_data(fdc_request_read_data_gold),
        .fdc_request_read_data_valid(fdc_request_read_data_valid_gold),
        .fdc_dma_transfer_valid(fdc_dma_transfer_valid),
        .fdc_dma_transfer_complete(fdc_dma_transfer_complete),
        .fdc_dma_terminal_count(fdc_dma_terminal_count),
        .fdc_dma_active_channel(fdc_dma_active_channel),
        .fdc_dma_transfer_data_in(fdc_dma_transfer_data_in),
        .fdc_dma_transfer_accept(fdc_dma_transfer_accept_gold),
        .fdc_dma_transfer_ready(fdc_dma_transfer_ready_gold),
        .fdc_dma_transfer_data_out(fdc_dma_transfer_data_out_gold),
        .fdc_dma_request(fdc_dma_request_gold),
        .fdc_irq6(fdc_irq6_gold),
        .fdc_mgmt_address(fdc_mgmt_address),
        .fdc_mgmt_writedata(fdc_mgmt_writedata),
        .fdc_mgmt_write(fdc_mgmt_write),
        .fdc_mgmt_read(fdc_mgmt_read),
        .fdc_mgmt_readdata(fdc_mgmt_readdata_gold),
        .fdc_floppy_write_protect(fdc_floppy_write_protect),
        .fdc_floppy_present(fdc_floppy_present_gold),
        .fdc_floppy_request(fdc_floppy_request_gold),
        .fdc_side_effect_count(fdc_side_effect_count_gold),
        .fdc_command_count(fdc_command_count_gold),
        .fdc_protocol_error(fdc_protocol_error_gold),
        .feature_opl2(feature_opl2),
        .feature_cms(feature_cms),
        .feature_tandy(feature_tandy),
        .feature_sb(feature_sb),
        .feature_midi(feature_midi),
        .at286ctl_eff_opl2(at286ctl_eff_opl2),
        .at286ctl_eff_cms(at286ctl_eff_cms),
        .at286ctl_eff_tandy(at286ctl_eff_tandy),
        .at286ctl_eff_sb(at286ctl_eff_sb),
        .at286ctl_eff_mpu401(at286ctl_eff_mpu401),
        .ems_runtime_enabled(ems_runtime_enabled),
        .a20_enable(a20_enable),
        .video_aperture_select(video_aperture_select),
        .cpu_grant(cpu_grant),
        .proof_core_dma_req(proof_core_dma_req_gold),
        .proof_core_dma_writedata(proof_core_dma_writedata_gold),
        .proof_core_irq(proof_core_irq_gold),
        .proof_core_io_readdata(proof_core_io_readdata_gold),
        .proof_core_fdd0_inserted(proof_core_fdd0_inserted_gold),
        .proof_core_mgmt_readdata(proof_core_mgmt_readdata_gold),
        .proof_core_request(proof_core_request_gold),
        .proof_route_exclusive(proof_route_exclusive_gold)
    );
    wire  cpu_ready_gate;
    wire [15:0] cpu_data_in_gate;
    wire  at_valid_gate;
    wire  at_command_valid_gate;
    wire [2:0] at_owner_gate;
    wire [3:0] at_cycle_class_gate;
    wire [23:0] at_address_gate;
    wire  at_a0_gate;
    wire  at_bhe_n_gate;
    wire [1:0] at_byte_enable_gate;
    wire [15:0] at_data_out_gate;
    wire  at_data_oe_gate;
    wire  at_write_gate;
    wire  at_io_gate;
    wire  at_inta_gate;
    wire  at_code_fetch_gate;
    wire  at_lock_gate;
    wire  at_accepted_gate;
    wire  at_completed_gate;
    wire  at_response_valid_gate;
    wire  bridge_idle_gate;
    wire [3:0] debug_state_gate;
    wire  bridge_protocol_error_gate;
    wire  fdc_request_accept_gate;
    wire  fdc_request_ready_gate;
    wire [15:0] fdc_request_read_data_gate;
    wire  fdc_request_read_data_valid_gate;
    wire  fdc_dma_transfer_accept_gate;
    wire  fdc_dma_transfer_ready_gate;
    wire [15:0] fdc_dma_transfer_data_out_gate;
    wire [7:0] fdc_dma_request_gate;
    wire  fdc_irq6_gate;
    wire [15:0] fdc_mgmt_readdata_gate;
    wire [1:0] fdc_floppy_present_gate;
    wire [1:0] fdc_floppy_request_gate;
    wire [15:0] fdc_side_effect_count_gate;
    wire [15:0] fdc_command_count_gate;
    wire  fdc_protocol_error_gate;
    wire  proof_core_dma_req_gate;
    wire [7:0] proof_core_dma_writedata_gate;
    wire  proof_core_irq_gate;
    wire [7:0] proof_core_io_readdata_gate;
    wire  proof_core_fdd0_inserted_gate;
    wire [15:0] proof_core_mgmt_readdata_gate;
    wire [1:0] proof_core_request_gate;
    wire  proof_route_exclusive_gate;
    wire memory_accept_gate = at_command_valid_gate && !at_io_gate && !at_inta_gate;
    wire sink_accept_gate = at_command_valid_gate && at_io_gate && (at_address_gate[15:0] == 16'h03F6);
    logic memory_ready_gate = 0; logic sink_ready_gate = 0;
    always @(posedge clk) begin
        if (bridge_reset) begin memory_ready_gate <= 0; sink_ready_gate <= 0; end
        else begin memory_ready_gate <= memory_accept_gate; sink_ready_gate <= sink_accept_gate; end
    end
    buffer_gate dut_gate(
        .clk(clk),
        .bridge_reset(bridge_reset),
        .cpu_sample_edge(cpu_sample_edge),
        .cpu_bus_valid(cpu_bus_valid),
        .cpu_address(cpu_address),
        .cpu_data_out(cpu_data_out),
        .cpu_data_oe(cpu_data_oe),
        .cpu_bus_write(cpu_bus_write),
        .cpu_bus_bhe_n(cpu_bus_bhe_n),
        .cpu_bus_status(cpu_bus_status),
        .cpu_bus_lock(cpu_bus_lock),
        .memory_drain_pending(memory_drain_pending),
        .cpu_memory_word_capable(cpu_memory_word_capable),
        .cpu_io_word_capable(cpu_io_word_capable),
        .cpu_ready(cpu_ready_gate),
        .cpu_data_in(cpu_data_in_gate),
        .at_valid(at_valid_gate),
        .at_command_valid(at_command_valid_gate),
        .at_owner(at_owner_gate),
        .at_cycle_class(at_cycle_class_gate),
        .at_address(at_address_gate),
        .at_a0(at_a0_gate),
        .at_bhe_n(at_bhe_n_gate),
        .at_byte_enable(at_byte_enable_gate),
        .at_data_out(at_data_out_gate),
        .at_data_oe(at_data_oe_gate),
        .at_write(at_write_gate),
        .at_io(at_io_gate),
        .at_inta(at_inta_gate),
        .at_code_fetch(at_code_fetch_gate),
        .at_lock(at_lock_gate),
        .at_accepted(at_accepted_gate),
        .at_completed(at_completed_gate),
        .at_response_valid(at_response_valid_gate),
        .at_accept(fdc_request_accept_gate || memory_accept_gate || sink_accept_gate),
        .at_ready(fdc_request_ready_gate || memory_ready_gate || sink_ready_gate),
        .at_read_data(fdc_request_read_data_valid_gate ? fdc_request_read_data_gate : memory_ready_gate ? 16'hA55A : 16'hFFFF),
        .at_read_data_valid(fdc_request_read_data_valid_gate || memory_ready_gate || sink_ready_gate),
        .bridge_idle(bridge_idle_gate),
        .debug_state(debug_state_gate),
        .bridge_protocol_error(bridge_protocol_error_gate),
        .fdc_reset(fdc_reset),
        .fdc_request_accept(fdc_request_accept_gate),
        .fdc_request_ready(fdc_request_ready_gate),
        .fdc_request_read_data(fdc_request_read_data_gate),
        .fdc_request_read_data_valid(fdc_request_read_data_valid_gate),
        .fdc_dma_transfer_valid(fdc_dma_transfer_valid),
        .fdc_dma_transfer_complete(fdc_dma_transfer_complete),
        .fdc_dma_terminal_count(fdc_dma_terminal_count),
        .fdc_dma_active_channel(fdc_dma_active_channel),
        .fdc_dma_transfer_data_in(fdc_dma_transfer_data_in),
        .fdc_dma_transfer_accept(fdc_dma_transfer_accept_gate),
        .fdc_dma_transfer_ready(fdc_dma_transfer_ready_gate),
        .fdc_dma_transfer_data_out(fdc_dma_transfer_data_out_gate),
        .fdc_dma_request(fdc_dma_request_gate),
        .fdc_irq6(fdc_irq6_gate),
        .fdc_mgmt_address(fdc_mgmt_address),
        .fdc_mgmt_writedata(fdc_mgmt_writedata),
        .fdc_mgmt_write(fdc_mgmt_write),
        .fdc_mgmt_read(fdc_mgmt_read),
        .fdc_mgmt_readdata(fdc_mgmt_readdata_gate),
        .fdc_floppy_write_protect(fdc_floppy_write_protect),
        .fdc_floppy_present(fdc_floppy_present_gate),
        .fdc_floppy_request(fdc_floppy_request_gate),
        .fdc_side_effect_count(fdc_side_effect_count_gate),
        .fdc_command_count(fdc_command_count_gate),
        .fdc_protocol_error(fdc_protocol_error_gate),
        .feature_opl2(feature_opl2),
        .feature_cms(feature_cms),
        .feature_tandy(feature_tandy),
        .feature_sb(feature_sb),
        .feature_midi(feature_midi),
        .at286ctl_eff_opl2(at286ctl_eff_opl2),
        .at286ctl_eff_cms(at286ctl_eff_cms),
        .at286ctl_eff_tandy(at286ctl_eff_tandy),
        .at286ctl_eff_sb(at286ctl_eff_sb),
        .at286ctl_eff_mpu401(at286ctl_eff_mpu401),
        .ems_runtime_enabled(ems_runtime_enabled),
        .a20_enable(a20_enable),
        .video_aperture_select(video_aperture_select),
        .cpu_grant(cpu_grant),
        .proof_core_dma_req(proof_core_dma_req_gate),
        .proof_core_dma_writedata(proof_core_dma_writedata_gate),
        .proof_core_irq(proof_core_irq_gate),
        .proof_core_io_readdata(proof_core_io_readdata_gate),
        .proof_core_fdd0_inserted(proof_core_fdd0_inserted_gate),
        .proof_core_mgmt_readdata(proof_core_mgmt_readdata_gate),
        .proof_core_request(proof_core_request_gate),
        .proof_route_exclusive(proof_route_exclusive_gate)
    );
    wire all_equal = (cpu_ready_gold === cpu_ready_gate) &&
            (cpu_data_in_gold === cpu_data_in_gate) &&
            (at_valid_gold === at_valid_gate) &&
            (at_command_valid_gold === at_command_valid_gate) &&
            (at_owner_gold === at_owner_gate) &&
            (at_cycle_class_gold === at_cycle_class_gate) &&
            (at_address_gold === at_address_gate) &&
            (at_a0_gold === at_a0_gate) &&
            (at_bhe_n_gold === at_bhe_n_gate) &&
            (at_byte_enable_gold === at_byte_enable_gate) &&
            (at_data_out_gold === at_data_out_gate) &&
            (at_data_oe_gold === at_data_oe_gate) &&
            (at_write_gold === at_write_gate) &&
            (at_io_gold === at_io_gate) &&
            (at_inta_gold === at_inta_gate) &&
            (at_code_fetch_gold === at_code_fetch_gate) &&
            (at_lock_gold === at_lock_gate) &&
            (at_accepted_gold === at_accepted_gate) &&
            (at_completed_gold === at_completed_gate) &&
            (at_response_valid_gold === at_response_valid_gate) &&
            (bridge_idle_gold === bridge_idle_gate) &&
            (debug_state_gold === debug_state_gate) &&
            (bridge_protocol_error_gold === bridge_protocol_error_gate) &&
            (fdc_request_accept_gold === fdc_request_accept_gate) &&
            (fdc_request_ready_gold === fdc_request_ready_gate) &&
            (fdc_request_read_data_gold === fdc_request_read_data_gate) &&
            (fdc_request_read_data_valid_gold === fdc_request_read_data_valid_gate) &&
            (fdc_dma_transfer_accept_gold === fdc_dma_transfer_accept_gate) &&
            (fdc_dma_transfer_ready_gold === fdc_dma_transfer_ready_gate) &&
            (fdc_dma_transfer_data_out_gold === fdc_dma_transfer_data_out_gate) &&
            (fdc_dma_request_gold === fdc_dma_request_gate) &&
            (fdc_irq6_gold === fdc_irq6_gate) &&
            (fdc_mgmt_readdata_gold === fdc_mgmt_readdata_gate) &&
            (fdc_floppy_present_gold === fdc_floppy_present_gate) &&
            (fdc_floppy_request_gold === fdc_floppy_request_gate) &&
            (fdc_side_effect_count_gold === fdc_side_effect_count_gate) &&
            (fdc_command_count_gold === fdc_command_count_gate) &&
            (fdc_protocol_error_gold === fdc_protocol_error_gate) &&
            (proof_core_dma_req_gold === proof_core_dma_req_gate) &&
            (proof_core_dma_writedata_gold === proof_core_dma_writedata_gate) &&
            (proof_core_irq_gold === proof_core_irq_gate) &&
            (proof_core_io_readdata_gold === proof_core_io_readdata_gate) &&
            (proof_core_fdd0_inserted_gold === proof_core_fdd0_inserted_gate) &&
            (proof_core_mgmt_readdata_gold === proof_core_mgmt_readdata_gate) &&
            (proof_core_request_gold === proof_core_request_gate) &&
            (proof_route_exclusive_gold === proof_route_exclusive_gate);
    always @(negedge clk) if (tracing) begin
        cycle = cycle + 1;
        if (!all_equal) $fatal(1,"FDC_PAIR_MISMATCH cycle=%0d",cycle);
        $fwrite(trace_gold,"%0d,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h\n",cycle, cpu_ready_gold, cpu_data_in_gold, at_valid_gold, at_command_valid_gold, at_owner_gold, at_cycle_class_gold, at_address_gold, at_a0_gold, at_bhe_n_gold, at_byte_enable_gold, at_data_out_gold, at_data_oe_gold, at_write_gold, at_io_gold, at_inta_gold, at_code_fetch_gold, at_lock_gold, at_accepted_gold, at_completed_gold, at_response_valid_gold, bridge_idle_gold, debug_state_gold, bridge_protocol_error_gold, fdc_request_accept_gold, fdc_request_ready_gold, fdc_request_read_data_gold, fdc_request_read_data_valid_gold, fdc_dma_transfer_accept_gold, fdc_dma_transfer_ready_gold, fdc_dma_transfer_data_out_gold, fdc_dma_request_gold, fdc_irq6_gold, fdc_mgmt_readdata_gold, fdc_floppy_present_gold, fdc_floppy_request_gold, fdc_side_effect_count_gold, fdc_command_count_gold, fdc_protocol_error_gold, proof_core_dma_req_gold, proof_core_dma_writedata_gold, proof_core_irq_gold, proof_core_io_readdata_gold, proof_core_fdd0_inserted_gold, proof_core_mgmt_readdata_gold, proof_core_request_gold, proof_route_exclusive_gold);
        $fwrite(trace_gate,"%0d,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h\n",cycle, cpu_ready_gate, cpu_data_in_gate, at_valid_gate, at_command_valid_gate, at_owner_gate, at_cycle_class_gate, at_address_gate, at_a0_gate, at_bhe_n_gate, at_byte_enable_gate, at_data_out_gate, at_data_oe_gate, at_write_gate, at_io_gate, at_inta_gate, at_code_fetch_gate, at_lock_gate, at_accepted_gate, at_completed_gate, at_response_valid_gate, bridge_idle_gate, debug_state_gate, bridge_protocol_error_gate, fdc_request_accept_gate, fdc_request_ready_gate, fdc_request_read_data_gate, fdc_request_read_data_valid_gate, fdc_dma_transfer_accept_gate, fdc_dma_transfer_ready_gate, fdc_dma_transfer_data_out_gate, fdc_dma_request_gate, fdc_irq6_gate, fdc_mgmt_readdata_gate, fdc_floppy_present_gate, fdc_floppy_request_gate, fdc_side_effect_count_gate, fdc_command_count_gate, fdc_protocol_error_gate, proof_core_dma_req_gate, proof_core_dma_writedata_gate, proof_core_irq_gate, proof_core_io_readdata_gate, proof_core_fdd0_inserted_gate, proof_core_mgmt_readdata_gate, proof_core_request_gate, proof_route_exclusive_gate);
        if (fdc_request_accept_gold) begin
            fdc_beats = fdc_beats + 1;
            if (at_write_gold) fdc_writes = fdc_writes + 1;
            else fdc_reads = fdc_reads + 1;
        end
        if (memory_accept_gold) memory_beats = memory_beats + 1;
        if (sink_accept_gold) begin
            ide_exclusions = ide_exclusions + 1;
            if (fdc_request_accept_gold) $fatal(1,"IDE_3F6_REACHED_FDC");
        end
    end

    task automatic check(input logic predicate, input string msg);
        if (predicate !== 1'b1) $fatal(1,"FDC_CHECK_FAIL %s",msg);
    endtask
    task automatic idle(input integer cycles);
        repeat(cycles) begin @(negedge clk); #1; end
    endtask
    task automatic management_write(input logic [15:0] address, input logic [15:0] value);
        @(negedge clk); #1;
        fdc_mgmt_address=address; fdc_mgmt_writedata=value; fdc_mgmt_write=1;
        @(negedge clk); #1; fdc_mgmt_write=0;
    endtask
    task automatic bus_transfer(input logic [23:0] address, input logic [15:0] value,
                                input logic write_cycle, input logic word_cycle,
                                input logic memory_cycle);
        integer timeout_cycles;
        @(negedge clk); #1;
        cpu_address=address; cpu_data_out=value;
        cpu_bus_write=write_cycle; cpu_data_oe=write_cycle;
        cpu_bus_bhe_n=word_cycle ? 0 : !address[0];
        cpu_bus_status=memory_cycle ? (write_cycle ? 4'h6 : 4'h5) :
                                     (write_cycle ? 4'hA : 4'h9);
        cpu_bus_valid=1;
        timeout_cycles=0;
        while (!cpu_ready_gold && timeout_cycles<100) begin
            @(negedge clk); #1; timeout_cycles=timeout_cycles+1;
        end
        check(cpu_ready_gold,"CPU transfer timed out");
        last_read=cpu_data_in_gold;
        cpu_transfers=cpu_transfers+1;
        if(word_cycle && !memory_cycle) split_beats=split_beats+2;
        @(negedge clk); #1; cpu_bus_valid=0; cpu_data_oe=0;
        timeout_cycles=0;
        while(!bridge_idle_gold && timeout_cycles<100) begin
            @(negedge clk); #1; timeout_cycles=timeout_cycles+1;
        end
        check(bridge_idle_gold,"CPU bridge did not drain");
        check(!bridge_protocol_error_gold,"Bridge protocol error");
        idle(2);
    endtask
    task automatic io_write(input logic [15:0] address, input logic [7:0] value);
        bus_transfer({8'h00,address},address[0] ? {value,8'h00} : {8'h00,value},1,0,0);
    endtask
    task automatic io_read(input logic [15:0] address);
        bus_transfer({8'h00,address},0,0,0,0);
    endtask
    initial begin
        if(!$value$plusargs("TRACE=%s",trace_path)) $fatal(1,"TRACE path required");
        trace_gold=$fopen({trace_path,"-gold.csv"},"w");
        trace_gate=$fopen({trace_path,"-gate.csv"},"w");
        check(trace_gold!=0 && trace_gate!=0,"Trace open failure");
        idle(4); bridge_reset=0; fdc_reset=0; idle(4); tracing=1;
        // Real FIFO memory writes even while rst_n is low; no force/deposit.
        @(negedge clk); #1; bridge_reset=1; fdc_reset=1;
        management_write(16'hF20F,16'h005A);
        check(dut_gold.u_fdc.u_fdc.fifo_to_floppy_inst.mem[0]===8'h5A,"Gold FIFO reset write missing");
        check(dut_gate.u_fdc.u_fdc.fifo_to_floppy_inst.mem[0]===8'h5A,"Gate FIFO reset write missing");
        fifo_reset_writes=fifo_reset_writes+1;
        management_write(16'hF20F,16'h00A7);
        check(dut_gold.u_fdc.u_fdc.fifo_to_floppy_inst.mem[0]===8'hA7,"Gold FIFO second reset write missing");
        check(dut_gate.u_fdc.u_fdc.fifo_to_floppy_inst.mem[0]===8'hA7,"Gate FIFO second reset write missing");
        fifo_reset_writes=fifo_reset_writes+1;
        bridge_reset=0; fdc_reset=0; idle(4);
        management_write(16'hF200,16'h0001); management_write(16'hF201,0);
        management_write(16'hF202,80); management_write(16'hF203,15);
        management_write(16'hF204,2400); management_write(16'hF205,2);
        check(fdc_floppy_present_gold[0],"Media insert not retained");
        io_write(16'h03F2,8'h0C); io_write(16'h03F2,8'h08); io_write(16'h03F2,8'h0C);
        idle(8); check(fdc_irq6_gold,"DOR reset did not raise IRQ6");
        io_write(16'h03F5,8'h08); io_read(16'h03F5);
        check((last_read[15:8]&8'hC0)==8'hC0,"Sense interrupt reset status");
        io_read(16'h03F5); check(last_read[15:8]==0,"Sense interrupt cylinder");
        io_write(16'h03F5,8'h03); io_write(16'h03F5,8'hCF); io_write(16'h03F5,8'h02);
        // Early memory address changes alter the real raw FDC read register.
        bus_transfer(24'h103302,0,0,1,1); check(last_read==16'hA55A,"Memory read data");
        bus_transfer(24'h103304,16'h1234,1,1,1);
        bus_transfer(24'h103307,0,0,0,1);
        io_read(16'h03F4); check(last_read[7],"FDC MSR not ready");
        // Native CPU word to byte-wide FDC becomes two physical beats.
        count_before=fdc_side_effect_count_gold;
        bus_transfer(24'h0003F2,16'h000C,1,1,0);
        check(fdc_side_effect_count_gold==count_before+2,"DOR word not split");
        count_before=fdc_command_count_gold;
        bus_transfer(24'h0003F4,16'h1000,1,1,0);
        check(fdc_command_count_gold==count_before+1,"DSR/FIFO split command count");
        bus_transfer(24'h0003F4,0,0,1,0);
        check(last_read[15:8]==8'h90,"Split word version readback");
        count_before=fdc_side_effect_count_gold;
        io_write(16'h03F6,8'h02); io_read(16'h03F6);
        check(fdc_side_effect_count_gold==count_before,"IDE port reached FDC");
        // CPU-local warm reset after a read access leaves FDC read pipeline alive.
        @(negedge clk); #1;
        cpu_address=24'h0003F4; cpu_data_out=0; cpu_bus_write=0; cpu_data_oe=0;
        cpu_bus_bhe_n=1; cpu_bus_status=4'h9; cpu_bus_valid=1;
        wait(fdc_request_accept_gold); @(posedge clk); #1;
        count_before=fdc_side_effect_count_gold;
        @(negedge clk); #1; bridge_reset=1; cpu_bus_valid=0;
        idle(3); bridge_reset=0; idle(6); warm_resets=warm_resets+1;
        check(fdc_side_effect_count_gold==count_before,"Warm reset changed FDC counter");
        check(fdc_floppy_present_gold[0],"Warm reset cleared media");
        check(!fdc_protocol_error_gold,"Legal FDC protocol error");
        check(proof_route_exclusive_gold,"FDC route priority exclusion");
        $display("RETAINED_FDC_COMPOSED_PASS cpu=%0d fdc=%0d writes=%0d reads=%0d split_beats=%0d memory=%0d ide_exclusions=%0d warm_reset=%0d fifo_reset_writes=%0d side_effects=%0d commands=%0d",
                 cpu_transfers,fdc_beats,fdc_writes,fdc_reads,split_beats,memory_beats,ide_exclusions,warm_resets,fifo_reset_writes,fdc_side_effect_count_gold,fdc_command_count_gold);
        $fclose(trace_gold); $fclose(trace_gate); $finish;
    end
    initial begin #200000; $fatal(1,"FDC global timeout"); end
endmodule
