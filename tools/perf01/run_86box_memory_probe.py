"""Run unchanged CHECKNUM with ideal or RTL-generated PCAT memory READY."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-root', required=True, type=Path)
    p.add_argument('--probe-root', required=True, type=Path)
    p.add_argument('--86box-root', dest='box', required=True, type=Path)
    p.add_argument('--roms', required=True, type=Path)
    p.add_argument('--mode', required=True, choices=['ideal', 'pcat'])
    p.add_argument('--seconds', type=int, default=0)
    p.add_argument('--probe-binary', type=Path)
    p.add_argument('--arm-name', help='Distinct directory name for an explicit repeat')
    p.add_argument('--at-refresh', type=int, choices=(0, 1),
                   help='Explicit AT refresh/HOLD control for the private extended adapter')
    a = p.parse_args()
    reference, probe, box = a.reference_root.resolve(), a.probe_root.resolve(), a.box.resolve()
    out = probe/(a.arm_name or a.mode)
    assert not out.exists(), 'Use a fresh diagnostic arm; preserve existing receipts'
    target = out/'spk50'
    target.mkdir(parents=True)
    # The non-executed preparation check is the exact initial measurement image.
    source = reference/'preparation-check/spk50/dos-test.img'
    prepared = json.loads((reference/'preparation-check/profiles.json').read_text())
    assert sha(source) == prepared['profiles']['spk50']['initial_image_sha256']
    sys.path.insert(0, str(box/'tools/spk286_cpu'))
    from run_pharlap import fat
    fs = fat(source, True)
    try:
        assert hashlib.sha256(fs.readbytes('/PHAR_LAP/CHECKNUM.EXE')).hexdigest() == \
            '38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6'
        assert b'/TESTMEM:OFF' in fs.readbytes('/CONFIG.SYS')
        assert b'TICKRUN > C:\\RESULTS\\TICKRUN.TXT' in fs.readbytes('/AUTOEXEC.BAT')
    finally:
        fs.close()
    shutil.copyfile(source, target/'dos-test.img')
    measured = reference/'spk50'
    for name in ('86box.cfg', 'global.cfg'):
        shutil.copyfile(measured/name, target/name)
    # Calibrated SPK50 CMOS avoids an interactive oscillator acknowledgement.
    shutil.copytree(measured/'nvr', target/'nvr')
    shutil.copytree(measured/'nvr', target/'nvr-initial')
    profiles = {'source':str(source), 'source_sha256_before':sha(source),
                'profiles':{'spk50':{'cpu_hz':50000000,
                    'initial_image_sha256':sha(target/'dos-test.img')}}}
    (out/'profiles.json').write_text(json.dumps(profiles, indent=2)+'\n')
    env = dict(os.environ, PCAT_MEMORY_TIMING='1' if a.mode == 'pcat' else '0',
               PCAT_MEMORY_PROFILE=str(target/'memory-profile.json'))
    if a.at_refresh is not None:
        env['PCAT_AT_REFRESH'] = str(a.at_refresh)
    runner_source = box/'tools/spk286_cpu/run_checknum.py'
    runner = out/'run_checknum_private.py'
    runner_text = runner_source.read_text()
    runner_text = runner_text.replace('from run_pharlap import digest, extract_results',
        'import sys\nsys.path.insert(0, '+repr(str(box/'tools/spk286_cpu'))+')\n'
        'from run_pharlap import digest, extract_results', 1)
    # Freeze the sampler with the arm. Read CPU and RTL ports during one stop;
    # a transient host stop timeout must not destroy an unfinished guest run.
    sampler = out/'coherent_sample.py'
    shutil.copyfile(Path(__file__).with_name('coherent_sample.py'), sampler)
    runner_text = runner_text.replace('import capture_cpu',
        'import capture_cpu\nsys.path.insert(0, '+repr(str(out))+')\n'
        'from coherent_sample import capture_owned, SampleUnavailable', 1)
    begin = runner_text.index('def machine_sample():\n')
    end = runner_text.index('\nlast_status = None', begin)
    runner_text = runner_text[:begin] + '''def machine_sample():
    return capture_owned(proc, exe, symbols, expected_hz, is_spk,
                         layout, spk_symbols)
''' + runner_text[end:]
    old_sample = '''            state = machine_sample()
            state['host_elapsed_seconds'] = round(elapsed, 3)
            if is_spk:
                cpu = capture_cpu.capture(proc, exe, layout, spk_symbols, out)
                state.update({k:cpu[k] for k in ('debug_cs', 'debug_instruction_ip',
                    'debug_timing_cycle_count', 'halted', 'shutdown', 'control_error',
                    'microcode_fault', 'unsupported_opcode')})'''
    new_sample = '''            try:
                state = machine_sample()
            except SampleUnavailable as error:
                skipped = {'host_elapsed_seconds': round(elapsed, 3),
                           'reason': str(error)}
                receipt.setdefault('skipped_samples', []).append(skipped)
                print('SAMPLE_SKIPPED', args.arm, json.dumps(skipped), flush=True)
                continue
            state['host_elapsed_seconds'] = round(elapsed, 3)'''
    assert runner_text.count(old_sample) == 1, 'Upstream sample block changed'
    runner_text = runner_text.replace(old_sample, new_sample)
    # Keep draining the owned PTY during teardown. Preserve guest completion
    # and an explicit timeout/termination receipt even if host cleanup stalls.
    old_shutdown = '''        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)'''
    new_shutdown = '''        receipt['host_teardown'] = 'normal'
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
        assert proc.poll() is not None, 'Owned emulator did not exit after SIGKILL' '''
    assert runner_text.count(old_shutdown) == 1, 'Upstream runner shutdown changed'
    runner.write_text(runner_text.replace(old_shutdown, new_shutdown))
    command = ['python3', str(runner),
               '--run-root', str(out), '--arm', 'spk50',
               '--exe', str((a.probe_binary or probe/'probe/86Box-memory-probe').resolve()),
               '--build-dir', str(box/'build/spk286'), '--roms', str(a.roms),
               '--seconds', str(a.seconds)]
    (out/'probe-run.json').write_text(json.dumps({'command':command,
        'at_refresh_control':a.at_refresh,
        'memory_mode':a.mode, 'initial_image_sha256':sha(target/'dos-test.img'),
        'config_sha256':sha(target/'86box.cfg'),
        'nvr_sha256':{f.name:sha(f) for f in (target/'nvr').iterdir()},
        'checknum_sha256':'38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6',
        'upstream_runner_sha256':sha(runner_source),
        'runner_sha256':sha(runner), 'sampler_sha256':sha(sampler)}, indent=2)+'\n')
    subprocess.run(command, env=env, check=True)


if __name__ == '__main__':
    main()
