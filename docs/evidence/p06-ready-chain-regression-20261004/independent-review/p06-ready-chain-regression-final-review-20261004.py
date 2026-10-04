"""Passive independent final audit of broad v3; does not run any RTL test.

Run under the same WSL environment as the compile-only cache to recheck its
external tool metadata. A pending/failed regression never produces a receipt.
"""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'build/p06-ready-chain-regression-20261004-v3'
OUTPUT = ROOT / 'build/p06-ready-chain-regression-final-review-20261004.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


receipt = json.loads((RUN / 'receipt.json').read_bytes())
assert receipt['status'] == 'SPK286_READY_CHAIN_REGRESSION_PASS', 'Broad regression not accepted yet'
assert receipt['exit_code'] == 0 and receipt['command'] == ['make', 'regression']
prelaunch_path = ROOT / 'build/p06-ready-chain-regression-cache-review-20261004.json'
assert sha(prelaunch_path) == '8a564e3fb334b646f066df9b4ea5bdae5e28336a9ff92f7cbe39e0a111cf1b80'
prelaunch = json.loads(prelaunch_path.read_bytes())
assert prelaunch['status'] == 'COMPILE_CACHE_INDEPENDENT_REVIEW_PASS_REGRESSION_PENDING'
for name, digest in prelaunch['source_sha256'].items():
    assert sha(ROOT / name) == digest, 'Reviewed prelaunch input changed: ' + name
for name in ('source_changes', 'snapshot_changes', 'corpus_changes', 'historical_fixture_changes',
             'cache_changes', 'reused_binary_changes', 'cache_event_binding_errors'):
    assert not receipt[name], 'Nonempty regression drift/error field: ' + name
for prefix in ('source', 'snapshot', 'corpus', 'cache'):
    assert receipt[prefix + '_sha256_before'] == receipt[prefix + '_sha256_after']
assert receipt['source_sha256_before'] == receipt['snapshot_sha256_before']
assert len(receipt['source_sha256_before']) == 581
assert len(receipt['corpus_sha256_before']) == 98
cpu = Path(receipt['snapshot_cwd'])
corpus = Path(receipt['external_corpus'])
for name, digest in receipt['source_sha256_after'].items():
    assert sha(ROOT / name) == digest, 'Current source changed: ' + name
    assert sha(RUN / 'snapshot' / name) == digest, 'Snapshot input changed: ' + name
for name, digest in receipt['corpus_sha256_after'].items():
    assert sha(corpus / name) == digest, 'External corpus changed: ' + name
for name, digest in receipt['cache_sha256_after'].items():
    assert sha(RUN / name) == digest, 'Cache helper/proof changed: ' + name
assert sha(RUN / 'run_regression.py') == receipt['runner_sha256']
assert sha(RUN / 'regression.log') == receipt['log_sha256']
log = (RUN / 'regression.log').read_text(errors='replace')
lines = log.splitlines()
assert lines.count('REGRESSION PASS') == 1 and lines.count('TEST PASS') == 1
for marker in ('LINT PASS', 'VERILATOR BUILD PASS', 'RESET_SMOKE PASS', 'STATE_VECTOR PASS', 'SYNTH_CHECK PASS'):
    assert marker in log, 'Missing real stage marker: ' + marker
assert sum(line.startswith('RESET_SMOKE PASS ') for line in lines) >= 2
assert sum(line.startswith('STATE_VECTOR PASS: ') for line in lines) >= 2
assert 'sim/iverilog/spk286_reset_tb.sv:' in log and '$finish called' in log
assert 'MICROCODE CHECK PASS: 123 entries, 743 words, 10-bit addresses, 8-bit control' in lines
assert 'MICROCODE AUDIT PASS: phase entries, emitted ROM, source coupling and round-trip' in lines
python_groups = []
for index, line in enumerate(lines):
    match = re.fullmatch(r'Ran (\d+) tests in (.+)', line)
    if match:
        following = [value for value in lines[index + 1:] if value.strip()]
        assert following and following[0] == 'OK', 'Python unittest group did not complete OK'
        python_groups.append(dict(tests=int(match.group(1)), summary=line, status='OK'))
assert len(python_groups) == 2 and [group['tests'] for group in python_groups] == [114, 297]

script = (cpu / 'scripts/test_units.sh').read_text()
units = []
for part in re.findall(r'tests(?:\+)?=\((.*?)\)', script, re.S):
    units.extend(re.findall(r'\bspk286_[a-z0-9_]+\b', part))
assert len(units) == len(set(units)) == 130
vl = re.findall(r'sim/unit/(spk286_[a-z0-9_]+_tb)\.sv:\d+: Verilog \$finish', log)
ic = re.findall(r'sim/unit/(spk286_[a-z0-9_]+_tb)\.sv:\d+: \$finish called', log)
expected_ic = {name + '_tb' for name in units}
expected_vl = expected_ic - {'spk286_protected_expand_down_tb'}
assert len(ic) == len(set(ic)) == 130 and set(ic) == expected_ic
assert len(vl) == len(set(vl)) == 129 and set(vl) == expected_vl
expected_skip = 'VERILATOR SKIP: spk286_protected_expand_down full matrix runs in Icarus; protected-system and event banks provide Verilator cross-checks'
assert receipt['skips'] == [expected_skip]
assert 'SINGLESTEP SMOKE SKIP' not in log and 'SINGLESTEP OPERAND SMOKE SKIP' not in log
assert 'SINGLESTEP ALU SMOKE SKIP' not in log and 'SINGLESTEP STACK/CONTROL SMOKE SKIP' not in log
summaries = [line for line in lines if line.startswith('SINGLESTEP SUMMARY ')]
assert len(summaries) == 4
sst = []
for line in summaries:
    counts = {name: int(re.search(r'\b' + name + r'=(\d+)', line).group(1))
              for name in ('executed', 'passed', 'failed', 'selected', 'prefix_skipped', 'exception_skipped')}
    assert counts['failed'] == 0 and counts['passed'] == counts['executed'] == counts['selected']
    assert counts['executed'] > 0
    sst.append(dict(summary=line, **counts))

sys.path.insert(0, str(RUN))
cache = importlib.import_module('compile_cache')
manifest = json.loads((RUN / 'cache-manifest.json').read_bytes())
controls = json.loads((RUN / 'cache-controls.json').read_bytes())
assert len(manifest['units']) == 70 and receipt['eligible_prior_compile_count'] == 70
assert controls['status'] == 'COMPILE_CACHE_CONTROLS_PASS'
assert controls['wrapper_sha256'] == sha(RUN / 'compile_cache.py')
assert controls['manifest_sha256'] == sha(RUN / 'cache-manifest.json')
assert controls['control_script_sha256'] == sha(RUN / 'cache_controls.py')
assert manifest['prepare_script_sha256'] == sha(RUN / 'prepare_cache.py')
assert len(controls['controls']) == 17
assert sum(c['observed'] == 'accept' for c in controls['controls']) == 1
assert sum(c['observed'] == 'reject' for c in controls['controls']) == 16
assert all(c['observed'] == c['expected'] for c in controls['controls'])
hit_units, misses = [], []
for record in receipt['cache_events']:
    event_path = Path(record['event_file'])
    assert event_path.resolve().is_relative_to((RUN / 'cache-events').resolve())
    assert sha(event_path) == record['event_file_sha256']
    event = json.loads(event_path.read_bytes())
    assert {k: v for k, v in record.items() if k not in ('event_file', 'event_file_sha256')} == event
    assert event['wrapper_sha256'] == sha(RUN / 'compile_cache.py')
    assert event['manifest_sha256'] == sha(RUN / 'cache-manifest.json')
    assert receipt['started_unix'] <= event['timestamp_unix'] <= receipt['finished_unix']
    if event['status'] == 'CACHE_MISS':
        misses.append(dict(reason=event['reason'], arguments=event['arguments']))
        continue
    assert event['status'] == 'CACHE_HIT'
    unit = event['unit']
    assert unit not in manifest['never_reuse'] and unit in expected_vl
    # Pure guard revalidation; reads source/tool/provenance only. No compile or simulation.
    proof = cache.validate(event['actual_arguments'], manifest, cpu)
    for key, value in proof.items():
        assert event[key] == value, 'Cache proof field changed: ' + key
    binary = Path(event['output_directory']) / unit
    historical_log = binary.parent / 'historical-build.log'
    assert sha(binary) == event['binary_sha256'] == event['copied_binary_sha256']
    assert sha(historical_log) == event['historical_compile_log_sha256']
    assert 'COMPILE_CACHE_HIT: ' + unit in (binary.parent / 'build.log').read_text()
    hit_units.append(unit)
assert len(hit_units) == len(set(hit_units)) == receipt['cache_hit_count']
assert len(misses) == receipt['cache_miss_count']
assert 'spk286_adjust_instructions_tb' not in hit_units
for name, digest in receipt['regenerated_vector_sha256'].items():
    assert sha(RUN / name) == digest
assert 'work/adjust-instruction-vectors.txt' in receipt['regenerated_vector_sha256']
adjust_markers = [line for line in lines if line.startswith('ADJUST_INSTRUCTIONS PASS:')]
assert adjust_markers == ['ADJUST_INSTRUCTIONS PASS: 8184 directed CPU cases; 1764540 checks; 16352 immediate stalls'] * 2

result = dict(status='BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS',
    scope='Passive independent receipt/log/source/corpus/cache proof audit. Original make regression executed all130 directed Icarus and129 directed Verilator units, with the explicit full-Icarus expand-down policy. All simulations/vectors/lint/smoke/state/SingleStep/synthesis ran anew; only validated identical unit compilations were reused. Not full fresh Verilator compilation, all external hardware cases, PCAT/OS tests, STA, cycle accuracy or MiSTer acceptance.',
    auditor_sha256=sha(__file__), regression_receipt_sha256=sha(RUN / 'receipt.json'),
    prelaunch_review_sha256=sha(prelaunch_path), prelaunch_sources_still_exact=True,
    actual_make_exit_code=0, source_inputs=581, corpus_inputs=98,
    current_and_snapshot_sources_exact=True, source_snapshot_corpus_cache_before_after_equal=True,
    unit_executions=dict(iverilog=130, verilator=129, simulator_policy_skips=[expected_skip]),
    python_unittest_groups=python_groups,
    python_count_scope='The114compiler/microcode tests are repeated within the297-test complete Python suite; these group execution counts must not be summed as unique tests.',
    generated_microcode_check_and_roundtrip_audit_pass=True,
    singlestep_smoke=sst, regenerated_vector_files=len(receipt['regenerated_vector_sha256']),
    cache=dict(eligible_units=70, hits=len(hit_units), misses=len(misses), hit_units=hit_units,
        independent_pure_guard_revalidation=True, positive_controls=1, rejection_controls=16,
        simulation_result_reuse=False, event_manifest_and_wrapper_identity_pass=True),
    synthesis_scope='Yosys full CPU frontend/proc/check plus mapped synth and component sanity, as original synth_check.sh.',
    log_sha256=receipt['log_sha256'], elapsed_seconds=receipt['elapsed_seconds'],
    tracked_edits_by_reviewer=False, new_simulations_by_reviewer=False, commit=False)
OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print('BROAD_REGRESSION_INDEPENDENT_AUDIT_PASS sources581 corpus98 Icarus130 Verilator129')
