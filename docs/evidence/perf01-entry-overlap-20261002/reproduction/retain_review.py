"""Archive this bounded review and an explicitly incomplete DOS run snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

run = Path(__file__).resolve().parent
root = run.parents[1]
out = root / 'docs/evidence/perf01-entry-overlap-20261002'
out.mkdir(parents=True, exist_ok=True)
receipt = []


def retain(source, target):
    destination = out / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    receipt.append({'source': str(source), 'retained': target,
                    'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})


for name in ('source-manifest.json', 'candidate.patch', 'directed-comparison.json',
             'completed-baseline-review.json'):
    retain(run / name, name)
for name in ('run_validation.py', 'analyze_review.py', 'retain_review.py'):
    retain(run / name, 'reproduction/' + name)
for variant in ('baseline', 'candidate'):
    work = run / ('directed-' + variant)
    for name in ('compiled-sources.sha256', 'performance-macros.txt',
                 'performance-config.sha256', 'sources-verified.log'):
        retain(work / name, 'directed/' + variant + '/' + name)
    for path in work.glob('*-p03-*.log'):
        retain(path, 'directed/' + variant + '/' + path.name)
    for path in (work / 'ideal-writes').glob('*.log'):
        retain(path, 'directed/' + variant + '/ideal-writes/' + path.name)
for path in (run / 'validation').glob('*.log'):
    retain(path, 'validation/' + path.name)
for name in ('validation.json', 'spk286_at_mister_memory_port_tb.sv',
             'spk286_at_bridge_cancel_pipeline_tb.sv', 'original-counter-tb.sv'):
    retain(run / 'validation' / name, 'validation/' + name)
for name in ('verilator-run.log', 'sources-verified.log'):
    retain(run / 'cancel-candidate' / name, 'small-cancel/' + name)
smoke = run / 'probe/memory_smoke'
smoke_output = subprocess.check_output([str(smoke)], text=True)
assert 'MEMORY_PROBE_SMOKE_PASS' in smoke_output
(out / 'validation/probe-smoke.log').write_text(smoke_output)
arm = run / 'pcat-entry-overlap'
for name in ('probe-run.json', 'profiles.json', 'spk50/measurement-start.json',
             'spk50/86box.cfg', 'spk50/global.cfg', 'spk50/memory-profile.json',
             'spk50/memory-profile.json.phases.jsonl'):
    retain(arm / name, 'ongoing-dos/' + name)
retain(run / 'probe/build-manifest.json', 'ongoing-dos/build-manifest.json')
# Check the retained snapshot's JSON and record that it is not a final result.
profile = json.loads((out / 'ongoing-dos/spk50/memory-profile.json').read_text())
samples = [json.loads(line) for line in (arm / 'spk50/samples.jsonl').read_text().splitlines()]
(out / 'ongoing-dos/status.json').write_text(json.dumps({
    'captured_utc': datetime.now(timezone.utc).isoformat(), 'completed': False,
    'profile_final': profile['final'], 'phase': profile['phase'],
    'latest_coherent_owned_sample': samples[-1],
    'note': 'Ongoing private CHECKNUM; no complete score or guest exit status accepted.',
}, indent=2) + '\n')
manifest = json.loads((run / 'source-manifest.json').read_text())
assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
           for name, digest in manifest['original_sha256'].items())
assert all(hashlib.sha256((run / variant / name).read_bytes()).hexdigest() == digest
           for variant, names in manifest['variant_sha256'].items()
           for name, digest in names.items())
(out / 'inventory.json').write_text(json.dumps({
    'files': receipt, 'production_inputs_unchanged': True,
    'private_variant_inputs_unchanged': True,
    'read_only_ongoing_process_snapshot': True, 'full_regression': False,
}, indent=2) + '\n')
print('ENTRY_OVERLAP_REVIEW_RETAINED', len(receipt), profile['phase'], flush=True)
