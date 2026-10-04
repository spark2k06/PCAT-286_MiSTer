#!/usr/bin/env python3
"""Bounded SPK286 make regression with immutable source bindings."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CPU = ROOT / "vendor/spk286"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files():
    paths = [CPU / "Makefile"]
    for directory in ("rtl", "microcode", "scripts", "tools", "tests", "sim"):
        paths += [p for p in (CPU / directory).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix.lower() in (".sv", ".v", ".svh", ".vh", ".hex", ".json", ".py", ".sh", ".cpp", ".c", ".h", ".hpp", ".yaml", ".yml", ".toml", ".mc", ".lst", ".asm", ".txt")]
    paths += [ROOT / "scripts/build_p06_profile_cpu.py",
              ROOT / "rtl/spk286_integration/spk286_machine_cpu.sv",
              CPU / "rtl/timed/spk286_profiled.sv",
              CPU / "rtl/timed/spk286_profiled_events.sv", Path(__file__)]
    return sorted(set(paths))

def bindings():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in source_files()}

def main():
    log = OUT / "regression.log"
    receipt_path = OUT / "receipt.json"
    if log.exists() or receipt_path.exists():
        raise RuntimeError("Fresh output files required")
    before = bindings()
    started = time.time()
    versions = {}
    for name, command in (("python", ["python3", "--version"]),
                          ("verilator", ["verilator", "--version"]),
                          ("iverilog", ["iverilog", "-V"]),
                          ("yosys", ["yosys", "-V"]),
                          ("make", ["make", "--version"])):
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        versions[name] = {"exit_code": proc.returncode, "first_line": proc.stdout.splitlines()[0] if proc.stdout else ""}
        if proc.returncode:
            raise RuntimeError("Tool unavailable: " + name)
    receipt = {"status": "RUNNING", "started_unix": started,
               "source_sha256_before": before, "tool_versions": versions,
               "command": ["make", "regression"],
               "cwd": CPU.relative_to(ROOT).as_posix(),
               "scope": "Broad standalone SPK286 make regression: compiler/Python, all existing dual units, strict lint, simulator/state smoke, available SingleStep smoke, Yosys sanity. Not full hardware corpus/PCAT/OS/STA or fit.",
               "build_dir": OUT.relative_to(ROOT).as_posix() + "/work"}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    env = os.environ.copy()
    env["SPK286_BUILD_DIR"] = str(OUT / "work")
    env["SPK286_BUILD_JOBS"] = "2"
    with log.open("w") as stream:
        proc = subprocess.Popen(["make", "regression"], cwd=CPU, env=env,
                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=10800)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = -124
    after = bindings()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    text = log.read_text(errors="replace")
    markers = [line for line in text.splitlines() if "PASS" in line or "SKIP" in line]
    skips = [line for line in markers if "SKIP" in line]
    passed = code == 0 and "REGRESSION PASS" in text and not changed
    receipt.update(status="SPK286_READY_CHAIN_REGRESSION_PASS" if passed else "FAILED",
                   exit_code=code, elapsed_seconds=round(time.time()-started, 3),
                   source_sha256_after=after, source_changes=changed,
                   log_sha256=sha(log), pass_skip_markers=markers, skips=skips,
                   finished_unix=time.time())
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "exit_code", "elapsed_seconds", "source_changes", "skips")}), flush=True)
    raise SystemExit(0 if passed else 1)

if __name__ == "__main__":
    main()
