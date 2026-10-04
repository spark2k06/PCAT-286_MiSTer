#!/usr/bin/env python3
"""Audit frozen M6e evidence without new simulation, synthesis or fitting."""
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
from build_p06_odd_read_cpu import build
from build_p06_register_cpu import replace_once
from check_p06_odd_components import BIU_INPUTS, BIU_OUTPUTS, no_private_input_cone
from run_p06_core_register import sha
from run_p06_memory_cpu import memory_vectors, private_bench
from run_p06_odd_read_cpu import odd_vectors, controlled_vectors, validate_rows, UNIT_NAMES
from run_p06_pilot import generic_stats
from run_p06_read_stream import stream_vectors, validate_rows as validate_stream_rows

M6C = "docs/evidence/p06-core-memory-20261004"
M6D = "docs/evidence/p06-core-read-stream-20261004"
ANCESTORS = {
    M6C: "59e8738bc24251b0a8ad5670435fd3987394eba858cd130943934b3fe5384f65",
    M6D: "52b0a77350ab5d38f03e4d588d7746c84cdbfc1763d4d8768ea42aebdab489ef",
}
DIRTY_GUARD_SHA256 = "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
MODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18]
ABANDONED = {3, 4, 5, 6, 7, 8, 10, 11, 12, 15, 16, 17, 18}
RESET_MODES = {5, 6, 11, 18}
SCOPE_MODES = {7, 8, 12, 17}
SUMMARY_FIELDS = {
    "id", "timed", "warm", "mode", "odd", "start_cpu", "retire_cpu", "elapsed",
    "code_accepts", "data_accepts", "code_captures", "data_captures", "code_responses",
    "data_responses", "code_external", "wait1", "wait2", "code_misses", "miss1", "miss2",
    "alignment_count", "first_tc", "final_tc", "first_tc_cpu", "off_boundary",
    "gpr", "flags", "ip", "retired", "scope",
}
TRACE_FIELDS = {
    "id", "edge", "boundary", "cpu_clock", "start", "code_start", "data_start",
    "code_capture", "data_capture", "first_tc", "final_tc", "gpr_write", "retired",
    "owner", "bus", "address", "status", "ready", "ip", "cursor", "gpr", "flags",
    "queue", "scope", "policy_wait", "diagnostic_wait", "alignment", "tmp0_pending", "scheduled",
}
# Each negative binds its actual mutation, caller fixture and independent failure.
NEGATIVES = {
    "alignment": ("odd read alignment/wait budget oracle failed", "spk286.sv",
                  ".alignment_event(p06_timed_read && p06_alignment_event)", ".alignment_event(1'b0)", "odd-vectors.txt", []),
    "waits": ("odd read alignment/wait budget oracle failed", "spk286.sv",
              ".read_wait_event(p06_timed_read && p06_read_wait_event)", ".read_wait_event(1'b0)", "odd-vectors.txt", []),
    "permit": ("odd read first eligible commit oracle failed", "spk286.sv",
               "(!p06_result_pending || permit)", "1'b1", "odd-vectors.txt", []),
    "second-early": ("odd read logical owner oracle failed: physical presence/second gate", "spk286_biu.sv",
                     "state_q == SECOND_TS || state_q == SECOND_TC ||", "1'b1 ||", "odd-vectors.txt", []),
    "first-publication": ("odd read word publication oracle failed", "spk286_biu.sv",
                          "assign p06_complete = sample_tc && state_q != ODD_TC && p06_board_ready && available;",
                          "assign p06_complete = sample_tc && p06_board_ready && (available || first_available);", "odd-vectors.txt", []),
    "first-release": ("odd read logical owner oracle failed", "spk286_biu.sv",
                      "(!P06_ODD_READ_TIMING || !address_q[0] || byte_q)", "1'b1", "odd-control-vectors.txt", ["+mode=16"]),
    "final-assembly": ("odd read assembled payload oracle failed", "spk286_biu.sv",
                       "(second_q ? {data_in[7:0], low_byte_q} : data_in)) : raw_data_read_data;",
                       "(second_q ? {low_byte_q, data_in[7:0]} : data_in)) : raw_data_read_data;", "odd-vectors.txt", []),
    "retained-assembly": ("odd read assembled payload oracle failed", "spk286_biu.sv",
                          "raw_data_read_data <= byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :\n"
                          "                                      (second_q ? {data_in[7:0], low_byte_q} : data_in);",
                          "raw_data_read_data <= byte_q ? {8'd0, (address_q[0] ? data_in[15:8] : data_in[7:0])} :\n"
                          "                                      (second_q ? {low_byte_q, data_in[7:0]} : data_in);", "odd-vectors.txt", []),
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
    result = {"odd/normal": (1, 1, 0, "odd-vectors.txt"),
              "odd/cold": (1, 0, 0, "odd-vectors.txt"),
              "odd/mode13-warm": (1, 1, 13, "odd-deadline-vectors.txt"),
              "original-max/normal": (0, 1, 0, "odd-vectors.txt"),
              "private-max/normal": (0, 1, 0, "odd-vectors.txt")}
    result.update({f"odd/mode{mode}-{label}": (1, warm, mode,
                   "odd-before-ready-vectors.txt" if mode == 15 else "odd-control-vectors.txt")
                   for mode in MODES for label, warm in [("warm", 1), ("cold", 0)]})
    assert len(result) == 39
    return result


def check_pairs(artifacts):
    prefixes = set(contexts()) | {f"{label}/{temperature}" for label in ["aligned-memory", "aligned-stream"]
                                for temperature in ["normal", "cold"]}
    assert len(prefixes) == 43
    expected = {prefix + "-iverilog-summary.csv" for prefix in prefixes}
    assert {name for name in artifacts if name.endswith("-iverilog-summary.csv")} == expected
    assert {name for name in artifacts if name.endswith("-verilator-summary.csv")} == {
        name.replace("-iverilog-", "-verilator-") for name in expected}
    expected_traces = {name.removesuffix("summary.csv") + "trace.csv" for name in expected}
    expected_traces |= {name.replace("-iverilog-", "-verilator-") for name in expected_traces}
    assert {name for name in artifacts if name.endswith("-trace.csv") and
            ("-iverilog-" in name or "-verilator-" in name)} == expected_traces
    result = {}
    for name in sorted(expected):
        for left in [name, name.removesuffix("summary.csv") + "trace.csv"]:
            right = left.replace("-iverilog-", "-verilator-")
            assert left in artifacts and right in artifacts and data(left) == data(right), left
        result[name] = rows(name)
        assert result[name], name
        if name.split("/")[0] not in ["aligned-memory", "aligned-stream"]:
            assert set(result[name][0]) == SUMMARY_FIELDS, name
    return result


def check_vectors(directory):
    path = directory / "odd-vectors.txt"
    assert odd_vectors(path) == 834 and path.read_bytes() == data(path.name)
    fields = [line.split() for line in path.read_text().splitlines()]
    assert {int(f[0]) for f in fields} == set(range(834)) and all(len(f) == 14 for f in fields)
    assert sum(int(f[4], 16) & 1 for f in fields) == 741
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xffff for f in fields)
    assert any((int(f[3], 16) << 4) + int(f[4], 16) == 0xfffff for f in fields)
    assert {int(f[1], 16) for f in fields} == {0x100, 0x101}
    assert any(int(f[5], 16) == (int(f[6], 16) & 0xffff) for f in fields)
    control, deadline, before_ready = controlled_vectors(directory)
    for selected in [control, deadline, before_ready]:
        assert selected.read_bytes() == data(selected.name), selected.name
    assert len(control.read_text().splitlines()) == 14
    assert len(deadline.read_text().splitlines()) == 3
    assert len(before_ready.read_text().splitlines()) == 12


def check_trace(prefix, records, path, timed, warm, mode):
    caller = {int(f[0]): f for f in (line.split() for line in path.read_text().splitlines())}
    trace = csv.DictReader(io.StringIO(data(prefix + "-iverilog-trace.csv").decode()))
    assert set(trace.fieldnames) == TRACE_FIELDS, prefix
    previous, observed, committed, counts, timelines = {}, set(), {}, {}, {}
    event_fields = ["data_start", "code_capture", "data_capture", "gpr_write", "retired"]
    for row in trace:
        identifier = int(row["id"])
        assert identifier in caller, (prefix, identifier)
        f = caller[identifier]
        observed.add(identifier)
        edge = int(row["edge"])
        assert edge == previous.get(identifier, 0) + 1, (prefix, identifier, edge)
        previous[identifier] = edge
        for field in ["boundary", "start", "code_start", "data_start", "code_capture", "data_capture",
                      "first_tc", "final_tc", "gpr_write", "retired", "bus", "ready", "scope",
                      "policy_wait", "diagnostic_wait", "alignment", "tmp0_pending"]:
            assert int(row[field]) in [0, 1], (prefix, field, row[field])
        assert 0 <= int(row["queue"]) <= 6, (prefix, row)
        # Event flags precede the edge; bus/address/status are printed after it.
        # A same-edge transfer of ownership must not be mistaken for bad metadata.
        if int(row["data_capture"]) or int(row["code_capture"]):
            assert int(row["ready"]) == 1, (prefix, row)
        committed.setdefault(identifier, int(f[6], 16))
        counts.setdefault(identifier, {field: 0 for field in event_fields})
        timelines.setdefault(identifier, {"admit": None, "captures": []})
        if int(row["data_start"]):
            assert timelines[identifier]["admit"] is None, (prefix, row)
            timelines[identifier]["admit"] = int(row["cpu_clock"])
        if int(row["data_capture"]):
            # An off-boundary capture is first available at the next boundary.
            eligible_cpu = int(row["cpu_clock"]) + int(not int(row["boundary"]))
            timelines[identifier]["captures"].append(eligible_cpu)
        if int(row["gpr_write"]):
            committed[identifier] = (int(f[6], 16) & ~0xffff) | int(f[5], 16)
        assert int(row["gpr"], 16) == committed[identifier], (prefix, row)
        assert int(row["flags"], 16) == int(f[7], 16), (prefix, row)
        if int(row["retired"]):
            assert int(row["ip"], 16) == (int(f[1], 16) + 3) & 0xffff, (prefix, row)
        for field in event_fields:
            counts[identifier][field] += int(row[field])
    assert observed == set(caller), prefix
    for row in records:
        identifier = int(row["id"])
        observed_counts = counts[identifier]
        assert observed_counts["gpr_write"] == observed_counts["retired"] == int(row["retired"])
        for event, field in [("data_start", "data_accepts"), ("code_capture", "code_captures"),
                             ("data_capture", "data_captures")]:
            assert observed_counts[event] == int(row[field]), (prefix, identifier, field)
        assert int(row["odd"]) == (int(caller[identifier][4], 16) & 1)
        assert int(row["scope"]) == int(mode in SCOPE_MODES), (prefix, row)
        # Trace first_tc/final_tc are post-edge combinational levels, not the
        # sampled events counted by the independent bench observer. Reconstruct
        # the first eligible Tc from caller waits and physical capture timing.
        if timed:
            assert 0 <= int(row["first_tc"]) <= int(row["odd"])
            assert 0 <= int(row["final_tc"]) <= 1
            if int(row["first_tc"]):
                timeline = timelines[identifier]
                first_eligible = max(timeline["admit"] + 2 + int(caller[identifier][9]), timeline["captures"][0])
                assert int(row["first_tc_cpu"]) == first_eligible, (prefix, row)
        if mode in ABANDONED - RESET_MODES:
            assert int(row["data_captures"]) == 2, (prefix, row)
        if mode == 18:
            assert int(row["data_captures"]) == 0, (prefix, row)
        if timed and int(row["retired"]):
            assert int(row["first_tc"]) == int(row["odd"]) and int(row["final_tc"]) == 1
            assert int(row["elapsed"]) == int(row["retire_cpu"]) - int(row["start_cpu"])
    for tool in ["iverilog", "verilator"]:
        log = data(prefix + "-" + tool + "-run.log").decode()
        pattern = r"P06_CORE_ODD_READ_PASS cases=(\d+) checks=(\d+) timed=(\d+) warm=(\d+) mode=(\d+)"
        matches = [match.groups() for line in log.splitlines() if (match := re.fullmatch(pattern, line))]
        assert len(matches) == 1, (prefix, tool)
        count, checks, actual_timed, actual_warm, actual_mode = map(int, matches[0])
        assert (count, actual_timed, actual_warm, actual_mode) == (len(caller), timed, warm, mode)
        assert checks > 0
    return validate_rows(records, path, timed, warm, mode)


def check_preservation(receipt, pairs, directory, ancestors):
    assert receipt["preserved"] == {"aligned-memory": 267, "aligned-stream": 240}
    for label, generator, bench, ancestor, subdirectory, expected in [
        ("aligned-memory", memory_vectors, "p06_core_memory_tb", M6C, "memory", 267),
        ("aligned-stream", stream_vectors, "p06_core_read_stream_tb", M6D, "streams", 240),
    ]:
        path = directory / (label + "-vectors.txt")
        assert generator(path) == expected and path.read_bytes() == data(path.name)
        adapted = replace_once((ROOT / "sim/spk286_timing_pilot" / (bench + ".sv")).read_text(),
                               ".P06_MEMORY_PILOT(TIMED)", ".P06_MEMORY_PILOT(TIMED), .P06_ODD_READ_PILOT(TIMED)")
        assert data(label + "-tb.sv").decode() == adapted
        for temperature in ["normal", "cold"]:
            for tool in ["iverilog", "verilator"]:
                for suffix in ["summary.csv", "trace.csv"]:
                    old_name = f"{subdirectory}/{temperature}-{tool}-{suffix}"
                    old_bytes = artifact(ROOT / ancestor, old_name)
                    assert hashlib.sha256(old_bytes).hexdigest() == ancestors[ancestor]["artifacts_sha256"][old_name]
                    assert data(f"{label}/{temperature}-{tool}-{suffix}") == old_bytes
            records = pairs[f"{label}/{temperature}-iverilog-summary.csv"]
            if label == "aligned-stream":
                assert validate_stream_rows(records, path, 1, int(temperature == "normal"), 0) == 1120
            else:
                assert len(records) == 267 and {int(r["id"]) for r in records} == set(range(267))


def check_components(receipt):
    components = receipt["components"]
    assert components == json.loads(data("component-checks.json"))
    assert components["ancestor_receipt_sha256"] == ANCESTORS[M6C]
    assert components["aligned_state_correspondence"] == {"gate": "genblk2.p06_data.state_q", "gold": "p06_data.state_q"}
    costs = components["costs"]
    assert set(costs) == {"spk286_biu", "p06_instruction_duration"}
    labels = {"spk286_biu": {"original", "m6c", "aligned", "odd", "max"},
              "p06_instruction_duration": {"original", "aligned", "odd", "max"}}
    for module, module_labels in labels.items():
        assert set(costs[module]) == module_labels
        for label in module_labels:
            assert generic_stats(HERE / f"generic-{module}-{label}.json") == costs[module][label]
            log = data(f"generic-{module}-{label}.log").decode()
            assert "Warning:" not in log and "ERROR:" not in log
    assert costs["spk286_biu"]["aligned"]["register_bits"] == costs["spk286_biu"]["m6c"]["register_bits"]
    assert costs["spk286_biu"]["max"]["register_bits"] == costs["spk286_biu"]["original"]["register_bits"]
    policy = costs["p06_instruction_duration"]
    assert policy["aligned"]["register_bits"] == policy["odd"]["register_bits"] == policy["original"]["register_bits"]
    assert policy["max"]["register_bits"] == 0
    expected_proofs = {"biu_max", "biu_aligned", "duration_aligned", "max_biu_private_control_cones_absent",
                       "duration_late0_alignment_cone_absent", "duration_hist0_alignment_cone_absent"}
    assert set(components["proofs"]) == expected_proofs and all(value is True for value in components["proofs"].values())
    for name, deleted in [("biu-max", BIU_OUTPUTS), ("biu-aligned", ["p06_alignment_event"]), ("duration-aligned", [])]:
        proof = data(name + "-equivalence.ys").decode()
        log = data(name + "-equivalence.log").decode()
        assert "Equivalence successfully proven!" in log and "ERROR:" not in log
        assert "delete -input" not in proof and "equiv_make gold gate equiv" in proof
        assert proof.count("equiv_status -assert") == 1 and "equiv_induct -seq 4" in proof
        actual_deletions = [line for line in proof.splitlines() if line.startswith("delete ")]
        assert actual_deletions == (["delete -output " + " ".join("gate/" + output for output in deleted)] if deleted else [])
        if name == "biu-aligned":
            assert "rename genblk2.p06_data.state_q p06_data.state_q" in proof
            assert proof.count("chparam -set P06_DATA_TIMING 1 -set P06_SHARED_TIMING 1 spk286_biu") == 2
    golden = replace_once((ROOT / "vendor/spk286/rtl/spk286_biu.sv").read_text(), "module spk286_biu (",
                          "module spk286_biu (\n    input logic " + ", ".join(BIU_INPUTS) + ",")
    assert data("biu-max-gold.sv").decode() == golden
    golden = replace_once((ROOT / "rtl/spk286_timing_pilot/p06_instruction_duration.sv").read_text(),
                          "    input logic read_wait_event,", "    input logic alignment_event,\n    input logic read_wait_event,")
    assert data("duration-aligned-gold.sv").decode() == golden
    maximum = json.loads(data("generic-spk286_biu-max.json"))["modules"]["spk286_biu"]
    no_private_input_cone(maximum, BIU_INPUTS)
    for name, constant in [("p06_scope_error", "0"), ("p06_scope_block", "0"), ("p06_code_admission", "1"),
                           ("p06_read_wait_event", "0"), ("p06_alignment_event", "0")]:
        assert maximum["ports"][name]["bits"] == [constant], name
    for label in ["aligned", "max"]:
        module = json.loads(data(f"generic-p06_instruction_duration-{label}.json"))["modules"]["p06_instruction_duration"]
        no_private_input_cone(module, ["alignment_event"])
    for label in ["max", "aligned", "odd"]:
        log = data("lint-" + label + ".log").decode()
        assert "%Error" not in log and "%Warning" not in log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT.resolve())
    out.mkdir(parents=True, exist_ok=False)
    freeze = json.loads((HERE / "freeze.json").read_text())
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_ODD_READ_CPU_PASS" and receipt["matrix_cases"] == 834
    for flag in ["dual_traces_equal", "max_traces_equal", "aligned_traces_preserved", "production_unchanged"]:
        assert receipt[flag] is True, flag
    assert freeze["sha256"] and receipt["sources_sha256"] and receipt["artifacts_sha256"]
    encoded = {name + ".gz" if name.endswith("-trace.csv") else name for name in receipt["artifacts_sha256"]}
    assert set(freeze["sha256"]) == encoded | {"audit.py", "receipt.json"}
    for name, expected in freeze["sha256"].items():
        assert sha(HERE / relative_name(name)) == expected, name
    assert sha(ROOT / "scripts/freeze_p06_odd_read_cpu.py") == freeze["freezer_sha256"]
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    for name, expected in receipt["artifacts_sha256"].items():
        assert hashlib.sha256(data(name)).hexdigest() == expected, name
    ancestors = {}
    for name, expected in ANCESTORS.items():
        assert sha(ROOT / name / "receipt.json") == expected, name
        assert receipt["sources_sha256"][name + "/receipt.json"] == expected, name
        ancestors[name] = json.loads((ROOT / name / "receipt.json").read_text())
    assert ancestors[M6C]["status"] == "P06_PRIVATE_MEMORY_CPU_PASS"
    assert ancestors[M6D]["status"] == "P06_PRIVATE_READ_STREAM_PASS"
    source_names = set(ancestors[M6C]["sources_sha256"]) | {
        "scripts/run_p06_odd_read_cpu.py", "scripts/build_p06_odd_read_cpu.py", "scripts/check_p06_odd_components.py",
        "scripts/run_p06_read_stream.py", "rtl/spk286_timing_pilot/p06_odd_read_biu_connection.svh",
        "sim/spk286_timing_pilot/p06_core_read_stream_tb.sv", "sim/spk286_timing_pilot/p06_core_odd_read_tb.sv",
        M6C + "/receipt.json", M6D + "/receipt.json",
    }
    assert set(receipt["sources_sha256"]) == source_names, "Incomplete source coverage"
    for ancestor in ancestors.values():
        for name in set(ancestor["sources_sha256"]) & source_names:
            assert receipt["sources_sha256"][name] == ancestor["sources_sha256"][name], name
    pairs = check_pairs(receipt["artifacts_sha256"])
    controls = {}
    with tempfile.TemporaryDirectory(prefix="reconstructed-", dir=out) as directory:
        directory = Path(directory)
        regenerated = build(directory)
        expected_names = set(ancestors[M6C]["generated_cpu_sha256"]) | {"p06_instruction_duration.sv"}
        assert len(expected_names) == 8 and set(regenerated) == expected_names
        assert {name: sha(path) for name, path in regenerated.items()} == receipt["generated_cpu_sha256"]
        check_vectors(directory)
        for prefix, (timed, warm, mode, vector_name) in contexts().items():
            count = check_trace(prefix, pairs[prefix + "-iverilog-summary.csv"], directory / vector_name, timed, warm, mode)
            assert count == (12 if mode == 15 else 14 if mode in MODES else 3 if mode == 13 else 834)
            if mode:
                controls[prefix.removeprefix("odd/")] = count
        check_preservation(receipt, pairs, directory, ancestors)
        bench = (ROOT / "sim/spk286_timing_pilot/p06_core_odd_read_tb.sv").read_text()
        maximum = replace_once(bench, "parameter bit TIMED=1'b1", "parameter bit TIMED=1'b0")
        assert data("odd-max-tb.sv").decode() == maximum
        assert data("odd-original-tb.sv").decode() == "`define P06_ORIGINAL\n" + maximum
        assert set(receipt["negative_checks"]) == set(NEGATIVES)
        for name, (marker, source, before, after, vector_name, extra) in NEGATIVES.items():
            check = receipt["negative_checks"][name]
            assert check["returncode"] != 0
            assert {key: check[key] for key in ["marker", "source", "before", "after", "vectors", "extra"]} == {
                "marker": marker, "source": source, "before": before, "after": after, "vectors": vector_name, "extra": extra}
            log = data(f"negative-{name}-run.log").decode()
            assert marker in log and "P06_CORE_ODD_READ_PASS" not in log
            assert data(f"negative-{name}-{source}").decode() == replace_once(regenerated[source].read_text(), before, after)
        assert set(receipt["max_units"]) == set(UNIT_NAMES)
        for name, marker in receipt["max_units"].items():
            adapted = private_bench(directory, name)
            text = adapted.read_text()
            if name.startswith("spk286_biu"):
                text = replace_once(text, "wire p06_scope_error,", "wire p06_alignment_event;\n    wire p06_scope_error,")
            assert data(name + "_tb.sv").decode() == text
            for tool in ["iverilog", "verilator"]:
                log = data(f"{name}/{tool}-run.log").decode()
                assert [line for line in log.splitlines() if "PASS" in line] == [marker], (name, tool)
    assert receipt["controls"] == controls
    assert sum(count for name, count in controls.items() if name != "mode13-warm") == 472
    assert controls["mode13-warm"] == 3
    timed_cpu_cases = 2 * receipt["matrix_cases"] + sum(controls.values())
    assert timed_cpu_cases == 2143
    for suffix in ["summary.csv", "trace.csv"]:
        assert data("original-max/normal-iverilog-" + suffix) == data("private-max/normal-iverilog-" + suffix)
    check_components(receipt)
    microcode = data("microcode.log")
    expected_microcode = artifact(ROOT / M6C, "microcode.log")
    assert hashlib.sha256(expected_microcode).hexdigest() == ancestors[M6C]["artifacts_sha256"]["microcode.log"]
    assert microcode == expected_microcode
    assert microcode.decode().splitlines() == [
        "MICROCODE CHECK PASS: 123 entries, 743 words, 10-bit addresses, 8-bit control"]
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == DIRTY_GUARD_SHA256
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / relative_name(name)) == expected, name
    result = {
        "status": "P06_M6E_FROZEN_ODD_READ_CPU_PASS", "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": len(pairs), "matrix_cases": 834, "controls": controls,
        "timed_cpu_cases": timed_cpu_cases, "directed_control_cases": 472, "deadline_cases": 3,
        "max_cases_per_cpu": 834, "preserved_memory_cases_per_temperature": 267,
        "preserved_stream_cases_per_temperature": 240, "preserved_stream_instructions_per_temperature": 1120,
        "private_cpu_reconstructed": True, "generated_cpu_sources": 8, "caller_fixtures_recreated": True,
        "architectural_summaries_checked": True, "max_traces_equal": True, "aligned_traces_preserved": True,
        "components": receipt["components"], "negative_checks": receipt["negative_checks"],
        "production_guards_unchanged": True, "ancestor_receipts_sha256": ANCESTORS,
        "receipt_sha256": sha(HERE / "receipt.json"), "scope": receipt["scope"],
    }
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
