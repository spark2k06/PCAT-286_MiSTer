"""Passive audit of the sealed broad regression packet; no simulation or source writes."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'docs/evidence/p06-ready-chain-regression-20261004'
RUN = ROOT / 'build/p06-ready-chain-regression-20261004-v3'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def sha(path):
    return digest(Path(path).read_bytes())

def read(path):
    return json.loads(Path(path).read_bytes())

manifest_path = PACKET / 'archive-manifest.json'
manifest = read(manifest_path)
assert manifest['status'] == 'BROAD_REGRESSION_ARCHIVE_HASH_VERIFIED'
verification_path = RUN / 'archive-verification.json'
verification = read(verification_path)
assert verification['status'] == 'REGRESSION_ARCHIVE_AND_LIVE_SOURCE_PASS'
assert verification['manifest_sha256'] == sha(manifest_path)
assert verification['verification_script_sha256'] == sha(RUN / 'verify_archive.py')
assert manifest['archiver_sha256'] == sha(RUN / 'archive_regression.py')
final_path = RUN / 'receipt.json'
final = read(final_path)
independent_path = ROOT / 'build/p06-ready-chain-regression-final-review-20261004.json'
independent = read(independent_path)
assert independent['status'] == 'BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS'
assert independent['regression_receipt_sha256'] == sha(final_path)
assert final['status'] == 'SPK286_READY_CHAIN_REGRESSION_PASS' and final['exit_code'] == 0

rows = {}
raw_bytes = stored_bytes = 0
for row in manifest['artifacts']:
    name = row['artifact']
    assert name not in rows, 'Duplicate archive artifact: ' + name
    path = (PACKET / name).resolve()
    assert path.is_relative_to(PACKET.resolve()), 'Path outside packet: ' + name
    stored = path.read_bytes()
    assert len(stored) == row['artifact_bytes'] and digest(stored) == row['artifact_sha256'], name
    raw = gzip.decompress(stored) if row['gzip'] else stored
    assert len(raw) == row['raw_bytes'] and digest(raw) == row['raw_sha256'], name
    rows[name] = row
    raw_bytes += len(raw)
    stored_bytes += len(stored)
assert {p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*') if p.is_file()} == set(rows) | {'archive-manifest.json'}
assert len(rows) == verification['artifact_count']
assert sha(PACKET / 'v3/receipt.json') == sha(final_path)
archived_review = rows['independent-review/p06-ready-chain-regression-final-review-20261004.json']
assert archived_review['raw_sha256'] == sha(independent_path)
assert rows['independent-review/p06-ready-chain-regression-final-review-20261004.py']['raw_sha256'] == independent['auditor_sha256']

sources = {name[len('compiled-source/'):].removesuffix('.gz') if row['gzip'] else name[len('compiled-source/'):]: row
           for name, row in rows.items() if name.startswith('compiled-source/')}
assert len(sources) == manifest['compiled_source_count'] == verification['compiled_source_count'] == 581
assert set(sources) == set(final['snapshot_sha256_after'])
for name, row in sources.items():
    assert row['raw_sha256'] == final['snapshot_sha256_after'][name] == sha(ROOT / name), name
assert manifest['external_corpus_inputs'] == verification['corpus_bindings'] == 98
assert manifest['cache_hits'] == final['cache_hit_count'] == 70
assert manifest['cache_misses'] == final['cache_miss_count'] == 59
assert manifest['source_corpus_cache_changes'] == []

derived = manifest['postrun_runtime_derivative_sha256']
for name, expected in derived.items():
    candidates = [row for artifact, row in rows.items()
                  if artifact == 'v3/postrun-derived/' + name + ('.gz' if row['gzip'] else '')]
    assert len(candidates) == 1 and candidates[0]['raw_sha256'] == expected, name
    assert sha(RUN / name) == expected, 'Live postrun derivative changed: ' + name
batch_files = [name for name in derived if name.startswith('work/singlestep/batches/') and name.endswith('.bin')]
assert len(batch_files) == 97
runtime_roms = [name for name in derived if name.endswith(('.hex', '.mem'))]
assert runtime_roms, 'Runtime ROM byte archive is empty'
yosys_logs = [name for name in derived if name.startswith('work/reports/') and name.endswith('.log')]
assert yosys_logs, 'Mapped Yosys reports absent'

result = dict(status='BROAD_REGRESSION_SEALED_ARCHIVE_INDEPENDENT_REVIEW_PASS',
    reviewer_sha256=sha(__file__), manifest_sha256=sha(manifest_path),
    primary_verification_sha256=sha(verification_path),
    regression_receipt_sha256=sha(final_path), regression_independent_review_sha256=sha(independent_path),
    artifacts=len(rows), raw_bytes=raw_bytes, stored_bytes=stored_bytes,
    source_inputs=581, corpus_hash_bindings=98, cache_hits=70, fresh_compile_misses=59,
    postrun_derivatives=len(derived), singlestep_binary_batches=len(batch_files),
    runtime_rom_files=len(runtime_roms), yosys_report_logs=len(yosys_logs),
    exact_inventory_and_stored_raw_sha=True, live_source_identity=True,
    scope='Passive archive inventory/size/raw and compressed SHA audit. Postrun ROM/batch/report bytes are bound as outputs; no invented input-before hashes. Functional acceptance is the already audited real make regression. No new simulator execution, physical/OS/MiSTer validation or timing closure.',
    tracked_source_edits=False, simulations_executed_by_reviewer=False, findings=[])
output = ROOT / 'build/p06-ready-chain-regression-archive-independent-review-20261004.json'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
print(result['status'], 'artifacts=' + str(len(rows)))
