#!/usr/bin/env python3
"""Verify receipt-bound raw phase streams and report actual admission coverage."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path


def read(path, expected):
    if not path.exists():
        path = path.with_suffix(path.suffix + ".gz")
    opener = gzip.open if path.suffix == ".gz" else open
    digest = hashlib.sha256()
    with opener(path, "rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise RuntimeError("Raw stream digest mismatch: " + str(path))
    with opener(path, "rt") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.input / "receipt.json").read_text())
    if receipt["status"] != "P06_M0_FULL_STARTUP_PHASE_SWEEP_PASS":
        raise RuntimeError("Completed sweep required")
    summary = {"status": "RUNNING", "profile": receipt["profile"],
               "search_control": receipt.get("search_control", "generator epoch offset"), "runs": []}
    admitted = {"current": set(), "previous": set()}
    initial = {"current": set(), "previous": set()}
    for run in receipt["runs"]:
        rows = read(args.input / run["trace"], run["trace_sha256"])
        backend = read(args.input / run["backend"], run["backend_sha256"])
        if len(rows) != len(backend) or any(a["edge"] != b["edge"] for a, b in zip(rows, backend)):
            raise RuntimeError("CPU/backend edge mismatch")
        profile, loops = int(run["profile"]), int(run["iterations"])
        if any(int(r["profile"]) != profile for r in rows):
            raise RuntimeError("Wrong applied profile")
        increment = receipt["phase_increment"]
        phase = run["phase_delay"]
        initial_state = (int(backend[0]["epoch_accumulator"]), int(backend[0]["epoch_parity"]))
        expected = ((increment * phase) % 50, (increment * phase // 50) % 2)
        if initial_state != expected:
            raise RuntimeError("Unnatural initial generator phase")
        for previous, current in zip(backend, backend[1:]):
            accumulator = int(previous["epoch_accumulator"]) + increment
            parity = int(previous["epoch_parity"]) ^ (accumulator >= 50)
            if (int(current["epoch_accumulator"]), int(current["epoch_parity"])) != (accumulator % 50, parity):
                raise RuntimeError("Generator did not advance naturally")
        start, end = int(run["start"]), int(run["end"])
        measured = [r for r in rows if start <= int(r["edge"]) <= end]
        retires = [r for r in measured if r["retire_fire"] == "1"]
        loop_edges = [int(r["edge"]) for r in retires if r["opcode"] == "e2"]
        if len(retires) != 5 * loops or len(loop_edges) != loops:
            raise RuntimeError("Exact M0 work mismatch")
        at_start = backend[start-1]
        state = (int(at_start["epoch_accumulator"]), int(at_start["epoch_parity"]))
        if state != (int(run["kernel_epoch"]["accumulator"]), int(run["kernel_epoch"]["parity"])):
            raise RuntimeError("Admission phase receipt mismatch")
        admitted[run["version"]].add(state)
        initial[run["version"]].add(initial_state)
        warm = [r for r in backend if loop_edges[0] < int(r["edge"]) < end]
        if any(r["sdram_read"] == "1" or r["cpu_hold"] == "1" or r["refresh_grant"] == "1" for r in warm):
            raise RuntimeError("Unexpected physical READ, HOLD or AT refresh in warm interval")
        intervals = Counter(b-a for a, b in zip(loop_edges[:-2], loop_edges[1:-1]))
        summary["runs"].append({key: run.get(key) for key in
            ("version", "phase_delay", "prelude_NOPs", "iterations", "start", "fabric_clocks", "extensions")} | {
            "initial_epoch": initial_state, "admitted_epoch": state,
            "warm_taken_LOOP_intervals": dict(sorted(intervals.items())),
            "warm_physical_READ_HOLD_AT_refresh": [0, 0, 0]})
    summary["actual_initial_epoch_coverage"] = {v: sorted(states) for v, states in initial.items()}
    summary["actual_kernel_admission_coverage"] = {v: sorted(states) for v, states in admitted.items()}
    confirmation = [r for r in summary["runs"] if r["iterations"] == "256"]
    summary["confirmed_256_fabric_ranges"] = {v: [min(int(r["fabric_clocks"]) for r in confirmation if r["version"] == v),
        max(int(r["fabric_clocks"]) for r in confirmation if r["version"] == v)] for v in admitted}
    summary["status"] = "P06_M0_RAW_PHASE_TRACE_ANALYSIS_PASS"
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("status", "actual_initial_epoch_coverage", "actual_kernel_admission_coverage", "confirmed_256_fabric_ranges")}))


if __name__ == "__main__":
    main()
