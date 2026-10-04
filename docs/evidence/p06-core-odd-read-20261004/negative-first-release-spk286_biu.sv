// Shared normalized 80286 bus. Fetch supplies code-cycle metadata; the BIU
// sequences logical memory/I/O bytes and words and owns every READY handshake.
// I/O starts with a zero-extended port; an odd word retains physical carry
// into A16 (FFFF -> 10000), as captured by the pinned 286 corpus.
// This is functional transaction timing, not native Ts/Tc/Ti timing.
`timescale 1ns/1ps
module spk286_biu #(parameter bit P06_DATA_TIMING = 1'b0, parameter bit P06_SHARED_TIMING = 1'b0, parameter bit P06_ODD_READ_TIMING = 1'b0) (
    /* verilator lint_off UNUSEDSIGNAL */
    input logic p06_cpu_boundary, p06_board_ready,
    input logic p06_code_issue, p06_code_complete, p06_code_canceled,
    /* verilator lint_on UNUSEDSIGNAL */
    output logic p06_scope_error, p06_code_admission, p06_scope_block, p06_read_wait_event, p06_alignment_event,
    input  logic clk, reset, cancel_data,
    input  logic ready,
    input  logic hold_request, lock_request,
    output logic hlda,
    input  logic ack_request,
    output logic ack_request_ready, ack_response_valid,
    input  logic ack_response_ready,
    output logic [7:0] ack_vector,
    output logic bus_lock,
    input  logic [15:0] data_in,
    input  logic code_valid, code_bhe_n,
    input  logic [23:0] code_address,
    output logic code_ready,
    input  logic data_request, data_write, data_byte, data_io,
    input  logic [23:0] data_address,
    input  logic [15:0] data_write_data,
    output logic data_request_ready,
    output logic data_response_valid,
    input  logic data_response_ready,
    output logic [15:0] data_read_data,
    output logic [23:0] address,
    output logic [15:0] data_out,
    output logic data_oe, bus_valid, bus_write, bus_bhe_n,
    output logic [3:0] bus_status
);
    generate
        if (P06_ODD_READ_TIMING && (!P06_DATA_TIMING || !P06_SHARED_TIMING)) begin : p06_invalid_odd_configuration
            initial $fatal(1, "M6e odd READ requires DATA and SHARED timing");
        end
    endgenerate
    logic data_active_q, write_q, second_q, canceled_q, byte_q, io_q;
    logic [23:0] address_q;
    logic [15:0] write_data_q;
    logic [7:0] low_byte_q;
    logic owner_valid_q, select_data, select_ack, data_complete;
    logic [1:0] owner_q, selected_owner;
    logic ack_active_q, ack_second_q, lock_chain_q, ack_canceled_q;
// Private M6e normalized READ adapter: one aligned beat or two odd-word beats.
// Reuse the original low_byte_q/second_q/raw slot. Only phase state grows.
    logic raw_data_response_valid;
    logic [15:0] raw_data_read_data;
    logic p06_admit, p06_response_fire, p06_physical_data_enable;
    /* verilator lint_off UNUSEDSIGNAL */
    logic p06_capture, p06_complete, p06_first_complete, p06_external_wait;
    /* verilator lint_on UNUSEDSIGNAL */
    assign p06_capture = data_complete;
    assign p06_response_fire = data_response_valid && data_response_ready;
    generate
        if (P06_DATA_TIMING && P06_ODD_READ_TIMING) begin : p06_data
            localparam logic [2:0] IDLE = 0, TS = 1, TC = 2, PUBLISHED = 3,
                ODD_TS = 4, ODD_TC = 5, SECOND_TS = 6, SECOND_TC = 7;
            logic [2:0] state_q;
            wire unsupported_data = data_request &&
                (data_write || data_io || (!P06_ODD_READ_TIMING && !data_byte && data_address[0]));
            wire unsupported_bus = (code_valid && !P06_SHARED_TIMING) || ack_request || hold_request || lock_request;
            wire scope_block = p06_scope_error || unsupported_data || unsupported_bus;
            assign p06_scope_block = scope_block;
            assign p06_data_idle = state_q == IDLE;
            // A physical first READY has already advanced address_q/second_q.
            // The retained flag remains true even after an early second capture.
            wire first_available = second_q ||
                (p06_capture && address_q[0] && !byte_q);
            wire final_capture = p06_capture && (!address_q[0] || byte_q);
            wire available = raw_data_response_valid || final_capture;
            wire tc_phase = state_q == TC || state_q == ODD_TC || state_q == SECOND_TC;
            wire sample_tc = !reset && !cancel_data && !canceled_q &&
                !scope_block && p06_cpu_boundary && tc_phase;
            wire first_complete = sample_tc && state_q == ODD_TC &&
                p06_board_ready && first_available;
            assign p06_first_complete = first_complete;
            /* verilator lint_off UNUSEDSIGNAL */
            wire external_wait = sample_tc && !p06_board_ready;
            assign p06_external_wait = external_wait;
            wire deadline_miss = sample_tc && p06_board_ready &&
                !(state_q == ODD_TC ? first_available : available);
            /* verilator lint_on UNUSEDSIGNAL */
            // Duration inputs use retained context, never request-derived scope.
            // A new scope edge can stop publication before its sticky flag rises.
            assign p06_read_wait_event = !reset && !cancel_data && !canceled_q &&
                !p06_scope_error && p06_cpu_boundary && tc_phase && !p06_board_ready;
            assign p06_alignment_event = P06_ODD_READ_TIMING && !reset && !cancel_data && !canceled_q &&
                !p06_scope_error && p06_cpu_boundary && state_q == ODD_TS;
            assign p06_complete = sample_tc && state_q != ODD_TC && p06_board_ready && available;
            assign data_response_valid = !reset && !cancel_data && !scope_block &&
                ((state_q == PUBLISHED && raw_data_response_valid) || p06_complete);
            // Same-edge final READY/Tc uses the original two-byte normalization.
            // An earlier final result uses the original retained complete-word slot.
            assign data_read_data = !raw_data_response_valid && final_capture ?
                (byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :
                    (second_q ? {data_in[7:0], low_byte_q} : data_in)) : raw_data_read_data;
            assign p06_admit = !scope_block && !reset && !cancel_data &&
                p06_cpu_boundary && state_q == IDLE && p06_shared_data_grant;
            // The second physical beat cannot start before its logical Ts. If
            // the accepted word is abandoned, drain both original physical
            // halves on fabric edges without waiting for virtual CPU/board ticks.
            assign p06_physical_data_enable = !P06_ODD_READ_TIMING || byte_q || !second_q ||
                state_q == SECOND_TS || state_q == SECOND_TC ||
                cancel_data || canceled_q || p06_scope_error;
            always_ff @(posedge clk) begin
                if (reset) begin state_q <= IDLE; p06_scope_error <= 0; end
                else begin
                    if (unsupported_data || unsupported_bus) p06_scope_error <= 1;
                    if (p06_cpu_boundary) begin
                        if (state_q == TS) state_q <= TC;
                        if (state_q == ODD_TS) state_q <= ODD_TC;
                        if (state_q == SECOND_TS) state_q <= SECOND_TC;
                    end
                    // First Tc starts the second Ts, keeping the same DATA owner.
                    // The second Tc is two virtual clocks after this boundary.
                    if (first_complete) state_q <= SECOND_TS;
                    if (p06_complete) state_q <= data_response_ready ? IDLE : PUBLISHED;
                    if (state_q == PUBLISHED && p06_response_fire) state_q <= IDLE;
                    if (data_request && data_request_ready)
                        state_q <= P06_ODD_READ_TIMING && !data_byte && data_address[0] ? ODD_TS : TS;
                    if (cancel_data) state_q <= IDLE;
                end
            end
        end else if (P06_DATA_TIMING) begin : p06_data
            localparam logic [1:0] IDLE = 0, TS = 1, TC = 2, PUBLISHED = 3;
            logic [1:0] state_q;
            wire unsupported_data = data_request &&
                (data_write || data_io || (!data_byte && data_address[0]));
            wire unsupported_bus = (code_valid && !P06_SHARED_TIMING) || ack_request || hold_request || lock_request;
            wire scope_block = p06_scope_error || unsupported_data || unsupported_bus;
            assign p06_scope_block = scope_block;
            assign p06_data_idle = state_q == IDLE;
            wire available = raw_data_response_valid || p06_capture;
            wire sample_tc = !reset && !cancel_data && !canceled_q &&
                !scope_block && p06_cpu_boundary && state_q == TC;
            /* verilator lint_off UNUSEDSIGNAL */
            wire external_wait = sample_tc && !p06_board_ready;
            // Duration observes the already accepted TC lifetime. Do
            // not feed current request-derived scope back into EU
            // permit/start. New scope invalidates this context; its
            // sticky flag suppresses the following wait boundaries.
            assign p06_read_wait_event = !reset && !cancel_data && !canceled_q &&
                !p06_scope_error && p06_cpu_boundary && state_q == TC && !p06_board_ready;
            wire deadline_miss = sample_tc && p06_board_ready && !available;
            /* verilator lint_on UNUSEDSIGNAL */
            assign p06_complete = sample_tc && p06_board_ready && available;
            assign data_response_valid = !reset && !cancel_data && !scope_block &&
                ((state_q == PUBLISHED && raw_data_response_valid) || p06_complete);
            // Same-edge READY/Tc uses the original lane normalization. An early
            // result uses only the retained original slot, never live bus data.
            assign data_read_data = !raw_data_response_valid && p06_capture ?
                (byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} : data_in) : raw_data_read_data;
            assign p06_admit = !scope_block && !reset && !cancel_data &&
                p06_cpu_boundary && state_q == IDLE && p06_shared_data_grant;
            always_ff @(posedge clk) begin
                if (reset) begin state_q <= IDLE; p06_scope_error <= 0; end
                else begin
                    if (unsupported_data || unsupported_bus) p06_scope_error <= 1;
                    if (state_q == TS && p06_cpu_boundary) state_q <= TC;
                    if (p06_complete) state_q <= data_response_ready ? IDLE : PUBLISHED;
                    if (state_q == PUBLISHED && p06_response_fire) state_q <= IDLE;
                    if (data_request && data_request_ready) state_q <= TS;
                    // Cancel the logical lifetime. The original data_active_q
                    // keeps the physical READ draining on every fabric edge;
                    // it independently prevents admission until capture/drain.
                    if (cancel_data) state_q <= IDLE;
                end
            end
            assign p06_alignment_event = 1'b0;
            assign p06_first_complete = 1'b0;
            assign p06_external_wait = external_wait;
            assign p06_physical_data_enable = 1'b1;
        end else begin : p06_data_maximum
            assign p06_scope_error = 1'b0;
            assign p06_complete = 1'b0;
            assign p06_scope_block = 1'b0;
            assign p06_read_wait_event = 1'b0;
            assign p06_alignment_event = 1'b0;
            assign p06_first_complete = 1'b0;
            assign p06_external_wait = 1'b0;
            assign p06_data_idle = 1'b1;
            assign p06_admit = 1'b1;
            assign p06_physical_data_enable = 1'b1;
            assign data_response_valid = raw_data_response_valid;
            assign data_read_data = raw_data_read_data;
        end
    endgenerate

// Shared logical CODE/DATA ownership; reuse original owner registers.
    /* verilator lint_off UNUSEDSIGNAL */
    logic p06_shared_data_grant, p06_shared_release, p06_data_candidate, p06_data_idle;
    /* verilator lint_on UNUSEDSIGNAL */
    generate
        if (P06_DATA_TIMING && P06_SHARED_TIMING) begin : p06_shared
            wire code_owned = owner_valid_q && owner_q == 2'd0;
            wire data_owned = owner_valid_q && owner_q == 2'd1;
            wire code_abort = p06_code_canceled || p06_scope_block;
            wire data_abort = cancel_data || canceled_q || p06_scope_block;
            // A pulse cancel is retained by the original fetch/DATA canceled
            // state until physical capture. No new cancel or payload slot.
            assign p06_shared_release =
                (code_owned && (p06_code_complete ||
                    (code_abort && (!code_valid || code_ready)))) ||
                (data_owned && (p06_complete ||
                    (data_abort && (!data_active_q || (data_complete &&
                    1'b1)))));
            wire free_owner = !owner_valid_q || p06_shared_release;
            // Neutral eligibility precedes arbitration. A held accepted DATA
            // request or occupied result slot must not steal CODE priority.
            assign p06_data_candidate = data_request && !reset && !cancel_data &&
                !p06_scope_block && p06_cpu_boundary && p06_data_idle &&
                !data_active_q && !raw_data_response_valid && !ack_active_q && !hlda;
            assign p06_shared_data_grant = free_owner;
            assign p06_code_admission = !reset && !p06_scope_block &&
                p06_cpu_boundary && free_owner && !p06_data_candidate;
        end else begin : p06_unshared
            assign p06_shared_release = 1'b0;
            assign p06_data_candidate = 1'b0;
            assign p06_shared_data_grant = 1'b1;
            assign p06_code_admission = 1'b1;
        end
    endgenerate

    assign data_request_ready = !reset && !cancel_data && !data_active_q && !raw_data_response_valid && !ack_active_q && !hlda && p06_admit;
    assign ack_request_ready = !reset && !cancel_data && !data_active_q && !raw_data_response_valid && !ack_active_q && !ack_response_valid && !hlda && !P06_DATA_TIMING;
    // Data has priority at a free boundary. Once a cycle is visible and waiting,
    // its owner cannot change even if a higher-priority request appears.
    assign selected_owner = owner_valid_q ? owner_q : (ack_active_q ? 2'd2 : (data_active_q ? 2'd1 : 2'd0));
    assign select_data = selected_owner == 2'd1;
    assign select_ack = selected_owner == 2'd2;
    assign bus_valid = !reset && !hlda && (select_ack ? ack_active_q : (select_data ? (data_active_q && p06_physical_data_enable) : (code_valid && !lock_chain_q && (!P06_DATA_TIMING || P06_SHARED_TIMING))));
    assign address = !bus_valid || select_ack ? 24'h000000 : (select_data ? address_q : code_address);
    assign bus_write = bus_valid && select_data && write_q;
    assign bus_bhe_n = !bus_valid || select_ack ? 1'b1 : (select_data ? (byte_q ? !address_q[0] : second_q) : code_bhe_n);
    assign data_out = !bus_write ? 16'h0000 :
                      (address_q[0] ? {write_data_q[7:0], 8'h00} :
                       (second_q ? {8'h00, write_data_q[15:8]} : (byte_q ? {8'd0, write_data_q[7:0]} : write_data_q)));
    assign data_oe = bus_write;
    assign bus_status = !bus_valid ? 4'hF : (select_ack ? 4'h0 : (!select_data ? 4'hD : (io_q ? (write_q ? 4'hA : 4'h9) : (write_q ? 4'h6 : 4'h5))));
    assign code_ready = bus_valid && !select_data && !select_ack && ready;
    assign data_complete = bus_valid && select_data && ready;
    assign bus_lock = !reset && ((lock_request && !P06_DATA_TIMING) || lock_chain_q || (bus_valid && select_ack));

    always_ff @(posedge clk) begin
        if (reset) hlda <= 1'b0;
        else if (hlda) begin
            // A HOLD can be accepted at a free boundary immediately before
            // execution raises an implicit LOCK for a memory XCHG.  LOCK
            // owns the next transaction, so release a stale grant before it
            // can hide the locked request behind HLDA.
            if (!(hold_request && !P06_DATA_TIMING) || (lock_request && !P06_DATA_TIMING)) hlda <= 1'b0;
        end else if (hold_request && !P06_DATA_TIMING && !bus_lock && !data_active_q && !ack_active_q &&
                     (!bus_valid || ready)) hlda <= 1'b1;
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            ack_active_q <= 1'b0; ack_second_q <= 1'b0; lock_chain_q <= 1'b0;
            ack_response_valid <= 1'b0; ack_vector <= 8'd0; ack_canceled_q <= 1'b0;
        end else begin
            if (ack_response_valid && ack_response_ready) ack_response_valid <= 1'b0;
            if (ack_request && ack_request_ready && !P06_DATA_TIMING) begin
                ack_active_q <= 1'b1; ack_second_q <= 1'b0; ack_canceled_q <= 1'b0;
            end
            if (bus_valid && select_ack) begin
                lock_chain_q <= 1'b1;
                if (ready) begin
                    if (!ack_second_q) ack_second_q <= 1'b1;
                    else begin
                        ack_active_q <= 1'b0;
                        ack_vector <= data_in[7:0];
                        ack_response_valid <= !cancel_data && !ack_canceled_q;
                        if (cancel_data || ack_canceled_q) lock_chain_q <= 1'b0;
                    end
                end
            end
            // B-2 correction: link both INTA cycles to the first complete frame
            // word. The second half of an odd push is still the same word.
            if (data_complete && !address_q[0] && write_q && !io_q && !byte_q) lock_chain_q <= 1'b0;
            if (cancel_data) begin
                ack_response_valid <= 1'b0;
                if (ack_active_q) ack_canceled_q <= 1'b1;
                else lock_chain_q <= 1'b0;
            end
        end
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            owner_valid_q <= 1'b0; owner_q <= 2'd0;
        end else if (P06_DATA_TIMING && P06_SHARED_TIMING) begin
            if (p06_shared_release) owner_valid_q <= 1'b0;
            if (p06_code_issue) begin owner_valid_q <= 1'b1; owner_q <= 2'd0; end
            if (data_request && data_request_ready) begin
                owner_valid_q <= 1'b1; owner_q <= 2'd1;
            end
        end else if (bus_valid) begin
            owner_valid_q <= !ready;
            owner_q <= selected_owner;
        end
    end
    always_ff @(posedge clk) begin
        if (reset) begin
            data_active_q <= 1'b0; write_q <= 1'b0; second_q <= 1'b0; canceled_q <= 1'b0;
            byte_q <= 1'b0; io_q <= 1'b0;
            address_q <= 24'h000000; write_data_q <= 16'h0000; low_byte_q <= 8'h00;
            raw_data_response_valid <= 1'b0; raw_data_read_data <= 16'h0000;
        end else begin
            if (p06_response_fire) raw_data_response_valid <= 1'b0;
            if (cancel_data) begin
                raw_data_response_valid <= 1'b0;
                if (data_active_q) canceled_q <= 1'b1;
            end
            if (data_request && data_request_ready) begin
                data_active_q <= 1'b1; write_q <= data_write; second_q <= 1'b0;
                canceled_q <= 1'b0; address_q <= data_io ? {8'd0, data_address[15:0]} : data_address; write_data_q <= data_write_data;
                byte_q <= data_byte; io_q <= data_io;
            end
            if (data_complete) begin
                if (address_q[0] && !byte_q) begin
                    low_byte_q <= data_in[15:8];
                    address_q <= address_q + 24'd1;
                    second_q <= 1'b1;
                end else begin
                    data_active_q <= 1'b0;
                    raw_data_read_data <= byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :
                                      (second_q ? {data_in[7:0], low_byte_q} : data_in);
                    raw_data_response_valid <= !canceled_q && !cancel_data &&
                        !(P06_DATA_TIMING && p06_response_fire);
                    canceled_q <= 1'b0;
                end
            end
        end
    end
endmodule
