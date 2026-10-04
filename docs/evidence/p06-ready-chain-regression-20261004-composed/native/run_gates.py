"""Run distinct standalone stages from a frozen applied source snapshot."""
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
SNAP = RUN / 'snapshot'
TIMEOUT = 1200
LOCK = threading.Lock()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    manifest = json.loads((RUN / 'manifest.json').read_text())
    for name, value in manifest['source_sha256'].items():
        assert sha(SNAP / name) == value, name
    receipt = dict(status='STANDALONE_DISTINCT_GATES_RUNNING', started_utc=utc(),
                   source_sha256=manifest['source_sha256'], manifest_sha256=sha(RUN/'manifest.json'),
                   timeout_seconds=TIMEOUT, parallel_jobs=2, results={},
                   scope='Fresh standalone distinct stages after approved minimal synchronization. Vendor broad gate is separate; this is not a standalone full regression claim.')

    def save():
        (RUN/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')

    def command(key, args, extra_env=None):
        log = RUN/'logs'/(key+'.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env['SPK286_BUILD_DIR'] = str(SNAP/'build'/key)
        env['SPK286_BUILD_JOBS'] = '1'
        env['SPK286_TEST_REAL_MODE_FETCH_WRAP'] = '1'
        env.update(extra_env or {})
        with LOCK:
            receipt['results'][key] = dict(status='RUNNING', command=args, started_utc=utc())
            save()
        started = time.monotonic()
        timed_out = False
        with log.open('w') as stream:
            proc = subprocess.Popen(args, cwd=SNAP, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                code, timed_out = None, True
        text = log.read_text(errors='replace')
        markers = [line for line in text.splitlines()
                   if re.search(r'PASS|FAILED|^ERROR:|^FAIL:|^Ran \d+ tests|^OK$|FATAL:|%Error', line)]
        row = dict(status='TIMEOUT' if timed_out else 'PASS' if code == 0 else 'FAIL',
                   exit_code=code, elapsed_seconds=round(time.monotonic()-started, 3),
                   completed_utc=utc(), command=args, log=log.relative_to(RUN).as_posix(),
                   log_sha256=sha(log), markers=markers)
        with LOCK:
            receipt['results'][key] = row
            save()
        print(key, json.dumps(row), flush=True)
        return code == 0

    def unit(name, simulator):
        key = name + '-' + simulator
        passed = command(key, ['bash', 'scripts/test_units.sh', simulator, name])
        if name == 'spk286_core' and passed:
            top = name + '_tb'
            obj = SNAP/'build'/key
            binary = (obj/'verilator'/top/top if simulator == 'verilator'
                      else obj/'iverilog'/top/(top+'.vvp'))
            args = [str(binary), '+max_policy'] if simulator == 'verilator' else ['vvp', str(binary), '+max_policy']
            command(key+'-max-policy', args)

    jobs = [
        ('lint', ['bash', 'scripts/lint.sh']),
        ('python-modern', ['python3', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
        ('microcode-check', ['python3', '-B', '-m', 'tools.microcode.compile_microcode', '--check']),
        ('profile-focused', ['python3', '-B', 'scripts/check_p06_profile_cpu.py', '--output', str(SNAP/'build/profile-focused')]),
    ]
    names = ('spk286_fetch', 'spk286_core', 'spk286_biu', 'spk286_biu_hold_lock',
             'spk286_biu_width_io', 'spk286_execution', 'spk286_microcode_execution',
             'spk286_adjust_instructions', 'spk286_event_lifecycle')
    # Preserve the standalone-only four sanity stages, using its exact portable
    # source-list loader and the same module commands as synth_check.sh.
    for name in ('spk286_selector', 'spk286_descriptor', 'spk286_protected_state', 'spk286_loadall_service'):
        script = 'set -euo pipefail; source scripts/rtl_sources.sh; yosys -Q -p "read_verilog -sv ${rtl_sources[*]}; hierarchy -check -top '+name+'; proc; opt; check -assert; stat"'
        jobs.append(('yosys-'+name, ['bash', '-c', script]))
    save()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(command, key, args) for key, args in jobs]
        futures += [pool.submit(unit, name, sim) for name in names for sim in ('iverilog', 'verilator')]
        for future in as_completed(futures):
            future.result()
    for name, value in manifest['source_sha256'].items():
        assert sha(SNAP / name) == value, 'Snapshot source changed: '+name
    receipt['sources_unchanged_after_run'] = True
    receipt['status'] = ('STANDALONE_DISTINCT_GATES_PASS'
                         if all(row['status']=='PASS' for row in receipt['results'].values())
                         else 'STANDALONE_DISTINCT_GATES_COMPLETED_WITH_FAILURES')
    receipt['completed_utc'] = utc()
    receipt['runner_sha256'] = sha(Path(__file__))
    save()
    print(receipt['status'], flush=True)


if __name__ == '__main__':
    main()
