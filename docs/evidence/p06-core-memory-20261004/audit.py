#!/usr/bin/env python3
"""Audit frozen M6c CPU evidence without new simulation, synthesis or fitting."""
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
from build_p06_memory_cpu import build
from run_p06_core_register import sha, vectors
from run_p06_iu import stream_vectors
from run_p06_memory_cpu import memory_vectors, directed_vectors, UNIT_NAMES
from run_p06_pilot import generic_stats

COUNTS = {
    "aligned_cases": 267, "warm": 267, "cold": 267, "max_memory": 267,
    "rr_ri_streams": 688, "rr_ri_instructions": 1448, "max_register": 208,
}
DIRECTED_MODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 20, 21]
NEGATIVES = {
    "permit": "A1 first eligible commit oracle failed",
    "duration": "A1 READ wait budget oracle failed",
    "read-waits": "A1 READ wait budget oracle failed",
    "pending": "A1 original TMP0 pending oracle failed",
    "config-00": "M6c requires REGISTER and FETCH timing",
    "config-01": "M6c requires REGISTER and FETCH timing",
    "config-10": "M6c requires REGISTER and FETCH timing",
}
MEMORY_FIELDS = {
    "id", "timed", "warm", "mode", "start_cpu", "retire_cpu", "elapsed",
    "data_accepts", "data_captures", "data_external", "data_misses", "gpr",
    "flags", "ip", "retired", "scope", "rr_started", "rr_retired",
}
COMPONENTS = {
    "spk286_biu": {
        "inputs": ["p06_cpu_boundary", "p06_board_ready", "p06_code_issue",
                   "p06_code_complete", "p06_code_canceled"],
        "outputs": {"p06_scope_error": "0", "p06_code_admission": "1",
                    "p06_scope_block": "0", "p06_read_wait_event": "0"},
    },
    "spk286_fetch": {
        "inputs": ["p06_cpu_boundary", "p06_board_ready", "p06_admission_enable", "p06_scope_block"],
        "outputs": {"p06_bus_issue": "0", "p06_bus_complete": "0", "p06_bus_canceled": "0"},
    },
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


def no_private_input_cone(module, inputs):
    private_bits = {b for p in inputs for b in module["ports"][p]["bits"] if isinstance(b, int)}
    cell_bits = {b for c in module["cells"].values() for bits in c["connections"].values()
                 for b in bits if isinstance(b, int)}
    output_bits = {b for p in module["ports"].values() if p["direction"] == "output"
                   for b in p["bits"] if isinstance(b, int)}
    assert not private_bits & (cell_bits | output_bits), inputs


def check_components(receipt, reconstructed):
    costs = receipt["components"]
    assert set(costs) == set(COMPONENTS)
    for name, interface in COMPONENTS.items():
        for label in ["original", "max", "timed"]:
            assert generic_stats(HERE / f"generic-{name}-{label}.json") == costs[name][label], (name, label)
        assert costs[name]["max"]["register_bits"] == costs[name]["original"]["register_bits"], name
        assert "Equivalence successfully proven!" in data(f"max-{name}-equivalence.log").decode(), name
        proof = data(f"max-{name}-equivalence.ys").decode()
        assert "delete -input" not in proof, name
        assert "equiv_status -assert" in proof and "equiv_make gold gate equiv" in proof, name
        maximum = json.loads(data(f"generic-{name}-max.json"))["modules"][name]
        no_private_input_cone(maximum, interface["inputs"])
        for port, constant in interface["outputs"].items():
            assert maximum["ports"][port]["bits"] == [constant], (name, port)
        golden = (ROOT / f"vendor/spk286/rtl/{name}.sv").read_text()
        anchor = f"module {name} ("
        assert golden.count(anchor) == 1, name
        golden = golden.replace(anchor, anchor + "\n    input logic " + ", ".join(interface["inputs"]) + ",")
        assert data(f"max-{name}-gold.sv").decode() == golden, name

    commit = receipt["commit_control"]
    assert set(commit) == {"0", "1"}
    for label in ["0", "1"]:
        assert generic_stats(HERE / f"generic-commit-control-{label}.json") == commit[label], label
        assert commit[label]["register_bits"] == 0, label
    maximum = json.loads(data("generic-commit-control-0.json"))["modules"]["p06_memory_commit_cost"]
    no_private_input_cone(maximum, ["operation", "temporary_valid_q", "p06_moffs_read", "move_word"])
    assert maximum["ports"]["p06_memory_result_pending"]["bits"] == ["0"]
    assert maximum["ports"]["operation_retire"]["bits"] == maximum["ports"]["register_complete"]["bits"]
    package = (ROOT / "vendor/spk286/microcode/generated/spk286_microcode_pkg.sv").read_text()
    width = int(re.search(r"MC_WORD_WIDTH = (\d+)", package)[1])
    move = re.search(r"MC_MOVE = ([^;]+);", package)[1]
    executor = reconstructed["spk286_micro_executor.sv"].read_text()
    fragment = re.search(r"    assign p06_memory_result_pending = .*?\n    assign operation_retire = .*?;", executor, re.S)[0]
    fragment = fragment.replace("spk286_microcode_pkg::MC_MOVE", move)
    probe = ("module p06_memory_commit_cost #(parameter bit P06_MEMORY_TIMING=1'b0) (\n" +
             f"input logic [{width-1}:0] operation, input logic [2:0] temporary_valid_q,\n" +
             "input logic p06_moffs_read, register_complete, move_word,\n" +
             "output logic p06_memory_result_pending, operation_retire);\n" + fragment + "\nendmodule\n")
    assert data("p06_memory_commit_cost.sv").decode() == probe


def check_dual_traces(artifacts):
    pairs = {}
    for name in artifacts:
        if not name.endswith("-iverilog-summary.csv"):
            continue
        trace = name.removesuffix("summary.csv") + "trace.csv"
        for left in [name, trace]:
            right = left.replace("-iverilog-", "-verilator-")
            assert left in artifacts and right in artifacts, left
            assert data(left) == data(right), left
        pairs[name] = rows(name)
    expected = {"memory/normal", "memory/cold", "original-memory-max/normal", "private-memory-max/normal",
                "original-register-max/normal", "private-register-max/normal"}
    expected.update(f"memory/mode{mode}-{warm}" for mode in DIRECTED_MODES for warm in ["warm", "cold"])
    expected.update(f"{directory}/{label}" for directory in ["frozen-iu", "memory-iu"] for label in ["normal", "cold"])
    assert set(pairs) == {name + "-iverilog-summary.csv" for name in expected}, "Missing or unexpected dual-simulator CPU traces"
    # No hashed Verilator summary can silently lack its Icarus counterpart.
    for name in artifacts:
        if name.endswith("-verilator-summary.csv"):
            assert name.replace("-verilator-", "-iverilog-") in pairs, name
    return pairs


def check_summaries(receipt, pairs):
    counts = receipt["counts"]
    for name, expected in COUNTS.items():
        assert counts[name] == expected, (name, counts[name])
    caller = {int(fields[0]): fields for fields in
              [line.split() for line in data("memory-vectors.txt").decode().splitlines()]}
    assert set(caller) == set(range(267))
    memory = {}
    stream_groups = []
    for name, records in pairs.items():
        assert records, name
        if MEMORY_FIELDS <= records[0].keys():
            context = {(int(r["timed"]), int(r["warm"]), int(r["mode"])) for r in records}
            assert len(context) == 1, name
            context = next(iter(context))
            memory.setdefault(context, []).append((name, records))
        elif {"id", "instruction", "form", "elapsed", "gpr", "flags"} <= records[0].keys():
            stream_groups.append((name, records))
    for warm in [0, 1]:
        groups = memory[(1, warm, 0)]
        assert len(groups) == 1, ("timed aligned", warm)
        records = groups[0][1]
        assert len(records) == 267 and {int(r["id"]) for r in records} == set(range(267))
        for r in records:
            fields = caller[int(r["id"])]
            expected_gpr = (int(fields[6], 16) & ~0xffff) | int(fields[5], 16)
            assert int(r["gpr"], 16) == expected_gpr
            assert int(r["flags"], 16) == int(fields[7], 16)
            assert int(r["ip"], 16) == (int(fields[1], 16) + 3) & 0xffff
            assert int(r["retired"]) == 1 and int(r["scope"]) == 0
            assert int(r["data_accepts"]) == int(r["data_captures"]) == 1
            assert int(r["data_external"]) == int(fields[9])
            assert int(r["elapsed"]) == int(r["retire_cpu"]) - int(r["start_cpu"])
            assert int(r["elapsed"]) >= 5 + int(r["data_external"])
    maximum = memory.get((0, 0, 0), []) + memory.get((0, 1, 0), [])
    assert len(maximum) == 2, "Expected original and private MAX memory traces"
    original = [x for x in maximum if "original" in x[0]]
    private = [x for x in maximum if "private" in x[0]]
    assert len(original) == len(private) == 1
    for suffix in ["summary.csv", "trace.csv"]:
        left = original[0][0].removesuffix("summary.csv") + suffix
        right = private[0][0].removesuffix("summary.csv") + suffix
        assert data(left) == data(right), (left, right)
    assert len(original[0][1]) == len(private[0][1]) == 267
    assert {int(r["id"]) for r in original[0][1]} == set(range(267))
    for r in original[0][1]:
        fields = caller[int(r["id"])]
        assert int(r["gpr"], 16) == (int(fields[6], 16) & ~0xffff) | int(fields[5], 16)
        assert int(r["flags"], 16) == int(fields[7], 16)
        assert int(r["ip"], 16) == (int(fields[1], 16) + 3) & 0xffff
        assert int(r["retired"]) == 1 and int(r["scope"]) == 0
        assert int(r["data_accepts"]) == int(r["data_captures"]) == 1
    # Directed records carry their own mode/warm metadata, independent of paths.
    directed = {f"mode{mode}-{'warm' if warm else 'cold'}": len(groups[0][1])
                for (timed, warm, mode), groups in memory.items() if timed == 1 and mode != 0}
    assert all(len(groups) == 1 for (timed, _, mode), groups in memory.items() if timed == 1 and mode != 0)
    assert set(directed) == {f"mode{mode}-{warm}" for mode in DIRECTED_MODES for warm in ["warm", "cold"]}
    assert directed == counts["directed"], (directed, counts["directed"])
    for (timed, _, mode), groups in memory.items():
        if timed != 1 or mode == 0:
            continue
        vector_set = "tc-waits" if mode in [15, 17, 18] else "deadline" if mode == 16 else "odd" if mode == 12 else "directed"
        expected_ids = {int(line.split()[0]) for line in data(vector_set + "-vectors.txt").decode().splitlines()}
        assert len(groups[0][1]) == len(expected_ids)
        assert {int(r["id"]) for r in groups[0][1]} == expected_ids, mode
        for r in groups[0][1]:
            if mode in [3, 4, 8, 9, 18]:
                assert int(r["retired"]) == 0, mode
            elif mode in [5, 10, 12, 13, 14, 17]:
                assert int(r["retired"]) == 0 and int(r["scope"]) == 1, mode
            else:
                assert int(r["retired"]) == 1, mode
            if mode in [20, 21]:
                assert int(r["rr_started"]) == int(r["rr_retired"]) == 1, mode
                if mode == 20 and int(r["warm"]):
                    assert int(r["start_cpu"]) == int(r["rr_retire_cpu"]), mode
                if mode == 21:
                    assert int(r["rr_start_cpu"]) > int(r["retire_cpu"]), mode
    assert all(int(r["timed"]) == 0 for _, records in maximum for r in records)
    streams = [(name, records) for name, records in stream_groups if len(records) == 1448]
    assert {name for name, _ in streams} == {f"{directory}/{label}-iverilog-summary.csv"
        for directory in ["frozen-iu", "memory-iu"] for label in ["normal", "cold"]}
    for name, records in streams:
        assert len({int(r["id"]) for r in records}) == 688, name
        assert len({(int(r["id"]), int(r["instruction"])) for r in records}) == 1448, name
        for r in records:
            assert int(r["elapsed"]) >= (2 if int(r["form"]) < 3 else 3), name
    for label in ["normal", "cold"]:
        for suffix in ["summary.csv", "trace.csv"]:
            assert data(f"frozen-iu/{label}-iverilog-{suffix}") == data(f"memory-iu/{label}-iverilog-{suffix}"), (label, suffix)
    aligned = memory[(1, 0, 0)][0][1] + memory[(1, 1, 0)][0][1]
    assert {int(r["data_external"]) for r in aligned} == {0, 1, 2}
    assert sum(int(r["off_boundary"]) for r in aligned) == counts["off_boundary_captures"] > 0
    assert any(int(r["data_misses"]) > 0 for r in aligned)
    assert any(int(r["code_misses"]) > 0 for r in memory[(1, 0, 0)][0][1])
    return directed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    freeze = json.loads((HERE / "freeze.json").read_text())
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_MEMORY_CPU_PASS"
    for flag in ["dual_traces_equal", "max_memory_trace_equal", "max_register_trace_equal",
                 "rr_ri_preserved_warm_cold", "max_biu_fetch_sequential_equivalence",
                 "max_private_control_cones_absent", "production_unchanged"]:
        assert receipt[flag] is True, flag
    assert freeze["sha256"] and receipt["sources_sha256"] and receipt["artifacts_sha256"]
    encoded = {name + ".gz" if name.endswith("-trace.csv") else name for name in receipt["artifacts_sha256"]}
    assert set(freeze["sha256"]) == encoded | {"audit.py", "receipt.json"}, "Frozen manifest coverage differs from accepted artifacts"
    for name, expected in freeze["sha256"].items():
        assert sha(HERE / relative_name(name)) == expected, name
    assert sha(ROOT / "scripts/freeze_p06_memory_cpu.py") == freeze["freezer_sha256"]
    assert "audit.py" in freeze["sha256"] and "receipt.json" in freeze["sha256"]
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    for name, expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected, name
    with tempfile.TemporaryDirectory(prefix="reconstructed-", dir=out) as directory:
        regenerated = build(Path(directory))
        assert set(regenerated) == set(receipt["generated_cpu_sha256"])
        for name, path in regenerated.items():
            assert sha(path) == receipt["generated_cpu_sha256"][name], name
        path = Path(directory) / "memory-vectors.txt"
        assert memory_vectors(path) == 267
        assert path.read_bytes() == data("memory-vectors.txt")
        controls = directed_vectors(Path(directory))
        for name, path in controls.items():
            assert path.read_bytes() == data(name + "-vectors.txt"), name
        for mode in DIRECTED_MODES:
            selected = controls["tc-waits" if mode in [15, 17, 18] else "deadline" if mode == 16 else "odd" if mode == 12 else "directed"]
            count = len(selected.read_text().splitlines())
            for warm in ["warm", "cold"]:
                assert receipt["counts"]["directed"][f"mode{mode}-{warm}"] == count
        path = Path(directory) / "iu-streams.txt"
        assert stream_vectors(path) == 688
        assert path.read_bytes() == data("iu-streams.txt")
        path = Path(directory) / "register-vectors.txt"
        assert vectors(path) == 208
        assert path.read_bytes() == data("register-vectors.txt")
        check_components(receipt, regenerated)
    pairs = check_dual_traces(receipt["artifacts_sha256"])
    directed = check_summaries(receipt, pairs)
    assert set(receipt["negative_checks"]) == set(NEGATIVES)
    for name, check in receipt["negative_checks"].items():
        assert check["returncode"] != 0 and check["marker"] == NEGATIVES[name], name
        log = check.get("log", f"negative-{name}-run.log")
        assert log in receipt["artifacts_sha256"] and check["marker"] in data(log).decode(), name
    assert receipt["negative_checks"], "Missing independent oracle negatives"
    assert set(receipt["max_units"]) == set(UNIT_NAMES)
    for name, marker in receipt["max_units"].items():
        for tool in ["iverilog", "verilator"]:
            log = f"{name}/{tool}-run.log"
            assert log in receipt["artifacts_sha256"] and marker in data(log).decode(), (name, tool)
    for suffix in ["summary.csv", "trace.csv"]:
        assert data("original-register-max/normal-iverilog-" + suffix) == data("private-register-max/normal-iverilog-" + suffix)
    for directory in ["original-register-max", "private-register-max"]:
        records = pairs[directory + "/normal-iverilog-summary.csv"]
        assert len(records) == 208 and {int(r["id"]) for r in records} == set(range(208)), directory
    for timed in [0, 1]:
        assert f"lint-full-{timed}.log" in receipt["artifacts_sha256"]
        assert "%Error" not in data(f"lint-full-{timed}.log").decode()
        assert "%Warning" not in data(f"lint-full-{timed}.log").decode()
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    result = {
        "status": "P06_M6C_FROZEN_MEMORY_CPU_PASS",
        "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": len(pairs),
        "private_cpu_reconstructed": True,
        "counts": {**COUNTS, "directed": directed},
        "max_components_equivalent": True,
        "max_private_control_cones_absent": True,
        "max_control_cone_scope": "Isolated BIU, fetch and extracted executor commit controls",
        "commit_control_register_bits": 0,
        "production_guards_unchanged": True,
        "receipt_sha256": sha(HERE / "receipt.json"),
        "scope": receipt["scope"],
        "generic_cost_scope": receipt["generic_cost_scope"],
    }
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
