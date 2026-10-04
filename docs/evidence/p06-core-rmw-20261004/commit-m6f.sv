module p06_rmw_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0) (
input logic [7:0] operation, input logic [2:0] temporary_valid_q,
input logic p06_moffs_read, p06_rmw_form, register_complete, move_word, allowed, flags_valid_q, result_disposed_q,
output logic p06_memory_result_pending, operation_retire, commit_flags);
    assign p06_memory_result_pending = P06_MEMORY_TIMING && p06_moffs_read &&
        operation == 8'd2 && temporary_valid_q[0];
    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word);
    assign commit_flags = allowed && operation == 8'd18 && flags_valid_q && result_disposed_q;
endmodule
