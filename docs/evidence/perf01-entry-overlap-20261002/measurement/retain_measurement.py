"""Retain complete P17 CHECKNUM receipts after strict P16 identity comparison."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

run = Path(__file__).resolve().parent
root = run.parents[1]
sys.path.insert(0, str(root / 'tools/perf01'))
from summarize_memory_probe import summarize
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
arms = {'baseline': root/'build/perf01-write-admission-20261002/pcat-write-admission',
        'candidate': run/'pcat-entry-overlap'}
comparison = json.loads((run/'comparison.json').read_text())
assert comparison['baseline']['dhrystones_per_second'] == 5666
assert comparison['baseline']['kwhetstones_per_second'] == 102.9
dest = root/'docs/evidence/perf01-entry-overlap-20261002/measurement'
dest.mkdir(exist_ok=False)
for name, arm in arms.items():
    assert summarize(arm, True) == comparison[name]
    target = dest/name
    target.mkdir()
    receipt = json.loads((arm/'spk50/measurement.json').read_text())
    binary = Path(receipt['command'][0])
    for source in (arm/'probe-run.json', arm/'profiles.json',
                   arm/'spk50/measurement.json', arm/'spk50/measurement-start.json',
                   arm/'spk50/memory-profile.json', arm/'spk50/memory-profile.json.phases.jsonl',
                   arm/'spk50/samples.jsonl', arm/'spk50/STATUS.TXT',
                   arm/'spk50/TICKRUN.TXT', arm/'spk50/86box.cfg',
                   arm/'run_checknum_private.py', arm/'coherent_sample.py'):
        shutil.copy2(source,target/source.name)
    shutil.copy2(binary.parent/'build-manifest.json',target/'adapter-build.json')
    run_receipt = json.loads((arm/'probe-run.json').read_text())
    assert sha(target/'run_checknum_private.py') == run_receipt['runner_sha256']
    assert sha(target/'coherent_sample.py') == run_receipt['sampler_sha256']
shutil.copy2(run/'comparison.json',dest/'comparison.json')
shutil.copy2(Path(__file__),dest/'retain_measurement.py')
files = {str(p.relative_to(dest)): {'sha256': sha(p), 'bytes': p.stat().st_size}
         for p in sorted(dest.rglob('*')) if p.is_file()}
(dest/'retained-files.json').write_text(json.dumps(files,indent=2)+'\n')
print('P17_COMPLETE_CHECKNUM_RETAINED',len(files),flush=True)
