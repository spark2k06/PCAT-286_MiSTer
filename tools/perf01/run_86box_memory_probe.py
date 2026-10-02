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
    command = ['python3', str(box/'tools/spk286_cpu/run_checknum.py'),
               '--run-root', str(out), '--arm', 'spk50',
               '--exe', str((a.probe_binary or probe/'probe/86Box-memory-probe').resolve()),
               '--build-dir', str(box/'build/spk286'), '--roms', str(a.roms),
               '--seconds', str(a.seconds)]
    (out/'probe-run.json').write_text(json.dumps({'command':command,
        'memory_mode':a.mode, 'initial_image_sha256':sha(target/'dos-test.img'),
        'config_sha256':sha(target/'86box.cfg'),
        'nvr_sha256':{f.name:sha(f) for f in (target/'nvr').iterdir()},
        'checknum_sha256':'38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6',
        'runner_sha256':sha(box/'tools/spk286_cpu/run_checknum.py')}, indent=2)+'\n')
    subprocess.run(command, env=env, check=True)


if __name__ == '__main__':
    main()
