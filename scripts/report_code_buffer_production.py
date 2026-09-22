"""Compare the production 512-byte buffer with the frozen capacity experiment."""
import argparse
import hashlib
import json
from pathlib import Path

from report_checkit_profile import WORKLOADS, read_run

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dir", type=Path)
    parser.add_argument("snapshot_manifest", type=Path)
    args = parser.parse_args()
    build = args.build_dir.resolve()
    manifest = json.loads(args.snapshot_manifest.read_text())
    baseline_path = ROOT / "docs/optimization/code_buffer_capacity_20260922.json"
    baseline = json.loads(baseline_path.read_text())
    # Production inputs must match the frozen synthesis snapshot. Verification
    # harnesses may evolve separately, so bind them to their compilation hashes.
    sources = {}
    for path, expected in manifest["source_sha256"].items():
        if path.startswith(("rtl/", "vendor/", "sys/")) or path in ("PCAT-286.sv", "config.tcl"):
            assert digest(ROOT / path) == expected, f"Frozen input changed: {path}"
            sources[path] = expected
    simulation_sources = {}
    for line in (build / "compiled-sources.sha256").read_text().splitlines():
        expected, path = line.split("  ", 1)
        assert digest(ROOT / path) == expected, f"Simulation input changed: {path}"
        simulation_sources[path] = expected
    assert (build / "performance-macros.txt").read_text().split() == baseline["performance_macros"]
    rows = []
    for workload in WORKLOADS:
        for enabled in (0, 1):
            run = read_run(build / f"{workload}-p03-{enabled}.log")
            reference = next(r for r in baseline["references"]
                             if r["result"]["workload"] == workload and r["result"]["p03"] == enabled)
            expected = (next(r for r in baseline["runs"] if r["enabled"] and
                             (r["lines"], r["ways"], r["hit_extra"]) == (64, 1, 0) and
                             r["result"]["workload"] == workload) if enabled else reference)
            # Exact timing/traffic equivalence to the selected model (or the
            # old bypass), not just similar benchmark scores.
            for key in ("result", "signature", "cpu", "latency", "misc"):
                assert run[key] == expected[key], (workload, enabled, key)
            assert run["signature"] == reference["signature"]
            assert run["signature"]["ideal_owner"] == "0"
            for key in ("retired", "writes", "sdram_writes"):
                assert run["result"][key] == reference["result"][key], (workload, key)
            run["log"] = str(Path(run["log"]).relative_to(ROOT))
            run["old_cycles"] = reference["result"]["cycles"]
            run["gain_percent"] = 100 * (run["old_cycles"] / run["result"]["cycles"] - 1)
            rows.append(run)
            print(f"CODE_BUFFER_PRODUCTION_MATCH workload={workload} enabled={enabled} "
                  f"cycles={run['result']['cycles']} gain={run['gain_percent']:.4f}%")
    receipt = dict(clock_mhz=50, data_bytes=512, lines=64, ways=1,
                   extra_hit_clocks=0, synthetic_not_dos_checkit=True,
                   baseline_receipt_sha256=digest(baseline_path),
                   synthesis_manifest_sha256=digest(args.snapshot_manifest),
                   source_sha256=sources, simulation_source_sha256=simulation_sources,
                   exact_model_and_bypass_match=True, runs=rows)
    (build / "production-comparison.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("CODE_BUFFER_PRODUCTION_COMPARISON_PASS runs=8")


if __name__ == "__main__":
    main()
