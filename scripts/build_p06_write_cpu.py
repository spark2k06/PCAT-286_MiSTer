#!/usr/bin/env python3
"""Private M6f serialized A3, built from hash-pinned M6e generated sources.

The original WRITE_RM16/operand/BIU service completes before the retained END.
Only retirement is qualified there; this is not historical write-buffer/EU
overlap, exact native issue phasing or a production selector change.
"""
import argparse
import json
from pathlib import Path
from build_p06_odd_read_cpu import build as build_odd
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha

M6E_RECEIPT_SHA256 = "42a54266c3d49bca026f26d9789db788abcfcb7211d5caa304a8767bc628da92"


def replace_count(text, old, new, expected):
    assert text.count(old) == expected, (old, text.count(old), expected)
    return text.replace(old, new)


def build(out):
    receipt_path = ROOT / "docs/evidence/p06-core-odd-read-20261004/receipt.json"
    assert sha(receipt_path) == M6E_RECEIPT_SHA256, "Frozen M6e receipt changed"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "P06_PRIVATE_ODD_READ_CPU_PASS"
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / name) == expected, name
    selected = build_odd(out)
    assert len(selected) == 8 and set(selected) == set(receipt["generated_cpu_sha256"])
    for name, path in selected.items():
        assert sha(path) == receipt["generated_cpu_sha256"][name], name

    biu = selected["spk286_biu.sv"].read_text()
    biu = replace_once(biu, "parameter bit P06_ODD_READ_TIMING = 1'b0)",
        "parameter bit P06_ODD_READ_TIMING = 1'b0, parameter bit P06_WRITE_TIMING = 1'b0)")
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_write_biu_connection.svh").read_text()
    biu = replace_once(biu, "// Private M6e normalized READ adapter:",
        connection + "\n// Private M6e normalized READ adapter:")
    # Both constant generate alternatives remain exact READ-only bypasses
    # when WRITE_TIMING=0. Byte WRITE and I/O stay outside M6f.
    biu = replace_count(biu, "data_write || data_io ||",
        "(data_write && (!P06_WRITE_TIMING || data_byte)) || data_io ||", 2)
    biu = replace_count(biu,
        "assign p06_read_wait_event = !reset && !cancel_data && !canceled_q &&",
        "assign p06_read_wait_event = p06_read_cycle && !reset && !cancel_data && !canceled_q &&", 2)
    selected["spk286_biu.sv"].write_text(biu, newline="\n")

    top = selected["spk286.sv"].read_text()
    top = replace_once(top, "parameter bit P06_ODD_READ_PILOT = 1'b0)",
        "parameter bit P06_ODD_READ_PILOT = 1'b0,\n    parameter bit P06_WRITE_PILOT = 1'b0)")
    top = replace_once(top, "    assign p06_result_pending = p06_register_result_pending || p06_read_result_pending;",
        "    logic p06_timed_write, p06_timed_data, p06_write_end_pending;\n" +
        "    assign p06_timed_write = P06_WRITE_PILOT && micro_active && !event_active && opcode_q == 8'hA3;\n" +
        "    assign p06_timed_data = p06_timed_read || p06_timed_write;\n" +
        "    // END is reachable only after the original operand WRITE response.\n" +
        "    // Its retained valid-ROM predicate never depends on execution enable.\n" +
        "    assign p06_write_end_pending = p06_timed_write && micro_valid && micro_end;\n" +
        "    assign p06_result_pending = p06_register_result_pending || p06_read_result_pending || p06_write_end_pending;")
    top = replace_once(top, "    generate\n        if (P06_ODD_READ_PILOT &&",
        "    generate\n" +
        "        if (P06_WRITE_PILOT && !P06_MEMORY_PILOT) begin : p06_invalid_write_configuration\n" +
        "            initial $fatal(1, \"M6f WRITE requires MEMORY timing\");\n" +
        "        end\n        if (P06_ODD_READ_PILOT &&")
    top = replace_once(top, "8'hA1: begin form = 4'd8; opcode_known = P06_MEMORY_PILOT; end",
        "8'hA1: begin form = 4'd8; opcode_known = P06_MEMORY_PILOT; end\n" +
        "                    8'hA3: begin form = 4'd9; opcode_known = P06_WRITE_PILOT; end")
    top = replace_once(top, "(!P06_MEMORY_PILOT || opcode_q != 8'hA1);",
        "(!P06_MEMORY_PILOT || opcode_q != 8'hA1) && (!P06_WRITE_PILOT || opcode_q != 8'hA3);")
    top = replace_once(top, "#(.P06_LATE_ALIGNMENT(P06_ODD_READ_PILOT)) duration_policy",
        "#(.P06_LATE_ALIGNMENT(P06_ODD_READ_PILOT), .P06_WRITE_ALIGNMENT(P06_WRITE_PILOT)) duration_policy")
    top = replace_once(top, ".alignment_event(p06_timed_read && p06_alignment_event)",
        ".alignment_event(p06_timed_data && p06_alignment_event)")
    top = replace_once(top, ".retire_ready(execution_allowed && operation_valid)",
        ".retire_ready(execution_allowed && (operation_valid || p06_write_end_pending))")
    top = replace_once(top,
        "!P06_MEMORY_PILOT || !p06_timed_read ||\n                    memory_write || memory_byte || io_transfer ||",
        "!P06_MEMORY_PILOT || !p06_timed_data ||\n" +
        "                    (memory_write != p06_timed_write) || memory_byte || io_transfer ||")
    top = replace_once(top, ".P06_ODD_READ_TIMING(P06_ODD_READ_PILOT)) biu",
        ".P06_ODD_READ_TIMING(P06_ODD_READ_PILOT), .P06_WRITE_TIMING(P06_WRITE_PILOT)) biu")
    top = replace_once(top, ".data_request(memory_request && (!P06_FETCH_PILOT || (P06_MEMORY_PILOT && p06_timed_read)))",
        ".data_request(memory_request && (!P06_FETCH_PILOT || (P06_MEMORY_PILOT && p06_timed_data)) &&\n" +
        "            (!P06_WRITE_PILOT || memory_write == p06_timed_write))")
    selected["spk286.sv"].write_text(top, newline="\n")

    policy = selected["p06_instruction_duration.sv"].read_text()
    policy = replace_once(policy, "parameter bit P06_LATE_ALIGNMENT = 1'b0",
        "parameter bit P06_LATE_ALIGNMENT = 1'b0, parameter bit P06_WRITE_ALIGNMENT = 1'b0")
    policy = replace_once(policy, "            logic active_q, permits_wait_q;",
        "            logic active_q, permits_wait_q;\n" +
        "            logic permits_alignment_q;\n" +
        "            wire permits_alignment = P06_WRITE_ALIGNMENT ? permits_alignment_q : permits_wait_q;")
    policy = replace_once(policy,
        "wire alignment_increment = P06_LATE_ALIGNMENT && active_q && cpu_boundary && permits_wait_q && alignment_event;",
        "wire alignment_increment = P06_LATE_ALIGNMENT && active_q && cpu_boundary && permits_alignment && alignment_event;")
    policy = replace_once(policy,
        "wire event_bad = (read_wait_event || (P06_LATE_ALIGNMENT && alignment_event)) &&\n" +
        "                (!active_q || !cpu_boundary || !permits_wait_q);",
        "wire event_bad = P06_WRITE_ALIGNMENT ?\n" +
        "                ((read_wait_event && (!active_q || !cpu_boundary || !permits_wait_q)) ||\n" +
        "                 (P06_LATE_ALIGNMENT && alignment_event && (!active_q || !cpu_boundary || !permits_alignment))) :\n" +
        "                ((read_wait_event || (P06_LATE_ALIGNMENT && alignment_event)) &&\n" +
        "                 (!active_q || !cpu_boundary || !permits_wait_q));")
    policy = replace_once(policy, "            always_ff @(posedge clk) begin\n                if (reset) begin",
        "            // One control bit distinguishes alignment eligibility from\n" +
        "            // READ-wait eligibility. It is absent when WRITE is disabled.\n" +
        "            if (P06_WRITE_ALIGNMENT) begin : write_alignment\n" +
        "                always_ff @(posedge clk) begin\n" +
        "                    if (reset || cancel) permits_alignment_q <= 1'b0;\n" +
        "                    else if (start_fire) permits_alignment_q <= memory_form;\n" +
        "                end\n" +
        "            end else begin : read_alignment\n" +
        "                assign permits_alignment_q = 1'b0;\n" +
        "            end\n\n            always_ff @(posedge clk) begin\n                if (reset) begin")
    selected["p06_instruction_duration.sv"].write_text(policy, newline="\n")
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    selected = build(out)
    (out / "prepared.json").write_text(json.dumps({
        "ancestor_receipt_sha256": M6E_RECEIPT_SHA256,
        "generated_cpu_sha256": {name: sha(path) for name, path in selected.items()},
    }, indent=2) + "\n")
    print(f"M6F_WRITE_PREPARED sources={len(selected)}")
