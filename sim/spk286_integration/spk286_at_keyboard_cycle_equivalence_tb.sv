`timescale 1ns/1ps
module spk286_at_keyboard_cycle_equivalence_tb;
    logic clk = 0;
    always #10 clk = ~clk;
    logic reset = 1, translate_set1 = 0, num_lock = 0, byte_ready = 0;
    logic [10:0] ps2_key = 0;
    wire reference_valid, candidate_valid, reference_overflow, candidate_overflow;
    wire [7:0] reference_byte, candidate_byte;
    logic [31:0] random_q = 32'h28650ACE;
    integer cycles = 0, transferred = 0, simultaneous = 0, full_simultaneous = 0;
    integer resets = 0, held = 0;
    logic [31:0] trace_hash = 32'h811C9DC5;

    spk286_at_keyboard_reference reference_keyboard (
        .clk(clk), .reset(reset), .ps2_key(ps2_key),
        .translate_set1(translate_set1), .num_lock(num_lock),
        .keyboard_byte_ready(byte_ready), .keyboard_byte_valid(reference_valid),
        .keyboard_byte(reference_byte), .overflow(reference_overflow)
    );
    spk286_at_keyboard candidate_keyboard (
        .clk(clk), .reset(reset), .ps2_key(ps2_key),
        .translate_set1(translate_set1), .num_lock(num_lock),
        .keyboard_byte_ready(byte_ready), .keyboard_byte_valid(candidate_valid),
        .keyboard_byte(candidate_byte), .overflow(candidate_overflow)
    );

    always @(posedge clk) begin
        if (reset) resets = resets + 1;
        if (!reset && reference_valid && byte_ready) begin
            transferred = transferred + 1;
            trace_hash = (trace_hash ^ {24'd0, reference_byte}) * 32'h01000193;
        end
        if (!reset && reference_valid && !byte_ready) held = held + 1;
        if (!reset && reference_keyboard.enqueue && reference_keyboard.load_event) begin
            simultaneous = simultaneous + 1;
            if (reference_keyboard.count_q == 32) full_simultaneous = full_simultaneous + 1;
        end
        #1;
        cycles = cycles + 1;
        if ({candidate_valid, candidate_byte, candidate_overflow} !==
            {reference_valid, reference_byte, reference_overflow})
            $fatal(1, "Cycle-visible keyboard mismatch cycle=%0d", cycles);
        if ({candidate_keyboard.sequence_q, candidate_keyboard.remaining_q,
             candidate_keyboard.read_ptr_q, candidate_keyboard.write_ptr_q,
             candidate_keyboard.count_q, candidate_keyboard.left_shift_q,
             candidate_keyboard.right_shift_q, candidate_keyboard.toggle_q} !==
            {reference_keyboard.sequence_q, reference_keyboard.remaining_q,
             reference_keyboard.read_ptr_q, reference_keyboard.write_ptr_q,
             reference_keyboard.count_q, reference_keyboard.left_shift_q,
             reference_keyboard.right_shift_q, reference_keyboard.toggle_q})
            $fatal(1, "Sequential keyboard mismatch cycle=%0d", cycles);
    end

    task automatic step(input bit resetting, input bit ready_input,
                        input bit new_event, input [9:0] event_data);
        @(negedge clk);
        reset = resetting;
        byte_ready = ready_input;
        if (new_event) ps2_key = {~ps2_key[10], event_data};
        @(posedge clk); #2;
    endtask

    task automatic advance_random;
        random_q = random_q ^ (random_q << 13);
        random_q = random_q ^ (random_q >> 17);
        random_q = random_q ^ (random_q << 5);
    endtask

    initial begin
        step(1, 0, 0, 0);
        step(1, 0, 1, {1'b1, 1'b0, 8'h12});
        step(0, 0, 0, 0);
        if (candidate_keyboard.count_q != 0) $fatal(1, "Replayed reset event");
        // Exactly fill the FIFO, overflow it, then enqueue on the very edge
        // that loads a sequence from a full queue. Preserve all 32 events.
        for (integer i = 0; i < 32; i = i + 1)
            step(0, 0, 1, {1'b1, 1'b0, 8'h1C});
        if (candidate_keyboard.count_q != 32) $fatal(1, "FIFO did not fill");
        step(0, 0, 1, {1'b1, 1'b1, 8'h75});
        if (!candidate_overflow || candidate_keyboard.count_q != 32)
            $fatal(1, "Full FIFO did not reject/report overflow");
        step(0, 1, 1, {1'b1, 1'b1, 8'h75});
        if (candidate_keyboard.count_q != 32) $fatal(1, "Full simultaneous enqueue/dequeue changed count");
        for (integer i = 0; i < 512; i = i + 1) step(0, 1, 0, 0);
        // Both shifts, navigation make/break, Pause and Print Screen, with
        // changing translation/LED policy and adversarial output stalls.
        for (integer policy = 0; policy < 4; policy = policy + 1) begin
            translate_set1 = policy[1];
            num_lock = policy[0];
            step(0, 0, 1, {1'b1, 1'b0, 8'h12});
            step(0, 0, 1, {1'b1, 1'b0, 8'h59});
            step(0, 0, 1, {1'b1, 1'b1, 8'h75});
            step(0, 0, 1, {1'b0, 1'b1, 8'h75});
            step(0, 0, 1, {1'b1, 1'b1, 8'h77});
            step(0, 0, 1, {1'b0, 1'b1, 8'h77});
            step(0, 0, 1, {1'b1, 1'b1, 8'h7C});
            step(0, 0, 1, {1'b0, 1'b1, 8'h7C});
            step(0, 0, 1, {1'b0, 1'b0, 8'h12});
            step(0, 0, 1, {1'b0, 1'b0, 8'h59});
            for (integer i = 0; i < 512; i = i + 1) step(0, i[1], 0, 0);
        end
        for (integer i = 0; i < 20000; i = i + 1) begin
            advance_random();
            translate_set1 = random_q[12];
            num_lock = random_q[13];
            step((i % 1024) == 0, random_q[2] && random_q[3],
                 random_q[0], random_q[23:14]);
        end
        for (integer i = 0; i < 512; i = i + 1) step(0, 1, 0, 0);
        if (candidate_keyboard.count_q || candidate_keyboard.remaining_q)
            $fatal(1, "Final queue did not drain");
        if (full_simultaneous == 0 || simultaneous < 2 || held == 0 || resets < 3)
            $fatal(1, "Missing temporal coverage");
        $display("AT_KEYBOARD_CYCLE_EQUIVALENCE_PASS cycles=%0d bytes=%0d held=%0d simultaneous=%0d full_simultaneous=%0d resets=%0d trace=%08x",
                 cycles, transferred, held, simultaneous, full_simultaneous, resets, trace_hash);
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1, "Keyboard equivalence timeout");
    end
endmodule
