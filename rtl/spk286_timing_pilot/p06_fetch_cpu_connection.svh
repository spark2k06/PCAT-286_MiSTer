// Private qualified register/code-only CPU connection. Shared M3 clock.
    logic p06_fetch_boundary, p06_fetch_admission, p06_fetch_block;
    generate
        if (P06_FETCH_PILOT) begin : p06_code_bus
            logic scope_error;
            wire unsupported_bus = hold_request || bus_lock || memory_request || ack_request;
            wire queue_fill = fetch_response_valid && fetch_response_ready && execute_enable;
            wire queue_consume = queue_consume_valid && queue_consume_ready;
            wire [4:0] next_queue_count = {1'b0, queue_count} +
                (queue_fill ? {3'd0, fetch_response_count} : 5'd0) - 5'(queue_consume);
            assign p06_fetch_admission = !execute_enable || next_queue_count <= 5'd4;
            assign p06_fetch_block = scope_error || hold_request;
            // HOLD/LOCK/data/INTA are not timed yet. Stop BEFORE they can grant
            // ownership or produce architectural/device side effects in this pilot.
            always_ff @(posedge clk) begin
                if (reset || restart) scope_error <= 1'b0;
                else if (execute_enable && unsupported_bus) scope_error <= 1'b1;
            end
        end else begin : p06_code_maximum
            assign p06_fetch_admission = 1'b1;
            assign p06_fetch_block = 1'b0;
        end
        if (P06_REGISTER_PILOT) begin : p06_shared_clock
            assign p06_fetch_boundary = p06_register.cpu_boundary;
        end else begin : p06_no_historical_clock
            assign p06_fetch_boundary = 1'b0;
        end
    endgenerate
