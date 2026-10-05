module miter(
input [15:0] protected_msw, address_offset, vector_offset, stack_offset, operand_offset,
input [63:0] protected_segment_limits, real_segment_limits,
input [31:0] protected_segment_access, real_segment_access_state,
input [3:0] protected_segment_protected, protected_segment_valid, protected_segment_present,
input [1:0] selected_segment_index, service_segment,
input [15:0] protected_call_stack_limit,
input operand_request, operand_select_rm, operand_register_direct, operand_write, operand_byte,
input protected_event_access, protected_descriptor_access, protected_tss_access,
input protected_call_stack_access, protected_call_stack_expand_down,
input vector_request, io_transfer, address_override, stack_request, system_table_operation,
output mismatch);
wire [15:0] selected_segment_limit, segment_limit, effective_offset;
wire [7:0] selected_segment_access;
wire protected_segment_is_loaded, protected_segment_is_valid, protected_segment_is_present;
wire protected_segment_is_code, protected_segment_is_readable, protected_segment_is_writable;
wire protected_segment_is_expand_down, protected_call_range_fault, segment_expand_down;
wire old_selected_fault, protected_selected_range_fault, old_access_fault, protected_access_fault;
wire old_system_fault, system_limit_fault, parallel_system_limit_fault;
localparam USE_PARALLEL_SYSTEM_LIMIT=1'b1;
    function automatic logic protected_range_exceeded(
        input logic [15:0] offset_value, limit_value,
        input logic expand_down, is_byte
    );
        protected_range_exceeded = expand_down ?
            (offset_value <= limit_value || (!is_byte && offset_value == 16'hFFFF)) :
            (offset_value > limit_value || (!is_byte && offset_value == limit_value));
    endfunction
    assign selected_segment_limit = protected_msw[0] ? protected_segment_limits[selected_segment_index * 16 +: 16] : real_segment_limits[selected_segment_index * 16 +: 16];
    assign selected_segment_access = protected_msw[0] ? protected_segment_access[selected_segment_index * 8 +: 8] : real_segment_access_state[selected_segment_index * 8 +: 8];
    assign segment_limit = selected_segment_limit;
    assign protected_segment_is_loaded = protected_msw[0] && protected_segment_protected[service_segment];
    assign protected_segment_is_valid = protected_segment_valid[service_segment];
    assign protected_segment_is_present = protected_segment_present[service_segment];
    assign protected_segment_is_code = selected_segment_access[3];
    assign protected_segment_is_readable = selected_segment_access[1];
    assign protected_segment_is_writable = !protected_segment_is_code && selected_segment_access[1];
    assign protected_segment_is_expand_down = !protected_segment_is_code && selected_segment_access[2];
    assign protected_call_range_fault = stack_request ?
        protected_range_exceeded(stack_offset, protected_call_stack_limit, protected_call_stack_expand_down, operand_byte) :
        address_override ? protected_range_exceeded(address_offset, protected_call_stack_limit, protected_call_stack_expand_down, operand_byte) :
        protected_range_exceeded(operand_offset, protected_call_stack_limit, protected_call_stack_expand_down, operand_byte);
assign effective_offset=operand_offset;
assign segment_expand_down=protected_msw[0] && protected_segment_is_expand_down;
    assign old_selected_fault = stack_request ?
        protected_range_exceeded(stack_offset, selected_segment_limit, protected_segment_is_expand_down, operand_byte) :
        address_override ? protected_range_exceeded(address_offset, selected_segment_limit, protected_segment_is_expand_down, operand_byte) :
        protected_range_exceeded(operand_offset, selected_segment_limit, protected_segment_is_expand_down, operand_byte);
    assign old_access_fault = operand_request && operand_select_rm && !operand_register_direct &&
                                   !protected_descriptor_access && !protected_tss_access && !protected_event_access &&
                                   !io_transfer && !vector_request &&
                                    (protected_call_stack_access ?
                                    (service_segment != 2'd2 || protected_call_range_fault) :
                                    (protected_segment_is_loaded &&
                                     (!protected_segment_is_valid || !protected_segment_is_present ||
                                      (protected_segment_is_code ? (!protected_segment_is_readable || operand_write) :
                                       (stack_request ? (!protected_segment_is_writable || service_segment != 2'd2) :
                                        (operand_write && !protected_segment_is_writable))) ||
                                      old_selected_fault)));
    assign old_system_fault = system_table_operation && !operand_register_direct &&
                                (segment_expand_down ?
                                 (effective_offset <= segment_limit ||
                                  {1'b0, effective_offset} + 17'd5 > 17'h0FFFF) :
                                 ({1'b0, effective_offset} + 17'd5 > {1'b0, segment_limit}));
    // Compare cache ranges before selecting the cache and offset sources.
    // Keep real-mode hidden limits, vector/I-O overlap and LOADALL state exact.
    (* keep *) logic [3:0] operand_io_ranges, operand_address_ranges, operand_stack_ranges;
    (* keep *) logic [3:0] operand_regular_ranges, operand_vector_ranges;
    (* keep *) logic [3:0] operand_system_ranges;
    logic parallel_operand_within_limit, parallel_system_cache_fault;
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
        // Six-byte table operands use the ordinary effective offset.
        // Complete each cache's range comparison before the late index mux.
        assign operand_system_ranges[operand_cache_index] = cache_expand_down ?
            (operand_offset <= cache_limit) :
            ({1'b0, operand_offset} + 17'd5 > {1'b0, cache_limit});
    end
    endgenerate
    assign parallel_operand_within_limit =
        (protected_event_access || protected_descriptor_access || protected_tss_access || protected_call_stack_access) ? 1'b1 :
        vector_request ? operand_vector_ranges[selected_segment_index] :
        io_transfer ? operand_io_ranges[selected_segment_index] :
        address_override && !stack_request ? operand_address_ranges[selected_segment_index] :
        stack_request ? operand_stack_ranges[selected_segment_index] :
        operand_regular_ranges[selected_segment_index];
    assign parallel_system_cache_fault = operand_system_ranges[selected_segment_index];
    assign protected_selected_range_fault = !parallel_operand_within_limit;
    assign protected_access_fault = operand_request && operand_select_rm && !operand_register_direct &&
                                   !protected_descriptor_access && !protected_tss_access && !protected_event_access &&
                                   !io_transfer && !vector_request &&
                                    (protected_call_stack_access ?
                                    (service_segment != 2'd2 || protected_call_range_fault) :
                                    (protected_segment_is_loaded &&
                                     (!protected_segment_is_valid || !protected_segment_is_present ||
                                      (protected_segment_is_code ? (!protected_segment_is_readable || operand_write) :
                                       (stack_request ? (!protected_segment_is_writable || service_segment != 2'd2) :
                                        (operand_write && !protected_segment_is_writable))) ||
                                      protected_selected_range_fault)));
assign parallel_system_limit_fault=parallel_system_cache_fault;
    assign system_limit_fault = system_table_operation && !operand_register_direct &&
                                (USE_PARALLEL_SYSTEM_LIMIT ? parallel_system_limit_fault : segment_expand_down ?
                                 (effective_offset <= segment_limit ||
                                  {1'b0, effective_offset} + 17'd5 > 17'h0FFFF) :
                                 ({1'b0, effective_offset} + 17'd5 > {1'b0, segment_limit}));
assign mismatch=(old_access_fault!=protected_access_fault)||(old_system_fault!=system_limit_fault);
endmodule
