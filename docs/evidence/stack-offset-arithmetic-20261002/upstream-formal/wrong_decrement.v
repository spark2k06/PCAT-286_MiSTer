module offset_old(
    input call_parameter_read, call_parameter_write, iret_outer_pop, read_frame_address,
    input allocation_valid_q,
    input [15:0] call_parameter_source_sp_q, stack_cursor_q, return_stack_pointer,
    input [15:0] allocation_q, frame_address_q, stack_native_offset,
    output [15:0] stack_offset
);
    assign stack_offset = call_parameter_read ? call_parameter_source_sp_q :
                          call_parameter_write ? (stack_cursor_q - 16'd2) :
                          iret_outer_pop ? (return_stack_pointer + (allocation_valid_q ? allocation_q : 16'd0)) :
                          read_frame_address ? frame_address_q : stack_native_offset;
endmodule
module offset_new(
    input call_parameter_read, call_parameter_write, iret_outer_pop, read_frame_address,
    input allocation_valid_q,
    input [15:0] call_parameter_source_sp_q, stack_cursor_q, return_stack_pointer,
    input [15:0] allocation_q, frame_address_q, stack_native_offset,
    output [15:0] stack_offset
);
wire [15:0] call_parameter_write_offset;
wire [15:0] iret_parameter_bytes;
wire [15:0] iret_outer_stack_offset;
    assign call_parameter_write_offset = stack_cursor_q - 16'd1;
    assign iret_parameter_bytes = allocation_valid_q ? allocation_q : 16'd0;
    assign iret_outer_stack_offset = return_stack_pointer + iret_parameter_bytes;
    assign stack_offset = call_parameter_read ? call_parameter_source_sp_q :
                          call_parameter_write ? call_parameter_write_offset :
                          iret_outer_pop ? iret_outer_stack_offset :
                          read_frame_address ? frame_address_q : stack_native_offset;
endmodule
module miter(
    input call_parameter_read, call_parameter_write, iret_outer_pop, read_frame_address,
    input allocation_valid_q,
    input [15:0] call_parameter_source_sp_q, stack_cursor_q, return_stack_pointer,
    input [15:0] allocation_q, frame_address_q, stack_native_offset,
    output equivalent
);
wire [15:0] stack_offset_old, stack_offset_new;
offset_old u_old (.call_parameter_read(call_parameter_read),.call_parameter_write(call_parameter_write),.iret_outer_pop(iret_outer_pop),.read_frame_address(read_frame_address),.allocation_valid_q(allocation_valid_q),.call_parameter_source_sp_q(call_parameter_source_sp_q),.stack_cursor_q(stack_cursor_q),.return_stack_pointer(return_stack_pointer),.allocation_q(allocation_q),.frame_address_q(frame_address_q),.stack_native_offset(stack_native_offset),.stack_offset(stack_offset_old));
offset_new u_new (.call_parameter_read(call_parameter_read),.call_parameter_write(call_parameter_write),.iret_outer_pop(iret_outer_pop),.read_frame_address(read_frame_address),.allocation_valid_q(allocation_valid_q),.call_parameter_source_sp_q(call_parameter_source_sp_q),.stack_cursor_q(stack_cursor_q),.return_stack_pointer(return_stack_pointer),.allocation_q(allocation_q),.frame_address_q(frame_address_q),.stack_native_offset(stack_native_offset),.stack_offset(stack_offset_new));
assign equivalent = stack_offset_old == stack_offset_new;
endmodule
