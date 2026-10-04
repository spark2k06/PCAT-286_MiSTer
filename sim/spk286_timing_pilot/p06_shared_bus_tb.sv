`timescale 1ns/1ps
// M6b component fixture: real fetch/queue/operand/BIU, one logical bus owner.
// All expected deadlines, metadata and results are maintained by the observer.
module p06_shared_bus_tb;
    logic clk=0, reset=1, cancel_data=0, restart=0, ready=0;
    logic hold_request=0, lock_request=0, ack_request=0;
    logic [15:0] data_in=16'hbad0, restart_ip=16'h0100;
    logic [23:0] code_base=0;
    logic [15:0] code_limit=16'hffff;
    logic manual_code_enable=0, code_consumer_enable=1, queue_consume=1;
    wire p06_cpu_boundary, phase_enable, phase_two, p06_scope_error, p06_scope_block;
    wire p06_code_admission, code_issue, code_complete, code_canceled;
    logic code_board_ready=1, data_board_ready=1;
    wire fetch_bus_valid, fetch_bus_bhe_n, fetch_bus_ready, fetch_ready, fetch_blocked;
    wire [23:0] fetch_address;
    wire [16:0] fetch_cursor;
    wire code_response_valid, code_response_ready;
    wire [15:0] code_response_data, code_response_ip;
    wire [1:0] code_response_count;
    wire queue_valid, queue_fill_ready;
    wire [7:0] queue_data;
    wire [3:0] queue_count;
    wire queue_fill=code_response_valid && code_response_ready;
    wire [4:0] projected_queue={1'b0,queue_count}+
        (queue_fill ? {3'd0,code_response_count} : 5'd0)-5'(queue_valid && queue_consume);
    wire p06_admission_enable=p06_code_admission && manual_code_enable && projected_queue<=5'd4;
    assign code_response_ready=code_consumer_enable && queue_fill_ready;
    p06_clock clock_policy (.clk(clk),.reset(reset),.phase_enable(phase_enable),
        .phase_two(phase_two),.cpu_enable(p06_cpu_boundary));
    spk286_fetch #(.P06_FETCH_TIMING(1'b1)) fetch (.clk(clk),.reset(reset),
        .p06_cpu_boundary(p06_cpu_boundary),.p06_board_ready(code_board_ready),
        .p06_admission_enable(p06_admission_enable),.p06_scope_block(p06_scope_block),
        .p06_bus_issue(code_issue),.p06_bus_complete(code_complete),.p06_bus_canceled(code_canceled),
        .ready(fetch_bus_ready),.data_in(data_in),.code_base(code_base),.code_limit(code_limit),
        .wrap_ip(1'b1),.restart(restart),.restart_ip(restart_ip),.request(manual_code_enable),
        .suspend(1'b0),.request_ready(fetch_ready),.response_ready(code_response_ready),
        .response_valid(code_response_valid),.response_data(code_response_data),
        .response_ip(code_response_ip),.response_count(code_response_count),
        .cursor(fetch_cursor),.blocked(fetch_blocked),.bus_valid(fetch_bus_valid),
        .bus_bhe_n(fetch_bus_bhe_n),.address(fetch_address));
    spk286_prefetch_queue queue (.clk(clk),.reset(reset),.flush(restart),
        .fill_valid(code_response_valid && code_consumer_enable),.fill_data(code_response_data),
        .fill_count(code_response_count),.fill_ready(queue_fill_ready),
        .consume_valid(queue_valid),.consume_data(queue_data),.consume_ready(queue_consume),.count(queue_count));

    logic op_valid=0, op_byte=1;
    logic [23:0] op_address=24'h002000;
    wire op_done, op_unlimited_done, op_blocked, op_gpr_write, op_gpr_byte;
    wire [15:0] op_read_data, op_gpr_data;
    wire [2:0] op_gpr_index;
    wire operand_request, operand_write, operand_byte, operand_response_ready, operand_wait;
    wire [23:0] operand_address;
    wire [15:0] operand_write_data;
    wire data_request_ready, data_response_valid;
    wire [15:0] data_read_data;
    spk286_operand operand (.clk(clk),.reset(reset),.cancel(cancel_data),
        .request_valid(op_valid),.request_write(1'b0),.request_check(1'b0),.request_byte(op_byte),
        .select_rm(1'b1),.write_data(16'hfedc),.done(op_done),.unlimited_memory_done(op_unlimited_done),
        .read_data(op_read_data),.register_state(128'd0),.reg_index(3'd0),.rm_index(3'd0),
        .register_direct(1'b0),.physical_address(op_address),.offset(16'h2000),
        .segment_limit(16'hffff),.segment_expand_down(1'b0),.parallel_within_limit(1'b1),
        .blocked(op_blocked),.gpr_write_en(op_gpr_write),.gpr_write_byte(op_gpr_byte),
        .gpr_write_index(op_gpr_index),.gpr_write_data(op_gpr_data),
        .memory_request(operand_request),.memory_request_ready(data_request_ready),
        .memory_write(operand_write),.memory_byte(operand_byte),.memory_address(operand_address),
        .memory_write_data(operand_write_data),.memory_response_valid(data_response_valid),
        .memory_response_ready(operand_response_ready),.timing_wait(operand_wait),.memory_read_data(data_read_data));
    logic direct_mode=0, direct_request=0, direct_write=0, direct_byte=1, direct_io=0;
    logic direct_consumer_enable=1;
    logic [23:0] direct_address=24'h002000;
    wire data_request=direct_mode ? direct_request : operand_request;
    wire data_write=direct_mode ? direct_write : operand_write;
    wire data_byte=direct_mode ? direct_byte : operand_byte;
    wire data_io=direct_mode && direct_io;
    wire [23:0] data_address=direct_mode ? direct_address : operand_address;
    wire [15:0] data_write_data=direct_mode ? 16'hdead : operand_write_data;
    wire data_response_ready=direct_mode ? direct_consumer_enable : operand_response_ready;
    wire [23:0] address;
    wire [15:0] data_out;
    wire data_oe, bus_valid, bus_write, bus_bhe_n, hlda, bus_lock;
    wire [3:0] bus_status;
    wire ack_request_ready, ack_response_valid;
    wire [7:0] ack_vector;
    spk286_biu #(.P06_DATA_TIMING(1'b1),.P06_SHARED_TIMING(1'b1)) dut (
        .clk(clk),.reset(reset),.cancel_data(cancel_data),.ready(ready),.data_in(data_in),
        .p06_cpu_boundary(p06_cpu_boundary),.p06_board_ready(data_board_ready),
        .p06_code_issue(code_issue),.p06_code_complete(code_complete),.p06_code_canceled(code_canceled),
        .p06_code_admission(p06_code_admission),.p06_scope_error(p06_scope_error),.p06_scope_block(p06_scope_block),
        .hold_request(hold_request),.lock_request(lock_request),.hlda(hlda),.bus_lock(bus_lock),
        .ack_request(ack_request),.ack_request_ready(ack_request_ready),.ack_response_valid(ack_response_valid),
        .ack_response_ready(1'b1),.ack_vector(ack_vector),.code_valid(fetch_bus_valid),
        .code_bhe_n(fetch_bus_bhe_n),.code_address(fetch_address),.code_ready(fetch_bus_ready),
        .data_request(data_request),.data_write(data_write),.data_byte(data_byte),.data_io(data_io),
        .data_address(data_address),.data_write_data(data_write_data),.data_request_ready(data_request_ready),
        .data_response_valid(data_response_valid),.data_response_ready(data_response_ready),.data_read_data(data_read_data),
        .address(address),.data_out(data_out),.data_oe(data_oe),.bus_valid(bus_valid),
        .bus_write(bus_write),.bus_bhe_n(bus_bhe_n),.bus_status(bus_status));

    localparam integer NONE=0,CODE=1,DATA=2;
    integer fabric_age=0,cpu_clocks=0,owner=NONE,case_id=0,cases=0,checks=0,mode=0;
    integer code_waits=0,data_waits=0,code_latency=0,data_latency=0;
    integer code_accepts=0,data_accepts=0,code_reads=0,data_reads=0;
    integer code_captures=0,data_captures=0,code_completes=0,data_completes=0;
    integer code_responses=0,data_responses=0,code_ext=0,data_ext=0,code_misses=0,data_misses=0;
    integer code_start_cpu=0,data_start_cpu=0,code_start_edge=0,data_start_edge=0;
    integer code_capture_edge=0,data_capture_edge=0,code_complete_cpu=0,data_complete_cpu=0;
    integer handoffs=0,off_boundary=0,all_off_boundary=0,queue_bytes=0;
    integer expected_queue_ip=256,code_limit_accepts=1,data_limit_accepts=1;
    integer observer_queue_count=0;
    logic [15:0] observer_cursor=16'hfff0;
    integer trace_fd,summary_fd,direction=0,lane=0,code_odd=0,guard_kind=-1,lifecycle_stage=-1;
    logic [23:0] code_expected_address,data_expected_address,queue_base=0;
    logic code_expected_bhe,data_expected_bhe;
    logic [15:0] code_expected_data,data_expected_data,code_expected_ip;
    logic [1:0] code_expected_count;
    bit code_pending=0,data_pending=0,code_captured=0,data_captured=0;
    bit code_finished=0,data_finished=0,code_aborted=0,data_aborted=0,scope_seen=0;
    bit physical_pending=0,poison_inputs=0;
    bit observer_operand_pending=0;
    integer physical_owner=NONE;
    logic [23:0] physical_address;
    logic physical_bhe;
    string trace_path,summary_path,vectors_path;

    function automatic [7:0] pattern(input logic [23:0] a);
        pattern=a[7:0]^a[15:8]^8'h5a;
    endfunction
    function automatic bit boundary_oracle;
        boundary_oracle=!reset && (3*(fabric_age+1)/25 != 3*fabric_age/25);
    endfunction
    function automatic integer cpu_edge(input integer n);
        cpu_edge=(25*n+2)/3;
    endfunction
    function automatic bit illegal_oracle;
        illegal_oracle=ack_request || hold_request || lock_request ||
            (data_request && (data_write || data_io || (!data_byte && data_address[0])));
    endfunction

    task automatic tick;
        bit boundary,c_start,d_start,c_capture,d_capture,c_publish,d_publish;
        bit c_complete_expected,d_complete_expected,c_valid_expected,d_valid_expected;
        bit c_external,d_external,c_miss,d_miss,illegal,owner_released,data_eligible;
        bit physical_expected,data_request_expected,c_start_expected,d_start_expected,code_slot_free,code_phase_free;
        bit c_ready_expected,d_ready_expected,c_publish_expected,d_publish_expected;
        integer next_cpu,this_edge,old_owner,earliest,physical_kind,reserved,observer_projected_queue;
        logic [15:0] word_on_bus;
        begin
            #8;
            boundary=boundary_oracle(); next_cpu=cpu_clocks+int'(boundary); this_edge=fabric_age+1;
            if (p06_cpu_boundary !== boundary) $fatal(1,"rational boundary oracle failed");
            code_board_ready=next_cpu>=code_start_cpu+2+code_waits;
            data_board_ready=next_cpu>=data_start_cpu+2+data_waits;
            physical_kind=bus_status==4'hd ? CODE : bus_status==4'h5 ? DATA : NONE;
            physical_expected=(owner==CODE && code_pending && !code_captured) ||
                (owner==DATA && data_pending && !data_captured);
            ready=physical_expected && (owner==CODE ?
                (code_latency==-1 ? boundary && next_cpu>=code_start_cpu+2+code_waits :
                    this_edge-code_start_edge-1>=code_latency) :
                (data_latency==-1 ? boundary && next_cpu>=data_start_cpu+2+data_waits :
                    this_edge-data_start_edge-1>=data_latency));
            word_on_bus={pattern({address[23:1],1'b1}),pattern({address[23:1],1'b0})};
            data_in=ready ? word_on_bus : 16'hbad0;
            #1;
            c_start=code_issue; d_start=data_request && data_request_ready;
            c_capture=bus_valid && ready && bus_status==4'hd;
            d_capture=bus_valid && ready && bus_status==4'h5;
            c_publish=code_response_valid && code_response_ready;
            d_publish=data_response_valid && data_response_ready;
            illegal=illegal_oracle(); old_owner=owner;
            if (!reset) begin
                checks=checks+1;
                if (restart || illegal || scope_seen) code_aborted=1;
                if (cancel_data || illegal || scope_seen) data_aborted=1;
                if (bus_valid !== physical_expected) $fatal(1,"shared logical owner oracle failed: physical service presence");
                if (p06_scope_block !== (illegal || scope_seen)) $fatal(1,"shared scope guard oracle failed");
                c_complete_expected=owner==CODE && code_pending && !code_finished && !code_aborted &&
                    boundary && next_cpu>=code_start_cpu+2+code_waits && (code_captured || c_capture);
                d_complete_expected=owner==DATA && data_pending && !data_finished && !data_aborted &&
                    boundary && next_cpu>=data_start_cpu+2+data_waits && (data_captured || d_capture);
                c_valid_expected=code_pending && !code_aborted && (code_finished || c_complete_expected);
                d_valid_expected=data_pending && !data_aborted && (data_finished || d_complete_expected);
                c_ready_expected=code_consumer_enable && code_pending &&
                    observer_queue_count+int'(code_expected_count)<=6;
                d_ready_expected=direct_mode ? direct_consumer_enable :
                    op_valid && !cancel_data && observer_operand_pending;
                c_publish_expected=c_valid_expected && c_ready_expected;
                d_publish_expected=d_valid_expected && d_ready_expected;
                owner_released=(owner==CODE && (c_complete_expected || (code_aborted && (code_captured || c_capture)))) ||
                    (owner==DATA && (d_complete_expected || (data_aborted && (data_captured || d_capture))));
                data_request_expected=direct_mode ? direct_request :
                    (op_valid && !cancel_data && !observer_operand_pending);
                if (data_request !== data_request_expected) $fatal(1,"operand independent request oracle failed");
                data_eligible=data_request_expected && !cancel_data && !illegal && !scope_seen && boundary &&
                    !data_pending;
                d_start_expected=data_eligible && (owner==NONE || owner_released);
                code_slot_free=!code_pending || c_publish_expected ||
                    (code_aborted && code_captured);
                code_phase_free=(!code_pending || code_aborted) ||
                    ((code_finished || c_complete_expected) && c_publish_expected);
                observer_projected_queue=observer_queue_count+(c_publish_expected ? int'(code_expected_count) : 0)-
                    int'(observer_queue_count>0 && queue_consume && !restart);
                c_start_expected=manual_code_enable && !restart && !illegal && !scope_seen && boundary &&
                    (owner==NONE || owner_released) && !data_eligible && code_slot_free && code_phase_free &&
                    !(code_pending && !code_captured) && observer_projected_queue<=4 &&
                    observer_cursor<=code_limit;
                if (c_start !== c_start_expected || d_start !== d_start_expected)
                    $fatal(1,"shared logical owner oracle failed: required grant case=%0d cpu=%0d CODE=%b/%b DATA=%b/%b",
                        case_id,next_cpu,c_start,c_start_expected,d_start,d_start_expected);
                if (queue_valid !== (observer_queue_count>0)) $fatal(1,"independent queue-valid oracle failed");
                if (code_complete !== c_complete_expected || code_response_valid !== c_valid_expected)
                    $fatal(1,"CODE publication oracle failed case=%0d edge=%0d complete=%b/%b valid=%b/%b",
                        case_id,this_edge,code_complete,c_complete_expected,code_response_valid,c_valid_expected);
                if (dut.p06_complete !== d_complete_expected || data_response_valid !== d_valid_expected)
                    $fatal(1,"DATA publication oracle failed case=%0d edge=%0d",case_id,this_edge);
                if ((c_valid_expected && code_response_ready !== c_ready_expected) ||
                    data_response_ready !== d_ready_expected || c_publish !== c_publish_expected || d_publish !== d_publish_expected)
                    $fatal(1,"independent response-consumer oracle failed");
                c_external=owner==CODE && !code_aborted && boundary && next_cpu>=code_start_cpu+2 &&
                    next_cpu<code_start_cpu+2+code_waits;
                d_external=owner==DATA && !data_aborted && boundary && next_cpu>=data_start_cpu+2 &&
                    next_cpu<data_start_cpu+2+data_waits;
                c_miss=owner==CODE && !code_aborted && boundary && next_cpu>=code_start_cpu+2+code_waits &&
                    !(code_captured || c_capture);
                d_miss=owner==DATA && !data_aborted && boundary && next_cpu>=data_start_cpu+2+data_waits &&
                    !(data_captured || d_capture);
                if (fetch.p06_historical.external_wait !== c_external || fetch.p06_historical.deadline_miss !== c_miss ||
                    dut.p06_data.external_wait !== d_external || dut.p06_data.deadline_miss !== d_miss)
                    $fatal(1,"shared wait/deadline oracle failed");
                if (c_external) code_ext=code_ext+1; if (d_external) data_ext=data_ext+1;
                if (c_miss) code_misses=code_misses+1; if (d_miss) data_misses=data_misses+1;
                if (bus_valid) begin
                    if (physical_kind==NONE || physical_kind!=owner || data_oe || bus_write || hlda || bus_lock)
                        $fatal(1,"shared logical owner oracle failed: physical owner/type");
                    if (address !== (physical_kind==CODE ? code_expected_address : data_expected_address) ||
                        bus_bhe_n !== (physical_kind==CODE ? code_expected_bhe : data_expected_bhe))
                        $fatal(1,"accepted request metadata oracle failed");
                    if (physical_pending && (physical_kind!=physical_owner || address!==physical_address || bus_bhe_n!==physical_bhe))
                        $fatal(1,"physical READ changed before READY");
                    if (!physical_pending) begin
                        physical_pending=1; physical_owner=physical_kind; physical_address=address; physical_bhe=bus_bhe_n;
                        if (physical_kind==CODE) code_reads=code_reads+1; else data_reads=data_reads+1;
                    end
                end
                if (ack_request_ready || ack_response_valid || op_gpr_write || op_blocked)
                    $fatal(1,"unsupported side effect in shared READ pilot");
                if (c_capture) begin code_captures=code_captures+1; code_captured=1; code_capture_edge=this_edge; physical_pending=0; end
                if (d_capture) begin data_captures=data_captures+1; data_captured=1; data_capture_edge=this_edge; physical_pending=0; end
                if ((c_capture || d_capture) && !boundary) begin off_boundary=off_boundary+1; all_off_boundary=all_off_boundary+1; end
                if (code_complete) begin
                    earliest=code_start_cpu+2+code_waits;
                    while (cpu_edge(earliest)<code_capture_edge) earliest=earliest+1;
                    if (next_cpu!=earliest) $fatal(1,"CODE earliest Tc oracle failed");
                    code_completes=code_completes+1; code_finished=1; code_complete_cpu=next_cpu;
                end
                if (dut.p06_complete) begin
                    earliest=data_start_cpu+2+data_waits;
                    while (cpu_edge(earliest)<data_capture_edge) earliest=earliest+1;
                    if (next_cpu!=earliest) $fatal(1,"DATA earliest Tc oracle failed");
                    data_completes=data_completes+1; data_finished=1; data_complete_cpu=next_cpu;
                end
                if (code_response_valid && (code_response_data!==code_expected_data ||
                    code_response_ip!==code_expected_ip || code_response_count!==code_expected_count))
                    $fatal(1,"CODE retained result/metadata oracle failed");
                if (data_response_valid && data_read_data!==data_expected_data) $fatal(1,"DATA retained result oracle failed");
                if (!direct_mode && (op_done!==d_publish || (op_valid && op_unlimited_done!==d_publish) ||
                    (op_done && op_read_data!==data_expected_data))) $fatal(1,"operand real response oracle failed");
                if (c_start && data_eligible) $fatal(1,"shared logical owner oracle failed: DATA priority");
                if ((c_start || d_start) && (!boundary || (owner!=NONE && !owner_released) || illegal || scope_seen) ||
                    (c_start && d_start)) $fatal(1,"shared logical owner oracle failed: admission before Tc/drain");
                if (owner_released) owner=NONE;
                if (c_publish) begin code_responses=code_responses+1; code_pending=0; code_finished=0; end
                if (d_publish) begin data_responses=data_responses+1; data_pending=0; data_finished=0; end
                if (queue_valid && queue_consume && !restart) begin
                    if (queue_data!==pattern(queue_base+{8'd0,16'(expected_queue_ip)})) $fatal(1,"prefetch queue byte order oracle failed");
                    expected_queue_ip=(expected_queue_ip+1)&65535; queue_bytes=queue_bytes+1;
                end
                if (c_start) begin
                    if (code_pending && !code_aborted) $fatal(1,"second CODE packet without existing slot");
                    code_pending=1; code_captured=0; code_finished=0; code_aborted=0;
                    code_accepts=code_accepts+1; owner=CODE; code_start_cpu=next_cpu; code_start_edge=this_edge;
                    code_expected_ip=observer_cursor; code_expected_address=code_base+{8'd0,observer_cursor};
                    code_expected_count=(code_expected_address[0] || observer_cursor==code_limit) ? 2'd1 : 2'd2;
                    code_expected_bhe=code_expected_count==1 && !code_expected_address[0];
                    code_expected_data=code_expected_count==1 ? {8'd0,pattern(code_expected_address)} :
                        {pattern(code_expected_address+24'd1),pattern(code_expected_address)};
                    if (old_owner!=NONE && owner_released) handoffs=handoffs+1;
                end
                if (d_start) begin
                    if (data_pending && !data_aborted) $fatal(1,"second DATA packet without existing slot");
                    data_pending=1; data_captured=0; data_finished=0; data_aborted=0;
                    data_accepts=data_accepts+1; owner=DATA; data_start_cpu=next_cpu; data_start_edge=this_edge;
                    data_expected_address=direct_mode ? direct_address : op_address;
                    data_expected_bhe=(direct_mode ? direct_byte : op_byte) ? !data_expected_address[0] : 1'b0;
                    data_expected_data=(direct_mode ? direct_byte : op_byte) ? {8'd0,pattern(data_expected_address)} :
                        {pattern(data_expected_address+24'd1),pattern(data_expected_address)};
                    if (data_address!==data_expected_address || data_byte!==(direct_mode ? direct_byte : op_byte))
                        $fatal(1,"caller DATA metadata oracle failed");
                    if (old_owner!=NONE && owner_released) handoffs=handoffs+1;
                end
                if (illegal) scope_seen=1;
                $fwrite(trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%06h,%0d,%04h,%0d,%0d,%0d,%0d,%0d\n",
                    case_id,this_edge,next_cpu,boundary,old_owner,c_start,d_start,c_capture,d_capture,
                    code_complete,dut.p06_complete,c_publish,d_publish,ready,restart,cancel_data,address,bus_bhe_n,
                    data_in,queue_count,code_ext,data_ext,code_misses,data_misses);
            end
            #1; clk=1; #10; clk=0;
            if (reset) begin
                fabric_age=0; cpu_clocks=0; owner=NONE; physical_pending=0; physical_owner=NONE;
                code_pending=0; data_pending=0; code_captured=0; data_captured=0;
                code_finished=0; data_finished=0; code_aborted=0; data_aborted=0; scope_seen=0;
                observer_cursor=16'hfff0; observer_queue_count=0; observer_operand_pending=0;
            end else begin
                fabric_age=this_edge; cpu_clocks=next_cpu;
                if (restart) begin observer_cursor=restart_ip; observer_queue_count=0; end
                else begin
                    observer_queue_count=observer_projected_queue;
                    if (c_capture && !code_aborted) observer_cursor=code_expected_ip+{14'd0,code_expected_count};
                end
                if (cancel_data || (d_publish && !direct_mode)) observer_operand_pending=0;
                if (d_start && !direct_mode) observer_operand_pending=1;
                if (code_aborted && code_captured) code_pending=0;
                if (data_aborted && data_captured) data_pending=0;
                if (c_start && code_accepts>=code_limit_accepts) manual_code_enable=0;
                if (d_publish && data_responses>=data_limit_accepts) begin op_valid=0; direct_request=0; end
                if (poison_inputs && c_start) begin code_base=24'hde0000; code_limit=16'h0000; end
                if (poison_inputs && d_start) begin op_address=24'had00c1; op_byte=!op_byte; direct_address=24'had00c1; end
                if (scope_seen && !p06_scope_error) $fatal(1,"scope guard not retained");
                reserved=code_pending && !code_aborted ? int'(code_expected_count) : 0;
                if (int'(queue_count)+reserved>6) $fatal(1,"queue plus reserved CODE bytes exceeded six");
                if (int'(queue_count)!=observer_queue_count) $fatal(1,"independent queue-count oracle failed");
                if (!scope_seen && fetch_cursor !== {1'b0,observer_cursor}) $fatal(1,"independent fetch cursor oracle failed");
                if (dut.owner_valid_q !== (owner!=NONE) ||
                    (owner!=NONE && dut.owner_q !== (owner==CODE ? 2'd0 : 2'd1)))
                    $fatal(1,"shared logical owner oracle failed: retained owner registers");
            end
        end
    endtask

    task automatic setup(input integer cw,dw,cl,dl,odd,kind,dir,use_direct);
        begin
            reset=1; restart=0; cancel_data=0; hold_request=0; lock_request=0; ack_request=0;
            manual_code_enable=0; op_valid=0; direct_request=0; direct_write=0; direct_io=0;
            code_consumer_enable=1; direct_consumer_enable=1; queue_consume=1; poison_inputs=0;
            direct_mode=use_direct!=0; code_base=0; queue_base=0; code_limit=16'hffff;
            tick(); reset=0;
            code_accepts=0; data_accepts=0; code_reads=0; data_reads=0; code_captures=0; data_captures=0;
            code_completes=0; data_completes=0; code_responses=0; data_responses=0;
            code_ext=0; data_ext=0; code_misses=0; data_misses=0; handoffs=0; off_boundary=0; queue_bytes=0;
            code_start_cpu=0; data_start_cpu=0; code_start_edge=0; data_start_edge=0;
            code_capture_edge=0; data_capture_edge=0; code_complete_cpu=0; data_complete_cpu=0;
            code_limit_accepts=1; data_limit_accepts=1; guard_kind=-1; lifecycle_stage=-1;
            code_waits=cw; data_waits=dw; code_latency=cl; data_latency=dl; lane=kind; code_odd=odd; direction=dir;
            op_byte=kind!=2; direct_byte=kind!=2; op_address=24'h002000+(kind==1 ? 24'd1 : 24'd0); direct_address=op_address;
            restart_ip=16'h0100+16'(odd); expected_queue_ip=int'(restart_ip);
            restart=1; tick(); restart=0;
        end
    endtask
    task automatic demand_data;
        begin if (direct_mode) direct_request=1; else op_valid=1; end
    endtask
    task automatic finish_counts(input integer expected_codes,expected_data);
        begin
            while ((code_responses<expected_codes || data_responses<expected_data) && fabric_age<1500) tick();
            repeat (31) tick();
            if (code_accepts!=expected_codes || data_accepts!=expected_data || code_reads!=expected_codes || data_reads!=expected_data ||
                code_captures!=expected_codes || data_captures!=expected_data || code_completes!=expected_codes || data_completes!=expected_data ||
                code_responses!=expected_codes || data_responses!=expected_data || owner!=NONE || bus_valid)
                $fatal(1,"shared pair lost/duplicated or timed out");
        end
    endtask
    task automatic finish_pair;
        begin finish_counts(1,1); end
    endtask
    task automatic receipt(input integer kind);
        begin
            $fwrite(summary_fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",
                case_id,kind,direction,code_odd,lane,code_waits,data_waits,code_latency,data_latency,
                code_accepts,data_accepts,code_captures,data_captures,code_completes,data_completes,
                code_responses,data_responses,code_start_cpu,data_start_cpu,code_complete_cpu,data_complete_cpu,
                handoffs,code_ext,data_ext,code_misses,data_misses,off_boundary,guard_kind,lifecycle_stage);
            cases=cases+1; case_id=case_id+1;
        end
    endtask
    task automatic await_owner_stage(input integer selected_owner,stage);
        begin
            if (stage==0) begin end
            else if (stage==1 || stage==2) begin
                while ((selected_owner==CODE ? code_accepts : data_accepts)==0 && fabric_age<300) tick();
            end else if (stage==3) begin
                while ((selected_owner==CODE ? code_captures : data_captures)==0 && fabric_age<300) tick();
            end else if (stage==4) begin
                while (!(boundary_oracle() && cpu_clocks+1>=
                    (selected_owner==CODE ? code_start_cpu+2+code_waits : data_start_cpu+2+data_waits)) && fabric_age<300) tick();
            end else begin
                while ((selected_owner==CODE ? code_completes : data_completes)==0 && fabric_age<300) tick();
            end
            if (fabric_age>=300) $fatal(1,"shared lifecycle stage timeout");
        end
    endtask
    task automatic guard(input integer kind);
        begin
            case (kind)
                0: ack_request=1;
                1: hold_request=1;
                2: lock_request=1;
                3: begin direct_mode=1; direct_request=1; direct_write=1; end
                4: begin direct_mode=1; direct_request=1; direct_io=1; end
                5: begin direct_mode=1; direct_request=1; direct_byte=0; direct_address=24'h002001; end
                default: $fatal(1,"unknown shared guard");
            endcase
        end
    endtask

    initial begin
        if (!$value$plusargs("trace=%s",trace_path) || !$value$plusargs("summary=%s",summary_path)) $fatal(1,"required trace/summary paths missing");
        if ($value$plusargs("vectors=%s",vectors_path)) begin end
        if ($value$plusargs("mode=%d",mode)) begin end
        trace_fd=$fopen(trace_path,"w"); summary_fd=$fopen(summary_path,"w");
        $fwrite(trace_fd,"case,fabric_edge,cpu_clock,boundary,owner,code_start,data_start,code_capture,data_capture,code_complete,data_complete,code_response,data_response,ready,restart,cancel,address,bhe_n,data,queue_count,code_external,data_external,code_misses,data_misses\n");
        $fwrite(summary_fd,"case,kind,direction,code_odd,data_lane,code_waits,data_waits,code_latency,data_latency,code_accepts,data_accepts,code_captures,data_captures,code_completes,data_completes,code_responses,data_responses,code_start_cpu,data_start_cpu,code_complete_cpu,data_complete_cpu,handoffs,code_external,data_external,code_misses,data_misses,off_boundary,guard_kind,lifecycle_stage\n");
        if (mode==0) begin
            for (integer dir=0;dir<2;dir=dir+1)
                for (integer cw=0;cw<3;cw=cw+1)
                    for (integer dw=0;dw<3;dw=dw+1)
                        for (integer cl=0;cl<3;cl=cl+1)
                            for (integer dl=0;dl<3;dl=dl+1)
                                for (integer odd=0;odd<2;odd=odd+1)
                                    for (integer kind=0;kind<3;kind=kind+1) begin
                                        setup(cw,dw,cl==0 ? 0 : cl==1 ? -1 : 80,dl==0 ? 0 : dl==1 ? -1 : 80,odd,kind,dir,0);
                                        manual_code_enable=1;
                                        if (dir==0) begin
                                            while (code_accepts==0 && fabric_age<300) tick(); demand_data();
                                        end else demand_data();
                                        finish_pair();
                                        if (handoffs!=1 || (dir==0 ? data_start_cpu!=code_complete_cpu : code_start_cpu!=data_complete_cpu) ||
                                            code_ext!=cw || data_ext!=dw)
                                            $fatal(1,"cross-owner Tc handoff/minimum oracle failed");
                                        receipt(0);
                                    end
        end else if (mode==1) begin
            // Paused CODE publication releases the logical bus to DATA.
            setup(1,2,0,-1,1,2,0,0); code_consumer_enable=0; manual_code_enable=1;
            while (code_accepts==0) tick(); demand_data();
            while (data_responses==0 && fabric_age<700) tick();
            if (code_responses!=0 || !code_response_valid || data_responses!=1 || owner!=NONE)
                $fatal(1,"CODE PUBLISHED incorrectly held shared bus");
            repeat (31) tick(); code_consumer_enable=1; finish_pair(); receipt(1);
            // A held accepted DATA request and occupied DATA slot do not win
            // a false priority against an eligible fresh CODE request.
            setup(0,1,-1,0,0,1,1,1); direct_consumer_enable=0; demand_data(); manual_code_enable=1;
            while (code_responses==0 && fabric_age<700) tick();
            if (data_responses!=0 || !data_response_valid || data_accepts!=1 || !direct_request)
                $fatal(1,"held accepted DATA blocked CODE or replayed");
            direct_consumer_enable=1; finish_pair(); receipt(2);
            // Real operand pause across DATA publication, with CODE advancing.
            setup(2,0,0,45,1,0,1,0); demand_data();
            while (data_accepts==0) tick(); op_valid=0; manual_code_enable=1;
            while (code_responses==0 && fabric_age<700) tick();
            if (data_responses!=0 || op_done || !data_response_valid) $fatal(1,"paused real operand lost response");
            repeat (31) tick(); op_valid=1; finish_pair(); receipt(3);
            // Both request metadata records are latched independently.
            for (integer dir=0;dir<2;dir=dir+1) begin
                setup(0,0,45,45,1,2,dir,0); poison_inputs=1; manual_code_enable=1;
                if (dir==0) begin while (code_accepts==0) tick(); demand_data(); end else demand_data();
                finish_pair(); receipt(4);
            end
            // CODE reservation stops at six bytes (five after an odd first
            // byte). DATA must still progress, then CODE resumes as bytes drain.
            for (integer odd=0;odd<2;odd=odd+1) begin
                setup(0,1,0,-1,odd,2,0,0); code_limit_accepts=4; manual_code_enable=1; queue_consume=0;
                while (code_responses<3 && fabric_age<500) tick();
                repeat (31) tick();
                if (code_accepts!=3 || observer_queue_count!=(odd==0 ? 6 : 5) || owner!=NONE)
                    $fatal(1,"CODE capacity/reservation did not stop correctly");
                demand_data(); while (data_responses==0 && fabric_age<800) tick();
                if (data_responses!=1 || code_accepts!=3) $fatal(1,"full CODE queue blocked DATA");
                queue_consume=1; finish_counts(4,1); receipt(7);
            end
            setup(0,2,0,0,1,1,0,0); code_limit_accepts=4; manual_code_enable=1;
            while (code_accepts==0) tick(); demand_data(); finish_counts(4,1); receipt(8);
        end else if (mode==2) begin
            // Independent owner cancellation, then a fresh opposite-owner
            // request without reset. An accepted physical READ drains once.
            for (integer selected_owner=CODE;selected_owner<=DATA;selected_owner=selected_owner+1)
                for (integer stage=0;stage<6;stage=stage+1) begin
                    setup(1,1,stage==1 ? 80 : stage==4 ? -1 : 0,
                        stage==1 ? 80 : stage==4 ? -1 : 0,0,0,selected_owner==CODE ? 0 : 1,0);
                    lifecycle_stage=stage; code_consumer_enable=0;
                    if (selected_owner==CODE) manual_code_enable=1; else demand_data();
                    if (selected_owner==DATA && stage!=0) begin
                        while (data_accepts==0) tick(); op_valid=0;
                    end
                    await_owner_stage(selected_owner,stage); manual_code_enable=0; op_valid=0;
                    if (selected_owner==CODE) begin restart=1; restart_ip=16'h0401; expected_queue_ip=int'(restart_ip); end
                    else cancel_data=1;
                    tick(); restart=0; cancel_data=0;
                    while (bus_valid && fabric_age<700) tick(); repeat (31) tick();
                    if (code_responses!=0 || data_responses!=0 || bus_valid || owner!=NONE ||
                        (selected_owner==CODE ? code_captures : data_captures)!=(stage==0 ? 0 : 1))
                        $fatal(1,"owner cancel failed discard/drain");
                    if (selected_owner==CODE) begin demand_data(); while (data_responses==0 && fabric_age<1000) tick(); end
                    else begin code_consumer_enable=1; manual_code_enable=1; while (code_responses==0 && fabric_age<1000) tick(); end
                    if ((selected_owner==CODE ? data_responses : code_responses)!=1) $fatal(1,"opposite owner failed recovery without reset");
                    receipt(5);
                end
            // Cancel the other client while a READ owns the bus. Neither
            // cancellation input may invalidate the current owner's result.
            for (integer selected_owner=CODE;selected_owner<=DATA;selected_owner=selected_owner+1)
                for (integer stage=1;stage<6;stage=stage+1) begin
                    setup(1,1,stage==1 ? 80 : stage==4 ? -1 : 0,
                        stage==1 ? 80 : stage==4 ? -1 : 0,0,0,selected_owner==CODE ? 0 : 1,0);
                    lifecycle_stage=stage;
                    if (selected_owner==CODE) manual_code_enable=1; else demand_data();
                    if (stage==5) begin
                        if (selected_owner==CODE) code_consumer_enable=0;
                        else begin while (data_accepts==0) tick(); op_valid=0; end
                    end
                    await_owner_stage(selected_owner,stage);
                    if (selected_owner==CODE) cancel_data=1;
                    else begin restart=1; restart_ip=16'h0401; expected_queue_ip=int'(restart_ip); end
                    tick(); cancel_data=0; restart=0;
                    if (selected_owner==CODE) begin code_consumer_enable=1; demand_data(); end
                    else begin if (stage==5) op_valid=1; manual_code_enable=1; end
                    finish_pair(); receipt(10);
                end
            for (integer selected_owner=CODE;selected_owner<=DATA;selected_owner=selected_owner+1)
                for (integer stage=0;stage<6;stage=stage+1) begin
                    setup(1,1,stage==1 ? 80 : stage==4 ? -1 : 0,
                        stage==1 ? 80 : stage==4 ? -1 : 0,0,0,selected_owner==CODE ? 0 : 1,1);
                    lifecycle_stage=stage; code_consumer_enable=0; direct_consumer_enable=0;
                    if (selected_owner==CODE) manual_code_enable=1; else demand_data();
                    await_owner_stage(selected_owner,stage);
                    manual_code_enable=0; direct_request=0; reset=1; tick(); reset=0;
                    code_consumer_enable=1; direct_consumer_enable=1; repeat (31) tick();
                    if (owner!=NONE || bus_valid || code_response_valid || data_response_valid || observer_queue_count!=0)
                        $fatal(1,"reset preserved old shared state");
                    receipt(11);
                end
            // Global scope guards also suppress an already-PUBLISHED CODE
            // packet when the consumer becomes ready on the offending edge.
            for (integer selected_owner=CODE;selected_owner<=DATA;selected_owner=selected_owner+1)
                for (integer stage=0;stage<6;stage=stage+1)
                    for (integer g=0;g<6;g=g+1) begin
                        setup(0,0,stage==1 ? 80 : stage==4 ? -1 : 0,
                            stage==1 ? 80 : stage==4 ? -1 : 0,0,0,selected_owner==CODE ? 0 : 1,1);
                        lifecycle_stage=stage; guard_kind=g; code_consumer_enable=0; direct_consumer_enable=0;
                        if (selected_owner==CODE) manual_code_enable=1; else demand_data();
                        await_owner_stage(selected_owner,stage); guard(g);
                        code_consumer_enable=1; direct_consumer_enable=1; tick();
                        while (bus_valid && fabric_age<700) tick(); repeat (31) tick();
                        if (!p06_scope_error || code_responses!=0 || data_responses!=0 || bus_valid ||
                            (selected_owner==CODE ? code_captures : data_captures)!=(stage==0 ? 0 : 1))
                            $fatal(1,"global scope failed physical drain/publication suppression");
                        receipt(6);
                    end
            setup(1,2,0,0,1,1,1,0); demand_data(); manual_code_enable=1; finish_pair(); receipt(9);
        end else $fatal(1,"unknown shared fixture mode");
        $fclose(trace_fd); $fclose(summary_fd);
        $display("P06_SHARED_BUS_PASS mode=%0d cases=%0d checks=%0d off_boundary_captures=%0d",mode,cases,checks,all_off_boundary);
        $finish;
    end
endmodule
