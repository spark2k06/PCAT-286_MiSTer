#!/usr/bin/env python3
"""Analyze archived target-handoff measurements without changing any workload."""
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
    ("6", "TGT6.CSV", 6, 1586, 30.2, "checknum-max-6-8-10.png"),
    ("8", "TGT8.CSV", 8, 2125, 39.8, "checknum-max-6-8-10.png"),
    ("10", "TGT10.CSV", 10, 2560, 48.3, "checknum-max-6-8-10.png"),
    ("12.5", "REF125.CSV", 12.5, 3157, 58.9, "checknum-125-16-20-25.png"),
    ("16", "TGT16.CSV", 16, 3683, 70.5, "checknum-125-16-20-25.png"),
    ("20", "TGT20.CSV", 20, 4143, 81.1, "checknum-125-16-20-25.png"),
    ("25", "TGT25.CSV", 25, 5023, 91.9, "checknum-125-16-20-25.png"),
    ("MAX", "TGTMAX.CSV", None, 6906, 121.6, "checknum-max-6-8-10.png"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def analyze(output):
    output = output.resolve()
    output.relative_to(ROOT)
    immutable = {}

    def read(path):
        data = path.read_bytes()
        immutable[path] = digest(data)
        return data

    def identity(path):
        data = read(path)
        return {"path": path.relative_to(ROOT).as_posix(),
                "bytes": len(data), "sha256": digest(data)}

    old_path = ROOT / "docs/evidence/p06-mister-ready-chain-20261005/analysis.json"
    physical_path = ROOT / "docs/evidence/p06-physical-reference-20261004/analysis.json"
    native_dir = ROOT / "docs/evidence/p06-native-allprofiles-20261005"
    native_path = native_dir / "manifest.json"
    fit_path = ROOT / "docs/evidence/p06-target-candidate-20261005/manifest.json"
    old = json.loads(read(old_path))
    physical = json.loads(read(physical_path))
    native = json.loads(read(native_path))
    json.loads(read(fit_path))
    assert old["validator_sha256"] == physical["validator_sha256"] == VALIDATOR_SHA256
    assert native["status"] == "ALL_SEVEN_NATIVE_PROFILES_AUTO_AND_VISIBLE_ZERO_GUEST_AND_HOST_PASS"

    def validated(path, label, expected_hash=None):
        data = read(path)
        if expected_hash is not None:
            assert digest(data) == expected_hash, str(path)
        validation = validate_csv(data.decode("ascii"), label)
        assert validation["csv_sha256"] == digest(data)
        return validation, stats(validation)

    captures, changes = {}, []
    for label, name, mhz, dhrystone, whetstone, picture in PROFILES:
        path = output / "raw" / name
        validation, measured = validated(path, label)
        assert validation["metadata"]["pit_mode"] == "2"
        previous = old["captures"][label]
        _, old_stats = validated(ROOT / previous["raw"]["path"], label,
                                 previous["raw"]["sha256"])
        assert old_stats == previous["statistics"]
        checknum = {"dhrystones": dhrystone, "whetstones_K": whetstone,
                    "source": identity(output / "screenshots" / picture),
                    "method": "Transcribed from user screenshot; separate benchmark execution"}
        captures[label] = {
            "raw": identity(path), "original_source": "F:/" + name,
            "nominal_mhz": mhz, "validation": validation, "statistics": measured,
            "checknum": checknum,
            "checknum_change_percent": {
                "dhrystones": 100 * (dhrystone / previous["checknum"]["dhrystones"] - 1),
                "whetstones_K": 100 * (whetstone / previous["checknum"]["whetstones_K"] - 1)},
        }
        for case in CASES:
            current = measured[case]["gross"]
            prior = old_stats[case]["gross"]
            net = measured[case]["difference_of_medians_ticks"]
            changes.append({"profile": label, "case": case,
                            "previous_gross_ticks": prior["median_ticks"],
                            "current_gross_ticks": current["median_ticks"],
                            "elapsed_change_percent": 100 * (current["median_ticks"] / prior["median_ticks"] - 1),
                            "all_new_samples_slower": current["min_ticks"] > prior["max_ticks"],
                            "all_new_samples_faster": current["max_ticks"] < prior["min_ticks"],
                            "net_difference_of_medians_ticks": net,
                            "conditional_nominal_clocks_per_iteration":
                                net * mhz * 1e6 / (256 * 1193182) if mhz else None})

    comparisons = []
    for label, _, _, *_ in PROFILES[:-1]:
        for selection in ("auto", "ws0"):
            name = "native" + label + "-" + selection
            control = native["selected_controls"][name]
            assert control["guest_rc"] == control["host_rc"] == 0
            assert control["cache_flags"] == [0, 0]
            path = native_dir / name / "REF.CSV"
            assert identity(path)["sha256"] == native["artifacts"][name + "/REF.CSV"]["sha256"]
            validation, ref = validated(path, label, control["csv_sha256"])
            assert validation["summaries"] == control["summaries"]
            for case in CASES:
                actual = captures[label]["statistics"][case]["gross"]["median_ticks"]
                expected = ref[case]["gross"]["median_ticks"]
                comparisons.append({"profile": label, "case": case, "reference": name,
                                    "reference_hz": control["hz"], "service_clocks": control["service"],
                                    "reference_gross_ticks": expected,
                                    "elapsed_difference_percent": 100 * (actual / expected - 1),
                                    "frequency_scaling": False, "baseline_subtracted": False})

    for name, row in physical["physical"].items():
        _, ref = validated(ROOT / row["archive_path"], str(row["program_argument"]), row["sha256"])
        assert ref == row["statistics"]
        mhz = row["hardware_selector_nominal_mhz"]
        label = "6" if mhz == 6 else "12.5"
        for case in CASES:
            actual = captures[label]["statistics"][case]["gross"]["median_ticks"]
            expected = ref[case]["gross"]["median_ticks"]
            comparisons.append({"profile": label, "case": case, "reference": name,
                                "reference_nominal_mhz": mhz,
                                "reference_gross_ticks": expected,
                                "raw_elapsed_difference_percent": 100 * (actual / expected - 1),
                                "illustrative_same_cycles_scaled_difference_percent":
                                    100 * (actual / (expected * mhz / float(label)) - 1),
                                "scaling_limit": "Illustrative nominal 12-to-12.5 scaling, not independently calibrated CPU or fixed board delays"})

    transitions = []
    for first, second in zip(PROFILES[:-1], PROFILES[1:]):
        for case in CASES:
            a = captures[first[0]]["statistics"][case]["gross"]
            b = captures[second[0]]["statistics"][case]["gross"]
            transitions.append({"from": first[0], "to": second[0], "case": case,
                                "all_current_faster": b["max_ticks"] < a["min_ticks"]})

    sources = [Path(__file__), ROOT / "scripts/analyze_p06_physical_reference.py",
               ROOT / "SW/CPUTIME/validate_t286ref.py"]
    report = {
        "status": "EIGHT_MISTER_TARGET_HANDOFF_PROFILES_RAW_PASS_MONOTONIC_CALIBRATION_OPEN",
        "date": "2026-10-05", "sources": [identity(p) for p in sources],
        "validator_sha256": VALIDATOR_SHA256,
        "reference_inputs": [identity(p) for p in (old_path, physical_path, native_path, fit_path)],
        "candidate": {
            "rbf_path": "build/p06-target-handoff-allfeatures-20261005-v2/work/output_files/PCAT-286.rbf",
            "rbf_sha256": "88f1075046876d13acafde4834a6ed2a0b385e7ec1de51a3d5646342dc1140b1",
            "association": "User identifies first RBF before beginning timing adjustments",
            "independent_loaded_rbf_identity": "NOT_OBSERVED",
            "fixed50_timing_status": "MEASURED_FIXED50_TIMING_FAIL"},
        "profile_count": len(captures),
        "sample_count": sum(c["validation"]["sample_count"] for c in captures.values()),
        "summary_count": sum(c["validation"]["summary_count"] for c in captures.values()),
        "captures": captures, "elapsed_changes_from_ready_chain": changes,
        "comparisons": comparisons, "adjacent_profile_transitions": transitions,
        "all_gross_transitions_strictly_faster": all(r["all_current_faster"] for r in transitions),
        "units": "Elapsed PIT input ticks; gross includes instrumentation and LOOP",
        "limits": ["Nominal PIT input1193182Hz and reload65536 are uncalibrated assumptions",
                   "Difference of medians is not isolated EU cycles or a paired sample subtraction",
                   "One seven-repetition capture per profile does not measure reboot variability",
                   "Endpoint timer arithmetic cannot exclude whole-period stalls",
                   "CHECKNUM is a separate mixed workload, not an instruction timing oracle",
                   "No new CPU regression, emulator execution, RTL change or fit"]}
    for source in sources:
        target = output / "sources" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == source.read_bytes(), str(target)
        else:
            target.write_bytes(source.read_bytes())
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert all(digest(p.read_bytes()) == expected for p, expected in immutable.items())
    artifacts = {p.relative_to(output).as_posix(): identity(p)
                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps({"status": report["status"],
        "artifacts": artifacts}, indent=2) + "\n", encoding="utf-8")
    for label, capture in captures.items():
        print(label, "gross", [capture["statistics"][c]["gross"]["median_ticks"] for c in CASES],
              "CHECKNUM", capture["checknum"]["dhrystones"], capture["checknum"]["whetstones_K"])
    print(report["status"], report["sample_count"], "samples;", report["summary_count"], "summaries")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    analyze(parser.parse_args().output)
