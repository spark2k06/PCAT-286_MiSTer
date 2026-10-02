#!/usr/bin/env python3
"""Restore independently validated upstream unit banks to the vendor package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    record = json.loads((run/'missing-unit-replays.json').read_text())
    assert record['complete'] and record['runs']
    assert all(row['exit_status'] == 0 for row in record['runs'])
    cpu = ROOT/'vendor/spk286'
    for name, digest in record['frozen_cpu_sha256'].items():
        assert sha(cpu/name) == digest, f'Production CPU changed: {name}'
    tested = {row['stage'] for row in record['runs']}
    destinations = {}
    for name, source in record['imported_test_benches'].items():
        relative = Path(name)
        assert relative.parts[:2] == ('sim', 'unit')
        assert relative.stem.removesuffix('_tb') in tested
        private = run/'replays/missing-unit-package'/relative
        assert sha(private) == source['sha256']
        assert sha(Path(source['source'])) == source['sha256']
        target = cpu/relative
        assert not target.exists(), f'Do not replace an existing bank: {target}'
        destinations[str(target.relative_to(ROOT))] = sha(private)
    for name in record['imported_test_benches']:
        shutil.copyfile(run/'replays/missing-unit-package'/name, cpu/name)
    result = dict(upstream_revision=record['upstream_revision'],
        copied_test_benches_sha256=destinations,
        frozen_cpu_sha256=record['frozen_cpu_sha256'],
        validated_runs=record['runs'],
        statement='Only missing verification files restored. Every bank passed both simulators with active CPU options and unchanged frozen PCAT RTL.')
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    assert not args.receipt.exists()
    args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print('VERIFICATION_PACKAGE_RESTORED', len(destinations))


if __name__ == '__main__':
    main()
