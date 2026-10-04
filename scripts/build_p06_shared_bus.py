#!/usr/bin/env python3
"""Extend frozen M4/M6a components with private shared logical bus ownership."""
import hashlib
import json
from build_p06_data_biu import build as build_data
from build_p06_fetch_cpu import fetch_source
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha


def build(out):
    data_receipt = json.loads((ROOT/"docs/evidence/p06-core-data-20261004/receipt.json").read_text())
    fetch_receipt = json.loads((ROOT/"docs/evidence/p06-core-fetch-20261004/receipt.json").read_text())
    for name in ["scripts/build_p06_data_biu.py","scripts/build_p06_register_cpu.py",
                 "rtl/spk286_timing_pilot/p06_data_biu_connection.svh"]:
        assert sha(ROOT/name) == data_receipt["sources_sha256"][name],name
    for name in ["scripts/build_p06_fetch_cpu.py","rtl/spk286_timing_pilot/p06_fetch_connection.svh"]:
        assert sha(ROOT/name) == fetch_receipt["sources_sha256"][name],name
    biu = build_data(out)
    assert sha(biu) == data_receipt["generated_biu_sha256"]
    text = biu.read_text()
    text = replace_once(text,"parameter bit P06_DATA_TIMING = 1'b0",
        "parameter bit P06_DATA_TIMING = 1'b0, parameter bit P06_SHARED_TIMING = 1'b0")
    text = replace_once(text,"input logic p06_cpu_boundary, p06_board_ready,",
        "input logic p06_cpu_boundary, p06_board_ready,\n"+
        "    input logic p06_code_issue, p06_code_complete, p06_code_canceled,")
    text = replace_once(text,"output logic p06_scope_error,",
        "output logic p06_scope_error, p06_code_admission, p06_scope_block,")
    text = replace_once(text,"wire unsupported_bus = code_valid ||",
        "wire unsupported_bus = (code_valid && !P06_SHARED_TIMING) ||")
    text = replace_once(text,"wire scope_block = p06_scope_error || unsupported_data || unsupported_bus;",
        "wire scope_block = p06_scope_error || unsupported_data || unsupported_bus;\n"+
        "            assign p06_scope_block = scope_block;\n"+
        "            assign p06_data_idle = state_q == IDLE;")
    text = replace_once(text,"assign p06_complete = 1'b0;",
        "assign p06_complete = 1'b0;\n"+
        "            assign p06_scope_block = 1'b0;\n"+
        "            assign p06_data_idle = 1'b1;")
    text = replace_once(text,"p06_cpu_boundary && state_q == IDLE;",
        "p06_cpu_boundary && state_q == IDLE && p06_shared_data_grant;")
    text = replace_once(text,"(code_valid && !lock_chain_q && !P06_DATA_TIMING)",
        "(code_valid && !lock_chain_q && (!P06_DATA_TIMING || P06_SHARED_TIMING))")
    text = replace_once(text,"    assign data_request_ready =",
        (ROOT/"rtl/spk286_timing_pilot/p06_shared_biu_connection.svh").read_text()+
        "\n    assign data_request_ready =")
    text = replace_once(text,"        end else if (bus_valid) begin\n            owner_valid_q <= !ready;",
        "        end else if (P06_DATA_TIMING && P06_SHARED_TIMING) begin\n"+
        "            if (p06_shared_release) owner_valid_q <= 1'b0;\n"+
        "            if (p06_code_issue) begin owner_valid_q <= 1'b1; owner_q <= 2'd0; end\n"+
        "            if (data_request && data_request_ready) begin\n"+
        "                owner_valid_q <= 1'b1; owner_q <= 2'd1;\n"+
        "            end\n"+
        "        end else if (bus_valid) begin\n            owner_valid_q <= !ready;")
    biu.write_text(text,newline="\n")
    text = fetch_source()
    assert hashlib.sha256(text.encode()).hexdigest() == fetch_receipt["generated_cpu_sha256"]["spk286_fetch.sv"]
    text = replace_once(text,"input logic p06_cpu_boundary, p06_board_ready, p06_admission_enable,",
        "input logic p06_cpu_boundary, p06_board_ready, p06_admission_enable, p06_scope_block,")
    text = replace_once(text,"    input  logic        clk,",
        "    output logic p06_bus_issue, p06_bus_complete, p06_bus_canceled,\n    input  logic        clk,")
    text = replace_once(text,"assign p06_can_issue = !suspend &&",
        "assign p06_can_issue = !suspend && (!P06_FETCH_TIMING || !p06_scope_block) &&")
    text = replace_once(text,"wire sample_tc = !reset && !restart && !canceled_q &&",
        "wire sample_tc = !reset && !restart && !canceled_q && !p06_scope_block &&")
    text = replace_once(text,"assign response_valid = !reset && !restart &&",
        "assign response_valid = !reset && !restart && !p06_scope_block &&")
    text = replace_once(text,"    assign cursor = cursor_q;",
        "    assign p06_bus_issue = P06_FETCH_TIMING && p06_issue;\n"+
        "    assign p06_bus_complete = P06_FETCH_TIMING && p06_complete;\n"+
        "    assign p06_bus_canceled = P06_FETCH_TIMING && (restart || canceled_q || p06_scope_block);\n"+
        "    assign cursor = cursor_q;")
    fetch = biu.parent/"spk286_fetch.sv"; fetch.write_text(text,newline="\n")
    return {"spk286_biu.sv":biu,"spk286_fetch.sv":fetch}
