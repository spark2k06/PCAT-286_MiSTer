`timescale 1ns/1ps
module spk286_at_pit_refresh_tb;
    logic clk=0, reset=1;
    always #10 clk=~clk;
    logic enable=1, timer_out=0, grant=0, accept=0, ready=0;
    wire request, valid, complete, error;
    wire [23:0] address;
    wire [15:0] count;
    integer checks=0;
    spk286_at_refresh unit_dut(
        .clk(clk), .reset(reset), .refresh_enable(enable), .timer_1_out(timer_out),
        .refresh_grant(grant), .refresh_accept(accept), .refresh_ready(ready),
        .refresh_request(request), .refresh_bus_valid(valid), .refresh_address(address),
        .refresh_complete(complete), .refresh_count(count), .protocol_error(error));
    task automatic step;
        @(posedge clk); #1;
    endtask
    task automatic check(input bit condition, input string label_text);
        checks++;
        if (!condition) $fatal(1,"PIT_REFRESH_CHECK %s",label_text);
    endtask
    task automatic pulse;
        @(negedge clk); timer_out=1; step();
        @(negedge clk); timer_out=0; step();
    endtask
    task automatic drain;
        @(negedge clk); grant=1; step();
        check(valid,"grant starts ownership");
        @(negedge clk); accept=1; ready=1; step();
        check(valid && !complete,"READY cannot precede accepted completion");
        @(negedge clk); accept=0; step();
        check(complete && !valid,"one accepted completion");
        @(negedge clk); ready=0; grant=0; step();
        check(!complete,"completion is a pulse");
    endtask

    wire counter_clock;
    logic pit_request=0;
    logic [23:0] pit_address=0;
    logic [1:0] pit_lanes=0;
    logic [15:0] pit_data=0;
    wire pit_accept, pit_ready, pit_error;
    wire [2:0] counter_out;
    wire real_request, real_valid, real_complete, real_error;
    wire [15:0] real_count;
    spk286_at_pit_clock clock_dut(.clk(clk),.reset(reset),.counter_clock(counter_clock));
    spk286_at_pit pit_dut(
        .clk(clk),.reset(reset),.counter_clock(counter_clock),.counter_2_gate(1'b0),
        .request_valid(pit_request),.request_command_valid(pit_request),.request_write(1'b1),
        .request_io(1'b1),.request_address(pit_address),.request_byte_enable(pit_lanes),
        .request_data_out(pit_data),.request_accept(pit_accept),.request_ready(pit_ready),
        .request_read_data(),.request_read_data_valid(),.irq0(),.counter_out(counter_out),
        .protocol_error(pit_error));
    spk286_at_refresh real_dut(
        .clk(clk),.reset(reset),.refresh_enable(1'b1),.timer_1_out(counter_out[1]),
        .refresh_grant(real_request),.refresh_accept(real_valid),.refresh_ready(real_valid),
        .refresh_request(real_request),.refresh_bus_valid(real_valid),.refresh_address(),
        .refresh_complete(real_complete),.refresh_count(real_count),.protocol_error(real_error));
    task automatic pit_write(input logic [15:0] port_number,input logic [7:0] value);
        @(negedge clk);
        pit_request=1; pit_address={8'd0,port_number};
        pit_lanes=port_number[0] ? 2'b10 : 2'b01;
        pit_data=port_number[0] ? {value,8'd0} : {8'd0,value};
        #1;
        while(!pit_accept) step();
        step();
        @(negedge clk); pit_request=0;
        while(!pit_ready) step();
        step();
    endtask
    integer cycles=0, edges=0, last_edge=0, periods=0;
    logic last_out=0, measure_period=0;
    always @(posedge clk) if(reset) begin
        cycles=0; edges=0; last_edge=0; periods=0; last_out=0;
    end else begin
        cycles++;
        if(counter_out[1] && !last_out) begin
            edges++;
            if(measure_period && last_edge!=0) begin
                if(cycles-last_edge<752 || cycles-last_edge>756)
                    $fatal(1,"PIT_REFRESH_PERIOD clocks=%0d",cycles-last_edge);
                periods++;
            end
            last_edge=cycles;
        end
        last_out=counter_out[1];
        if(pit_error || real_error || error) $fatal(1,"PIT_REFRESH_PROTOCOL_ERROR");
    end
    integer before_edges, measured_periods;
    initial begin
        repeat(5) step(); @(negedge clk); reset=0;
        repeat(100) step(); check(!request && count==0,"no free running 32-clock requester");
        pulse(); check(request && !valid,"request retained without grant");
        repeat(12) step(); check(request && !valid,"LOCK/arbitration delay retains request");
        drain(); check(count==1 && address==1,"first row completion");
        @(negedge clk); timer_out=1;
        repeat(20) step(); drain(); check(count==2 && !request,"high level produces one event");
        @(negedge clk); timer_out=0; step(); pulse();
        @(negedge clk); grant=1; step(); check(valid,"second active transaction");
        pulse(); pulse(); // Multiple events during active ownership coalesce.
        @(negedge clk); accept=1; ready=1; step();
        @(negedge clk); accept=0; step(); check(complete && request,"pending survives active completion");
        @(negedge clk); ready=0; grant=0; step(); drain();
        check(count==4 && !request,"one coalesced pending transaction");
        pulse(); @(negedge clk); enable=0; step();
        check(!request,"disable discards ungranted request");
        @(negedge clk); enable=1; step(); pulse();
        @(negedge clk); grant=1; step();
        @(negedge clk); enable=0; accept=1; ready=0; step();
        check(valid,"disable preserves accepted transaction");
        @(negedge clk); accept=0; ready=1; step();
        check(complete && count==5,"disabled active transaction drains");
        @(negedge clk); ready=0; grant=0; step();
        before_edges=edges; repeat(1000) step();
        check(edges==before_edges,"unprogrammed PIT has no periodic refresh");
        pit_write(16'h43,8'h74); // Channel 1, low/high, mode 2.
        pit_write(16'h41,8'd18); pit_write(16'h41,8'd0);
        repeat(1600) step(); // Exclude initialization/loading transition.
        last_edge=0; measure_period=1;
        repeat(8000) step(); measure_period=0;
        repeat(10) step();
        $display("PIT_OBSERVATION cycles=%0d edges=%0d periods=%0d count=%0d out=%b",cycles,edges,periods,real_count,counter_out);
        check(periods>=9,"real PIT periods measured");
        measured_periods=periods;
        check({16'd0,real_count}==edges,"one completion per actual OUT1 rising edge");
        @(negedge clk); reset=1; step();
        check(count==0 && real_count==0 && !request && !real_request,"global reset clears state");
        $display("PIT_REFRESH_PASS checks=%0d periods=%0d (18 / 1193182 Hz)",checks,measured_periods);
        $finish;
    end
    initial begin #1000000; $fatal(1,"PIT_REFRESH_WATCHDOG"); end
endmodule
