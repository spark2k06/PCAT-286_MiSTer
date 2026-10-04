#!/usr/bin/env python3
"""Build one private CPU variant from hash-pinned production sources.

Only the selected source list is compiled. There is no committed clone of the
functional engine and no change to production QIP/source/86Box/RBF. Literal
anchors must match once; fail rather than silently patch a different CPU.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Private CPU anchor occurs {text.count(old)} times: {old[:90]}")
    return text.replace(old, new)


def build(out):
    reference = json.loads((ROOT / "docs/evidence/p06-core-register-20261004/observation/receipt.json").read_text())
    for name, expected in reference["sources_sha256"].items():
        if name.startswith("vendor/spk286/"):
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    target = out / "private-rtl"
    target.mkdir(parents=True, exist_ok=False)
    top = (ROOT / "vendor/spk286/rtl/spk286.sv").read_text()
    top = replace_once(top, "module spk286 (", "module spk286 #(parameter bit P06_REGISTER_PILOT = 1'b0) (")
    # Rename all internal cursor uses, keeping the public port name unchanged.
    top = top.replace("debug_ip", "p06_cursor_ip")
    top = replace_once(top, "output logic [15:0]  p06_cursor_ip,", "output logic [15:0]  debug_ip,")
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_register_connection.svh").read_text()
    top = replace_once(top, "    // A CS reload requires", connection + "\n    // A CS reload requires")
    top = replace_once(top, "assign execution_allowed = execute_enable && commit_allowed", "assign execution_allowed = execute_enable && !p06_block && commit_allowed")
    top = replace_once(top, "assign opcode_start = decode_ready &&", "assign opcode_start = p06_admit && decode_ready &&")
    top = replace_once(top, "assign prefix_accept = decode_ready &&", "assign prefix_accept = !P06_REGISTER_PILOT && decode_ready &&")
    top = replace_once(top, "assign service_start = event_dispatch || (decode_ready &&", "assign service_start = event_dispatch || (p06_admit && decode_ready &&")
    top = replace_once(top, "end else if (decode_ready && !event_active && !event_request", "end else if (p06_admit && decode_ready && !event_active && !event_request")
    top = replace_once(top, ".operation_valid(operation_valid), .operation(micro_word),", ".register_result_pending(p06_result_pending),\n        .operation_valid(operation_valid && p06_executor_permit), .operation(micro_word),")
    top = replace_once(top, "assign operation_done = micro_end || executor_done || loadall_complete;", "assign operation_done = (micro_end || executor_done || loadall_complete) &&\n                            (!p06_result_pending || p06_executor_permit);")
    executor = (ROOT / "vendor/spk286/rtl/spk286_micro_executor.sv").read_text()
    executor = replace_once(executor, "output logic operation_done, operation_retire, dispatch_request,", "output logic operation_done, operation_retire, dispatch_request,\n    output logic register_result_pending,")
    # Existing pending_q is written only after accepted register ModR/M or the
    # final immediate byte. Its validity must not depend on the gated decode
    # enable: decode_done itself is qualified by that enable and would loop.
    executor = replace_once(executor, "assign register_complete = allowed && register_pending_q &&", "assign register_result_pending = register_pending_q;\n    assign register_complete = allowed && register_pending_q &&")
    (target / "spk286.sv").write_text(top, newline="\n")
    (target / "spk286_micro_executor.sv").write_text(executor, newline="\n")
    return {"spk286.sv": target / "spk286.sv",
            "spk286_micro_executor.sv": target / "spk286_micro_executor.sv"}
