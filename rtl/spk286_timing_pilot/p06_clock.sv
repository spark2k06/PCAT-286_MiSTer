// Provisional CPU timing component. Not part of the production QIP.
// 50 MHz fabric -> 12 MHz phase events -> 6 MHz processor boundaries.
// Enables are sampled on the existing rising edge; they are not clocks.
`timescale 1ns/1ps
module p06_clock #(
    parameter bit HISTORICAL = 1'b1
) (
    input  logic clk,
    input  logic reset,
    output logic phase_enable,
    output logic phase_two,
    output logic cpu_enable
);
    generate
        if (HISTORICAL) begin : historical
            logic [4:0] phase_accumulator_q;
            logic phase_parity_q;
            wire [5:0] phase_sum = {1'b0, phase_accumulator_q} + 6'd6;
            wire carry = phase_sum >= 6'd25;

            assign phase_enable = !reset && carry;
            assign phase_two = phase_enable && phase_parity_q;
            assign cpu_enable = phase_two;

            always_ff @(posedge clk) begin
                if (reset) begin
                    phase_accumulator_q <= 5'd0;
                    phase_parity_q <= 1'b0;
                end else begin
                    phase_accumulator_q <= carry ?
                        5'(phase_sum - 6'd25) : phase_sum[4:0];
                    if (carry) phase_parity_q <= !phase_parity_q;
                end
            end
        end else begin : maximum
            // No historical phase meaning in MAX; no state or timing delay.
            assign phase_enable = 1'b0;
            assign phase_two = 1'b0;
            assign cpu_enable = !reset;
        end
    endgenerate
endmodule
