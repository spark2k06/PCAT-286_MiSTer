// Private full-CPU connection. Inserted once by build_p06_register_cpu.py.
// No production QIP or second execution engine. MAX elaborates constant bypasses.
    logic [15:0] p06_cursor_ip;
    logic p06_admit, p06_block, p06_executor_permit, p06_result_pending;
    generate
        if (P06_REGISTER_PILOT) begin : p06_register
            logic cpu_boundary, active, permit, start_ready;
            logic metadata_error, timing_error;
            logic scope_error;
            logic [2:0] scope_reason;
            logic opcode_known, has_modrm, bad_modrm;
            logic [3:0] form;
            logic [7:0] elapsed, scheduled;
            /* verilator lint_off UNUSEDSIGNAL */
            logic phase_enable, phase_two, dependency_blocked, consumer_blocked;
            logic metadata_qualified;
            logic [5:0] minimum_clocks;
            /* verilator lint_on UNUSEDSIGNAL */
            // Scope tags use the existing decoder's head and retained opcode.
            // They do not choose functional entry points, operands or results.
            always_comb begin
                opcode_known = 1'b1;
                form = 4'd0;
                case (queue_consume_data)
                    8'h01, 8'h03: form = 4'd0;
                    8'h31, 8'h33: form = 4'd1;
                    8'h39, 8'h3B: form = 4'd2;
                    8'h05, 8'h81, 8'h83: form = 4'd3;
                    8'h35: form = 4'd4;
                    default: opcode_known = 1'b0;
                endcase
            end
            // 81/83 ADD and XOR both cost three clocks. Validate the extension
            // before consuming ModR/M, so other groups/memory cannot issue work.
            assign has_modrm = opcode_q != 8'h05 && opcode_q != 8'h35;
            assign bad_modrm = micro_active && has_modrm && !operand_context_valid &&
                queue_consume_valid && (queue_consume_data[7:6] != 2'b11 ||
                ((opcode_q == 8'h81 || opcode_q == 8'h83) &&
                 queue_consume_data[5:3] != 3'd0 && queue_consume_data[5:3] != 3'd6));
            assign p06_block = scope_error || bad_modrm || protected_msw[0] || event_active;
            assign p06_admit = start_ready && opcode_known && !is_prefix && !p06_block;
            assign p06_executor_permit = !p06_block && (!p06_result_pending || permit);
            // The event unit already owns the saved start IP. The register IP
            // remains the private byte cursor, including internal fault/frame uses.
            assign debug_ip = active ? debug_instruction_ip : p06_cursor_ip;

            p06_clock clock_policy (.clk(clk), .reset(reset),
                .phase_enable(phase_enable), .phase_two(phase_two), .cpu_enable(cpu_boundary));
            p06_instruction_duration duration_policy (
                .clk(clk), .reset(reset), .cancel(semantic_cancel), .cpu_boundary(cpu_boundary),
                .start_valid(opcode_start), .start_ready(start_ready), .instruction_form(form),
                .real_mode(!protected_msw[0]), .prefix_free(!context_active && !is_prefix),
                .taken(1'b0), .branch_outcome_known(1'b0), .target_length_known(1'b0),
                .next_length(4'd0), .operand_odd(1'b0), .ea_base_index_disp(1'b0),
                .read_wait_event(1'b0), .functional_done(p06_result_pending),
                .dependencies_ready(p06_result_pending),
                .retire_ready(execution_allowed && operation_valid), .retire_enable(permit),
                .dependency_blocked(dependency_blocked), .consumer_blocked(consumer_blocked), .metadata_qualified(metadata_qualified),
                .metadata_error(metadata_error), .timing_error(timing_error), .active(active),
                .minimum_clocks(minimum_clocks), .elapsed_clocks(elapsed), .scheduled_clocks(scheduled));

            // Diagnostic, not #UD: a private pilot has no timed event/PM coverage.
            // Never fall back to zero-cost execution for an unqualified form.
            always_ff @(posedge clk) begin
                if (reset || restart) begin scope_error <= 0; scope_reason <= 0; end
                else if (execute_enable && !scope_error) begin
                    if (protected_msw[0]) begin scope_error <= 1; scope_reason <= 3; end
                    else if (event_active || event_request) begin scope_error <= 1; scope_reason <= 4; end
                    else if (bad_modrm) begin scope_error <= 1; scope_reason <= 2; end
                    else if (metadata_error || timing_error ||
                        (!micro_active && !raw_retired && !event_completed &&
                         queue_consume_valid && (!opcode_known || is_prefix))) begin
                        scope_error <= 1; scope_reason <= 1;
                    end
                end
            end
            // These are read by the private directed benches/trace, not ports.
            /* verilator lint_off UNUSEDSIGNAL */
            wire [19:0] trace_policy = {scope_error, scope_reason, elapsed, scheduled};
            /* verilator lint_on UNUSEDSIGNAL */
        end else begin : p06_maximum
            assign p06_admit = 1'b1;
            assign p06_block = 1'b0;
            assign p06_executor_permit = 1'b1;
            assign debug_ip = p06_cursor_ip;
        end
    endgenerate
