"""Passive review binding for the staged standalone sentinel migration."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'build/spk286-ready-chain-port-probes-20261004-v1'
PLAN = ROOT / 'build/spk286-ready-chain-port-plan-20261004'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

manifest_path = PROBE / 'evidence-manifest.json'
assert sha(manifest_path) == 'ca92a008855c6a0c25e3555e999e9d57d623e7a86883fab51e85313708d2a809'
manifest = json.loads(manifest_path.read_bytes())
names = set()
for artifact in manifest['artifacts']:
    name = artifact['path']
    assert name not in names
    names.add(name)
    path = ROOT / name
    assert path.resolve().is_relative_to((ROOT / 'build').resolve())
    assert sha(path) == artifact['sha256'] and path.stat().st_size == artifact['bytes']
summary = json.loads((PROBE / 'focused-summary.json').read_bytes())
assert summary['status'] == 'STANDALONE_EXECUTION_ADAPTERS_FRESH_DUAL_PASS'
assert summary['sources_unchanged_after_run'] and summary['matching_recorded_sentinel_traces']
assert sha(PROBE / 'manifest.json') == summary['snapshot_manifest_sha256']
assert sha(PROBE / 'receipt.json') == summary['receipt_sha256']
assert sha(PLAN / 'stage-manifest.json') == summary['stage_manifest_sha256']
receipt = json.loads((PROBE / 'receipt.json').read_bytes())
results = receipt['results']
assert set(results) == {unit + '/' + sim for unit in ('spk286_execution', 'spk286_microcode_execution')
                      for sim in ('iverilog', 'verilator')}
sentinels = []
for simulator in ('iverilog', 'verilator'):
    for unit in ('spk286_execution', 'spk286_microcode_execution'):
        result = results[unit + '/' + simulator]
        assert result['status'] == 'PASS' and result['exit_code'] == 0
        log_path = PROBE / result['log']
        assert sha(log_path) == result['log_sha256']
        log = log_path.read_text(errors='replace')
        if unit == 'spk286_execution':
            assert log.count('EXECUTION_SENTINEL_PASS origin=0200 cycles=9') == 1
        else:
            records = re.findall(r'MICROCODE_EXECUTION_SENTINEL_CASE origin=([0-9a-f]+) cycles=(\d+) retires=(\d+)', log)
            assert records == [('0103', '2', '1')] * 24 + [('0104', '3', '1')] * 24
            assert log.count('MICROCODE_EXECUTION_SENTINEL_PASS cases=48') == 1
            assert log.count('MICROCODE_EXECUTION PASS: 48 MOV vectors, 8-MOV stream, 3 cancellation/reset/resume boundaries; 5512 checks; 382 underfill cycles') == 1
            sentinels.append(records)
assert sentinels[0] == sentinels[1]
result = dict(status='STANDALONE_SENTINEL_ADAPTER_INDEPENDENT_REVIEW_PASS',
    scope='Read-only patch and focused receipt/log integrity review. No new simulation, source mutation or standalone commit by reviewer; not full standalone regression or architectural release.',
    reviewer_source_sha256=sha(__file__), evidence_manifest_sha256=sha(manifest_path),
    reviewed_patch_sha256=sha(PLAN / 'required-adapters.patch'),
    reviewed_portable_contract_patch_sha256=sha(PLAN / 'portable-profile-contract.patch'),
    focused_receipt_sha256=sha(PROBE / 'receipt.json'), bound_artifacts=len(names),
    microcode=dict(original_mov_vectors=48, actual_ud_acceptances_per_simulator=48,
        fault_origins={'0103': 24, '0104': 24}, cycles=[2, 3], retirements=1,
        mov_stream=8, cancellation_reset_resume_boundaries=3, checks_per_simulator=5512,
        underfill_cycles_per_simulator=382, identical_recorded_sentinel_traces=True),
    execution=dict(retained_fault_ip='0200', actual_ud_acceptance_cycles_per_simulator=9,
        complete_128bit_gpr_signature_preserved=True),
    static_contract=['First post-edge event_active plus event_cancel precedes entry dispatch and stack writes.',
        'Event vector6/kindFAULT1 and retained event CS/IP/FLAGS are asserted; no live-IP substitution.',
        'Original exact MOV architecture and pause checks precede resumed sentinel execution.',
        'No second retirement/MOV, unsupported latch, event completion or stack write is accepted.',
        'Portable selected milestone explicitly pins new functional CPU while preserving historical baseline contract.'],
    findings=[], production_or_frozen_pcat_changed=False)
output = ROOT / 'build/spk286-ready-chain-sentinel-independent-review-20261004.json'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(result['status'])
