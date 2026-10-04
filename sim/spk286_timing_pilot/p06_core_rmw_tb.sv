`timescale 1ns/1ps
// Private full-CPU 81 /36 XOR: READ, retained ALU result, then WRITE and FLAGS.
// Accepted writes drain after cancel; reset aborts only future transfers.
// Logical phases below are independent of the DUT's phase/second registers.
module p06_core_rmw_tb #(parameter bit TIMED=1'b1);
    `include "spk286_signals.svh"
    logic p06_code_board_ready=1, p06_data_board_ready=1;
`ifdef P06_ORIGINAL
    spk286 dut (.*);
`else
    spk286 #(.P06_REGISTER_PILOT(TIMED),.P06_FETCH_PILOT(TIMED),
        .P06_IU_PILOT(TIMED),.P06_MEMORY_PILOT(TIMED),.P06_ODD_READ_PILOT(TIMED),.P06_WRITE_PILOT(TIMED),.P06_RMW_PILOT(TIMED)) dut (.*);
`endif
    wire timed_boundary,code_issue,code_complete,data_complete,first_complete,memory_pending;
    wire timing_scope,timing_active,policy_read_wait,diagnostic_read_wait,alignment_event,form_event;
    wire [7:0] timing_scheduled;
    wire [15:0] cursor_ip;
    wire functional_pending=dut.micro_active && !dut.event_active && dut.opcode_q==8'h81 &&
        dut.micro_word==spk286_microcode_pkg::MC_COMMIT_FLAGS &&
        dut.micro_executor.flags_valid_q && dut.micro_executor.result_disposed_q;
`ifndef P06_ORIGINAL
    generate if (TIMED) begin : timed_view
        assign timed_boundary=dut.p06_register.cpu_boundary;
        assign code_issue=dut.fetch.p06_bus_issue; assign code_complete=dut.fetch.p06_bus_complete;
        assign data_complete=dut.biu.p06_complete; assign first_complete=dut.biu.p06_first_complete;
        assign memory_pending=dut.p06_rmw_result_pending;
        assign timing_scope=dut.p06_register.scope_error || dut.p06_biu_scope_error;
        assign timing_active=dut.p06_register.active; assign timing_scheduled=dut.p06_register.scheduled;
        assign policy_read_wait=dut.p06_read_wait_event; assign diagnostic_read_wait=dut.biu.p06_external_wait;
        assign alignment_event=dut.p06_alignment_event; assign cursor_ip=dut.p06_cursor_ip;
        assign form_event=dut.p06_register.duration_policy.p06_form_increment;
    end else begin : maximum_view
        assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0; assign first_complete=0;
        assign memory_pending=0; assign timing_scope=0; assign timing_active=0; assign timing_scheduled=0;
        assign policy_read_wait=0; assign diagnostic_read_wait=0; assign alignment_event=0; assign cursor_ip=debug_ip; assign form_event=0;
    end endgenerate
`else
    assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0; assign first_complete=0;
    assign memory_pending=0; assign timing_scope=0; assign timing_active=0; assign timing_scheduled=0;
    assign policy_read_wait=0; assign diagnostic_read_wait=0; assign alignment_event=0; assign cursor_ip=debug_ip; assign form_event=0;
`endif
    localparam integer NONE=0,CODE=1,DATA=2;
    integer vector_fd,trace_fd,summary_fd,scan,id,start_ip,mode=0;
    logic [15:0] cs_selector,ds_selector,moffs,initial_mem,immediate_value,initial_flags,expected_flags,committed_flags;
    logic [15:0] memory_actual,memory_expected;
    logic [7:0] guard_before_actual,guard_after_actual;
    logic [15:0] write_value;
    logic [127:0] initial_gpr,expected_gpr,committed_gpr;
    logic [23:0] code_base,data_address;
    integer code_waits,read_wait1,read_wait2,write_wait1,write_wait2,code_latency;
    integer read_latency1,read_latency2,write_latency1,write_latency2;
    integer wait1=0,wait2=0,latency1=0,latency2=0,data_phase=0,read_captures=0,write_captures=0;
    integer observed_wait[0:3],observed_miss[0:3];
    bit form_qualified=0;
    integer age=0,cpu=0,cycle=0,cases=0,checks=0,started=0,retired=0,consumes=0;
    integer start_cpu=0,retire_cpu=0,owner=NONE,observer_queue_count=0;
    integer code_start_cpu=0,code_start_edge=0,data_start_cpu=0,data_start_edge=0;
    integer code_capture_edge=0,capture1_edge=0,capture2_edge=0,first_tc_cpu=0,first_tc_edge=0,second_start_edge=0;
    integer code_ext=0,ext1=0,ext2=0,code_misses=0,miss1=0,miss2=0,alignment_count=0;
    integer code_accepts=0,data_accepts=0,code_captures=0,data_captures=0,code_responses=0,data_responses=0;
    integer first_completions=0,data_completions=0,off_boundary=0,physical_start_edge=0,exact_capture_cpu=0;
    logic [15:0] observer_cursor,code_expected_ip,code_expected_data;
    logic [1:0] code_expected_count;
    logic [23:0] code_expected_address,held_address;
    logic code_expected_bhe,held_bhe;
    logic [3:0] held_status;
    bit odd=0,code_pending=0,data_pending=0,code_captured=0,captured1=0,captured2=0;
    bit code_finished=0,data_finished=0,first_tc_seen=0,second_started=0,code_aborted=0,data_aborted=0;
    bit physical_pending=0,watch=0,warming=0,warm=1,aborted=0,action_done=0,observer_bus_scope=0;
    string vectors_path,trace_path,summary_path;

    function automatic [7:0] memory_byte(input logic [23:0] a);
        begin
            memory_byte=8'hf4;
            if (a==code_base+{8'd0,16'(start_ip)}) memory_byte=8'h81;
            else if (a==code_base+{8'd0,16'(start_ip+1)}) memory_byte=8'h36;
            else if (a==code_base+{8'd0,16'(start_ip+2)}) memory_byte=moffs[7:0];
            else if (a==code_base+{8'd0,16'(start_ip+3)}) memory_byte=moffs[15:8];
            else if (a==code_base+{8'd0,16'(start_ip+4)}) memory_byte=immediate_value[7:0];
            else if (a==code_base+{8'd0,16'(start_ip+5)}) memory_byte=immediate_value[15:8];
            if (a==data_address) memory_byte=memory_actual[7:0];
            if (a==data_address+24'd1) memory_byte=memory_actual[15:8];
            if (a==data_address-24'd1) memory_byte=guard_before_actual;
            if (a==data_address+24'd2) memory_byte=guard_after_actual;
        end
    endfunction
    function automatic bit boundary_oracle;
        boundary_oracle=!reset && (3*(age+1)/25 != 3*age/25);
    endfunction
    function automatic integer cpu_edge(input integer n);
        cpu_edge=(25*n+2)/3;
    endfunction

    // The external model applies received pins. The separate expected model
    // derives enabled bytes and values solely from the accepted caller word.
    task automatic store_lane(input logic [23:0] a,input logic [7:0] b);
        begin
            if (a==data_address) memory_actual[7:0]=b;
            else if (a==data_address+24'd1) memory_actual[15:8]=b;
            else if (a==data_address-24'd1) guard_before_actual=b;
            else if (a==data_address+24'd2) guard_after_actual=b;
            else $fatal(1,"RMW physical write escaped the caller footprint");
        end
    endtask

    task automatic tick;
        bit boundary,instruction_start,gpr_commit,flags_commit,consume,c_start,d_start;
        bit c_capture,d_capture,first_capture,final_capture,c_publish,d_publish;
        bit c_complete_expected,d_complete_expected,first_complete_expected,c_valid_expected,d_valid_expected;
        bit c_abort_now,d_abort_now,old_scope,old_data_abort,physical_data_expected,released,data_start_expected;
        bit alignment_expected,read_wait_expected,retire_expected,policy_wait_this,diagnostic_wait_this,align_this,pending_this;
        bit first_tc_this,final_tc_this,bus_this,write_this,bhe_this,ready_this,execute_this,cancel_this,form_expected,form_this;
        logic [23:0] address_this;
        logic [15:0] dataout_this,datain_this,memory_before_this;
        logic [3:0] status_this;
        integer next_cpu,this_edge,old_owner,old_phase,earliest,code_fill_count,latency_now,beat_start,beat_latency,wait_index;
        logic [15:0] word_on_bus;
        logic [23:0] expected_bus_address;
        logic expected_bhe;
        begin
            #8; boundary=boundary_oracle(); this_edge=age+1; next_cpu=cpu+(TIMED ? int'(boundary) : int'(!reset));
            if (TIMED && timed_boundary !== boundary) $fatal(1,"RMW rational clock oracle failed");
            old_scope=observer_bus_scope; old_data_abort=data_aborted;
            c_abort_now=code_aborted || dut.stream_restart || observer_bus_scope || hold_request;
            d_abort_now=data_aborted || dut.semantic_cancel || observer_bus_scope || hold_request;
            if (watch && TIMED && odd && data_pending && captured1 && !second_started && d_abort_now) begin
                second_started=1; second_start_edge=this_edge;
            end
            if (!watch || reset) begin ready=bus_valid; p06_code_board_ready=1; p06_data_board_ready=1; end
            else if (TIMED) begin
                p06_code_board_ready=next_cpu>=code_start_cpu+2+code_waits;
                p06_data_board_ready=!(aborted || observer_bus_scope || hold_request) &&
                    (first_tc_seen ? next_cpu>=first_tc_cpu+2+wait2 : next_cpu>=data_start_cpu+2+wait1);
                beat_start=odd && captured1 ? second_start_edge : data_start_edge;
                beat_latency=odd && captured1 ? latency2 : latency1;
                ready=(owner==CODE && code_pending && !code_captured) ?
                    (code_latency==-1 ? boundary && p06_code_board_ready : this_edge-code_start_edge-1>=code_latency) :
                    (owner==DATA && data_pending && !captured2) ?
                    (mode==29 && data_phase==2 && (!odd || captured1) && !d_abort_now ?
                        boundary && next_cpu==(odd ? first_tc_cpu+2+wait2 : data_start_cpu+2+wait1) :
                        beat_latency==-1 && !d_abort_now ? boundary && p06_data_board_ready :
                        this_edge-beat_start-1>=(beat_latency==-1 ? 0 : beat_latency)) : 1'b0;
            end else begin
                if (bus_valid && !physical_pending) physical_start_edge=this_edge;
                latency_now=bus_status==4'h5 || bus_status==4'h6 ? (odd && captured1 ? latency2 : latency1) : code_latency;
                ready=bus_valid && this_edge-physical_start_edge>=(latency_now==-1 ? 16 : latency_now);
            end
            word_on_bus={memory_byte({address[23:1],1'b1}),memory_byte({address[23:1],1'b0})};
            // Only selected READ lanes are meaningful; all other payloads are poisoned.
            if (ready && bus_status==4'hd) data_in=word_on_bus;
            else if (ready && bus_status==4'h5) data_in=odd ?
                (captured1 ? {8'hba,initial_mem[15:8]} : {initial_mem[7:0],8'hd0}) : initial_mem;
            else data_in=16'hbad0;
            #1;
            instruction_start=dut.opcode_start;
            gpr_commit=execute_enable && dut.effective_gpr_write_en && dut.commit_allowed;
            flags_commit=execute_enable && dut.effective_flags_write_en && dut.commit_allowed;
            consume=dut.queue_consume_valid && dut.queue_consume_ready;
            c_start=code_issue; d_start=dut.memory_request && dut.memory_request_ready;
            c_capture=bus_valid && ready && bus_status==4'hd; d_capture=bus_valid && ready && (bus_status==4'h5 || bus_status==4'h6);
            first_capture=d_capture && odd && !captured1;
            final_capture=d_capture && (!odd || captured1);
            c_publish=dut.fetch_response_valid && dut.fetch_response_ready;
            d_publish=dut.memory_response_valid && dut.memory_response_ready;
            policy_wait_this=policy_read_wait; diagnostic_wait_this=diagnostic_read_wait;
            align_this=alignment_event; pending_this=functional_pending; old_owner=owner; old_phase=data_phase; code_fill_count=int'(code_expected_count);
            first_tc_this=first_complete; final_tc_this=data_complete;
            bus_this=bus_valid; write_this=bus_write; bhe_this=bus_bhe_n; ready_this=ready;
            address_this=address; dataout_this=data_out; datain_this=data_in; status_this=bus_status; memory_before_this=memory_actual;
            execute_this=execute_enable; cancel_this=dut.semantic_cancel; form_this=form_event;
            retire_expected=0; form_expected=TIMED && !aborted && !observer_bus_scope && !hold_request &&
                boundary && started==1 && consumes>=2 && !form_qualified;
            if (watch && !reset) begin
                checks=checks+1; cycle=cycle+1;
                if (TIMED) begin
                    if (!dut.semantic_cancel && !observer_bus_scope && !hold_request && form_event !== form_expected)
                        $fatal(1,"RMW independent late form event oracle failed");
                    if (debug_prefetch_count!==4'(observer_queue_count)) $fatal(1,"RMW independent queue occupancy oracle failed");
                    observer_bus_scope=observer_bus_scope || hold_request || bus_lock || dut.ack_request ||
                        (dut.memory_request && (dut.io_transfer || dut.memory_byte));
                    c_abort_now=code_aborted || dut.stream_restart || observer_bus_scope;
                    d_abort_now=data_aborted || dut.semantic_cancel || observer_bus_scope;
                    physical_data_expected=owner==DATA && data_pending && !captured2 &&
                        (!odd || !captured1 || first_tc_seen || dut.semantic_cancel || old_data_abort || old_scope);
                    if (bus_valid !== ((owner==CODE && code_pending && !code_captured) || physical_data_expected) ||
                        (bus_valid && bus_status!=(owner==CODE ? 4'hd : (data_phase==1 ? 4'h5 : 4'h6))))
                        $fatal(1,"RMW logical owner oracle failed: physical presence/second gate");
                    code_aborted=c_abort_now; data_aborted=d_abort_now;
                    c_complete_expected=owner==CODE && code_pending && !code_finished && !c_abort_now &&
                        boundary && next_cpu>=code_start_cpu+2+code_waits && (code_captured || c_capture);
                    first_complete_expected=owner==DATA && data_pending && odd && !first_tc_seen && !d_abort_now &&
                        boundary && next_cpu>=data_start_cpu+2+wait1 && (captured1 || first_capture);
                    d_complete_expected=owner==DATA && data_pending && !data_finished && !d_abort_now &&
                        boundary && (odd ? first_tc_seen && next_cpu>=first_tc_cpu+2+wait2 : next_cpu>=data_start_cpu+2+wait1) &&
                        (captured2 || final_capture);
                    c_valid_expected=code_pending && !c_abort_now && (code_finished || c_complete_expected);
                    d_valid_expected=data_pending && !d_abort_now && (data_finished || d_complete_expected);
                    if (code_complete !== c_complete_expected || dut.fetch_response_valid !== c_valid_expected)
                        $fatal(1,"RMW CODE publication oracle failed");
                    if (first_complete !== first_complete_expected) $fatal(1,"RMW first eligible first Tc oracle failed");
                    if (data_complete !== d_complete_expected || dut.memory_response_valid !== d_valid_expected)
                        $fatal(1,"RMW word publication oracle failed");
                    alignment_expected=owner==DATA && data_pending && odd && boundary && next_cpu==data_start_cpu+1;
                    read_wait_expected=owner==DATA && data_pending && !d_abort_now && boundary &&
                        (first_tc_seen ? next_cpu>=first_tc_cpu+2 && !p06_data_board_ready :
                            next_cpu>=data_start_cpu+2 && !p06_data_board_ready);
                    if (!d_abort_now && !c_abort_now && (alignment_event !== alignment_expected ||
                        policy_read_wait !== (read_wait_expected && data_phase==1) || diagnostic_read_wait !== read_wait_expected))
                        $fatal(1,"RMW independent alignment/wait event oracle failed");
                    if (alignment_expected && !d_abort_now) alignment_count=alignment_count+1;
                    if (owner==CODE && boundary && !c_abort_now && next_cpu>=code_start_cpu+2) begin
                        if (!p06_code_board_ready) code_ext=code_ext+1;
                        else if (!(code_captured || c_capture)) code_misses=code_misses+1;
                    end
                    if (owner==DATA && boundary && !d_abort_now) begin
                        if (!first_tc_seen && next_cpu>=data_start_cpu+2) begin
                            if (!p06_data_board_ready) begin ext1=ext1+1; observed_wait[2*(data_phase-1)]=observed_wait[2*(data_phase-1)]+1; end
                            else if (!(odd ? captured1 || first_capture : captured2 || final_capture)) begin
                                miss1=miss1+1; observed_miss[2*(data_phase-1)]=observed_miss[2*(data_phase-1)]+1; end
                        end else if (first_tc_seen && next_cpu>=first_tc_cpu+2) begin
                            if (!p06_data_board_ready) begin ext2=ext2+1; observed_wait[2*(data_phase-1)+1]=observed_wait[2*(data_phase-1)+1]+1; end
                            else if (!(captured2 || final_capture)) begin miss2=miss2+1;
                                observed_miss[2*(data_phase-1)+1]=observed_miss[2*(data_phase-1)+1]+1; end
                        end
                    end
                end
                if (bus_valid) begin
                    if (hlda || bus_lock || (bus_status!=4'hd && bus_status!=4'h5 && bus_status!=4'h6) ||
                        bus_write !== (bus_status==4'h6) || data_oe !== (bus_status==4'h6))
                        $fatal(1,"unqualified physical access in RMW pilot");
                    if (physical_pending && (address!==held_address || bus_bhe_n!==held_bhe || bus_status!==held_status))
                        $fatal(1,"RMW physical metadata changed before READY");
                    physical_pending=1; held_address=address; held_bhe=bus_bhe_n; held_status=bus_status;
                    expected_bus_address=data_address+(odd && captured1 ? 24'd1 : 24'd0);
                    expected_bhe=odd && captured1;
                    if ((bus_status==4'h5 || bus_status==4'h6) &&
                        (address!==expected_bus_address || bus_bhe_n!==expected_bhe ||
                        (bus_status==4'h6 && data_out !==
                            (odd ? (captured1 ? {8'd0,write_value[15:8]} : {write_value[7:0],8'd0}) : write_value))))
                        $fatal(1,"RMW caller-derived address/lane/payload oracle failed");
                    if (TIMED && bus_status==4'hd && (address!==code_expected_address || bus_bhe_n!==code_expected_bhe))
                        $fatal(1,"RMW independent CODE metadata oracle failed");
                end
                if (c_capture) begin
                    code_captures=code_captures+1; code_captured=1; code_capture_edge=this_edge; physical_pending=0;
                    if (TIMED && !c_abort_now) observer_cursor=code_expected_ip+{14'd0,code_expected_count};
                end
                if (d_capture) begin
                    if (data_phase==2) begin
                        if (odd && !captured1) memory_expected[7:0]=write_value[7:0];
                        else if (odd) memory_expected[15:8]=write_value[15:8];
                        else memory_expected=write_value;
                        write_captures=write_captures+1;
                    end else read_captures=read_captures+1;
                    data_captures=data_captures+1; physical_pending=0;
                    if (first_capture) begin captured1=1; capture1_edge=this_edge; end
                    else begin captured2=1; capture2_edge=this_edge; if (!odd) begin captured1=1; capture1_edge=this_edge; end end
                    if (mode==29 && data_phase==2 && final_capture) begin
                        if (!boundary || next_cpu!=(odd ? first_tc_cpu+2+wait2 : data_start_cpu+2+wait1) || functional_pending)
                            $fatal(1,"RMW final READY/Tc coincidence oracle failed");
                        exact_capture_cpu=next_cpu;
                    end
                end
                if ((c_capture || d_capture) && !boundary) off_boundary=off_boundary+1;
                if (TIMED) begin
                    if (code_complete) begin
                        earliest=code_start_cpu+2+code_waits; while (cpu_edge(earliest)<code_capture_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"RMW CODE first eligible Tc oracle failed");
                        code_finished=1;
                    end
                    if (first_complete) begin
                        earliest=data_start_cpu+2+wait1; while (cpu_edge(earliest)<capture1_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"RMW first eligible first Tc oracle failed");
                        first_tc_seen=1; first_tc_cpu=next_cpu; first_tc_edge=this_edge;
                        second_started=1; second_start_edge=this_edge; first_completions=first_completions+1;
                    end
                    if (data_complete) begin
                        earliest=(odd ? first_tc_cpu+2+wait2 : data_start_cpu+2+wait1);
                        while (cpu_edge(earliest)<capture2_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"RMW first eligible final Tc oracle failed");
                        data_finished=1; data_completions=data_completions+1;
                    end
                    if (dut.memory_response_valid && data_phase==1 && dut.memory_read_data!==initial_mem)
                        $fatal(1,"RMW independent READ response payload oracle failed");
                    if (dut.fetch_response_valid && (dut.fetch_response_data!==code_expected_data ||
                        dut.fetch_response_ip!==code_expected_ip || dut.fetch_response_count!==code_expected_count))
                        $fatal(1,"RMW retained CODE payload oracle failed");
                    // A WRITE response acknowledges the operation; its data is unused.
                    released=(owner==CODE && (code_complete || (c_abort_now && code_captured))) ||
                        (owner==DATA && (data_complete || (d_abort_now && captured2)));
                    data_start_expected=dut.memory_request && boundary && !dut.semantic_cancel && !observer_bus_scope &&
                        !data_pending && (owner==NONE || released);
                    if (d_start !== data_start_expected) $fatal(1,"RMW first eligible DATA admission oracle failed");
                    if ((c_start || d_start) && (!boundary || (owner!=NONE && !released)) || (c_start && d_start))
                        $fatal(1,"RMW logical owner oracle failed: admission before final Tc/drain");
                    if (released) owner=NONE;
                    if (c_publish) begin code_pending=0; code_finished=0; code_responses=code_responses+1; end
                    if (d_publish) begin data_pending=0; data_finished=0; end
                    if (c_start) begin
                        owner=CODE; code_pending=1; code_captured=0; code_finished=0; code_aborted=0;
                        code_start_cpu=next_cpu; code_start_edge=this_edge; code_accepts=code_accepts+1;
                        code_expected_ip=observer_cursor; code_expected_address=code_base+{8'd0,observer_cursor};
                        code_expected_count=(code_expected_address[0] || observer_cursor==16'hffff) ? 2'd1 : 2'd2;
                        code_expected_bhe=code_expected_count==1 && !code_expected_address[0];
                        code_expected_data=code_expected_count==1 ? {8'd0,memory_byte(code_expected_address)} :
                            {memory_byte(code_expected_address+24'd1),memory_byte(code_expected_address)};
                    end
                    if (c_publish && execute_enable) observer_queue_count=observer_queue_count+code_fill_count;
                    if (consume) observer_queue_count=observer_queue_count-1;
                    if (redirect && ip_write_en) observer_queue_count=0;
                    if (observer_queue_count<0 || observer_queue_count>6 ||
                        observer_queue_count+(code_pending && !code_aborted ? int'(code_expected_count) : 0)>6)
                        $fatal(1,"RMW independent six-byte reservation oracle failed");
                end
                if (d_publish) data_responses=data_responses+1;
                if (d_start) begin
                    if (dut.memory_write !== (data_accepts==1) || dut.memory_byte || dut.io_transfer || dut.memory_address!==data_address ||
                        (data_accepts==1 && dut.memory_write_data!==write_value) || data_accepts>1 || consumes!=6)
                        $fatal(1,"RMW caller-derived logical request oracle failed");
                    data_accepts=data_accepts+1; data_phase=data_accepts;
                    wait1=data_phase==1 ? read_wait1 : write_wait1; wait2=data_phase==1 ? read_wait2 : write_wait2;
                    latency1=data_phase==1 ? read_latency1 : write_latency1; latency2=data_phase==1 ? read_latency2 : write_latency2;
                    captured1=0; captured2=0; first_tc_seen=0; second_started=0;
                    if (TIMED) begin owner=DATA; data_pending=1; data_finished=0; data_aborted=0;
                        data_start_cpu=next_cpu; data_start_edge=this_edge; end
                end
                if (instruction_start) begin
                    if (started!=0 || (TIMED && (!boundary || cursor_ip!=16'(start_ip)))) $fatal(1,"RMW instruction start oracle failed");
                    started=1; start_cpu=next_cpu;
                end
                if (consume && !warming) begin
                    if (consumes>=6 || dut.queue_consume_data!==memory_byte(code_base+{8'd0,16'(start_ip+consumes)}))
                        $fatal(1,"RMW independent consumed byte oracle failed");
                    consumes=consumes+1;
                end
                if (gpr_commit) $fatal(1,"RMW changed GPR");
                if (TIMED && memory_pending !== functional_pending) $fatal(1,"RMW original FLAGS pending oracle failed");
                if (functional_pending && (data_responses!=2 || read_captures!=(odd ? 2 : 1) || write_captures!=(odd ? 2 : 1) ||
                    memory_actual!==write_value)) $fatal(1,"RMW original WRITE disposition dependency oracle failed");
                if (dut.micro_active && dut.opcode_q==8'h81 && dut.micro_executor.temporary_valid_q[0] &&
                    dut.micro_executor.tmp0_q!==initial_mem) $fatal(1,"RMW original retained READ payload oracle failed");
                if (dut.micro_active && dut.opcode_q==8'h81 && dut.micro_executor.temporary_valid_q[1] &&
                    dut.micro_executor.tmp1_q!==immediate_value) $fatal(1,"RMW original retained immediate oracle failed");
                if (dut.micro_active && dut.opcode_q==8'h81 && dut.micro_executor.temporary_valid_q[2] &&
                    dut.micro_executor.tmp2_q!==write_value) $fatal(1,"RMW original retained result oracle failed");
                retire_expected=TIMED && functional_pending && boundary && started==1 && retired==0 &&
                    next_cpu-start_cpu>=7+4*int'(odd)+observed_wait[0]+observed_wait[1] && execute_enable && !control_error &&
                    !dut.semantic_cancel && !observer_bus_scope && !aborted && !timing_scope;
                if (TIMED && flags_commit !== retire_expected) $fatal(1,"RMW first eligible FLAGS commit oracle failed");
                if (flags_commit) begin
                    if (!functional_pending || (dut.internal_flags_write_data & 16'h08c5)!==(expected_flags & 16'h08c5))
                        $fatal(1,"RMW independent XOR FLAGS payload oracle failed");
                    committed_flags=expected_flags;
                end
                if (form_expected && !dut.semantic_cancel && !observer_bus_scope && !aborted) form_qualified=1;
            end
            #1; clk=1; #10; clk=0;
            if (watch && !reset && d_capture && write_this) begin
                if (!address_this[0]) store_lane({address_this[23:1],1'b0},dataout_this[7:0]);
                if (!bhe_this) store_lane({address_this[23:1],1'b1},dataout_this[15:8]);
            end
            if (watch && (memory_actual!==memory_expected || guard_before_actual!==8'h3c || guard_after_actual!==8'hc7))
                $fatal(1,"RMW per-edge external memory side-effect oracle failed");
            if (reset) begin age=0; cpu=0; physical_pending=0; owner=NONE; observer_queue_count=0;
                code_pending=0; data_pending=0; code_captured=0; captured1=0; captured2=0; end
            else begin age=this_edge; cpu=next_cpu; end
            if (watch && !reset) begin
                if (redirect && ip_write_en) observer_cursor=ip_write_data;
                if (code_aborted && code_captured) code_pending=0;
                if (data_aborted && captured2) data_pending=0;
                if (TIMED && debug_prefetch_count!==4'(observer_queue_count)) $fatal(1,"RMW post-edge queue occupancy oracle failed");
                if (TIMED && (dut.biu.owner_valid_q !== (owner!=NONE) ||
                    (owner!=NONE && dut.biu.owner_q!==(owner==CODE ? 2'd0 : 2'd1))))
                    $fatal(1,"RMW logical owner oracle failed: retained ownership");
                if (TIMED && instruction_retired !== retire_expected) $fatal(1,"RMW first eligible retirement oracle failed");
                if (instruction_retired) begin
                    if (aborted || retired!=0 || started!=1 || debug_gpr!==expected_gpr ||
                        debug_flags!==expected_flags || debug_ip!=16'(start_ip+6) || (TIMED && !boundary))
                        $fatal(1,"RMW retirement/architectural oracle failed");
                    if (TIMED && timing_active) $fatal(1,"RMW retired duration policy remained active");
                    if (TIMED && !flags_commit) $fatal(1,"RMW FLAGS/retirement did not share the qualified edge");
                    retired=1; retire_cpu=cpu;
                end
                if (!aborted && (debug_gpr!==committed_gpr || debug_flags!==committed_flags)) $fatal(1,"RMW state changed outside commit");
                if (TIMED && !aborted && retired==0 && debug_ip!=16'(start_ip)) $fatal(1,"RMW IP advanced before retirement");
                if (TIMED && started==1 && !aborted && !observer_bus_scope && !timing_scope && timing_active &&
                    timing_scheduled!==8'(3+4*int'(form_qualified)+2*alignment_count+observed_wait[0]+observed_wait[1])) $fatal(1,"RMW alignment/wait budget oracle failed");
                if (microcode_fault || unsupported_opcode || shutdown || (control_error && !warming)) $fatal(1,"unexpected full CPU RMW fault");
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%04h,%04h,%032h,%04h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%04h,%04h,%04h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%04h\n",
                    id,cycle,boundary,cpu,instruction_start,c_start,d_start,c_capture,d_capture,first_tc_this,final_tc_this,
                    gpr_commit,instruction_retired,old_owner,bus_this,address_this,status_this,ready_this,debug_ip,cursor_ip,debug_gpr,
                    debug_flags,debug_prefetch_count,timing_scope,policy_wait_this,diagnostic_wait_this,align_this,pending_this,timing_scheduled,
                    write_this,bhe_this,dataout_this,memory_before_this,memory_actual,execute_this,cancel_this,old_phase,flags_commit,consumes,int'(form_qualified),form_this,datain_this);
            end
        end
    endtask

    task automatic setup;
        begin
            // Each vector rebases the external fixture; CPU reset never rewinds it.
            memory_actual=initial_mem; memory_expected=initial_mem;
            guard_before_actual=8'h3c; guard_after_actual=8'hc7;
            watch=0; execute_enable=0; reset=1; intr=0; nmi=0; hold_request=0;
            redirect=0; ip_write_en=0; segment_load_en=0; gpr_write_en=0; flags_write_en=0; fetch_request=0; fetch_ready=1;
            tick(); reset=0; repeat (40) tick(); if (bus_valid) $fatal(1,"RMW reset fetch did not drain");
            for (integer r=0;r<8;r=r+1) begin gpr_write_en=1; gpr_write_index=3'(r); gpr_write_data=initial_gpr[r*16+:16]; tick(); end
            gpr_write_en=0; flags_write_en=1; flags_write_data=initial_flags; flags_write_mask=16'hffff; tick(); flags_write_en=0;
            segment_load_en=1; segment_load_index=3; segment_load_selector=ds_selector; tick();
            segment_load_index=1; segment_load_selector=cs_selector; redirect=1; ip_write_en=1; ip_write_data=16'(start_ip); tick();
            segment_load_en=0; redirect=0; ip_write_en=0; fetch_ready=0;
            if (debug_gpr!==initial_gpr || debug_flags!==initial_flags || debug_ip!=16'(start_ip) ||
                debug_segment_bases[3*24+:24]!=={4'd0,ds_selector,4'd0}) $fatal(1,"RMW external state seed mismatch");
            cycle=0; started=0; retired=0; consumes=0; start_cpu=0; retire_cpu=0;
            code_accepts=0; data_accepts=0; code_captures=0; data_captures=0; code_responses=0; data_responses=0;
            code_ext=0; ext1=0; ext2=0; code_misses=0; miss1=0; miss2=0; alignment_count=0; off_boundary=0;
            first_completions=0; data_completions=0; first_tc_cpu=0; first_tc_edge=0; second_start_edge=0; exact_capture_cpu=0;
            code_start_cpu=0; data_start_cpu=0; code_start_edge=0; data_start_edge=0;
            owner=NONE; code_pending=0; data_pending=0; code_captured=0; captured1=0; captured2=0;
            code_finished=0; data_finished=0; first_tc_seen=0; second_started=0; code_aborted=0; data_aborted=0;
            physical_pending=0; observer_cursor=16'(start_ip); committed_gpr=initial_gpr; committed_flags=initial_flags;
            data_phase=0; read_captures=0; write_captures=0; form_qualified=0;
            for (integer q=0;q<4;q=q+1) begin observed_wait[q]=0; observed_miss[q]=0; end
            observer_bus_scope=0; observer_queue_count=0; action_done=0; aborted=0; watch=1; execute_enable=1;
            if (warm && TIMED) begin
                warming=1; redirect=1;
                while ((debug_prefetch_count<5 || owner!=NONE || code_pending) && cycle<1600) tick();
                if (started!=0 || debug_prefetch_count<5) $fatal(1,"RMW warm prefill failed");
                warming=0; redirect=0;
            end
        end
    endtask
    function automatic bit action_trigger;
        begin
            case (mode)
                1,12,19,26: action_trigger=functional_pending;
                2,7,14,21,27: action_trigger=data_accepts==1 && !captured1;
                3,10,17,24,28: action_trigger=data_accepts==2 && !captured1;
                4,8,15,22: action_trigger=data_phase==1 && first_tc_seen && !captured2;
                5,11,18,25: action_trigger=data_phase==2 && first_tc_seen && !captured2;
                9,16,23: action_trigger=data_responses==1 && data_accepts==1;
                6,13,20: action_trigger=dut.memory_request && data_accepts==0;
                default: action_trigger=0;
            endcase
        end
    endfunction

    task automatic lifecycle;
        integer accepted_before,captures_before,target_phase;
        begin
            action_done=1; accepted_before=data_accepts; captures_before=data_captures; target_phase=data_phase;
            if ((mode==4 || mode==5 || mode==8 || mode==11 || mode==15 || mode==18 || mode==22 || mode==25) && !odd)
                $fatal(1,"RMW between-beat fixture requires odd word");
            if ((mode==7 || mode==10 || mode==14 || mode==17 || mode==21 || mode==24) && latency1!=0)
                $fatal(1,"RMW first READY coincidence fixture requires early backend");
            if ((mode==27 || mode==28) && latency1<=0)
                $fatal(1,"RMW before READY cancellation fixture requires late backend");
            if (mode>=1 && mode<=5) begin
                execute_enable=0;
                repeat (41) begin tick(); if (retired!=0 || debug_gpr!==initial_gpr || debug_flags!==initial_flags)
                    $fatal(1,"RMW paused caller leaked FLAGS/retirement"); end
                execute_enable=1;
            end else if (mode>=6 && mode<=12 || mode==27 || mode==28) begin
                aborted=1; execute_enable=0; redirect=1; ip_write_en=1; ip_write_data=16'h0500;
                tick(); redirect=0; ip_write_en=0; fetch_ready=1;
                if ((mode==7 || mode==10) && data_captures!=captures_before+1 ||
                    (mode==27 || mode==28) && data_captures!=captures_before)
                    $fatal(1,"RMW cancel/first READY coincidence oracle failed");
                if (instruction_retired || memory_pending || timing_active || debug_gpr!==initial_gpr ||
                    debug_flags!==initial_flags || debug_ip!=16'h0500) $fatal(1,"RMW redirect cancellation oracle failed");
                // Two 80-edge DATA halves and a following 80-edge canceled
                // CODE transfer fit inside this fixed external-drain window.
                repeat (320) tick();
                if (owner!=NONE || data_pending || bus_valid || data_accepts!=accepted_before ||
                    data_captures!=accepted_before*(odd ? 2 : 1) || dut.memory_response_valid ||
                    memory_actual!==(accepted_before==2 ? write_value : initial_mem))
                    $fatal(1,"RMW canceled accepted transfer did not drain without new WRITE");
            end else if (mode>=13 && mode<=19) begin
                hold_request=1;
            end else if (mode>=20 && mode<=26) begin
                aborted=1; execute_enable=0; reset=1; tick(); reset=0;
                // Reset suppresses the would-be first READY; external bytes
                // captured earlier survive. Only future backend beats abort.
                if ((mode==21 || mode==24) && data_captures!=captures_before)
                    $fatal(1,"RMW reset/first READY abort oracle failed");
                if (instruction_retired || memory_pending || timing_active) $fatal(1,"RMW reset retained result");
                watch=0; fetch_ready=1; repeat (40) tick();
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s",vectors_path) || !$value$plusargs("trace=%s",trace_path) ||
            !$value$plusargs("summary=%s",summary_path)) $fatal(1,"required RMW paths missing");
        if ($value$plusargs("mode=%d",mode)) begin end
        if (mode<0 || mode>29 || (!TIMED && mode!=0)) $fatal(1,"undefined RMW mode");
        warm=!$test$plusargs("cold"); vector_fd=$fopen(vectors_path,"r"); trace_fd=$fopen(trace_path,"w"); summary_fd=$fopen(summary_path,"w");
        if (vector_fd==0 || trace_fd==0 || summary_fd==0) $fatal(1,"RMW files unavailable");
        $fwrite(trace_fd,"id,edge,boundary,cpu_clock,start,code_start,data_start,code_capture,data_capture,first_tc,final_tc,gpr_write,retired,owner,bus,address,status,ready,ip,cursor,gpr,flags,queue,scope,policy_wait,diagnostic_wait,alignment,flags_pending,scheduled,write,bhe,dataout,memory_before,memory_after,execute,cancel,phase,flags_commit,consumes,form_count,form_event,datain\n");
        $fwrite(summary_fd,"id,timed,warm,mode,odd,start_cpu,retire_cpu,elapsed,code_accepts,data_accepts,code_captures,data_captures,code_responses,data_responses,read_accepts,write_accepts,read_captures,write_captures,read_responses,write_responses,code_external,read_wait1,read_wait2,write_wait1,write_wait2,code_misses,read_miss1,read_miss2,write_miss1,write_miss2,alignment_count,form_count,first_tc,final_tc,off_boundary,gpr,flags,ip,retired,scope,memory,guard_before,guard_after,scheduled\n");
        while (!$feof(vector_fd)) begin
            scan=$fscanf(vector_fd,"%d %h %h %h %h %h %h %h %h %d %d %d %d %d %d %d %d %d %d\n",
                id,start_ip,cs_selector,ds_selector,moffs,initial_mem,immediate_value,initial_gpr,initial_flags,
                code_waits,read_wait1,read_wait2,write_wait1,write_wait2,code_latency,read_latency1,read_latency2,write_latency1,write_latency2);
            if (scan!=19 || start_ip<0 || start_ip>65530 || moffs==16'hffff || initial_flags[8] ||
                code_waits<0 || code_waits>2 || read_wait1<0 || read_wait1>2 || read_wait2<0 || read_wait2>2 ||
                write_wait1<0 || write_wait1>2 || write_wait2<0 || write_wait2>2 || code_latency< -1 ||
                read_latency1< -1 || read_latency2< -1 || write_latency1< -1 || write_latency2< -1 ||
                (!moffs[0] && (read_wait2!=0 || write_wait2!=0))) $fatal(1,"invalid RMW vector schema");
            // Explicit caller snapshots avoid any simulator-dependent aliases
            // of mutable fscanf destinations, and never reference DUT values.
            write_value=initial_mem ^ immediate_value;
            expected_flags=(initial_flags & ~16'h08c5) | (write_value[15] ? 16'h0080 : 16'd0) |
                (write_value==0 ? 16'h0040 : 16'd0) | ((~^write_value[7:0]) ? 16'h0004 : 16'd0);
            odd=moffs[0]; code_base={4'd0,cs_selector,4'd0}; data_address={4'd0,ds_selector,4'd0}+{8'd0,moffs};
            if (data_address+24'd1>=code_base+{8'd0,16'(start_ip)} && data_address<=code_base+{8'd0,16'(start_ip+10)})
                $fatal(1,"RMW code/data sparse fixture overlap");
            expected_gpr=initial_gpr; setup();
            while (retired==0 && cycle<6500 && !aborted && !timing_scope) begin
                if (!action_done && action_trigger()) lifecycle();
                if (!aborted && !timing_scope) tick();
            end
            if (aborted) begin
                if (!action_done || retired!=0) $fatal(1,"RMW cancellation/reset action was not reached");
            end else if (mode>=13 && mode<=19) begin
                if (!timing_scope || retired!=0 || debug_gpr!==initial_gpr || debug_flags!==initial_flags)
                    $fatal(1,"RMW scope did not stop before FLAGS commit");
                repeat (320) tick();
                if (retired!=0 || hlda || bus_write || data_oe || owner!=NONE || bus_valid ||
                    data_captures!=data_accepts*(odd ? 2 : 1) ||
                    memory_actual!==(data_accepts==2 ? write_value : initial_mem))
                    $fatal(1,"RMW scoped accepted transfer did not drain without new WRITE");
            end else begin
                if (retired!=1 || started!=1 || consumes!=6 || data_accepts!=2 ||
                    read_captures!=(odd ? 2 : 1) || write_captures!=(odd ? 2 : 1) || data_responses!=2 ||
                    debug_gpr!==expected_gpr || debug_flags!==expected_flags || debug_ip!=16'(start_ip+6) ||
                    memory_actual!==write_value || (mode!=0 && mode!=29 && !action_done))
                    $fatal(1,"RMW independent final architecture/count oracle failed");
                if (TIMED && (observed_wait[0]!=read_wait1 || observed_wait[1]!=(odd ? read_wait2 : 0) ||
                    observed_wait[2]!=write_wait1 || observed_wait[3]!=(odd ? write_wait2 : 0) ||
                    alignment_count!=2*int'(odd) || first_completions!=2*int'(odd) || data_completions!=2 ||
                    !form_qualified || retire_cpu-start_cpu<7+4*int'(odd)+observed_wait[0]+observed_wait[1]))
                    $fatal(1,"RMW independent timing/count oracle failed");
            end
            $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h,%04h,%0d,%0d,%04h,%02h,%02h,%0d\n",
                id,TIMED,warm,mode,odd,start_cpu,retire_cpu,retire_cpu-start_cpu,code_accepts,data_accepts,code_captures,data_captures,
                code_responses,data_responses,int'(data_accepts>=1),int'(data_accepts>=2),read_captures,write_captures,
                int'(data_responses>=1),int'(data_responses>=2),code_ext,observed_wait[0],observed_wait[1],observed_wait[2],observed_wait[3],
                code_misses,observed_miss[0],observed_miss[1],observed_miss[2],observed_miss[3],alignment_count,int'(form_qualified),
                first_completions,data_completions,off_boundary,debug_gpr,debug_flags,debug_ip,retired,timing_scope,memory_actual,
                guard_before_actual,guard_after_actual,timing_scheduled);
            execute_enable=0; watch=0; warming=0; cases=cases+1;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_CORE_RMW_PASS cases=%0d checks=%0d timed=%0d warm=%0d mode=%0d",cases,checks,TIMED,warm,mode); $finish;
    end
endmodule
