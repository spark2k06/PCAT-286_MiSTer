"""Run six independent original-bank tests from an immutable source snapshot."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time

RUN = Path(__file__).resolve().parent
WORK = RUN / 'work'
VENDOR = WORK / 'vendor/spk286'
UNITS = ('spk286_stack_frame_instructions', 'spk286_far_instructions', 'spk286_muldiv_instructions')
TIMEOUT_SECONDS = 1200
LOCK = threading.Lock()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    manifest = json.loads((RUN / 'manifest.json').read_text())
    hashes = manifest['source_sha256']
    for name, expected in hashes.items():
        assert sha(WORK / name) == expected, name
    receipt = dict(status='STARVATION_PREFLIGHT_RUNNING', started_utc=utc(),
                   source_count=len(hashes), manifest_sha256=sha(RUN/'manifest.json'),
                   source_sha256=hashes, units=list(UNITS), timeout_seconds_per_run=TIMEOUT_SECONDS,
                   parallel_jobs=2, results={},
                   scope='Unmodified frozen CPU RTL and original full instruction banks. No architectural oracle, fixture or expectation change; independent simulators even on failure.')
    def save():
        (RUN/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    save()
    def execute(unit, simulator):
        key = unit + '/' + simulator
        destination = RUN / 'results' / unit / simulator
        destination.mkdir(parents=True, exist_ok=False)
        env = os.environ.copy()
        env['SPK286_BUILD_DIR'] = str(destination/'objects')
        env['SPK286_BUILD_JOBS'] = '1'
        command = ['bash', 'scripts/test_units.sh', simulator, unit]
        with LOCK:
            receipt['results'][key] = dict(status='RUNNING', started_utc=utc(), command=command)
            save()
        start = time.monotonic()
        timed_out = False
        with (destination/'run.log').open('w') as output:
            try:
                process = subprocess.Popen(command, cwd=VENDOR, env=env,
                                           stdout=output, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                code = process.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                timed_out, code = True, None
        log = (destination/'run.log').read_text(errors='replace')
        markers = [line for line in log.splitlines() if re.search(r'(?:INSTRUCTIONS PASS|%Fatal|%Error|FATAL:|Error [0-9]|immediate starvation|starvation exercised)', line)]
        for name, expected in hashes.items():
            assert sha(WORK/name) == expected, 'Snapshot mutated: '+name
        result = dict(status='TIMEOUT' if timed_out else 'PASS' if code==0 else 'FAIL',
                      exit_code=code, elapsed_seconds=round(time.monotonic()-start,3),
                      completed_utc=utc(), log=str((destination/'run.log').relative_to(RUN)),
                      log_sha256=sha(destination/'run.log'), markers=markers)
        with LOCK:
            receipt['results'][key] = result
            save()
        print(key, json.dumps(result), flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(execute, unit, simulator)
                for unit in UNITS for simulator in ('verilator','iverilog')]
        for job in as_completed(jobs):
            job.result()
    receipt['status'] = ('STARVATION_PREFLIGHT_DUAL_PASS'
                         if all(r['status']=='PASS' for r in receipt['results'].values())
                         else 'STARVATION_PREFLIGHT_COMPLETED_WITH_FAILURES')
    receipt['completed_utc'] = utc()
    receipt['runner_sha256'] = sha(Path(__file__))
    save()
    print(receipt['status'], flush=True)


if __name__=='__main__':
    main()
