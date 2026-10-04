#!/usr/bin/env python3
"""Non-mutating acceptance/rejection controls for exact compile validation."""
import copy
import json
from pathlib import Path
import compile_cache as cache

OUT = Path(__file__).resolve().parent


def controls(manifest):
    # Validate against the immutable v2 snapshot; no source/log/binary is edited.
    # Production uses the current snapshot and its strict original output path.
    probe = copy.deepcopy(manifest)
    prior = OUT.parent / "p06-ready-chain-regression-20261004-v2"
    probe["current_cpu"] = str(prior / "snapshot/vendor/spk286")
    probe["current_work"] = str(prior / "work")
    unit = "spk286_registers_tb"
    arguments = list(probe["units"][unit]["arguments"])
    records = []
    proof = cache.validate(arguments, probe, probe["current_cpu"])
    records.append({"control": "exact_original_compile", "expected": "accept", "observed": "accept",
                    "binary_sha256": proof["binary_sha256"], "source_closure": proof["source_sha256"]})
    cases = []
    modified = list(arguments)
    modified.remove("--assert")
    cases.append(("changed_compile_flag", modified, copy.deepcopy(probe), probe["current_cpu"]))
    modified = list(arguments)
    modified[-1], modified[-2] = modified[-2], modified[-1]
    cases.append(("changed_compile_source_order", modified, copy.deepcopy(probe), probe["current_cpu"]))
    modified = list(arguments)
    modified[modified.index("--Mdir") + 1] += "-wrong"
    cases.append(("wrong_output_directory", modified, copy.deepcopy(probe), probe["current_cpu"]))
    cases.append(("wrong_snapshot_cwd", arguments, copy.deepcopy(probe), str(prior)))
    for label, name in (("changed_rtl_hash", "rtl/spk286_fetch.sv"),
                        ("changed_bench_hash", "sim/unit/spk286_registers_tb.sv")):
        modified_manifest = copy.deepcopy(probe)
        modified_manifest["units"][unit]["source_sha256"][name] = "0" * 64
        cases.append((label, arguments, modified_manifest, probe["current_cpu"]))
    # Registers has no signals include; use a bank that demonstrably consumed it.
    include_unit = next(name for name, entry in probe["units"].items()
                        if "sim/unit/spk286_signals.svh" in entry["source_sha256"])
    modified_manifest = copy.deepcopy(probe)
    modified_manifest["units"][include_unit]["source_sha256"]["sim/unit/spk286_signals.svh"] = "0" * 64
    cases.append(("changed_included_svh_hash", probe["units"][include_unit]["arguments"], modified_manifest, probe["current_cpu"]))
    for label, field in (("changed_binary_historic_binding", "binary_sha256"),
                         ("changed_compile_log_historic_binding", "build_log_sha256"),
                         ("changed_original_dat_binding", "dat_sha256"),
                         ("changed_prior_receipt_binding", "prior_receipt_sha256"),
                         ("changed_cleanup_receipt_binding", "cleanup_receipt_sha256")):
        modified_manifest = copy.deepcopy(probe)
        modified_manifest["units"][unit][field] = "0" * 64
        cases.append((label, arguments, modified_manifest, probe["current_cpu"]))
    modified_manifest = copy.deepcopy(probe)
    modified_manifest["shared_source_sha256"]["scripts/test_units.sh"] = "0" * 64
    cases.append(("changed_real_test_runner_binding", arguments, modified_manifest, probe["current_cpu"]))
    modified_manifest = copy.deepcopy(probe)
    modified_manifest["verilator_version"] += " altered"
    cases.append(("changed_tool_version", arguments, modified_manifest, probe["current_cpu"]))
    modified_manifest = copy.deepcopy(probe)
    modified_manifest["never_reuse"].append(unit)
    cases.append(("explicitly_ineligible_unit", arguments, modified_manifest, probe["current_cpu"]))
    modified_manifest = copy.deepcopy(probe)
    del modified_manifest["units"][unit]
    cases.append(("unit_without_historic_dual_proof", arguments, modified_manifest, probe["current_cpu"]))
    for label, args, candidate, cwd in cases:
        try:
            cache.validate(args, candidate, cwd)
        except (ValueError, OSError, KeyError) as error:
            records.append({"control": label, "expected": "reject", "observed": "reject", "reason": str(error)})
        else:
            raise RuntimeError("Cache accepted invalid control: " + label)
    result = {"status": "COMPILE_CACHE_CONTROLS_PASS", "controls": records,
              "source_mutation": "None: candidate expectations/arguments are altered in isolated in-memory copies only.",
              "wrapper_sha256": cache.sha(OUT / "compile_cache.py"),
              "manifest_sha256": cache.sha(OUT / "cache-manifest.json"),
              "control_script_sha256": cache.sha(__file__)}
    return result


if __name__ == "__main__":
    manifest = json.loads((OUT / "cache-manifest.json").read_text())
    result = controls(manifest)
    (OUT / "cache-controls.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "control_count": len(result["controls"])}))
