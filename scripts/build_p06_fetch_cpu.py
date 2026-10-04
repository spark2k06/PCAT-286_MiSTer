#!/usr/bin/env python3
"""Extend the hash-pinned private M3 CPU with retained CODE Ts/Tc timing."""
from pathlib import Path
from build_p06_register_cpu import ROOT, build as build_register, replace_once


def fetch_source():
    text = (ROOT / "vendor/spk286/rtl/spk286_fetch.sv").read_text()
    text = replace_once(text, "module spk286_fetch (", "module spk286_fetch #(parameter bit P06_FETCH_TIMING = 1'b0) (\n    // Timing-only inputs deliberately disappear in MAX.\n    /* verilator lint_off UNUSEDSIGNAL */\n    input logic p06_cpu_boundary, p06_board_ready, p06_admission_enable,\n    /* verilator lint_on UNUSEDSIGNAL */")
    for name in ["response_valid", "response_data", "response_ip", "response_count"]:
        text = text.replace(name, "raw_" + name)
    for declaration in ["logic        raw_response_valid", "logic [15:0] raw_response_data",
                        "logic [15:0] raw_response_ip", "logic [1:0]  raw_response_count"]:
        text = replace_once(text, "output " + declaration, "output " + declaration.replace("raw_", ""))
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_fetch_connection.svh").read_text()
    text = replace_once(text, "    assign cursor = cursor_q;", connection + "\n    assign cursor = cursor_q;")
    text = replace_once(text, "wire response_fire = raw_response_valid && response_ready;", "wire response_fire = response_valid && response_ready;")
    # Slot reuse is available only when the LOGICAL result is actually consumed.
    text = replace_once(text, "!active_q && response_slot_available && !blocked;", "!active_q && response_slot_available && !blocked && p06_admit;")
    text = replace_once(text, "end else if (!suspend && response_slot_available && !blocked &&\n                         (restart_pending_q || request)) begin", "end else if (p06_can_issue) begin")
    text = replace_once(text, "raw_response_valid <= 1'b1;", "raw_response_valid <= !(P06_FETCH_TIMING && response_fire);")
    return text


def build(out):
    selected = build_register(out)
    top = selected["spk286.sv"].read_text()
    top = replace_once(top, "parameter bit P06_REGISTER_PILOT = 1'b0", "parameter bit P06_REGISTER_PILOT = 1'b0,\n    parameter bit P06_FETCH_PILOT = 1'b0")
    connection = (ROOT / "rtl/spk286_timing_pilot/p06_fetch_cpu_connection.svh").read_text()
    top = replace_once(top, "    // A CS reload requires", connection + "\n    // A CS reload requires")
    top = replace_once(top, "execute_enable && !p06_block && commit_allowed", "execute_enable && !p06_block && !p06_fetch_block && commit_allowed")
    top = replace_once(top, "spk286_fetch fetch (", "spk286_fetch #(.P06_FETCH_TIMING(P06_FETCH_PILOT)) fetch (\n        .p06_cpu_boundary(p06_fetch_boundary), .p06_board_ready(1'b1),\n        .p06_admission_enable(p06_fetch_admission),")
    top = replace_once(top, ".suspend(event_active || halted || shutdown)", ".suspend(event_active || halted || shutdown || p06_fetch_block)")
    top = replace_once(top, ".hold_request(hold_request), .lock_request", ".hold_request(hold_request && !P06_FETCH_PILOT), .lock_request")
    top = replace_once(top, ".ack_request(ack_request && !ack_pending_q),", ".ack_request(ack_request && !ack_pending_q && !P06_FETCH_PILOT),")
    top = replace_once(top, ".data_request(memory_request), .data_request_ready", ".data_request(memory_request && !P06_FETCH_PILOT), .data_request_ready")
    selected["spk286.sv"].write_text(top, newline="\n")
    fetch = out / "private-rtl/spk286_fetch.sv"
    fetch.write_text(fetch_source(), newline="\n")
    selected["spk286_fetch.sv"] = fetch
    return selected
