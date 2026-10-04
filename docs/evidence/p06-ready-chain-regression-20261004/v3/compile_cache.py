#!/usr/bin/env python3
"""Fail-closed Verilator unit compile reuse; never reuse simulation results."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
REAL_TOOL = "/usr/bin/verilator"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_stat(path):
    value = Path(path).stat()
    return [value.st_size, value.st_ino, value.st_ctime_ns // 10**9,
            value.st_ctime_ns % 10**9, value.st_mtime_ns // 10**9,
            value.st_mtime_ns % 10**9]


def parse_dat(path):
    lines = Path(path).read_text().splitlines()
    command = [line for line in lines if line.startswith('C "')]
    if len(command) != 1 or not command[0].endswith('"'):
        raise ValueError("Missing/ambiguous original compile command")
    arguments = shlex.split(command[0][3:-1])
    inputs = {}
    for line in lines:
        if not line.startswith("S "):
            continue
        tokens = shlex.split(line)
        if len(tokens) != 8 or tokens[7] in inputs:
            raise ValueError("Invalid/duplicate source closure row")
        inputs[tokens[7]] = [int(n) for n in tokens[1:7]]
    if not inputs:
        raise ValueError("No original source closure")
    return arguments, inputs


def argument_value(arguments, option):
    if arguments.count(option) != 1:
        raise ValueError("Missing/duplicate " + option)
    index = arguments.index(option)
    if index + 1 >= len(arguments):
        raise ValueError("Missing value " + option)
    return arguments[index + 1]


def normalized(arguments):
    result = list(arguments)
    index = result.index("--Mdir")
    result[index + 1] = "<OUTPUT_DIR>"
    return result


def validate(arguments, manifest, cwd):
    """Return a complete proof or reject. Has no filesystem mutation."""
    if arguments.count("--binary") != 1:
        raise ValueError("Not a unit --binary compilation")
    unit = argument_value(arguments, "--top-module")
    if not re.fullmatch(r"spk286_[a-z0-9_]+_tb", unit):
        raise ValueError("Non-unit top module")
    if unit in manifest["never_reuse"] or unit not in manifest["units"]:
        raise ValueError("No prior dual-completed eligible unit")
    entry = manifest["units"][unit]
    cpu = Path(manifest["current_cpu"]).resolve()
    if Path(cwd).resolve() != cpu:
        raise ValueError("Wrong frozen snapshot cwd")
    mdir = Path(argument_value(arguments, "--Mdir")).resolve()
    if mdir != (Path(manifest["current_work"]) / "verilator" / unit).resolve():
        raise ValueError("Wrong current output directory")
    if argument_value(arguments, "-o") != unit:
        raise ValueError("Wrong executable name")
    prior_dat = Path(entry["dat"])
    if sha(prior_dat) != entry["dat_sha256"]:
        raise ValueError("Original compile dat drift")
    prior_args, prior_inputs = parse_dat(prior_dat)
    if normalized(arguments) != normalized(prior_args):
        raise ValueError("Compile argument/flag/source ordering mismatch")
    if Path(argument_value(prior_args, "--Mdir")).resolve() != Path(entry["directory"]).resolve():
        raise ValueError("Original compile output directory mismatch")
    closure = {}
    for name, expected in entry["source_sha256"].items():
        path = cpu / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError("Compiled source/include drift: " + name)
        closure[name] = expected
    # Compiler and vector scripts remain real executions, but changes invalidate reuse.
    for name, expected in manifest["shared_source_sha256"].items():
        path = cpu / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError("Build/compiler/generator script drift: " + name)
    actual_closure = {name for name in prior_inputs if not Path(name).is_absolute()}
    if actual_closure != set(entry["source_sha256"]):
        raise ValueError("Original source closure changed")
    version = subprocess.check_output([REAL_TOOL, "--version"], text=True).strip()
    if version != manifest["verilator_version"]:
        raise ValueError("Verilator version drift")
    external = {}
    for name, metadata in prior_inputs.items():
        if not Path(name).is_absolute():
            continue
        if name not in entry["external_sha256"] or file_stat(name) != metadata:
            raise ValueError("Original external Verilator input metadata drift: " + name)
        if sha(name) != entry["external_sha256"][name]:
            raise ValueError("External Verilator input drift: " + name)
        external[name] = {"sha256": entry["external_sha256"][name], "original_stat": metadata}
    for path, expected in manifest["toolchain_sha256"].items():
        if file_stat(path) != manifest["toolchain_stat"][path] or sha(path) != expected:
            raise ValueError("Compile toolchain/header drift: " + path)
    for key in ("prior_receipt", "prior_log", "cleanup_receipt"):
        if sha(entry[key]) != entry[key + "_sha256"]:
            raise ValueError("Historical proof drift: " + key)
    if sha(entry["binary"]) != entry["binary_sha256"]:
        raise ValueError("Executable differs from historical cleanup binding")
    if sha(entry["build_log"]) != entry["build_log_sha256"]:
        raise ValueError("Compile log differs from historical cleanup binding")
    return {"unit": unit, "normalized_arguments": normalized(arguments),
            "actual_arguments": arguments, "source_sha256": closure,
            "shared_source_sha256": manifest["shared_source_sha256"],
            "external_original_inputs": external,
            "verilator_version": version, "binary_sha256": entry["binary_sha256"],
            "historical_compile_log_sha256": entry["build_log_sha256"],
            "historical_dual_finish_lines": entry["finish_lines"],
            "prior_receipt_sha256": entry["prior_receipt_sha256"],
            "prior_log_sha256": entry["prior_log_sha256"],
            "cleanup_receipt_sha256": entry["cleanup_receipt_sha256"],
            "original_dat_sha256": entry["dat_sha256"], "output_directory": str(mdir)}


def event(record):
    directory = OUT / "cache-events"
    directory.mkdir(exist_ok=True)
    record.update(timestamp_unix=time.time(), wrapper_sha256=sha(__file__),
                  manifest_sha256=sha(OUT / "cache-manifest.json"))
    destination = directory / (str(time.time_ns()) + "-" + str(os.getpid()) + ".json")
    destination.write_text(json.dumps(record, indent=2) + "\n")


def main():
    arguments = sys.argv[1:]
    if "--binary" not in arguments:
        os.execv(REAL_TOOL, [REAL_TOOL] + arguments)
    manifest = json.loads((OUT / "cache-manifest.json").read_text())
    try:
        proof = validate(arguments, manifest, Path.cwd())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        event({"status": "CACHE_MISS", "arguments": arguments, "reason": str(error)})
        print("COMPILE_CACHE_MISS: " + str(error), flush=True)
        os.execv(REAL_TOOL, [REAL_TOOL] + arguments)
    entry = manifest["units"][proof["unit"]]
    destination = Path(proof["output_directory"])
    destination.mkdir(parents=True, exist_ok=True)
    binary = destination / proof["unit"]
    # The shell redirects wrapper stdout into the new build.log. Do not overwrite
    # that open file. Store the old compile log separately, labelled historical.
    historical_log = destination / "historical-build.log"
    shutil.copy2(entry["binary"], binary)
    shutil.copy2(entry["build_log"], historical_log)
    binary.chmod(binary.stat().st_mode | 0o111)
    if sha(binary) != proof["binary_sha256"] or sha(historical_log) != proof["historical_compile_log_sha256"]:
        raise RuntimeError("Copied executable/log verification failed")
    proof.update(status="CACHE_HIT", copied_binary_sha256=sha(binary),
                 copied_historical_compile_log_sha256=sha(historical_log),
                 scope="Only compilation reused. No simulation output copied; caller must execute this binary again with newly generated vectors.")
    event(proof)
    print("COMPILE_CACHE_HIT: " + proof["unit"] + " exact validated binary " + proof["binary_sha256"], flush=True)
    print("HISTORICAL_COMPILE_LOG: " + str(historical_log) + "; compile log only, no simulation result reused", flush=True)


if __name__ == "__main__":
    main()
