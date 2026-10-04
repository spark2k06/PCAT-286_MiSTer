"""Passive integrity check of the standalone evidence overlay, without imports or tests."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'build/spk286-ready-chain-standalone-gates-20261004-v1/portable/docs/evidence/ready-chaining-20261004'

def sha(data):
    return hashlib.sha256(data).hexdigest()

manifest_bytes = (PACKET / 'manifest.json').read_bytes()
manifest = json.loads(manifest_bytes)
assert manifest['status'] == 'STANDALONE_COMPOSED_GATES_PASS'
names, raw_digests = set(), set()
for row in manifest['artifacts']:
    name = row['stored_path']
    assert name not in names
    names.add(name)
    path = (PACKET / name).resolve()
    assert path.is_relative_to(PACKET.resolve())
    stored = path.read_bytes()
    assert len(stored) == row['bytes'] and sha(stored) == row['stored_sha256'], name
    if row['original_sha256'] is None:
        assert name in ('standalone-source.tar.gz', 'vendor-source.tar.gz',
                        'fresh-archive-manifest.json', 'verify_packet.py')
    else:
        raw = gzip.decompress(stored) if name.endswith('.gz') else stored
        assert sha(raw) == row['original_sha256'], name
        raw_digests.add(sha(raw))
assert len(names) == manifest['artifact_count'] == 151
assert {p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*') if p.is_file()} == names | {'manifest.json'}
for archive, key, count in (('standalone-source.tar.gz', 'standalone_source_sha256', 1079),
                            ('vendor-source.tar.gz', 'vendor_source_sha256', 581)):
    expected = manifest[key]
    assert len(expected) == count
    observed = {}
    with tarfile.open(PACKET / archive, 'r:gz') as source_archive:
        for member in source_archive:
            assert member.isfile(), 'Unexpected non-file archive member: ' + member.name
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert member.name not in observed
            content = source_archive.extractfile(member).read()
            assert len(content) == member.size
            observed[member.name] = sha(content)
    assert observed == expected, archive
review_files = ('build/p06-ready-chain-regression-final-review-20261004.json',
                'build/p06-ready-chain-regression-final-review-20261004.py',
                'build/spk286-ready-chain-composed-independent-review-20261004.json',
                'build/spk286-ready-chain-composed-independent-review-20261004.py')
for name in review_files:
    assert sha((ROOT / name).read_bytes()) in raw_digests, 'Independent proof missing: ' + name
composed = json.loads((ROOT / 'build/spk286-ready-chain-standalone-gates-20261004-v1/composed-receipt.json').read_bytes())
assert composed['status'] == manifest['status']
assert sha((ROOT / 'build/spk286-ready-chain-standalone-gates-20261004-v1/composed-receipt.json').read_bytes()) in raw_digests
result = dict(status='STANDALONE_PORTABLE_ARCHIVE_INDEPENDENT_REVIEW_PASS',
    manifest_sha256=sha(manifest_bytes), reviewer_sha256=sha(Path(__file__).read_bytes()),
    artifact_count=len(names), inventory_files=len(names) + 1,
    standalone_source_archive_files=1079, vendor_source_archive_files=581,
    exact_inventory=True, all_stored_and_raw_sha_verified=True,
    independent_acceptance_receipts_and_helpers_preserved=True,
    scope='Passive byte integrity of the prepared standalone overlay. Its functional claim remains exact shared source identity plus fresh native stages, not literal standalone make regression, physical hardware or timing closure.',
    source_writes=False, new_tests=False, findings=[])
output = ROOT / 'build/spk286-ready-chain-portable-archive-independent-review-20261004.json'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(result['status'], 'artifacts=' + str(len(names)))
