#!/usr/bin/env python3
"""Audit private M6g RMW evidence without rerunning simulation or synthesis.

The independent edge oracle uses immutable caller words, pre-edge physical
lanes and payloads, and post-edge architecture. Undefined AF follows the
preserved MAX policy; it is not claimed as an Intel-defined XOR result.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_p06_rmw_cpu import build
from build_p06_register_cpu import replace_once
from check_p06_odd_components import BIU_INPUTS, BIU_OUTPUTS, no_private_input_cone
from run_p06_core_register import sha
from run_p06_memory_cpu import private_bench
from run_p06_rmw_cpu import rmw_vectors, controlled_vectors
from run_p06_odd_read_cpu import odd_vectors, UNIT_NAMES
from run_p06_write_cpu import write_vectors
from run_p06_iu import stream_vectors
from run_p06_pilot import generic_stats

M6F = "docs/evidence/p06-core-write-20261004"
M6F_SHA256 = "89e91b391a0ef829290594099cf9ce03a9fd666ba1028c4b7f160e356eacbb65"
M6E = "docs/evidence/p06-core-odd-read-20261004"
M6E_SHA256 = "42a54266c3d49bca026f26d9789db788abcfcb7211d5caa304a8767bc628da92"
M6C = "docs/evidence/p06-core-memory-20261004"
M6C_SHA256 = "59e8738bc24251b0a8ad5670435fd3987394eba858cd130943934b3fe5384f65"
DIRTY_GUARD_SHA256 = "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
MODES = list(range(1, 29))
ABANDONED = set(range(6, 29))
RESET_MODES = set(range(20, 27))
SCOPE_MODES = set(range(13, 20))
SUMMARY_FIELDS = set("id timed warm mode odd start_cpu retire_cpu elapsed code_accepts data_accepts code_captures data_captures code_responses data_responses read_accepts write_accepts read_captures write_captures read_responses write_responses code_external read_wait1 read_wait2 write_wait1 write_wait2 code_misses read_miss1 read_miss2 write_miss1 write_miss2 alignment_count form_count first_tc final_tc off_boundary gpr flags ip retired scope memory guard_before guard_after scheduled".split())
TRACE_FIELDS = set("id edge boundary cpu_clock start code_start data_start code_capture data_capture first_tc final_tc gpr_write retired owner bus address status ready ip cursor gpr flags queue scope policy_wait diagnostic_wait alignment flags_pending scheduled write bhe dataout memory_before memory_after execute cancel phase flags_commit consumes form_count form_event datain".split())
# Exact generated-copy mutations and observed independent markers must be bound
# here before acceptance. An empty contract intentionally rejects acceptance.
NEGATIVES = {
    "late-form": ("RMW independent late form event oracle failed", "spk286.sv",
        ".rmw_form_valid(p06_timed_rmw)", ".rmw_form_valid(1'b0)", "rmw-vectors.txt", []),
    "alignment": ("RMW alignment/wait budget oracle failed", "spk286.sv",
        ".alignment_event(p06_timed_data && p06_alignment_event)", ".alignment_event(1'b0)", "rmw-vectors.txt", []),
    "read-wait": ("RMW alignment/wait budget oracle failed", "spk286.sv",
        ".read_wait_event((p06_timed_read || p06_timed_rmw) && p06_read_wait_event)",
        ".read_wait_event(1'b0)", "rmw-vectors.txt", []),
    "write-as-read-wait": ("RMW independent alignment/wait event oracle failed", "spk286_biu.sv",
        "wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;", "wire p06_read_cycle = 1'b1;", "rmw-vectors.txt", []),
    "permit-boundary": ("RMW first eligible FLAGS commit oracle failed", "spk286.sv",
        "(!p06_result_pending || permit)", "1'b1", "rmw-vectors.txt", []),
    "early-flags": ("RMW first eligible FLAGS commit oracle failed", "spk286_micro_executor.sv",
        "assign commit_flags = allowed && operation == spk286_microcode_pkg::MC_COMMIT_FLAGS && flags_valid_q && result_disposed_q;",
        "assign commit_flags = allowed && flags_valid_q && (operation == spk286_microcode_pkg::MC_COMMIT_FLAGS || operation == spk286_microcode_pkg::MC_WRITE_RESULT_RM16);",
        "rmw-vectors.txt", []),
    "retire-at-alu": ("RMW first eligible retirement oracle failed", "spk286_micro_executor.sv",
        "(P06_RMW_TIMING && p06_rmw_form && commit_flags)",
        "(P06_RMW_TIMING && p06_rmw_form && compute_alu)", "rmw-vectors.txt", []),
    "read-assembly": ("RMW independent READ response payload oracle failed", "spk286_biu.sv",
        "(second_q ? {data_in[7:0], low_byte_q} : data_in)) : raw_data_read_data;",
        "(second_q ? {low_byte_q, data_in[7:0]} : data_in)) : raw_data_read_data;", "rmw-vectors.txt", []),
    "write-payload": ("RMW caller-derived logical request oracle failed", "spk286_micro_executor.sv",
        "(result_operation ? tmp2_q : tmp0_q)", "(result_operation ? tmp0_q : tmp0_q)", "rmw-vectors.txt", []),
}


def relative_name(name):
    path = Path(name)
    assert not path.is_absolute() and not path.drive and ".." not in path.parts, name
    assert path.as_posix() == name, name
    return path


def artifact(base, name):
    path = base / relative_name(name)
    compressed = Path(str(path) + ".gz")
    assert not (path.is_file() and compressed.is_file()), f"Ambiguous artifact: {name}"
    return path.read_bytes() if path.is_file() else gzip.decompress(compressed.read_bytes())


def data(name):
    return artifact(HERE, name)


def rows(name):
    return list(csv.DictReader(io.StringIO(data(name).decode())))


def xor_flags(old, value):
    result = (0x80 if value & 0x8000 else 0) | (0x40 if value == 0 else 0)
    result |= 4 if (value & 255).bit_count() % 2 == 0 else 0
    return (old & ~0x08c5) | result


def contexts():
    result = {
        "rmw/normal": (1, 1, 0, "rmw-vectors.txt"),
        "rmw/cold": (1, 0, 0, "rmw-vectors.txt"),
        "rmw/mode29-warm": (1, 1, 29, "rmw-deadline-vectors.txt"),
        "original-max/normal": (0, 1, 0, "rmw-vectors.txt"),
        "private-max/normal": (0, 1, 0, "rmw-vectors.txt"),
    }
    result.update({f"rmw/mode{mode}-{label}": (1, warm, mode,
        "rmw-read-late-vectors.txt" if mode == 27 else "rmw-write-late-vectors.txt" if mode == 28 else
        "rmw-control-vectors.txt") for mode in MODES for label, warm in [("warm", 1), ("cold", 0)]})
    assert len(result) == 61
    return result


def check_pairs(artifacts):
    prefixes = set(contexts()) | {f"{name}/{temperature}" for name in
        ["odd-read", "write-preserved", "register-streams"] for temperature in ["normal", "cold"]}
    assert len(prefixes) == 67
    expected = {prefix + "-iverilog-summary.csv" for prefix in prefixes}
    assert {name for name in artifacts if name.endswith("-iverilog-summary.csv")} == expected
    assert {name for name in artifacts if name.endswith("-verilator-summary.csv")} == {
        name.replace("-iverilog-", "-verilator-") for name in expected}
    traces = {name.removesuffix("summary.csv") + "trace.csv" for name in expected}
    traces |= {name.replace("-iverilog-", "-verilator-") for name in traces}
    assert {name for name in artifacts if name.endswith("-trace.csv") and
        ("-iverilog-" in name or "-verilator-" in name)} == traces
    result = {}
    for name in sorted(expected):
        for left in [name, name.removesuffix("summary.csv") + "trace.csv"]:
            assert data(left) == data(left.replace("-iverilog-", "-verilator-")), left
        result[name] = rows(name)
        assert result[name], name
        if name.removesuffix("-iverilog-summary.csv") in contexts():
            assert set(result[name][0]) == SUMMARY_FIELDS, name
    return result


def check_vectors(directory):
    path = directory / "rmw-vectors.txt"
    assert rmw_vectors(path) == 858 and path.read_bytes() == data(path.name)
    fields = [line.split() for line in path.read_text().splitlines()]
    assert {int(f[0]) for f in fields} == set(range(858)) and all(len(f) == 19 for f in fields)
    assert sum(int(f[4], 16) & 1 for f in fields) == 765
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xffff for f in fields)
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xfffff for f in fields)
    values = {int(f[5], 16) ^ int(f[6], 16) for f in fields}
    assert {0, 1, 3, 0x81, 0x1ff, 0x8000}.issubset(values)
    expected_controls = [
        [f for f in fields if int(f[4], 16) & 1 and f[14:19] == ["0"] * 5][::19],
        [next(f for f in fields if int(f[4], 16) & 1 and f[9:14] == ["0"] + [str(w)] * 4 and
            f[14:19] == ["0"] * 5) for w in range(3)],
        [f for f in fields if int(f[4], 16) & 1 and f[15] == "80"][::18],
        [f for f in fields if int(f[4], 16) & 1 and f[17] == "80"][::18],
    ]
    for generated, expected, count in zip(controlled_vectors(directory), expected_controls, [14, 3, 14, 14]):
        expected_bytes = ("\n".join(" ".join(f) for f in expected) + "\n").encode()
        assert len(expected) == count and generated.read_bytes() == expected_bytes == data(generated.name)


def check_trace(prefix, records, path, timed, warm, mode, tools=("iverilog", "verilator")):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    assert {int(r["id"]) for r in records} == set(caller) and len(records) == len(caller)
    trace = csv.DictReader(io.StringIO(data(prefix + "-iverilog-trace.csv").decode()))
    assert set(trace.fieldnames) == TRACE_FIELDS, prefix
    events = "start code_start data_start code_capture data_capture first_tc final_tc alignment retired flags_commit form_event".split()
    nonbinary = set("id edge cpu_clock owner address status ip cursor gpr flags queue scheduled dataout memory_before memory_after phase consumes datain".split())
    states = {}
    for row in trace:
        identifier = int(row["id"])
        assert identifier in caller, (prefix, identifier)
        f = caller[identifier]
        odd, initial = int(f[4], 16) & 1, int(f[5], 16)
        value, flags = initial ^ int(f[6], 16), int(f[8], 16)
        expected_flags = xor_flags(flags, value)
        address = (int(f[3], 16) << 4) + int(f[4], 16)
        state = states.setdefault(identifier, {"edge": 0, "memory": initial, "tx": [], "start": None,
            "retire": None, "flags": flags, "counts": {field: 0 for field in events}, "off": 0,
            "waits": [0] * 4, "misses": [0] * 4, "consumes": 0, "form": 0, "aborted": False,
            "held": None, "last_cpu": None, "last": None})
        edge, cpu, boundary = int(row["edge"]), int(row["cpu_clock"]), int(row["boundary"])
        assert edge == state["edge"] + 1, (prefix, row)
        state["edge"] = edge
        for field in TRACE_FIELDS - nonbinary:
            assert int(row[field]) in [0, 1], (prefix, field, row[field])
        assert 0 <= int(row["queue"]) <= 6 and 0 <= int(row["owner"]) <= 2
        if state["last_cpu"] is not None:
            assert cpu - state["last_cpu"] == (boundary if timed else 1), (prefix, row)
        state["last_cpu"] = cpu
        assert int(row["memory_before"], 16) == state["memory"], (prefix, row)
        assert int(row["gpr_write"]) == 0 and int(row["gpr"], 16) == int(f[7], 16), (prefix, row)
        assert int(row["phase"]) == len(state["tx"]), (prefix, row)
        live = not state["aborted"] and not int(row["cancel"]) and not int(row["scope"])
        if int(row["start"]):
            assert state["start"] is None and (not timed or boundary), (prefix, row)
            state["start"] = cpu
        form_expected = timed and live and boundary and state["start"] is not None and state["consumes"] >= 2 and not state["form"]
        # scope is a post-edge sticky level. The first HOLD edge can expose a
        # pre-edge diagnostic form_event while the independent caller rejects
        # qualification. It never grants FLAGS, retirement, or a new request.
        if live:
            assert int(row["form_event"]) == int(bool(form_expected)), (prefix, row)
        if form_expected:
            state["form"] = 1
        assert int(row["form_count"]) == state["form"], (prefix, row)
        consumed = int(row["consumes"])
        assert state["consumes"] <= consumed <= min(6, state["consumes"] + 1), (prefix, row)
        state["consumes"] = consumed
        tx = state["tx"][-1] if state["tx"] else None
        phase = len(state["tx"])
        active = tx is not None and tx["final"] is None
        diagnostic_expected = False
        alignment_expected = bool(timed and live and boundary and active and odd and cpu == tx["accept"] + 1)
        if timed and live and boundary and active:
            beat_index = int(tx["first"] is not None)
            threshold = (tx["first"] + 2) if beat_index else tx["accept"] + 2
            ready_at = threshold + int(f[10 + 2 * (phase - 1) + beat_index])
            diagnostic_expected = cpu >= threshold and cpu < ready_at
            if cpu >= threshold:
                index = 2 * (phase - 1) + beat_index
                if diagnostic_expected:
                    state["waits"][index] += 1
                elif len(tx["captures"]) < (2 if beat_index else 1):
                    # This miss may capture on this very edge; update below.
                    if not int(row["data_capture"]):
                        state["misses"][index] += 1
        if timed and live:
            assert int(row["alignment"]) == int(alignment_expected), (prefix, row)
            assert int(row["diagnostic_wait"]) == int(diagnostic_expected), (prefix, row)
            assert int(row["policy_wait"]) == int(diagnostic_expected and phase == 1), (prefix, row)
        else:
            assert not int(row["policy_wait"]), (prefix, row)
        bus, status = int(row["bus"]), int(row["status"])
        read_bus, write_bus = bool(bus and status == 5), bool(bus and status == 6)
        data_bus = read_bus or write_bus
        assert int(row["write"]) == int(write_bus), (prefix, row)
        assert int(row["data_capture"]) == int(data_bus and int(row["ready"])), (prefix, row)
        assert int(row["code_capture"]) == int(bool(bus and status == 13 and int(row["ready"]))), (prefix, row)
        if bus:
            assert status in [5, 6, 13], (prefix, row)
        assert state["held"] is None or data_bus, (prefix, row)
        if data_bus:
            assert tx is not None and len(tx["captures"]) < 1 + odd, (prefix, row)
            beat = len(tx["captures"])
            assert status == (5 if phase == 1 else 6), (prefix, row)
            expected_address, expected_bhe = address + int(odd and beat == 1), int(odd and beat == 1)
            assert (int(row["address"], 16), int(row["bhe"])) == (expected_address, expected_bhe), (prefix, row)
            if write_bus:
                payload = value if not odd else ((value & 255) << 8 if beat == 0 else value >> 8)
                assert int(row["dataout"], 16) == payload, (prefix, row)
                assert len(state["tx"]) == 2 and len(state["tx"][0]["captures"]) == 1 + odd, (prefix, row)
            if read_bus and int(row["ready"]):
                payload = initial if not odd else ((initial & 255) << 8 | 0xd0 if beat == 0 else 0xba00 | (initial >> 8))
                assert int(row["datain"], 16) == payload, (prefix, row)
            metadata = (int(row["address"], 16), status, int(row["bhe"]), int(row["dataout"], 16) if write_bus else None)
            assert state["held"] is None or metadata == state["held"], (prefix, row)
            state["held"] = None if int(row["data_capture"]) else metadata
            if timed:
                assert int(row["owner"]) == 2, (prefix, row)
                if odd and beat == 1 and live:
                    assert tx["first"] is not None and cpu >= tx["first"], (prefix, row)
        if int(row["data_capture"]):
            tx["captures"].append(cpu + int(timed and not boundary))
            if write_bus:
                a, payload = int(row["address"], 16), int(row["dataout"], 16)
                lanes = []
                if not a & 1:
                    lanes.append((a & ~1, payload & 255))
                if not int(row["bhe"]):
                    lanes.append((a | 1, payload >> 8))
                for byte_address, byte in lanes:
                    assert byte_address in [address, address + 1], (prefix, row)
                    shift = 8 * (byte_address - address)
                    state["memory"] = (state["memory"] & ~(255 << shift)) | (byte << shift)
        assert int(row["memory_after"], 16) == state["memory"], (prefix, row)
        if timed and live and active:
            first_expected = bool(odd and tx["first"] is None and boundary and tx["captures"] and
                cpu >= max(tx["accept"] + 2 + int(f[10 + 2 * (phase - 1)]), tx["captures"][0]))
            final_expected = bool(boundary and len(tx["captures"]) == 1 + odd and
                (not odd or tx["first"] is not None) and cpu >= max(
                (tx["first"] + 2 + int(f[11 + 2 * (phase - 1)])) if odd else
                tx["accept"] + 2 + int(f[10 + 2 * (phase - 1)]), tx["captures"][-1]))
            assert int(row["first_tc"]) == int(first_expected), (prefix, row)
            assert int(row["final_tc"]) == int(final_expected), (prefix, row)
        if int(row["first_tc"]):
            assert timed and odd and boundary and tx is not None and tx["first"] is None and tx["captures"], (prefix, row)
            assert int(row["owner"]) == 2
            assert cpu == max(tx["accept"] + 2 + int(f[10 + 2 * (phase - 1)]), tx["captures"][0]), (prefix, row)
            tx["first"] = cpu
        if int(row["final_tc"]):
            assert timed and boundary and tx is not None and tx["final"] is None and len(tx["captures"]) == 1 + odd, (prefix, row)
            assert int(row["owner"]) == 2
            earliest = tx["first"] + 2 + int(f[11 + 2 * (phase - 1)]) if odd else tx["accept"] + 2 + int(f[10 + 2 * (phase - 1)])
            assert cpu == max(earliest, tx["captures"][-1]), (prefix, row)
            tx["final"] = cpu
        if int(row["data_start"]):
            assert phase < 2 and live and (not timed or boundary) and consumed == 6, (prefix, row)
            if phase:
                assert len(tx["captures"]) == 1 + odd and (not timed or tx["final"] is not None), (prefix, row)
            state["tx"].append({"accept": cpu, "captures": [], "first": None, "final": None})
        if int(row["flags_pending"]):
            assert phase == 2 and len(tx["captures"]) == 1 + odd and (not timed or tx["final"] is not None), (prefix, row)
            assert state["memory"] == value, (prefix, row)
        if timed and live:
            eligible = bool(int(row["flags_pending"]) and boundary and int(row["execute"]) and state["retire"] is None and
                state["start"] is not None and cpu - state["start"] >= 7 + 4 * odd + state["waits"][0] + state["waits"][1])
            assert int(row["flags_commit"]) == int(row["retired"]) == int(eligible), (prefix, row)
        if int(row["flags_commit"]):
            assert phase == 2 and len(tx["captures"]) == 1 + odd and state["counts"]["flags_commit"] == 0, (prefix, row)
            assert live and int(row["execute"]) and state["memory"] == value
            state["flags"] = expected_flags
        assert int(row["flags"], 16) == state["flags"], (prefix, row)
        if int(row["retired"]):
            assert state["retire"] is None and mode not in ABANDONED and state["flags"] == expected_flags, (prefix, row)
            assert phase == 2 and state["memory"] == value and (not timed or boundary), (prefix, row)
            assert int(row["ip"], 16) == (int(f[1], 16) + 6) & 0xffff, (prefix, row)
            state["retire"] = cpu
        if timed and live and state["retire"] is None:
            assert int(row["ip"], 16) == int(f[1], 16), (prefix, row)
        for field in events:
            state["counts"][field] += int(row[field])
        state["off"] += int((int(row["data_capture"]) or int(row["code_capture"])) and not boundary)
        if timed and live and state["start"] is not None:
            assert int(row["scheduled"]) == 3 + 4 * state["form"] + 2 * state["counts"]["alignment"] + state["waits"][0] + state["waits"][1], (prefix, row)
        state["aborted"] |= bool(int(row["cancel"]) or int(row["scope"]))
        state["last"] = row
    assert set(states) == set(caller), prefix
    for row in records:
        identifier = int(row["id"])
        state, f = states[identifier], caller[identifier]
        odd = int(f[4], 16) & 1
        assert (int(row["timed"]), int(row["warm"]), int(row["mode"]), int(row["odd"])) == (timed, warm, mode, odd)
        assert int(row["retired"]) == int(mode not in ABANDONED) and int(row["scope"]) == int(mode in SCOPE_MODES), (prefix, row)
        assert state["counts"]["start"] == 1 and state["off"] == int(row["off_boundary"]), (prefix, row)
        for event, summary in [("code_start", "code_accepts"), ("data_start", "data_accepts"),
            ("code_capture", "code_captures"), ("data_capture", "data_captures"), ("first_tc", "first_tc"),
            ("final_tc", "final_tc"), ("alignment", "alignment_count"), ("retired", "retired")]:
            # MAX deliberately has no private CODE admission diagnostic.
            if timed or event != "code_start":
                assert state["counts"][event] == int(row[summary]), (prefix, identifier, summary)
        assert state["form"] == int(row["form_count"])
        assert int(row["memory"], 16) == state["memory"] and (int(row["guard_before"], 16), int(row["guard_after"], 16)) == (0x3c, 0xc7)
        if mode not in RESET_MODES:
            assert int(row["gpr"], 16) == int(f[7], 16) and int(row["flags"], 16) == state["flags"], (prefix, row)
        read_captures = len(state["tx"][0]["captures"]) if state["tx"] else 0
        write_captures = len(state["tx"][1]["captures"]) if len(state["tx"]) == 2 else 0
        assert (int(row["read_captures"]), int(row["write_captures"])) == (read_captures, write_captures)
        assert (int(row["read_accepts"]), int(row["write_accepts"])) == (int(len(state["tx"]) >= 1), int(len(state["tx"]) == 2))
        assert [int(row[key]) for key in ["read_wait1", "read_wait2", "write_wait1", "write_wait2"]] == state["waits"]
        assert [int(row[key]) for key in ["read_miss1", "read_miss2", "write_miss1", "write_miss2"]] == state["misses"]
        if mode in ABANDONED:
            accepted = 0 if mode in [6, 13, 20] else 1 if mode in [7, 8, 9, 14, 15, 16, 21, 22, 23, 27] else 2
            assert len(state["tx"]) == accepted and state["retire"] is None and state["counts"]["flags_commit"] == 0, (prefix, row)
            if mode not in RESET_MODES:
                assert all(len(tx["captures"]) == 1 + odd for tx in state["tx"]), (prefix, row)
        if int(row["retired"]):
            assert state["consumes"] == 6 and state["counts"]["flags_commit"] == 1
            assert len(state["tx"]) == 2 and read_captures == write_captures == 1 + odd
            assert int(row["data_responses"]) == 2 and int(row["read_responses"]) == int(row["write_responses"]) == 1
            assert int(row["start_cpu"]) == state["start"] and int(row["retire_cpu"]) == state["retire"]
            assert int(row["elapsed"]) == state["retire"] - state["start"]
            assert int(row["ip"], 16) == (int(f[1], 16) + 6) & 0xffff
            if timed:
                assert state["waits"] == [int(f[10]), odd * int(f[11]), int(f[12]), odd * int(f[13])]
                minimum = 7 + 4 * odd + int(f[10]) + odd * int(f[11])
                assert int(row["scheduled"]) == minimum and int(row["elapsed"]) >= minimum
                assert int(row["first_tc"]) == 2 * odd and int(row["final_tc"]) == 2 and state["form"] == 1
    for tool in tools:
        log = data(prefix + "-" + tool + "-run.log").decode()
        matches = [m.groups() for line in log.splitlines() if (m := re.fullmatch(
            r"P06_CORE_RMW_PASS cases=(\d+) checks=(\d+) timed=(\d+) warm=(\d+) mode=(\d+)", line))]
        assert len(matches) == 1, (prefix, tool)
        count, checks, actual_timed, actual_warm, actual_mode = map(int, matches[0])
        assert (count, actual_timed, actual_warm, actual_mode) == (len(caller), timed, warm, mode) and checks > 0
    return len(records)


def commit_probe_text(source, new):
    package = (ROOT / "vendor/spk286/microcode/generated/spk286_microcode_pkg.sv").read_text()
    width = int(re.search(r"MC_WORD_WIDTH = (\d+)", package)[1])
    fragment = re.search(r"    assign p06_memory_result_pending = .*?\n    assign operation_retire = .*?;", source, re.S)[0]
    commit = re.search(r"    assign commit_flags = .*?;", source, re.S)[0]
    for name in ["MC_MOVE", "MC_COMMIT_FLAGS"]:
        constant = re.search(r"\b" + name + r" = ([^;]+);", package)[1]
        fragment = fragment.replace("spk286_microcode_pkg::" + name, constant)
        commit = commit.replace("spk286_microcode_pkg::" + name, constant)
    return ("module p06_rmw_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0" +
        (", parameter bit P06_RMW_TIMING=1'b0" if new else "") + ") (\n" +
        f"input logic [{width-1}:0] operation, input logic [2:0] temporary_valid_q,\n" +
        "input logic p06_moffs_read, p06_rmw_form, register_complete, move_word, allowed, flags_valid_q, result_disposed_q,\n" +
        "output logic p06_memory_result_pending, operation_retire, commit_flags" +
        (", p06_rmw_result_pending" if new else "") + ");\n" + fragment + "\n" + commit + "\nendmodule\n")


def check_components(receipt, ancestor, generated):
    components = receipt["components"]
    assert components == json.loads(data("component-checks.json"))
    assert components["status"] == "PINNED_COMPONENT_PREPARED" and components["ancestor_receipt_sha256"] == M6F_SHA256
    costs = components["costs"]
    labels = {"spk286_biu": {"original", "m6f", "rmw", "max"},
        "p06_instruction_duration": {"m6f", "rmw-off", "rmw", "max"},
        "executor_commit_assignments": {"m6f", "rmw-off", "rmw", "max"}}
    assert set(costs) == set(labels)
    for module, module_labels in labels.items():
        assert set(costs[module]) == module_labels
        artifact_module = "p06_rmw_commit_cost" if module == "executor_commit_assignments" else module
        for label in module_labels:
            assert generic_stats(HERE / f"generic-{artifact_module}-{label}.json") == costs[module][label]
            log = data(f"generic-{artifact_module}-{label}.log").decode()
            assert "Warning:" not in log and "ERROR:" not in log
        if module != "spk286_biu":
            assert costs[module]["rmw"]["register_bits"] == costs[module]["rmw-off"]["register_bits"] == costs[module]["m6f"]["register_bits"]
    assert costs["spk286_biu"]["rmw"] == costs["spk286_biu"]["m6f"]
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    assert costs["p06_instruction_duration"]["max"]["register_bits"] == 0 and costs["p06_instruction_duration"]["max"]["generic_cells"] == 3
    for label in ["m6f", "rmw-off", "rmw"]:
        stats = generic_stats(HERE / f"preabc-p06_instruction_duration-{label}.json")
        assert stats == components["duration_pre_abc"][label]
        log = data(f"preabc-p06_instruction_duration-{label}.log").decode()
        assert "Warning:" not in log and "ERROR:" not in log
    assert components["duration_rmw_off_pre_abc_identical"] is True
    assert components["duration_pre_abc"]["rmw-off"] == components["duration_pre_abc"]["m6f"]
    proofs = {"duration_rmw_off", "duration_max", "executor_assignments_rmw_off", "executor_assignments_max", "biu_max",
        "biu_source_identical_to_m6f", "max_biu_private_cones_absent", "duration_rmw_off_input_cone_absent",
        "duration_hist0_private_cones_absent", "executor_assignments_rmw_off_private_cone_absent", "executor_assignments_max_private_cone_absent"}
    assert set(components["proofs"]) == proofs and all(components["proofs"].values())
    for name in ["duration-rmw-off", "duration-max", "commit-rmw-off", "commit-max", "biu-max"]:
        proof, log = data(name + "-equivalence.ys").decode(), data(name + "-equivalence.log").decode()
        assert "Equivalence successfully proven!" in log and "ERROR:" not in log
        assert "delete -input" not in proof and "equiv_make gold gate equiv" in proof
        assert proof.count("equiv_status -assert") == 1 and "equiv_induct -seq 4" in proof
        deletions = [line for line in proof.splitlines() if line.startswith("delete ")]
        expected = ["delete -output " + " ".join("gate/" + output for output in BIU_OUTPUTS)] if name == "biu-max" else (
            ["delete -output gate/p06_rmw_result_pending"] if name.startswith("commit-") else [])
        assert deletions == expected, (name, deletions)
    golden = replace_once((ROOT / "vendor/spk286/rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
        "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ",")
    assert data("biu-max-gold.sv").decode() == golden
    for name, expected in ancestor["generated_cpu_sha256"].items():
        assert hashlib.sha256(data("m6f-component-source/private-rtl/" + name)).hexdigest() == expected
    old_policy = data("m6f-component-source/private-rtl/p06_instruction_duration.sv").decode()
    assert data("duration-m6f-gold.sv").decode() == replace_once(old_policy,
        "    output logic [7:0] elapsed_clocks, scheduled_clocks\n",
        "    output logic [7:0] elapsed_clocks, scheduled_clocks,\n    input logic rmw_form_valid\n")
    old_executor = data("m6f-component-source/private-rtl/spk286_micro_executor.sv").decode()
    assert data("commit-m6f.sv").decode() == commit_probe_text(old_executor, False)
    assert data("commit-m6g.sv").decode() == commit_probe_text(generated["spk286_micro_executor.sv"].read_text(), True)
    assert sha(generated["spk286_biu.sv"]) == ancestor["generated_cpu_sha256"]["spk286_biu.sv"]
    maximum = json.loads(data("generic-spk286_biu-max.json"))["modules"]["spk286_biu"]
    no_private_input_cone(maximum, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"), ("p06_code_admission", "1"),
        ("p06_read_wait_event", "0"), ("p06_alignment_event", "0")]:
        assert maximum["ports"][name]["bits"] == [constant]
    for label in ["rmw-off", "max"]:
        net = json.loads(data(f"generic-p06_instruction_duration-{label}.json"))["modules"]["p06_instruction_duration"]
        no_private_input_cone(net, ["rmw_form_valid"])
        if label == "max":
            no_private_input_cone(net, ["alignment_event"])
        net = json.loads(data(f"generic-p06_rmw_commit_cost-{label}.json"))["modules"]["p06_rmw_commit_cost"]
        no_private_input_cone(net, ["p06_rmw_form"])
        assert net["ports"]["p06_rmw_result_pending"]["bits"] == ["0"]
    for label in ["max", "aligned-write-off", "write-off", "aligned-rmw", "rmw"]:
        log = data("lint-" + label + ".log").decode()
        assert "%Error" not in log and "%Warning" not in log


def check_preservation(receipt, directory):
    assert receipt["preserved"] == {"odd-read": 834, "write-preserved": 834,
        "register-streams": {"programs": 688, "instructions": 1448}}
    for label, generator, top, parameter, ancestor_name, ancestor_hash, old_label in [
        ("odd-read", odd_vectors, "p06_core_odd_read_tb", ".P06_ODD_READ_PILOT(TIMED)", M6E, M6E_SHA256, "odd"),
        ("write-preserved", write_vectors, "p06_core_write_tb", ".P06_WRITE_PILOT(TIMED)", M6F, M6F_SHA256, "write"),
        ("register-streams", stream_vectors, "p06_core_iu_tb", ".P06_IU_PILOT(OVERLAP)", M6C, M6C_SHA256, "memory-iu"),
    ]:
        vector_name = "register-streams.txt" if label == "register-streams" else label + "-vectors.txt"
        path = directory / vector_name
        assert generator(path) == (688 if label == "register-streams" else 834)
        assert path.read_bytes() == data(vector_name)
        source = (ROOT / "sim/spk286_timing_pilot" / (top + ".sv")).read_text()
        extension = ",.P06_RMW_PILOT(TIMED)" + (",.P06_WRITE_PILOT(TIMED)" if label == "odd-read" else "")
        if label == "register-streams":
            source = replace_once(source, "module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);",
                "module p06_core_iu_tb #(parameter bit OVERLAP = 1'b1);\n    wire p06_code_board_ready=1, p06_data_board_ready=1;")
            extension = ",.P06_MEMORY_PILOT(1'b1),.P06_ODD_READ_PILOT(1'b1),.P06_WRITE_PILOT(1'b1),.P06_RMW_PILOT(1'b1)"
        assert data(label + "-tb.sv").decode() == replace_once(source, parameter, parameter + extension)
        assert sha(ROOT / ancestor_name / "receipt.json") == ancestor_hash
        previous_receipt = json.loads((ROOT / ancestor_name / "receipt.json").read_text())
        for temperature in ["normal", "cold"]:
            for tool in ["iverilog", "verilator"]:
                for suffix in ["summary.csv", "trace.csv"]:
                    old_name = f"{old_label}/{temperature}-{tool}-{suffix}"
                    old = artifact(ROOT / ancestor_name, old_name)
                    assert hashlib.sha256(old).hexdigest() == previous_receipt["artifacts_sha256"][old_name]
                    assert data(f"{label}/{temperature}-{tool}-{suffix}") == old


def main():
    global HERE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="Audit accepted raw artifacts before freezing")
    args = parser.parse_args()
    if args.input is not None:
        HERE = args.input.resolve()
        HERE.relative_to(ROOT.resolve())
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    is_frozen = args.input is None
    freeze = json.loads((HERE / "freeze.json").read_text()) if is_frozen else None
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_RMW_CPU_PASS" and receipt["matrix_cases"] == 858
    for flag in ["dual_traces_equal", "max_traces_equal", "previous_traces_preserved", "production_unchanged"]:
        assert receipt[flag] is True, flag
    if is_frozen:
        encoded = {name + ".gz" if name.endswith("-trace.csv") else name for name in receipt["artifacts_sha256"]}
        assert set(freeze["sha256"]) == encoded | {"audit.py", "receipt.json"}
        for name, expected in freeze["sha256"].items():
            assert sha(HERE / relative_name(name)) == expected
        assert sha(ROOT / "scripts/freeze_p06_rmw_cpu.py") == freeze["freezer_sha256"]
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    for name, expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected, name
    assert set(receipt["tool_versions"]) == {"iverilog", "verilator", "yosys"}
    for tool, version in receipt["tool_versions"].items():
        assert data(tool + "-version.log").decode().splitlines()[0] == version
    assert sha(ROOT / M6F / "receipt.json") == M6F_SHA256
    ancestor = json.loads((ROOT / M6F / "receipt.json").read_text())
    source_names = set(ancestor["sources_sha256"]) | {M6F + "/receipt.json", "scripts/build_p06_rmw_cpu.py",
        "scripts/check_p06_rmw_components.py", "scripts/run_p06_rmw_cpu.py", "scripts/run_p06_iu.py",
        "sim/spk286_timing_pilot/p06_core_iu_tb.sv", "sim/spk286_timing_pilot/p06_core_rmw_tb.sv"}
    assert set(receipt["sources_sha256"]) == source_names
    assert receipt["sources_sha256"][M6F + "/receipt.json"] == M6F_SHA256
    for name, expected in ancestor["sources_sha256"].items():
        assert receipt["sources_sha256"][name] == expected, name
    pairs = check_pairs(receipt["artifacts_sha256"])
    controls = {}
    with tempfile.TemporaryDirectory(prefix="reconstructed-", dir=out) as directory:
        directory = Path(directory)
        generated = build(directory)
        assert len(generated) == 8 and set(generated) == set(ancestor["generated_cpu_sha256"])
        assert {name: sha(path) for name, path in generated.items()} == receipt["generated_cpu_sha256"]
        for name, expected in receipt["generated_cpu_sha256"].items():
            assert hashlib.sha256(data("private-rtl/" + name)).hexdigest() == expected, name
        assert sha(generated["spk286_biu.sv"]) == ancestor["generated_cpu_sha256"]["spk286_biu.sv"]
        check_vectors(directory)
        for prefix, (timed, warm, mode, vector_name) in contexts().items():
            count = check_trace(prefix, pairs[prefix + "-iverilog-summary.csv"], directory / vector_name, timed, warm, mode)
            assert count == (14 if mode in MODES else 3 if mode == 29 else 858)
            if mode:
                controls[prefix.removeprefix("rmw/")] = count
        check_preservation(receipt, directory)
        bench = (ROOT / "sim/spk286_timing_pilot/p06_core_rmw_tb.sv").read_text()
        maximum = replace_once(bench, "parameter bit TIMED=1'b1", "parameter bit TIMED=1'b0")
        assert data("rmw-max-tb.sv").decode() == maximum
        assert data("rmw-original-tb.sv").decode() == "`define P06_ORIGINAL\n" + maximum
        assert NEGATIVES and set(receipt["negative_checks"]) == set(NEGATIVES)
        expected_negative_artifacts = {f"negative-{name}-{source}" for name, (_, source, *_) in NEGATIVES.items()}
        expected_negative_artifacts |= {f"negative-{name}-{suffix}" for name in NEGATIVES for suffix in
            ["build.log", "run.log", "trace.csv", "summary.csv"]}
        assert {name for name in receipt["artifacts_sha256"] if name.startswith("negative-")} == expected_negative_artifacts
        for name, (marker, source, before, after, vector_name, extra) in NEGATIVES.items():
            check = receipt["negative_checks"][name]
            assert check["returncode"] != 0
            assert {key: check[key] for key in ["marker", "source", "before", "after", "vectors", "extra"]} == {
                "marker": marker, "source": source, "before": before, "after": after, "vectors": vector_name, "extra": extra}
            log = data(f"negative-{name}-run.log").decode()
            assert marker in log and "P06_CORE_RMW_PASS" not in log
            assert data(f"negative-{name}-{source}").decode() == replace_once(generated[source].read_text(), before, after)
        assert set(receipt["max_units"]) == set(UNIT_NAMES)
        assert receipt["max_units"] == ancestor["max_units"]
        for name, marker in receipt["max_units"].items():
            adapted = private_bench(directory, name)
            text = adapted.read_text()
            if name.startswith("spk286_biu"):
                text = replace_once(text, "wire p06_scope_error,", "wire p06_alignment_event;\n    wire p06_scope_error,")
            assert data(name + "_tb.sv").decode() == text
            for tool in ["iverilog", "verilator"]:
                assert [line for line in data(f"{name}/{tool}-run.log").decode().splitlines() if "PASS" in line] == [marker]
        check_components(receipt, ancestor, generated)
    assert receipt["controls"] == controls
    assert sum(count for name, count in controls.items() if name != "mode29-warm") == 784 and controls["mode29-warm"] == 3
    timed_cases = 2 * receipt["matrix_cases"] + sum(controls.values())
    assert timed_cases == 2503
    for suffix in ["summary.csv", "trace.csv"]:
        assert data("original-max/normal-iverilog-" + suffix) == data("private-max/normal-iverilog-" + suffix)
    microcode = data("microcode.log")
    old_microcode = artifact(ROOT / M6F, "microcode.log")
    assert hashlib.sha256(old_microcode).hexdigest() == ancestor["artifacts_sha256"]["microcode.log"]
    assert microcode == old_microcode and microcode.decode().splitlines() == [
        "MICROCODE CHECK PASS: 123 entries, 743 words, 10-bit addresses, 8-bit control"]
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == DIRTY_GUARD_SHA256
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    cell_deltas = {name: {"generic_cells": costs["rmw"]["generic_cells"] - costs["m6f"]["generic_cells"],
        "register_bits": costs["rmw"]["register_bits"] - costs["m6f"]["register_bits"]}
        for name, costs in receipt["components"]["costs"].items()}
    result = {"status": "P06_M6G_FROZEN_RMW_CPU_PASS" if is_frozen else "P06_M6G_RAW_RMW_CPU_AUDIT_PASS",
        "evidence_frozen": is_frozen, "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": len(pairs), "matrix_cases": 858, "timed_cpu_cases": timed_cases,
        "directed_control_cases": 784, "deadline_cases": 3, "controls": controls, "max_cases_per_cpu": 858,
        "preserved_odd_read_cases_per_temperature": 834, "preserved_write_cases_per_temperature": 834,
        "preserved_register_programs_per_temperature": 688, "preserved_register_instructions_per_temperature": 1448,
        "private_cpu_reconstructed": True, "generated_cpu_sources": 8, "caller_fixtures_recreated": True,
        "per_edge_rmw_payload_and_visibility_checked": True, "read_write_phases_checked": True,
        "late_form_and_per_reference_alignment_checked": True, "write_wait_not_eu_charged": True,
        "flags_and_retirement_checked": True, "max_traces_equal": True, "previous_traces_preserved": True,
        "generic_component_deltas_from_m6f": cell_deltas,
        "formal_scope": "Isolated BIU/duration and extracted real executor pending/retire/commit_flags assignments; full CPU elaboration is lint, not formal equivalence",
        "components": receipt["components"], "negative_checks": receipt["negative_checks"],
        "production_guards_unchanged": True, "ancestor_receipt_sha256": M6F_SHA256,
        "receipt_sha256": sha(HERE / "receipt.json"), "scope": receipt["scope"]}
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
