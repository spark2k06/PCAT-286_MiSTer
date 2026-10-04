"""Run three independent source-guarded compatibility shards, then aggregate."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUNNER = ROOT / "scripts/test_p06_profile_compatibility.py"
sys.path.insert(0, str(ROOT / "scripts"))
import test_p06_profile_compatibility as h

GROUPS = (h.UNITS[:9], h.UNITS[9:18], h.UNITS[18:])
assert [len(group) for group in GROUPS] == [9, 9, 8]
assert len({name for group in GROUPS for name in group}) == 26
COMMANDS = [[sys.executable, str(RUNNER), "--output", str(OUT / f"shard-{index}"),
             "--units", ",".join(group)] for index, group in enumerate(GROUPS, 1)]
manifest = {"runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
            "commands": COMMANDS, "counts": "208 Icarus + 56 Verilator + 26 original/private MAX"}
(OUT / "launch.json").write_text(json.dumps(manifest, indent=2) + "\n")
processes = set()
lock = threading.Lock()

def worker(item):
    index, command = item
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    with lock:
        processes.add(process)
    try:
        with (OUT / f"shard-{index}-progress.log").open("w") as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(f"SHARD{index} {line.rstrip()}", flush=True)
        code = process.wait()
        return {"shard": index, "returncode": code, "seconds": time.monotonic() - started}
    finally:
        with lock:
            processes.discard(process)

pool = ThreadPoolExecutor(max_workers=3)
try:
    results = list(pool.map(worker, enumerate(COMMANDS, 1)))
except KeyboardInterrupt:
    # Only terminate process groups created by this launcher.
    with lock:
        owned = list(processes)
    for process in owned:
        os.killpg(process.pid, signal.SIGTERM)
    raise
finally:
    pool.shutdown(wait=True, cancel_futures=True)
(OUT / "shard-exits.json").write_text(json.dumps(results, indent=2) + "\n")
if any(result["returncode"] != 0 for result in results):
    raise RuntimeError("one or more shards failed; see preserved progress logs")
aggregate_command = [sys.executable, str(RUNNER), "--output", str(OUT), "--aggregate",
                     *(str(OUT / f"shard-{index}/receipt.json") for index in (1, 2, 3))]
manifest["aggregate_command"] = aggregate_command
(OUT / "launch.json").write_text(json.dumps(manifest, indent=2) + "\n")
subprocess.run(aggregate_command, cwd=ROOT, check=True)
