#!/usr/bin/env python3
"""Audit M4 frozen CODE evidence and reconstruct its private CPU and bench."""
import argparse
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_p06_fetch_cpu import build
from run_p06_core_register import sha
from run_p06_timed_fetch import full_cpu_bench, bus_scope_bench
from run_p06_pilot import generic_stats


def rows(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((HERE / "freeze.json").read_text())
    for name, expected in frozen["sha256"].items():
        assert sha(HERE / name) == expected, "Changed frozen evidence: " + name
    receipt = json.loads((HERE / "receipt.json").read_text())
    assert receipt["status"] == "P06_PRIVATE_CODE_FETCH_PASS"
    for name, expected in receipt["sources_sha256"].items():
        assert sha(ROOT / name) == expected, "Changed source: " + name
    for name, expected in receipt["artifacts_sha256"].items():
        assert sha(HERE / name) == expected, "Changed artifact: " + name
    recreated = build(out)
    for name, path in recreated.items():
        assert sha(path) == receipt["generated_cpu_sha256"][name]
    bench = full_cpu_bench(out)
    assert sha(bench) == receipt["generated_bench_sha256"]
    guard = bus_scope_bench(out, bench)
    assert sha(guard) == sha(HERE / guard.name)
    baseline = json.loads((ROOT / "docs/evidence/p06-intel-contract-20261003/manifest.json").read_text())
    for name, metadata in baseline["integration_reference"]["sources"].items():
        assert sha(ROOT / name) == metadata["sha256"], "Changed production guard: " + name
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    paired = 0
    for folder in ["fetch", "original-max", "private-max", "historical", "bus-guards"]:
        for summary in (HERE / folder).glob("*-iverilog-summary.csv"):
            prefix = summary.name.removesuffix("-iverilog-summary.csv")
            for artifact in ["trace.csv", "summary.csv"]:
                assert (summary.parent / (prefix + "-iverilog-" + artifact)).read_bytes() == (
                    summary.parent / (prefix + "-verilator-" + artifact)).read_bytes()
            paired += 1
    for artifact in ["trace.csv", "summary.csv"]:
        assert (HERE / "original-max" / ("normal-iverilog-" + artifact)).read_bytes() == (
            HERE / "private-max" / ("normal-iverilog-" + artifact)).read_bytes()
    assert len(rows(HERE / "fetch/normal-iverilog-summary.csv")) == 297
    cold = rows(HERE / "historical/normal-iverilog-summary.csv")
    warm = rows(HERE / "historical/warm-iverilog-summary.csv")
    assert len(cold) == len(warm) == 208
    for row in cold + warm:
        assert int(row["elapsed"]) >= (2 if int(row["form"]) < 3 else 3)
        assert row["commit_edge"] == row["retire_edge"] and row["writes"] == "0"
    for row in warm:
        assert int(row["elapsed"]) == (2 if int(row["form"]) < 3 else 3)
    guard_count = 0
    for summary in (HERE / "bus-guards").glob("*-iverilog-summary.csv"):
        for row in rows(summary):
            assert row["scope_error"] == "1" and all(row[k] == "0" for k in ["hlda", "writes", "retired"])
            guard_count += 1
    assert guard_count == 52
    for name in ["original", "max", "timed"]:
        assert generic_stats(HERE / f"generic-{name}.json") == receipt["generic_fetch_synthesis"][name]
    assert "Equivalence successfully proven!" in (HERE / "max-fetch-equivalence.log").read_text()
    assert receipt["max_fetch_sequential_equivalence"]
    assert receipt["negative_returncode"] != 0 and "publication before logical Tc" in (HERE / "negative-run.log").read_text()
    result = {"status": "P06_M4_FROZEN_CODE_EVIDENCE_PASS", "artifacts_checked": len(receipt["artifacts_sha256"]),
        "dual_trace_pairs": paired, "private_cpu_and_benches_reconstructed": True,
        "fetch_cases": 297, "warm_exact_minima": 208, "cold_functional_cases": 208,
        "unsupported_bus_guard_cases": guard_count, "max_fetch_sequential_equivalence": True,
        "production_guards_unchanged": True, "receipt_sha256": sha(HERE / "receipt.json"),
        "scope": receipt["scope"]}
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
