"""Archive this milestone's source-bound validation without build objects."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/p06-ready-chain-20261004'
SPECS = {
    'fetch': ('build/fetch-turnaround-20261004-v3', 'FETCH_TURNAROUND_DUAL_PASS'),
    'ideal': ('build/p06-ready-chain-r0-ideal-20261004-v1', 'P06_R0_IDEAL_DUAL_TRACE_PASS'),
    'pcat': ('build/p06-ready-chain-r0-pcat-20261004-v1', 'P06_R0_PCAT_TRACE_PASS'),
    'profiles': ('build/p06-ready-chain-profile-compat-complete-20261004-v2', 'PASS'),
    'machine': ('build/p06-ready-chain-at-profiles-20261004-v1', 'AT_SPEED_PROFILES_DIRECTED_PASS'),
}
sha = lambda data: hashlib.sha256(data).hexdigest()
records, sources, receipts = {}, {}, {}


def put(name, data, origin):
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    packed = name.endswith('.gz')
    payload = gzip.compress(data, compresslevel=9, mtime=0) if packed else data
    if target.exists() and target.read_bytes() != payload:
        raise RuntimeError('Refuse different existing evidence: ' + name)
    target.write_bytes(payload)
    records[name] = dict(source_name=origin, raw_sha256=sha(data),
        archive_sha256=sha(payload), raw_bytes=len(data), archive_bytes=len(payload))


for owner, (directory, expected) in SPECS.items():
    run = ROOT / directory
    receipt = json.loads((run / 'receipt.json').read_text())
    if receipt['status'] != expected:
        raise RuntimeError(f'{owner}: {receipt["status"]}')
    if owner == 'profiles':
        assert receipt['profiles'] == list(range(8)) and len(receipt['units']) == 26
        assert not receipt['failures'] and not receipt['source_changes']
        assert all(row['status'] == 'PASS' for row in receipt['results'])
        assert receipt['counts'] == {'iverilog': 202, 'verilator': 64, 'max_equivalence': 26,
                                    'dual_trace_pairs': 58, 'unpaired_verilator_functional': 6}
        audit = json.loads((run / 'max-audit.json').read_text())
        assert audit['status'] == 'PASS' and audit['max_pairs'] == 26
        assert audit['metadata_negative_checks'] == 130
        assert audit['aggregate_receipt_sha256'] == sha((run / 'receipt.json').read_bytes())
        assert sha((run / 'audit_max.py').read_bytes()) == audit['auditor_sha256']
    if owner == 'machine':
        assert sorted(row['profile'] for row in receipt['results']) == list(range(8))
    receipts[owner] = dict(status=expected, original_path=directory,
                          receipt_sha256=sha((run / 'receipt.json').read_bytes()))
    for name, digest in receipt['source_sha256'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise RuntimeError('Changed validation source: ' + name)
        if name in sources and sources[name] != digest:
            raise RuntimeError('Mixed source sets: ' + name)
        sources[name] = digest
    for path in sorted(run.rglob('*')):
        if not path.is_file() or any(part.startswith('obj') or part == 'verilator-obj'
                                     for part in path.relative_to(run).parts):
            continue
        # Hash sidecars replace the full stream only where the profile runner
        # explicitly declares its bounded digest-storage mode in the receipt.
        if path.suffix not in ('.csv', '.json', '.log', '.hex', '.sv', '.rom', '.txt', '.py'):
            continue
        relative = path.relative_to(run).as_posix()
        destination = f'{owner}/{relative}'
        if path.name not in ('receipt.json', 'analysis.json', 'generation.json', 'fixture.json'):
            destination += '.gz'
        put(destination, path.read_bytes(), directory + '/' + relative)

for owner, original in (
    ('fidelity.log.gz', 'build/p06-ready-chain-fidelity-20261004.log'),
    ('fetch-legacy.log.gz', 'build/p06-ready-chain-fetch-20261004.log'),
    ('lint.log.gz', 'build/p06-ready-chain-lint-20261004.log'),
):
    put(owner, (ROOT / original).read_bytes(), original)

cost_dir = ROOT / 'build/p06-ready-chain-regression-20261004-v1/fetch-cost'
cost = json.loads((cost_dir / 'receipt.json').read_text())
if cost['status'] != 'PASS' or cost['source_sha256_before'] != cost['source_sha256_after']:
    raise RuntimeError('Generic synthesis source guard failed')
for name, digest in cost['artifacts_sha256'].items():
    path = cost_dir / name
    if sha(path.read_bytes()) != digest:
        raise RuntimeError('Changed cost artifact: ' + name)
    put('fetch-cost/' + name + '.gz', path.read_bytes(), str(path.relative_to(ROOT)))
put('fetch-cost/receipt.json', (cost_dir / 'receipt.json').read_bytes(), str(cost_dir.relative_to(ROOT)) + '/receipt.json')

for name, digest in sorted(sources.items()):
    put('inputs/' + name + '.gz', (ROOT / name).read_bytes(), name)
put('archive_ready_chain.py', Path(__file__).read_bytes(), 'build/archive_ready_chain.py')
put('.gitattributes', b'* -text -whitespace\n', 'archive byte preservation policy')

fit = json.loads((ROOT / 'build/p06-ready-chain-allfeatures-20261004-v1/manifest.json').read_text())
fit_inputs = {name.replace('\\', '/'): digest for name, digest in fit['source_sha256'].items()}
fit_sources = {name: digest for name, digest in sources.items() if name in fit_inputs}
for name, digest in fit_sources.items():
    if fit_inputs[name] != digest:
        raise RuntimeError('Fit source differs from directed validation: ' + name)
assert all(name in fit_sources for name in ('vendor/spk286/rtl/spk286_fetch.sv',
    'vendor/spk286/rtl/spk286.sv', 'vendor/spk286/rtl/timed/spk286_profiled.sv',
    'rtl/spk286_integration/spk286_machine_cpu.sv', 'rtl/spk286_integration/spk286_at_bus_bridge.sv'))
binding = dict(status='FIXED50_DIRECTED_VALIDATION_PASS', source_sha256=fit_sources,
    auxiliary_sources_absent_from_fit={name: digest for name, digest in sources.items() if name not in fit_inputs},
    receipts=receipts, scope='Source-bound fetch, original R0 ideal/composed PCAT, '
    'all-profile CPU compatibility and AT diagnostic. Separate standalone regression '
    'receipt is required for accepting the RTL commit; no native-cycle-accuracy, '
    'guest OS or hardware performance claim.')
put('functional-sources.json', (json.dumps(binding, indent=2)+'\n').encode(), 'assembled verified receipts')
manifest = dict(format=1, scope='READY-chain directed correction evidence, '
    'raw traces/logs and source inputs. Profile full streams are represented '
    'by declared raw/canonical hash sidecars where digest storage was selected.',
    files=records)
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', newline='\n')
for name, item in records.items():
    data = (OUT / name).read_bytes()
    if sha(data) != item['archive_sha256'] or sha(gzip.decompress(data) if name.endswith('.gz') else data) != item['raw_sha256']:
        raise RuntimeError('Archive integrity failed: ' + name)
print('READY_CHAIN_DIRECTED_EVIDENCE_PASS', len(records), 'artifacts', len(sources), 'sources')
