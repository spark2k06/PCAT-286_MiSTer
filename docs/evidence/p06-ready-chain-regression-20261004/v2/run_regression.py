#!/usr/bin/env python3
"""Broad make regression on a complete, immutable current-vendor snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
LIVE = ROOT / "vendor/spk286"
SNAPSHOT = OUT / "snapshot"
CPU = SNAPSHOT / "vendor/spk286"
CORPUS = Path("/mnt/d/GitHub/SPK286/.cache/singlestep-80286")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bindings(root, relative_files):
    return {name: sha(root / name) for name in relative_files}


def changes(before, after):
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def main():
    log = OUT / "regression.log"
    receipt_path = OUT / "receipt.json"
    if log.exists() or receipt_path.exists() or SNAPSHOT.exists():
        raise RuntimeError("Fresh output directory required")
    started = time.time()
    files = sorted(p.decode() for p in subprocess.check_output(
        ["git", "ls-files", "-z", "--", "vendor/spk286"], cwd=ROOT).split(b"\0") if p)
    if not files:
        raise RuntimeError("Missing tracked vendor inputs")
    before = bindings(ROOT, files)
    for name in files:
        destination = SNAPSHOT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    snapshot_before = bindings(SNAPSHOT, files)
    if snapshot_before != before:
        raise RuntimeError("Snapshot differs from origin")
    sys.path.insert(0, str(CPU))
    from tools.run_singlestep import INHERITED_OPCODES
    corpus_files = ["revocation_list.txt"] + ["v1_real_mode/" + op + ".MOO.gz"
                                             for op in sorted(set(INHERITED_OPCODES))]
    missing_corpus = [name for name in corpus_files if not (CORPUS / name).is_file()]
    if missing_corpus:
        raise RuntimeError("Required original smoke corpus inputs absent: " + repr(missing_corpus))
    corpus_before = bindings(CORPUS, corpus_files)
    versions = {}
    for name, command in (("python", ["python3", "--version"]),
                          ("verilator", ["verilator", "--version"]),
                          ("iverilog", ["iverilog", "-V"]),
                          ("yosys", ["yosys", "-V"]),
                          ("make", ["make", "--version"])):
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        versions[name] = {"exit_code": proc.returncode,
                          "first_line": proc.stdout.splitlines()[0] if proc.stdout else ""}
        if proc.returncode:
            raise RuntimeError("Tool unavailable: " + name)
    prior = json.loads((OUT.parent / "p06-ready-chain-regression-20261004-v1/receipt.json").read_text())
    fixture_changes = changes(
        {k: v for k, v in prior["source_sha256_before"].items()
         if k.startswith("vendor/spk286/tests/fixtures/")},
        {k: v for k, v in before.items() if k.startswith("vendor/spk286/tests/fixtures/")
         and k in prior["source_sha256_before"]})
    if fixture_changes:
        raise RuntimeError("Historical fixtures changed: " + repr(fixture_changes))
    receipt = {"status": "RUNNING", "started_unix": started,
               "command": ["make", "regression"], "snapshot_cwd": str(CPU),
               "origin_git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "source_sha256_before": before, "snapshot_sha256_before": snapshot_before,
               "runner_sha256": sha(Path(__file__)), "tool_versions": versions,
               "external_corpus": str(CORPUS), "corpus_sha256_before": corpus_before,
               "historical_fixture_changes": fixture_changes,
               "build_dir": str(OUT / "work"),
               "scope": "Unmodified standalone make regression against the complete current tracked vendor snapshot: compiler/Python, strict lint, all directed units in both simulators with existing explicit expand-down policy, simulator/state smoke, 10-case per admitted inherited SingleStep opcode smoke, Yosys full synthesis sanity. Not full external hardware corpus, PCAT/OS regression, STA or Quartus fit.",
               "baseline_failure": "v1 exact pre-existing three failures/five errors in historical compiler fixtures retained; six adapter files migrated explicitly without changing JSON fixtures. Existing LOADALL token-deletion negative exposed a compiler guard defect; guard fixed without changing ROM/compiler encoding or weakening the negative."}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": "RUNNING", "snapshot_files": len(files),
                      "corpus_inputs": len(corpus_files), "receipt": str(receipt_path)}), flush=True)
    env = os.environ.copy()
    env["SPK286_BUILD_DIR"] = str(OUT / "work")
    env["SPK286_BUILD_JOBS"] = "2"
    env["SPK286_SINGLESTEP_ROOT"] = str(CORPUS)
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
    after = bindings(ROOT, files)
    snapshot_after = bindings(SNAPSHOT, files)
    corpus_after = bindings(CORPUS, corpus_files)
    origin_changes = changes(before, after)
    snapshot_changes = changes(snapshot_before, snapshot_after)
    corpus_changes = changes(corpus_before, corpus_after)
    lines = log.read_text(errors="replace").splitlines()
    markers = [line for line in lines if "PASS" in line or "SKIP" in line or "SINGLESTEP SUMMARY" in line]
    skips = [line for line in markers if "SKIP" in line]
    passed = (code == 0 and "REGRESSION PASS" in lines and
              not origin_changes and not snapshot_changes and not corpus_changes)
    receipt.update(status="SPK286_READY_CHAIN_REGRESSION_PASS" if passed else "FAILED",
                   exit_code=code, elapsed_seconds=round(time.time()-started, 3),
                   source_sha256_after=after, snapshot_sha256_after=snapshot_after,
                   corpus_sha256_after=corpus_after,
                   source_changes=origin_changes, snapshot_changes=snapshot_changes,
                   corpus_changes=corpus_changes, log_sha256=sha(log),
                   pass_skip_markers=markers, skips=skips, finished_unix=time.time())
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "exit_code", "elapsed_seconds",
                                             "source_changes", "snapshot_changes", "corpus_changes", "skips")}), flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
