// Board-side phase correction only. CPU/KFSDRAM remain on the original 50 MHz.
`timescale 1ns/1ps
module spk286_at_sdram_phase_clock (
    input wire clk_50, reset,
    output wire shifted_clock, locked
);
    wire unused_fboutclock;
    altera_pll #(
        .fractional_vco_multiplier("false"),
        .reference_clock_frequency("50.0 MHz"),
        .operation_mode("direct"), .number_of_clocks(1),
        .output_clock_frequency0("50.0 MHz"),
        .phase_shift0("-3000 ps"), .duty_cycle0(50),
        .pll_type("General"), .pll_subtype("General")
    ) pll (
        .refclk(clk_50), .rst(reset), .outclk(shifted_clock),
        .locked(locked), .fboutclk(unused_fboutclock), .fbclk(1'b0)
    );
endmodule
