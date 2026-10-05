module miter(
input task_commit_gpr_write,iret_outer_sp_commit,retf_outer_sp_commit,
input return_same_sp_commit,call_gate_sp_commit,segment_pop_sp_commit,
input descriptor_result_write,fixed_result_write,string_index_write,
input string_count_write,string_write_acc,add_allocation_arch,frame_write_gpr,
input allocate_stack,move_source,stack_arch_write,count_operation,result_to_dst,move_word,
input commit_context,allocation_valid_q,write_result_dx,
input [3:0] task_commit_phase_q,
input [127:0] task_loaded_gpr,
input [15:0] iret_outer_sp_q,allocation_q,stack_cursor_q,descriptor_result_data,
input [15:0] auxiliary_q,tmp0_q,tmp1_q,tmp2_q,string_index,string_delta,
input [15:0] count_value,stack_pointer,stack_next_sp,operand_gpr_write_data,architectural_flags,
output mismatch);
wire [15:0] old_data,sequential_gpr_write_data;
    assign old_data = task_commit_gpr_write ? task_loaded_gpr[task_commit_phase_q[2:0] * 16 +: 16] : iret_outer_sp_commit ? iret_outer_sp_q : retf_outer_sp_commit ? iret_outer_sp_q + allocation_q : return_same_sp_commit ? stack_cursor_q + ((commit_context && allocation_valid_q) ? allocation_q : 16'd0) : call_gate_sp_commit ? stack_cursor_q : segment_pop_sp_commit ? stack_cursor_q : descriptor_result_write ? descriptor_result_data : fixed_result_write ? (write_result_dx ? auxiliary_q : tmp2_q) : string_index_write ? (architectural_flags[10] ? string_index-string_delta : string_index+string_delta) : string_count_write ? count_value-16'd1 : string_write_acc ? tmp0_q : add_allocation_arch ? stack_pointer+allocation_q : frame_write_gpr ? tmp0_q : allocate_stack ? stack_cursor_q - allocation_q : move_source ? tmp1_q : stack_arch_write ? stack_next_sp : (count_operation ? count_value - 16'd1 : (result_to_dst ? tmp2_q : (move_word ? tmp0_q : operand_gpr_write_data)));
    logic [19:0] gpr_data_requests;
    (* keep *) logic [19:0] gpr_data_onehot;
    logic [319:0] gpr_data_values;
    function automatic logic [15:0] reduce_gpr_data(
        input logic [19:0] enables, input logic [319:0] values
    );
        reduce_gpr_data = 16'd0;
        for (integer i = 0; i < 20; i = i + 1)
            reduce_gpr_data = reduce_gpr_data | ({16{enables[i]}} & values[i*16 +: 16]);
    endfunction
    genvar gpr_data_index;
    generate
    for (gpr_data_index = 0; gpr_data_index < 20; gpr_data_index = gpr_data_index + 1) begin : g_gpr_data_priority
        if (gpr_data_index == 0) begin : g_first
            assign gpr_data_onehot[gpr_data_index] = gpr_data_requests[gpr_data_index];
        end else begin : g_remaining
            assign gpr_data_onehot[gpr_data_index] = gpr_data_requests[gpr_data_index] &&
                                                   1'b1;
        end
    end
    endgenerate
    assign gpr_data_requests = {1'b1, move_word, result_to_dst, count_operation, stack_arch_write, move_source, allocate_stack, frame_write_gpr, add_allocation_arch, string_write_acc, string_count_write, string_index_write, fixed_result_write, descriptor_result_write, segment_pop_sp_commit, call_gate_sp_commit, return_same_sp_commit, retf_outer_sp_commit, iret_outer_sp_commit, task_commit_gpr_write};
    assign gpr_data_values = {
        (operand_gpr_write_data),
        (tmp0_q),
        (tmp2_q),
        (count_value - 16'd1),
        (stack_next_sp),
        (tmp1_q),
        (stack_cursor_q - allocation_q),
        (tmp0_q),
        (stack_pointer+allocation_q),
        (tmp0_q),
        (count_value-16'd1),
        (architectural_flags[10] ? string_index-string_delta : string_index+string_delta),
        (write_result_dx ? auxiliary_q : tmp2_q),
        (descriptor_result_data),
        (stack_cursor_q),
        (stack_cursor_q),
        (stack_cursor_q + ((commit_context && allocation_valid_q) ? allocation_q : 16'd0)),
        (iret_outer_sp_q + allocation_q),
        (iret_outer_sp_q),
        (task_loaded_gpr[task_commit_phase_q[2:0] * 16 +: 16])
    };
    assign sequential_gpr_write_data = reduce_gpr_data(gpr_data_onehot, gpr_data_values);
assign mismatch=old_data!=sequential_gpr_write_data;
endmodule
