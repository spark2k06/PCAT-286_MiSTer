"""Retain production P17 integration evidence without changing earlier raw receipts."""
from pathlib import Path
import hashlib
import json
import re
import shutil

run = Path(__file__).resolve().parent
root = run.parents[1]
dest = root / 'docs/evidence/perf01-entry-overlap-20261002/promotion'
dest.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
normalize = lambda p: re.sub(r'\s+', '', re.sub(r'//[^\n]*', '', p.read_text()))
trial = json.loads((run / 'source-manifest.json').read_text())
for name in trial['changed_between_variants']:
    assert normalize(root / name) == normalize(run / 'candidate' / name), name
unchanged = {name: h for name, h in trial['original_sha256'].items()
             if name not in trial['changed_between_variants'] and not name.startswith(('sim/', 'scripts/'))}
assert all(sha(root / name) == h for name, h in unchanged.items()), 'Changed CPU/cache/controller input'
for group in ('promotion-final', 'promotion-entry-final'):
    receipt = json.loads((run / group / 'validation.json').read_text())
    assert receipt['inputs_unchanged'] and all(r['exit_code'] == 0 for r in receipt['checks'])
    target = dest / group
    target.mkdir()
    for source in (run / group).glob('*.json'):
        shutil.copy2(source, target / source.name)
    for source in (run / group).glob('*.log'):
        shutil.copy2(source, target / source.name)
    for record in receipt['checks']:
        assert sha(target / (record['script'] + '.log')) == record['log_sha256']
for name in ('run_promotion.py', 'retain_promotion.py'):
    shutil.copy2(run / name, dest / name)
for group, name in (('promotion', 'test_a1_at_bridge.sh.log'),
                    ('promotion', 'test_at_mister_memory_port.sh.log'),
                    ('promotion-recheck', 'test_a1_at_bridge.sh.log')):
    target = dest / 'initial-fixture-failures'
    target.mkdir(exist_ok=True)
    shutil.copy2(run / group / name, target / (group + '-' + name))
diagnostic = dest / 'initial-rom-failure'
diagnostic.mkdir()
for name in ('control.json', 'baseline-trace.log', 'candidate-trace.log',
             'trace_tb.sv', 'run-baseline.sh', 'run-candidate.sh'):
    shutil.copy2(run / 'rom-diagnostic' / name, diagnostic / name)
shutil.copy2(run/'promotion-entry/test_at_memory_entry/entry.rom',diagnostic/'invalid-jcc.rom')
shutil.copy2(run/'run_rom_control.py',diagnostic/'run_rom_control.py')
record = {'frozen_candidate_matches_production_except_comments': True,
          'unchanged_cpu_cache_controller_config_sha256': unchanged,
          'production_sources_sha256': {name: sha(root / name) for name in trial['changed_between_variants']},
          'full_regression': False,
          'fixture_changes': ['Native command now offered at initial edge; live width changes only after capture.',
                              'Synchronous tag hits counted at completion, cancelled requests inspected by retained tag result.',
                              'Port stimulus settles after changing backend READY before checking combinational outputs.',
                              'New diagnostic ROM initially contained NASM 0F85 (386 near Jcc). P16 and P17 reject with vector 6. Fixed to short Jcc plus near JMP; CPU 286 assembly directive prevents recurrence.'],
          'files': {str(p.relative_to(dest)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                    for p in sorted(dest.rglob('*')) if p.is_file()}}
(dest / 'retained-files.json').write_text(json.dumps(record, indent=2) + '\n')
print('P17_PROMOTION_EVIDENCE_RETAINED', len(record['files']), flush=True)
