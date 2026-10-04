#!/usr/bin/env python3
"""Build private M6e odd-word A1 on the frozen M6c CPU (commit 61bdfce).

No ancestor, production selector or payload storage changes. The original
first-byte assembly/physical READY capture is reused; the second physical READ
starts after first logical Tc. This is a normalized backend adapter, not a
claim about native 286 issue phase, EU lookahead or externally accurate pins.
The late known alignment correction has its own event; it is not a READ wait.
"""
import argparse
import json
from pathlib import Path
from build_p06_memory_cpu import build as build_memory
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha

M6C_RECEIPT_SHA256 = "59e8738bc24251b0a8ad5670435fd3987394eba858cd130943934b3fe5384f65"


def build(out):
    receipt_path = ROOT / "docs/evidence/p06-core-memory-20261004/receipt.json"
    assert sha(receipt_path) == M6C_RECEIPT_SHA256, "Frozen M6c receipt changed"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "P06_PRIVATE_MEMORY_CPU_PASS"
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / name) == expected, name
    selected = build_memory(out)
    assert set(selected) == set(receipt["generated_cpu_sha256"])
    for name, path in selected.items():
        assert sha(path) == receipt["generated_cpu_sha256"][name], name

    biu = selected["spk286_biu.sv"].read_text()
    biu = replace_once(biu, "parameter bit P06_SHARED_TIMING = 1'b0)",
        "parameter bit P06_SHARED_TIMING = 1'b0, parameter bit P06_ODD_READ_TIMING = 1'b0)")
    biu = replace_once(biu, "p06_scope_block, p06_read_wait_event,",
        "p06_scope_block, p06_read_wait_event, p06_alignment_event,")
    start = biu.index("// Private M6a byte/even-word memory READ timing.")
    end = biu.index("\n// Shared logical CODE/DATA ownership;", start)
    aligned = biu[start:end]
    body_start = aligned.index("        if (P06_DATA_TIMING) begin : p06_data\n") + len("        if (P06_DATA_TIMING) begin : p06_data\n")
    body_end = aligned.index("        end else begin : p06_data_maximum\n", body_start)
    aligned_body = aligned[body_start:body_end]
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_odd_read_biu_connection.svh").read_text()
    # Keep the frozen aligned state machine verbatim when the private odd
    # parameter is zero. Constant generate alternatives share one datapath.
    connection = replace_once(connection, "        end else begin : p06_data_maximum\n",
        "        end else if (P06_DATA_TIMING) begin : p06_data\n" + aligned_body +
        "            assign p06_alignment_event = 1'b0;\n" +
        "            assign p06_first_complete = 1'b0;\n" +
        "            assign p06_external_wait = external_wait;\n" +
        "            assign p06_physical_data_enable = 1'b1;\n" +
        "        end else begin : p06_data_maximum\n")
    biu = replace_once(biu, biu[start:end], connection.rstrip() + "\n")
    biu = replace_once(biu, "(data_abort && (!data_active_q || data_complete))",
        "(data_abort && (!data_active_q || (data_complete &&\n" +
        "                    (!P06_ODD_READ_TIMING || !address_q[0] || byte_q))))")
    biu = replace_once(biu, "(select_data ? data_active_q : (code_valid",
        "(select_data ? (data_active_q && p06_physical_data_enable) : (code_valid")
    biu = replace_once(biu, "    logic data_active_q, write_q, second_q, canceled_q, byte_q, io_q;",
        "    generate\n" +
        "        if (P06_ODD_READ_TIMING && (!P06_DATA_TIMING || !P06_SHARED_TIMING)) begin : p06_invalid_odd_configuration\n" +
        "            initial $fatal(1, \"M6e odd READ requires DATA and SHARED timing\");\n" +
        "        end\n" +
        "    endgenerate\n    logic data_active_q, write_q, second_q, canceled_q, byte_q, io_q;")
    selected["spk286_biu.sv"].write_text(biu, newline="\n")

    top = selected["spk286.sv"].read_text()
    top = replace_once(top, "parameter bit P06_MEMORY_PILOT = 1'b0)",
        "parameter bit P06_MEMORY_PILOT = 1'b0,\n    parameter bit P06_ODD_READ_PILOT = 1'b0)")
    top = replace_once(top, "logic p06_code_issue, p06_code_complete, p06_code_canceled, p06_read_wait_event;",
        "logic p06_code_issue, p06_code_complete, p06_code_canceled, p06_read_wait_event, p06_alignment_event;")
    top = replace_once(top, "    generate\n        if (P06_MEMORY_PILOT &&",
        "    generate\n" +
        "        if (P06_ODD_READ_PILOT && !P06_MEMORY_PILOT) begin : p06_invalid_odd_configuration\n" +
        "            initial $fatal(1, \"M6e odd READ requires MEMORY timing\");\n" +
        "        end\n        if (P06_MEMORY_PILOT &&")
    top = replace_once(top, "memory_write || memory_byte || io_transfer || memory_address[0]));",
        "memory_write || memory_byte || io_transfer || (!P06_ODD_READ_PILOT && memory_address[0])));")
    top = replace_once(top, ".P06_SHARED_TIMING(P06_MEMORY_PILOT)) biu (",
        ".P06_SHARED_TIMING(P06_MEMORY_PILOT), .P06_ODD_READ_TIMING(P06_ODD_READ_PILOT)) biu (")
    top = replace_once(top, ".p06_scope_block(p06_biu_scope_block), .p06_read_wait_event(p06_read_wait_event),",
        ".p06_scope_block(p06_biu_scope_block), .p06_read_wait_event(p06_read_wait_event),\n" +
        "        .p06_alignment_event(p06_alignment_event),")
    top = replace_once(top, "p06_instruction_duration duration_policy (",
        "p06_instruction_duration #(.P06_LATE_ALIGNMENT(P06_ODD_READ_PILOT)) duration_policy (")
    top = replace_once(top, ".read_wait_event(p06_timed_read && p06_read_wait_event),",
        ".alignment_event(p06_timed_read && p06_alignment_event),\n" +
        "                .read_wait_event(p06_timed_read && p06_read_wait_event),")
    selected["spk286.sv"].write_text(top, newline="\n")

    # The A1 offset is not known at opcode admission. Its accepted odd Ts
    # supplies one retained-state correction event after the existing start.
    # Patch a generated policy copy only; M3/M6c source remains frozen.
    duration = (ROOT / "rtl/spk286_timing_pilot/p06_instruction_duration.sv").read_text()
    duration = replace_once(duration, "parameter bit HISTORICAL = 1'b1",
        "parameter bit HISTORICAL = 1'b1, parameter bit P06_LATE_ALIGNMENT = 1'b0")
    duration = replace_once(duration, "    input logic read_wait_event,",
        "    /* verilator lint_off UNUSEDSIGNAL */\n" +
        "    input logic alignment_event,\n" +
        "    /* verilator lint_on UNUSEDSIGNAL */\n    input logic read_wait_event,")
    duration = replace_once(duration,
        "wire [8:0] extended_budget = {1'b0, budget_q} + 9'(wait_increment);",
        "wire alignment_increment = P06_LATE_ALIGNMENT && active_q && cpu_boundary && permits_wait_q && alignment_event;\n" +
        "            wire [8:0] extended_budget = {1'b0, budget_q} + 9'(wait_increment) +\n" +
        "                (alignment_increment ? 9'd2 : 9'd0);")
    duration = replace_once(duration,
        "wire event_bad = read_wait_event &&\n                (!active_q || !cpu_boundary || !permits_wait_q);",
        "wire event_bad = (read_wait_event || (P06_LATE_ALIGNMENT && alignment_event)) &&\n" +
        "                (!active_q || !cpu_boundary || !permits_wait_q);")
    duration = replace_once(duration, "if (wait_increment && !overflow) budget_q <= extended_budget[7:0];",
        "if ((wait_increment || alignment_increment) && !overflow) budget_q <= extended_budget[7:0];")
    duration_path = out / "private-rtl/p06_instruction_duration.sv"
    duration_path.write_text(duration, newline="\n")
    selected[duration_path.name] = duration_path
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT.resolve())
    output.mkdir(parents=True, exist_ok=False)
    selected = build(output)
    manifest = {"ancestor_receipt_sha256": M6C_RECEIPT_SHA256,
                "generated_cpu_sha256": {name: sha(path) for name, path in selected.items()}}
    (output / "prepared.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"M6E_ODD_READ_PREPARED sources={len(selected)}")
