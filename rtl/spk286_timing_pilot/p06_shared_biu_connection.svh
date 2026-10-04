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
                    (data_abort && (!data_active_q || data_complete))));
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
