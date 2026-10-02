`timescale 1ns/1ps
module spk286_at_posted_write_buffer_tb;
    logic clk = 0, reset = 1, cancel_cpu = 0, cpu_lock = 0;
    always #10 clk = ~clk;
    logic valid = 0, command = 0, wr = 0, refresh = 0, code = 0, burst = 0;
    logic [1:0] who = 0, lanes = 3;
    logic [3:0] kind = 6;
    logic [24:0] address = 0;
    logic [15:0] value = 0;
    wire accept, ready, read_valid, pending, idle, error;
    wire [15:0] read_data;
    wire ov, oc, ow, ore, ocode, ob;
    wire [1:0] owner, ol;
    wire [3:0] status;
    wire [24:0] oa;
    wire [15:0] od;
    wire pa, pr, pv, pi, pe;
    wire [15:0] pd, dq_in, dq_out;
    logic stall = 0, stale_ready = 0;
    wire [31:0] posts, drains, blocked;
    wire [12:0] pin_address;
    wire cke, cs, ras, cas, we, dq_io, ldqm, udqm;
    wire [1:0] bank, dq_valid;
    integer reads, writes, checks = 0, cycles = 0, refreshes = 0;
    integer expected_writes = 0;

    spk286_at_posted_write_buffer dut (
        .clk(clk), .reset(reset), .cancel_cpu(cancel_cpu), .cpu_lock(cpu_lock),
        .in_valid(valid), .in_command_valid(command), .in_owner(who),
        .in_write(wr), .in_refresh(refresh), .in_code_fetch(code), .in_burst(burst),
        .in_cycle_class(kind), .in_address(address), .in_byte_enable(lanes),
        .in_data_out(value), .in_accept(accept), .in_ready(ready),
        .in_read_data(read_data), .in_read_data_valid(read_valid),
        .out_valid(ov), .out_command_valid(oc), .out_owner(owner),
        .out_write(ow), .out_refresh(ore), .out_code_fetch(ocode), .out_burst(ob),
        .out_cycle_class(status), .out_address(oa), .out_byte_enable(ol), .out_data_out(od),
        .out_accept(pa), .out_ready(pr || stale_ready), .out_read_data(pd), .out_read_data_valid(pv),
        .pending_write(pending), .idle(idle), .protocol_error(error),
        .debug_post_count(posts), .debug_drain_count(drains), .debug_stall_count(blocked)
    );
    spk286_at_mister_sdram_owner #(
        .SDRAM_INIT_WAIT(16'd8), .SDRAM_REFRESH_CYCLE(16'd24), .SDRAM_FORCE_REFRESH(16'd48)
    ) physical (
        .clk(clk), .reset(reset), .request_valid(ov && !stall),
        .request_command_valid(oc && !stall), .request_owner_refresh(ore),
        .request_write(ow), .request_code_fetch(ocode), .request_burst(ob),
        .request_cycle_class(status), .request_address(oa),
        .request_byte_enable(ol), .request_data_out(od),
        .request_accept(pa), .request_ready(pr), .request_read_data(pd), .request_read_data_valid(pv),
        .physical_idle(pi), .debug_state(), .protocol_error(pe),
        .sdram_address(pin_address), .sdram_cke(cke), .sdram_cs(cs),
        .sdram_ras(ras), .sdram_cas(cas), .sdram_we(we), .sdram_ba(bank),
        .sdram_dq_in(dq_in), .sdram_dq_out(dq_out), .sdram_dq_io(dq_io),
        .sdram_ldqm(ldqm), .sdram_udqm(udqm)
    );
    spk286_sdram_pin_model #(.MEM_WORDS(16777216)) pins (
        .clk(clk), .reset(reset), .address(pin_address), .cke(cke),
        .cs_n(cs), .ras_n(ras), .cas_n(cas), .we_n(we), .ba(bank),
        .dq_from_controller(dq_out), .controller_dq_oe(!dq_io),
        .dqm({udqm, ldqm}), .dq_to_controller(dq_in), .dq_valid(dq_valid),
        .read_count(reads), .write_count(writes)
    );

    // The real bridge/arbiter see the same pending record as the machine.
    logic bv = 0, bl = 0, br = 1, dma = 0, done = 0;
    logic [3:0] bs = 5;
    wire av, ac, bridge_idle, bridge_error, at_lock, dma_grant, arbiter_error;
    spk286_at_bus_bridge bridge (
        .clk(clk), .reset(reset || br), .cpu_sample_edge(1'b1), .cpu_bus_valid(bv),
        .cpu_address(24'h002000), .cpu_data_out(16'h1234), .cpu_data_oe(bs == 6),
        .cpu_bus_write(bs == 6), .cpu_bus_bhe_n(1'b0), .cpu_bus_status(bs),
        .cpu_bus_lock(bl), .memory_drain_pending(pending),
        .cpu_memory_word_capable(bs == 5 || bs == 6 || bs == 13), .cpu_io_word_capable(1'b0),
        .cpu_ready(), .cpu_data_in(), .at_valid(av), .at_command_valid(ac), .at_lock(at_lock),
        .at_accept(1'b0), .at_ready(1'b0), .at_read_data(16'd0), .at_read_data_valid(1'b0),
        .bridge_idle(bridge_idle), .debug_state(), .protocol_error(bridge_error)
    );
    spk286_at_arbiter arbiter (
        .clk(clk), .reset(reset || br), .cpu_hlda(1'b1), .cpu_bridge_idle(bridge_idle),
        .cpu_lock(at_lock), .cpu_odd_word_active(1'b0), .cpu_inta_lock_chain(1'b0),
        .cpu_response_pending(av), .dma_request(dma), .refresh_request(1'b0),
        .loader_request(1'b0), .loader_reset_owner(1'b0), .external_done(done),
        .cpu_hold_request(), .cpu_grant(), .external_grant(), .bus_owner_valid(),
        .bus_owner(), .dma_grant(dma_grant), .refresh_grant(), .loader_grant(),
        .protocol_error(arbiter_error)
    );

    task automatic check(input logic condition, input string message);
        checks++;
        if (!condition) $fatal(1, "POSTED check %0d: %s", checks, message);
    endtask
    task automatic poison;
        valid = 0; command = 0; who = 3; wr = 0; refresh = 1; code = 1; burst = 1;
        kind = 0; address = 25'h1ffffff; lanes = 0; value = 16'hdead;
    endtask
    task automatic admit(input logic [1:0] initiator, input logic write_cycle,
                         input logic [24:0] addr, input logic [1:0] bytes,
                         input logic [15:0] data, input logic line_read = 0);
        integer guard;
        @(negedge clk);
        who = initiator; valid = 1; command = 1; wr = write_cycle;
        refresh = initiator == 2; code = line_read; burst = line_read;
        kind = write_cycle ? 6 : line_read ? 13 : 5;
        address = addr; lanes = bytes; value = data;
        #1; guard = 0;
        while (!accept && guard < 300) begin @(negedge clk); #1; guard++; end
        check(accept && !ready, "acceptance must precede logical completion");
        @(posedge clk); #1;
        poison();
    endtask
    task automatic finish_response(input logic expected_post, input logic [15:0] expected = 0,
                                   input logic read_response = 0);
        integer guard;
        guard = 0;
        if (expected_post) check(ready && pending && !read_valid, "retained write gives early ACK");
        while (!ready && guard < 300) begin @(negedge clk); #1; guard++; end
        check(ready, "response deadline");
        if (read_response) check(read_valid && read_data == expected, "physical read data");
        if (!expected_post) check(!pending, "nonposted owner is physically completed");
        @(posedge clk); #1;
    endtask
    task automatic drain;
        integer guard;
        guard = 0;
        while ((!idle || !pi) && guard < 300) begin @(negedge clk); #1; guard++; end
        check(idle && pi, "physical drain deadline");
        check(!ready, "physical completion cannot acknowledge a later request");
    endtask
    task automatic put(input logic [1:0] initiator, input logic [24:0] addr,
                       input logic [1:0] bytes, input logic [15:0] data);
        admit(initiator, 1, addr, bytes, data);
        finish_response(initiator == 0 && !cpu_lock &&
                        (addr < 25'ha0000 || (addr >= 25'h100000 && addr < 25'h11e0000)));
        drain(); expected_writes++;
        check(writes == expected_writes, "one physical write per accepted store");
    endtask

    always @(posedge clk) begin
        cycles++;
        if (cycles > 30000) $fatal(1, "POSTED timeout");
        if (!reset && (error || pe || bridge_error || arbiter_error)) $fatal(1, "POSTED protocol fault");
        if (!reset && !cs && !ras && !cas && we) refreshes++;
    end

    initial begin
        repeat (3) @(negedge clk); reset = 0; wait(pi); @(negedge clk);
        // Capture during physical backpressure; poison every live field.
        stall = 1;
        admit(0, 1, 25'h2000, 3, 16'ha55a);
        check(!dut.issued_q && pending, "queue accepts during physical backpressure");
        finish_response(1);
        stale_ready = 1;
        repeat (4) begin
            @(negedge clk); #1;
            check(pending && !ready && !accept && oa == 25'h2000 && od == 16'ha55a && ol == 3,
                  "idle READY cannot discard an unissued retained write");
        end
        stale_ready = 0;
        // I/O and locked reads cannot enter the bridge; HLDA cannot grant DMA.
        br = 0; bv = 1; bs = 10; dma = 1;
        repeat (4) begin @(negedge clk); #1; check(!av && !ac && !bridge_idle && !dma_grant, "I/O and DMA drain fence"); end
        bs = 5; bl = 1;
        repeat (4) begin @(negedge clk); #1; check(!av && !ac && !dma_grant, "LOCK read drain fence"); end
        bv = 0; bl = 0; cancel_cpu = 1;
        repeat (3) begin @(negedge clk); #1; check(pending && !dma_grant, "CPU reset retains posted store"); end
        stall = 0; drain(); expected_writes++;
        check(pins.mem['h1000] == 16'ha55a && writes == expected_writes, "reset drains exactly once");
        cancel_cpu = 0; #1; check(dma_grant, "DMA eligible after physical drain");
        @(negedge clk); done = 1; @(negedge clk); done = 0; dma = 0; br = 1;
        put(0, 25'h2001, 2'b10, 16'hc300);
        put(0, 25'h2000, 2'b01, 16'h007e);
        admit(1, 0, 25'h2000, 3, 0); finish_response(0, 16'hc37e, 1); drain();
        // Non-CPU stores and locked stores retain physical acknowledgement.
        put(1, 25'h2000, 3, 16'h1122);
        put(3, 25'h2000, 3, 16'h3344);
        cpu_lock = 1; put(0, 25'h2000, 3, 16'h5566); cpu_lock = 0;
        // ROM, refresh, and burst requests are never posted.
        put(0, 25'hf2000, 3, 16'h7788);
        admit(2, 0, 25'h2000, 3, 0); finish_response(0); drain();
        for (integer i = 0; i < 4; i++) put(0, 25'h2400 + 25'(2*i), 3, 16'h3100 + 16'(i));
        admit(0, 0, 25'h2400, 3, 0, 1);
        for (integer beat = 0; beat < 4; beat++) begin
            while (!read_valid) begin @(negedge clk); #1; end
            check(read_data == 16'h3100 + 16'(beat), "burst beat order");
            check(ready == (beat == 3), "burst final completion");
            @(posedge clk); #1;
        end
        drain();
        for (integer i = 0; i < 32; i++)
            put(0, 25'h2800 + 25'(2*i) + (i[0] ? 25'h1000000 : 0), 3, 16'h5000 + 16'(i));
        for (integer i = 0; i < 32; i++) begin
            admit(0, 0, 25'h2800 + 25'(2*i) + (i[0] ? 25'h1000000 : 0), 3, 0);
            finish_response(0, 16'h5000 + 16'(i), 1); drain();
        end
        check(posts == drains && refreshes > 10, "all posts drained with periodic refresh");
        // Global reset drops an unissued record, with no later replay.
        stall = 1; admit(0, 1, 25'h3000, 3, 16'hffff); finish_response(1);
        @(negedge clk); reset = 1;
        repeat (3) @(negedge clk);
        check(!pending && idle, "global reset clears queue");
        reset = 0; stall = 0; wait(pi);
        repeat (8) @(negedge clk);
        check(writes == 0 && posts == 0 && drains == 0, "global reset does not replay a discarded record");
        $display("AT_POSTED_WRITE_BUFFER_PASS checks=%0d cycles=%0d refreshes=%0d", checks, cycles, refreshes);
        $finish;
    end
endmodule
