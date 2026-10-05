"""Verify this portable evidence packet without a PCAT checkout or build tree."""
from pathlib import Path, PurePosixPath
import gzip
import hashlib
import json
import tarfile

ROOT=Path(__file__).resolve().parent


def digest(data):return hashlib.sha256(data).hexdigest()


def safe(path):
    rel=PurePosixPath(path)
    assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in path,path
    target=(ROOT/path).resolve()
    assert target.is_relative_to(ROOT),path
    return target


def source_bundle(name,expected):
    with tarfile.open(safe(name),'r:gz') as archive:
        members=archive.getmembers()
        assert all(row.isfile() for row in members),name
        observed={row.name:digest(archive.extractfile(row).read()) for row in members}
    assert observed==expected,name


def raw_json(path):return json.loads(gzip.decompress(safe(path).read_bytes()))


def main():
    manifest=json.loads(safe('manifest.json').read_text())
    assert manifest['schema_version']==1
    rows=manifest['artifacts']
    assert len(rows)==manifest['artifact_count']
    assert len({row['stored_path'] for row in rows})==len(rows)
    for row in rows:
        data=safe(row['stored_path']).read_bytes()
        assert digest(data)==row['stored_sha256'],row['stored_path']
        if row['original_sha256'] is not None:
            assert digest(gzip.decompress(data))==row['original_sha256'],row['stored_path']
    source_bundle('standalone-source.tar.gz',manifest['standalone_source_sha256'])
    main=raw_json('raw/fresh/receipt.json.gz')
    native=raw_json('raw/fresh/smoke-state-receipt.json.gz')
    assert main['status']=='STANDALONE_DISTINCT_GATES_PASS' and len(main['results'])==28
    assert native['status']=='STANDALONE_NATIVE_SMOKE_STATE_PASS' and len(native['results'])==5
    assert all(row['status']=='PASS' and row['exit_code']==0 for group in (main,native) for row in group['results'].values())
    assert manifest['standalone_full_make_regression_executed'] is False
    if manifest['shared_vendor_gate_bound']:
        source_bundle('vendor-source.tar.gz',manifest['vendor_source_sha256'])
        vendor=raw_json('shared/vendor-receipt.json.gz')
        composed=raw_json('shared/composed-receipt.json.gz')
        assert vendor['status']=='SPK286_READY_CHAIN_REGRESSION_PASS' and vendor['exit_code']==0
        for field in ('source_changes','snapshot_changes','corpus_changes','cache_changes','reused_binary_changes','cache_event_binding_errors'):
            assert field in vendor and vendor[field]==[],field
        assert composed['status']=='STANDALONE_COMPOSED_GATES_PASS'
        assert digest(gzip.decompress(safe('shared/vendor-receipt.json.gz').read_bytes()))==composed['shared']['vendor_receipt_sha256_at_compose']
        assert digest(gzip.decompress(safe('shared/regression.log.gz').read_bytes()))==vendor['log_sha256']
        broad_review=raw_json('shared/reviews/broad-review.json.gz')
        composed_review=raw_json('shared/reviews/composed-review.json.gz')
        assert broad_review['status']=='BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS'
        assert composed_review['status']=='STANDALONE_COMPOSED_INDEPENDENT_REVIEW_PASS'
        assert broad_review['regression_receipt_sha256']==composed['shared']['vendor_receipt_sha256_at_compose']
        assert composed_review['broad_receipt_sha256']==composed['shared']['vendor_receipt_sha256_at_compose']
        assert composed_review['composed_receipt_sha256']==digest(gzip.decompress(safe('shared/composed-receipt.json.gz').read_bytes()))
        assert composed_review['broad_independent_review_sha256']==digest(gzip.decompress(safe('shared/reviews/broad-review.json.gz').read_bytes()))
        assert broad_review['auditor_sha256']==digest(gzip.decompress(safe('shared/reviews/broad-review.py.gz').read_bytes()))
        assert composed_review['reviewer_source_sha256']==digest(gzip.decompress(safe('shared/reviews/composed-review.py.gz').read_bytes()))
    print('PORTABLE_PACKET_PASS artifacts=%d standalone_sources=%d shared_vendor_bound=%s' %
          (len(rows),manifest['source_count'],manifest['shared_vendor_gate_bound']))
    print(manifest['status'])


if __name__=='__main__':main()
