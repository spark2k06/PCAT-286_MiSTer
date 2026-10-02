"""Run unchanged CHECKNUM under a BIOS-tick wrapper on a prepared DOS image."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import signal
import subprocess
import time

import sys
sys.path.insert(0, '/mnt/d/GitHub/86Box_dev/tools/spk286_cpu')
from run_pharlap import digest, extract_results
import capture_cpu
sys.path.insert(0, '/mnt/d/GitHub/PCAT-286_MiSTer/build/perf01-data2way-20261002/pcat-data2way')
from coherent_sample import capture_owned, SampleUnavailable

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-root', required=True, type=Path)
parser.add_argument('--arm', required=True, choices=['native50', 'spk50', 'native25-control'])
parser.add_argument('--exe', required=True, type=Path)
parser.add_argument('--build-dir', required=True, type=Path)
parser.add_argument('--roms', required=True, type=Path)
parser.add_argument('--seconds', type=float, default=0,
                    help='Optional host-time bound; zero waits for completion')
args = parser.parse_args()
root = args.run_root.resolve()
out = root / args.arm
exe = args.exe.resolve()
image = out / 'dos-test.img'
profiles = json.loads((root/'profiles.json').read_text())
assert digest(image) == profiles['profiles'][args.arm]['initial_image_sha256']
assert not (out/'measurement.json').exists(), 'Do not overwrite a completed run'
expected_hz = profiles['profiles'][args.arm]['cpu_hz']
is_spk = args.arm == 'spk50'
listing = subprocess.check_output(['nm', '-S', '-C', str(exe)], text=True)
names = ['ram', 'cpu_s', 'cpu_exec', 'cpu_isa_speed', 'isa_cycles', 'tsc']
names += ['exec_spk286' if is_spk else 'exec386_2386']
symbols = {name: int(next(l.split()[0] for l in listing.splitlines()
                         if l.endswith(' '+name)), 16) for name in names}
layout = capture_cpu.offsets(out, args.build_dir) if is_spk else None
spk_symbols = capture_cpu.symbols(exe) if is_spk else None
master, slave = pty.openpty()
env = dict(os.environ, SDL_VIDEODRIVER='offscreen', SDL_AUDIODRIVER='dummy',
           ALSOFT_DRIVERS='null')
command = [str(exe), '-P', str(out), '-O', str(out/'global.cfg'),
           '-R', str(args.roms), '-L', str(out/'86box.log'),
           '-V', 'CHECKNUM '+args.arm]
proc = subprocess.Popen(command, cwd=out, env=env, stdin=slave, stdout=slave,
                        stderr=subprocess.STDOUT)
os.close(slave)
os.set_blocking(master, False)
log = (out/'console.log').open('wb')
started = time.monotonic()
receipt = {'arm':args.arm, 'command':command, 'binary_sha256':digest(exe),
           'started':datetime.datetime.now().astimezone().isoformat(),
           'cpu_hz':expected_hz, 'pid':proc.pid, 'completion':False,
           'image_sha256_before':digest(image), 'samples':[]}
(out/'pid').write_text(str(proc.pid))
(out/'measurement-start.json').write_text(json.dumps(receipt, indent=2)+'\n')
print('START', args.arm, 'pid', proc.pid, flush=True)

def send(command):
    os.write(master, (command+'\n').encode())

def drain():
    try:
        while True:
            data = os.read(master, 65536)
            if not data:
                break
            log.write(data)
            log.flush()
    except (BlockingIOError, OSError):
        pass

def machine_sample():
    return capture_owned(proc, exe, symbols, expected_hz, is_spk,
                         layout, spk_symbols)

last_status = None
next_sample = 8
fast = False
failure = None
try:
    while proc.poll() is None:
        drain()
        elapsed = time.monotonic()-started
        if not fast and elapsed >= 2:
            send('fastfwd')
            fast = True
        if elapsed >= next_sample:
            next_sample = elapsed+30
            try:
                state = machine_sample()
            except SampleUnavailable as error:
                skipped = {'host_elapsed_seconds': round(elapsed, 3),
                           'reason': str(error)}
                receipt.setdefault('skipped_samples', []).append(skipped)
                print('SAMPLE_SKIPPED', args.arm, json.dumps(skipped), flush=True)
                continue
            state['host_elapsed_seconds'] = round(elapsed, 3)
            receipt['samples'].append(state)
            with (out/'samples.jsonl').open('a') as f:
                f.write(json.dumps(state)+'\n')
            results = extract_results(image, out)
            status = results.get('STATUS.TXT', '')
            if status != last_status:
                print('STATUS', args.arm, round(elapsed, 1), repr(status), flush=True)
                last_status = status
            print('PROGRESS', args.arm, json.dumps(state), flush=True)
            send('screenshot')
            if 'ALL_DONE' in status:
                receipt['completion'] = True
                break
        if (root/'stop').exists():
            failure = 'user_stop'
            break
        if args.seconds and elapsed >= args.seconds:
            failure = 'host_time_limit'
            break
        time.sleep(.25)
except Exception as error:
    failure = repr(error)
    raise
finally:
    if proc.poll() is None:
        send('screenshot')
        time.sleep(.5)
        send('exit')
        receipt['host_teardown'] = 'normal'
        for shutdown_stage, seconds in [('exit', 60), ('terminate', 10), ('kill', 10)]:
            if proc.poll() is not None:
                break
            if shutdown_stage == 'terminate':
                receipt['host_teardown'] = 'exit_timeout_then_sigterm'
                proc.terminate()
            elif shutdown_stage == 'kill':
                receipt['host_teardown'] = 'exit_timeout_then_sigkill'
                proc.kill()
            deadline = time.monotonic()+seconds
            while proc.poll() is None and time.monotonic() < deadline:
                drain()
                time.sleep(.1)
        assert proc.poll() is not None, 'Owned emulator did not exit after SIGKILL' 
    drain()
    log.close()
    os.close(master)
    receipt['host_elapsed_seconds'] = round(time.monotonic()-started, 3)
    receipt['emulator_returncode'] = proc.returncode
    receipt['finished'] = datetime.datetime.now().astimezone().isoformat()
    receipt['stop_reason'] = 'all_done' if receipt['completion'] else failure or 'emulator_exit'
    results = extract_results(image, out)
    receipt['guest_status'] = results.get('STATUS.TXT', '')
    value = results.get('TICKRUN.TXT', '')
    receipt['guest_output'] = value
    receipt['guest_success'] = 'RC TICKRUN 0' in receipt['guest_status']
    match = re.fullmatch(r'TICKS_BEGIN=(\d+)\s+(\d+)\s+(\d+\.\d+)\s+TICKS_END=(\d+)\s*', value)
    if match:
        begin, score, math, end = match.groups()
        delta = (int(end)-int(begin)) % 1573040
        receipt.update(dhrystones_per_second=int(score), kwhetstones_per_second=float(math),
                       bios_ticks_begin=int(begin), bios_ticks_end=int(end),
                       guest_application_ticks=delta,
                       guest_application_seconds=delta*65536/1193182)
    receipt['image_sha256_after'] = digest(image)
    receipt['source_sha256_after'] = digest(Path(profiles['source']))
    assert receipt['source_sha256_after'] == profiles['source_sha256_before'], 'Original source image changed'
    (out/'measurement.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('FINISH', args.arm, json.dumps({k:v for k,v in receipt.items() if k not in ('samples','command')}), flush=True)
if not (receipt['completion'] and receipt['guest_success'] and match):
    raise SystemExit('CHECKNUM did not complete with two valid scores and exit code zero')
