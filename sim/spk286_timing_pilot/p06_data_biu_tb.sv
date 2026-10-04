`timescale 1ns/1ps
// Private M6a: real operand service and real BIU, with an independent timing
// oracle. This does not model CODE ownership or whole-instruction execution.
module p06_data_biu_tb;
    logic clk = 0, reset = 1, cancel_data = 0, ready = 0;
    logic hold_request = 0, lock_request = 0, ack_request = 0;
    logic ack_response_ready = 1, code_valid = 0, code_bhe_n = 0;
    logic [23:0] code_address = 24'h007000;
    logic [15:0] data_in = 16'hbad0;
    wire hlda, ack_request_ready, ack_response_valid, bus_lock, code_ready;
    wire [7:0] ack_vector;
    wire [23:0] address;
    wire [15:0] data_out, data_read_data;
    wire data_oe, bus_valid, bus_write, bus_bhe_n;
    wire [3:0] bus_status;
    wire p06_cpu_boundary, phase_enable, phase_two, p06_scope_error;
    logic p06_board_ready = 1;
    p06_clock clock_policy (.clk(clk), .reset(reset), .phase_enable(phase_enable),
        .phase_two(phase_two), .cpu_enable(p06_cpu_boundary));

    logic use_operand = 1, op_valid = 0, op_write = 0, op_byte = 1;
    logic [23:0] op_address = 24'h001000;
    wire op_done, op_unlimited_done, op_blocked, op_gpr_write, op_gpr_byte;
    wire [2:0] op_gpr_index;
    wire [15:0] op_read_data, op_gpr_data;
    wire operand_request, operand_write, operand_byte, operand_response_ready, operand_wait;
    wire [23:0] operand_address;
    wire [15:0] operand_write_data;
    spk286_operand operand (.clk(clk), .reset(reset), .cancel(cancel_data),
        .request_valid(op_valid), .request_write(op_write), .request_check(1'b0),
        .request_byte(op_byte), .select_rm(1'b1), .write_data(16'hfedc),
        .done(op_done), .unlimited_memory_done(op_unlimited_done), .read_data(op_read_data),
        .register_state(128'd0), .reg_index(3'd0), .rm_index(3'd0),
        .register_direct(1'b0), .physical_address(op_address), .offset(16'h1000),
        .segment_limit(16'hffff), .segment_expand_down(1'b0), .parallel_within_limit(1'b1),
        .blocked(op_blocked), .gpr_write_en(op_gpr_write), .gpr_write_byte(op_gpr_byte),
        .gpr_write_index(op_gpr_index), .gpr_write_data(op_gpr_data),
        .memory_request(operand_request), .memory_request_ready(data_request_ready),
        .memory_write(operand_write), .memory_byte(operand_byte), .memory_address(operand_address),
        .memory_write_data(operand_write_data), .memory_response_valid(data_response_valid),
        .memory_response_ready(operand_response_ready), .timing_wait(operand_wait),
        .memory_read_data(data_read_data));

    logic direct_request = 0, direct_write = 0, direct_byte = 1, direct_io = 0;
    logic [23:0] direct_address = 24'h001000;
    logic [15:0] direct_write_data = 16'h1234;
    logic consumer_enabled = 1, hold_ready = 0, poison_request = 0;
    wire data_request = use_operand ? operand_request : direct_request;
    wire data_write = use_operand ? operand_write : direct_write;
    wire data_byte = use_operand ? operand_byte : direct_byte;
    wire data_io = use_operand ? 1'b0 : direct_io;
    wire [23:0] data_address = use_operand ? operand_address : direct_address;
    wire [15:0] data_write_data = use_operand ? operand_write_data : direct_write_data;
    wire data_response_ready = use_operand ? operand_response_ready : consumer_enabled;
    wire data_request_ready, data_response_valid;
    spk286_biu #(.P06_DATA_TIMING(1'b1)) dut (.*);

    integer fabric_age = 0, cpu_clocks = 0, case_id = 0, cases = 0, checks = 0;
    integer waits = 0, latency = 0, lane = 0, accept_target = 1;
    integer request_cpu = 0, request_edge = 0, physical_age = 0, capture_edge = 0;
    integer accepts = 0, reads = 0, captures = 0, completes = 0, responses = 0;
    integer external_waits = 0, misses = 0, off_boundary = 0, all_off_boundary = 0;
    integer first_complete_cpu = 0, first_complete_edge = 0;
    integer trace_fd, summary_fd, mode = 0;
    integer guard_kind = -1, lifecycle_stage = -1;
    bit physical_pending = 0, logical_pending = 0, result_captured = 0;
    bit logical_completed = 0, logical_canceled = 0, scope_seen = 0;
    logic [23:0] held_address;
    logic held_bhe;
    logic [23:0] expected_bus_address;
    logic expected_bus_bhe;
    logic [15:0] expected_result;
    string trace_path, summary_path, vectors_path;

    function automatic [7:0] pattern(input logic [23:0] a);
        pattern = a[7:0] ^ a[15:8] ^ 8'h5a;
    endfunction
    function automatic bit boundary_oracle;
        boundary_oracle = !reset && (3*(fabric_age+1)/25 != 3*fabric_age/25);
    endfunction
    function automatic integer cpu_edge(input integer clock_number);
        cpu_edge = (25*clock_number+2)/3;
    endfunction
    function automatic bit unsupported_oracle;
        unsupported_oracle = code_valid || ack_request || hold_request || lock_request ||
            (data_request && (data_write || data_io || (!data_byte && data_address[0])));
    endfunction

    task automatic tick;
        bit boundary, acceptance, capture, publication, complete_now;
        bit expected_complete, expected_valid, expected_external, expected_miss, illegal;
        integer next_cpu, this_edge, earliest_cpu;
        logic [15:0] bus_word;
        begin
            #8;
            boundary = boundary_oracle();
            next_cpu = cpu_clocks + int'(boundary);
            this_edge = fabric_age + 1;
            if (p06_cpu_boundary !== boundary) $fatal(1,"scheduler differs from independent rational oracle");
            p06_board_ready = next_cpu >= request_cpu + 2 + waits;
            ready = hold_ready || (bus_valid && (latency == -1 ?
                (boundary && next_cpu >= request_cpu+2+waits) : physical_age >= latency));
            bus_word = {pattern({address[23:1],1'b1}),pattern({address[23:1],1'b0})};
            data_in = ready ? bus_word : 16'hbad0;
            #1;
            acceptance = data_request && data_request_ready;
            capture = bus_valid && ready;
            complete_now = dut.p06_complete;
            publication = data_response_valid && data_response_ready;
            illegal = unsupported_oracle();
            if (!reset) begin
                checks = checks + 1;
                if (cancel_data || illegal || scope_seen) begin
                    logical_canceled=1; logical_pending=0; logical_completed=0;
                end
                expected_external = logical_pending && !logical_completed && !logical_canceled &&
                    boundary && next_cpu >= request_cpu+2 && next_cpu < request_cpu+2+waits;
                expected_miss = logical_pending && !logical_completed && !logical_canceled &&
                    boundary && next_cpu >= request_cpu+2+waits && !(result_captured || capture);
                expected_complete = logical_pending && !logical_completed && !logical_canceled &&
                    boundary && next_cpu >= request_cpu+2+waits && (result_captured || capture);
                expected_valid = !logical_canceled && (logical_completed || expected_complete);
                if (dut.p06_data.external_wait !== expected_external || dut.p06_data.deadline_miss !== expected_miss)
                    $fatal(1,"wait classification case=%0d cpu=%0d ext=%b/%b miss=%b/%b",
                        case_id,next_cpu,dut.p06_data.external_wait,expected_external,dut.p06_data.deadline_miss,expected_miss);
                if (complete_now !== expected_complete || data_response_valid !== expected_valid)
                    $fatal(1,"independent logical publication oracle failed case=%0d edge=%0d complete=%b/%b valid=%b/%b",
                        case_id,this_edge,complete_now,expected_complete,data_response_valid,expected_valid);
                if (physical_pending && bus_valid && (address !== held_address || bus_bhe_n !== held_bhe))
                    $fatal(1,"physical metadata changed before READY");
                if (logical_canceled && dut.data_active_q && data_request_ready)
                    $fatal(1,"new READ admitted before canceled physical drain");
                if (bus_valid) begin
                    if (address !== expected_bus_address || bus_bhe_n !== expected_bus_bhe)
                        $fatal(1,"physical address/lane differs from independently accepted request");
                    if (!physical_pending) begin
                        reads = reads + 1; physical_pending = 1;
                        held_address = address; held_bhe = bus_bhe_n;
                    end
                    if (bus_write || data_oe || bus_status != 4'h5 || hlda || bus_lock)
                        $fatal(1,"scope guard leaked an unsupported physical operation");
                end
                if (ack_request_ready || ack_response_valid || code_ready || op_gpr_write || op_blocked)
                    $fatal(1,"unrelated service affected private memory READ");
                if (capture) begin
                    if (!physical_pending) $fatal(1,"capture without physical READ");
                    captures = captures + 1; physical_pending = 0; result_captured = 1;
                    capture_edge = this_edge;
                    if (!boundary) begin off_boundary = off_boundary+1; all_off_boundary = all_off_boundary+1; end
                end
                if (expected_external) external_waits = external_waits + 1;
                if (expected_miss) misses = misses + 1;
                if (complete_now) begin
                    earliest_cpu = request_cpu + 2 + waits;
                    while (cpu_edge(earliest_cpu) < capture_edge) earliest_cpu = earliest_cpu+1;
                    if (next_cpu != earliest_cpu || this_edge != cpu_edge(earliest_cpu))
                        $fatal(1,"independent earliest Tc oracle failed");
                    completes = completes + 1; logical_completed = 1;
                    if (completes == 1) begin first_complete_cpu=next_cpu; first_complete_edge=this_edge; end
                end
                if (data_response_valid && data_read_data !== expected_result)
                    $fatal(1,"poison/lane/retention mismatch case=%0d data=%h expected=%h",case_id,data_read_data,expected_result);
                // unlimited_memory_done requires its caller to establish
                // request_valid; unlike DONE, it is not an admission gate.
                if (use_operand && (op_done !== publication || (op_valid && op_unlimited_done !== publication) ||
                    (op_done && op_read_data !== expected_result)))
                    $fatal(1,"operand completion bypassed real BIU response");
                if (publication) begin
                    responses = responses + 1; logical_pending = 0; logical_completed = 0;
                end
                if (acceptance) begin
                    if (!boundary || logical_pending || illegal || cancel_data)
                        $fatal(1,"invalid READ admission");
                    accepts = accepts + 1; request_cpu=next_cpu; request_edge=this_edge;
                    physical_age=0; capture_edge=0; logical_pending=1; result_captured=0;
                    logical_completed=0; logical_canceled=0;
                    expected_result = data_byte ? {8'd0,pattern(data_address)} :
                        {pattern(data_address+24'd1),pattern(data_address)};
                    expected_bus_address=data_address;
                    expected_bus_bhe=data_byte ? !data_address[0] : 1'b0;
                end else if (bus_valid && !capture) physical_age=physical_age+1;
                if (illegal) scope_seen=1;
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%04h,%0d,%0d,%0d\n",
                    case_id,this_edge,next_cpu,boundary,acceptance,capture,complete_now,publication,
                    ready,cancel_data,illegal,p06_scope_error,dut.p06_data.state_q,address,bus_bhe_n,
                    data_read_data,external_waits,misses,operand_wait);
            end
            #1; clk=1; #10; clk=0;
            if (reset) begin
                fabric_age=0; cpu_clocks=0; physical_pending=0; logical_pending=0;
                logical_completed=0; logical_canceled=0; result_captured=0; scope_seen=0;
            end else begin
                fabric_age=this_edge; cpu_clocks=next_cpu;
                if (scope_seen && !p06_scope_error) $fatal(1,"scope violation was not sticky");
                if (publication && use_operand) op_valid=0;
                if (!use_operand && responses >= accept_target) direct_request=0;
                if (acceptance && poison_request) begin
                    direct_request=0; direct_address=24'hdeadc1; direct_byte=!direct_byte;
                    direct_write=1; direct_io=1; direct_write_data=16'hbad1;
                end
            end
        end
    endtask

    task automatic setup(input integer ws, delay, lane_kind, direct_mode);
        begin
            reset=1; cancel_data=0; hold_request=0; lock_request=0; ack_request=0; code_valid=0;
            op_valid=0; direct_request=0; direct_write=0; direct_io=0; op_write=0;
            use_operand=direct_mode == 0; consumer_enabled=1; hold_ready=0; poison_request=0; tick(); reset=0;
            accepts=0; reads=0; captures=0; completes=0; responses=0; external_waits=0; misses=0;
            first_complete_cpu=0; first_complete_edge=0; request_cpu=0; request_edge=0;
            guard_kind=-1; lifecycle_stage=-1;
            physical_age=0; capture_edge=0; off_boundary=0; accept_target=1;
            waits=ws; latency=delay; lane=lane_kind;
            op_byte=lane_kind != 2; direct_byte=lane_kind != 2;
            op_address=24'h001000+(lane_kind == 1 ? 24'd1 : 24'd0);
            direct_address=op_address;
            if (use_operand) op_valid=1; else direct_request=1;
        end
    endtask
    task automatic receipt(input integer kind);
        begin
            $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",
                case_id,kind,lane,waits,latency,accepts,reads,captures,completes,responses,
                first_complete_cpu,first_complete_edge,external_waits,misses,off_boundary,p06_scope_error,
                guard_kind,lifecycle_stage);
            cases=cases+1; case_id=case_id+1;
        end
    endtask
    task automatic drain(input integer count);
        begin
            while (responses < count && fabric_age < 1500) tick();
            if (responses != count) $fatal(1,"response timeout");
            repeat (31) tick();
            if (accepts != count || reads != count || captures != count || completes != count || responses != count || bus_valid || data_response_valid)
                $fatal(1,"held request lost or replayed transaction");
        end
    endtask
    // The stage is selected before the affected rising edge. Cancel/reset on a
    // READY or Tc edge must suppress that logical result, without losing drain.
    task automatic await_stage(input integer stage);
        begin
            lifecycle_stage=stage;
            if (stage == 0) begin end
            else if (stage == 1 || stage == 2) begin
                while (accepts == 0 && fabric_age < 200) tick();
            end else if (stage == 3) begin
                while (captures == 0 && fabric_age < 200) tick();
            end else if (stage == 4) begin
                while (!(boundary_oracle() && cpu_clocks+1 >= request_cpu+2+waits) && fabric_age < 200) tick();
            end else begin
                while (completes == 0 && fabric_age < 200) tick();
            end
            if (fabric_age >= 200) $fatal(1,"lifecycle stage timeout");
        end
    endtask
    task automatic guard(input integer kind);
        begin
            guard_kind=kind;
            case (kind)
                0: code_valid=1;
                1: begin direct_byte=0; direct_address=24'h001001; direct_request=1; end
                2: begin direct_write=1; direct_request=1; end
                3: begin direct_io=1; direct_request=1; end
                4: ack_request=1;
                5: hold_request=1;
                6: lock_request=1;
                default: $fatal(1,"unknown guard kind");
            endcase
        end
    endtask

    initial begin
        if (!$value$plusargs("trace=%s",trace_path) || !$value$plusargs("summary=%s",summary_path))
            $fatal(1,"required trace/summary paths missing");
        if ($value$plusargs("vectors=%s",vectors_path)) begin end
        if ($value$plusargs("mode=%d",mode)) begin end
        trace_fd=$fopen(trace_path,"w"); summary_fd=$fopen(summary_path,"w");
        $fwrite(trace_fd,"case,fabric_edge,cpu_clock,boundary,accept,capture,complete,response,ready,cancel,illegal,scope_error,state,address,bhe_n,data,external_waits,misses,operand_wait\n");
        $fwrite(summary_fd,"case,kind,lane,waits,latency,accepts,reads,captures,completes,responses,first_complete_cpu,first_complete_edge,external_waits,misses,off_boundary,scope_error,guard_kind,lifecycle_stage\n");
        if (mode == 0) begin
            for (integer ws=0;ws<3;ws=ws+1)
                for (integer d=0;d<48;d=d+1)
                    for (integer l=0;l<3;l=l+1) begin
                        setup(ws,d<46 ? d : d==46 ? -1 : 80,l,0);
                        drain(1);
                        if (external_waits != ws || (d==47 && misses==0) || (d==46 && misses!=0))
                            $fatal(1,"matrix dependency classification failed");
                        receipt(0);
                    end
        end else if (mode == 1) begin
            for (integer stage=1;stage<=4;stage=stage+1) begin
                if (stage!=2) begin
                    setup(1,stage==1 ? 80 : stage==4 ? -1 : 0,0,0);
                    await_stage(stage); op_valid=0;
                    while (completes==0 && fabric_age<500) tick();
                    repeat (31) tick();
                    if (!data_response_valid || responses!=0 || op_done || accepts!=1 || captures!=1)
                        $fatal(1,"paused operand lost retained result or completed without caller");
                    op_valid=1; drain(1); receipt(9);
                end
            end
            for (integer l=0;l<3;l=l+1) begin
                setup(1,0,l,1); consumer_enabled=0;
                while (completes==0 && fabric_age<300) tick();
                repeat (31) tick();
                if (!data_response_valid || accepts!=1 || captures!=1 || responses!=0)
                    $fatal(1,"backpressure failed retained slot");
                consumer_enabled=1; drain(1); receipt(1);
                setup(0,-1,l,1); accept_target=2; drain(2); receipt(2);
                setup(2,0,l,1); hold_ready=1; accept_target=2; drain(2); receipt(6);
                setup(1,45,l,1); poison_request=1; drain(1); receipt(7);
            end
            for (integer action=0;action<2;action=action+1)
                for (integer stage=0;stage<6;stage=stage+1) begin
                    setup(1,stage==1 ? 80 : stage==4 ? -1 : 0,0,1);
                    consumer_enabled=0; await_stage(stage); direct_request=0;
                    if (action==0) cancel_data=1; else reset=1;
                    tick(); cancel_data=0; reset=0;
                    if (action==0) begin
                        while (bus_valid && fabric_age<500) tick();
                        repeat (40) tick();
                        if (responses!=0 || captures!=(stage==0 ? 0 : 1) || bus_valid || data_response_valid)
                            $fatal(1,"cancellation leaked response or abandoned READ");
                    end else begin
                        repeat (40) tick();
                        if (bus_valid || data_response_valid || dut.raw_data_response_valid || dut.p06_data.state_q!=0)
                            $fatal(1,"reset retained logical/physical state");
                    end
                    receipt(action==0 ? 3 : 4);
                    if (action==0) begin
                        // Recover without reset. The old physical read has
                        // drained, and no canceled packet may be reused.
                        accepts=0; reads=0; captures=0; completes=0; responses=0;
                        external_waits=0; misses=0; off_boundary=0;
                        first_complete_cpu=0; first_complete_edge=0;
                        direct_address=24'h002001; direct_byte=1; direct_request=1;
                        latency=0; consumer_enabled=1; drain(1); receipt(8);
                    end
                end
        end else if (mode == 2) begin
            for (integer stage=0;stage<6;stage=stage+1)
                for (integer g=0;g<7;g=g+1) begin
                    setup(0,stage==1 ? 80 : stage==4 ? -1 : 0,0,1);
                    consumer_enabled=0; await_stage(stage);
                    guard(g); tick();
                    while (bus_valid && fabric_age<500) tick();
                    repeat (50) tick();
                    if (!p06_scope_error || accepts!=(stage==0 ? 0 : 1) || reads!=(stage==0 ? 0 : 1) ||
                        captures!=(stage==0 ? 0 : 1) || completes!=(stage==5 ? 1 : 0) || responses!=0 ||
                        bus_valid || data_response_valid || data_request_ready)
                        $fatal(1,"guard failed admission/physical drain separation kind=%0d stage=%0d",g,stage);
                    receipt(5);
                end
        end else $fatal(1,"unknown test mode");
        $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_DATA_BIU_PASS mode=%0d cases=%0d checks=%0d off_boundary_captures=%0d",mode,cases,checks,all_off_boundary);
        $finish;
    end
endmodule
