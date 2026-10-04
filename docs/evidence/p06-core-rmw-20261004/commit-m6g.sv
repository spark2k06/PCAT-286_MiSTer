module p06_rmw_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0, parameter bit P06_RMW_TIMING=1'b0) (
input logic [7:0] operation, input logic [2:0] temporary_valid_q,
input logic p06_moffs_read, p06_rmw_form, register_complete, move_word, allowed, flags_valid_q, result_disposed_q,
output logic p06_memory_result_pending, operation_retire, commit_flags, p06_rmw_result_pending);
    assign p06_memory_result_pending = P06_MEMORY_TIMING && p06_moffs_read &&
        operation == 8'd2 && temporary_valid_q[0];
    // FLAGS and final retirement share the existing real COMMIT_FLAGS
    // edge, after WRITE response disposed TMP2. Only the END tail is
    // skipped. Pending must be visible while ALLOWED is gated.
    assign p06_rmw_result_pending = P06_RMW_TIMING && p06_rmw_form &&
        operation == 8'd18 && flags_valid_q && result_disposed_q;
    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word) ||
        (P06_RMW_TIMING && p06_rmw_form && commit_flags);
    assign commit_flags = allowed && operation == 8'd18 && flags_valid_q && result_disposed_q;
endmodule
