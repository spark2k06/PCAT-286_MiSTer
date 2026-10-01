// Connectivity-only model. This does not simulate PLL phase, locking or jitter.
`timescale 1ns/1ps
module altera_pll #(
    parameter fractional_vco_multiplier="false",
    parameter reference_clock_frequency="50.0 MHz", operation_mode="direct",
    parameter number_of_clocks=1, output_clock_frequency0="50.0 MHz",
    parameter phase_shift0="0 ps", duty_cycle0=50,
    parameter pll_type="General", pll_subtype="General"
) (
    input wire refclk, rst, fbclk,
    output wire [number_of_clocks-1:0] outclk,
    output wire locked, fboutclk
);
    assign outclk={number_of_clocks{refclk}};
    assign locked=!rst;
    assign fboutclk=1'b0;
endmodule
