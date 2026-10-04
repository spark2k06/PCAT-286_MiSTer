// Unwired minimum-duration policy, NOT complete instruction timing.
// Start at the qualified instruction start, in parallel with functional work.
// The functional owner retains results and determines dependencies/commit.
// No read/write issue phase is inferred from the aggregate Intel tables here.
`timescale 1ns/1ps
module p06_instruction_duration #(
    parameter bit HISTORICAL = 1'b1, parameter bit P06_LATE_ALIGNMENT = 1'b0
) (
    input logic clk, reset, cancel, cpu_boundary,
    input logic start_valid,
    output logic start_ready,
    input logic [3:0] instruction_form,
    input logic real_mode, prefix_free, taken, branch_outcome_known,
    input logic target_length_known,
    input logic [3:0] next_length,
    input logic operand_odd, ea_base_index_disp,
    // One actual extra wait on a qualified memory READ at a CPU boundary.
    // Write/fetch/consumer waits are not included in this table correction.
    /* verilator lint_off UNUSEDSIGNAL */
    input logic alignment_event,
    /* verilator lint_on UNUSEDSIGNAL */
    input logic read_wait_event,
    input logic functional_done, dependencies_ready, retire_ready,
    output logic retire_enable, dependency_blocked, consumer_blocked,
    output logic metadata_qualified, metadata_error, timing_error, active,
    output logic [5:0] minimum_clocks,
    output logic [7:0] elapsed_clocks, scheduled_clocks
);
    generate
        if (HISTORICAL) begin : historical
            // These are already-decoded forms, not another opcode decoder.
            localparam logic [3:0] ADD_RR = 0, XOR_RR = 1, CMP_RR = 2,
                ADD_RI = 3, XOR_RI = 4, JCC = 5, JMP_SHORT = 6, LOOP = 7,
                MOFFS_READ = 8, MOFFS_WRITE = 9, ADD_RM = 10, XOR_MI = 11;
            logic row_known, memory_form, permits_read_wait, branch_form;
            logic requires_target_length;
            logic [5:0] base_clocks, alignment_clocks;
            logic active_q, permits_wait_q;
            logic [7:0] elapsed_q, budget_q;
            wire wait_increment = active_q && cpu_boundary && permits_wait_q && read_wait_event;
            wire alignment_increment = P06_LATE_ALIGNMENT && active_q && cpu_boundary && permits_wait_q && alignment_event;
            wire [8:0] extended_budget = {1'b0, budget_q} + 9'(wait_increment) +
                (alignment_increment ? 9'd2 : 9'd0);
            wire [8:0] next_elapsed = (elapsed_q == 8'hff) ? 9'd255 :
                                      ({1'b0, elapsed_q} + 9'd1);
            wire event_bad = (read_wait_event || (P06_LATE_ALIGNMENT && alignment_event)) &&
                (!active_q || !cpu_boundary || !permits_wait_q);
            wire overflow = active_q && cpu_boundary && extended_budget[8];
            wire eligible = !reset && !cancel && active_q && cpu_boundary &&
                            !timing_error && !event_bad && !overflow &&
                            next_elapsed >= extended_budget;
            wire retire_fire = retire_enable && retire_ready;
            wire admission_boundary = !reset && !cancel && cpu_boundary &&
                                      !timing_error && (!active_q || retire_fire);
            wire start_fire = start_valid && start_ready;

            always_comb begin
                row_known = 1'b1; memory_form = 1'b0; permits_read_wait = 1'b0;
                branch_form = 1'b0; requires_target_length = 1'b0;
                base_clocks = 6'd0; alignment_clocks = 6'd0;
                case (instruction_form)
                    ADD_RR, XOR_RR, CMP_RR: base_clocks = 6'd2;
                    ADD_RI, XOR_RI: base_clocks = 6'd3;
                    JCC: begin
                        branch_form = 1'b1;
                        base_clocks = taken ? 6'd7 : 6'd3;
                        requires_target_length = taken;
                    end
                    JMP_SHORT: begin
                        base_clocks = 6'd7; requires_target_length = 1'b1;
                    end
                    LOOP: begin
                        branch_form = 1'b1; base_clocks = taken ? 6'd8 : 6'd4;
                    end
                    MOFFS_READ: begin
                        base_clocks = 6'd5; memory_form = 1'b1; permits_read_wait = 1'b1;
                    end
                    MOFFS_WRITE: begin base_clocks = 6'd3; memory_form = 1'b1; end
                    ADD_RM, XOR_MI: begin
                        base_clocks = 6'd7; memory_form = 1'b1; permits_read_wait = 1'b1;
                    end
                    default: row_known = 1'b0;
                endcase
                if (operand_odd && memory_form)
                    alignment_clocks = (instruction_form == XOR_MI) ? 6'd4 : 6'd2;
                minimum_clocks = base_clocks + alignment_clocks +
                    6'(memory_form && ea_base_index_disp) +
                    (requires_target_length ? {2'b0, next_length} : 6'd0);
                metadata_qualified = row_known && real_mode && prefix_free &&
                    (!branch_form || branch_outcome_known) &&
                    (memory_form || (!operand_odd && !ea_base_index_disp)) &&
                    // Direct-offset A1/A3 cannot use a base/index EA.
                    (!ea_base_index_disp || instruction_form == ADD_RM || instruction_form == XOR_MI) &&
                    (!requires_target_length || (target_length_known && next_length >= 1 && next_length <= 6));
                if (!metadata_qualified) minimum_clocks = 6'd0;
            end

            assign start_ready = admission_boundary && metadata_qualified;
            assign metadata_error = admission_boundary && start_valid && !metadata_qualified;
            assign retire_enable = eligible && functional_done && dependencies_ready;
            assign dependency_blocked = eligible && (!functional_done || !dependencies_ready);
            assign consumer_blocked = retire_enable && !retire_ready;
            assign active = active_q;
            assign elapsed_clocks = elapsed_q;
            assign scheduled_clocks = budget_q;

            always_ff @(posedge clk) begin
                if (reset) begin
                    active_q <= 0; permits_wait_q <= 0;
                    elapsed_q <= 0; budget_q <= 0; timing_error <= 0;
                end else begin
                    // Budget overflow/malformed wait is explicit, never wraps or retires.
                    if (!cancel && (event_bad || overflow)) timing_error <= 1'b1;
                    if (active_q && cpu_boundary) begin
                        elapsed_q <= next_elapsed[7:0];
                        if ((wait_increment || alignment_increment) && !overflow) budget_q <= extended_budget[7:0];
                    end
                    if (retire_fire) active_q <= 1'b0;
                    if (cancel) begin
                        active_q <= 0; permits_wait_q <= 0; elapsed_q <= 0; budget_q <= 0;
                    end
                    if (start_fire) begin
                        active_q <= 1'b1; permits_wait_q <= permits_read_wait;
                        elapsed_q <= 0; budget_q <= {2'b0, minimum_clocks};
                    end
                end
            end
        end else begin : maximum
            // Functional owner supplies its existing dispatch/commit contract.
            assign start_ready = !reset && !cancel;
            assign retire_enable = !reset && !cancel && functional_done && dependencies_ready;
            assign metadata_qualified = 1'b1; assign metadata_error = 1'b0;
            assign timing_error = 1'b0; assign active = 1'b0;
            assign dependency_blocked = 1'b0; assign consumer_blocked = 1'b0;
            assign minimum_clocks = 6'd0; assign elapsed_clocks = 8'd0;
            assign scheduled_clocks = 8'd0;
        end
    endgenerate
endmodule
