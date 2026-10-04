`timescale 1ns/1ps
// Real full CPU and immutable caller-owned sparse memory. This qualifies the
// existing serialized A1 handoff, without adding any DUT storage or force.
module p06_core_read_stream_tb #(parameter bit TIMED=1'b0);
    `include "spk286_signals.svh"
    logic p06_code_board_ready=1, p06_data_board_ready=1;
`ifdef P06_ORIGINAL
    spk286 dut (.*);
`else
    spk286 #(.P06_REGISTER_PILOT(TIMED),.P06_FETCH_PILOT(TIMED),
        .P06_IU_PILOT(TIMED),.P06_MEMORY_PILOT(TIMED)) dut (.*);
`endif
    wire timed_boundary,code_issue,code_complete,data_complete,memory_pending;
    wire timing_scope,timing_active,policy_read_wait,diagnostic_read_wait;
    wire ghost_data_valid,ghost_code_valid;
    wire [7:0] timing_scheduled;
    wire [15:0] cursor_ip;
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
        assign timing_active=dut.p06_register.active;
        assign timing_scheduled=dut.p06_register.scheduled;
        assign policy_read_wait=dut.p06_read_wait_event;
        assign diagnostic_read_wait=dut.biu.p06_data.external_wait;
        assign cursor_ip=dut.p06_cursor_ip;
        assign ghost_data_valid=dut.biu.raw_data_response_valid;
        assign ghost_code_valid=dut.fetch.raw_response_valid;
    end else begin : max_view
        assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0;
        assign memory_pending=0; assign timing_scope=0; assign timing_active=0; assign timing_scheduled=0;
        assign policy_read_wait=0; assign diagnostic_read_wait=0; assign cursor_ip=debug_ip;
        assign ghost_data_valid=dut.memory_response_valid; assign ghost_code_valid=dut.fetch_response_valid;
    end endgenerate
`else
    assign timed_boundary=0; assign code_issue=0; assign code_complete=0; assign data_complete=0;
    assign memory_pending=0; assign timing_scope=0; assign timing_active=0; assign timing_scheduled=0;
    assign policy_read_wait=0; assign diagnostic_read_wait=0; assign cursor_ip=debug_ip;
    assign ghost_data_valid=dut.memory_response_valid; assign ghost_code_valid=dut.fetch_response_valid;
`endif
    localparam integer NONE=0,CODE=1,DATA=2;
    integer vector_fd,trace_fd,summary_fd,scan,id,read_count,start_ip,mode=0,action_read=0;
    logic [15:0] cs_selector,ds_selector,initial_flags,wait_pack,latency_pack;
    logic [127:0] initial_gpr,offset_pack,value_pack,committed_gpr;
    logic [15:0] offsets[0:7],values[0:7];
    logic [23:0] data_addresses[0:7],code_base;
    integer waits[0:7],latencies[0:7];
    integer code_waits,code_latency;
    integer age=0,cpu=0,cycle=0,cases=0,checks=0,started=0,retired=0,consumes=0;
    integer read_index=0,data_index=0,owner=NONE,observer_queue_count=0;
    integer code_start_cpu=0,code_start_edge=0,data_start_cpu=0,data_start_edge=0;
    integer code_capture_edge=0,data_capture_edge=0,code_ext=0,code_misses=0,data_misses=0;
    integer code_accepts=0,data_accepts=0,code_captures=0,data_captures=0,code_responses=0,data_responses=0;
    integer instruction_start_cpu[0:7],instruction_retire_cpu[0:7],instruction_ext[0:7];
    integer instruction_accepts[0:7],instruction_captures[0:7],instruction_responses[0:7];
    logic [127:0] retired_gpr[0:7];
    logic [15:0] retired_flags[0:7],retired_ip[0:7];
    integer physical_start_edge=0,off_boundary=0,paused_waits=0,exact_capture_cpu=0;
    integer action_retired=0,action_captures=0,recovered=0,recovery_resets=0;
    logic [15:0] observer_cursor,code_expected_ip,code_expected_data;
    logic [1:0] code_expected_count;
    logic [23:0] code_expected_address,held_address;
    logic code_expected_bhe,held_bhe;
    logic [3:0] held_status;
    bit code_pending=0,data_pending=0,code_captured=0,data_captured=0;
    bit code_finished=0,data_finished=0,code_aborted=0,data_aborted=0;
    bit physical_pending=0,watch=0,warming=0,warm=1,aborted=0,action_done=0,observer_bus_scope=0;
    string vectors_path,trace_path,summary_path;

    function automatic [7:0] memory_byte(input logic [23:0] a);
        begin
            memory_byte=8'hf4;
            for (integer n=0;n<read_count;n=n+1) begin
                if (a==code_base+{8'd0,16'(start_ip+3*n)}) memory_byte=8'ha1;
                else if (a==code_base+{8'd0,16'(start_ip+3*n+1)}) memory_byte=offsets[n][7:0];
                else if (a==code_base+{8'd0,16'(start_ip+3*n+2)}) memory_byte=offsets[n][15:8];
                if (a==data_addresses[n]) memory_byte=values[n][7:0];
                if (a==data_addresses[n]+24'd1) memory_byte=values[n][15:8];
            end
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
        bit c_valid_expected,d_valid_expected,c_abort_now,d_abort_now,released,data_start_expected,commit_expected;
        bit policy_wait_this,diagnostic_wait_this,pending_this;
        integer next_cpu,this_edge,old_owner,earliest,latency_now,code_fill_count;
        logic [15:0] word_on_bus;
        begin
            #8; boundary=boundary_oracle(); this_edge=age+1; next_cpu=cpu+(TIMED ? int'(boundary) : int'(!reset));
            if (TIMED && timed_boundary !== boundary) $fatal(1,"read stream rational clock oracle failed");
            if (!watch || reset) begin ready=bus_valid; p06_code_board_ready=1; p06_data_board_ready=1; end
            else if (TIMED) begin
                p06_code_board_ready=next_cpu>=code_start_cpu+2+code_waits;
                p06_data_board_ready=next_cpu>=data_start_cpu+2+waits[data_index];
                ready=(owner==CODE && code_pending && !code_captured) ?
                    (code_latency==-1 ? boundary && p06_code_board_ready : this_edge-code_start_edge-1>=code_latency) :
                    (owner==DATA && data_pending && !data_captured) ?
                    (mode==12 && data_index==action_read ? boundary && next_cpu==instruction_start_cpu[data_index]+5+waits[data_index] :
                        latencies[data_index]==-1 ? boundary && p06_data_board_ready :
                        this_edge-data_start_edge-1>=latencies[data_index]) : 1'b0;
            end else begin
                if (bus_valid && !physical_pending) physical_start_edge=this_edge;
                latency_now=bus_status==4'h5 ? latencies[read_index] : code_latency;
                ready=bus_valid && this_edge-physical_start_edge>=(latency_now==-1 ? 16 : latency_now);
            end
            word_on_bus={memory_byte({address[23:1],1'b1}),memory_byte({address[23:1],1'b0})};
            data_in=ready ? word_on_bus : 16'hbad0;
            #1;
            instruction_start=dut.opcode_start;
            gpr_commit=execute_enable && dut.effective_gpr_write_en && dut.commit_allowed;
            flags_commit=execute_enable && dut.effective_flags_write_en && dut.commit_allowed;
            consume=dut.queue_consume_valid && dut.queue_consume_ready;
            c_start=code_issue; d_start=dut.memory_request && dut.memory_request_ready;
            c_capture=bus_valid && ready && bus_status==4'hd;
            d_capture=bus_valid && ready && bus_status==4'h5;
            c_publish=dut.fetch_response_valid && dut.fetch_response_ready;
            d_publish=dut.memory_response_valid && dut.memory_response_ready;
            policy_wait_this=policy_read_wait; diagnostic_wait_this=diagnostic_read_wait; pending_this=functional_pending;
            old_owner=owner; code_fill_count=int'(code_expected_count);
            if (watch && !reset) begin
                checks=checks+1; cycle=cycle+1;
                if (TIMED && debug_prefetch_count!==4'(observer_queue_count))
                    $fatal(1,"read stream independent prefetch occupancy oracle failed");
                if (TIMED) begin
                    observer_bus_scope=observer_bus_scope || hold_request || bus_lock || dut.ack_request ||
                        (dut.memory_request && (dut.memory_write || dut.io_transfer || dut.memory_byte || dut.memory_address[0]));
                    c_abort_now=code_aborted || dut.stream_restart || observer_bus_scope;
                    d_abort_now=data_aborted || dut.semantic_cancel || observer_bus_scope;
                    code_aborted=c_abort_now; data_aborted=d_abort_now;
                    c_complete_expected=owner==CODE && code_pending && !code_finished && !c_abort_now &&
                        boundary && next_cpu>=code_start_cpu+2+code_waits && (code_captured || c_capture);
                    d_complete_expected=owner==DATA && data_pending && !data_finished && !d_abort_now &&
                        boundary && next_cpu>=data_start_cpu+2+waits[data_index] && (data_captured || d_capture);
                    c_valid_expected=code_pending && !c_abort_now && (code_finished || c_complete_expected);
                    d_valid_expected=data_pending && !d_abort_now && (data_finished || d_complete_expected);
                    if (code_complete !== c_complete_expected || dut.fetch_response_valid !== c_valid_expected)
                        $fatal(1,"read stream CODE publication oracle failed id=%0d edge=%0d",id,this_edge);
                    if (data_complete !== d_complete_expected || dut.memory_response_valid !== d_valid_expected)
                        $fatal(1,"read stream DATA publication oracle failed id=%0d edge=%0d",id,this_edge);
                    if (bus_valid !== ((owner==CODE && code_pending && !code_captured) ||
                        (owner==DATA && data_pending && !data_captured)) ||
                        (bus_valid && bus_status!=(owner==CODE ? 4'hd : 4'h5)))
                        $fatal(1,"read stream logical owner oracle failed: physical presence/owner");
                    if (owner==CODE && boundary && !c_abort_now && next_cpu>=code_start_cpu+2) begin
                        if (!p06_code_board_ready) code_ext=code_ext+1;
                        else if (!(code_captured || c_capture)) code_misses=code_misses+1;
                    end
                    if (owner==DATA && boundary && !d_abort_now && next_cpu>=data_start_cpu+2) begin
                        if (!p06_data_board_ready) instruction_ext[data_index]=instruction_ext[data_index]+1;
                        else if (!(data_captured || d_capture)) data_misses=data_misses+1;
                    end
                    if (!execute_enable && policy_read_wait) paused_waits=paused_waits+1;
                end
                if (bus_valid) begin
                    if (bus_write || data_oe || hlda || bus_lock || (bus_status!=4'hd && bus_status!=4'h5))
                        $fatal(1,"unqualified physical access in aligned read stream");
                    if (physical_pending && (address!==held_address || bus_bhe_n!==held_bhe || bus_status!==held_status))
                        $fatal(1,"read stream READ metadata changed before READY");
                    physical_pending=1; held_address=address; held_bhe=bus_bhe_n; held_status=bus_status;
                    if (bus_status==4'h5 && (address!==data_addresses[data_index] || bus_bhe_n!==1'b0))
                        $fatal(1,"read stream independent DS/moffs/lane oracle failed");
                    if (TIMED && bus_status==4'hd && (address!==code_expected_address || bus_bhe_n!==code_expected_bhe))
                        $fatal(1,"read stream independent CODE cursor/address oracle failed");
                end
                if (c_capture) begin
                    code_captures=code_captures+1; code_captured=1; code_capture_edge=this_edge; physical_pending=0;
                    if (TIMED && !c_abort_now) observer_cursor=code_expected_ip+{14'd0,code_expected_count};
                end
                if (d_capture) begin
                    data_captures=data_captures+1; instruction_captures[data_index]=instruction_captures[data_index]+1;
                    data_captured=1; data_capture_edge=this_edge; physical_pending=0;
                    if (mode==12 && data_index==action_read) begin
                        if (!boundary || next_cpu!=instruction_start_cpu[data_index]+5+waits[data_index] || gpr_commit)
                            $fatal(1,"read stream deadline coincidence oracle failed");
                        exact_capture_cpu=next_cpu;
                    end
                end
                if ((c_capture || d_capture) && !boundary) off_boundary=off_boundary+1;
                if (TIMED) begin
                    if (code_complete) begin
                        earliest=code_start_cpu+2+code_waits;
                        while (cpu_edge(earliest)<code_capture_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"read stream CODE first eligible Tc oracle failed");
                        code_finished=1;
                    end
                    if (data_complete) begin
                        earliest=data_start_cpu+2+waits[data_index];
                        while (cpu_edge(earliest)<data_capture_edge) earliest=earliest+1;
                        if (next_cpu!=earliest) $fatal(1,"read stream DATA first eligible Tc oracle failed");
                        data_finished=1;
                    end
                    if (dut.fetch_response_valid && (dut.fetch_response_data!==code_expected_data ||
                        dut.fetch_response_ip!==code_expected_ip || dut.fetch_response_count!==code_expected_count))
                        $fatal(1,"read stream retained CODE payload/metadata oracle failed");
                    if (dut.memory_response_valid && dut.memory_read_data!==values[data_index])
                        $fatal(1,"read stream retained DATA association oracle failed");
                    released=(owner==CODE && (code_complete || (c_abort_now && code_captured))) ||
                        (owner==DATA && (data_complete || (d_abort_now && data_captured)));
                    data_start_expected=dut.memory_request && boundary && !dut.semantic_cancel &&
                        !observer_bus_scope && !data_pending && (owner==NONE || released);
                    if (d_start !== data_start_expected) $fatal(1,"read stream first eligible DATA admission oracle failed");
                    if ((c_start || d_start) && (!boundary || (owner!=NONE && !released)) || (c_start && d_start))
                        $fatal(1,"read stream logical owner oracle failed: admission before Tc/drain");
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
                        $fatal(1,"read stream six-byte queue/reservation oracle failed");
                end
                if (d_publish) begin data_responses=data_responses+1;
                    instruction_responses[data_index]=instruction_responses[data_index]+1; end
                if (instruction_start) begin
                    if (started!=retired || started>=read_count ||
                        (TIMED && (!boundary || cursor_ip!=16'(start_ip+3*started) ||
                            (started>0 && next_cpu<=instruction_retire_cpu[started-1]))))
                        $fatal(1,"read stream serialized instruction start oracle failed");
                    read_index=started; instruction_start_cpu[read_index]=next_cpu;
                    started=started+1;
                end
                if (d_start) begin
                    if (started!=retired+1 || dut.memory_write || dut.memory_byte || dut.io_transfer ||
                        dut.memory_address!==data_addresses[read_index] || instruction_accepts[read_index]!=0)
                        $fatal(1,"read stream caller-derived DATA request/association oracle failed");
                    data_index=read_index; data_accepts=data_accepts+1;
                    instruction_accepts[data_index]=instruction_accepts[data_index]+1;
                    if (TIMED) begin owner=DATA; data_pending=1; data_captured=0; data_finished=0; data_aborted=0;
                        data_start_cpu=next_cpu; data_start_edge=this_edge; end
                end
                if (consume && !warming) begin
                    if (consumes>=3*read_count || dut.queue_consume_data!==memory_byte(code_base+{8'd0,16'(start_ip+consumes)}))
                        $fatal(1,"read stream independent consumed byte oracle failed");
                    consumes=consumes+1;
                end
                if (flags_commit) $fatal(1,"read stream A1 changed FLAGS");
                if (TIMED && memory_pending !== functional_pending) $fatal(1,"read stream original TMP0 pending oracle failed");
                if (functional_pending && dut.micro_executor.tmp0_q!==values[read_index])
                    $fatal(1,"read stream original TMP0 association oracle failed");
                commit_expected=TIMED && functional_pending && boundary && started==retired+1 &&
                    next_cpu-instruction_start_cpu[read_index]>=5+instruction_ext[read_index] &&
                    execute_enable && !control_error && !dut.semantic_cancel && !observer_bus_scope && !aborted && !timing_scope;
                if (TIMED && gpr_commit !== commit_expected) $fatal(1,"read stream first eligible commit oracle failed");
                if (gpr_commit) begin
                    if (dut.effective_gpr_write_index!=0 || dut.effective_gpr_write_data!==values[read_index] ||
                        instruction_captures[read_index]!=1 || instruction_accepts[read_index]!=1 ||
                        (TIMED && (!boundary || !functional_pending)))
                        $fatal(1,"read stream qualified AX commit oracle failed");
                    if (mode==12 && read_index==action_read && next_cpu!=exact_capture_cpu+1)
                        $fatal(1,"read stream captured TMP0 did not commit at next boundary");
                    committed_gpr[15:0]=values[read_index];
                end
            end
            #1; clk=1; #10; clk=0;
            if (reset) begin age=0; cpu=0; physical_pending=0; owner=NONE;
                code_pending=0; data_pending=0; code_captured=0; data_captured=0; observer_queue_count=0; end
            else begin age=this_edge; cpu=next_cpu; end
            if (watch && !reset) begin
                if (redirect && ip_write_en) observer_cursor=ip_write_data;
                if (code_aborted && code_captured) code_pending=0;
                if (data_aborted && data_captured) data_pending=0;
                if (TIMED && debug_prefetch_count!==4'(observer_queue_count))
                    $fatal(1,"read stream independent post-edge queue occupancy oracle failed");
                if (TIMED && (dut.biu.owner_valid_q !== (owner!=NONE) ||
                    (owner!=NONE && dut.biu.owner_q!==(owner==CODE ? 2'd0 : 2'd1))))
                    $fatal(1,"read stream logical owner oracle failed: retained owner registers");
                if (instruction_retired) begin
                    if (aborted || retired>=read_count || started!=retired+1 || (TIMED && !gpr_commit) ||
                        debug_gpr!==committed_gpr || debug_flags!==initial_flags ||
                        debug_ip!=16'(start_ip+3*(retired+1)) || (TIMED && !boundary) ||
                        instruction_accepts[retired]!=1 || instruction_captures[retired]!=1 || instruction_responses[retired]!=1)
                        $fatal(1,"read stream per-instruction retirement oracle failed id=%0d read=%0d",id,retired);
                    instruction_retire_cpu[retired]=cpu; retired_gpr[retired]=debug_gpr;
                    retired_flags[retired]=debug_flags; retired_ip[retired]=debug_ip; retired=retired+1;
                end
                if (!aborted && (debug_gpr!==committed_gpr || debug_flags!==initial_flags))
                    $fatal(1,"read stream state changed outside observed commit");
                if (TIMED && !aborted && debug_ip!=16'(start_ip+3*retired))
                    $fatal(1,"read stream architectural IP advanced before retirement");
                if (TIMED && started==retired+1 && !aborted && !observer_bus_scope && !timing_scope &&
                    timing_active && timing_scheduled!==8'(5+instruction_ext[read_index]))
                    $fatal(1,"read stream per-instruction READ wait budget oracle failed");
                if (microcode_fault || unsupported_opcode || shutdown || (control_error && !warming))
                    $fatal(1,"unexpected full CPU read stream fault");
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%0d,%04h,%04h,%032h,%04h,%0d,%0d,%0d,%0d,%0d,%0d\n",
                    id,recovered,cycle,boundary,cpu,read_index,instruction_start,c_start,d_start,c_capture,d_capture,
                    code_complete,data_complete,gpr_commit,instruction_retired,old_owner,address,bus_status,ready,
                    debug_ip,cursor_ip,debug_gpr,debug_flags,debug_prefetch_count,timing_scope,
                    policy_wait_this,diagnostic_wait_this,pending_this,timing_scheduled);
            end
        end
    endtask

    task automatic seed;
        begin
            watch=0; execute_enable=0; intr=0; nmi=0; hold_request=0;
            redirect=0; ip_write_en=0; segment_load_en=0; gpr_write_en=0; flags_write_en=0;
            fetch_request=0; fetch_ready=1;
            for (integer r=0;r<8;r=r+1) begin gpr_write_en=1; gpr_write_index=3'(r);
                gpr_write_data=initial_gpr[r*16+:16]; tick(); end
            gpr_write_en=0; flags_write_en=1; flags_write_data=initial_flags; flags_write_mask=16'hffff;
            tick(); flags_write_en=0;
            segment_load_en=1; segment_load_index=3; segment_load_selector=ds_selector; tick();
            segment_load_index=1; segment_load_selector=cs_selector; redirect=1; ip_write_en=1; ip_write_data=16'(start_ip); tick();
            segment_load_en=0; redirect=0; ip_write_en=0; fetch_ready=0;
            if (debug_gpr!==initial_gpr || debug_flags!==initial_flags || debug_ip!=16'(start_ip) ||
                debug_segment_bases[3*24+:24]!=={4'd0,ds_selector,4'd0}) $fatal(1,"read stream external state seed mismatch");
            cycle=0; started=0; retired=0; consumes=0; read_index=0; data_index=0;
            code_accepts=0; data_accepts=0; code_captures=0; data_captures=0; code_responses=0; data_responses=0;
            code_ext=0; code_misses=0; data_misses=0; off_boundary=0; paused_waits=0; exact_capture_cpu=0;
            for (integer n=0;n<8;n=n+1) begin
                instruction_start_cpu[n]=0; instruction_retire_cpu[n]=0; instruction_ext[n]=0;
                instruction_accepts[n]=0; instruction_captures[n]=0; instruction_responses[n]=0;
                retired_gpr[n]=0; retired_flags[n]=0; retired_ip[n]=0;
            end
            code_start_cpu=0; data_start_cpu=0; code_start_edge=0; data_start_edge=0;
            owner=NONE; code_pending=0; data_pending=0; code_captured=0; data_captured=0;
            code_finished=0; data_finished=0; code_aborted=0; data_aborted=0;
            physical_pending=0; observer_cursor=16'(start_ip); committed_gpr=initial_gpr;
            observer_bus_scope=0; observer_queue_count=0; aborted=0; watch=1; execute_enable=1;
            if (warm && TIMED) begin
                warming=1; redirect=1;
                while ((debug_prefetch_count<5 || owner!=NONE || code_pending) && cycle<1600) tick();
                if (started!=0 || debug_prefetch_count<5) $fatal(1,"read stream warm prefill failed");
                warming=0; redirect=0;
            end
        end
    endtask
    task automatic setup;
        begin
            watch=0; execute_enable=0; reset=1; tick(); reset=0; fetch_ready=1;
            repeat (40) tick();
            if (bus_valid) $fatal(1,"read stream reset fetch did not drain before seeding");
            seed();
        end
    endtask
    task automatic change_recovery_memory;
        begin
            // The host changes immutable memory only after old physical work
            // has drained (or an explicit reset has abandoned that context).
            // A canceled old payload cannot satisfy this new caller program.
            cs_selector=cs_selector ^ 16'h1000; start_ip=start_ip ^ 32'h0400;
            code_base={4'd0,cs_selector,4'd0};
            if (start_ip>65535-3*read_count) $fatal(1,"recovery program exceeds CS limit");
            for (integer n=0;n<read_count;n=n+1) values[n]=values[n] ^ 16'ha55a;
        end
    endtask
    task automatic lifecycle;
        integer previous_retired;
        logic [127:0] previous_gpr;
        begin
            action_done=1; previous_retired=retired; previous_gpr=committed_gpr;
            if (mode==1 || mode==2 || mode==9) begin
                execute_enable=0;
                repeat (41) begin tick();
                    if (retired!=previous_retired || debug_gpr!==previous_gpr || debug_flags!==initial_flags)
                        $fatal(1,"read stream paused caller leaked architectural work"); end
                execute_enable=1;
            end else if (mode==3 || mode==4) begin
                aborted=1; execute_enable=0; redirect=1; ip_write_en=1; ip_write_data=16'h0500;
                tick(); redirect=0; ip_write_en=0; fetch_ready=1;
                // Original fetch performs one automatic restart fetch even
                // with EU disabled. Consume that new-context response through
                // its public external port while the canceled old READ drains.
                if (memory_pending || timing_active || instruction_retired || debug_gpr!==previous_gpr ||
                    debug_flags!==initial_flags || debug_ip!=16'h0500) $fatal(1,"read stream redirect failed cancellation");
                repeat (200) tick();
                if (owner!=NONE || code_pending || data_pending || bus_valid || instruction_captures[action_read]!=1)
                    $fatal(1,"read stream canceled READ did not drain once owner=%0d code=%0d data=%0d bus=%0d captures=%0d",owner,code_pending,data_pending,bus_valid,instruction_captures[action_read]);
                if (dut.memory_response_valid || dut.fetch_response_valid || ghost_data_valid ||
                    ghost_code_valid) $fatal(1,"read stream cancel retained ghost response");
                action_retired=retired; action_captures=data_captures; recovered=1; change_recovery_memory(); seed();
            end else if (mode==5 || mode==6) begin
                action_retired=retired; action_captures=data_captures;
                aborted=1; execute_enable=0; reset=1; tick(); reset=0;
                if (instruction_retired || memory_pending || timing_active) $fatal(1,"read stream reset retained old instruction");
                watch=0; fetch_ready=1; repeat (40) tick();
                recovered=1; recovery_resets=1; change_recovery_memory(); seed();
            end else if (mode==7 || mode==8) begin
                hold_request=1; tick();
                if (!timing_scope || instruction_retired || debug_gpr!==previous_gpr || debug_flags!==initial_flags)
                    $fatal(1,"read stream HOLD scope failed before commit");
                repeat (200) tick();
                if (hlda || bus_write || data_oe || owner!=NONE || bus_valid || retired!=previous_retired ||
                    instruction_captures[action_read]!=1) $fatal(1,"read stream scope drain leaked work");
                action_retired=retired; action_captures=data_captures;
                recovered=1; recovery_resets=1; hold_request=0; change_recovery_memory(); setup();
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("vectors=%s",vectors_path) || !$value$plusargs("trace=%s",trace_path) ||
            !$value$plusargs("summary=%s",summary_path)) $fatal(1,"required read stream paths missing");
        if ($value$plusargs("mode=%d",mode)) begin end
        if ($value$plusargs("action_read=%d",action_read)) begin end
        if (!(mode>=0 && mode<=9 || mode==12) || (!TIMED && mode!=0)) $fatal(1,"undefined read stream mode");
        warm=!$test$plusargs("cold");
        vector_fd=$fopen(vectors_path,"r"); trace_fd=$fopen(trace_path,"w"); summary_fd=$fopen(summary_path,"w");
        if (vector_fd==0 || trace_fd==0 || summary_fd==0) $fatal(1,"read stream files unavailable");
        $fwrite(trace_fd,"id,recovered,edge,boundary,cpu_clock,read_index,start,code_start,data_start,code_capture,data_capture,code_complete,data_complete,gpr_write,retired,owner,address,status,ready,ip,cursor,gpr,flags,queue,scope,policy_read_wait,diagnostic_read_wait,tmp0_pending,scheduled\n");
        $fwrite(summary_fd,"id,timed,warm,mode,count,read_index,start_cpu,retire_cpu,elapsed,data_external,data_accepts,data_captures,data_responses,code_accepts,code_captures,code_external,code_misses,data_misses,off_boundary,gpr,flags,ip,recovered,action_retired,action_captures,recovery_resets,paused_waits\n");
        while (!$feof(vector_fd)) begin
            scan=$fscanf(vector_fd,"%d %d %h %h %h %h %h %d %d %h %h %h %h\n",
                id,read_count,start_ip,cs_selector,ds_selector,initial_gpr,initial_flags,
                code_waits,code_latency,offset_pack,value_pack,wait_pack,latency_pack);
            if (scan!=13 || (read_count!=2 && read_count!=4 && read_count!=8) ||
                start_ip<0 || start_ip>65535-3*read_count || initial_flags[8] || code_waits<0 || code_waits>2 ||
                code_latency< -1 || action_read<0 || action_read>=read_count || (mode==9 && action_read>=read_count-1))
                $fatal(1,"invalid aligned read stream vector schema");
            code_base={4'd0,cs_selector,4'd0};
            for (integer n=0;n<8;n=n+1) begin
                offsets[n]=offset_pack[n*16+:16]; values[n]=value_pack[n*16+:16];
                data_addresses[n]={4'd0,ds_selector,4'd0}+{8'd0,offsets[n]};
                waits[n]=int'(wait_pack[n*2+:2]);
                case (latency_pack[n*2+:2])
                    0:latencies[n]=0; 1:latencies[n]=-1; 2:latencies[n]=80; 3:latencies[n]=160;
                endcase
                if (n<read_count && (offsets[n][0] || waits[n]>2 ||
                    (data_addresses[n]+24'd1>=code_base+{8'd0,16'(start_ip)} &&
                     data_addresses[n]<=code_base+{8'd0,16'(start_ip+3*read_count+6)})))
                    $fatal(1,"invalid read stream aligned sparse memory fixture");
                for (integer previous=0;previous<n;previous=previous+1)
                    if (n<read_count && offsets[n]==offsets[previous] && values[n]!=values[previous])
                        $fatal(1,"read stream repeated address requires stable value");
            end
            action_done=0; recovered=0; recovery_resets=0; action_retired=0; action_captures=0; setup();
            while (retired<read_count && cycle<6000) begin
                if (!action_done && ((mode>=1 && mode<=8 && read_index==action_read &&
                    ((mode[0] && functional_pending) || (!mode[0] && instruction_accepts[action_read]==1))) ||
                    (mode==9 && retired==action_read+1))) lifecycle();
                tick();
            end
            if (retired!=read_count || started!=read_count || consumes!=3*read_count || data_accepts!=read_count ||
                data_captures!=read_count || data_responses!=read_count || debug_flags!==initial_flags ||
                debug_ip!=16'(start_ip+3*read_count) || debug_gpr[15:0]!==values[read_count-1] ||
                debug_gpr[127:16]!==initial_gpr[127:16] || (mode!=0 && mode!=12 && !action_done))
                $fatal(1,"read stream independent final architecture/count oracle failed id=%0d",id);
            for (integer n=0;n<read_count;n=n+1) begin
                if (instruction_accepts[n]!=1 || instruction_captures[n]!=1 || instruction_responses[n]!=1 ||
                    (TIMED && (instruction_ext[n]!=waits[n] || instruction_retire_cpu[n]-instruction_start_cpu[n]<5+waits[n])))
                    $fatal(1,"read stream independent per-read count/wait oracle failed");
                $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%032h,%04h,%04h,%0d,%0d,%0d,%0d,%0d\n",
                    id,TIMED,warm,mode,read_count,n,instruction_start_cpu[n],instruction_retire_cpu[n],
                    instruction_retire_cpu[n]-instruction_start_cpu[n],instruction_ext[n],instruction_accepts[n],
                    instruction_captures[n],instruction_responses[n],code_accepts,code_captures,code_ext,code_misses,
                    data_misses,off_boundary,retired_gpr[n],retired_flags[n],retired_ip[n],recovered,action_retired,action_captures,recovery_resets,paused_waits);
            end
            execute_enable=0; watch=0; warming=0; cases=cases+1;
        end
        $fclose(vector_fd); $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_CORE_READ_STREAM_PASS cases=%0d checks=%0d timed=%0d warm=%0d mode=%0d",cases,checks,TIMED,warm,mode); $finish;
    end
endmodule
