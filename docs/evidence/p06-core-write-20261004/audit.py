#!/usr/bin/env python3
"""Audit M6f serialized A3 evidence without another simulation or synthesis.

WRITE payload, lanes and external visibility derive from the caller fixture.
The runner's summary validator is deliberately not used as this oracle.
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
from build_p06_write_cpu import build
from build_p06_register_cpu import replace_once
from check_p06_odd_components import BIU_INPUTS, BIU_OUTPUTS, no_private_input_cone
from run_p06_core_register import sha
from run_p06_memory_cpu import private_bench
from run_p06_odd_read_cpu import odd_vectors, controlled_vectors, UNIT_NAMES
from run_p06_pilot import generic_stats

M6E = "docs/evidence/p06-core-odd-read-20261004"
M6E_SHA256 = "42a54266c3d49bca026f26d9789db788abcfcb7211d5caa304a8767bc628da92"
DIRTY_GUARD_SHA256 = "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
MODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21]
ABANDONED = {3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21}
RESET_MODES = {5, 6, 11, 18, 21}
SCOPE_MODES = {7, 8, 12, 17, 20}
SUMMARY_FIELDS = {
    "id", "timed", "warm", "mode", "odd", "start_cpu", "retire_cpu", "elapsed",
    "code_accepts", "data_accepts", "code_captures", "data_captures", "code_responses",
    "data_responses", "code_external", "wait1", "wait2", "code_misses", "miss1", "miss2",
    "alignment_count", "first_tc", "final_tc", "first_tc_cpu", "off_boundary",
    "gpr", "flags", "ip", "retired", "scope", "memory", "guard_before", "guard_after", "scheduled",
}
TRACE_FIELDS = {
    "id", "edge", "boundary", "cpu_clock", "start", "code_start", "data_start",
    "code_capture", "data_capture", "first_tc", "final_tc", "gpr_write", "retired",
    "owner", "bus", "address", "status", "ready", "ip", "cursor", "gpr", "flags",
    "queue", "scope", "policy_wait", "diagnostic_wait", "alignment", "end_pending", "scheduled",
    "write", "bhe", "dataout", "memory_before", "memory_after", "execute", "cancel",
}
# Bind exact source mutations and independent failure markers before freezing.
NEGATIVES = {
    "alignment": ("A3 write alignment/wait budget oracle failed", "spk286.sv",
                  ".alignment_event(p06_timed_data && p06_alignment_event)", ".alignment_event(1'b0)", "write-vectors.txt", []),
    "write-as-read-wait": ("A3 write independent alignment/wait event oracle failed", "spk286_biu.sv",
                           "wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;", "wire p06_read_cycle = 1'b1;", "write-vectors.txt", []),
    "permit": ("A3 first eligible retirement oracle failed", "spk286.sv",
               "(!p06_result_pending || permit)", "1'b1", "write-vectors.txt", []),
    "end-handshake": ("A3 write retirement/architectural oracle failed", "spk286.sv",
                      ".retire_ready(execution_allowed && (operation_valid || p06_write_end_pending))",
                      ".retire_ready(execution_allowed && operation_valid)", "write-vectors.txt", []),
    "second-early": ("A3 write logical owner oracle failed: physical presence/second gate", "spk286_biu.sv",
                     "state_q == SECOND_TS || state_q == SECOND_TC ||", "1'b1 ||", "write-vectors.txt", []),
    "first-publication": ("A3 write word publication oracle failed", "spk286_biu.sv",
                          "assign p06_complete = sample_tc && state_q != ODD_TC && p06_board_ready && available;",
                          "assign p06_complete = sample_tc && p06_board_ready && (available || first_available);", "write-vectors.txt", []),
    "first-release": ("A3 write logical owner oracle failed", "spk286_biu.sv",
                      "(!P06_ODD_READ_TIMING || !address_q[0] || byte_q)", "1'b1", "write-control-vectors.txt", ["+mode=16"]),
    "payload-lane": ("A3 write caller-derived address/lane/payload oracle failed", "spk286_biu.sv",
                     "(address_q[0] ? {write_data_q[7:0], 8'h00} :",
                     "(address_q[0] ? {write_data_q[15:8], 8'h00} :", "write-vectors.txt", []),
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


def contexts():
    result = {
        "write/normal": (1, 1, 0, "write-vectors.txt"),
        "write/cold": (1, 0, 0, "write-vectors.txt"),
        "write/mode13-warm": (1, 1, 13, "write-deadline-vectors.txt"),
        "original-max/normal": (0, 1, 0, "write-vectors.txt"),
        "private-max/normal": (0, 1, 0, "write-vectors.txt"),
    }
    result.update({f"write/mode{mode}-{label}": (1, warm, mode,
                   "write-before-ready-vectors.txt" if mode == 15 else "write-control-vectors.txt")
                   for mode in MODES for label, warm in [("warm", 1), ("cold", 0)]})
    assert len(result) == 45
    return result


def check_pairs(artifacts):
    prefixes = set(contexts()) | {"odd-read/normal", "odd-read/cold"}
    assert len(prefixes) == 47
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
        if not name.startswith("odd-read/"):
            assert set(result[name][0]) == SUMMARY_FIELDS, name
    return result


def check_vectors(directory):
    path = directory / "write-vectors.txt"
    assert odd_vectors(path) == 834 and path.read_bytes() == data(path.name)
    fields = [line.split() for line in path.read_text().splitlines()]
    assert {int(f[0]) for f in fields} == set(range(834)) and all(len(f) == 14 for f in fields)
    assert sum(int(f[4], 16) & 1 for f in fields) == 741
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xffff for f in fields)
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xfffff for f in fields)
    assert any(int(f[5], 16) == (int(f[6], 16) & 0xffff) for f in fields)
    generate = directory / "control-generation"
    generate.mkdir()
    odd_vectors(generate / "odd-vectors.txt")
    assert (generate / "odd-vectors.txt").read_bytes() == data("control-generation/odd-vectors.txt")
    for old, new, count in zip(controlled_vectors(generate),
                               ["write-control-vectors.txt", "write-deadline-vectors.txt", "write-before-ready-vectors.txt"],
                               [14, 3, 12]):
        assert old.read_bytes() == data("control-generation/" + old.name)
        assert old.read_bytes() == data(new) and len(old.read_text().splitlines()) == count
        (directory / new).write_bytes(old.read_bytes())


def check_trace(prefix, records, path, timed, warm, mode, tools=("iverilog", "verilator")):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    assert {int(r["id"]) for r in records} == set(caller) and len(records) == len(caller)
    trace = csv.DictReader(io.StringIO(data(prefix + "-iverilog-trace.csv").decode()))
    assert set(trace.fieldnames) == TRACE_FIELDS, prefix
    states = {}
    events = ["start", "data_start", "code_capture", "data_capture", "first_tc", "final_tc", "alignment", "retired"]
    for row in trace:
        identifier = int(row["id"])
        assert identifier in caller, (prefix, identifier)
        f = caller[identifier]
        odd = int(f[4], 16) & 1
        value = int(f[6], 16) & 0xffff
        address = (int(f[3], 16) << 4) + int(f[4], 16)
        state = states.setdefault(identifier, {
            "edge": 0, "memory": int(f[5], 16), "captures": [], "accept_cpu": None,
            "first_cpu": None, "final_cpu": None, "start_cpu": None, "retire_cpu": None,
            "counts": {field: 0 for field in events}, "off_boundary": 0, "last": None, "held": None,
        })
        edge, cpu = int(row["edge"]), int(row["cpu_clock"])
        boundary = int(row["boundary"])
        assert edge == state["edge"] + 1, (prefix, identifier, edge)
        state["edge"] = edge
        for field in TRACE_FIELDS - {"id", "edge", "cpu_clock", "owner", "address", "status", "ip", "cursor",
                                      "gpr", "flags", "queue", "scheduled", "dataout", "memory_before", "memory_after"}:
            assert int(row[field]) in [0, 1], (prefix, field, row[field])
        assert 0 <= int(row["queue"]) <= 6, (prefix, row)
        assert int(row["memory_before"], 16) == state["memory"], (prefix, row)
        assert int(row["gpr_write"]) == 0, (prefix, row)
        assert int(row["gpr"], 16) == int(f[6], 16), (prefix, row)
        assert int(row["flags"], 16) == int(f[7], 16), (prefix, row)
        assert int(row["policy_wait"]) == 0, (prefix, row)
        if int(row["data_start"]):
            assert state["accept_cpu"] is None and (not timed or boundary), (prefix, row)
            state["accept_cpu"] = cpu
        if int(row["start"]):
            assert state["start_cpu"] is None and (not timed or boundary), (prefix, row)
            state["start_cpu"] = cpu
        if timed and mode not in ABANDONED:
            expected_alignment = bool(odd and boundary and state["accept_cpu"] is not None and
                                      cpu == state["accept_cpu"] + 1)
            assert int(row["alignment"]) == int(expected_alignment), (prefix, row)
        beat = len(state["captures"])
        write_bus = int(row["bus"]) and int(row["status"]) == 6
        assert int(row["write"]) == int(write_bus), (prefix, row)
        assert int(row["data_capture"]) == int(write_bus and int(row["ready"])), (prefix, row)
        assert state["held"] is None or write_bus, (prefix, row)
        if int(row["bus"]):
            assert int(row["status"]) in [6, 13], (prefix, row)
        if timed and (write_bus or int(row["first_tc"]) or int(row["final_tc"])):
            assert int(row["owner"]) == 2, (prefix, row)
        if write_bus:
            assert beat < 1 + odd and state["accept_cpu"] is not None, (prefix, row)
            expected_address = address + int(odd and beat == 1)
            expected_bhe = int(odd and beat == 1)
            expected_payload = value if not odd else ((value & 0xff) << 8 if beat == 0 else value >> 8)
            assert (int(row["address"], 16), int(row["bhe"]), int(row["dataout"], 16)) == (
                expected_address, expected_bhe, expected_payload), (prefix, row)
            metadata = (int(row["address"], 16), int(row["status"]), int(row["bhe"]), int(row["dataout"], 16))
            if state["held"] is not None:
                assert metadata == state["held"], (prefix, row)
            state["held"] = None if int(row["data_capture"]) else metadata
            if timed and odd and beat == 1 and mode not in ABANDONED:
                assert state["first_cpu"] is not None and cpu >= state["first_cpu"], (prefix, row)
        if int(row["data_capture"]):
            if not odd:
                state["memory"] = value
            elif beat == 0:
                state["memory"] = (state["memory"] & 0xff00) | (value & 0xff)
            else:
                state["memory"] = (state["memory"] & 0xff) | (value & 0xff00)
            state["captures"].append(cpu + int(timed and not boundary))
        assert int(row["memory_after"], 16) == state["memory"], (prefix, row)
        if int(row["first_tc"]):
            assert timed and odd and boundary and state["first_cpu"] is None and state["captures"], (prefix, row)
            assert cpu == max(state["accept_cpu"] + 2 + int(f[9]), state["captures"][0]), (prefix, row)
            state["first_cpu"] = cpu
        if int(row["final_tc"]):
            assert timed and boundary and state["final_cpu"] is None and len(state["captures"]) == 1 + odd, (prefix, row)
            earliest = (state["first_cpu"] + 2 + int(f[10])) if odd else state["accept_cpu"] + 2 + int(f[9])
            assert cpu == max(earliest, state["captures"][-1]), (prefix, row)
            state["final_cpu"] = cpu
        if int(row["end_pending"]):
            assert len(state["captures"]) == 1 + odd and (not timed or state["final_cpu"] is not None), (prefix, row)
        if timed and mode not in ABANDONED:
            eligible = int(row["end_pending"]) and boundary and int(row["execute"]) and not int(row["cancel"]) and not int(row["scope"]) and state["retire_cpu"] is None and cpu - state["start_cpu"] >= 3 + 2 * odd
            assert int(row["retired"]) == int(bool(eligible)), (prefix, row)
        if int(row["retired"]):
            assert state["retire_cpu"] is None and mode not in ABANDONED, (prefix, row)
            assert not timed or (boundary and int(row["end_pending"]) and state["final_cpu"] is not None), (prefix, row)
            assert int(row["ip"], 16) == (int(f[1], 16) + 3) & 0xffff, (prefix, row)
            state["retire_cpu"] = cpu
        for field in events:
            state["counts"][field] += int(row[field])
        state["off_boundary"] += int((int(row["data_capture"]) or int(row["code_capture"])) and not boundary)
        if timed and mode not in ABANDONED and state["start_cpu"] is not None:
            assert int(row["scheduled"]) == 3 + 2 * state["counts"]["alignment"], (prefix, row)
        state["last"] = row
    assert set(states) == set(caller), prefix
    for row in records:
        identifier = int(row["id"])
        state, f = states[identifier], caller[identifier]
        odd = int(f[4], 16) & 1
        assert state["counts"]["start"] == 1 and state["off_boundary"] == int(row["off_boundary"]), (prefix, row)
        assert (int(row["timed"]), int(row["warm"]), int(row["mode"]), int(row["odd"])) == (timed, warm, mode, odd)
        assert int(row["retired"]) == int(mode not in ABANDONED)
        assert int(row["scope"]) == int(mode in SCOPE_MODES), (prefix, row)
        for event, summary in [("data_start", "data_accepts"), ("code_capture", "code_captures"),
                               ("data_capture", "data_captures"), ("first_tc", "first_tc"),
                               ("final_tc", "final_tc"), ("alignment", "alignment_count"), ("retired", "retired")]:
            assert state["counts"][event] == int(row[summary]), (prefix, identifier, summary)
        assert int(row["memory"], 16) == state["memory"]
        assert (int(row["guard_before"], 16), int(row["guard_after"], 16)) == (0x3c, 0xc7)
        if mode not in RESET_MODES:
            assert int(row["gpr"], 16) == int(f[6], 16) and int(row["flags"], 16) == int(f[7], 16)
        if mode in ABANDONED - RESET_MODES - {19, 20}:
            assert len(state["captures"]) == 1 + odd
        if mode in [18, 19, 20, 21]:
            assert len(state["captures"]) == 0
        if mode in [19, 20, 21]:
            assert state["accept_cpu"] is None and state["memory"] == int(f[5], 16)
        if int(row["retired"]):
            assert int(row["memory"], 16) == int(f[6], 16) & 0xffff
            assert len(state["captures"]) == 1 + odd and int(row["data_accepts"]) == int(row["data_responses"]) == 1
            assert int(row["ip"], 16) == (int(f[1], 16) + 3) & 0xffff
            assert int(row["start_cpu"]) == state["start_cpu"] and int(row["retire_cpu"]) == state["retire_cpu"]
            assert int(row["elapsed"]) == state["retire_cpu"] - state["start_cpu"]
            if timed:
                assert (int(row["wait1"]), int(row["wait2"])) == (int(f[9]), odd * int(f[10]))
                assert int(row["scheduled"]) == 3 + 2 * odd and int(row["elapsed"]) >= 3 + 2 * odd
                assert int(row["first_tc"]) == odd and int(row["final_tc"]) == 1
                assert int(row["first_tc_cpu"]) == (state["first_cpu"] or 0)
    for tool in tools:
        log = data(prefix + "-" + tool + "-run.log").decode()
        matches = [m.groups() for line in log.splitlines() if (m := re.fullmatch(
            r"P06_CORE_WRITE_PASS cases=(\d+) checks=(\d+) timed=(\d+) warm=(\d+) mode=(\d+)", line))]
        assert len(matches) == 1, (prefix, tool)
        count, checks, actual_timed, actual_warm, actual_mode = map(int, matches[0])
        assert (count, actual_timed, actual_warm, actual_mode) == (len(caller), timed, warm, mode) and checks > 0
    return len(records)


def check_components(receipt, ancestor):
    components = receipt["components"]
    assert components == json.loads(data("component-checks.json"))
    assert components["ancestor_receipt_sha256"] == M6E_SHA256
    costs = components["costs"]
    assert set(costs) == {"spk286_biu", "p06_instruction_duration"}
    labels = {"spk286_biu": {"original", "m6e", "write-off", "write", "max"},
              "p06_instruction_duration": {"m6e", "write-off", "write", "late-off", "max"}}
    for module, module_labels in labels.items():
        assert set(costs[module]) == module_labels
        for label in module_labels:
            assert generic_stats(HERE / f"generic-{module}-{label}.json") == costs[module][label]
            log = data(f"generic-{module}-{label}.log").decode()
            assert "Warning:" not in log and "ERROR:" not in log
        assert costs[module]["write-off"]["register_bits"] == costs[module]["m6e"]["register_bits"]
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    assert costs["spk286_biu"]["write"]["register_bits"] == costs["spk286_biu"]["m6e"]["register_bits"]
    assert costs["p06_instruction_duration"]["write"]["register_bits"] == costs["p06_instruction_duration"]["m6e"]["register_bits"] + 1
    assert costs["p06_instruction_duration"]["max"]["register_bits"] == 0
    proofs = {"biu_max", "biu_write_off", "duration_write_off", "duration_max",
              "max_biu_private_input_cones_absent", "duration_late0_alignment_cone_absent",
              "duration_hist0_alignment_cone_absent"}
    assert set(components["proofs"]) == proofs and all(components["proofs"].values())
    for name in ["biu-max", "biu-write-off", "duration-write-off", "duration-max"]:
        proof, log = data(name + "-equivalence.ys").decode(), data(name + "-equivalence.log").decode()
        assert "Equivalence successfully proven!" in log and "ERROR:" not in log
        assert "delete -input" not in proof and "equiv_make gold gate equiv" in proof
        assert proof.count("equiv_status -assert") == 1 and "equiv_induct -seq 4" in proof
        deletions = [line for line in proof.splitlines() if line.startswith("delete ")]
        assert deletions == (["delete -output " + " ".join("gate/" + output for output in BIU_OUTPUTS)] if name == "biu-max" else [])
    golden = replace_once((ROOT / "vendor/spk286/rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
                          "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ",")
    assert data("biu-max-gold.sv").decode() == golden
    maximum = json.loads(data("generic-spk286_biu-max.json"))["modules"]["spk286_biu"]
    no_private_input_cone(maximum, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"), ("p06_code_admission", "1"),
                           ("p06_read_wait_event", "0"), ("p06_alignment_event", "0")]:
        assert maximum["ports"][name]["bits"] == [constant], name
    for label in ["late-off", "max"]:
        no_private_input_cone(json.loads(data(f"generic-p06_instruction_duration-{label}.json"))["modules"]["p06_instruction_duration"], ["alignment_event"])
    for label in ["max", "aligned-read", "read", "aligned-write", "write"]:
        log = data("lint-" + label + ".log").decode()
        assert "%Error" not in log and "%Warning" not in log
    for name in ancestor["generated_cpu_sha256"]:
        assert hashlib.sha256(data("m6e-component-source/private-rtl/" + name)).hexdigest() == ancestor["generated_cpu_sha256"][name]


def main():
    global HERE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="Audit the accepted raw build before its freeze")
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
    assert receipt["status"] == "P06_PRIVATE_WRITE_CPU_PASS" and receipt["matrix_cases"] == 834
    for flag in ["dual_traces_equal", "max_traces_equal", "read_traces_preserved", "production_unchanged"]:
        assert receipt[flag] is True, flag
    if is_frozen:
        encoded = {name + ".gz" if name.endswith("-trace.csv") else name for name in receipt["artifacts_sha256"]}
        assert set(freeze["sha256"]) == encoded | {"audit.py", "receipt.json"}
        for name, expected in freeze["sha256"].items():
            assert sha(HERE / relative_name(name)) == expected, name
        assert sha(ROOT / "scripts/freeze_p06_write_cpu.py") == freeze["freezer_sha256"]
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    for name, expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected, name
    assert sha(ROOT / M6E / "receipt.json") == M6E_SHA256
    ancestor = json.loads((ROOT / M6E / "receipt.json").read_text())
    source_names = set(ancestor["sources_sha256"]) | {
        M6E + "/receipt.json", "scripts/run_p06_write_cpu.py", "scripts/build_p06_write_cpu.py",
        "scripts/check_p06_write_components.py", "rtl/spk286_timing_pilot/p06_write_biu_connection.svh",
        "sim/spk286_timing_pilot/p06_core_write_tb.sv",
    }
    assert set(receipt["sources_sha256"]) == source_names
    assert receipt["sources_sha256"][M6E + "/receipt.json"] == M6E_SHA256
    for name, expected in ancestor["sources_sha256"].items():
        assert receipt["sources_sha256"][name] == expected, name
    pairs = check_pairs(receipt["artifacts_sha256"])
    controls = {}
    with tempfile.TemporaryDirectory(prefix="reconstructed-", dir=out) as directory:
        directory = Path(directory)
        generated = build(directory)
        assert len(generated) == 8 and set(generated) == set(ancestor["generated_cpu_sha256"])
        assert {name: sha(path) for name, path in generated.items()} == receipt["generated_cpu_sha256"]
        # The restored original WRITE payload remains the only retained word.
        biu = generated["spk286_biu.sv"].read_text()
        for declaration in ["logic data_active_q, write_q, second_q, canceled_q, byte_q, io_q;",
                            "logic [23:0] address_q;", "logic [15:0] write_data_q;", "logic [7:0] low_byte_q;"]:
            assert biu.count(declaration) == 1, declaration
        assert "wire p06_read_cycle = !P06_WRITE_TIMING || !write_q;" in biu
        assert "(memory_write != p06_timed_write)" in generated["spk286.sv"].read_text()
        check_vectors(directory)
        for prefix, (timed, warm, mode, vector_name) in contexts().items():
            count = check_trace(prefix, pairs[prefix + "-iverilog-summary.csv"], directory / vector_name, timed, warm, mode)
            assert count == (12 if mode == 15 else 14 if mode in MODES else 3 if mode == 13 else 834)
            if mode:
                controls[prefix.removeprefix("write/")] = count
        assert receipt["preserved"] == {"odd-read": 834}
        read_vectors = directory / "read-vectors.txt"
        assert odd_vectors(read_vectors) == 834 and read_vectors.read_bytes() == data(read_vectors.name)
        preserved_bench = replace_once((ROOT / "sim/spk286_timing_pilot/p06_core_odd_read_tb.sv").read_text(),
                                      ".P06_ODD_READ_PILOT(TIMED)", ".P06_ODD_READ_PILOT(TIMED),.P06_WRITE_PILOT(TIMED)")
        assert data("read-preservation-tb.sv").decode() == preserved_bench
        for temperature in ["normal", "cold"]:
            for tool in ["iverilog", "verilator"]:
                for suffix in ["summary.csv", "trace.csv"]:
                    old_name = f"odd/{temperature}-{tool}-{suffix}"
                    old_bytes = artifact(ROOT / M6E, old_name)
                    assert hashlib.sha256(old_bytes).hexdigest() == ancestor["artifacts_sha256"][old_name]
                    assert data(f"odd-read/{temperature}-{tool}-{suffix}") == old_bytes
        bench = (ROOT / "sim/spk286_timing_pilot/p06_core_write_tb.sv").read_text()
        maximum = replace_once(bench, "parameter bit TIMED=1'b1", "parameter bit TIMED=1'b0")
        assert data("write-max-tb.sv").decode() == maximum
        assert data("write-original-tb.sv").decode() == "`define P06_ORIGINAL\n" + maximum
        assert NEGATIVES and set(receipt["negative_checks"]) == set(NEGATIVES)
        for name, (marker, source, before, after, vector_name, extra) in NEGATIVES.items():
            check = receipt["negative_checks"][name]
            assert check["returncode"] != 0
            assert {key: check[key] for key in ["marker", "source", "before", "after", "vectors", "extra"]} == {
                "marker": marker, "source": source, "before": before, "after": after, "vectors": vector_name, "extra": extra}
            log = data(f"negative-{name}-run.log").decode()
            assert marker in log and "P06_CORE_WRITE_PASS" not in log
            assert data(f"negative-{name}-{source}").decode() == replace_once(generated[source].read_text(), before, after)
        assert set(receipt["max_units"]) == set(UNIT_NAMES)
        for name, marker in receipt["max_units"].items():
            adapted = private_bench(directory, name)
            text = adapted.read_text()
            if name.startswith("spk286_biu"):
                text = replace_once(text, "wire p06_scope_error,", "wire p06_alignment_event;\n    wire p06_scope_error,")
            assert data(name + "_tb.sv").decode() == text
            for tool in ["iverilog", "verilator"]:
                assert [line for line in data(f"{name}/{tool}-run.log").decode().splitlines() if "PASS" in line] == [marker]
    assert receipt["controls"] == controls
    assert sum(count for name, count in controls.items() if name != "mode13-warm") == 556
    assert controls["mode13-warm"] == 3
    timed_cases = 2 * receipt["matrix_cases"] + sum(controls.values())
    assert timed_cases == 2227
    for suffix in ["summary.csv", "trace.csv"]:
        assert data("original-max/normal-iverilog-" + suffix) == data("private-max/normal-iverilog-" + suffix)
    check_components(receipt, ancestor)
    microcode = data("microcode.log")
    old_microcode = artifact(ROOT / M6E, "microcode.log")
    assert hashlib.sha256(old_microcode).hexdigest() == ancestor["artifacts_sha256"]["microcode.log"]
    assert microcode == old_microcode and microcode.decode().splitlines() == [
        "MICROCODE CHECK PASS: 123 entries, 743 words, 10-bit addresses, 8-bit control"]
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == DIRTY_GUARD_SHA256
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    result = {
        "status": "P06_M6F_FROZEN_WRITE_CPU_PASS" if is_frozen else "P06_M6F_RAW_WRITE_CPU_AUDIT_PASS",
        "evidence_frozen": is_frozen, "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": len(pairs), "matrix_cases": 834, "timed_cpu_cases": timed_cases,
        "directed_control_cases": 556, "deadline_cases": 3, "controls": controls,
        "max_cases_per_cpu": 834, "preserved_odd_read_cases_per_temperature": 834,
        "private_cpu_reconstructed": True, "generated_cpu_sources": 8,
        "caller_fixtures_recreated": True, "per_edge_write_payload_and_visibility_checked": True,
        "serial_end_and_minimum_budget_checked": True, "write_wait_not_eu_charged": True,
        "max_traces_equal": True, "read_traces_preserved": True,
        "components": receipt["components"], "negative_checks": receipt["negative_checks"],
        "production_guards_unchanged": True, "ancestor_receipt_sha256": M6E_SHA256,
        "receipt_sha256": sha(HERE / "receipt.json"), "scope": receipt["scope"],
    }
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
