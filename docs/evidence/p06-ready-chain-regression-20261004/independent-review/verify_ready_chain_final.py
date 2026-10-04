import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/p06-ready-chain-final-integrity.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_archive(directory, manifest_name, field, kind):
    base = ROOT / directory
    receipt = json.loads((base / manifest_name).read_text())
    entries = receipt[field]
    for name, meta in entries.items():
        raw = (base / name).read_bytes()
        if kind == 'directed':
            assert digest(raw) == meta['archive_sha256'], name
            assert len(raw) == meta['archive_bytes'], name
            original = gzip.decompress(raw) if name.endswith('.gz') else raw
            assert digest(original) == meta['raw_sha256'], name
            assert len(original) == meta['raw_bytes'], name
        elif kind == 'fit':
            assert digest(raw) == meta['sha256'], name
            assert len(raw) == meta['bytes'], name
            if 'raw_sha256' in meta:
                original = gzip.decompress(raw) if meta['compression'] == 'gzip' else raw
                assert digest(original) == meta['raw_sha256'], name
                assert len(original) == meta['raw_bytes'], name
        else:
            assert digest(raw) == meta, name
    return {'artifacts_checked': len(entries), 'manifest_sha256': digest((base / manifest_name).read_bytes())}


results = {}
results['directed'] = check_archive('docs/evidence/p06-ready-chain-20261004', 'manifest.json', 'files', 'directed')
results['fit'] = check_archive('docs/evidence/p06-ready-chain-fit-20261004', 'archive-manifest.json', 'artifacts', 'fit')
results['microcode'] = check_archive('docs/evidence/spk286-microcode-repair-20261004', 'receipt.json', 'artifacts_sha256', 'microcode')
binding = json.loads((ROOT / 'docs/evidence/p06-ready-chain-20261004/functional-sources.json').read_text())
for name, expected in binding['source_sha256'].items():
    assert digest((ROOT / name).read_bytes()) == expected, f'Current directed input drift: {name}'
results['current_directed_inputs'] = len(binding['source_sha256'])
microcode = json.loads((ROOT / 'docs/evidence/spk286-microcode-repair-20261004/receipt.json').read_text())
for name, expected in microcode['source_sha256_after'].items():
    assert digest((ROOT / name).read_bytes()) == expected, f'Current compiler/test input drift: {name}'
results['current_microcode_repair_inputs'] = len(microcode['source_sha256_after'])
rbf = ROOT / 'build/p06-ready-chain-allfeatures-20261004-v1/work/output_files/PCAT-286.rbf'
data = rbf.read_bytes()
assert len(data) == 4124316
assert digest(data) == '6b0b1dd42f756908298b076a12210630e6a1b0d314950635b391ba0c87ec37f1'
results['rbf'] = {'bytes': len(data), 'sha256': digest(data)}
results['status'] = 'ARCHIVE_AND_CURRENT_COMPILED_INPUT_INTEGRITY_PASS'
results['scope'] = 'Read-only archive/source/bitstream integrity audit; broad regression acceptance is recorded separately.'
OUT.write_text(json.dumps(results, indent=2) + '\n', newline='\n')
print(json.dumps(results, indent=2))
