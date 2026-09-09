`timescale 1ns/1ps

// Cycle-for-cycle equivalence check for the production timing formulation.
module spk286_operand_reference (
    input logic clk, reset, cancel,
    input logic request_valid, request_write, request_check, request_byte, select_rm,
    input logic [15:0] write_data,
    output logic done, output logic [15:0] read_data,
    input logic [127:0] register_state,
    input logic [2:0] reg_index, rm_index, input logic register_direct,
    input logic [23:0] physical_address, input logic [15:0] offset, segment_limit,
    output logic blocked, output logic gpr_write_en, gpr_write_byte,
    output logic [2:0] gpr_write_index, output logic [15:0] gpr_write_data,
    output logic memory_request, input logic memory_request_ready,
    output logic memory_write, memory_byte, output logic [23:0] memory_address,
    output logic [15:0] memory_write_data, input logic memory_response_valid,
    output logic memory_response_ready, input logic [15:0] memory_read_data
);
    logic pending_q, is_memory, allowed, within_limit;
    logic [2:0] register_index, word_index;
    logic [15:0] register_word;
    assign register_index = select_rm ? rm_index : reg_index;
    assign is_memory = select_rm && !register_direct;
    assign within_limit = ({1'b0, offset} + (request_byte ? 17'd0 : 17'd1)) <= {1'b0, segment_limit};
    assign allowed = request_valid && !reset && !cancel && !blocked;
    assign memory_request = allowed && is_memory && !pending_q && within_limit && !request_check;
    assign memory_write = request_write;
    assign memory_byte = request_byte;
    assign memory_address = physical_address;
    assign memory_write_data = write_data;
    assign memory_response_ready = allowed && pending_q;
    assign done = allowed && ((request_check && (!is_memory || within_limit) && !pending_q) ||
                              (!is_memory && !pending_q) ||
                              (pending_q && memory_response_valid));
    assign word_index = request_byte ? {1'b0, register_index[1:0]} : register_index;
    assign register_word = register_state[word_index * 16 +: 16];
    assign read_data = is_memory ? memory_read_data : (request_byte ?
                       {8'd0, (register_index[2] ? register_word[15:8] : register_word[7:0])} : register_word);
    assign gpr_write_en = done && request_write && !is_memory && !request_check;
    assign gpr_write_index = register_index;
    assign gpr_write_byte = request_byte;
    assign gpr_write_data = write_data;
    always_ff @(posedge clk) begin
        if (reset || cancel) begin pending_q <= 1'b0; blocked <= 1'b0; end
        else begin
            if (allowed && is_memory && !within_limit) blocked <= 1'b1;
            if (memory_request && memory_request_ready) pending_q <= 1'b1;
            if (memory_response_ready && memory_response_valid) pending_q <= 1'b0;
        end
    end
endmodule

module spk286_operand_timing_tb;
    logic clk=0, reset=1, cancel=0;
    logic request_valid=0, request_write=0, request_check=0, request_byte=0, select_rm=0;
    logic [15:0] write_data=0, offset=0, segment_limit=16'hffff, memory_read_data=0;
    logic [127:0] register_state=0;
    logic [2:0] reg_index=0, rm_index=0;
    logic register_direct=0;
    logic [23:0] physical_address=0;
    logic memory_request_ready=0, memory_response_valid=0;
    integer checks=0;

    always #5 clk=~clk;

`define OPERAND_PORTS(PFX) \
    .clk(clk),.reset(reset),.cancel(cancel),.request_valid(request_valid), \
    .request_write(request_write),.request_check(request_check),.request_byte(request_byte), \
    .select_rm(select_rm),.write_data(write_data),.done(PFX``done),.read_data(PFX``read_data), \
    .register_state(register_state),.reg_index(reg_index),.rm_index(rm_index), \
    .register_direct(register_direct),.physical_address(physical_address),.offset(offset), \
    .segment_limit(segment_limit),.blocked(PFX``blocked),.gpr_write_en(PFX``gpr_write_en), \
    .gpr_write_byte(PFX``gpr_write_byte),.gpr_write_index(PFX``gpr_write_index), \
    .gpr_write_data(PFX``gpr_write_data),.memory_request(PFX``memory_request), \
    .memory_request_ready(memory_request_ready),.memory_write(PFX``memory_write), \
    .memory_byte(PFX``memory_byte),.memory_address(PFX``memory_address), \
    .memory_write_data(PFX``memory_write_data),.memory_response_valid(memory_response_valid), \
    .memory_response_ready(PFX``memory_response_ready),.memory_read_data(memory_read_data)

    wire ref_done,ref_blocked,ref_gpr_write_en,ref_gpr_write_byte,ref_memory_request;
    wire ref_memory_write,ref_memory_byte,ref_memory_response_ready;
    wire [15:0] ref_read_data,ref_gpr_write_data,ref_memory_write_data;
    wire [2:0] ref_gpr_write_index;
    wire [23:0] ref_memory_address;
    wire dut_done,dut_blocked,dut_gpr_write_en,dut_gpr_write_byte,dut_memory_request;
    wire dut_memory_write,dut_memory_byte,dut_memory_response_ready;
    wire [15:0] dut_read_data,dut_gpr_write_data,dut_memory_write_data;
    wire [2:0] dut_gpr_write_index;
    wire [23:0] dut_memory_address;

    spk286_operand_reference reference (`OPERAND_PORTS(ref_));
    spk286_operand dut (`OPERAND_PORTS(dut_));

    task automatic compare;
        begin
            checks++;
            if ({dut_done,dut_read_data,dut_blocked,dut_gpr_write_en,dut_gpr_write_byte,
                 dut_gpr_write_index,dut_gpr_write_data,dut_memory_request,dut_memory_write,
                 dut_memory_byte,dut_memory_address,dut_memory_write_data,dut_memory_response_ready} !==
                {ref_done,ref_read_data,ref_blocked,ref_gpr_write_en,ref_gpr_write_byte,
                 ref_gpr_write_index,ref_gpr_write_data,ref_memory_request,ref_memory_write,
                 ref_memory_byte,ref_memory_address,ref_memory_write_data,ref_memory_response_ready} ||
                dut.pending_q !== reference.pending_q) begin
                $display("FAIL equivalence at check %0d",checks); $fatal(1);
            end
        end
    endtask

    task automatic step;
        begin @(negedge clk); #1; compare(); end
    endtask

    initial begin
        register_state=128'h0123456789abcdef_fedcba9876543210;
        repeat(2) step(); reset=0;

        // Directed accepted-memory response with a subsequently invalid offset.
        request_valid=1; select_rm=1; register_direct=0; offset=16'h1000;
        segment_limit=16'hffff; memory_request_ready=1; step();
        memory_request_ready=0; offset=16'hffff; memory_response_valid=1; step();
        memory_response_valid=0; cancel=1; step(); cancel=0;

        repeat(50000) begin
            request_valid=$urandom; request_write=$urandom; request_check=$urandom;
            request_byte=$urandom; select_rm=$urandom; register_direct=$urandom;
            write_data=$urandom; register_state={$urandom,$urandom,$urandom,$urandom};
            reg_index=$urandom; rm_index=$urandom; physical_address=$urandom;
            offset=$urandom; segment_limit=$urandom; memory_read_data=$urandom;
            memory_request_ready=$urandom; memory_response_valid=$urandom;
            cancel=($urandom_range(0,63)==0); reset=($urandom_range(0,255)==0);
            step();
        end
        $display("SPK286_OPERAND_TIMING_EQUIVALENCE_PASS checks=%0d",checks);
        $finish;
    end
endmodule
