#!/usr/bin/env python3
"""Audit frozen full-CPU milestones and reconstruct the selected private CPU."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_p06_register_cpu import build
from run_p06_pilot import generic_stats


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((HERE / "freeze.json").read_text())
    for name, expected in frozen["sha256"].items():
        assert sha(HERE / name) == expected, "Changed frozen evidence: " + name
    checked = 0
    receipts = {}
    for stage in ["observation", "timed"]:
        folder = HERE / stage
        receipt = json.loads((folder / "receipt.json").read_text())
        for name, expected in receipt["sources_sha256"].items():
            assert sha(ROOT / name) == expected, "Changed input: " + name
        for name, expected in receipt["artifacts_sha256"].items():
            if stage == "observation" and name == "test.vvp":
                continue  # Explicitly omitted generated executable.
            assert sha(folder / name) == expected, "Changed artifact: " + stage + "/" + name
            checked += 1
        assert receipt["negative_control"]["returncode"] != 0
        assert receipt["dual_simulator_trace_equal"] if stage == "observation" else receipt["dual_simulator_all_traces_equal"]
        receipts[stage] = receipt
    timed = receipts["timed"]
    assert timed["status"] == "P06_PRIVATE_FULL_CPU_REGISTER_PASS"
    assert timed["max_cycle_trace_equal"] and timed["max_temporal_generate_pruned"]
    assert timed["production_sources_unchanged"] and timed["production_qip_excludes_pilot"]
    recreated = build(out)
    for name, path in recreated.items():
        assert sha(path) == timed["generated_cpu_sha256"][name], "Generated CPU differs: " + name
    for historical in [0, 1]:
        assert generic_stats(HERE / "timed" / f"generic-{historical}.json") == timed["generic_synthesis"][str(historical)]
    assert timed["generic_synthesis"]["0"]["register_bits"] == 0
    assert timed["negative_control"]["expected_reason"] in (HERE / "timed/negative-run.log").read_text()
    for artifact in ["trace.csv", "summary.csv"]:
        assert (HERE / "timed/original-max" / ("normal-iverilog-" + artifact)).read_bytes() == (
            HERE / "timed/private-max" / ("normal-iverilog-" + artifact)).read_bytes()
    for summary in (HERE / "timed/historical").glob("*-iverilog-summary.csv"):
        prefix = summary.name.removesuffix("-iverilog-summary.csv")
        for artifact in ["trace.csv", "summary.csv"]:
            assert (summary.parent / (prefix + "-iverilog-" + artifact)).read_bytes() == (
                summary.parent / (prefix + "-verilator-" + artifact)).read_bytes()
    rows = list(csv.DictReader((HERE / "timed/historical/normal-iverilog-summary.csv").open()))
    assert len(rows) == 221
    for row in rows[:208]:
        assert int(row["elapsed"]) == (2 if int(row["form"]) < 3 else 3)
        assert row["commit_edge"] == row["retire_edge"]
    stream = list(csv.DictReader((HERE / "timed/historical/stream-iverilog-summary.csv").open()))
    for previous, current in zip(stream, stream[1:]):
        assert int(current["start_clock"]) - int(previous["retire_clock"]) == 1
    baseline = json.loads((ROOT / "docs/evidence/p06-intel-contract-20261003/manifest.json").read_text())
    for name, metadata in baseline["integration_reference"]["sources"].items():
        assert sha(ROOT / name) == metadata["sha256"], "Changed production reference: " + name
    assert "spk286_timing_pilot" not in (ROOT / "rtl/spk286_integration/spk286_integration.qip").read_text()
    assert sha(ROOT / "scripts/test_at_landmark_dma.sh") == "0fba7826ccc810c5fa151115416d74357c0919f531a1f5e2ff795ea1a6c3d28c"
    result = {"status": "P06_M3_FROZEN_EVIDENCE_PASS", "artifacts_checked": checked,
        "receipt_sha256": {stage: sha(HERE / stage / "receipt.json") for stage in receipts},
        "private_cpu_reconstructed": True, "normal_virtual_minima_verified": 208,
        "max_traces_equal": True, "production_guards_unchanged": True,
        "generic_synthesis": timed["generic_synthesis"],
        "scope": "Register pilot; full historical CPU, physical calibration, FPGA fit/STA remain open"}
    (out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
