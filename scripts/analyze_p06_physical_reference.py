#!/usr/bin/env python3
"""Archive and compare four collaborator T286REF2 physical CSV captures.

Python standard library only. Inputs remain byte-exact and read-only. Raw
validation is conditional on the program's PIT reload/crystal assumptions;
no calibrated CPU clock, per-instruction cycle count or board wait is inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SW/CPUTIME"))
from validate_t286ref import validate_csv, VALIDATOR_SHA256  # noqa: E402

PROGRAM_SHA256 = "006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643"
PHYSICAL = (("REG6_6.CSV", 6, "6"), ("REG6_12.CSV", 6, "12"),
            ("REG12_6.CSV", 12, "6"), ("REG12_12.CSV", 12, "12"))
NATIVE = (
    ("native6-auto", "p06-timing-reference-20261003/native6-final", 6000000, None, 0, 2),
    ("native12-auto", "p06-timing-reference-20261003/native12-final", 12500000, None, 0, 3),
    ("native6-ws1", "p06-waitstates-reference-20261003/native6-ws1", 6000000, 1, 2, 3),
    ("native12-ws1", "p06-waitstates-reference-20261003/native12-ws1", 12500000, 1, 2, 3),
    ("native6-ws2", "p06-waitstates-reference-20261003/native6-ws2", 6000000, 2, 3, 4),
    ("native12-ws2", "p06-waitstates-reference-20261003/native12-ws2", 12500000, 2, 3, 4),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def copy_exact(source, target):
    data = source.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == data, f"Refusing to replace changed raw archive {target}"
    else:
        target.write_bytes(data)
    return {"source": source.relative_to(ROOT).as_posix(), "sha256": sha(data), "bytes": len(data)}


def stats(validation, repetitions=7):
    result = {}
    for case in ("R0", "B0", "M0"):
        result[case] = {}
        for kind in ("baseline", "gross"):
            values = [row["ticks"] for row in validation["samples"]
                      if row["case"] == case and row["kind"] == kind]
            assert len(values) == repetitions
            result[case][kind] = {
                "ticks_by_rep": values, "n": repetitions, "min_ticks": min(values),
                "median_ticks": statistics.median(values), "max_ticks": max(values),
                "range_percent_of_median": 100 * (max(values) - min(values)) / statistics.median(values),
            }
        result[case]["difference_of_medians_ticks"] = (
            result[case]["gross"]["median_ticks"] - result[case]["baseline"]["median_ticks"])
    return result


def capture(path, copied, expected_nominal):
    data = path.read_bytes()
    validation = validate_csv(data.decode("ascii"), expected_nominal)
    assert validation["csv_sha256"] == sha(data)
    copied.parent.mkdir(parents=True, exist_ok=True)
    if copied.exists():
        assert copied.read_bytes() == data, f"Refusing to replace changed raw archive {copied}"
    else:
        copied.write_bytes(data)
    assert copied.read_bytes() == data
    return {"source_path": str(path.resolve()), "archive_path": copied.relative_to(ROOT).as_posix(),
            "bytes": len(data), "sha256": sha(data), "validation": validation, "statistics": stats(validation)}


def compare(physical, native):
    result = []
    for name, physical_row in physical.items():
        physical_hz = physical_row["hardware_selector_nominal_mhz"] * 1000000
        for label, native_row in native.items():
            if (physical_hz == 6000000) != (native_row["actual_cpu_hz"] == 6000000):
                continue
            scale = native_row["actual_cpu_hz"] / physical_hz
            for case in ("R0", "B0", "M0"):
                p = physical_row["statistics"][case]["gross"]["median_ticks"]
                n = native_row["statistics"][case]["gross"]["median_ticks"]
                result.append({"physical": name, "native": label, "case": case,
                    "physical_gross_median_ticks": p, "native_gross_median_ticks": n,
                    "raw_elapsed_ratio": p / n, "raw_elapsed_percent_difference": 100 * (p / n - 1),
                    "native_frequency_scale_to_physical_nominal": scale,
                    "illustrative_scaled_native_ticks": n * scale,
                    "frequency_normalized_elapsed_ratio": p / (n * scale),
                    "frequency_normalized_elapsed_percent_difference": 100 * (p / (n * scale) - 1),
                    "normalization_scope": "Same-cycle-count frequency scaling only; not a measured native 12 MHz run or board-timing equivalence"})
    return result


def analyze(input_dir, output, refresh=False, zero_wait_bundle=None):
    output = output.resolve()
    output.relative_to(ROOT.resolve())
    output.mkdir(parents=True, exist_ok=refresh)
    physical, native = {}, {}
    for name, hardware_mhz, argument in PHYSICAL:
        physical[name] = capture(input_dir / name, output / "physical" / name, argument)
        row = physical[name]
        row.update({"hardware_selector_nominal_mhz": hardware_mhz, "program_argument": argument,
            "hardware_selector_source": "Direct user statement: first filename number is hardware selector; second is program argument",
            "cpu_board_bios_ram_dos_identity": "NOT_PROVIDED",
            "program_binary_sha256_on_physical_machine": "NOT_PROVIDED"})
        assert row["validation"]["metadata"]["pit_mode"] == "3"
        for sample in row["validation"]["samples"]:
            assert sample["raw_delta"] == 2 * sample["ticks"]
    native_inputs = [(label, ROOT / "docs/evidence" / folder, hz, wait, config, service)
                     for label, folder, hz, wait, config, service in NATIVE]
    zero_verification = None
    if zero_wait_bundle is not None:
        zero_wait_bundle = zero_wait_bundle.resolve()
        zero_wait_bundle.relative_to(ROOT.resolve())
        native_inputs += [
            ("native6-ws0", zero_wait_bundle / "native6-ws0", 6000000, 0, 1, 2),
            ("native12-ws0", zero_wait_bundle / "native12-ws0", 12500000, 0, 1, 2),
        ]
        data = (zero_wait_bundle / "verification.json").read_bytes()
        zero_verification = json.loads(data)
        assert zero_verification["status"] == "TWO_NATIVE_VISIBLE_ZERO_WAIT_GUEST_AND_HOST_PASS"
        assert len(zero_verification["runs"]) == 2
        assert {row["label"] for row in zero_verification["runs"]} == {"native6-ws0", "native12-ws0"}
        for row in zero_verification["runs"]:
            assert row["guest_rc"] == row["host_rc"] == row["runner_rc"] == 0
            assert not row["process_alive"] and row["config"] == 1 and row["service"] == 2
            assert row["visible_wait_states"] == 0 and row["cache_flags"] == [0, 0]
            assert row["program_sha256"] == PROGRAM_SHA256
        copy_exact(zero_wait_bundle / "verification.json", output / "native-zero-verification.json")
        # Keep the input layout reusable from committed archives, without
        # depending on the ignored build directory or copying a disk/exe.
        copy_exact(zero_wait_bundle / "verification.json", output / "native" / "verification.json")
    for label, source, hz, wait, config, service in native_inputs:
        nominal = "6" if hz == 6000000 else "12.5"
        native[label] = capture(source / "REF.CSV", output / "native" / label / "REF.CSV", nominal)
        data = (source / "measurement.json").read_bytes()
        measure = json.loads(data)
        assert measure["completed"] and measure["guest_success"]
        assert measure["emulator_returncode"] == 0 and measure["failure"] is None
        assert measure["hz"] == hz and measure["program_sha256"] == PROGRAM_SHA256
        assert measure["csv_validation"]["csv_sha256"] == native[label]["sha256"]
        assert measure["validator_sha256"] == VALIDATOR_SHA256
        assert measure["cpu_waitstates_config"] == config if wait is not None else True
        assert measure.get("requested_visible_wait_states") == wait
        assert measure["samples"]
        for sample in measure["samples"]:
            assert sample["cpu_hz_actual"] == hz and sample["cpu_waitstates"] == config
            assert all(sample[key] == service for key in ("cpu_prefetch_cycles", "cpu_cycles_read", "cpu_cycles_write"))
            if wait == 0:
                assert sample["cpu_cache_int_enabled"] == sample["cpu_cache_ext_enabled"] == 0
        archived = output / "native" / label / "measurement.json"
        if archived.exists():
            assert archived.read_bytes() == data
        else:
            archived.write_bytes(data)
        native[label].update({"actual_cpu_hz": hz, "visible_wait_states": wait,
            "selection": "automatic" if wait is None else f"visible_{wait}_wait_states",
            "cpu_waitstates_config": config, "prefetch_read_write_service_cycles": service,
            "measurement_source": (source / "measurement.json").relative_to(ROOT).as_posix(),
            "measurement_sha256": sha(data), "program_sha256": measure["program_sha256"],
            "native_executable_sha256": measure["binary_sha256"],
            "measurement_samples": measure["samples"], "host_exit": 0, "guest_success": True})
        assert native[label]["validation"]["metadata"]["pit_mode"] == "2"
        for sample in native[label]["validation"]["samples"]:
            assert sample["raw_delta"] == sample["ticks"]
        if wait == 0:
            verified = next(row for row in zero_verification["runs"] if row["label"] == label)
            assert verified["hz"] == hz and verified["csv_sha256"] == native[label]["sha256"]
            assert verified["artifacts"]["measurement.json"] == sha(data)
            assert verified["binary_sha256"] == measure["binary_sha256"]
            assert (source / "STATUS.TXT").read_text().splitlines() == ["BEGIN", "RC0", "ALL_DONE"]
            supporting = {}
            for name in ("STATUS.TXT", "samples.json", "start.json", "initial-86box.cfg",
                         "initial-config-provenance.json", "86box.cfg", "console.log", "86box.log"):
                supporting[name] = copy_exact(source / name, output / "native" / label / name)
                if name in verified["artifacts"]:
                    assert supporting[name]["sha256"] == verified["artifacts"][name], name
            assert supporting["initial-86box.cfg"]["sha256"] == measure["initial_config_sha256"]
            assert (source / "nvr-initial").is_dir()
            for path in sorted((source / "nvr-initial").glob("*")):
                assert path.is_file()
                name = "nvr-initial/" + path.name
                supporting[name] = copy_exact(path, output / "native" / label / name)
                assert supporting[name]["sha256"] == measure["initial_nvr_sha256"][path.name]
            native[label]["supporting_artifacts"] = supporting
    comparisons = compare(physical, native)
    pooled = {}
    for hardware_mhz in (6, 12):
        names = [f"REG{hardware_mhz}_6.CSV", f"REG{hardware_mhz}_12.CSV"]
        left, right = (physical[name] for name in names)
        for key in ("code_segment_decimal", "aligned_word_offset_decimal", "pit_mode", "pit_status_without_out"):
            assert left["validation"]["metadata"][key] == right["validation"]["metadata"][key], key
        records = left["validation"]["samples"] + right["validation"]["samples"]
        pooled[f"physical{hardware_mhz}-pooled"] = {
            "hardware_selector_nominal_mhz": hardware_mhz, "source_files": names,
            "n_per_case_kind": 14, "sample_count": 84,
            "basis": "Two captures at the same hardware selector; argument6/12 is metadata-only, not another CPU speed",
            "statistics": stats({"samples": records}, 14),
        }
    pooled_comparisons = compare(pooled, native)
    parameter_controls = []
    for hardware_mhz in (6, 12):
        left, right = physical[f"REG{hardware_mhz}_6.CSV"], physical[f"REG{hardware_mhz}_12.CSV"]
        for case in ("R0", "B0", "M0"):
            for kind in ("baseline", "gross"):
                a, b = (x["statistics"][case][kind]["median_ticks"] for x in (left, right))
                parameter_controls.append({"hardware_selector_nominal_mhz": hardware_mhz,
                    "case": case, "kind": kind, "argument6_median_ticks": a,
                    "argument12_median_ticks": b, "percent_change_arg12_vs_arg6": 100 * (b / a - 1)})
    selector_ratios = []
    for argument in ("6", "12"):
        for case in ("R0", "B0", "M0"):
            a = physical[f"REG6_{argument}.CSV"]["statistics"][case]["gross"]["median_ticks"]
            b = physical[f"REG12_{argument}.CSV"]["statistics"][case]["gross"]["median_ticks"]
            selector_ratios.append({"program_argument": argument, "case": case,
                "elapsed_ratio_selector6_over_selector12": a / b})
    exploratory_model = []
    for case in ("R0", "B0", "M0"):
        t6 = physical["REG6_6.CSV"]["statistics"][case]["gross"]["median_ticks"]
        t12 = physical["REG12_12.CSV"]["statistics"][case]["gross"]["median_ticks"]
        intercept = 2 * t12 - t6
        exploratory_model.append({"case": case, "formula": "T_ticks(f_MHz)=A/f_MHz+B",
            "A_ticks_times_MHz": 6 * (t6 - intercept), "B_ticks": intercept,
            "basis": "Two primary gross medians at nominal selectors6/12 only",
            "scope": "Exact descriptive two-point fit; no residual degrees of freedom, causal attribution, per-instruction timings or high-frequency extrapolation"})
    program = ROOT / "docs/evidence/p06-timing-reference-20261003/T286REF.COM"
    assert sha(program.read_bytes()) == PROGRAM_SHA256
    report = {
        "status": "PHYSICAL_REFERENCE_RAW_VALIDATION_PASS_NOT_CALIBRATED",
        "analysis_source_sha256": sha(Path(__file__).read_bytes()),
        "validator_sha256": VALIDATOR_SHA256,
        "asm_source_sha256": sha((ROOT / "SW/CPUTIME/t286ref.asm").read_bytes()),
        "known_reference_program_sha256": PROGRAM_SHA256,
        "physical": physical, "native": native, "comparisons": comparisons,
        "pooled_physical": pooled, "pooled_comparisons": pooled_comparisons,
        "parameter_controls": parameter_controls, "hardware_selector_ratios": selector_ratios,
        "exploratory_two_point_model": exploratory_model,
        "physical_sample_count": 168, "native_sample_count": len(native) * 42,
        "units": "Elapsed PIT input ticks, conditional on assumed divisor65536 and nominal input1193182Hz",
        "gross_scope": "Fixed256iterations including setup/dispatch/LOOP/signature stores/timer read overhead; seven samples per case/kind; no baseline subtraction",
        "native_zero_selection_limit": ("Automatic config0 and explicitly measured visible0 config1 are archived separately; neither identifies the unknown physical board waits"
            if zero_wait_bundle else "Archived config0 means Automatic, not visible zero wait states; no visible0 control is present in this bundle"),
        "native_zero_verification_sha256": sha((zero_wait_bundle / "verification.json").read_bytes()) if zero_wait_bundle else None,
        "limits": ["Physical CPU marking/board/BIOS/RAM/DOS/TSRs/waits and executable hash unprovided",
            "Physical actual6/12MHz and PIT crystal/reload are not independently calibrated",
            "Native12.5MHz differs from physical selector nominal12MHz",
            "Frequency scaling assumes equal cycle counts and does not scale ISA/PIT/board fixed delays independently",
            "Mode3 physical CSV exercises existing arithmetic/signatures but does not independently certify PIT implementation",
            "Endpoint intervals cannot rule out whole-period stalls, SMI/NMI or unknown board READY activity",
            "No CPU cycle count, single wait-state value, native-pin accuracy or production timing change inferred"],
        "decision": "Anchor provisional6/12 fixed-work validation with these physical observations. Use a class/bus-sensitive model for EU, prefetch and RAM, retaining Intel contracts and separate board READY policy. Predict8/10/12.5/16/20/25 profiles from that model and native86Box reference until measured. Do not identify one global scale/wait value or immediately retune RTL solely from these three aggregate kernels. MAX remains dependency-driven and separate.",
    }
    (output / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    artifacts = {p.relative_to(output).as_posix(): {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps({"status": report["status"],
        "analysis_source_sha256": report["analysis_source_sha256"], "artifacts": artifacts,
        "provenance": "User-supplied physical files; unmodified frozen native reference CSV/measurement receipts; no source files overwritten"}, indent=2) + "\n")
    for name, row in physical.items():
        print(name, "gross", "/".join(str(row["statistics"][c]["gross"]["median_ticks"]) for c in ("R0", "B0", "M0")), "RAW_VALIDATED")
    for row in comparisons:
        if row["physical"] in ("REG6_6.CSV", "REG12_12.CSV"):
            print(row["physical"], row["native"], row["case"],
                  f"normalized elapsed {row['frequency_normalized_elapsed_percent_difference']:+.3f}%")
    for row in pooled_comparisons:
        print(row["physical"], row["native"], row["case"],
              f"pooled normalized elapsed {row['frequency_normalized_elapsed_percent_difference']:+.3f}%")
    print(report["status"], f"physical_samples=168 native_samples={report['native_sample_count']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--refresh-report", action="store_true", help="Recompute derived JSON only; existing raw archives must remain byte-identical")
    parser.add_argument("--zero-wait-bundle", type=Path, help="Optional completed native6-ws0/native12-ws0 bundle; both guest/host/runtime controls must pass")
    args = parser.parse_args()
    analyze(args.input_dir, args.output, args.refresh_report, args.zero_wait_bundle)
