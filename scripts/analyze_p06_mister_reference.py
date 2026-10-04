#!/usr/bin/env python3
"""Preserve and analyze user supplied MiSTer T286REF2 profile captures.

Read-only workload analysis with the existing validator. No emulator, RTL
test or synthesis is launched. Elapsed comparisons do not measure CPU clocks.
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

PROFILES = (
    ("MAX", "REF_MAX.CSV", "MAX", None, 6906, 121.6),
    ("6", "REF_6.CSV", "6", 6, 1674, 32.2),
    ("8", "REF_8.CSV", "8", 8, 2181, 41.8),
    ("10", "REF_10.CSV", "10", 10, 2695, 52.0),
    ("12.5", "REF_125.CSV", "12.5", 12.5, 3234, 61.4),
    ("16", "REF_16.CSV", "16", 16, 3854, 74.6),
    ("20", "REF_20.CSV", "20", 20, 4361, 84.1),
    ("25", "REF_25.CSV", "25", 25, 5023, 91.9),
)
SCREENSHOTS = (
    ("codex-clipboard-6328f217-5687-427f-95f3-28d1b4ec5080.png", "checknum-max-6-8-10.png"),
    ("codex-clipboard-86b90b66-c8f1-4311-a924-a39501c9cfbb.png", "checknum-125-16-20.png"),
    ("codex-clipboard-9903b3ef-ad44-4583-a3aa-815828156440.png", "checknum-25.png"),
)
CASES = ("R0", "B0", "M0")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == data, f"Changed raw archive: {path}"
    else:
        path.write_bytes(data)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(data), "bytes": len(data)}


def reference(row, expected):
    data = (ROOT / row["archive_path"]).read_bytes()
    assert sha(data) == row["sha256"]
    validation = validate_csv(data.decode("ascii"), expected)
    measured = stats(validation)
    assert measured == row["statistics"]
    return measured


def compare(profile, mhz, source, source_mhz, measured, ref):
    rows = []
    for case in CASES:
        actual = measured[case]["gross"]["median_ticks"]
        raw = ref[case]["gross"]["median_ticks"]
        normalized = raw * source_mhz / mhz
        rows.append({"profile": profile, "case": case, "reference": source,
                     "reference_nominal_mhz": source_mhz,
                     "mister_gross_median_ticks": actual,
                     "reference_gross_median_ticks": raw,
                     "frequency_normalized_reference_ticks": normalized,
                     "elapsed_percent_difference": 100 * (actual / normalized - 1),
                     "frequency_normalization": "reference_ticks * reference_MHz / profile_MHz",
                     "normalization_limit": "Illustrative equal-cycle-count scaling; fixed board/ISA/port delays are not independently scaled"})
    return rows


def analyze(input_dir, output, screenshots=None):
    output = output.resolve()
    output.relative_to(ROOT.resolve())
    output.mkdir(parents=True, exist_ok=True)
    captures = {}
    for label, filename, nominal, mhz, dhrystone, whetstone in PROFILES:
        data = (input_dir / filename).read_bytes()
        validation = validate_csv(data.decode("ascii"), nominal)
        assert validation["csv_sha256"] == sha(data)
        assert validation["metadata"]["pit_mode"] == "2"
        assert all(r["raw_delta"] == r["ticks"] for r in validation["samples"])
        captures[label] = {
            "user_source": "F:/" + filename,
            "archive": archive(data, output / "raw" / filename),
            "nominal_profile_mhz": mhz, "validation": validation,
            "statistics": stats(validation),
            "checknum": {"dhrystones": dhrystone, "whetstones_K": whetstone,
                         "source": "Numbers transcribed from user supplied screenshots; separate run from T286REF"},
        }
    reference_path = ROOT / "docs/evidence/p06-physical-reference-20261004/analysis.json"
    reference_data = reference_path.read_bytes()
    references = json.loads(reference_data)
    comparisons = []
    controls = {}
    for profile, mhz, prefix in (("6", 6, "native6"), ("12.5", 12.5, "native12")):
        for selection in ("ws0", "auto", "ws1", "ws2"):
            name = prefix + "-" + selection
            row = references["native"][name]
            measured = reference(row, profile)
            controls[name] = {k: row[k] for k in (
                "actual_cpu_hz", "visible_wait_states", "selection", "cpu_waitstates_config",
                "prefetch_read_write_service_cycles", "archive_path", "sha256")}
            comparisons += compare(profile, mhz, name, row["actual_cpu_hz"] / 1e6,
                                   captures[profile]["statistics"], measured)
    for profile, mhz, filename, nominal in (("6", 6, "REG6_6.CSV", "6"),
                                          ("12.5", 12.5, "REG12_12.CSV", "12")):
        row = references["physical"][filename]
        comparisons += compare(profile, mhz, filename, float(nominal),
                               captures[profile]["statistics"], reference(row, nominal))
    scaling, transitions = [], []
    for label, _, _, mhz, _, _ in PROFILES[1:]:
        measured = captures[label]["statistics"]
        for case in CASES:
            baseline = measured[case]["baseline"]["median_ticks"]
            gross = measured[case]["gross"]["median_ticks"]
            scaling.append({"profile": label, "case": case,
                            "gross_ticks_times_nominal_mhz": gross * mhz,
                            "difference_of_medians_ticks": gross - baseline,
                            "conditional_nominal_clocks_per_iteration_from_difference":
                                (gross - baseline) * mhz * 1e6 / 1193182 / 256,
                            "limit": "Descriptive subtraction/normalization, not isolated EU cycles or a measured clock"})
    for previous, current in zip(PROFILES[1:-1], PROFILES[2:]):
        for case in CASES:
            a, b = (captures[p[0]]["statistics"][case]["gross"] for p in (previous, current))
            transitions.append({"from": previous[0], "to": current[0], "case": case,
                                "elapsed_percent_change": 100 * (b["median_ticks"] / a["median_ticks"] - 1),
                                "all_current_samples_slower_than_all_previous": b["min_ticks"] > a["max_ticks"]})
    screenshot_archives = []
    if screenshots:
        for source, target in SCREENSHOTS:
            screenshot_archives.append(archive((screenshots / source).read_bytes(), output / "screenshots" / target))
    else:
        for _, target in SCREENSHOTS:
            path = output / "screenshots" / target
            if path.exists():
                screenshot_archives.append(archive(path.read_bytes(), path))
    fit_path = ROOT / "docs/evidence/p06-osd-candidate-20261004/fit/record/receipt.json"
    fit_data = fit_path.read_bytes()
    fit = json.loads(fit_data)
    rbf_sha = "61337ec247fed74f0ebdeb388c0b86243f9152744f0a5c8debb3f4ffb6b63067"
    assert fit["rbf"]["sha256"] == rbf_sha and fit["rbf"]["bytes"] == 4122520
    report = {
        "status": "MISTER_PROFILE_RAW_VALIDATION_PASS_CALIBRATION_PENDING",
        "date": "2026-10-04", "analysis_source_sha256": sha(Path(__file__).read_bytes()),
        "statistics_source_sha256": sha((ROOT / "scripts/analyze_p06_physical_reference.py").read_bytes()),
        "validator_sha256": VALIDATOR_SHA256,
        "reference_analysis": {"path": reference_path.relative_to(ROOT).as_posix(), "sha256": sha(reference_data)},
        "candidate": {
            "rbf_path": "build/p06-osd-allfeatures-seed1-v2-fit-20261004/work/output_files/PCAT-286.rbf",
            "rbf_sha256": rbf_sha,
            "fit_receipt": fit_path.relative_to(ROOT).as_posix(), "fit_receipt_sha256": sha(fit_data),
            "association": "User confirms this RBF and Reset & apply settings for each selected profile",
            "frequency_display": "User reports BIOS and CheckIT display the intended nominal MHz",
            "physical_timing": "Common 50MHz clock; archived setup=-17.001ns, hold=+0.076ns. These captures do not close STA",
        },
        "profile_count": len(captures), "sample_count": sum(c["validation"]["sample_count"] for c in captures.values()),
        "summary_count": sum(c["validation"]["summary_count"] for c in captures.values()),
        "units": "Elapsed PIT input ticks conditional on assumed reload65536 and nominal input1193182Hz",
        "captures": captures, "screenshots": screenshot_archives,
        "native_controls": controls, "comparisons": comparisons,
        "scaling": scaling, "adjacent_profile_transitions": transitions,
        "previous_user_reported_max_checknum": {"dhrystones": 6906, "whetstones_K": 121.6,
                                               "same_numbers_now": True, "scope": "Auxiliary benchmark preservation, not a complete regression"},
        "limits": ["One capture per MiSTer profile with seven repetitions per kernel/kind",
                   "Physical collaborator board identity, actual clock and executable hash remain unverified",
                   "MiSTer executable identity is not independently established by the CSV",
                   "Mode2 MiSTer/native and mode3 physical are normalized by the unchanged validator",
                   "No measured native T286REF controls at8/10/16/20/25MHz exist in this reference bundle",
                   "T286REF intervals include setup, dispatch, LOOP, signatures and port I/O",
                   "BIOS/CheckIT MHz indication alone does not calibrate every instruction or board wait",
                   "The25vs20 R0 cause is unassigned pending a CPU/BIU scheduling trace"],
        "decision": "First synthesized selector has hardware fixed-work evidence for all eight profiles. Keep MAX unchanged. P06/P12 historical calibration remains open; qualify branch/prefetch, board READ policy and25MHz implementation extensions before any timing adjustment. Do not derive one global benchmark multiplier.",
    }
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    artifacts = {p.relative_to(output).as_posix(): {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps({"status": report["status"], "artifacts": artifacts}, indent=2) + "\n", encoding="utf-8")
    for label, row in captures.items():
        print(label, "gross", "/".join(str(row["statistics"][c]["gross"]["median_ticks"]) for c in CASES),
              "CHECKNUM", row["checknum"]["dhrystones"], row["checknum"]["whetstones_K"])
    for row in comparisons:
        if row["reference"].endswith("ws0") or row["reference"].endswith(".CSV"):
            print(row["profile"], row["reference"], row["case"], f"elapsed {row['elapsed_percent_difference']:+.3f}%")
    print(report["status"], "samples=", report["sample_count"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    analyze(args.input_dir, args.output, args.screenshots)
