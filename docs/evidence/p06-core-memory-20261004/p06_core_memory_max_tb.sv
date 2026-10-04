`timescale 1ns/1ps
// Full real CPU, private aligned RM A1 only. External state ports seed cases.
// Sparse memory comes from the caller's CS/DS/moffs/value, never CPU caches.
module p06_core_memory_tb #(parameter bit TIMED=1'b0);
    `include "spk286_signals.svh"
    logic p06_code_board_ready=1, p06_data_board_ready=1;
`ifdef P06_ORIGINAL
    spk286 dut (.*);
`else
    spk286 #(.P06_REGISTER_PILOT(TIMED),.P06_FETCH_PILOT(TIMED),
        .P06_IU_PILOT(TIMED),.P06_MEMORY_PILOT(TIMED)) dut (.*);
`endif
    wire timed_boundary,code_issue,code_complete,data_complete,memory_pending;
    wire timing_scope,timing_permit,timing_active;
    wire policy_read_wait,diagnostic_read_wait;
    wire [7:0] timing_scheduled;
    wire [15:0] cursor_ip;
    // This is the original executor's retained functional phase, independently
    // of the newly inserted pending export and all temporal permit wiring.
    wire functional_pending=dut.micro_active && !dut.event_active && dut.opcode_q==8'ha1 &&
        dut.micro_executor.operation==spk286_microcode_pkg::MC_MOVE && dut.micro_executor.temporary_valid_q[0];
`ifndef P06_ORIGINAL
    generate if (TIMED) begin : timed_view
        assign timed_boundary=dut.p06_register.cpu_boundary;
        assign code_issue=dut.fetch.p06_bus_issue;
        assign code_complete=dut.fetch.p06_bus_complete;
        assign data_complete=dut.biu.p06_complete;
        assign memory_pending=dut.p06_read_result_pending;
        assign timing_scope=dut.p06_register.scope_error || dut.p06_biu_scope_error;
        assign timing_permit=dut.p06_register.permit;
        assign timing_active=dut.p06_register.active;
        assign timing_scheduled=dut.p06_register.scheduled;
        assign policy_read_wait=dut.p06_read_wait_event;
        assign diagnostic_read_wait=dut.biu.p06_data.external_wait;
        assign cursor_ip=dut.p06_cursor_ip;
    end else begin : max_view
        assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0;
        assign memory_pending=0; assign timing_scope=0; assign timing_permit=0; assign timing_active=0;
        assign timing_scheduled=0;
        assign policy_read_wait=0; assign diagnostic_read_wait=0;
        assign cursor_ip=debug_ip;
    end endgenerate
`else
    assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0;
    assign memory_pending=0; assign timing_scope=0; assign timing_permit=0; assign timing_active=0;
    assign timing_scheduled=0;
    assign policy_read_wait=0; assign diagnostic_read_wait=0;
    assign cursor_ip=debug_ip;
`endif
    localparam integer NONE=0,CODE=1,DATA=2;
    integer vector_fd,trace_fd,summary_fd,scan,id,start_ip,mode=0;
    logic [15:0] cs_selector,ds_selector,moffs,value,initial_flags,effective_moffs;
    logic [127:0] initial_gpr,expected_gpr,committed_gpr;
    logic [127:0] a1_gpr,rr_gpr;
    logic [15:0] committed_flags,rr_flags,a1_ip,rr_result;
    integer rr_started=0,rr_retired=0,rr_start_cpu=0,rr_retire_cpu=0;
    bit mixed=0;
    logic [23:0] expected_code_base,expected_data_address;
    integer code_waits,data_waits,code_latency,data_latency;
    integer age=0,cpu=0,cycle=0,cases=0,checks=0,started=0,retired=0,consumes=0;
    integer start_cpu=0,retire_cpu=0,start_edge=0,retire_edge=0,data_request_cpu=0;
    integer owner=NONE,code_start_cpu=0,code_start_edge=0,data_start_cpu=0,data_start_edge=0;
    integer code_capture_edge=0,data_capture_edge=0,code_ext=0,data_ext=0,code_misses=0,data_misses=0;
    integer code_accepts=0,data_accepts=0,code_captures=0,data_captures=0,code_responses=0,data_responses=0;
    integer physical_start_edge=0,off_boundary=0;
    integer paused_waits=0,exact_capture_cpu=0;
    integer observer_queue_count=0;
    logic [15:0] observer_cursor,code_expected_ip,code_expected_data;
    logic [1:0] code_expected_count;
    logic [23:0] code_expected_address;
    logic code_expected_bhe;
    bit code_pending=0,data_pending=0,code_captured=0,data_captured=0;
    bit code_finished=0,data_finished=0,code_aborted=0,data_aborted=0;
    bit physical_pending=0,watch=0,warming=0,warm=1,aborted=0,action_done=0;
    bit observer_bus_scope=0;
    logic [23:0] held_address;
    logic held_bhe;
    logic [3:0] held_status;
    string vectors_path,trace_path,summary_path;

    function automatic [7:0] memory_byte(input logic [23:0] a);
        begin
            memory_byte=8'hf4;
            if (mixed) begin
                if (a==expected_code_base+{8'd0,a1_ip}) memory_byte=8'ha1;
                else if (a==expected_code_base+{8'd0,a1_ip+16'd1}) memory_byte=effective_moffs[7:0];
                else if (a==expected_code_base+{8'd0,a1_ip+16'd2}) memory_byte=effective_moffs[15:8];
                else if (a==expected_code_base+{8'd0,16'(start_ip+(mode==21 ? 3 : 0))}) memory_byte=8'h01;
                else if (a==expected_code_base+{8'd0,16'(start_ip+(mode==21 ? 4 : 1))}) memory_byte=8'hc3;
            end else begin
            if (a==expected_code_base+{8'd0,16'(start_ip)})
                memory_byte=mode==13 ? 8'hf3 : mode==14 ? 8'ha3 : 8'ha1;
            else if (a==expected_code_base+{8'd0,16'(start_ip+1)}) memory_byte=effective_moffs[7:0];
            else if (a==expected_code_base+{8'd0,16'(start_ip+2)}) memory_byte=effective_moffs[15:8];
            end
            if (a==expected_data_address) memory_byte=value[7:0];
            if (a==expected_data_address+24'd1) memory_byte=value[15:8];
        end
    endfunction
    function automatic [15:0] add_flags(input logic [15:0] a,b,old_flags);
        logic [16:0] result;
        logic [15:0] flags;
        begin
            result={1'b0,a}+{1'b0,b}; flags=old_flags & ~16'h08d5;
            flags[0]=result[16]; flags[2]=~^result[7:0];
            flags[4]=(a[4]^b[4]^result[4]); flags[6]=result[15:0]==0;
            flags[7]=result[15]; flags[11]=(!(a[15]^b[15]) && (a[15]^result[15]));
            add_flags=flags;
        end
    endfunction
    function automatic bit boundary_oracle;
        boundary_oracle=!reset && (3*(age+1)/25 != 3*age/25);
    endfunction
    function automatic integer cpu_edge(input integer n);
        cpu_edge=(25*n+2)/3;
    endfunction

    task automatic tick;
        bit boundary,instruction_start,gpr_commit,flags_commit,consume,c_start,d_start;
        bit c_capture,d_capture,c_publish,d_publish,c_complete_expected,d_complete_expected;
        bit c_valid_expected,d_valid_expected,c_abort_now,d_abort_now,released;
        bit commit_expected;
        bit a1_write,rr_write;
        bit data_start_expected;
        bit policy_wait_this,diagnostic_wait_this,pending_this;
        integer next_cpu,this_edge,old_owner,earliest,latency_now,code_fill_count;
        logic [15:0] word_on_bus;
        begin
            #8; boundary=boundary_oracle(); this_edge=age+1; next_cpu=cpu+(TIMED ? int'(boundary) : int'(!reset));
            if (TIMED && timed_boundary !== boundary) $fatal(1,"memory rational clock oracle failed");
            if (!watch || reset) begin ready=bus_valid; p06_code_board_ready=1; p06_data_board_ready=1; end
            else if (TIMED) begin
                p06_code_board_ready=next_cpu>=code_start_cpu+2+code_waits;
                p06_data_board_ready=next_cpu>=data_start_cpu+2+data_waits;
                ready=(owner==CODE && code_pending && !code_captured) ?
                    (code_latency==-1 ? boundary && p06_code_board_ready : this_edge-code_start_edge-1>=code_latency) :
                    (owner==DATA && data_pending && !data_captured) ?
                    (mode==16 ? boundary && next_cpu==start_cpu+5+data_waits :
                        data_latency==-1 ? boundary && p06_data_board_ready : this_edge-data_start_edge-1>=data_latency) : 1'b0;
            end else begin
                if (bus_valid && !physical_pending) physical_start_edge=this_edge;
                latency_now=bus_status==4'h5 ? data_latency : code_latency;
                // -1 is an exact-Tc stimulus in TIMED; MAX has no Tc and uses
                // an explicit 16-fabric-edge backend latency instead.
                ready=bus_valid && this_edge-physical_start_edge>=(latency_now==-1 ? 16 : latency_now);
            end
            word_on_bus={memory_byte({address[23:1],1'b1}),memory_byte({address[23:1],1'b0})};
            data_in=ready ? word_on_bus : 16'hbad0;
            #1;
            instruction_start=dut.opcode_start;
            gpr_commit=execute_enable && dut.effective_gpr_write_en && dut.commit_allowed;
            flags_commit=execute_enable && dut.effective_flags_write_en && dut.commit_allowed;
            policy_wait_this=policy_read_wait; diagnostic_wait_this=diagnostic_read_wait; pending_this=functional_pending;
            a1_write=gpr_commit && dut.effective_gpr_write_index==0;
            rr_write=gpr_commit && dut.effective_gpr_write_index==3;
            consume=dut.queue_consume_valid && dut.queue_consume_ready;
            c_start=code_issue; d_start=dut.memory_request && dut.memory_request_ready;
            c_capture=bus_valid && ready && bus_status==4'hd;
            d_capture=bus_valid && ready && bus_status==4'h5;
            c_publish=dut.fetch_response_valid && dut.fetch_response_ready;
            d_publish=dut.memory_response_valid && dut.memory_response_ready;
            old_owner=owner;
            code_fill_count=int'(code_expected_count);
            if (watch && !reset) begin
                checks=checks+1; cycle=cycle+1;
                if (TIMED && debug_prefetch_count!==4'(observer_queue_count))
                    $fatal(1,"A1 independent prefetch occupancy oracle failed");
                if (TIMED) begin
                    // The sticky global bus guard is reconstructed from its
                    // unqualified request, not read back from the DUT flag.
                    observer_bus_scope=observer_bus_scope || hold_request || bus_lock || dut.ack_request ||
                        (dut.memory_request && (dut.memory_write || dut.io_transfer ||
                            (!dut.memory_byte && expected_data_address[0])));
                    c_abort_now=code_aborted || dut.stream_restart || observer_bus_scope;
                    d_abort_now=data_aborted || dut.semantic_cancel || observer_bus_scope;
                    code_aborted=c_abort_now; data_aborted=d_abort_now;
                    c_complete_expected=owner==CODE && code_pending && !code_finished && !c_abort_now &&
                        boundary && next_cpu>=code_start_cpu+2+code_waits && (code_captured || c_capture);
                    d_complete_expected=owner==DATA && data_pending && !data_finished && !d_abort_now &&
                        boundary && next_cpu>=data_start_cpu+2+data_waits && (data_captured || d_capture);
                    c_valid_expected=code_pending && !c_abort_now && (code_finished || c_complete_expected);
                    d_valid_expected=data_pending && !d_abort_now && (data_finished || d_complete_expected);
                    if (code_complete !== c_complete_expected || dut.fetch_response_valid !== c_valid_expected)
                        $fatal(1,"full memory CODE publication oracle failed id=%0d edge=%0d",id,this_edge);
                    if (data_complete !== d_complete_expected || dut.memory_response_valid !== d_valid_expected)
                        $fatal(1,"full memory DATA publication oracle failed id=%0d edge=%0d",id,this_edge);
                    if (bus_valid !== ((owner==CODE && code_pending && !code_captured) ||
                        (owner==DATA && data_pending && !data_captured)))
                        $fatal(1,"full memory logical owner oracle failed: physical presence");
                    if (bus_valid && (bus_status!=(owner==CODE ? 4'hd : 4'h5)))
                        $fatal(1,"full memory logical owner oracle failed: physical owner");
                    if (owner==CODE && boundary && !c_abort_now && next_cpu>=code_start_cpu+2) begin
                        if (!p06_code_board_ready) code_ext=code_ext+1;
                        else if (!(code_captured || c_capture)) code_misses=code_misses+1;
                    end
                    if (owner==DATA && boundary && !d_abort_now && next_cpu>=data_start_cpu+2) begin
                        if (!p06_data_board_ready) data_ext=data_ext+1;
                        else if (!(data_captured || d_capture)) data_misses=data_misses+1;
                    end
                    if (mode==15 && !execute_enable && policy_read_wait) paused_waits=paused_waits+1;
                    if (mode==17 && hold_request && boundary && next_cpu==data_start_cpu+2 &&
                        (policy_read_wait!==1'b1 || diagnostic_read_wait!==1'b0 || data_complete || d_publish))
                        $fatal(1,"A1 new-scope TC wait context oracle failed");
                    if (mode==18 && dut.semantic_cancel && boundary && next_cpu==data_start_cpu+2 &&
                        (policy_read_wait || diagnostic_read_wait || data_complete || d_publish))
                        $fatal(1,"A1 canceled TC wait context oracle failed");
                end
                if (bus_valid) begin
                    if (bus_write || data_oe || hlda || bus_lock || (bus_status!=4'hd && bus_status!=4'h5))
                        $fatal(1,"unqualified physical access in A1 pilot");
                    if (physical_pending && (address!==held_address || bus_bhe_n!==held_bhe || bus_status!==held_status))
                        $fatal(1,"full memory READ metadata changed before READY");
                    physical_pending=1; held_address=address; held_bhe=bus_bhe_n; held_status=bus_status;
                    if (bus_status==4'h5 && (address!==expected_data_address || bus_bhe_n!==1'b0))
                        $fatal(1,"A1 independent DS/moffs address/lane oracle failed");
                    if (TIMED && bus_status==4'hd && (address!==code_expected_address || bus_bhe_n!==code_expected_bhe))
                        $fatal(1,"A1 independent CODE cursor/address oracle failed");
                end
                if (c_capture) begin
                    code_captures=code_captures+1; code_captured=1; code_capture_edge=this_edge; physical_pending=0;
                    if (TIMED && !c_abort_now) observer_cursor=code_expected_ip+{14'd0,code_expected_count};
                end
                if (d_capture) begin
                    data_captures=data_captures+1; data_captured=1; data_capture_edge=this_edge; physical_pending=0;
                    if (mode==16) begin
                        if (next_cpu!=start_cpu+5+data_waits || !boundary || gpr_commit)
                            $fatal(1,"A1 deadline coincidence fixture/oracle failed");
                        exact_capture_cpu=next_cpu;
                    end
                end
                if ((c_capture || d_capture) && !boundary) off_boundary=off_boundary+1;
                if (TIMED) begin
                    if (code_complete) begin
                        earliest=code_start_cpu+2+code_waits;
                        while (cpu_edge(earliest)<code_capture_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"CODE first eligible Tc oracle failed");
                        code_finished=1;
                    end
                    if (data_complete) begin
                        earliest=data_start_cpu+2+data_waits;
                        while (cpu_edge(earliest)<data_capture_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"DATA first eligible Tc oracle failed");
                        data_finished=1;
                    end
                    if (dut.fetch_response_valid && (dut.fetch_response_data!==code_expected_data ||
                        dut.fetch_response_ip!==code_expected_ip || dut.fetch_response_count!==code_expected_count))
                        $fatal(1,"A1 retained CODE payload/metadata oracle failed");
                    if (dut.memory_response_valid && dut.memory_read_data!==value)
                        $fatal(1,"A1 retained DATA payload oracle failed");
                    released=(owner==CODE && (code_complete || (c_abort_now && code_captured))) ||
                        (owner==DATA && (data_complete || (d_abort_now && data_captured)));
                    data_start_expected=dut.memory_request && boundary && !dut.semantic_cancel &&
                        !observer_bus_scope && !data_pending && (owner==NONE || released);
                    if (d_start !== data_start_expected)
                        $fatal(1,"A1 first eligible DATA admission oracle failed");
                    if ((c_start || d_start) && (!boundary || (owner!=NONE && !released)) || (c_start && d_start))
                        $fatal(1,"full memory logical owner oracle failed: admission before Tc/drain");
                    if (released) owner=NONE;
                    if (c_publish) begin code_pending=0; code_finished=0; code_responses=code_responses+1; end
                    if (d_publish) begin data_pending=0; data_finished=0; data_responses=data_responses+1; end
                    if (c_start) begin
                        owner=CODE; code_pending=1; code_captured=0; code_finished=0; code_aborted=0;
                        code_start_cpu=next_cpu; code_start_edge=this_edge; code_accepts=code_accepts+1;
                        code_expected_ip=observer_cursor; code_expected_address=expected_code_base+{8'd0,observer_cursor};
                        code_expected_count=(code_expected_address[0] || observer_cursor==16'hffff) ? 2'd1 : 2'd2;
                        code_expected_bhe=code_expected_count==1 && !code_expected_address[0];
                        code_expected_data=code_expected_count==1 ? {8'd0,memory_byte(code_expected_address)} :
                            {memory_byte(code_expected_address+24'd1),memory_byte(code_expected_address)};
                    end
                end
                if (TIMED) begin
                    if (c_publish && execute_enable) observer_queue_count=observer_queue_count+code_fill_count;
                    if (consume) observer_queue_count=observer_queue_count-1;
                    if (redirect && ip_write_en) observer_queue_count=0;
                    if (observer_queue_count<0 || observer_queue_count>6 ||
                        observer_queue_count+(code_pending && !code_aborted ? int'(code_expected_count) : 0)>6)
                        $fatal(1,"A1 six-byte queue/reservation oracle failed");
                end
                if (d_start) begin
                    if (dut.memory_write || dut.memory_byte || dut.io_transfer || dut.memory_address!==expected_data_address)
                        $fatal(1,"A1 caller-derived DATA request oracle failed");
                    data_accepts=data_accepts+1; data_request_cpu=next_cpu;
                    if (TIMED) begin owner=DATA; data_pending=1; data_captured=0; data_finished=0; data_aborted=0;
                        data_start_cpu=next_cpu; data_start_edge=this_edge; end
                end
                if (instruction_start) begin
                    if (mixed && dut.queue_consume_data==8'h01) begin
                        if (rr_started!=0 || !boundary || (mode==21 && retired!=1))
                            $fatal(1,"A1/RR serialized start oracle failed");
                        rr_started=rr_started+1; rr_start_cpu=next_cpu;
                    end else begin
                        if (started!=0 || (TIMED && (!boundary || cursor_ip!=a1_ip)))
                            $fatal(1,"A1 instruction start oracle failed");
                        if (mode==20 && warm && !rr_write)
                            $fatal(1,"RR to A1 same-edge relaunch oracle failed");
                        started=started+1; start_cpu=next_cpu; start_edge=this_edge;
                    end
                end
                if (consume && !warming) begin
                    consumes=consumes+1;
                    if (consumes>(mixed ? 5 : 3) || dut.queue_consume_data!==memory_byte(expected_code_base+{8'd0,16'(start_ip+consumes-1)}))
                        $fatal(1,"A1 independent consumed instruction byte oracle failed");
                end
                if (flags_commit && (!mixed || !rr_write))
                    $fatal(1,"A1/RR independent FLAGS oracle failed");
                // A retained real TMP0 is functional readiness. The first
                // permitted commit boundary follows an independent 5+READ
                // wait deadline; neither permit nor the DUT budget is used.
                if (TIMED && memory_pending !== functional_pending)
                    $fatal(1,"A1 original TMP0 pending oracle failed");
                if (functional_pending && dut.micro_executor.tmp0_q!==value)
                    $fatal(1,"A1 original TMP0 payload oracle failed");
                commit_expected=TIMED && functional_pending && boundary && started==1 && retired==0 &&
                    next_cpu-start_cpu>=5+data_ext && execute_enable && !control_error &&
                    !dut.semantic_cancel && !observer_bus_scope && !aborted && !timing_scope;
                if (TIMED && a1_write !== commit_expected)
                    $fatal(1,"A1 first eligible commit oracle failed id=%0d cpu=%0d start=%0d waits=%0d pending=%0d",id,next_cpu,start_cpu,data_ext,memory_pending);
                if (a1_write) begin
                    if (dut.effective_gpr_write_index!=0 || dut.effective_gpr_write_data!==value || data_captures!=1 ||
                        (TIMED && (!boundary || !memory_pending || next_cpu-start_cpu<5+data_ext)))
                        $fatal(1,"A1 qualified commit oracle failed id=%0d cpu=%0d start=%0d waits=%0d",id,next_cpu,start_cpu,data_ext);
                    if (mode==16 && next_cpu!=exact_capture_cpu+1)
                        $fatal(1,"A1 captured TMP0 did not commit at next boundary");
                    committed_gpr=a1_gpr;
                end else if (rr_write && mixed) begin
                    if (rr_started!=1 || !flags_commit || dut.effective_gpr_write_data!==rr_result ||
                        !boundary || next_cpu-rr_start_cpu<2)
                        $fatal(1,"A1/RR independent RR commit oracle failed");
                    committed_gpr=rr_gpr; committed_flags=rr_flags;
                end else if (gpr_commit) begin
                    $fatal(1,"A1/RR unexpected GPR commit");
                end
            end
            #1; clk=1; #10; clk=0;
            if (reset) begin age=0; cpu=0; physical_pending=0; owner=NONE;
                code_pending=0; data_pending=0; code_captured=0; data_captured=0; observer_queue_count=0; end
            else begin age=this_edge; cpu=next_cpu; end
            if (watch && !reset) begin
                if (redirect && ip_write_en) observer_cursor=ip_write_data;
                if (TIMED && debug_prefetch_count!==4'(observer_queue_count))
                    $fatal(1,"A1 independent post-edge queue occupancy oracle failed");
                if (code_aborted && code_captured) code_pending=0;
                if (data_aborted && data_captured) data_pending=0;
                if (instruction_retired) begin
                    if (mixed && rr_write) begin
                        if (rr_retired!=0 || rr_started!=1 || debug_gpr!==rr_gpr || debug_flags!==rr_flags ||
                            debug_ip!=16'(start_ip+(mode==21 ? 5 : 2)))
                            $fatal(1,"A1/RR independent RR retirement oracle failed");
                        rr_retired=rr_retired+1; rr_retire_cpu=cpu;
                    end else begin
                        if (retired!=0 || started!=1 || (TIMED && !a1_write) || debug_gpr!==a1_gpr ||
                            debug_flags!==committed_flags || debug_ip!=(a1_ip+16'd3) || (TIMED && !boundary))
                            $fatal(1,"A1 retirement/architectural oracle failed id=%0d",id);
                        retired=retired+1; retire_edge=this_edge; retire_cpu=cpu;
                    end
                end
                if (!aborted && (debug_gpr!==committed_gpr || debug_flags!==committed_flags))
                    $fatal(1,"A1 state changed outside observed commit");
                if (TIMED && !aborted && started==1 && retired==0 && debug_ip!=a1_ip)
                    $fatal(1,"A1 architectural IP advanced before retirement");
                if (TIMED && started==1 && retired==0 && !aborted && !observer_bus_scope && !timing_scope &&
                    timing_active && timing_scheduled!==8'(5+data_ext))
                    $fatal(1,"A1 READ wait budget oracle failed");
                if (microcode_fault || unsupported_opcode || shutdown ||
                    (control_error && !warming && mode!=2)) $fatal(1,"unexpected full CPU A1 fault");
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%04h,%04h,%04h,%032h,%04h,%0d,%0d,%0d,%0d,%0d,%0d\n",
                    id,cycle,boundary,cpu,instruction_start,c_start,d_start,c_capture,d_capture,code_complete,data_complete,
                    gpr_commit,instruction_retired,old_owner,bus_valid,address,bus_status,ready,debug_ip,cursor_ip,
                    debug_instruction_ip,debug_gpr,debug_flags,debug_prefetch_count,timing_scope,
                    policy_wait_this,diagnostic_wait_this,pending_this,timing_scheduled);
            end
        end
    endtask

    task automatic setup;
        begin
            watch=0; execute_enable=0; reset=1; intr=0; nmi=0; hold_request=0;
            redirect=0; ip_write_en=0; segment_load_en=0; gpr_write_en=0; flags_write_en=0;
            fetch_request=0; fetch_ready=1; tick(); reset=0;
            // Drain the original automatic reset fetch through its external
            // response port, before loading the requested CS/IP program.
            repeat (40) tick();
            if (bus_valid) $fatal(1,"reset fetch did not drain before seeding");
            for (integer r=0;r<8;r=r+1) begin gpr_write_en=1; gpr_write_index=3'(r);
                gpr_write_data=initial_gpr[r*16+:16]; tick(); end
            gpr_write_en=0; flags_write_en=1; flags_write_data=initial_flags; flags_write_mask=16'hffff;
            tick(); flags_write_en=0;
            segment_load_en=1; segment_load_index=3; segment_load_selector=ds_selector; tick();
            segment_load_index=1; segment_load_selector=cs_selector; redirect=1; ip_write_en=1; ip_write_data=16'(start_ip); tick();
            segment_load_en=0; redirect=0; ip_write_en=0; fetch_ready=0;
            if (debug_gpr!==initial_gpr || debug_flags!==initial_flags || debug_ip!=16'(start_ip) ||
                debug_segment_bases[3*24+:24]!=={4'd0,ds_selector,4'd0}) $fatal(1,"A1 external state seed mismatch");
            cycle=0; started=0; retired=0; consumes=0; start_cpu=0; retire_cpu=0; start_edge=0; retire_edge=0;
            code_accepts=0; data_accepts=0; code_captures=0; data_captures=0; code_responses=0; data_responses=0;
            code_ext=0; data_ext=0; code_misses=0; data_misses=0; off_boundary=0;
            code_start_cpu=0; data_start_cpu=0; code_start_edge=0; data_start_edge=0;
            owner=NONE; code_pending=0; data_pending=0; code_captured=0; data_captured=0;
            code_finished=0; data_finished=0; code_aborted=0; data_aborted=0;
            physical_pending=0; observer_cursor=16'(start_ip); committed_gpr=initial_gpr;
            committed_flags=initial_flags; rr_started=0; rr_retired=0; rr_start_cpu=0; rr_retire_cpu=0;
            observer_bus_scope=0;
            observer_queue_count=0;
            paused_waits=0; exact_capture_cpu=0;
            action_done=0; aborted=0; watch=1; execute_enable=1;
            if (warm && TIMED) begin
                warming=1; redirect=1;
                while ((debug_prefetch_count<5 || owner!=NONE || code_pending) && cycle<600) tick();
                if (started!=0 || debug_prefetch_count<5) $fatal(1,"A1 warm prefill failed");
                warming=0; redirect=0;
            end
        end
    endtask

    task automatic lifecycle;
        begin
            action_done=1;
            if (mode==1 || mode==7 || mode==2 || mode==15) begin
                if (mode==2) redirect=1; else execute_enable=0;
                repeat (33) begin tick();
                    if (instruction_retired || debug_gpr!==initial_gpr || debug_flags!==initial_flags)
                        $fatal(1,"A1 pause/controller error leaked architectural commit"); end
                execute_enable=1; redirect=0;
            end else if (mode==3 || mode==8 || mode==18) begin
                execute_enable=0; redirect=1; ip_write_en=1; ip_write_data=16'h0500; aborted=1;
                tick(); redirect=0; ip_write_en=0;
                if (instruction_retired || memory_pending || timing_active || debug_gpr!==initial_gpr ||
                    debug_flags!==initial_flags || debug_ip!=16'h0500) $fatal(1,"A1 redirect failed cancellation");
                repeat (120) tick();
            end else if (mode==4 || mode==9) begin
                execute_enable=0; reset=1; aborted=1; tick(); reset=0;
                if (instruction_retired || memory_pending || timing_active) $fatal(1,"A1 reset retained old instruction");
                watch=0; repeat (33) tick();
            end else if (mode==5 || mode==10 || mode==17) hold_request=1;
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s",vectors_path) || !$value$plusargs("trace=%s",trace_path) ||
            !$value$plusargs("summary=%s",summary_path)) $fatal(1,"required memory probe paths missing");
        if ($value$plusargs("mode=%d",mode)) begin end
        if (!(mode>=0 && mode<=10 || mode>=12 && mode<=18 || mode==20 || mode==21))
            $fatal(1,"undefined A1 probe mode");
        warm=!$test$plusargs("cold");
        vector_fd=$fopen(vectors_path,"r"); trace_fd=$fopen(trace_path,"w"); summary_fd=$fopen(summary_path,"w");
        if (vector_fd==0 || trace_fd==0 || summary_fd==0) $fatal(1,"memory probe files unavailable");
        $fwrite(trace_fd,"id,edge,boundary,cpu_clock,start,code_start,data_start,code_capture,data_capture,code_complete,data_complete,gpr_write,retired,owner,bus,address,status,ready,ip,cursor,start_ip,gpr,flags,queue,scope,policy_read_wait,diagnostic_read_wait,tmp0_pending,scheduled\n");
        $fwrite(summary_fd,"id,timed,warm,mode,start_cpu,retire_cpu,elapsed,code_accepts,data_accepts,code_captures,data_captures,code_external,data_external,code_misses,data_misses,off_boundary,gpr,flags,ip,retired,scope,rr_started,rr_retired,rr_start_cpu,rr_retire_cpu\n");
        while (!$feof(vector_fd)) begin
            scan=$fscanf(vector_fd,"%d %h %h %h %h %h %h %h %d %d %d %d\n",
                id,start_ip,cs_selector,ds_selector,moffs,value,initial_gpr,initial_flags,code_waits,data_waits,code_latency,data_latency);
            if (scan!=12 || start_ip<0 || start_ip>65532 || moffs[0] || initial_flags[8] ||
                code_waits<0 || code_waits>2 || data_waits<0 || data_waits>2 || code_latency< -1 || data_latency< -1)
                $fatal(1,"invalid aligned A1 vector schema");
            if ((mode==15 || mode==17 || mode==18) && data_waits==0)
                $fatal(1,"directed TC wait fixture requires board waits");
            effective_moffs=mode==12 ? moffs|16'd1 : moffs;
            mixed=mode==20 || mode==21;
            if (mixed && (!TIMED || start_ip>65530)) $fatal(1,"invalid mixed A1/RR fixture");
            a1_ip=16'(start_ip+(mode==20 ? 2 : 0));
            expected_code_base={4'd0,cs_selector,4'd0}; expected_data_address={4'd0,ds_selector,4'd0}+{8'd0,effective_moffs};
            if (expected_data_address>=expected_code_base+{8'd0,16'(start_ip)} &&
                expected_data_address<=expected_code_base+{8'd0,16'(start_ip+3)}) $fatal(1,"A1 code/data fixture overlap");
            a1_gpr=initial_gpr; a1_gpr[15:0]=value; expected_gpr=a1_gpr;
            rr_result=initial_gpr[63:48]+(mode==21 ? value : initial_gpr[15:0]);
            rr_gpr=initial_gpr; rr_gpr[63:48]=rr_result;
            rr_flags=add_flags(initial_gpr[63:48],mode==21 ? value : initial_gpr[15:0],initial_flags);
            if (mixed) begin
                expected_gpr[63:48]=rr_result;
                if (mode==20) a1_gpr=expected_gpr; else rr_gpr=expected_gpr;
            end
            setup();
            while ((retired==0 || (mixed && rr_retired==0)) && cycle<2000 && !aborted && !timing_scope) begin
                if (!action_done && ((mode>=1 && mode<=5 && functional_pending) ||
                    (mode>=7 && mode<=10 && data_accepts==1) || (mode==15 && data_accepts==1) ||
                    ((mode==17 || mode==18) && data_pending && boundary_oracle() && cpu+1==data_start_cpu+2))) lifecycle();
                if (!aborted && !timing_scope) tick();
            end
            if (aborted) begin if (!action_done || retired!=0) $fatal(1,"A1 cancellation action not reached"); end
            else if (mode==5 || mode==10 || mode==12 || mode==13 || mode==14 || mode==17) begin
                if (!TIMED || !timing_scope || retired!=0 || debug_gpr!==initial_gpr || debug_flags!==initial_flags)
                    $fatal(1,"A1 unqualified case did not stop before commit");
                repeat (160) tick();
                if (retired!=0 || hlda || bus_write || data_oe) $fatal(1,"A1 scope leaked work after stop");
            end else begin
                if (retired!=1 || started!=1 || consumes!=(mixed ? 5 : 3) || data_accepts!=1 || data_captures!=1 ||
                    debug_gpr!==expected_gpr || debug_flags!==(mixed ? rr_flags : initial_flags) ||
                    debug_ip!=16'(start_ip+(mixed ? 5 : 3)) || (mixed && (rr_started!=1 || rr_retired!=1)))
                    $fatal(1,"A1 independent architectural result mismatch id=%0d",id);
                if (TIMED && retire_cpu-start_cpu<5+data_ext) $fatal(1,"A1 retired before minimum plus read waits");
                if (mode==15 && paused_waits!=data_waits) $fatal(1,"A1 paused EU did not retain READ wait budget");
                if (mode==6) begin repeat (80) tick(); if (!timing_scope || started!=1) $fatal(1,"A1 suffix scope was not explicit"); end
            end
            $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h,%04h,%0d,%0d,%0d,%0d,%0d,%0d\n",
                id,TIMED,warm,mode,start_cpu,retire_cpu,retire_cpu-start_cpu,code_accepts,data_accepts,code_captures,data_captures,
                code_ext,data_ext,code_misses,data_misses,off_boundary,debug_gpr,debug_flags,debug_ip,retired,timing_scope,
                rr_started,rr_retired,rr_start_cpu,rr_retire_cpu);
            execute_enable=0; watch=0; warming=0; cases=cases+1;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_CORE_MEMORY_PASS cases=%0d checks=%0d timed=%0d warm=%0d mode=%0d",cases,checks,TIMED,warm,mode); $finish;
    end
endmodule
