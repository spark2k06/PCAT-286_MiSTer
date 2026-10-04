#!/usr/bin/env python3
"""Audit frozen M6d evidence without new simulation, synthesis or fitting."""
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
from build_p06_memory_cpu import build, replace_once
from run_p06_core_register import sha, sources
from run_p06_read_stream import stream_vectors, control_vectors, validate_rows

M6C_RECEIPT = "docs/evidence/p06-core-memory-20261004/receipt.json"
M6C_RECEIPT_SHA256 = "59e8738bc24251b0a8ad5670435fd3987394eba858cd130943934b3fe5384f65"
DIRTY_GUARD_SHA256 = "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
NEGATIVES = {
    "permit": ("read stream first eligible commit oracle failed", "spk286.sv",
               "(!p06_result_pending || permit)", "1'b1"),
    "waits": ("read stream per-instruction READ wait budget oracle failed", "spk286.sv",
              ".read_wait_event(p06_timed_read && p06_read_wait_event)", ".read_wait_event(1'b0)"),
    "payload": ("read stream retained DATA association oracle failed", "spk286_biu.sv",
                ": raw_data_read_data;", ": (raw_data_read_data ^ 16'h0001);"),
}
SUMMARY_FIELDS = {
    "id", "timed", "warm", "mode", "count", "read_index", "start_cpu", "retire_cpu",
    "elapsed", "data_external", "data_accepts", "data_captures", "data_responses",
    "code_accepts", "code_captures", "code_external", "code_misses", "data_misses",
    "off_boundary", "gpr", "flags", "ip", "recovered", "action_retired", "action_captures",
    "recovery_resets", "paused_waits",
}
TRACE_FIELDS = {
    "id", "recovered", "edge", "boundary", "cpu_clock", "read_index", "start",
    "code_start", "data_start", "code_capture", "data_capture", "code_complete",
    "data_complete", "gpr_write", "retired", "owner", "address", "status", "ready",
    "ip", "cursor", "gpr", "flags", "queue", "scope", "policy_read_wait",
    "diagnostic_read_wait", "tmp0_pending", "scheduled",
}


def relative_name(name):
    path = Path(name)
    assert not path.is_absolute() and not path.drive and ".." not in path.parts, name
    assert path.as_posix() == name, name
    return path


def data(name):
    path = HERE / relative_name(name)
    compressed = Path(str(path) + ".gz")
    assert not (path.is_file() and compressed.is_file()), f"Ambiguous frozen artifact: {name}"
    return path.read_bytes() if path.is_file() else gzip.decompress(compressed.read_bytes())


def rows(name):
    return list(csv.DictReader(io.StringIO(data(name).decode())))


def expected_sources():
    names = ["scripts/run_p06_read_stream.py", "scripts/build_p06_memory_cpu.py",
             "scripts/run_p06_memory_cpu.py", "scripts/build_p06_shared_bus.py",
             "scripts/build_p06_data_biu.py", "scripts/build_p06_iu_cpu.py",
             "scripts/build_p06_fetch_cpu.py", "scripts/build_p06_register_cpu.py",
             "scripts/run_p06_iu.py", "scripts/run_p06_core_register.py",
             "scripts/run_p06_timed_register.py", "scripts/run_p06_pilot.py",
             "scripts/run_p06_timed_fetch.py", "rtl/spk286_timing_pilot/p06_clock.sv",
             "rtl/spk286_timing_pilot/p06_instruction_duration.sv", "config.tcl",
             "scripts/test_at_landmark_dma.sh", "rtl/spk286_integration/spk286_integration.qip",
             M6C_RECEIPT, "vendor/spk286/sim/unit/spk286_signals.svh",
             "sim/spk286_timing_pilot/p06_core_read_stream_tb.sv"]
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT / "rtl/spk286_timing_pilot").glob("*connection.svh")
              if "odd" not in p.name]
    return {p.relative_to(ROOT).as_posix() for p in sources()} | set(names)


def contexts():
    result = {"streams/normal": (1, 1, 0, "streams.txt"),
              "streams/cold": (1, 0, 0, "streams.txt"),
              "streams/mode12-warm": (1, 1, 12, "deadline-streams.txt"),
              "original-max/normal": (0, 1, 0, "streams.txt"),
              "private-max/normal": (0, 1, 0, "streams.txt")}
    result.update({f"streams/mode{mode}-{label}": (1, warm, mode, "selected-streams.txt")
                   for mode in range(1, 10) for label, warm in [("warm", 1), ("cold", 0)]})
    assert len(result) == 23
    return result


def check_pairs(artifacts):
    pairs = {}
    expected = {prefix + "-iverilog-summary.csv" for prefix in contexts()}
    actual = {name for name in artifacts if name.endswith("-iverilog-summary.csv")}
    assert actual == expected, "Missing or unexpected dual-simulator stream summaries"
    assert {name for name in artifacts if name.endswith("-verilator-summary.csv")} == {
        name.replace("-iverilog-", "-verilator-") for name in expected}
    expected_traces = {name.removesuffix("summary.csv") + "trace.csv" for name in expected}
    expected_traces |= {name.replace("-iverilog-", "-verilator-") for name in expected_traces}
    assert {name for name in artifacts if name.endswith("-trace.csv") and
            ("-iverilog-" in name or "-verilator-" in name)} == expected_traces
    for name in sorted(expected):
        for left in [name, name.removesuffix("summary.csv") + "trace.csv"]:
            right = left.replace("-iverilog-", "-verilator-")
            assert left in artifacts and right in artifacts and data(left) == data(right), left
        pairs[name] = rows(name)
        assert pairs[name] and set(pairs[name][0]) == SUMMARY_FIELDS, name
    return pairs


def check_trace(prefix, records, vector_path, timed, warm, mode):
    caller = {int(f[0]): f for f in (line.split() for line in vector_path.read_text().splitlines())}
    trace = rows(prefix + "-iverilog-trace.csv")
    assert trace and set(trace[0]) == TRACE_FIELDS, prefix
    assert {int(r["id"]) for r in trace} == set(caller), prefix
    recovered = mode in range(3, 9)
    last_edge, retired, committed, writes = {}, {}, {}, {}
    for r in trace:
        identifier, phase, edge = int(r["id"]), int(r["recovered"]), int(r["edge"])
        f = caller[identifier]
        assert phase in ([0, 1] if recovered else [0]), (prefix, r)
        key = (identifier, phase)
        assert edge == last_edge.get(key, 0) + 1, (prefix, key, edge)
        last_edge[key] = edge
        assert 0 <= int(r["read_index"]) < int(f[1]), (prefix, r)
        for field in ["boundary", "start", "code_start", "data_start", "code_capture", "data_capture",
                      "code_complete", "data_complete", "gpr_write", "retired", "ready", "scope",
                      "policy_read_wait", "diagnostic_read_wait", "tmp0_pending"]:
            assert int(r[field]) in [0, 1], (prefix, field, r[field])
        assert 0 <= int(r["queue"]) <= 6, (prefix, r)
        # Capture flags are sampled before the edge, while status/address are
        # printed after it. A legal same-edge owner handoff can change them.
        if int(r["data_capture"]) or int(r["code_capture"]):
            assert int(r["ready"]) == 1, (prefix, r)
        committed.setdefault(key, int(f[5], 16))
        writes.setdefault(key, set())
        if int(r["gpr_write"]):
            index = int(r["read_index"])
            assert index not in writes[key], (prefix, key, index)
            writes[key].add(index)
            value = (int(f[10], 16) >> (16 * index)) & 0xffff
            if phase:
                value ^= 0xa55a
            committed[key] = (int(f[5], 16) & ~0xffff) | value
        assert int(r["gpr"], 16) == committed[key], (prefix, r)
        assert int(r["flags"], 16) == int(f[6], 16), (prefix, r)
        if int(r["retired"]):
            index = retired.get(key, 0)
            assert int(r["read_index"]) == index, (prefix, r)
            first_ip = int(f[2], 16) ^ (0x400 if phase else 0)
            assert int(r["ip"], 16) == (first_ip + 3 * (index + 1)) & 0xffff, (prefix, r)
        retired[key] = retired.get(key, 0) + int(r["retired"])
    for identifier, f in caller.items():
        assert retired[(identifier, int(recovered))] == int(f[1]), (prefix, identifier)
        assert writes[(identifier, int(recovered))] == set(range(int(f[1]))), (prefix, identifier)
        if recovered:
            assert retired[(identifier, 0)] == 1, (prefix, identifier)
            assert writes[(identifier, 0)] == {0}, (prefix, identifier)
    for tool in ["iverilog", "verilator"]:
        log = data(prefix + "-" + tool + "-run.log").decode()
        pattern = r"P06_CORE_READ_STREAM_PASS cases=(\d+) checks=(\d+) timed=(\d+) warm=(\d+) mode=(\d+)"
        matches = [match.groups() for line in log.splitlines()
                   if (match := re.fullmatch(pattern, line))]
        assert len(matches) == 1, (prefix, tool)
        count, checks, actual_timed, actual_warm, actual_mode = map(int, matches[0])
        assert (count, actual_timed, actual_warm, actual_mode) == (len(caller), timed, warm, mode)
        assert checks > 0
    # The summary helper checks values and IP against the caller, rather than
    # treating dual-simulator agreement or a PASS marker as an architectural oracle.
    return validate_rows(records, vector_path, timed, warm, mode)


def check_vectors(directory):
    path = directory / "streams.txt"
    assert stream_vectors(path) == 240 and path.read_bytes() == data(path.name)
    fields = [line.split() for line in path.read_text().splitlines()]
    assert {int(f[0]) for f in fields} == set(range(240))
    assert sum(int(f[1]) for f in fields) == 1120
    assert {int(f[1]) for f in fields} == {2, 4, 8}
    assert {int(f[2], 16) for f in fields} == {0x100, 0x101}
    assert any((int(f[10], 16) & 0xffff) == (int(f[5], 16) & 0xffff) for f in fields)
    selected = control_vectors(directory)
    assert len(selected.read_text().splitlines()) == 19
    assert selected.read_bytes() == data(selected.name)
    assert sum(int(line.split()[1]) for line in selected.read_text().splitlines()) == 86
    lines = path.read_text().splitlines()
    chosen = [next(line for line in lines if line.split()[1:3] == ["2", "0100"] and
                   line.split()[7:9] == ["0", "0"] and int(line.split()[11], 16) ==
                   sum(pattern << (2 * n) for n in range(2))) for pattern in range(3)]
    deadline = directory / "deadline-streams.txt"
    deadline.write_text("\n".join(chosen) + "\n")
    assert deadline.read_bytes() == data(deadline.name) and len(chosen) == 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    freeze = json.loads((HERE / "freeze.json").read_text())
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_READ_STREAM_PASS"
    for flag in ["dual_traces_equal", "max_traces_equal", "generated_rtl_unchanged", "production_unchanged"]:
        assert receipt[flag] is True, flag
    assert receipt["streams"] == 240 and receipt["instructions_per_matrix"] == 1120
    assert receipt["new_rtl_cost"] == 0
    assert freeze["sha256"] and receipt["sources_sha256"] and receipt["artifacts_sha256"]
    encoded = {name + ".gz" if name.endswith("-trace.csv") else name for name in receipt["artifacts_sha256"]}
    assert set(freeze["sha256"]) == encoded | {"audit.py", "receipt.json"}, "Incomplete frozen manifest"
    for name, expected in freeze["sha256"].items():
        assert sha(HERE / relative_name(name)) == expected, name
    assert sha(ROOT / "scripts/freeze_p06_read_stream.py") == freeze["freezer_sha256"]
    assert set(receipt["sources_sha256"]) == expected_sources(), "Incomplete accepted source coverage"
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    for name, expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected, name
    assert sha(ROOT / M6C_RECEIPT) == M6C_RECEIPT_SHA256
    old = json.loads((ROOT / M6C_RECEIPT).read_text())
    assert old["status"] == "P06_PRIVATE_MEMORY_CPU_PASS"
    assert receipt["sources_sha256"][M6C_RECEIPT] == M6C_RECEIPT_SHA256
    for name in set(old["sources_sha256"]) & set(receipt["sources_sha256"]):
        assert receipt["sources_sha256"][name] == old["sources_sha256"][name], name
    assert receipt["generated_cpu_sha256"] == old["generated_cpu_sha256"]
    pairs = check_pairs(receipt["artifacts_sha256"])
    controls = {}
    with tempfile.TemporaryDirectory(prefix="reconstructed-", dir=out) as directory:
        directory = Path(directory)
        regenerated = build(directory)
        assert {name: sha(path) for name, path in regenerated.items()} == old["generated_cpu_sha256"]
        check_vectors(directory)
        for prefix, (timed, warm, mode, vector_name) in contexts().items():
            count = check_trace(prefix, pairs[prefix + "-iverilog-summary.csv"], directory / vector_name,
                                timed, warm, mode)
            if mode:
                controls[prefix.removeprefix("streams/")] = count
                assert count == (6 if mode == 12 else 86), prefix
            else:
                assert count == 1120, prefix
        bench = (ROOT / "sim/spk286_timing_pilot/p06_core_read_stream_tb.sv").read_text()
        maximum = replace_once(bench, "parameter bit TIMED=1'b1", "parameter bit TIMED=1'b0")
        assert data("read-stream-max-tb.sv").decode() == maximum
        assert data("read-stream-original-tb.sv").decode() == "`define P06_ORIGINAL\n" + maximum
        assert set(receipt["negative_checks"]) == set(NEGATIVES)
        for name, (marker, source_name, before, after) in NEGATIVES.items():
            check = receipt["negative_checks"][name]
            assert check["returncode"] != 0 and check["marker"] == marker, name
            log = data(f"negative-{name}-run.log").decode()
            assert marker in log and "P06_CORE_READ_STREAM_PASS" not in log, name
            assert data(f"negative-{name}-{source_name}").decode() == replace_once(
                regenerated[source_name].read_text(), before, after), name
    assert receipt["controls"] == controls
    for suffix in ["summary.csv", "trace.csv"]:
        assert data("original-max/normal-iverilog-" + suffix) == data("private-max/normal-iverilog-" + suffix)
    for timed in [0, 1]:
        log = data(f"lint-full-{timed}.log").decode()
        assert "%Error" not in log and "%Warning" not in log
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == DIRTY_GUARD_SHA256
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    # Catch concurrent source edits during reconstruction and evidence checking.
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    result = {
        "status": "P06_M6D_FROZEN_READ_STREAM_PASS",
        "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": len(pairs), "streams": 240, "instructions_per_matrix": 1120,
        "controls": controls, "timed_stream_cases": 825, "timed_instructions": 3794,
        "private_cpu_reconstructed": True, "generated_rtl_unchanged": True, "new_rtl_cost": 0,
        "caller_fixtures_recreated": True, "architectural_summaries_checked": True,
        "max_traces_equal": True, "negative_checks": receipt["negative_checks"],
        "production_guards_unchanged": True, "receipt_sha256": sha(HERE / "receipt.json"),
        "ancestor_receipt_sha256": M6C_RECEIPT_SHA256, "scope": receipt["scope"],
    }
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
