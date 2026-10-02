#!/usr/bin/env python3
"""Bounded, isolated validation of the prepared PERF01 owner prototype."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/mnt/d/GitHub/PCAT-286_MiSTer')
EXP = ROOT / 'build/perf01-owner-experiment'
BASE = ROOT / 'build/perf01-response-baseline-20261002/work'
WORK = EXP / 'work'
OWNER = Path('rtl/spk286_integration/spk286_at_mister_sdram_owner.sv')
PROTO = EXP / 'spk286_at_mister_sdram_owner_direct_response.sv'

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def manifest(root):
    return {str(p.relative_to(root)): digest(p)
            for p in sorted(root.rglob('*')) if p.is_file()
            and 'build' not in p.relative_to(root).parts}

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

if WORK.exists():
    raise SystemExit('Private work already exists; refusing to replace it.')
baseline = manifest(BASE)
assert digest(BASE / OWNER) == '06567e808d7d8a9c444efeb60c9ac163eb573a9e1e33946ef63ac8a5738f2992'
shutil.copytree(BASE, WORK, copy_function=shutil.copy2)
shutil.copyfile(PROTO, WORK / OWNER)
candidate = manifest(WORK)
differences = [name for name in sorted(set(baseline) | set(candidate))
               if baseline.get(name) != candidate.get(name)]
assert differences == [str(OWNER)], differences
write_json(EXP / 'private-sources.json', {
    'baseline_root': str(BASE), 'candidate_root': str(WORK),
    'changed_files': differences, 'baseline': baseline, 'candidate': candidate,
    'copy_method': 'shutil.copytree/copy2: independent file contents, no hardlinks',
})
print(f'PRIVATE_OWNER_COPY_PASS files={len(candidate)} changed=1', flush=True)

def run(name, command, env_extra=None):
    started = datetime.now(timezone.utc).isoformat()
    env = os.environ.copy()
    env.update(env_extra or {})
    log = EXP / f'{name}.log'
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=WORK, env=env,
                                stdout=stream, stderr=subprocess.STDOUT)
    record = {'name': name, 'command': command, 'cwd': str(WORK),
              'environment': env_extra or {}, 'started_utc': started,
              'ended_utc': datetime.now(timezone.utc).isoformat(),
              'exit_code': result.returncode, 'log': str(log),
              'log_sha256': digest(log)}
    write_json(EXP / f'{name}-result.json', record)
    print(f'OWNER_STAGE {name} exit={result.returncode}', flush=True)
    if result.returncode:
        print('\n'.join(log.read_text(errors='replace').splitlines()[-16:]), flush=True)
    return record

def directed():
    stages = [
        ('capture', ['bash', 'scripts/test_at_sdram_capture.sh'],
         {'PCAT_BUILD_DIR': str(EXP / 'capture'),
          'AT_SDRAM_OWNER_SOURCE': str(WORK / OWNER)}),
        ('entry', ['bash', 'scripts/test_at_sdram_entry.sh', str(EXP / 'entry')], {}),
        ('owner', ['bash', 'scripts/test_at_mister_sdram_owner.sh'], {}),
        ('ram-buffer-pipeline', ['bash', 'scripts/test_at_ram_read_buffer.sh'],
         {'PCAT_BUILD_DIR': str(EXP / 'ram-buffer-pipeline')}),
        ('code-buffer', ['bash', 'scripts/test_at_sdram_read_buffer.sh'], {}),
        ('memory-port', ['bash', 'scripts/test_at_mister_memory_port.sh'], {}),
    ]
    return [run(*stage) for stage in stages]

def profile():
    return run('profile', ['bash', 'scripts/test_checkit_directed.sh'],
               {'PCAT_SOURCE_ROOT': str(WORK), 'PCAT_BUILD_DIR': str(EXP / 'profile'),
                'PCAT_PROFILE': '1'})

with ThreadPoolExecutor(max_workers=2) as pool:
    directed_future = pool.submit(directed)
    profile_future = pool.submit(profile)
    records = directed_future.result() + [profile_future.result()]

assert manifest(BASE) == baseline, 'Baseline source copy changed during validation'
assert manifest(WORK) == candidate, 'Candidate source copy changed during validation'
write_json(EXP / 'validation-summary.json', {
    'status': 'PASS' if all(r['exit_code'] == 0 for r in records) else 'FAIL',
    'source_guard': 'PASS', 'baseline_unchanged': True,
    'owner_only_difference': True, 'records': records,
})
print('OWNER_SOURCE_GUARD_PASS', flush=True)
raise SystemExit(0 if all(r['exit_code'] == 0 for r in records) else 1)
