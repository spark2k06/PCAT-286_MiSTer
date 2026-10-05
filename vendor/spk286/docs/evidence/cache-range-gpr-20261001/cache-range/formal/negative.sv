module miter(
input [15:0] protected_msw, address_offset, vector_offset, stack_offset, operand_offset,
input [63:0] protected_segment_limits, real_segment_limits,
input [31:0] protected_segment_access, real_segment_access_state,
input [1:0] selected_segment_index,
input operand_byte, protected_event_access, protected_descriptor_access,
input protected_tss_access, protected_call_stack_access,
input vector_request, io_transfer, address_override, stack_request,
output mismatch);
wire [15:0] service_offset, selected_segment_limit, segment_limit, offset, op_limit;
wire [7:0] selected_segment_access;
wire protected_segment_is_code, protected_segment_is_expand_down;
wire segment_expand_down, request_byte, within_limit;
    function automatic logic protected_range_exceeded(
        input logic [15:0] offset_value, limit_value,
        input logic expand_down, is_byte
    );
        protected_range_exceeded = expand_down ?
            (offset_value <= limit_value || (!is_byte && offset_value == 16'hFFFF)) :
            (offset_value > limit_value || (!is_byte && offset_value == limit_value));
    endfunction
    assign service_offset = io_transfer ? 16'd0 : address_override && !stack_request && !vector_request ? address_offset : vector_request ? vector_offset : (stack_request ? stack_offset : operand_offset);
    assign selected_segment_limit = protected_msw[0] ? protected_segment_limits[selected_segment_index * 16 +: 16] : real_segment_limits[selected_segment_index * 16 +: 16];
    assign selected_segment_access = protected_msw[0] ? protected_segment_access[selected_segment_index * 8 +: 8] : real_segment_access_state[selected_segment_index * 8 +: 8];
    assign segment_limit = selected_segment_limit;
    assign protected_segment_is_code = selected_segment_access[3];
    assign protected_segment_is_expand_down = !protected_segment_is_code && selected_segment_access[2];
assign offset=(protected_event_access || protected_descriptor_access || protected_tss_access || protected_call_stack_access) ? 16'd0 : service_offset;
assign segment_expand_down=protected_msw[0] && protected_segment_is_expand_down && !protected_call_stack_access && !protected_event_access && !protected_descriptor_access && !protected_tss_access;
assign request_byte=operand_byte;
assign op_limit=(protected_event_access || protected_descriptor_access || protected_tss_access || protected_call_stack_access) ? 16'hFFFF : (vector_request ? 16'hFFFF : segment_limit);
    assign within_limit = segment_expand_down ?
                          (offset > op_limit &&
                           (request_byte || offset != 16'hFFFF)) :
                          (offset < op_limit ||
                           (request_byte && offset == op_limit));
    // Compare cache ranges before selecting the cache and offset sources.
    // Keep real-mode hidden limits, vector/I-O overlap and LOADALL state exact.
    (* keep *) logic [3:0] operand_io_ranges, operand_address_ranges, operand_stack_ranges;
    (* keep *) logic [3:0] operand_regular_ranges, operand_vector_ranges;
    logic parallel_operand_within_limit;
    genvar operand_cache_index;
    generate
    for (operand_cache_index = 0; operand_cache_index < 4; operand_cache_index = operand_cache_index + 1) begin : g_operand_cache_range
        wire [15:0] cache_limit = protected_msw[0] ?
            protected_segment_limits[operand_cache_index*16 +: 16] :
            real_segment_limits[operand_cache_index*16 +: 16];
        wire cache_expand_down = protected_msw[0] &&
            !protected_segment_access[operand_cache_index*8+3] &&
            protected_segment_access[operand_cache_index*8+2];
        assign operand_io_ranges[operand_cache_index] =
            !protected_range_exceeded(16'd0, cache_limit, cache_expand_down, operand_byte);
        assign operand_address_ranges[operand_cache_index] =
            !protected_range_exceeded(address_offset, cache_limit, cache_expand_down, operand_byte);
        assign operand_stack_ranges[operand_cache_index] =
            !protected_range_exceeded(stack_offset, cache_limit, cache_expand_down, operand_byte);
        assign operand_regular_ranges[operand_cache_index] =
            !protected_range_exceeded(operand_offset, cache_limit, cache_expand_down, operand_byte);
        assign operand_vector_ranges[operand_cache_index] =
            !protected_range_exceeded(io_transfer ? 16'd0 : vector_offset, 16'hFFFF, cache_expand_down, operand_byte);
    end
    endgenerate
    assign parallel_operand_within_limit =
        (protected_event_access || protected_descriptor_access || protected_tss_access || protected_call_stack_access) ? 1'b1 :
        vector_request ? operand_vector_ranges[selected_segment_index] :
        1'b0 ? operand_io_ranges[selected_segment_index] :
        address_override && !stack_request ? operand_address_ranges[selected_segment_index] :
        stack_request ? operand_stack_ranges[selected_segment_index] :
        operand_regular_ranges[selected_segment_index];
assign mismatch=within_limit!=parallel_operand_within_limit;
endmodule
