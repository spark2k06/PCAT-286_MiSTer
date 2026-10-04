import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'docs/evidence/p06-osd-candidate-20261004'
COMPAT = ROOT/'build/p06-profile-compat-final2-20261004'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1048576):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def hashes(directory, mapping):
    for name, expected in mapping.items():
        path = (directory/name).resolve()
        assert path.is_relative_to(directory.resolve()), name
        assert sha(path) == expected, str(path)


def log_marker(path, marker):
    body = path.read_text(encoding='utf-8', errors='replace')
    assert marker in body and 'FATAL' not in body, str(path)
    return sha(path)


def validate_inputs():
    """Read-only acceptance gates; finish every check before creating DEST."""
    sources, gates = {}, {}

    def source_guard(receipt):
        mapping = receipt.get('source_sha256', receipt.get('sources_sha256', {}))
        assert mapping, 'receipt must bind its sources'
        hashes(ROOT, mapping)
        for name, expected in mapping.items():
            assert sources.get(name, expected) == expected, name
            sources[name] = expected

    def generated_guard(receipt, directory, key='generated_sha256'):
        mapping = receipt[key]
        assert set(mapping) == {'spk286_profiled.sv', 'spk286_profiled_events.sv'}
        assert mapping == acceptance['generated_source_sha256']
        hashes(directory, mapping)
        hashes(ROOT/'vendor/spk286/rtl/timed', mapping)

    acceptance = load(COMPAT/'receipt.json')
    assert acceptance['status'] == 'PASS'
    assert not acceptance['failures'] and not acceptance['source_changes']
    assert acceptance['profiles'] == list(range(8)) and len(set(acceptance['units'])) == 26
    assert acceptance['counts'] == dict(iverilog=202, verilator=64,
        max_equivalence=26, dual_trace_pairs=58, unpaired_verilator_functional=6)
    assert acceptance['omitted_icarus'] == [dict(unit='iopl_access', profile=p,
        name=name) for p, name in zip(range(2, 8), ['8', '10', '12.5', '16', '20', '25'])]
    source_guard(acceptance)
    hashes(COMPAT, acceptance['verification_source_sha256'])
    hashes(ROOT/'vendor/spk286/rtl/timed', acceptance['generated_source_sha256'])
    leaves = {item['path']: item['sha256'] for item in acceptance['leaf_receipts']}
    assert len(leaves) == 4
    hashes(ROOT, leaves)
    records = acceptance['results']
    assert len(records) == 292 and all(r['status'] == 'PASS' for r in records)
    for record in records:
        directory = (ROOT/record['artifact_root']).resolve()
        assert directory.is_relative_to(COMPAT.resolve())
        leaf = ROOT/record['leaf_receipt']
        assert leaf.relative_to(ROOT).as_posix() in leaves
        if 'simulator' in record:
            digest = load(directory/record['unit']/
                f"profile-{record['profile']}-{record['simulator']}.digest.json")
            assert digest == record['trace'], (record['unit'], record['profile'])
            assert digest['sha256'] == record['trace_sha256']
            assert digest['canonical_sha256'] == record['canonical_trace_sha256']
            assert record['returncode'] == 0 and record['pass']
    # Require the independent audit and its exact binding to these receipts and
    # original MAX artifacts, not merely the aggregate's equality strings.
    maximum = load(COMPAT/'max-audit.json')
    assert maximum['status'] == 'PASS'
    assert maximum['max_pairs'] == 26 and maximum['metadata_negative_checks'] == 130
    assert maximum['aggregate_receipt_sha256'] == sha(COMPAT/'receipt.json')
    assert maximum['auditor_sha256'] == sha(COMPAT/'audit_max.py')
    assert len(maximum['results']) == 26
    spec = importlib.util.spec_from_file_location('p06_max_audit_gate', COMPAT/'audit_max.py')
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    audited = {item['unit']: item for item in maximum['results']}
    max_records = [r for r in records if r.get('kind') == 'MAX per-edge equivalence']
    assert set(audited) == {r['unit'] for r in max_records} == set(acceptance['units'])
    for record in max_records:
        unit = record['unit']
        directory = ROOT/record['artifact_root']/unit
        observed = audited[unit]
        assert observed['leaf_receipt_sha256'] == sha(ROOT/record['leaf_receipt'])
        for field, filename in [('original_log_sha256', 'original-run.log'),
                ('original_meta_sha256', 'original-max.digest.json'),
                ('profiled_meta_sha256', 'profile-0-iverilog.digest.json')]:
            assert observed[field] == sha(directory/filename), (unit, field)
        original = load(directory/'original-max.digest.json')
        profiled = load(directory/'profile-0-iverilog.digest.json')
        trusted = [r for r in records if r.get('unit') == unit and
            r.get('simulator') == 'iverilog' and r.get('profile') == 0]
        assert len(trusted) == 1
        auditor.pair(original, profiled, trusted[0]['trace'], record)
        assert observed['raw_sha256'] == original['sha256']
        assert observed['bytes'] == original['bytes'] and observed['rows'] == original['rows']
        log_marker(directory/'original-run.log', 'PASS')
    gates['compatibility'] = dict(receipt_sha256=sha(COMPAT/'receipt.json'),
        max_audit_sha256=sha(COMPAT/'max-audit.json'), counts=acceptance['counts'])

    directory = ROOT/'build/p06-instruction-metadata-final1-20261004'
    receipt = load(directory/'receipt.json')
    assert receipt['status'] == 'PASS' and receipt['coverage']['cases'] == 43878
    source_guard(receipt)
    hashes(directory, receipt['artifacts_sha256'])
    assert receipt['artifacts_sha256']['iverilog-trace.csv'] == receipt['artifacts_sha256']['verilator-trace.csv']
    for simulator in ('iverilog', 'verilator'):
        log_marker(directory/f'{simulator}-run.log', 'SPK286_INSTRUCTION_TIMING_PASS cases=43878')
    assert set(receipt['negative']) == {'immediate', 'out', 'odd-double-charge',
        'stale-modrm', 'count-truncate', 'silent-default', 'include-guard'}
    for name, negative in receipt['negative'].items():
        assert negative['returncode'] != 0
        log = directory/f'negative-{name}'/('build.log' if name == 'include-guard' else 'run.log')
        assert negative['marker'] in log.read_text(encoding='utf-8', errors='replace')
    gates['metadata'] = dict(receipt_sha256=sha(directory/'receipt.json'), cases=43878, negatives=7)

    directory = ROOT/'build/p06-profile-components7-20261004'
    receipt = load(directory/'components.json')
    assert receipt['status'] == 'PROFILE_COMPONENT_PREPARATION_PASS_NOT_FULL_ACCEPTANCE'
    source_guard(receipt)
    generated_guard(receipt, directory/'candidate')
    generation = load(directory/'candidate/generation.json')
    source_guard(generation)
    generated_guard(generation, directory/'candidate')
    logs = {}
    for simulator in ('iverilog', 'verilator'):
        for kind, marker in [('schedule', 'PROFILE_SCHEDULE_PASS checks45'),
                ('prefix', 'PROFILE_PREFIX_PASS cases8 checks553')]:
            filename = f'{kind}-{simulator}-run.log'
            logs[filename] = log_marker(directory/filename, marker)
    assert not (directory/'lint-profiled.log').read_text(encoding='utf-8', errors='replace').strip()
    gates['components'] = dict(receipt_sha256=sha(directory/'components.json'), log_sha256=logs)

    directory = ROOT/'build/p06-profile-upstream-audit-20261004'
    receipt = load(directory/'receipt.json')
    assert receipt['status'] == 'PROFILE_GENERATION_AND_ACTIVE_MICROCODE_PASS_WITH_UPSTREAM_UNIT_FAILURE'
    source_guard(receipt)
    hashes(directory/'rebuilt', receipt['selected_sha256'])
    assert {name: digest for name, digest in receipt['selected_sha256'].items()
        if name != 'generation.json'} == acceptance['generated_source_sha256']
    assert set(receipt['checks']) == {'microcode_coupling_roundtrip',
        'focused_upstream_units', 'focused_adapters_and_microcode'}
    for name, check in receipt['checks'].items():
        path = ROOT/check['log']
        assert sha(path) == check['sha256']
        expected_rc = 1 if name == 'focused_adapters_and_microcode' else 0
        assert check['returncode'] == expected_rc
    log_marker(directory/'microcode_coupling_roundtrip.log', 'MICROCODE AUDIT PASS')
    log_marker(directory/'focused_upstream_units.log', 'OK')
    failure = receipt['upstream_unit_failure']
    assert failure['test'] == 'test_microcode_system_access.SystemAccessMicrocodeTests.test_frozen_h01_rom_adds_only_the_eight_documented_checks'
    body = (directory/'focused_adapters_and_microcode.log').read_text(encoding='utf-8')
    assert 'First differing element 725:' in body and 'FAILED (failures=1)' in body
    assert 'Ran 38 tests' in body and 'test_frozen_h01_rom_adds_only_the_eight_documented_checks' in body
    microcode = load(directory/'microcode/audit.json')
    assert microcode['validation'] == microcode['roundtrip'] == 'PASS'
    # audit_microcode records hashes of the selected active ROM artifacts;
    # its output directory contains the report and canonical.mc, not ROM copies.
    hashes(ROOT/'vendor/spk286/microcode/generated', microcode['artifact_sha256'])
    hashes(ROOT/'vendor/spk286/microcode/source', microcode['source_sha256'])
    gates['active-microcode-audit'] = dict(receipt_sha256=sha(directory/'receipt.json'),
        status=receipt['status'], upstream_unit_failure=failure)

    directory = ROOT/'build/p06-profile-pause-probe-20261004'
    receipt = load(directory/'receipt.json')
    assert receipt['status'] == 'CPU_COMPLETED_INTERVAL_NOTIFICATION_DURING_VERIFIER_PAUSE_PASS'
    source_guard(receipt)
    generated_guard(receipt, directory/'candidate')
    hashes(directory, receipt['artifact_sha256'])
    log_marker(directory/'run.log', 'PROFILE_PAUSE_PENDING_PASS retire1 pause_boundaries7 checks195')
    gates['pause-after-raw'] = dict(receipt_sha256=sha(directory/'receipt.json'), scope=receipt['scope'])

    directory = ROOT/'build/p06-profile-compat-stream-final-20261004'
    receipt = load(directory/'stream-receipt.json')
    assert receipt['status'] == 'PASS'
    source_guard(receipt)
    assert receipt['verification_helper_sha256'] == sha(directory/'verify_stream.py')
    assert receipt['raw_receipt_sha256'] == sha(directory/'raw/receipt.json')
    generated_guard(receipt, directory/'raw/generated', key='generated_source_sha256')
    raw_receipt = load(directory/'raw/receipt.json')
    assert raw_receipt['status'] == 'PASS' and not raw_receipt['failures'] and not raw_receipt['source_changes']
    assert raw_receipt['units'] == ['event_lifecycle'] and raw_receipt['profiles'] == [0, 1]
    source_guard(raw_receipt)
    generated_guard(raw_receipt, directory/'raw/generated', key='generated_source_sha256')
    assert [r['profile'] for r in receipt['results']] == [0, 1]
    for item in receipt['results']:
        assert item['raw_and_canonical_identical_to_csv'] is True
        stem = f"profile-{item['profile']}-iverilog"
        raw_csv = directory/'raw/event_lifecycle'/f'{stem}.csv'
        digest = load(directory/'stream'/f'{stem}.digest.json')
        assert digest == item['trace'] and sha(raw_csv) == digest['sha256']
        log_marker(directory/'stream'/f"profile-{item['profile']}.log", 'EVENT_LIFECYCLE PASS')
    gates['stream-validation'] = dict(receipt_sha256=sha(directory/'stream-receipt.json'),
        raw_receipt_sha256=sha(directory/'raw/receipt.json'), verifier_sha256=sha(directory/'verify_stream.py'),
        scope='Full raw CSV bound to stream digest; recorded synthetic chunk validation. No new CPU timing claim.')

    machine = ROOT/'build/p06-osd-machine-all-final3-20261004/receipt.json'
    receipt = load(machine)
    assert receipt['status'] == 'AT_SPEED_PROFILES_DIRECTED_PASS'
    source_guard(receipt)
    assert [r['profile'] for r in receipt['results']] == list(range(8))
    for item in receipt['results']:
        path = machine.parent/f"profile-{item['profile']}.log"
        assert log_marker(path, item['marker']) == item['log_sha256']
    gates['machine'] = dict(receipt_sha256=sha(machine), profiles=8)

    directory = ROOT/'build/p06-osd-bridge-window-final1-20261004'
    bindings = {}
    for line in (directory/'sources.sha256').read_text(encoding='utf-8').splitlines():
        digest, name = line.split(None, 1)
        assert len(digest) == 64 and name not in bindings
        bindings[name] = digest
    assert set(bindings) == {'rtl/spk286_integration/spk286_at_cpu_profile.sv',
        'rtl/spk286_integration/spk286_at_bus_bridge.sv',
        'sim/spk286_integration/spk286_at_profile_bridge_tb.sv', 'scripts/test_at_profile_bridge.sh'}
    source_guard(dict(source_sha256=bindings))
    marker = 'AT_PROFILE_BRIDGE_PASS cases=1576 checks=9024 commands=2087 captures=2087 publications=1576 misses=4909'
    logs = {f'{s}-run.log': log_marker(directory/f'{s}-run.log', marker)
        for s in ('iverilog', 'verilator')}
    assert not (directory/'lint.log').read_text(encoding='utf-8', errors='replace').strip()
    for name in bindings:
        assert f'{name}: OK' in (directory/'sources-verified.log').read_text(encoding='utf-8')
    gates['bridge'] = dict(sources_manifest_sha256=sha(directory/'sources.sha256'), log_sha256=logs)

    directory = ROOT/'build/p06-osd-bridge-window-max-proof-20261004'
    receipt = load(directory/'receipt.json')
    assert receipt['status'] == 'AT_PROFILE_BRIDGE_MAX_EQUIVALENCE_PASS'
    assert receipt['candidate_sha256'] == sha(ROOT/'rtl/spk286_integration/spk286_at_bus_bridge.sv')
    assert receipt['script_sha256'] == sha(ROOT/'scripts/prove_at_profile_bridge.py')
    assert receipt['modes'] == [dict(complete_on_cpu_sample=m, proof='PASS', negative_control='rejected') for m in (0, 1)]
    logs = {}
    for mode in (0, 1):
        folder = directory/f'sample-{mode}'
        logs[f'sample-{mode}/proof.log'] = log_marker(folder/'proof.log', 'Equivalence successfully proven!')
        negative = (folder/'negative-control.log').read_text(encoding='utf-8', errors='replace')
        assert 'ERROR: Found' in negative and "unproven $equiv cells in 'equiv_status -assert'" in negative
        logs[f'sample-{mode}/negative-control.log'] = sha(folder/'negative-control.log')
        for filename in ('gold.sv', 'gate.sv', 'mutant.sv', 'elaborated.il', 'elaborated.json'):
            assert (folder/filename).stat().st_size > 0
    gates['bridge-max-proof'] = dict(receipt_sha256=sha(directory/'receipt.json'),
        reference_sha256=receipt['reference_sha256'], log_sha256=logs, scope=receipt['scope'])
    return acceptance, machine, sources, gates


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.stat().st_size > 300000 and source.suffix in ('.csv', '.rpt', '.json', '.il', '.txt'):
        target = target.with_name(target.name+'.gz')
        with source.open('rb') as inp, target.open('wb') as stream:
            with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as out:
                shutil.copyfileobj(inp, out)
        return dict(path=target.relative_to(DEST).as_posix(), sha256=sha(target),
                    raw_sha256=sha(source), encoding='gzip', raw_bytes=source.stat().st_size)
    shutil.copy2(source, target)
    return dict(path=target.relative_to(DEST).as_posix(), sha256=sha(target))


def main():
    acceptance, machine, guarded_sources, gates = validate_inputs()
    DEST.mkdir(parents=True, exist_ok=False)
    runs = {
        'metadata': ROOT/'build/p06-instruction-metadata-final1-20261004',
        'components': ROOT/'build/p06-profile-components7-20261004',
        'active-microcode-audit': ROOT/'build/p06-profile-upstream-audit-20261004',
        'pause-after-raw': ROOT/'build/p06-profile-pause-probe-20261004',
        'stream-validation': ROOT/'build/p06-profile-compat-stream-final-20261004',
        'compatibility': COMPAT,
        'machine': machine.parent,
        'bridge': ROOT/'build/p06-osd-bridge-window-final1-20261004',
        'bridge-max-proof': ROOT/'build/p06-osd-bridge-window-max-proof-20261004',
    }
    artifacts = []
    for label, directory in runs.items():
        assert directory.is_dir(), str(directory)
        for source in sorted(directory.rglob('*')):
            rel = source.relative_to(directory)
            if not source.is_file() or any(p in ('obj', 'schedule-verilator', 'prefix-verilator',
                    'verilator-obj', 'verilator', 'obj_dir') for p in rel.parts):
                continue
            # Preserve every asserted result, digest, bounded stream sample,
            # build-only fixture, independent auditor and proof input. Compiled
            # simulator objects are regenerated from the recorded sources.
            if source.suffix not in ('.log', '.json', '.sv', '.csv', '.py', '.ys', '.il', '.txt', '.sha256'):
                continue
            artifacts.append(copy(source, DEST/'validation'/label/rel))
    names = sorted(guarded_sources)
    # The repository and immutable fit snapshot retain the complete dependency
    # closure. Freeze the new/changed CPU integration here for direct inspection.
    extra = ['.gitattributes', 'scripts/record_p06_osd_fit.py',
             'scripts/check_p06_profile_components.py', 'scripts/test_spk286_instruction_timing.py',
             'scripts/prove_at_profile_bridge.py', 'scripts/test_at_profile_bridge.sh',
             'sim/spk286_integration/spk286_at_profile_bridge_tb.sv',
             'sim/spk286_integration/spk286_at_config_tb.sv',
             'sim/spk286_integration/spk286_instruction_timing_tb.sv',
             'sim/spk286_timing/spk286_instruction_schedule_tb.sv',
             'sim/spk286_timing/spk286_profile_prefix_tb.sv',
             'vendor/spk286/rtl/timed/spk286_profiled.sv',
             'vendor/spk286/rtl/timed/spk286_profiled_events.sv',
             'vendor/spk286/rtl/timed/generation.json']
    source_hashes = {name: sha(ROOT/name) for name in sorted(set(names+extra))}
    inspected = [name for name in source_hashes if name.startswith((
        'rtl/spk286_timing/', 'vendor/spk286/rtl/timed/', 'sim/spk286_timing/'))]
    inspected += ['PCAT-286.sv', 'config.tcl', 'rtl/spk286_integration/spk286_at_machine.sv',
        'rtl/spk286_integration/spk286_machine_cpu.sv', 'rtl/spk286_integration/spk286_at_cpu_profile.sv',
        'rtl/spk286_integration/spk286_at_bus_bridge.sv', 'rtl/spk286_integration/spk286_integration.qip',
        'scripts/build_p06_profile_cpu.py', 'scripts/test_at_speed_profiles.py',
        'scripts/test_p06_profile_compatibility.py', 'scripts/record_p06_osd_fit.py']
    for name in sorted(set(inspected)):
        artifacts.append(copy(ROOT/name, DEST/'source'/name))
    artifacts.append(copy(Path(__file__), DEST/'freeze_validation.py'))
    result = dict(status='DIRECTED_OSD_SPEED_SELECTOR_VALIDATION_PASS',
        compatibility_receipt_sha256=sha(COMPAT/'receipt.json'),
        machine_receipt_sha256=sha(machine), source_sha256=source_hashes,
        validation_gates=gates, artifacts=artifacts,
        scope='Source-bound directed functional/component validation. Historical intervals provisional; fit, physical calibration, hardware and complete OS regression separate.')
    (DEST/'validation-manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], 'artifacts', len(artifacts))


if __name__ == '__main__':
    main()
