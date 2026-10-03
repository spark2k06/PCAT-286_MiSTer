`timescale 1ns/1ps
module spk286_at_retained_fdc_malformed_tb;
    logic  clk = '0;
    logic  reset = 1'b1;
    logic  request_valid = '0;
    logic  request_command_valid = '0;
    logic  request_write = '0;
    logic  request_io = '0;
    logic [23:0] request_address = '0;
    logic [1:0] request_byte_enable = '0;
    logic [15:0] request_data_out = '0;
    logic  dma_transfer_valid = '0;
    logic  dma_transfer_complete = '0;
    logic  dma_terminal_count = '0;
    logic [2:0] dma_active_channel = '0;
    logic [15:0] dma_transfer_data_in = '0;
    logic [15:0] mgmt_address = '0;
    logic [15:0] mgmt_writedata = '0;
    logic  mgmt_write = '0;
    logic  mgmt_read = '0;
    logic [1:0] floppy_write_protect = '0;
    always #10 clk = ~clk;
    integer cycle=0; integer trace_gold; integer trace_gate; string trace_path;
    logic tracing=0; integer malformed_count=0; integer valid_count=0;
    wire  request_accept_gold;
    wire  request_ready_gold;
    wire [15:0] request_read_data_gold;
    wire  request_read_data_valid_gold;
    wire  dma_transfer_accept_gold;
    wire  dma_transfer_ready_gold;
    wire [15:0] dma_transfer_data_out_gold;
    wire [7:0] dma_request_gold;
    wire  irq6_gold;
    wire [15:0] mgmt_readdata_gold;
    wire [1:0] floppy_present_gold;
    wire [1:0] floppy_request_gold;
    wire [15:0] side_effect_count_gold;
    wire [15:0] command_count_gold;
    wire  proof_core_dma_req_gold;
    wire [7:0] proof_core_dma_writedata_gold;
    wire  proof_core_irq_gold;
    wire [7:0] proof_core_io_readdata_gold;
    wire  proof_core_fdd0_inserted_gold;
    wire [15:0] proof_core_mgmt_readdata_gold;
    wire [1:0] proof_core_request_gold;
    wire  protocol_error_gold;
    spk286_at_fdc_gold dut_gold(
        .clk(clk),
        .reset(reset),
        .request_valid(request_valid),
        .request_command_valid(request_command_valid),
        .request_write(request_write),
        .request_io(request_io),
        .request_address(request_address),
        .request_byte_enable(request_byte_enable),
        .request_data_out(request_data_out),
        .request_accept(request_accept_gold),
        .request_ready(request_ready_gold),
        .request_read_data(request_read_data_gold),
        .request_read_data_valid(request_read_data_valid_gold),
        .dma_transfer_valid(dma_transfer_valid),
        .dma_transfer_complete(dma_transfer_complete),
        .dma_terminal_count(dma_terminal_count),
        .dma_active_channel(dma_active_channel),
        .dma_transfer_data_in(dma_transfer_data_in),
        .dma_transfer_accept(dma_transfer_accept_gold),
        .dma_transfer_ready(dma_transfer_ready_gold),
        .dma_transfer_data_out(dma_transfer_data_out_gold),
        .dma_request(dma_request_gold),
        .irq6(irq6_gold),
        .mgmt_address(mgmt_address),
        .mgmt_writedata(mgmt_writedata),
        .mgmt_write(mgmt_write),
        .mgmt_read(mgmt_read),
        .mgmt_readdata(mgmt_readdata_gold),
        .floppy_write_protect(floppy_write_protect),
        .floppy_present(floppy_present_gold),
        .floppy_request(floppy_request_gold),
        .side_effect_count(side_effect_count_gold),
        .command_count(command_count_gold),
        .proof_core_dma_req(proof_core_dma_req_gold),
        .proof_core_dma_writedata(proof_core_dma_writedata_gold),
        .proof_core_irq(proof_core_irq_gold),
        .proof_core_io_readdata(proof_core_io_readdata_gold),
        .proof_core_fdd0_inserted(proof_core_fdd0_inserted_gold),
        .proof_core_mgmt_readdata(proof_core_mgmt_readdata_gold),
        .proof_core_request(proof_core_request_gold),
        .protocol_error(protocol_error_gold)
    );
    wire  request_accept_gate;
    wire  request_ready_gate;
    wire [15:0] request_read_data_gate;
    wire  request_read_data_valid_gate;
    wire  dma_transfer_accept_gate;
    wire  dma_transfer_ready_gate;
    wire [15:0] dma_transfer_data_out_gate;
    wire [7:0] dma_request_gate;
    wire  irq6_gate;
    wire [15:0] mgmt_readdata_gate;
    wire [1:0] floppy_present_gate;
    wire [1:0] floppy_request_gate;
    wire [15:0] side_effect_count_gate;
    wire [15:0] command_count_gate;
    wire  proof_core_dma_req_gate;
    wire [7:0] proof_core_dma_writedata_gate;
    wire  proof_core_irq_gate;
    wire [7:0] proof_core_io_readdata_gate;
    wire  proof_core_fdd0_inserted_gate;
    wire [15:0] proof_core_mgmt_readdata_gate;
    wire [1:0] proof_core_request_gate;
    wire  protocol_error_gate;
    spk286_at_fdc_gate #(.RETAINED_FDC_WRITE(1'b1)) dut_gate(
        .clk(clk),
        .reset(reset),
        .request_valid(request_valid),
        .request_command_valid(request_command_valid),
        .request_write(request_write),
        .request_io(request_io),
        .request_address(request_address),
        .request_byte_enable(request_byte_enable),
        .request_data_out(request_data_out),
        .retained_io_command(request_valid && request_command_valid && request_io),
        .retained_io_address(request_address),
        .retained_io_write(request_write),
        .retained_io_byte_enable(request_byte_enable),
        .retained_io_data_out(request_data_out),
        .request_accept(request_accept_gate),
        .request_ready(request_ready_gate),
        .request_read_data(request_read_data_gate),
        .request_read_data_valid(request_read_data_valid_gate),
        .dma_transfer_valid(dma_transfer_valid),
        .dma_transfer_complete(dma_transfer_complete),
        .dma_terminal_count(dma_terminal_count),
        .dma_active_channel(dma_active_channel),
        .dma_transfer_data_in(dma_transfer_data_in),
        .dma_transfer_accept(dma_transfer_accept_gate),
        .dma_transfer_ready(dma_transfer_ready_gate),
        .dma_transfer_data_out(dma_transfer_data_out_gate),
        .dma_request(dma_request_gate),
        .irq6(irq6_gate),
        .mgmt_address(mgmt_address),
        .mgmt_writedata(mgmt_writedata),
        .mgmt_write(mgmt_write),
        .mgmt_read(mgmt_read),
        .mgmt_readdata(mgmt_readdata_gate),
        .floppy_write_protect(floppy_write_protect),
        .floppy_present(floppy_present_gate),
        .floppy_request(floppy_request_gate),
        .side_effect_count(side_effect_count_gate),
        .command_count(command_count_gate),
        .proof_core_dma_req(proof_core_dma_req_gate),
        .proof_core_dma_writedata(proof_core_dma_writedata_gate),
        .proof_core_irq(proof_core_irq_gate),
        .proof_core_io_readdata(proof_core_io_readdata_gate),
        .proof_core_fdd0_inserted(proof_core_fdd0_inserted_gate),
        .proof_core_mgmt_readdata(proof_core_mgmt_readdata_gate),
        .proof_core_request(proof_core_request_gate),
        .protocol_error(protocol_error_gate)
    );
    wire all_equal = (request_accept_gold === request_accept_gate) &&
        (request_ready_gold === request_ready_gate) &&
        (request_read_data_gold === request_read_data_gate) &&
        (request_read_data_valid_gold === request_read_data_valid_gate) &&
        (dma_transfer_accept_gold === dma_transfer_accept_gate) &&
        (dma_transfer_ready_gold === dma_transfer_ready_gate) &&
        (dma_transfer_data_out_gold === dma_transfer_data_out_gate) &&
        (dma_request_gold === dma_request_gate) &&
        (irq6_gold === irq6_gate) &&
        (mgmt_readdata_gold === mgmt_readdata_gate) &&
        (floppy_present_gold === floppy_present_gate) &&
        (floppy_request_gold === floppy_request_gate) &&
        (side_effect_count_gold === side_effect_count_gate) &&
        (command_count_gold === command_count_gate) &&
        (proof_core_dma_req_gold === proof_core_dma_req_gate) &&
        (proof_core_dma_writedata_gold === proof_core_dma_writedata_gate) &&
        (proof_core_irq_gold === proof_core_irq_gate) &&
        (proof_core_io_readdata_gold === proof_core_io_readdata_gate) &&
        (proof_core_fdd0_inserted_gold === proof_core_fdd0_inserted_gate) &&
        (proof_core_mgmt_readdata_gold === proof_core_mgmt_readdata_gate) &&
        (proof_core_request_gold === proof_core_request_gate) &&
        (protocol_error_gold === protocol_error_gate);
    always @(negedge clk) if(tracing) begin
        cycle=cycle+1; if(!all_equal) $fatal(1,"MALFORMED_PAIR_MISMATCH cycle=%0d",cycle);
        $fwrite(trace_gold,"%0d,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h\n",cycle,request_accept_gold,request_ready_gold,request_read_data_gold,request_read_data_valid_gold,dma_transfer_accept_gold,dma_transfer_ready_gold,dma_transfer_data_out_gold,dma_request_gold,irq6_gold,mgmt_readdata_gold,floppy_present_gold,floppy_request_gold,side_effect_count_gold,command_count_gold,proof_core_dma_req_gold,proof_core_dma_writedata_gold,proof_core_irq_gold,proof_core_io_readdata_gold,proof_core_fdd0_inserted_gold,proof_core_mgmt_readdata_gold,proof_core_request_gold,protocol_error_gold);
        $fwrite(trace_gate,"%0d,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h,%h\n",cycle,request_accept_gate,request_ready_gate,request_read_data_gate,request_read_data_valid_gate,dma_transfer_accept_gate,dma_transfer_ready_gate,dma_transfer_data_out_gate,dma_request_gate,irq6_gate,mgmt_readdata_gate,floppy_present_gate,floppy_request_gate,side_effect_count_gate,command_count_gate,proof_core_dma_req_gate,proof_core_dma_writedata_gate,proof_core_irq_gate,proof_core_io_readdata_gate,proof_core_fdd0_inserted_gate,proof_core_mgmt_readdata_gate,proof_core_request_gate,protocol_error_gate);
    end

    task automatic illegal_lane(input [23:0] address_value,input [1:0] lane_value);
        @(negedge clk); #1;
        request_valid=1; request_command_valid=1; request_io=1; request_write=1;
        request_address=address_value; request_byte_enable=lane_value; request_data_out=16'h100C;
        #1;
        if(request_accept_gold !== 0 || request_accept_gate !== 0) $fatal(1,"Malformed request was accepted");
        @(posedge clk); #1;
        if(protocol_error_gold !== 1 || protocol_error_gate !== 1) $fatal(1,"Missing protocol error");
        if(side_effect_count_gold !== 0 || command_count_gold !== 0) $fatal(1,"Malformed side effect");
        @(negedge clk); #1;
        request_valid=0; request_command_valid=0; request_io=0; request_write=0;
        request_address=24'h000004; request_data_out=16'hCAFE;
        repeat(3) @(negedge clk);
        #1;
        if(request_ready_gold !== 0 || protocol_error_gold !== 1) $fatal(1,"Malformed completion/error not sticky");
        malformed_count=malformed_count+1;
    endtask
    initial begin
        if(!$value$plusargs("TRACE=%s",trace_path)) $fatal(1,"Missing TRACE");
        trace_gold=$fopen({trace_path,"-gold.csv"},"w");
        trace_gate=$fopen({trace_path,"-gate.csv"},"w");
        repeat(4) @(negedge clk); #1 reset=0;
        repeat(4) @(negedge clk); #1 tracing=1;
        illegal_lane(24'h0003F5,2'b01);
        illegal_lane(24'h0003F4,2'b10);
        illegal_lane(24'h0003F5,2'b11);
        illegal_lane(24'h0003F5,2'b00);
        @(negedge clk); #1 reset=1;
        repeat(3) @(negedge clk); #1;
        if(protocol_error_gold !== 0 || side_effect_count_gold !== 0 || command_count_gold !== 0)
            $fatal(1,"Reset failed to clear wrapper counters/error");
        reset=0;
        repeat(3) @(negedge clk); #1;
        request_valid=1; request_command_valid=1; request_io=1; request_write=1;
        request_address=24'h0003F2; request_byte_enable=2'b01; request_data_out=16'h000C;
        #1;
        if(request_accept_gold !== 1 || request_accept_gate !== 1) $fatal(1,"Valid DOR not accepted");
        @(posedge clk); #1;
        if(request_ready_gold !== 1 || request_ready_gate !== 1 || side_effect_count_gold !== 1 || command_count_gold !== 0)
            $fatal(1,"Valid DOR expected completion/counter failure");
        @(negedge clk); #1;
        request_valid=0; request_command_valid=0; request_io=0; request_write=0;
        valid_count=valid_count+1;
        repeat(5) @(negedge clk); #1;
        if(protocol_error_gold !== 0 || side_effect_count_gold !== 1 || command_count_gold !== 0)
            $fatal(1,"Valid DOR final counters/error failure");
        $display("RETAINED_FDC_MALFORMED_PASS malformed=%0d valid=%0d side_effects=%0d commands=%0d protocol_error=%0d",
            malformed_count,valid_count,side_effect_count_gold,command_count_gold,protocol_error_gold);
        $fclose(trace_gold);$fclose(trace_gate);$finish;
    end
    initial begin #100000; $fatal(1,"Malformed timeout"); end
endmodule
