#!/usr/bin/env python3
"""Recompute the eight READY-chain MiSTer captures without altering raw inputs.

Elapsed PIT ticks and signatures are qualified by the unchanged T286REF2
validator. This is measurement analysis, not a calibrated instruction oracle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SW/CPUTIME"))
from validate_t286ref import validate_csv, VALIDATOR_SHA256  # noqa: E402
from analyze_p06_physical_reference import stats  # noqa: E402

CASES = ("R0", "B0", "M0")
PROFILES = (
    ("6", "NEW6.CSV", 6, 1629, 32.0, "checknum-6-8-10-125-16.png"),
    ("8", "NEW8.CSV", 8, 2181, 41.7, "checknum-6-8-10-125-16.png"),
    ("10", "NEW10.CSV", 10, 2631, 49.6, "checknum-6-8-10-125-16.png"),
    ("12.5", "NEW125.CSV", 12.5, 3234, 61.6, "checknum-6-8-10-125-16.png"),
    ("16", "NEW16.CSV", 16, 3854, 74.3, "checknum-6-8-10-125-16.png"),
    ("20", "NEW20.CSV", 20, 4250, 82.9, "checknum-25-20-max.png"),
    ("25", "NEW25.CSV", 25, 5139, 95.1, "checknum-25-20-max.png"),
    ("MAX", "NEWMAX.CSV", None, 6906, 121.6, "checknum-25-20-max.png"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identified(path):
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha(data)}


def reference(row, nominal):
    data = (ROOT / row["archive_path"]).read_bytes()
    assert sha(data) == row["sha256"], row["archive_path"]
    result = stats(validate_csv(data.decode("ascii"), nominal))
    assert result == row["statistics"]
    return result


def analyze(input_dir, output):
    input_dir, output = input_dir.resolve(), output.resolve()
    input_dir.relative_to(ROOT)
    output.relative_to(ROOT)
    old_path = ROOT / "docs/evidence/p06-mister-reference-20261004/analysis.json"
    physical_path = ROOT / "docs/evidence/p06-physical-reference-20261004/analysis.json"
    fit_path = ROOT / "docs/evidence/p06-ready-chain-fit-20261004/receipt.json"
    old = json.loads(old_path.read_bytes())
    references = json.loads(physical_path.read_bytes())
    fit = json.loads(fit_path.read_bytes())
    rbf_sha = "6b0b1dd42f756908298b076a12210630e6a1b0d314950635b391ba0c87ec37f1"
    assert fit["rbf"]["sha256"] == rbf_sha
    captures, changes, comparisons = {}, [], []
    immutable_inputs = [old_path, physical_path, fit_path]
    for label, name, mhz, dhrystone, whetstone, screenshot in PROFILES:
        path = input_dir / name
        data = path.read_bytes()
        validation = validate_csv(data.decode("ascii"), label)
        assert validation["csv_sha256"] == sha(data)
        assert validation["metadata"]["pit_mode"] == "2"
        measured = stats(validation)
        previous = old["captures"][label]
        previous_raw = ROOT / previous["archive"]["path"]
        previous_data = previous_raw.read_bytes()
        assert sha(previous_data) == previous["archive"]["sha256"]
        assert stats(validate_csv(previous_data.decode("ascii"), label)) == previous["statistics"]
        picture = input_dir.parent / "screenshots" / screenshot
        captures[label] = {
            "raw": identified(path), "validation": validation, "statistics": measured,
            "nominal_mhz": mhz,
            "checknum": {"dhrystones": dhrystone, "whetstones_K": whetstone,
                         "source": identified(picture), "method": "User screenshot transcription; separate benchmark run"},
        }
        immutable_inputs.extend((path, previous_raw, picture))
        for case in CASES:
            now = measured[case]["gross"]
            before = previous["statistics"][case]["gross"]
            changes.append({"profile": label, "case": case,
                            "previous_gross_ticks": before["median_ticks"],
                            "current_gross_ticks": now["median_ticks"],
                            "elapsed_change_percent": 100 * (now["median_ticks"] / before["median_ticks"] - 1),
                            "all_new_samples_slower": now["min_ticks"] > before["max_ticks"],
                            "all_new_samples_faster": now["max_ticks"] < before["min_ticks"]})
        captures[label]["checknum_change_percent"] = {
            "dhrystones": 100 * (dhrystone / previous["checknum"]["dhrystones"] - 1),
            "whetstones_K": 100 * (whetstone / previous["checknum"]["whetstones_K"] - 1),
        }
    for label, mhz, prefix in (("6", 6, "native6"), ("12.5", 12.5, "native12")):
        for selection in ("ws0", "auto", "ws1", "ws2"):
            name = prefix + "-" + selection
            row = references["native"][name]
            ref = reference(row, label)
            for case in CASES:
                actual = captures[label]["statistics"][case]["gross"]["median_ticks"]
                expected = ref[case]["gross"]["median_ticks"]
                comparisons.append({"profile": label, "case": case, "reference": name,
                                    "actual_reference_hz": row["actual_cpu_hz"],
                                    "visible_wait_states": row["visible_wait_states"],
                                    "elapsed_difference_percent": 100 * (actual / expected - 1)})
            immutable_inputs.append(ROOT / row["archive_path"])
    for label, mhz, name, reference_mhz in (("6", 6, "REG6_6.CSV", 6),
                                            ("12.5", 12.5, "REG12_12.CSV", 12)):
        row = references["physical"][name]
        ref = reference(row, str(reference_mhz))
        for case in CASES:
            actual = captures[label]["statistics"][case]["gross"]["median_ticks"]
            expected = ref[case]["gross"]["median_ticks"] * reference_mhz / mhz
            comparisons.append({"profile": label, "case": case, "reference": name,
                                "illustrative_frequency_scaling": reference_mhz != mhz,
                                "elapsed_difference_percent": 100 * (actual / expected - 1),
                                "limit": "12 to12.5 scaling assumes equal cycles; fixed board delays are not independently scaled"})
        immutable_inputs.append(ROOT / row["archive_path"])
    transitions = []
    for previous, current in zip(PROFILES[:-1], PROFILES[1:]):
        for case in CASES:
            a = captures[previous[0]]["statistics"][case]["gross"]
            b = captures[current[0]]["statistics"][case]["gross"]
            transitions.append({"from": previous[0], "to": current[0], "case": case,
                                "elapsed_change_percent": 100 * (b["median_ticks"] / a["median_ticks"] - 1),
                                "all_current_faster": b["max_ticks"] < a["min_ticks"]})
    sources = [Path(__file__), ROOT / "scripts/analyze_p06_physical_reference.py",
               ROOT / "SW/CPUTIME/validate_t286ref.py"]
    immutable_inputs.extend(sources)
    before_hashes = {str(p): sha(p.read_bytes()) for p in set(immutable_inputs)}
    report = {
        "status": "EIGHT_MISTER_READY_CHAIN_PROFILES_RAW_PASS_MONOTONIC_CALIBRATION_OPEN",
        "date": "2026-10-05", "sources": [identified(p) for p in sources],
        "validator_sha256": VALIDATOR_SHA256,
        "reference_inputs": [identified(p) for p in (old_path, physical_path, fit_path)],
        "candidate": {"rbf_path": "build/p06-ready-chain-allfeatures-20261004-v1/work/output_files/PCAT-286.rbf",
                      "rbf_sha256": rbf_sha,
                      "association": "User confirms20/25/MAX candidate; supplies6..16 followup after request for same candidate/reset",
                      "independent_loaded_rbf_identity": "NOT_OBSERVED",
                      "fixed50_timing_status": "MEASURED_FIXED50_TIMING_FAIL"},
        "profile_count": len(captures),
        "sample_count": sum(c["validation"]["sample_count"] for c in captures.values()),
        "summary_count": sum(c["validation"]["summary_count"] for c in captures.values()),
        "units": "Elapsed PIT input ticks conditional on assumed reload65536; no isolated CPU-cycle measurement",
        "captures": captures, "elapsed_changes_from_previous": changes,
        "adjacent_profile_transitions": transitions, "comparisons": comparisons,
        "all_gross_transitions_strictly_faster": all(r["all_current_faster"] for r in transitions),
        "decision": "Hardware confirms corrected25MHzR0 ordering. Investigate6/8MHzM0 penalty with frozen identical workloads before any retune. PreserveIntel timings andMAX; causal historical calibration remains open.",
        "limits": ["Seven repetitions in one capture per profile are not independent boot repeats",
                   "PIT/CPU clocks and physical board READY policy are not independently calibrated",
                   "NativeT286REF controls at8/10/16/20/25 are separate pending work",
                   "Endpoint timer checks do not exclude whole-period stalls",
                   "Mixed CHECKNUM and directed kernel differences cannot identify a unique wait count",
                   "No new simulation, regression or fit is performed by this analyzer"],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for source in sources:
        target = output / "sources" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError("Refusing to replace changed source snapshot: " + str(target))
        if not target.exists():
            target.write_bytes(data)
    assert before_hashes == {str(p): sha(p.read_bytes()) for p in set(immutable_inputs)}
    artifacts = {p.relative_to(output).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps({"status": report["status"], "artifacts": artifacts}, indent=2) + "\n", encoding="utf-8")
    for label, row in captures.items():
        print(label, "gross", "/".join(str(row["statistics"][c]["gross"]["median_ticks"]) for c in CASES),
              "CHECKNUM", row["checknum"]["dhrystones"], row["checknum"]["whetstones_K"])
    print(report["status"], "samples=", report["sample_count"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.input_dir, args.output)
