"""Independently validate sealed traces without rebuilding or extracting files."""
from pathlib import Path
import csv
import hashlib
import io
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = 'build/p06-timing-audit-20261005/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    archive = HERE / 'p06-historical-timing-audit-20261005.tar.gz'
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        assert all(m.isfile() and m.name.startswith(PREFIX)
                   and '..' not in Path(m.name).parts for m in members)
        assert len({m.name for m in members}) == len(members)

        def read(name):
            return tar.extractfile(name).read()

        manifest = json.loads(read(PREFIX + 'sealed-manifest.json'))
        assert len(members) == len(manifest['artifacts']) + 1
        for name, entry in manifest['artifacts'].items():
            data = read(name)
            assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], name
        for name, digest in manifest['source_hashes'].items():
            data = read(name) if name.startswith(PREFIX) else (ROOT / name).read_bytes()
            assert sha(data) == digest, name
        receipt = json.loads(read(PREFIX + 'branch-receipt.json'))
        assert receipt['status'] == 'P06_BRANCH_DEPENDENCY_DUAL_DIAGNOSIS_PASS'
        assert len(receipt['runs']) == 304 and len(receipt['comparisons']) == 152
        all_rows = 0
        dead_rows = 0
        for comparison in receipt['comparisons']:
            base = f"p{comparison['profile']}-{comparison['name']}.csv"
            streams = [list(csv.DictReader(io.StringIO(read(PREFIX + simulator + '-' + base).decode())))
                       for simulator in ('iverilog', 'verilator')]
            assert len(streams[0]) == len(streams[1]) == comparison['rows']
            ignored = []
            for a, b in zip(*streams):
                delta = {key: [a[key], b[key]] for key in a if a[key] != b[key]}
                if delta:
                    assert all(row['consume_valid'] == row['opcode_start'] == row['start_interval'] == '0'
                               for row in (a, b))
                    assert set(delta) <= {'queue_byte', 'metadata_valid', 'metadata_clocks', 'scheduled', 'estimated'}
                    ignored.append({'edge': int(a['edge']), 'unused_empty_queue_fields': delta})
            assert ignored == comparison['empty_queue_differences']
            all_rows += len(streams[0])
            dead_rows += len(ignored)
        for run in receipt['runs']:
            data = read(run['trace'])
            assert sha(data) == run['trace_sha256']
            rows = list(csv.DictReader(io.StringIO(data.decode())))
            start = next(r for r in rows if r['start_interval'] == '1'
                         and int(r['cs'], 16) == 0x106e and int(r['ip'], 16) == run['branch_ip'])
            if run['name'] in ('baseline', 'b0'):
                end = [r for r in rows if r['retire_fire'] == '1' and r['opcode'] == 'e2'][-1]
                assert int(end['tick']) - int(start['tick']) == run['processor_boundaries']
                assert int(end['edge']) - int(start['edge']) == run['fabric_clocks']
            else:
                end = next(r for r in rows if r['retire_fire'] == '1' and int(r['instruction_ip'], 16) == run['branch_ip'])
                target_end = next(r for r in rows if r['retire_fire'] == '1' and int(r['instruction_ip'], 16) == run['target_ip'])
                assert int(end['tick']) - int(start['tick']) == run['branch_processor_clocks']
                assert int(target_end['tick']) - int(start['tick']) == run['pair_processor_clocks']
                assert run['branch_processor_clocks'] == (8 if run['name'].startswith('loop') else 7)
        assert all_rows == manifest['complete_paired_trace_rows'] == 188145
        assert dead_rows == manifest['declared_unused_empty_head_difference_rows'] == 3724
    result = {'status': 'INDEPENDENT_ARCHIVE_HASH_SOURCE_AND_TRACE_REVIEW_PASS',
              'archive_sha256': sha(archive.read_bytes()), 'archive_bytes': archive.stat().st_size,
              'members': len(members), 'runs': 304, 'paired_rows': all_rows,
              'unused_empty_head_difference_rows': dead_rows,
              'production_source_hashes_checked': len(manifest['source_hashes']),
              'simulation_rerun': False}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
