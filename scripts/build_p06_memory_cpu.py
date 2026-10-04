#!/usr/bin/env python3
"""Private M6c: real aligned A1 READ with M5 IU and M6b shared bus.

Frozen builders/evidence remain unchanged. Only one selected functional CPU is
compiled. All new parameters default to zero; historical scope is provisional.
"""
import json
import shutil
from build_p06_iu_cpu import build as build_iu
from build_p06_shared_bus import build as build_shared
from build_p06_register_cpu import ROOT, replace_once
from run_p06_core_register import sha


def build(out):
    iu_receipt = json.loads((ROOT/"docs/evidence/p06-core-iu-20261004/receipt.json").read_text())
    shared_receipt = json.loads((ROOT/"docs/evidence/p06-core-shared-bus-20261004/receipt.json").read_text())
    for name in ["scripts/build_p06_iu_cpu.py","rtl/spk286_timing_pilot/p06_iu_connection.svh",
                 "rtl/spk286_timing_pilot/p06_register_connection.svh",
                 "rtl/spk286_timing_pilot/p06_fetch_cpu_connection.svh"]:
        assert sha(ROOT/name) == iu_receipt["sources_sha256"][name],name
    for name in ["scripts/build_p06_shared_bus.py","rtl/spk286_timing_pilot/p06_shared_biu_connection.svh"]:
        assert sha(ROOT/name) == shared_receipt["sources_sha256"][name],name
    selected = build_iu(out)
    for name,path in selected.items():
        assert sha(path) == iu_receipt["generated_cpu_sha256"][name],name
    intermediate = out/"shared-source"; intermediate.mkdir()
    shared = build_shared(intermediate)
    for name,path in shared.items():
        assert sha(path) == shared_receipt["generated_sha256"][name],name
        target = out/"private-rtl"/name
        shutil.copyfile(path,target); selected[name] = target

    biu = selected["spk286_biu.sv"].read_text()
    biu = replace_once(biu,"output logic p06_scope_error, p06_code_admission, p06_scope_block,",
        "output logic p06_scope_error, p06_code_admission, p06_scope_block, p06_read_wait_event,")
    biu = replace_once(biu,"wire external_wait = sample_tc && !p06_board_ready;",
        "wire external_wait = sample_tc && !p06_board_ready;\n"+
        "            // Duration observes the already accepted TC lifetime. Do\n"+
        "            // not feed current request-derived scope back into EU\n"+
        "            // permit/start. New scope invalidates this context; its\n"+
        "            // sticky flag suppresses the following wait boundaries.\n"+
        "            assign p06_read_wait_event = !reset && !cancel_data && !canceled_q &&\n"+
        "                !p06_scope_error && p06_cpu_boundary && state_q == TC && !p06_board_ready;")
    biu = replace_once(biu,"assign p06_scope_block = 1'b0;",
        "assign p06_scope_block = 1'b0;\n            assign p06_read_wait_event = 1'b0;")
    selected["spk286_biu.sv"].write_text(biu,newline="\n")

    top = selected["spk286.sv"].read_text()
    top = replace_once(top,"parameter bit P06_IU_PILOT = 1'b0",
        "parameter bit P06_IU_PILOT = 1'b0,\n    parameter bit P06_MEMORY_PILOT = 1'b0")
    top = replace_once(top,"    input  logic         clk,",
        "    /* verilator lint_off UNUSEDSIGNAL */\n"+
        "    input logic p06_code_board_ready, p06_data_board_ready,\n"+
        "    /* verilator lint_on UNUSEDSIGNAL */\n    input  logic         clk,")
    top = replace_once(top,"    logic p06_relaunch_window, p06_relaunch;",
        "    logic p06_relaunch_window, p06_relaunch;\n"+
        "    logic p06_register_result_pending, p06_read_result_pending, p06_timed_read;\n"+
        "    /* verilator lint_off UNUSEDSIGNAL */\n"+
        "    logic p06_biu_scope_error, p06_biu_scope_block, p06_code_grant;\n"+
        "    logic p06_code_issue, p06_code_complete, p06_code_canceled, p06_read_wait_event;\n"+
        "    /* verilator lint_on UNUSEDSIGNAL */\n"+
        "    assign p06_timed_read = P06_MEMORY_PILOT && micro_active && !event_active && opcode_q == 8'hA1;\n"+
        "    assign p06_result_pending = p06_register_result_pending || p06_read_result_pending;\n"+
        "    generate\n        if (P06_MEMORY_PILOT && (!P06_REGISTER_PILOT || !P06_FETCH_PILOT)) begin : p06_invalid_memory_configuration\n"+
        "            initial $fatal(1, \"M6c requires REGISTER and FETCH timing\");\n"+
        "        end\n    endgenerate")
    top = replace_once(top,"8'h35: form = 4'd4;",
        "8'h35: form = 4'd4;\n                    8'hA1: begin form = 4'd8; opcode_known = P06_MEMORY_PILOT; end")
    top = replace_once(top,"assign has_modrm = opcode_q != 8'h05 && opcode_q != 8'h35;",
        "assign has_modrm = opcode_q != 8'h05 && opcode_q != 8'h35 &&\n                (!P06_MEMORY_PILOT || opcode_q != 8'hA1);")
    top = replace_once(top,"assign p06_block = scope_error || bad_modrm || protected_msw[0] || event_active;",
        "// Only sticky bus scope reaches EU gating; the combinational bus\n"+
        "            // guard contains memory_request and must not close an enable loop.\n"+
        "            assign p06_block = scope_error || bad_modrm || protected_msw[0] || event_active ||\n"+
        "                (P06_MEMORY_PILOT && p06_biu_scope_error);")
    top = replace_once(top,".read_wait_event(1'b0), .functional_done(p06_result_pending),",
        ".read_wait_event(p06_timed_read && p06_read_wait_event), .functional_done(p06_result_pending),")
    top = replace_once(top,"wire unsupported_bus = hold_request || bus_lock || memory_request || ack_request;",
        "wire unsupported_bus = hold_request || bus_lock || ack_request ||\n"+
        "                (memory_request && (!P06_MEMORY_PILOT || !p06_timed_read ||\n"+
        "                    memory_write || memory_byte || io_transfer || memory_address[0]));")
    top = replace_once(top,"assign p06_fetch_block = scope_error || hold_request;",
        "assign p06_fetch_block = scope_error || hold_request || (P06_MEMORY_PILOT && p06_biu_scope_error);")
    top = replace_once(top,"    spk286_biu biu (",
        "    spk286_biu #(.P06_DATA_TIMING(P06_MEMORY_PILOT), .P06_SHARED_TIMING(P06_MEMORY_PILOT)) biu (\n"+
        "        .p06_cpu_boundary(p06_fetch_boundary),\n"+
        "        .p06_board_ready(!P06_MEMORY_PILOT || p06_data_board_ready),\n"+
        "        .p06_code_issue(p06_code_issue), .p06_code_complete(p06_code_complete), .p06_code_canceled(p06_code_canceled),\n"+
        "        .p06_code_admission(p06_code_grant), .p06_scope_error(p06_biu_scope_error),\n"+
        "        .p06_scope_block(p06_biu_scope_block), .p06_read_wait_event(p06_read_wait_event),")
    top = replace_once(top,".hold_request(hold_request && !P06_FETCH_PILOT)",
        ".hold_request(hold_request && (!P06_FETCH_PILOT || P06_MEMORY_PILOT))")
    top = replace_once(top,".ack_request(ack_request && !ack_pending_q && !P06_FETCH_PILOT)",
        ".ack_request(ack_request && !ack_pending_q && (!P06_FETCH_PILOT || P06_MEMORY_PILOT))")
    top = replace_once(top,".data_request(memory_request && !P06_FETCH_PILOT)",
        ".data_request(memory_request && (!P06_FETCH_PILOT || (P06_MEMORY_PILOT && p06_timed_read)))")
    top = replace_once(top,".p06_cpu_boundary(p06_fetch_boundary), .p06_board_ready(1'b1),",
        ".p06_cpu_boundary(p06_fetch_boundary), .p06_board_ready(!P06_MEMORY_PILOT || p06_code_board_ready),\n"+
        "        .p06_scope_block(P06_MEMORY_PILOT && p06_biu_scope_block),\n"+
        "        .p06_bus_issue(p06_code_issue), .p06_bus_complete(p06_code_complete), .p06_bus_canceled(p06_code_canceled),")
    top = replace_once(top,".p06_admission_enable(p06_fetch_admission)",
        ".p06_admission_enable(p06_fetch_admission && (!P06_MEMORY_PILOT || p06_code_grant))")
    top = replace_once(top,".USE_PARALLEL_SYSTEM_LIMIT(1'b1), .P06_IU_OVERLAP(P06_IU_PILOT)",
        ".USE_PARALLEL_SYSTEM_LIMIT(1'b1), .P06_IU_OVERLAP(P06_IU_PILOT),\n        .P06_MEMORY_TIMING(P06_MEMORY_PILOT)")
    top = replace_once(top,".register_result_pending(p06_result_pending)",
        ".register_result_pending(p06_register_result_pending),\n"+
        "        .p06_moffs_read(p06_timed_read), .p06_memory_result_pending(p06_read_result_pending)")
    selected["spk286.sv"].write_text(top,newline="\n")

    executor = selected["spk286_micro_executor.sv"].read_text()
    executor = replace_once(executor,"parameter bit P06_IU_OVERLAP = 1'b0,",
        "parameter bit P06_IU_OVERLAP = 1'b0, parameter bit P06_MEMORY_TIMING = 1'b0,")
    executor = replace_once(executor,"input logic p06_relaunch_window,",
        "input logic p06_relaunch_window,\n"+
        "    /* verilator lint_off UNUSEDSIGNAL */\n    input logic p06_moffs_read,\n"+
        "    /* verilator lint_on UNUSEDSIGNAL */\n    output logic p06_memory_result_pending,")
    executor = replace_once(executor,"assign operation_retire = register_complete;",
        "// Retained TMP0/MOVE phase is independent of the gated functional\n"+
        "    // enable. The permitted real MOVE writes AX and retires together.\n"+
        "    assign p06_memory_result_pending = P06_MEMORY_TIMING && p06_moffs_read &&\n"+
        "        operation == spk286_microcode_pkg::MC_MOVE && temporary_valid_q[0];\n"+
        "    assign operation_retire = register_complete || (P06_MEMORY_TIMING && p06_moffs_read && move_word);")
    selected["spk286_micro_executor.sv"].write_text(executor,newline="\n")
    return selected
