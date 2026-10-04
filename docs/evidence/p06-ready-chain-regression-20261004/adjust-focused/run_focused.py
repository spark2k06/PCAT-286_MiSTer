#!/usr/bin/env python3
"""Validate the strengthened CODE-starvation stimulus without changing oracles."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CPU = ROOT / "vendor/spk286"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt_path = OUT / "receipt.json"
    if receipt_path.exists():
        raise RuntimeError("Fresh outputs required")
    files = sorted(p.decode() for p in subprocess.check_output(
        ["git", "ls-files", "-z", "--", "vendor/spk286"], cwd=ROOT).split(b"\0") if p)
    before = {rel: sha(ROOT / rel) for rel in files}
    started = time.time()
    env = os.environ.copy()
    env["SPK286_BUILD_DIR"] = str(OUT / "work")
    env["SPK286_BUILD_JOBS"] = "2"
    receipt = {"status": "RUNNING", "source_sha256_before": before,
               "started_unix": started, "scope": "Unmodified existing dual adjust instruction bank with CODE READY latency strengthened by 16 cycles, plus strict standalone lint. 8184 architecture vectors and original coverage oracle retained."}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    commands = [["bash", "scripts/lint.sh"],
                ["bash", "scripts/test_units.sh", "both", "spk286_adjust_instructions"]]
    exits = []
    with (OUT / "focused.log").open("w") as stream:
        for command in commands:
            code = subprocess.run(command, cwd=CPU, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=1800).returncode
            exits.append(code)
            if code:
                break
    after = {rel: sha(ROOT / rel) for rel in files}
    changed = sorted(rel for rel in before if before[rel] != after[rel])
    receipt.update(status="ADJUST_CODE_STARVATION_PASS" if not any(exits) and not changed else "FAILED",
                   commands=commands, exit_codes=exits, source_sha256_after=after,
                   source_changes=changed, elapsed_seconds=round(time.time()-started, 3),
                   log_sha256=sha(OUT / "focused.log"))
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "elapsed_seconds", "exit_codes", "source_changes")}), flush=True)
    raise SystemExit(0 if receipt["status"].endswith("PASS") else 1)


if __name__ == "__main__":
    main()
