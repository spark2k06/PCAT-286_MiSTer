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
