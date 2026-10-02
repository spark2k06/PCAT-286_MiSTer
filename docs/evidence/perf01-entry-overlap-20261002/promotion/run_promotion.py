"""Run bounded production integration checks and retain immutable input hashes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

run = Path(__file__).resolve().parent
root = run.parents[1]
out = run / (sys.argv[1] if len(sys.argv) > 1 else 'promotion')
out.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
names = [str(p.relative_to(root)) for folder in ('rtl/spk286_integration',
    'sim/spk286_integration', 'vendor/spk286/rtl', 'vendor/spk286/microcode/generated')
    for p in (root / folder).glob('*') if p.suffix in ('.sv', '.svh')]
scripts = ['test_at_bridge_response.sh', 'test_a1_at_bridge.sh',
           'test_at_bridge_cancel_pipeline.sh', 'test_at_mister_memory_port.sh',
           'test_at_ram_read_buffer.sh', 'test_at_machine_boundary.sh',
           'test_a2_memory_arbiter.sh']
if len(sys.argv) > 2:
    scripts = sys.argv[2:]
names += ['scripts/' + name for name in scripts] + ['config.tcl',
          'scripts/at_performance_flags.sh', 'tools/perf01/memory_probe_smoke.cpp']
before = {name: sha(root / name) for name in names}
(out / 'input-manifest.json').write_text(json.dumps(before, indent=2) + '\n')

def execute(name):
    start = time.monotonic()
    env = dict(os.environ, PCAT_BUILD_DIR=str(out / name.removesuffix('.sh')))
    log = out / (name + '.log')
    command = ['bash', str(root / 'scripts' / name)]
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=root, env=env, timeout=1200,
                                stdout=stream, stderr=subprocess.STDOUT)
    record = dict(script=name, command=command, exit_code=result.returncode,
                  elapsed_seconds=time.monotonic()-start, log_sha256=sha(log))
    print('P17_PROMOTION_CHECK', json.dumps(record), flush=True)
    return record

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(execute, scripts))
changed = [name for name, h in before.items() if sha(root / name) != h]
receipt = {'checks': results, 'inputs_unchanged': not changed,
           'changed_during_run': changed, 'full_regression': False}
(out / 'validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert not changed, changed
assert all(r['exit_code'] == 0 for r in results), results
print('P17_PRODUCTION_DIRECTED_PASS', flush=True)
