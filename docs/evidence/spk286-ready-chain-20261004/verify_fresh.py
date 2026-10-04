"""Read-only verification of the immutable fresh standalone evidence archive."""
from pathlib import Path, PurePosixPath
import gzip
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(name):
    rel = PurePosixPath(name)
    assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in name, name
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT), name
    return path


def raw_json(name):
    return json.loads(gzip.decompress(local(name).read_bytes()))


def main():
    manifest = json.loads(local('fresh-archive-manifest.json').read_text())
    assert manifest['status'] == 'STANDALONE_FRESH_GATES_ARCHIVED_SHARED_ACCEPTANCE_SEPARATE'
    rows = manifest['artifacts']
    assert len(rows) == manifest['artifact_count'] == 133
    assert len({row['stored_path'] for row in rows}) == len(rows)
    for row in rows:
        data = local(row['stored_path']).read_bytes()
        assert digest(data) == row['stored_sha256'], row['stored_path']
        plain = gzip.decompress(data)
        assert digest(plain) == row['sha256'], row['stored_path']
        assert len(plain) == row['bytes'], row['stored_path']
    bundle = local('standalone-source.tar.gz')
    assert digest(bundle.read_bytes()) == manifest['source_bundle_sha256']
    with tarfile.open(bundle, 'r:gz') as archive:
        members = archive.getmembers()
        assert all(item.isfile() for item in members)
        assert len({item.name for item in members}) == len(members)
        sources = {item.name: digest(archive.extractfile(item).read()) for item in members}
    assert sources == manifest['source_sha256']
    assert len(sources) == manifest['source_count'] == 1079
    assert digest(local('record_fresh.py').read_bytes()) == manifest['record_fresh_sha256']
    main_receipt = raw_json('raw/fresh/receipt.json.gz')
    native_receipt = raw_json('raw/fresh/smoke-state-receipt.json.gz')
    focused = raw_json('raw/focused/receipt.json.gz')
    assert main_receipt['status'] == 'STANDALONE_DISTINCT_GATES_PASS'
    assert native_receipt['status'] == 'STANDALONE_NATIVE_SMOKE_STATE_PASS'
    assert len(main_receipt['results']) == 28 and len(native_receipt['results']) == 5
    assert len(focused['results']) == 4
    for receipt in (main_receipt, native_receipt, focused):
        assert all(row['status'] == 'PASS' and row['exit_code'] == 0 for row in receipt['results'].values())
    # Keep the preliminary receipt historical. Final shared acceptance belongs
    # to the separately reviewed portable packet in the standalone repository.
    preliminary = raw_json('raw/preliminary/composed-receipt.json.gz')
    assert preliminary['status'] == 'STANDALONE_FRESH_GATES_PASS_SHARED_VENDOR_PENDING'
    assert preliminary['standalone_full_make_regression_executed'] is False
    print('STANDALONE_FRESH_ARCHIVE_VERIFIED artifacts=133 sources=1079 stages=33 focused=4 shared_acceptance=separate')
    print('Manifest SHA256 ' + digest(local('fresh-archive-manifest.json').read_bytes()))


if __name__ == '__main__':
    main()
