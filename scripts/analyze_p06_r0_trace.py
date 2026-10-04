#!/usr/bin/env python3
"""Recompute the 20/25 MHz R0 diagnosis from bound ideal/PCAT trace receipts."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path


def raw(directory, name):
    path = directory / name
    return path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix + ".gz").read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rows(directory, name, expected):
    data = raw(directory, name)
    if digest(data) != expected: raise RuntimeError("Trace binding failed: " + name)
    return list(csv.DictReader(io.StringIO(data.decode())))


def histogram(values):
    return dict(sorted(Counter(values).items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ideal-dir", type=Path, required=True)
    parser.add_argument("--pcat-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ideal = json.loads((args.ideal_dir / "receipt.json").read_text())
    pcat = json.loads((args.pcat_dir / "receipt.json").read_text())
    if ideal["status"] != "P06_R0_IDEAL_DUAL_TRACE_PASS" or pcat["status"] != "P06_R0_PCAT_TRACE_PASS":
        raise RuntimeError("Successful source-bound receipts required")
    shared = set(ideal["source_sha256"]) & set(pcat["source_sha256"])
    for path in shared:
        if ideal["source_sha256"][path] != pcat["source_sha256"][path]:
            raise RuntimeError("CPU/workload source mismatch: " + path)
    cases = []
    source_sets = (("ideal", args.ideal_dir, ideal), ("pcat", args.pcat_dir, pcat))
    warm = []
    phase_examples = []
    for owner, directory, receipt in source_sets:
        for item in receipt["runs"]:
            profile, count = int(item["profile"]), int(item["iterations"])
            kind = item["kind"]
            simulator = item.get("simulator", "verilator")
            name = f"{simulator}-p{profile}-{kind}-{count}"
            trace = rows(directory, name + ".csv", item["trace_sha256"])
            if digest(raw(directory, name + ".log")) != item["log_sha256"]:
                raise RuntimeError("Log binding failed: " + name)
            start, end = int(item["start"]), int(item["end"])
            elapsed = int(item["fabric_clocks"])
            if end - start != elapsed or int(item["instructions"]) != count * (5 if kind == "r0" else 1):
                raise RuntimeError("Fixed-work measurement failed: " + name)
            # Inclusive receipt bounds include the final LOOP retirement even
            # though the in_kernel flag is cleared on that observer edge.
            retired = [r for r in trace if start <= int(r["edge"]) <= end and r["retire_fire"] == "1"]
            if len(retired) != int(item["instructions"]):
                raise RuntimeError("Retirement count failed: " + name)
            extensions = histogram(r["opcode"] for r in retired if r["implementation_extension"] == "1")
            if sum(extensions.values()) != int(item["extensions"]):
                raise RuntimeError("Extension count failed: " + name)
            cases.append({"path": owner, "simulator": simulator, "profile": profile,
                "nominal_mhz": 20 if profile == 6 else 25, "kind": kind, "iterations": count,
                "fabric_clocks": elapsed, "microseconds_at_50mhz": elapsed / 50,
                "extensions_by_opcode_hex": extensions})
            if owner != "pcat": continue
            backend = rows(directory, name + "-backend.csv", item["backend_sha256"])
            if [r["edge"] for r in trace] != [r["edge"] for r in backend]:
                raise RuntimeError("CPU/backend observers are not synchronized")
            if kind != "r0" or count != 32: continue
            left, right = 350, 1400
            selected = [r for r in trace if left <= int(r["edge"]) <= right]
            services = [int(r["edge"]) for r in selected if r["fetch_valid"] == "1" and r["fetch_ready"] == "1"]
            starts = [int(r["edge"]) for r in selected if r["opcode_start"] == "1" and r["ip"] == "048b"]
            selected_backend = [r for r in backend if left <= int(r["edge"]) <= right]
            physical = sum(r["sdram_read"] == "1" for r in selected_backend)
            holds = sum(r["cpu_hold"] == "1" for r in selected_backend)
            refresh = sum(r["refresh_grant"] == "1" for r in selected_backend)
            if physical or holds or refresh: raise RuntimeError("Warm isolation assumption failed")
            warm.append({"profile": profile, "fabric_edge_window_inclusive": [left, right],
                "code_service_interval_fabric": histogram(b-a for a,b in zip(services,services[1:])),
                "iteration_interval_fabric": histogram(b-a for a,b in zip(starts,starts[1:])),
                "sdram_read_commands": physical, "hold_edges": holds, "at_refresh_grant_edges": refresh})
            anchor, stop = (310, 315) if profile == 6 else (322, 328)
            phase_examples.append({"profile": profile, "rows": [r for r in backend if anchor <= int(r["edge"]) <= stop]})
    derived = []
    for owner in ("ideal", "pcat"):
        for count in (32,256):
            for profile in (6,7):
                pair = [r for r in cases if r["path"] == owner and r["simulator"] == "verilator" and
                        r["profile"] == profile and r["iterations"] == count]
                if len(pair) != 2: raise RuntimeError("Missing comparison case")
                baseline = next(r["fabric_clocks"] for r in pair if r["kind"] == "baseline")
                body = next(r["fabric_clocks"] for r in pair if r["kind"] == "r0")
                extra = body-baseline
                derived.append({"path": owner, "profile": profile, "iterations": count,
                    "r0_minus_baseline_fabric": extra,
                    "conditional_nominal_clocks_per_iteration": extra/count * (20 if profile == 6 else 25)/50})
    result = {"status": "P06_R0_TRACE_ANALYSIS_PASS", "cases": cases,
              "derived": derived, "warm_pcat": warm, "phase_examples_pre_edge": phase_examples,
              "limits": "Opcode admission to last LOOP retirement; no DOS/PIT/BIOS instrumentation. "
                        "Warm window isolates P03 hits, not physical SDRAM timing. Subtracted counts are not isolated EU cycles."}
    args.output.write_text(json.dumps(result,indent=2) + "\n")
    print(result["status"])
    for item in derived:
        if item["iterations"] == 256: print(json.dumps(item))
    for item in warm: print(json.dumps(item))


if __name__ == "__main__": main()
