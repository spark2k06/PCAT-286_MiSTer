`timescale 1ns/1ps

module spk286_at_splash_control_tb;
    logic clk = 1'b0;
    logic reset = 1'b1;
    logic option_off = 1'b0;
    logic second_tick = 1'b0;
    wire  splash_active;

    always #5 clk = ~clk;

    spk286_at_splash_control dut (
        .clk(clk), .reset(reset), .option_off(option_off),
        .second_tick(second_tick), .splash_active(splash_active)
    );

    task automatic pulse_second;
        begin
            @(negedge clk);
            second_tick = 1'b1;
            @(negedge clk);
            second_tick = 1'b0;
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        reset = 1'b0;
        #1;
        if (splash_active)
            $fatal(1, "splash started before the one-second delay");

        pulse_second();
        #1;
        if (!splash_active)
            $fatal(1, "splash did not start after the delay");

        repeat (5) pulse_second();
        #1;
        if (splash_active)
            $fatal(1, "splash did not expire after five seconds");

        reset = 1'b1;
        option_off = 1'b0;
        repeat (2) @(posedge clk);
        reset = 1'b0;
        option_off = 1'b1;
        pulse_second();
        #1;
        if (splash_active)
            $fatal(1, "OSD No option did not suppress splash");

        $display("AT_SPLASH_CONTROL_PASS");
        $finish;
    end
endmodule
