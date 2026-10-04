// Private M6a byte/even-word memory READ timing. No extra data/address buffer.
    logic raw_data_response_valid;
    logic [15:0] raw_data_read_data;
    logic p06_admit, p06_response_fire;
    /* verilator lint_off UNUSEDSIGNAL */
    logic p06_capture, p06_complete;
    /* verilator lint_on UNUSEDSIGNAL */
    assign p06_capture = data_complete;
    assign p06_response_fire = data_response_valid && data_response_ready;
    generate
        if (P06_DATA_TIMING) begin : p06_data
            localparam logic [1:0] IDLE = 0, TS = 1, TC = 2, PUBLISHED = 3;
            logic [1:0] state_q;
            wire unsupported_data = data_request &&
                (data_write || data_io || (!data_byte && data_address[0]));
            wire unsupported_bus = code_valid || ack_request || hold_request || lock_request;
            wire scope_block = p06_scope_error || unsupported_data || unsupported_bus;
            wire available = raw_data_response_valid || p06_capture;
            wire sample_tc = !reset && !cancel_data && !canceled_q &&
                !scope_block && p06_cpu_boundary && state_q == TC;
            /* verilator lint_off UNUSEDSIGNAL */
            wire external_wait = sample_tc && !p06_board_ready;
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
                p06_cpu_boundary && state_q == IDLE;
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
        end else begin : p06_data_maximum
            assign p06_scope_error = 1'b0;
            assign p06_complete = 1'b0;
            assign p06_admit = 1'b1;
            assign data_response_valid = raw_data_response_valid;
            assign data_read_data = raw_data_read_data;
        end
    endgenerate
