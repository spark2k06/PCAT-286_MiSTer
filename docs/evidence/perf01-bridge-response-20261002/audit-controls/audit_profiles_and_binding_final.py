from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
import sys

ROOT = Path('/mnt/d/GitHub/PCAT-286_MiSTer')
OUT = ROOT / 'build/perf01-audit-controls'
SOURCE_PROFILE = ROOT / 'build/perf01-response-baseline-20261002/profile'
SCRIPTS = OUT / 'final-checked-scripts'
OUT = OUT / 'final-controls'
OUT.mkdir()
sys.path.insert(0, str(SCRIPTS))
import compare_at_latency_profiles as comparator

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def copy_profile(name):
    path = OUT / name
    path.mkdir()
    for source in list(SOURCE_PROFILE.glob('*-p03-*.log')) + list(SOURCE_PROFILE.glob('checkit-*.rom')) + [
            SOURCE_PROFILE / 'compiled-sources.sha256',
            SOURCE_PROFILE / 'sources-verified.log',
            SOURCE_PROFILE / 'performance-macros.txt']:
        shutil.copy2(source, path / source.name)
    return path

baseline = copy_profile('baseline')
results = []

def check_profile(name, mutation, expected_reject=True, mutate_baseline=None):
    candidate = copy_profile(name)
    before = baseline if mutate_baseline is None else copy_profile(name + '-baseline')
    mutation(candidate)
    if mutate_baseline is not None:
        mutate_baseline(before)
    stream = io.StringIO()
    error = None
    try:
        with redirect_stdout(stream):
            report = comparator.compare(before, candidate)
        (candidate / 'accepted-report.json').write_text(json.dumps(report, indent=2) + '\n')
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    (candidate / 'comparator.log').write_text(stream.getvalue() + (error or '') + '\n')
    results.append({'scope': 'full comparator function', 'name': name,
                    'expected_reject': expected_reject, 'rejected': error is not None,
                    'error': error, 'case_directory': str(candidate)})
    print(f'COMPARATOR {name} expected_reject={expected_reject} rejected={error is not None}', flush=True)

def empty_manifests(path):
    for name in ('compiled-sources.sha256', 'sources-verified.log'):
        (path / name).write_text('')

def omit_manifest_row(path):
    for name in ('compiled-sources.sha256', 'sources-verified.log'):
        text = (path / name).read_text().splitlines()
        (path / name).write_text('\n'.join(text[1:]) + '\n')

def false_verification_paths(path):
    target = path / 'sources-verified.log'
    target.write_text('unrelated-file: OK\n' * len(target.read_text().splitlines()))

def change_manifest_hash(path, wanted):
    target = path / 'compiled-sources.sha256'
    lines = target.read_text().splitlines()
    hits = [i for i, line in enumerate(lines) if line.split(maxsplit=1)[1] == wanted]
    assert len(hits) == 1
    lines[hits[0]] = '0' * 64 + '  ' + wanted
    target.write_text('\n'.join(lines) + '\n')

def replace_log(path, regex, replacement):
    target = path / 'dhrystone-p03-1.log'
    text, count = re.subn(regex, replacement, target.read_text(), count=1, flags=re.M)
    assert count == 1
    target.write_text(text)

def missing_signatures(path):
    for target in path.glob('*-p03-*.log'):
        text, count = re.subn(r'^PROFILE_SIGNATURE .*$', 'PROFILE_SIGNATURE ideal_owner=0',
                              target.read_text(), flags=re.M)
        assert count == 1
        target.write_text(text)

check_profile('positive', lambda path: None, expected_reject=False)
check_profile('empty-manifests', empty_manifests)
check_profile('omitted-source-row', omit_manifest_row)
check_profile('wrong-verification-paths', false_verification_paths)
check_profile('changed-cpu-hash', lambda path: change_manifest_hash(path, 'vendor/spk286/rtl/spk286.sv'))
check_profile('changed-config-hash', lambda path: change_manifest_hash(path, 'config.tcl'))
check_profile('changed-firmware-hash', lambda path: change_manifest_hash(path, 'tests/firmware/checkit_dhrystone.asm'))
check_profile('changed-signature', lambda path: replace_log(path, r'^(PROFILE_SIGNATURE gpr=)[0-9a-f]+', r'\g<1>deadbeef'))
check_profile('changed-retired-count', lambda path: replace_log(path, r'^(CHECKIT_DIRECTED_PASS .*?retired=)\d+', r'\g<1>1'))
check_profile('disabled-ram-buffer', lambda path: replace_log(path, r'^RAM_BUFFER_RESULT enabled=1 ', 'RAM_BUFFER_RESULT enabled=0 '))
check_profile('missing-signatures-both', missing_signatures, mutate_baseline=missing_signatures)

# Exercise the exact new source-binding block, without reprocessing unrelated
# timing reports or pretending a new fit exists. This is a bounded parser/guard
# control, not an end-to-end TimeQuest evidence audit.
checker_path = SCRIPTS / 'check_at_timing_closure.py'
checker = checker_path.read_text()
start = checker.index('integration_cycle_binding=None\n')
end = checker.index('compiled_rom=analyze_compiled_image(run)', start)
binding_source = checker[start:end]
(OUT / 'binding-source-exercised.py.txt').write_text(binding_source)
trusted_manifest = ROOT / 'docs/evidence/stack-offset-arithmetic-20261002/compiled-cycle-sources.sha256'
owner_manifest = ROOT / 'build/perf01-owner-experiment/profile/compiled-sources.sha256'
owner_run = ROOT / 'build/perf01-owner-experiment'
valid_lines = owner_manifest.read_text().splitlines()

def check_binding(name, lines, expected_reject=True):
    path = OUT / f'binding-{name}.sha256'
    path.write_text('\n'.join(lines) + '\n')
    namespace = {'Path': Path, 'sha': sha, 're': re, 'cycle_sources': trusted_manifest,
                 'args': SimpleNamespace(integration_cycle_sources=path), 'run': owner_run}
    error = None
    try:
        exec(compile(binding_source, str(checker_path), 'exec'), namespace)
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    record = {'scope': 'exact source-binding block only', 'name': name,
              'expected_reject': expected_reject, 'rejected': error is not None,
              'error': error, 'manifest_sha256': sha(path),
              'validated_source_count': namespace.get('validated_source_count'),
              'integration_cycle_binding': namespace.get('integration_cycle_binding')}
    results.append(record)
    print(f'BINDING {name} expected_reject={expected_reject} rejected={error is not None}', flush=True)

def mutated_lines(wanted):
    result = list(valid_lines)
    hits = [i for i, line in enumerate(result) if line.split(maxsplit=1)[1] == wanted]
    assert len(hits) == 1
    result[hits[0]] = '0' * 64 + '  ' + wanted
    return result

check_binding('positive-owner-only', valid_lines, expected_reject=False)
check_binding('omitted-source', valid_lines[1:])
check_binding('empty', [])
check_binding('changed-cpu', mutated_lines('vendor/spk286/rtl/spk286.sv'))
check_binding('changed-config', mutated_lines('config.tcl'))
check_binding('changed-firmware', mutated_lines('tests/firmware/checkit_dhrystone.asm'))
check_binding('changed-harness', mutated_lines('sim/spk286_integration/spk286_checkit_workload_tb.sv'))
check_binding('duplicate-identical', valid_lines + [valid_lines[0]])
check_binding('duplicate-contradictory', ['0' * 64 + '  ' + valid_lines[0].split(maxsplit=1)[1]] + valid_lines)

receipt = {'comparator_sha256': sha(SCRIPTS / 'compare_at_latency_profiles.py'),
           'read_run_sha256': sha(SCRIPTS / 'report_checkit_profile.py'),
           'checker_sha256': sha(checker_path),
           'binding_source_sha256': sha(OUT / 'binding-source-exercised.py.txt'),
           'note': 'No RTL compilation or new timing fit; originals are read-only.',
           'cases': results,
           'unexpected_acceptances': [r['name'] for r in results if r['expected_reject'] and not r['rejected']]}
(OUT / 'audit-results.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('AUDIT_CONTROLS_COMPLETE unexpected_acceptances=' + ','.join(receipt['unexpected_acceptances']), flush=True)
