// Private M5/IU01 register handoff. No extra registers, queue, PLL or engine.
    generate
        if (P06_IU_PILOT && P06_REGISTER_PILOT && P06_FETCH_PILOT) begin : p06_iu
            logic old_form_ready;
            // Pending RI is captured only after the final immediate. Pending
            // RR additionally requires the retained decoder's RESOLVE state.
            // These state predicates do not use DONE/START combinational gates.
            assign old_form_ready = opcode_q == 8'h05 || opcode_q == 8'h35 ||
                opcode_q == 8'h81 || opcode_q == 8'h83 ||
                (operand_context_valid && operand_register_direct &&
                 operand_decode.state_q == 3'd3);
            // Independent of START: old retained operands and the old duration
            // permit remain visible while services clear for the new opcode.
            // Events/shadows require serialization; their existing owner decides
            // entry after retirement. The private pilot stops before event work.
            assign p06_relaunch_window = p06_register.permit && p06_result_pending && old_form_ready &&
                operation_valid && execution_allowed && !semantic_cancel &&
                !event_active && !event_completed &&
                !nmi && !debug_nmi_pending && !(intr && debug_flags[9]) &&
                !debug_flags[8] && !debug_sti_shadow && !unused_ss_shadow;
            assign p06_relaunch = p06_relaunch_window && micro_active && opcode_start;
        end else begin : p06_iu_disabled
            assign p06_relaunch_window = 1'b0;
            assign p06_relaunch = 1'b0;
        end
    endgenerate
