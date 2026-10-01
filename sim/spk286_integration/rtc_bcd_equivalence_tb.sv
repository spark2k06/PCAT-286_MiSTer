`timescale 1ns/1ps

module rtc_bcd_equivalence_tb;
    logic [7:0] value = 0;
    wire [7:0] candidate_result;
    wire [7:0] reference_result;
    integer checks = 0;

    rtc_bcd_candidate candidate_dut(value, candidate_result);
    rtc_bcd_reference reference_dut(value, reference_result);

    task automatic compare_results;
        #1;
        if (candidate_result !== reference_result)
            $fatal(1, "BCD mismatch input=%h actual=%h reference=%h",
                   value, candidate_result, reference_result);
        checks = checks + 1;
    endtask

    initial begin
        for (integer i = 0; i < 256; i = i + 1) begin
            value = 8'(i);
            compare_results();
        end
`ifdef TEST_FOUR_STATE
        for (integer i = 0; i < 256; i = i + 1) begin
            for (integer bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                value = 8'(i);
                value[bit_index] = 1'bx;
                compare_results();
                value = 8'(i);
                value[bit_index] = 1'bz;
                compare_results();
            end
        end
        value = 'x;
        compare_results();
        value = 'z;
        compare_results();
`endif
        $display("RTC_BCD_CONVERSION_PASS checks=%0d", checks);
        $finish;
    end
endmodule
