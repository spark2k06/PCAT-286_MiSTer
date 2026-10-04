// Inserted into the private original fetch by build_p06_fetch_cpu.py.
// Physical READY capture uses the ORIGINAL result slot on every fabric edge.
// Only logical issue/publication and availability are temporally qualified.
    logic raw_response_valid;
    logic [15:0] raw_response_data, raw_response_ip;
    logic [1:0] raw_response_count;
    logic p06_admit, p06_can_issue;
    // Hierarchical timing diagnostics are intentionally pruned in MAX.
    /* verilator lint_off UNUSEDSIGNAL */
    logic p06_issue, p06_capture, p06_complete;
    /* verilator lint_on UNUSEDSIGNAL */
    assign p06_capture = !reset && active_q && ready;
    assign p06_can_issue = !suspend &&
        response_slot_available && !blocked && (restart_pending_q || request) && p06_admit;
    assign p06_issue = !reset && !restart && !active_q && p06_can_issue;
    generate
        if (P06_FETCH_TIMING) begin : p06_historical
            localparam logic [1:0] IDLE = 0, TS = 1, TC = 2, PUBLISHED = 3;
            logic [1:0] state_q;
            wire available = raw_response_valid || p06_capture;
            wire sample_tc = !reset && !restart && !canceled_q &&
                p06_cpu_boundary && state_q == TC;
            /* verilator lint_off UNUSEDSIGNAL */
            wire external_wait = sample_tc && !p06_board_ready;
            wire deadline_miss = sample_tc && p06_board_ready && !available;
            /* verilator lint_on UNUSEDSIGNAL */
            assign p06_complete = sample_tc && p06_board_ready && available;
            assign response_valid = !reset && !restart &&
                ((state_q == PUBLISHED && raw_response_valid) || p06_complete);
            // Same-edge physical READY at Tc has an explicit data/metadata bypass.
            // A poisoned data_in after an earlier READY cannot change retention.
            assign response_data = !raw_response_valid && p06_capture ?
                (request_count_q == 2 ? data_in :
                    (address_q[0] ? {8'd0, data_in[15:8]} : {8'd0, data_in[7:0]})) : raw_response_data;
            assign response_ip = !raw_response_valid && p06_capture ? request_ip_q : raw_response_ip;
            assign response_count = !raw_response_valid && p06_capture ? request_count_q : raw_response_count;
            assign p06_admit = !reset && !restart && p06_cpu_boundary && p06_admission_enable &&
                (state_q == IDLE || ((p06_complete || state_q == PUBLISHED) && response_fire));
            always_ff @(posedge clk) begin
                if (reset || restart) state_q <= IDLE;
                else begin
                    if (state_q == TS && p06_cpu_boundary) state_q <= TC;
                    if (p06_complete) state_q <= response_ready ? IDLE : PUBLISHED;
                    if (state_q == PUBLISHED && response_fire) state_q <= IDLE;
                    // No Ti bubble when a reserved next fetch is admitted at Tc.
                    if (p06_issue) state_q <= TS;
                end
            end
        end else begin : p06_maximum
            assign response_valid = raw_response_valid;
            assign response_data = raw_response_data;
            assign response_ip = raw_response_ip;
            assign response_count = raw_response_count;
            assign p06_admit = 1'b1;
            assign p06_complete = 1'b0;
        end
    endgenerate
