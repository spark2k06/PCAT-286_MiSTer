"""Passive composed acceptance audit; never runs tests or writes a source."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'build/spk286-ready-chain-standalone-gates-20261004-v1'
SNAP = RUN / 'snapshot'
V3 = ROOT / 'build/p06-ready-chain-regression-20261004-v3'
VENDOR = V3 / 'snapshot/vendor/spk286'
PLAN = ROOT / 'build/spk286-ready-chain-port-plan-20261004'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def declarations(path):
    text = re.sub(r'//[^\n]*', '', Path(path).read_text())
    pattern = re.compile(r'\b(logic|wire)\s*(\[[^;\n]+\])?\s+([^;]+);')
    result = {}
    for match in pattern.finditer(text):
        kind, width, names = match.groups()
        for item in names.split(','):
            name, _, initial = item.strip().partition('=')
            name = name.strip()
            assert re.fullmatch(r'[a-zA-Z_]\w*', name) and name not in result
            result[name] = dict(kind=kind, width=re.sub(r'\s+', '', width or ''),
                               initial=re.sub(r'\s+', '', initial))
    assert not pattern.sub('', text).strip(), 'Header contains an unreviewed executable/directive statement'
    return result

broad = read(V3 / 'receipt.json')
review_path = ROOT / 'build/p06-ready-chain-regression-final-review-20261004.json'
broad_review = read(review_path)
assert broad['status'] == 'SPK286_READY_CHAIN_REGRESSION_PASS' and broad['exit_code'] == 0
assert broad_review['status'] == 'BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS'
assert broad_review['regression_receipt_sha256'] == sha(V3 / 'receipt.json')
combined = read(RUN / 'composed-receipt.json')
assert combined['status'] == 'STANDALONE_COMPOSED_GATES_PASS'
assert combined['standalone_full_make_regression_executed'] is False
assert combined['shared']['vendor_status_at_compose'] == broad['status']
assert combined['shared']['vendor_receipt_sha256_at_compose'] == sha(V3 / 'receipt.json')
assert combined['composer_sha256'] == sha(RUN / 'compose_receipt.py')
manifest = read(RUN / 'manifest.json')
assert combined['snapshot_manifest_sha256'] == sha(RUN / 'manifest.json')
for name, digest in manifest['source_sha256'].items():
    assert sha(SNAP / name) == digest, 'Native snapshot source changed: ' + name

fresh = ('spk286_fetch', 'spk286_core', 'spk286_biu', 'spk286_biu_hold_lock',
         'spk286_biu_width_io', 'spk286_execution', 'spk286_microcode_execution',
         'spk286_adjust_instructions', 'spk286_event_lifecycle')
stages = {'lint', 'python-modern', 'microcode-check', 'profile-focused'}
stages |= {'yosys-' + name for name in ('spk286_selector', 'spk286_descriptor',
                                      'spk286_protected_state', 'spk286_loadall_service')}
stages |= {name + '-' + sim for name in fresh for sim in ('iverilog', 'verilator')}
stages |= {'spk286_core-' + sim + '-max-policy' for sim in ('iverilog', 'verilator')}
main = read(RUN / 'receipt.json')
native = read(RUN / 'smoke-state-receipt.json')
assert main['status'] == 'STANDALONE_DISTINCT_GATES_PASS' and set(main['results']) == stages
assert native['status'] == 'STANDALONE_NATIVE_SMOKE_STATE_PASS'
assert set(native['results']) == {'native-verilator-smoke', 'native-state-default',
    'native-state-fixture', 'native-icarus-reset', 'native-microcode-audit'}
for packet, runner in ((main, 'run_gates.py'), (native, 'run_smoke_state.py')):
    assert packet['sources_unchanged_after_run'] and packet['manifest_sha256'] == sha(RUN / 'manifest.json')
    assert packet['source_sha256'] == manifest['source_sha256']
    assert packet['runner_sha256'] == sha(RUN / runner)
    for name, row in packet['results'].items():
        assert row['status'] == 'PASS' and row['exit_code'] == 0, name
        assert sha(RUN / row['log']) == row['log_sha256'], name
assert combined['fresh']['main_receipt_sha256'] == sha(RUN / 'receipt.json')
assert combined['fresh']['native_receipt_sha256'] == sha(RUN / 'smoke-state-receipt.json')
python_log = (RUN / main['results']['python-modern']['log']).read_text(errors='replace')
assert re.search(r'Ran 355 tests in [^\n]+\n\nOK\n', python_log)
assert len(main['results']) + len(native['results']) == combined['fresh']['commands'] == 33

audit_path = RUN / 'regression-scope-audit.json'
audit = read(audit_path)
assert combined['regression_scope_audit_sha256'] == sha(audit_path)
assert audit['only_standalone_units'] == [] and audit['only_vendor_units'] == ['spk286_event_arbitration']
units = {row['unit']: row for row in audit['unit_testbenches']}
assert len(units) == len(audit['unit_testbenches']) == 129
assert sum(row['identical'] for row in units.values()) == 125
assert {name for name, row in units.items() if not row['identical']} == {
    'spk286_core', 'spk286_execution', 'spk286_microcode_execution', 'spk286_event_lifecycle'}
for name, row in units.items():
    assert sha(SNAP / row['testbench']) == row['standalone_sha256'], name
    assert sha(VENDOR / row['testbench']) == row['vendor_v3_sha256'], name
    assert row['identical'] == (row['standalone_sha256'] == row['vendor_v3_sha256'])
    if name not in fresh:
        assert row['identical'], 'Different native bench lacks a fresh execution: ' + name
assert set(combined['shared']['common_only_unit_names']) == set(units) - set(fresh)
assert combined['shared']['common_only_unit_count'] == 120
for row in audit['runner_modules']:
    assert row['identical'] and sha(SNAP / row['path']) == row['standalone_sha256']
    assert sha(VENDOR / row['path']) == row['vendor_v3_sha256'] == row['standalone_sha256']
assert len(audit['runner_modules']) == 24
for row in audit['fixture_inventory']:
    assert sha(SNAP / row['path']) == row['standalone_sha256']
    if row['vendor_v3_sha256'] is not None:
        assert sha(VENDOR / row['path']) == row['vendor_v3_sha256']

header = read(PLAN / 'header-declarations-bridge.json')
assert combined['shared']['header_bridge_sha256'] == sha(PLAN / 'header-declarations-bridge.json')
assert header['selected_header_sha256'] == sha(SNAP / 'sim/unit/spk286_signals.svh')
assert header['vendor_header_sha256'] == sha(VENDOR / 'sim/unit/spk286_signals.svh')
native_decls = declarations(SNAP / 'sim/unit/spk286_signals.svh')
vendor_decls = declarations(VENDOR / 'sim/unit/spk286_signals.svh')
assert native_decls == vendor_decls and len(native_decls) == header['names'] == 136
for name, row in header['declarations'].items():
    normalized = {key: re.sub(r'\s+', '', value or '') for key, value in row.items()}
    assert native_decls[name] == normalized
for name in ('scripts/test.sh', 'scripts/test_verilator.sh', 'scripts/test_iverilog.sh',
             'scripts/rtl_sources.sh', 'tools/run_singlestep.py', 'tools/singlestep.py',
             'tools/state_vectors.py', 'sim/verilator/singlestep.cpp'):
    assert sha(SNAP / name) == sha(VENDOR / name), 'Shared driver differs: ' + name
assert len(combined['source_sha256']) == 40 and len(combined['literal_microcode_source_sha256']) == 20
assert set(name for name in combined['source_sha256'] if name.startswith('microcode/generated/')) == {
    'microcode/generated/spk286_microcode_pkg.sv',
    'microcode/generated/spk286_microcode_rom.sv',
    'microcode/generated/spk286_microcode_sync_rom.sv'}
for mapping in ('source_sha256', 'literal_microcode_source_sha256'):
    for name, digest in combined[mapping].items():
        assert sha(SNAP / name) == sha(VENDOR / name) == digest
for name, digest in combined['selected_profiled_sha256'].items():
    assert sha(SNAP / 'rtl/timed' / name) == sha(VENDOR / 'rtl/timed' / name) == digest
assert len(combined['selected_profiled_sha256']) == 2
for name, field in (('tools/profile_cpu_baseline.json', 'historical_baseline_contract_sha256'),
                    ('tools/profile_cpu_ready_chain.json', 'selected_contract_sha256'),
                    ('docs/evidence/profile-cpu-20261004/receipt.json', 'historical_profile_receipt_sha256')):
    assert sha(SNAP / name) == combined[field]
profile_dir = SNAP / 'build/profile-focused'
profile = read(profile_dir / 'receipt.json')
assert sha(profile_dir / 'receipt.json') == combined['fresh']['profile_receipt_sha256']
assert profile['status'] == 'CPU_ONLY_PROFILE_FOCUSED_PASS_NOT_HOST_ACCEPTANCE'
assert profile['selected_functional_sha256'] == combined['source_sha256']
assert profile['generated_sha256'] == combined['selected_profiled_sha256']
assert profile['schedule_oracle_checks_per_simulator'] == 45
assert profile['passive_full_top_prefix_cases_per_simulator'] == 8
assert profile['independent_metadata_cases_per_simulator'] == 43878
for name, digest in profile['sources_sha256'].items():
    assert sha(SNAP / name) == digest
for name, digest in profile['artifact_sha256'].items():
    assert sha(profile_dir / name) == digest

result = dict(status='STANDALONE_COMPOSED_INDEPENDENT_REVIEW_PASS',
    scope='Qualification by exact common CPU/test/vector/driver identity plus fresh native distinct stages. Does not certify a literal standalone make regression execution, all external corpus cases, five different legacy release auditors, native pin accuracy or board/OS/MiSTer hardware acceptance.',
    reviewer_source_sha256=sha(__file__), composed_receipt_sha256=sha(RUN / 'composed-receipt.json'),
    composer_sha256=sha(RUN / 'compose_receipt.py'), native_snapshot_manifest_sha256=sha(RUN / 'manifest.json'),
    main_receipt_sha256=sha(RUN / 'receipt.json'), native_receipt_sha256=sha(RUN / 'smoke-state-receipt.json'),
    broad_receipt_sha256=sha(V3 / 'receipt.json'), broad_independent_review_sha256=sha(review_path),
    source_snapshot_inputs=len(manifest['source_sha256']), rtl_closure_inputs=40, literal_microcode_inputs=20,
    generated_microcode_modules_within_closure=3,
    profiled_generated_modules=2, identical_testbench_inventory=125, distinct_testbenches_fresh_dual=4,
    composed_unit_coverage=dict(iverilog=129, verilator=128, common_only_credit_units=120,
        fresh_dual_unit_names=list(fresh), extra_core_max_executions=2,
        inherited_skip='Full protected expand-down matrix only in Icarus; preserve exact existing shared policy.'),
    native_fresh_commands=33, native_python_tests=355, identical_vector_generator_modules=24,
    header_declarations_independently_equal=136, schedule_cases_per_simulator=45,
    prefix_cases_per_simulator=8, metadata_cases_per_simulator=43878,
    standalone_full_make_regression_executed=False, new_tests_by_reviewer=False, source_edits_by_reviewer=False,
    findings=[])
output = ROOT / 'build/spk286-ready-chain-composed-independent-review-20261004.json'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(result['status'])
