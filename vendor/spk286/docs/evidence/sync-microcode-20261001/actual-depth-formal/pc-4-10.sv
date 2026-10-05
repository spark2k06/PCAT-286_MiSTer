module miter #(parameter ADDRESS_WIDTH=4, ROM_DEPTH=10) (
input reset, cancel, enable, start, rom_valid, rom_end,
input operation_done, operation_retire, branch_request, branch_target_valid,
input active, retired, fault,
input [ADDRESS_WIDTH-1:0] micro_pc, micro_entry, start_entry, branch_target,
output mismatch
);
localparam [ADDRESS_WIDTH:0] DEPTH=(ADDRESS_WIDTH+1)'(ROM_DEPTH);
wire start_ready=enable && !reset && !cancel && !active && !fault;
reg expected_active, expected_retired, expected_fault;
reg [ADDRESS_WIDTH-1:0] expected_micro_pc, expected_micro_entry, next_micro_pc;
    always_comb begin
        expected_active = active;
        expected_micro_pc = micro_pc;
        expected_micro_entry = micro_entry;
        expected_retired = retired;
        expected_fault = fault;

        if (reset || cancel) begin
            expected_active = 1'b0;
            expected_micro_pc = '0;
            expected_micro_entry = '0;
            expected_retired = 1'b0;
            expected_fault = 1'b0;
        end else begin
            // A pulse clears even when execution is paused after retirement.
            expected_retired = 1'b0;
            if (enable) begin
                if (active) begin
                    if (!rom_valid || {1'b0, micro_pc} >= DEPTH) begin
                        expected_active = 1'b0;
                        expected_fault = 1'b1;
                    end else if (operation_done) begin
                        if (rom_end || operation_retire) begin
                            expected_active = 1'b0;
                            expected_retired = 1'b1;
                        end else if (branch_request) begin
                            if (!branch_target_valid || {1'b0, branch_target} >= DEPTH) begin
                                expected_active = 1'b0;
                                expected_fault = 1'b1;
                            end else begin
                                expected_micro_pc = branch_target;
                            end
                        end else if ({1'b0, micro_pc} + 1'b1 >= DEPTH) begin
                            // Never wrap or silently fall off an entry lacking END.
                            expected_active = 1'b0;
                            expected_fault = 1'b1;
                        end else begin
                            expected_micro_pc = micro_pc + 1'b1;
                        end
                    end
                end else if (start && start_ready) begin
                    expected_micro_pc = start_entry;
                    expected_micro_entry = start_entry;
                    if ({1'b0, start_entry} >= DEPTH)
                        expected_fault = 1'b1;
                    else
                        expected_active = 1'b1;
                end
            end
        end
    end
    // The synchronous ROM samples the same address that micro_pc takes at
    // this edge. Stalls, terminal operations and invalid branches hold it;
    // no speculative micro-operation or extra execution cycle is introduced.
    always_comb begin
        next_micro_pc = micro_pc;
        if (reset || cancel)
            next_micro_pc = '0;
        else if (enable) begin
            if (active) begin
                if (rom_valid && {1'b0, micro_pc} < DEPTH && operation_done &&
                    !rom_end && !operation_retire) begin
                    if (branch_request) begin
                        if (branch_target_valid && {1'b0, branch_target} < DEPTH)
                            next_micro_pc = branch_target;
                    end else if ({1'b0, micro_pc} + 1'b1 < DEPTH)
                        next_micro_pc = micro_pc + 1'b1;
                end
            end else if (start && start_ready)
                next_micro_pc = start_entry;
        end
    end

assign mismatch=expected_micro_pc != next_micro_pc;
endmodule
