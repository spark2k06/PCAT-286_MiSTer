#!/usr/bin/env python3
"""Private M6g bounded 81 36 disp16 imm16 XOR word timing adapter.

Starts from frozen M6f, preserving the functional READ/TMP0/ALU/TMP2/WRITE/
COMMIT_FLAGS path. The original retained decoder qualifies the memory form;
the RI three-clock admission is corrected once to the seven-clock memory row.
This serializes final FLAGS/retirement. It does not validate write-buffer EU
overlap, exact native issue phasing, LOCK or arbitrary memory instructions.
"""
import argparse
import json
from pathlib import Path
from build_p06_write_cpu import build as build_write
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha

# Normal acceptance must fail while the preceding milestone is unfinished.
# Development explicitly checks the fixed candidate inputs/output hashes below.
M6F_RECEIPT_SHA256 = "89e91b391a0ef829290594099cf9ce03a9fd666ba1028c4b7f160e356eacbb65"
M6F_SOURCES_SHA256 = {
    "scripts/build_p06_write_cpu.py": "0f717012afaffe9260534fd3f3b21e12d5f69b7c555b72bbf0b9c927fb2b5fa4",
    "rtl/spk286_timing_pilot/p06_write_biu_connection.svh": "6c1c2a8f1312a9bf46144d65a8ab5d72cc2c392e4b78ae71da9db29b05cb737d",
    "scripts/check_p06_write_components.py": "85e8fe8267e9b722a6bbe0612872079171ef8765a93cad407d9f07def3cd2e7d",
}
M6F_GENERATED_SHA256 = {
    "p06_instruction_duration.sv": "9c86a8432ea446d62805d998535a4192ab768e8fc199400b4cea18a5bebb738f",
    "spk286_biu.sv": "1db489c22f8c98c18cf3a1f4c103ff02d6f19edd3aa313c5750935a0f1b614f3",
    "spk286_fetch.sv": "79fe3403f71752a21347bdcd3e3dea8d5df38206bc2fdd6a90a8d9b4645b24ef",
    "spk286_instruction_context.sv": "9fe734ec2ac54e08ddef9d91ea62d6d823cae119dea8d492016a365d93eaf75d",
    "spk286_micro_executor.sv": "f928e8c3b2aad54c092e6716de6e9102e813f56ede18c07e58191edd58acb2ca",
    "spk286_microsequencer.sv": "88a67b3296c4d17cec2ba832ee39df4f0aff21cf09e7295b52fe12c954c30cb1",
    "spk286_operand_decode.sv": "a7c7f5743575c8c10e80f499be70462608134e618709cfc1217a2505a7b46b4e",
    "spk286.sv": "dc35c546b61f68c0c093c8dec92f85aac5f61e28f74866babf1e0103e1162a8d",
}


def ancestor(out, development=False):
    """Reconstruct M6f and validate it before patching any generated copies."""
    if development:
        expected_sources = M6F_SOURCES_SHA256
        expected_generated = M6F_GENERATED_SHA256
    else:
        if M6F_RECEIPT_SHA256 == "TBD":
            raise RuntimeError("M6f receipt is not frozen; use explicit --development for non-accepted preparation")
        receipt_path = ROOT / "docs/evidence/p06-core-write-20261004/receipt.json"
        assert sha(receipt_path) == M6F_RECEIPT_SHA256, "Frozen M6f receipt changed"
        receipt = json.loads(receipt_path.read_text())
        assert receipt["status"] == "P06_PRIVATE_WRITE_CPU_PASS"
        expected_sources = receipt["sources_sha256"]
        expected_generated = receipt["generated_cpu_sha256"]
    for name, expected in expected_sources.items():
        assert sha(ROOT / name) == expected, name
    selected = build_write(out)
    assert len(selected) == 8 and set(selected) == set(expected_generated)
    for name, path in selected.items():
        assert sha(path) == expected_generated[name], name
    return selected


def build(out, development=False):
    selected = ancestor(out, development)
    top = selected["spk286.sv"].read_text()
    top = replace_once(top, "parameter bit P06_WRITE_PILOT = 1'b0)",
        "parameter bit P06_WRITE_PILOT = 1'b0,\n    parameter bit P06_RMW_PILOT = 1'b0)")
    top = replace_once(top, "    assign p06_timed_data = p06_timed_read || p06_timed_write;",
        "    logic p06_timed_rmw, p06_rmw_result_pending;\n" +
        "    logic p06_rmw_read_phase, p06_rmw_write_phase, p06_expected_write, p06_qualified_data;\n" +
        "    // Retained original ModR/M fields qualify 81 /6, ModR/M 36h. They\n" +
        "    // may become valid between CPU boundaries, before EA resolution.\n" +
        "    // This level never depends on request, DONE or execution enable.\n" +
        "    assign p06_timed_rmw = P06_RMW_PILOT && micro_active && !event_active &&\n" +
        "        opcode_q == 8'h81 && operand_context_valid && operand_mode == 2'b00 &&\n" +
        "        operand_reg == 3'd6 && operand_rm == 3'd6;\n" +
        "    assign p06_rmw_read_phase = p06_timed_rmw && micro_word == spk286_microcode_pkg::MC_READ_RM16;\n" +
        "    assign p06_rmw_write_phase = p06_timed_rmw && micro_word == spk286_microcode_pkg::MC_WRITE_RESULT_RM16;\n" +
        "    assign p06_expected_write = p06_timed_write || p06_rmw_write_phase;\n" +
        "    assign p06_timed_data = p06_timed_read || p06_timed_write || p06_timed_rmw;\n" +
        "    assign p06_qualified_data = p06_timed_data && (!p06_timed_rmw || p06_rmw_read_phase || p06_rmw_write_phase);")
    top = replace_once(top,
        "p06_register_result_pending || p06_read_result_pending || p06_write_end_pending;",
        "p06_register_result_pending || p06_read_result_pending || p06_write_end_pending || p06_rmw_result_pending;")
    top = replace_once(top, "    generate\n        if (P06_WRITE_PILOT &&",
        "    generate\n" +
        "        if (P06_RMW_PILOT && !P06_WRITE_PILOT) begin : p06_invalid_rmw_configuration\n" +
        "            initial $fatal(1, \"M6g RMW requires WRITE timing\");\n" +
        "        end\n        if (P06_WRITE_PILOT &&")
    top = replace_once(top,
        "queue_consume_valid && (queue_consume_data[7:6] != 2'b11 ||",
        "queue_consume_valid && !(P06_RMW_PILOT && opcode_q == 8'h81 && queue_consume_data == 8'h36) &&\n" +
        "                (queue_consume_data[7:6] != 2'b11 ||")
    top = replace_once(top,
        "#(.P06_LATE_ALIGNMENT(P06_ODD_READ_PILOT), .P06_WRITE_ALIGNMENT(P06_WRITE_PILOT)) duration_policy",
        "#(.P06_LATE_ALIGNMENT(P06_ODD_READ_PILOT), .P06_WRITE_ALIGNMENT(P06_WRITE_PILOT),\n" +
        "                .P06_RMW_TIMING(P06_RMW_PILOT)) duration_policy")
    top = replace_once(top, ".read_wait_event(p06_timed_read && p06_read_wait_event)",
        ".rmw_form_valid(p06_timed_rmw),\n                .read_wait_event((p06_timed_read || p06_timed_rmw) && p06_read_wait_event)")
    top = replace_once(top, "!P06_MEMORY_PILOT || !p06_timed_data ||\n                    (memory_write != p06_timed_write)",
        "!P06_MEMORY_PILOT || !p06_qualified_data ||\n                    (memory_write != p06_expected_write)")
    top = replace_once(top, "opcode_q == 8'h81 || opcode_q == 8'h83 ||\n                (operand_context_valid",
        "(opcode_q == 8'h81 && !p06_timed_rmw) || opcode_q == 8'h83 ||\n                (operand_context_valid")
    top = replace_once(top,
        ".data_request(memory_request && (!P06_FETCH_PILOT || (P06_MEMORY_PILOT && p06_timed_data)) &&\n            (!P06_WRITE_PILOT || memory_write == p06_timed_write))",
        ".data_request(memory_request && (!P06_FETCH_PILOT || (P06_MEMORY_PILOT && p06_qualified_data)) &&\n            (!P06_WRITE_PILOT || memory_write == p06_expected_write))")
    top = replace_once(top, ".P06_MEMORY_TIMING(P06_MEMORY_PILOT)\n    ) micro_executor",
        ".P06_MEMORY_TIMING(P06_MEMORY_PILOT), .P06_RMW_TIMING(P06_RMW_PILOT)\n    ) micro_executor")
    top = replace_once(top, ".p06_moffs_read(p06_timed_read), .p06_memory_result_pending(p06_read_result_pending),",
        ".p06_moffs_read(p06_timed_read), .p06_memory_result_pending(p06_read_result_pending),\n" +
        "        .p06_rmw_form(p06_timed_rmw), .p06_rmw_result_pending(p06_rmw_result_pending),")
    selected["spk286.sv"].write_text(top, newline="\n")

    executor = selected["spk286_micro_executor.sv"].read_text()
    executor = replace_once(executor, "parameter bit P06_MEMORY_TIMING = 1'b0,",
        "parameter bit P06_MEMORY_TIMING = 1'b0, parameter bit P06_RMW_TIMING = 1'b0,")
    executor = replace_once(executor, "    input logic p06_moffs_read,",
        "    input logic p06_moffs_read, p06_rmw_form,")
    executor = replace_once(executor, "    output logic p06_memory_result_pending,",
        "    output logic p06_memory_result_pending, p06_rmw_result_pending,")
    executor = replace_once(executor,
        "    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word);",
        "    // FLAGS and final retirement share the existing real COMMIT_FLAGS\n" +
        "    // edge, after WRITE response disposed TMP2. Only the END tail is\n" +
        "    // skipped. Pending must be visible while ALLOWED is gated.\n" +
        "    assign p06_rmw_result_pending = P06_RMW_TIMING && p06_rmw_form &&\n" +
        "        operation == spk286_microcode_pkg::MC_COMMIT_FLAGS && flags_valid_q && result_disposed_q;\n" +
        "    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word) ||\n" +
        "        (P06_RMW_TIMING && p06_rmw_form && commit_flags);")
    selected["spk286_micro_executor.sv"].write_text(executor, newline="\n")

    policy = selected["p06_instruction_duration.sv"].read_text()
    policy = replace_once(policy, "parameter bit P06_WRITE_ALIGNMENT = 1'b0",
        "parameter bit P06_WRITE_ALIGNMENT = 1'b0, parameter bit P06_RMW_TIMING = 1'b0")
    policy = replace_once(policy, "    output logic [7:0] elapsed_clocks, scheduled_clocks\n",
        "    output logic [7:0] elapsed_clocks, scheduled_clocks,\n" +
        "    /* verilator lint_off UNUSEDSIGNAL */\n" +
        "    input logic rmw_form_valid\n    /* verilator lint_on UNUSEDSIGNAL */\n")
    policy = replace_once(policy, "            wire [8:0] extended_budget =",
        "            // ModR/M is retained metadata, not an off-boundary event.\n" +
        "            // RI admission costs three clocks. 81 /6, ModR/M 36h upgrades\n" +
        "            // once to the seven-clock XOR_MI row. The existing READ\n" +
        "            // permit flag marks qualification; no new register.\n" +
        "            wire form_increment = P06_RMW_TIMING && !reset && !cancel && active_q && cpu_boundary &&\n" +
        "                rmw_form_valid && !permits_wait_q;\n" +
        "            wire [8:0] extended_budget =")
    policy = replace_once(policy, "(alignment_increment ? 9'd2 : 9'd0);",
        "(alignment_increment ? 9'd2 : 9'd0) + (form_increment ? 9'd4 : 9'd0);")
    policy = replace_once(policy, "                    else if (start_fire) permits_alignment_q <= memory_form;",
        "                    else if (start_fire) permits_alignment_q <= memory_form;\n" +
        "                    else if (form_increment) permits_alignment_q <= 1'b1;")
    policy = replace_once(policy,
        "if ((wait_increment || alignment_increment) && !overflow) budget_q <= extended_budget[7:0];",
        "if ((wait_increment || alignment_increment || form_increment) && !overflow) budget_q <= extended_budget[7:0];\n" +
        "                        if (form_increment) permits_wait_q <= 1'b1;")
    # Keep one body, with a constant bypass and an internal diagnostic alias.
    # An unchanged register count/equivalence, not an ABC gate-count integer,
    # establishes the disabled adapter's functional/state preservation.
    policy = replace_once(policy, "    generate\n", "    /* verilator lint_off UNUSEDSIGNAL */\n" +
        "    wire p06_form_increment;\n    /* verilator lint_on UNUSEDSIGNAL */\n    generate\n")
    policy = replace_once(policy, "                rmw_form_valid && !permits_wait_q;\n",
        "                rmw_form_valid && !permits_wait_q;\n            assign p06_form_increment = form_increment;\n")
    policy = replace_once(policy, "        end else begin : maximum\n",
        "        end else begin : maximum\n            assign p06_form_increment = 1'b0;\n")
    selected["p06_instruction_duration.sv"].write_text(policy, newline="\n")
    # RMW introduces no BIU states, payload slots, queues or bus shortcuts.
    assert sha(selected["spk286_biu.sv"]) == M6F_GENERATED_SHA256["spk286_biu.sv"]
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    selected = build(out, args.development)
    (out / "prepared.json").write_text(json.dumps({
        "status": "DEV_NOT_ACCEPTED" if args.development else "PINNED_PREPARED",
        "ancestor_receipt_sha256": M6F_RECEIPT_SHA256,
        "generated_cpu_sha256": {name: sha(path) for name, path in selected.items()},
    }, indent=2) + "\n")
    print(f"M6G_RMW_PREPARED sources={len(selected)} development={int(args.development)}")
