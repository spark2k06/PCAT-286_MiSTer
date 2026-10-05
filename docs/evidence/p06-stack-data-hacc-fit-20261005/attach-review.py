"""Attach independent review without altering the sealed fit archive."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
packet = root / 'docs/evidence/p06-stack-data-hacc-fit-20261005'
review = root / 'build/p06-stack-data-hacc-actual-review-20261005'
manifest_path = packet / 'manifest.json'
manifest = json.loads(manifest_path.read_bytes())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(packet / manifest['archive']) == manifest['sha256']
result = json.loads((review / 'review.json').read_bytes())
assert result['status'] == 'INDEPENDENT_ACTUAL_FIT_REVIEW_PASS_TIMING_STILL_OPEN'
assert result['archive_sha256'] == manifest['sha256']
names = {
    'review_actual.py': 'independent-review.v1.py',
    'review_actual_v2.py': 'independent-review.v2.py',
    'review_v1_failure.json': 'independent-review.v1-failure.json',
    'review.json': 'independent-review.json',
    'review.md': 'independent-review.md',
}
bindings = {}
for source, target in names.items():
    origin, destination = review / source, packet / target
    assert not destination.exists()
    shutil.copyfile(origin, destination)
    assert origin.read_bytes() == destination.read_bytes()
    bindings[target] = {'sha256': digest(destination), 'bytes': destination.stat().st_size}
manifest['independent_review'] = {
    'status': result['status'],
    'archive_sha256': result['archive_sha256'],
    'files': bindings,
    'scope': 'Ancillary review files; sealed archive and its member identities remain unchanged.',
}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
assert digest(packet / manifest['archive']) == manifest['sha256']
print('INDEPENDENT_REVIEW_ATTACHED', len(bindings), manifest['sha256'])
