"""Bind fresh standalone gates to the shared vendor regression source scope.

This is a read-only evidence combiner. Its status stays preliminary while the
shared gate runs; it cannot convert a partial or failed shared gate into PASS.
"""
from pathlib import Path
import hashlib
import json
import re

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
SNAP = RUN/'snapshot'
V3 = ROOT/'build/p06-ready-chain-regression-20261004-v3'
VENDOR = V3/'snapshot/vendor/spk286'
PLAN = ROOT/'build/spk286-ready-chain-port-plan-20261004'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((RUN/'manifest.json').read_text())
    main = json.loads((RUN/'receipt.json').read_text())
    native = json.loads((RUN/'smoke-state-receipt.json').read_text())
    profile = json.loads((SNAP/'build/profile-focused/receipt.json').read_text())
    audit = json.loads((RUN/'regression-scope-audit.json').read_text())
    v3 = json.loads((V3/'receipt.json').read_text())
    assert main['status']=='STANDALONE_DISTINCT_GATES_PASS'
    assert native['status']=='STANDALONE_NATIVE_SMOKE_STATE_PASS'
    assert len(main['results'])==28 and len(native['results'])==5
    for group in (main,native):
        assert group['sources_unchanged_after_run']
        assert group['manifest_sha256']==sha(RUN/'manifest.json')
        for row in group['results'].values():
            assert row['status']=='PASS' and row['exit_code']==0
            assert sha(RUN/row['log'])==row['log_sha256']
    for name,expected in manifest['source_sha256'].items():
        assert sha(SNAP/name)==expected,name
    contract=json.loads((SNAP/'tools/profile_cpu_baseline.json').read_text())
    selected=json.loads((SNAP/'tools/profile_cpu_ready_chain.json').read_text())
    closure={name:sha(SNAP/name) for name in contract['ordered_rtl_sources']}
    for name,value in closure.items():
        assert value==sha(VENDOR/name),name
    microcode={p.relative_to(SNAP).as_posix():sha(p) for p in sorted((SNAP/'microcode/source').glob('*.mc'))}
    for name,value in microcode.items():
        assert value==sha(VENDOR/name),name
    generated={name:sha(SNAP/'rtl/timed'/name) for name in selected['expected_profiled_sha256']}
    assert generated==selected['expected_profiled_sha256']==profile['generated_sha256']
    for name,value in generated.items():
        assert value==sha(VENDOR/'rtl/timed'/name),name
    assert profile['selected_functional_sha256']==closure
    assert profile['baseline_sha256']==contract['baseline_sha256']
    assert profile['selected_contract_sha256']==sha(SNAP/'tools/profile_cpu_ready_chain.json')
    assert profile['status']=='CPU_ONLY_PROFILE_FOCUSED_PASS_NOT_HOST_ACCEPTANCE'
    assert profile['schedule_oracle_checks_per_simulator']==45
    assert profile['passive_full_top_prefix_cases_per_simulator']==8
    assert profile['independent_metadata_cases_per_simulator']==43878
    fresh=('spk286_fetch','spk286_core','spk286_biu','spk286_biu_hold_lock','spk286_biu_width_io',
           'spk286_execution','spk286_microcode_execution','spk286_adjust_instructions','spk286_event_lifecycle')
    units={row['unit']:row for row in audit['unit_testbenches']}
    common=[name for name,row in units.items() if row['identical'] and name not in fresh]
    assert len(units)==129 and len(common)==120
    assert set(audit['different_unit_testbenches'])=={
        'spk286_core','spk286_execution','spk286_microcode_execution','spk286_event_lifecycle'}
    assert all(row['identical'] for row in audit['runner_modules'])
    assert audit['only_standalone_units']==[] and audit['only_vendor_units']==['spk286_event_arbitration']
    py=(RUN/main['results']['python-modern']['log']).read_text()
    assert re.search(r'Ran 355 tests in .*\n\nOK',py)
    historical=json.loads((PLAN/'functional-closure-bridge.json').read_text())
    assert sha(SNAP/'tools/profile_cpu_baseline.json')==historical['standalone_baseline_contract_sha256']
    assert sha(SNAP/'docs/evidence/profile-cpu-20261004/receipt.json')==historical['historical_profile_receipt_sha256']
    header=json.loads((PLAN/'header-declarations-bridge.json').read_text())
    assert header['selected_header_sha256']==sha(SNAP/'sim/unit/spk286_signals.svh')
    assert header['vendor_header_sha256']==sha(VENDOR/'sim/unit/spk286_signals.svh')
    assert header['names']==136
    # Exact PASS vocabulary belongs to the shared driver; do not infer PASS
    # from a missing field, clean tree, marker from another run or all-budget use.
    drift_fields=('source_changes','snapshot_changes','corpus_changes','cache_changes',
                  'reused_binary_changes','cache_event_binding_errors')
    shared_pass = (v3['status']=='SPK286_READY_CHAIN_REGRESSION_PASS' and v3.get('exit_code')==0 and
                   all(field in v3 and v3[field]==[] for field in drift_fields))
    result={
        'status':'STANDALONE_COMPOSED_GATES_PASS' if shared_pass else 'STANDALONE_FRESH_GATES_PASS_SHARED_VENDOR_PENDING',
        'standalone_full_make_regression_executed':False,
        'standalone_base_head':manifest['standalone_base_head'],
        'fresh':{'main_receipt_sha256':sha(RUN/'receipt.json'),'native_receipt_sha256':sha(RUN/'smoke-state-receipt.json'),
                 'commands':33,'python_tests':355,'dual_unit_names':list(fresh),'extra_core_max_runs':2,
                 'extra_yosys_modules':['spk286_selector','spk286_descriptor','spk286_protected_state','spk286_loadall_service'],
                 'profile_receipt_sha256':sha(SNAP/'build/profile-focused/receipt.json'),
                 'profile_schedule_cases_per_simulator':45,'profile_prefix_cases_per_simulator':8,
                 'profile_metadata_cases_per_simulator':43878,'native_state_initialization_cases':4,
                 'normal_reset_simulators':['iverilog','verilator'],'microcode_audit':'PASS'},
        'shared':{'vendor_receipt_path':(V3/'receipt.json').relative_to(ROOT).as_posix(),
                  'vendor_receipt_sha256_at_compose':sha(V3/'receipt.json'),'vendor_status_at_compose':v3['status'],
                  'required_pass_status':'SPK286_READY_CHAIN_REGRESSION_PASS',
                  'vendor_drift_fields_at_compose':{field:v3.get(field) for field in drift_fields},
                  'common_only_unit_names':common,'common_only_unit_count':120,
                  'identical_unit_testbench_count':125,'different_unit_testbench_names':audit['different_unit_testbenches'],
                  'standalone_registry_count':129,'vendor_registry_count':130,
                  'extra_vendor_unit_not_claimed_as_standalone':['spk286_event_arbitration'],
                  'declared_verilator_exception':'spk286_protected_expand_down full matrix is Icarus only; preserve the exact shared gate scope',
                  'byte_identical_vector_generators':audit['runner_modules'],
                  'header_bridge_sha256':sha(PLAN/'header-declarations-bridge.json'),
                  'header_bridge_scope':'Equal 136 declarations, not byte identity; all variable/net types, widths, names and initializers equal; no executable statement exists in either header'},
        'source_sha256':closure,'literal_microcode_source_sha256':microcode,'selected_profiled_sha256':generated,
        'snapshot_manifest_sha256':sha(RUN/'manifest.json'),
        'regression_scope_audit_sha256':sha(RUN/'regression-scope-audit.json'),
        'selected_contract_sha256':sha(SNAP/'tools/profile_cpu_ready_chain.json'),
        'historical_baseline_contract_sha256':sha(SNAP/'tools/profile_cpu_baseline.json'),
        'historical_profile_receipt_sha256':sha(SNAP/'docs/evidence/profile-cpu-20261004/receipt.json'),
        'composer_sha256':sha(Path(__file__)),
        'unsupported_claims':['No standalone full make regression rerun','No native 286 pin/cycle-accurate timing certification',
                              'No host, board or MiSTer hardware acceptance','No certification of the five different legacy release auditors'],
    }
    (RUN/'composed-receipt.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(result['status'])
    print('composed-receipt SHA256 '+sha(RUN/'composed-receipt.json'))


if __name__=='__main__':main()
