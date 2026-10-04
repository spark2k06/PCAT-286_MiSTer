#!/usr/bin/env python3
"""Private M4 extension: qualified register retirement and dispatch share an edge.

This is a bounded instruction-unit pilot, not a decoded instruction queue.
All new parameters default to zero. The frozen M3/M4 builders are unchanged.
"""
from build_p06_fetch_cpu import build as build_fetch, replace_once
from build_p06_register_cpu import ROOT


def build(out):
    selected = build_fetch(out)
    top = selected["spk286.sv"].read_text()
    top = replace_once(top, "parameter bit P06_FETCH_PILOT = 1'b0",
                       "parameter bit P06_FETCH_PILOT = 1'b0,\n    parameter bit P06_IU_PILOT = 1'b0")
    # Declare before nested generate connections: Icarus otherwise creates an
    # implicit local net at the earlier duration-policy port expression.
    top = replace_once(top, "logic p06_admit, p06_block, p06_executor_permit, p06_result_pending;",
                       "logic p06_admit, p06_block, p06_executor_permit, p06_result_pending;\n    logic p06_relaunch_window, p06_relaunch;")
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_iu_connection.svh").read_text()
    top = replace_once(top, "    // A CS reload requires", connection + "\n    // A CS reload requires")
    top = replace_once(top, ".prefix_free(!context_active && !is_prefix)",
                       ".prefix_free((!context_active || p06_relaunch_window) && !is_prefix)")
    top = replace_once(top, "spk286_instruction_context instruction_context (",
                       "spk286_instruction_context #(.P06_IU_OVERLAP(P06_IU_PILOT)) instruction_context (")
    top = replace_once(top, ".complete(raw_retired || event_completed)",
                       ".complete(P06_IU_PILOT ? (p06_relaunch || (raw_retired && !micro_active) || event_completed) :\n                  (raw_retired || event_completed))")
    top = replace_once(top, ".ROM_DEPTH(spk286_microcode_pkg::MC_DEPTH)",
                       ".ROM_DEPTH(spk286_microcode_pkg::MC_DEPTH), .P06_IU_OVERLAP(P06_IU_PILOT)")
    top = replace_once(top, ") microsequencer (", ") microsequencer (\n        .p06_relaunch_window(p06_relaunch_window),")
    top = replace_once(top, ".USE_PARALLEL_SYSTEM_LIMIT(1'b1)",
                       ".USE_PARALLEL_SYSTEM_LIMIT(1'b1), .P06_IU_OVERLAP(P06_IU_PILOT)")
    top = replace_once(top, ") micro_executor (", ") micro_executor (\n        .p06_relaunch_window(p06_relaunch_window),")
    top = replace_once(top, "spk286_operand_decode operand_decode (",
                       "spk286_operand_decode #(.P06_IU_OVERLAP(P06_IU_PILOT)) operand_decode (\n        .p06_relaunch_window(p06_relaunch_window),")
    top = replace_once(top, ".instruction_start((prefix_accept || opcode_start) && !context_active)",
                       ".instruction_start((prefix_accept || opcode_start) && (!context_active || p06_relaunch))")
    selected["spk286.sv"].write_text(top, newline="\n")

    executor = selected["spk286_micro_executor.sv"].read_text()
    executor = replace_once(executor, "module spk286_micro_executor #(",
                            "module spk286_micro_executor #(\n    parameter bit P06_IU_OVERLAP = 1'b0,")
    executor = replace_once(executor, "input  logic start,",
                            "input  logic start,\n    input logic p06_relaunch_window,")
    executor = replace_once(executor, "operation_valid && !reset && !cancel && !start &&",
                            "operation_valid && !reset && !cancel &&\n                     (!start || (P06_IU_OVERLAP && p06_relaunch_window)) &&")
    selected["spk286_micro_executor.sv"].write_text(executor, newline="\n")

    seq = (ROOT / "vendor/spk286/rtl/spk286_microsequencer.sv").read_text()
    seq = replace_once(seq, "parameter integer ADDRESS_WIDTH = 2,",
                       "parameter bit P06_IU_OVERLAP = 1'b0,\n    parameter integer ADDRESS_WIDTH = 2,")
    seq = replace_once(seq, "input  logic                     start,",
                       "input  logic                     start,\n    input  logic                     p06_relaunch_window,")
    seq = replace_once(seq, "!active && !fault;",
                       "!fault && (!active ||\n        (P06_IU_OVERLAP && p06_relaunch_window && rom_valid && !rom_end &&\n         {1'b0, micro_pc} < DEPTH));")
    seq = replace_once(seq, "if (active) begin\n                if (rom_valid",
                       "if (P06_IU_OVERLAP && active && start && start_ready)\n                next_micro_pc = start_entry;\n            else if (active) begin\n                if (rom_valid")
    seq = replace_once(seq, "active <= 1'b0;\n                            retired <= 1'b1;",
                       "active <= 1'b0;\n                            retired <= 1'b1;\n                            if (P06_IU_OVERLAP && start && start_ready) begin\n                                micro_pc <= start_entry; micro_entry <= start_entry;\n                                if ({1'b0, start_entry} >= DEPTH) fault <= 1'b1;\n                                else active <= 1'b1;\n                            end")

    operand = (ROOT / "vendor/spk286/rtl/spk286_operand_decode.sv").read_text()
    operand = replace_once(operand, "module spk286_operand_decode (",
                           "module spk286_operand_decode #(parameter bit P06_IU_OVERLAP = 1'b0) (\n    input logic p06_relaunch_window,")
    # Only old DONE can survive START. Byte acceptance and FF reset still belong
    # to the new instruction; no combinational dependency on the new START.
    operand = replace_once(operand, "assign done = allowed && (state_q == RESOLVE || (state_q == COMPLETE && reuse_q));",
                           "assign done = enable && !reset && !cancel &&\n        (!start || (P06_IU_OVERLAP && p06_relaunch_window)) &&\n        (state_q == RESOLVE || (state_q == COMPLETE && reuse_q));")

    context = (ROOT / "vendor/spk286/rtl/spk286_instruction_context.sv").read_text()
    context = replace_once(context, "module spk286_instruction_context (",
                           "module spk286_instruction_context #(parameter bit P06_IU_OVERLAP = 1'b0) (")
    context = replace_once(context, "segment_index <= 0; repeat_kind <= 0; byte_count <= 0;",
                           "segment_index <= 0; repeat_kind <= 0; byte_count <= 0;\n            if (P06_IU_OVERLAP && complete && consume && !reset && !cancel) begin\n                active <= 1; byte_count <= 1;\n            end")
    for name, text in [("spk286_microsequencer.sv", seq), ("spk286_operand_decode.sv", operand),
                       ("spk286_instruction_context.sv", context)]:
        path = out / "private-rtl" / name
        path.write_text(text, newline="\n"); selected[name] = path
    return selected
