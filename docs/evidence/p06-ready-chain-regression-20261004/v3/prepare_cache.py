#!/usr/bin/env python3
"""Bind only successful v2 dual units to compile commands and historic hashes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import compile_cache as cache

OUT = Path(__file__).resolve().parent
PRIOR = OUT.parent / "p06-ready-chain-regression-20261004-v2"


def prepare():
    receipt_path = PRIOR / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if receipt["source_changes"] or receipt["snapshot_changes"] or receipt["corpus_changes"]:
        raise ValueError("v2 source/corpus drift")
    if cache.sha(PRIOR / "regression.log") != receipt["log_sha256"]:
        raise ValueError("v2 regression log drift")
    text = (PRIOR / "regression.log").read_text(errors="replace")
    finishes = {}
    previous_nonempty = ""
    pass_lines = {}
    for line in text.splitlines():
        match = re.search(r"sim/unit/(spk286_[a-z0-9_]+_tb)\.sv:\d+: (?:Verilog \$finish|\$finish called)", line)
        if match:
            if " PASS" in previous_nonempty and "MICROCODE CHECK" not in previous_nonempty:
                finishes.setdefault(match[1], []).append(line)
                pass_lines.setdefault(match[1], []).append(previous_nonempty)
        if line.strip():
            previous_nonempty = line
    cleanup = {}
    for path in sorted(PRIOR.glob("cleanup-*.json")):
        saved = json.loads(path.read_text())
        if saved["status"] != "COMPLETED_UNIT_INTERMEDIATE_CLEANUP":
            continue
        for unit in saved["units"]:
            if unit["binary_sha256_before"] != unit["binary_sha256_after"] or unit["build_log_sha256_before"] != unit["build_log_sha256_after"]:
                raise ValueError("Historical cleanup changed preserved artifacts")
            cleanup[unit["unit"]] = (path, unit)
    version = subprocess.check_output([cache.REAL_TOOL, "--version"], text=True).strip()
    if version != receipt["tool_versions"]["verilator"]["first_line"]:
        raise ValueError("Tool version differs from v2")
    # The shared scripts remain executed; their identity also binds compile reuse.
    shared = {name[len("vendor/spk286/"):]: value for name, value in receipt["snapshot_sha256_after"].items()
              if name == "vendor/spk286/Makefile" or name.startswith(("vendor/spk286/scripts/", "vendor/spk286/tools/"))}
    toolchain_paths = {Path(p).resolve() for p in ("/usr/bin/verilator", "/usr/bin/verilator_bin", "/usr/bin/g++", "/usr/bin/gcc", "/usr/bin/as", "/usr/bin/ld", "/usr/bin/ar")}
    toolchain_paths.update(p.resolve() for p in Path("/usr/share/verilator/include").rglob("*") if p.is_file())
    toolchain_stat = {str(p): cache.file_stat(p) for p in sorted(toolchain_paths)}
    # On ext4, ctime cannot be restored by copy/touch. Reject if any compile
    # tool/header was installed/replaced/edited after the original run began.
    if any(value[2] + value[3] / 10**9 > receipt["started_unix"] for value in toolchain_stat.values()):
        raise ValueError("Toolchain/header changed since v2 began; use fresh compilation")
    toolchain_sha = {path: cache.sha(path) for path in toolchain_stat}
    units = {}
    rejected = {}
    for unit, lines in sorted(finishes.items()):
        try:
            if not any("Verilog $finish" in line for line in lines) or not any("$finish called" in line for line in lines):
                raise ValueError("Not dual completed")
            if unit == "spk286_adjust_instructions_tb" or unit not in cleanup:
                raise ValueError("No prior historical cleanup binding")
            cleanup_path, bound = cleanup[unit]
            directory = PRIOR / "work/verilator" / unit
            dat = directory / ("V" + unit + "__verFiles.dat")
            arguments, inputs = cache.parse_dat(dat)
            source_hashes, external_hashes = {}, {}
            for name, metadata in inputs.items():
                if Path(name).is_absolute():
                    if cache.file_stat(name) != metadata:
                        raise ValueError("Original external input metadata differs")
                    external_hashes[name] = cache.sha(name)
                    continue
                full_name = "vendor/spk286/" + name
                expected = receipt["snapshot_sha256_before"][full_name]
                if expected != receipt["snapshot_sha256_after"][full_name] or cache.sha(Path(receipt["snapshot_cwd"]) / name) != expected:
                    raise ValueError("Original source closure drift")
                source_hashes[name] = expected
            binary, log = directory / unit, directory / "build.log"
            if cache.sha(binary) != bound["binary_sha256_before"] or cache.sha(log) != bound["build_log_sha256_before"]:
                raise ValueError("Binary/log differs from historical cleanup binding")
            units[unit] = {"directory": str(directory), "arguments": arguments,
                           "dat": str(dat), "dat_sha256": cache.sha(dat),
                           "source_sha256": source_hashes, "external_sha256": external_hashes,
                           "binary": str(binary), "binary_sha256": bound["binary_sha256_before"],
                           "build_log": str(log), "build_log_sha256": bound["build_log_sha256_before"],
                           "prior_receipt": str(receipt_path), "prior_receipt_sha256": cache.sha(receipt_path),
                           "prior_log": str(PRIOR / "regression.log"), "prior_log_sha256": receipt["log_sha256"],
                           "cleanup_receipt": str(cleanup_path), "cleanup_receipt_sha256": cache.sha(cleanup_path),
                           "finish_lines": lines, "pass_lines": pass_lines[unit]}
        except (OSError, ValueError, KeyError) as error:
            rejected[unit] = str(error)
    manifest = {"scope": "Exact previous Verilator binary compilations only; all vector generation and simulation must run anew.",
                "current_cpu": str(OUT / "snapshot/vendor/spk286"), "current_work": str(OUT / "work"),
                "never_reuse": ["spk286_adjust_instructions_tb"], "verilator_version": version,
                "shared_source_sha256": shared, "toolchain_stat": toolchain_stat,
                "toolchain_sha256": toolchain_sha, "units": units, "rejected_prior_units": rejected,
                "prepare_script_sha256": cache.sha(__file__)}
    return manifest


if __name__ == "__main__":
    manifest = prepare()
    destination = OUT / "cache-manifest.json"
    if destination.exists():
        raise RuntimeError("Fresh manifest required")
    destination.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"eligible_prior_units": len(manifest["units"]), "rejected": manifest["rejected_prior_units"]}))
