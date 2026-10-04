`timescale 1ns/1ps
// Cost fixture of the EXACT private connection, not a functional CPU or fit.
// Retain diagnostic reason outputs; these three bits can disappear without debug.
module p06_register_policy_cost #(
    parameter bit P06_REGISTER_PILOT = 1'b1
) (
    input logic clk, reset, semantic_cancel, restart, execute_enable,
    input logic [0:0] protected_msw,
    input logic [7:0] queue_consume_data, opcode_q,
    input logic micro_active, operand_context_valid, queue_consume_valid,
    input logic event_active, event_request, is_prefix, context_active,
    input logic raw_retired, event_completed, opcode_start,
    input logic execution_allowed, operation_valid, result_pending,
    input logic [15:0] cursor, debug_instruction_ip,
    output logic [15:0] debug_ip,
    output logic admit, block_execution, executor_permit, scope_error,
    output logic [2:0] scope_reason
);
    `include "p06_register_connection.svh"
    assign p06_cursor_ip = cursor;
    assign p06_result_pending = result_pending;
    assign admit = p06_admit;
    assign block_execution = p06_block;
    assign executor_permit = p06_executor_permit;
    generate
        if (P06_REGISTER_PILOT) begin : diagnostics
            assign scope_error = p06_register.scope_error;
            assign scope_reason = p06_register.scope_reason;
        end else begin : maximum_diagnostics
            assign scope_error = 1'b0;
            assign scope_reason = 3'd0;
        end
    endgenerate
endmodule
