`timescale 1ns/1ps
module spk286_at_keyboard_packing_tb;
    logic [7:0] code = 0;
    logic pressed = 0, extended = 0, translate_set1 = 0, num_lock = 0;
    logic left_shift_q = 0, right_shift_q = 0;
    wire [63:0] reference_sequence, candidate_sequence;
    wire [3:0] reference_length, candidate_length;
    integer cases = 0;
    integer length_counts [0:8];

    keyboard_packing_reference reference_packer (
        .code(code), .pressed(pressed), .extended(extended),
        .translate_set1(translate_set1), .num_lock(num_lock),
        .left_shift_q(left_shift_q), .right_shift_q(right_shift_q),
        .next_sequence(reference_sequence), .next_length(reference_length)
    );
    keyboard_packing_candidate candidate_packer (
        .code(code), .pressed(pressed), .extended(extended),
        .translate_set1(translate_set1), .num_lock(num_lock),
        .left_shift_q(left_shift_q), .right_shift_q(right_shift_q),
        .next_sequence(candidate_sequence), .next_length(candidate_length)
    );

    initial begin
        for (integer length = 0; length <= 8; length = length + 1)
            length_counts[length] = 0;
        for (integer value = 0; value < 16384; value = value + 1) begin
            {pressed, extended, translate_set1, num_lock,
             left_shift_q, right_shift_q, code} = value[13:0];
            #1;
            if (reference_sequence !== candidate_sequence ||
                reference_length !== candidate_length)
                $fatal(1, "Packing mismatch input=%04x reference=%016x/%0d candidate=%016x/%0d",
                       value, reference_sequence, reference_length,
                       candidate_sequence, candidate_length);
            if (candidate_length > 8) $fatal(1, "Sequence exceeded eight bytes");
            length_counts[candidate_length] = length_counts[candidate_length] + 1;
            cases = cases + 1;
        end
        for (integer length = 0; length <= 8; length = length + 1) begin
            if (length_counts[length] == 0) $fatal(1, "Uncovered length %0d", length);
            $display("PACKING_LENGTH %0d cases=%0d", length, length_counts[length]);
        end
        $display("AT_KEYBOARD_PACKING_EQUIVALENCE_PASS cases=%0d full_64bit_sequence_and_length", cases);
        $finish;
    end
endmodule
