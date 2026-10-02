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
