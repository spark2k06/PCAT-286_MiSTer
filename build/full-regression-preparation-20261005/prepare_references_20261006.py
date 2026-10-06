"""Bind exact existing reference inputs for the requested regression.

Only three archived buffer files and seven prior FDC files are copied. Original
firmware and physical captures remain read-only external inputs; missing images
are not substituted.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'build/full-regression-references-20261006-v1'
BUFFER_PACKET = ROOT / 'docs/evidence/p06-buffer-idle-payload-20261005'
FDC_RECEIPT = ROOT / 'docs/evidence/fixed50-timing-20261003/retained-fdc-portable-directed.json'
FDC_BEFORE = ROOT / 'build/fixed50-retained-io-directed-20261003/machine/before/work'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wsl(path):
    rel = path.resolve().relative_to(ROOT)
    return '/mnt/d/GitHub/PCAT-286_MiSTer/' + rel.as_posix()


def inventory(path):
    if path.is_file():
        return {'file': sha(path.read_bytes())}
    return {p.relative_to(path).as_posix(): sha(p.read_bytes())
            for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    assert not OUTPUT.exists(), 'Reference set must be fresh'
    packet = json.loads((BUFFER_PACKET / 'archive-manifest.json').read_bytes())
    archive = BUFFER_PACKET / packet['archive']
    assert sha(archive.read_bytes()) == packet['archive_sha256']
    receipt = json.loads((BUFFER_PACKET / 'receipt.json').read_bytes())
    fdc = json.loads(FDC_RECEIPT.read_bytes())
    copies = {}
    with tarfile.open(archive) as tar:
        for name, expected in receipt['reference_sha256'].items():
            source = 'reference/' + name
            data = tar.extractfile(source).read()
            assert sha(data) == expected == packet['members'][source]['sha256']
            copies['buffer/' + name] = data
    for name, evidence in fdc['source_sha256'].items():
        data = (FDC_BEFORE / name).read_bytes()
        assert sha(data) == evidence['reference']
        copies['fdc/' + name] = data
    externals = {
        'PHOENIX': ROOT / 'build/timing-debug-div2-20260921-1332/work/SW/ROMs/test/Phoenix_AT_Clone_A286_v1.01_64K.ROM',
        'QUARTUS_ALTERA_MF_V': ROOT / 'build/sdram-ddio-waveform-20261001/altera_mf.v',
        'TIMING_NEGATIVE_RUN': ROOT / 'build/p06-null-segment-allfeatures-20261005-v1',
        'VIDEO_INVENTORY': ROOT / 'docs/evidence/video-register-placement-20261002/register-locations.tsv',
    }
    assert sha(externals['PHOENIX'].read_bytes()) == '306ac7c3a0ee713385de53f5dd0625ee040f3ea6606b09e9d5fce3c6a00b273e'
    OUTPUT.mkdir()
    for name, data in copies.items():
        dest = OUTPUT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        assert dest.read_bytes() == data
    externals['BUFFER_REFERENCE'] = OUTPUT / 'buffer'
    externals['FDC_REFERENCE'] = OUTPUT / 'fdc'
    references = {name: {'path': wsl(path), 'sha256': inventory(path)}
                  for name, path in externals.items()}
    (OUTPUT / 'references.json').write_text(json.dumps(references, indent=2) + '\n', encoding='utf-8', newline='\n')
    (OUTPUT / 'provenance.json').write_text(json.dumps({
        'status': 'EXISTING_REFERENCES_BOUND_NO_FIRMWARE_SUBSTITUTION',
        'buffer_packet_sha256': packet['archive_sha256'],
        'buffer_receipt_sha256': sha((BUFFER_PACKET / 'receipt.json').read_bytes()),
        'fdc_receipt_sha256': sha(FDC_RECEIPT.read_bytes()),
        'copies_sha256': {name: sha(data) for name, data in copies.items()},
        'reference_sha256': {name: spec['sha256'] for name, spec in references.items()},
        'missing': ['LANDMARK_ORIGINAL', 'LANDMARK_SKIP_PM'],
    }, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('REGRESSION_REFERENCES_BOUND', len(copies), len(references))


if __name__ == '__main__':
    main()
