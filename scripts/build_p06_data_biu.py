#!/usr/bin/env python3
"""Hash-pinned private BIU data READ timing; byte/even-word, no CODE ownership.

Reuses the original final response slot. This is a component milestone, not
whole-CPU memory-instruction timing or production adoption.
"""
import json
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha


def build(out):
    original = ROOT / "vendor/spk286/rtl/spk286_biu.sv"
    receipt = json.loads((ROOT / "docs/evidence/p06-core-iu-20261004/receipt.json").read_text())
    assert sha(original) == receipt["sources_sha256"][original.relative_to(ROOT).as_posix()]
    text = original.read_text()
    text = replace_once(text, "module spk286_biu (",
                        "module spk286_biu #(parameter bit P06_DATA_TIMING = 1'b0) (\n"+
                        "    /* verilator lint_off UNUSEDSIGNAL */\n"+
                        "    input logic p06_cpu_boundary, p06_board_ready,\n"+
                        "    /* verilator lint_on UNUSEDSIGNAL */\n"+
                        "    output logic p06_scope_error,")
    for name in ["data_response_valid", "data_read_data"]:
        text = text.replace(name, "raw_" + name)
    for declaration in ["logic raw_data_response_valid", "logic [15:0] raw_data_read_data"]:
        text = replace_once(text, "output " + declaration, "output " + declaration.replace("raw_", ""))
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_data_biu_connection.svh").read_text()
    text = replace_once(text, "    assign data_request_ready =", connection + "\n    assign data_request_ready =")
    text = replace_once(text, "!raw_data_response_valid && !ack_active_q && !hlda;",
                        "!raw_data_response_valid && !ack_active_q && !hlda && p06_admit;")
    text = replace_once(text, "!ack_response_valid && !hlda;",
                        "!ack_response_valid && !hlda && !P06_DATA_TIMING;")
    text = replace_once(text, "(code_valid && !lock_chain_q)", "(code_valid && !lock_chain_q && !P06_DATA_TIMING)")
    text = replace_once(text, "if (!hold_request || lock_request)",
                        "if (!(hold_request && !P06_DATA_TIMING) || (lock_request && !P06_DATA_TIMING))")
    text = replace_once(text, "else if (hold_request && !bus_lock", "else if (hold_request && !P06_DATA_TIMING && !bus_lock")
    text = replace_once(text, "(lock_request || lock_chain_q", "((lock_request && !P06_DATA_TIMING) || lock_chain_q")
    text = replace_once(text, "if (ack_request && ack_request_ready)", "if (ack_request && ack_request_ready && !P06_DATA_TIMING)")
    text = replace_once(text, "if (raw_data_response_valid && data_response_ready)", "if (p06_response_fire)")
    text = replace_once(text, "raw_data_response_valid <= !canceled_q && !cancel_data;",
                        "raw_data_response_valid <= !canceled_q && !cancel_data &&\n                        !(P06_DATA_TIMING && p06_response_fire);")
    target = out / "private-rtl/spk286_biu.sv"; target.parent.mkdir(parents=True,exist_ok=False)
    target.write_text(text,newline="\n")
    return target
