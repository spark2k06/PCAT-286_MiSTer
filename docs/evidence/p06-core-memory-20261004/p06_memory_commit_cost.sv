module p06_memory_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0) (
input logic [7:0] operation, input logic [2:0] temporary_valid_q,
input logic p06_moffs_read, register_complete, move_word,
output logic p06_memory_result_pending, operation_retire);
    assign p06_memory_result_pending = P06_MEMORY_TIMING && p06_moffs_read &&
        operation == 8'd2 && temporary_valid_q[0];
    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word);
endmodule
