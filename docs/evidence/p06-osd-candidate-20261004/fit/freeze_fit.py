"""Preserve the newly generated selector bitstream evidence without claiming closure."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/p06-osd-candidate-20261004'
DEST = BASE / 'fit'
RUN = ROOT / 'build/p06-osd-allfeatures-seed1-v2-fit-20261004'
RECORD = ROOT / 'build/p06-osd-allfeatures-seed1-v2-record-20261004'
SUPPLEMENT = ROOT / 'build/p06-osd-allfeatures-seed1-v2-supplement-20261004'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(source, name, artifacts):
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    original_sha = sha(source)
    if source.stat().st_size > 300000:
        target = target.with_name(target.name + '.gz')
        with source.open('rb') as inp, target.open('wb') as stream:
            with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as out:
                shutil.copyfileobj(inp, out)
        assert hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest() == original_sha
        encoding = 'gzip'
    else:
        shutil.copy2(source, target)
        assert sha(target) == original_sha
        encoding = 'raw'
    artifacts.append(dict(path=target.relative_to(BASE).as_posix(), sha256=sha(target),
                          raw_sha256=original_sha, raw_bytes=source.stat().st_size,
                          encoding=encoding))


def main():
    validation = BASE / 'validation-manifest.json'
    before = sha(validation)
    assert json.loads(validation.read_text())['status'] == 'DIRECTED_OSD_SPEED_SELECTOR_VALIDATION_PASS'
    record = json.loads((RECORD / 'receipt.json').read_text())
    supplement = json.loads((SUPPLEMENT / 'receipt.json').read_text())
    assert record['status'] == 'NEW_OSD_RBF_MEASURED_NOT_HARDWARE_ACCEPTED'
    assert supplement['status'] == 'P06_OSD_FIT_SUPPLEMENTARY_EVIDENCE_INTEGRITY_PASS'
    assert supplement['recorder_receipt_sha256'] == sha(RECORD / 'receipt.json')
    assert sha(RUN / 'manifest.json') == record['manifest_sha256'] == supplement['manifest_sha256']
    auditor = RUN / 'audit_source/audit_p06_osd_fit.py'
    assert sha(auditor) == supplement['auditor_sha256']
    assert supplement['rbf'] == record['rbf']
    assert sha(Path(record['rbf']['path'])) == record['rbf']['sha256']
    DEST.mkdir(parents=True, exist_ok=False)
    artifacts = []
    if 'manifest.json' not in supplement['run_artifacts_sha256']:
        copy(RUN / 'manifest.json', 'run/manifest.json', artifacts)
    for name, digest in supplement['run_artifacts_sha256'].items():
        name = name.replace('\\', '/')
        source = RUN / name
        assert sha(source) == digest, name
        if source.suffix in ('.rbf', '.sof'):
            continue
        copy(source, 'run/' + name, artifacts)
    # Preserve raw report bytes, including Quartus' legacy degree symbol.
    for name in ('work/output_files/PCAT-286.sta.rpt',
                 'work/output_files/PCAT-286.map.rpt',
                 'work/output_files/PCAT-286.map.summary',
                 'work/output_files/PCAT-286.asm.rpt',
                 'git-status.txt', 'tracked.patch', 'rbf-info.txt', 'bitstreams.sha256',
                 'compile-started.txt', 'timing.log', 'driver-console.log'):
        copy(RUN / name, 'run/' + name, artifacts)
    rom = record['compiled_rom']
    mif = RUN / 'work' / rom['mif'].replace('\\', '/')
    assert sha(mif) == rom['mif_sha256']
    copy(mif, 'compiled-rom/' + mif.name, artifacts)
    for directory, label in ((RECORD, 'record'), (SUPPLEMENT, 'supplement')):
        for source in sorted(directory.iterdir()):
            if source.is_file():
                copy(source, label + '/' + source.name, artifacts)
    copy(auditor, 'audit_source/' + auditor.name, artifacts)
    copy(RUN / 'audit_source/prepare-check.json', 'audit_source/prepare-check.json', artifacts)
    for name in ['scripts/record_p06_osd_fit.py', 'scripts/build_at_no_debug.sh',
                 'scripts/p05_snapshot.py', 'scripts/report_at_50mhz_timing.tcl',
                 'scripts/check_p05_at_project.tcl', 'PCAT-286.qsf', 'SYSTEM.sdc',
                 'sys/sys_top.sdc',
                 'config.tcl', *supplement['imported_frozen_helpers_sha256']]:
        copy(RUN / 'work' / name, 'frozen-source/' + name, artifacts)
    baseline = ROOT / 'docs/evidence/pcat-resources-20261004'
    for name in ('resources.json', 'PCAT-286.fit.summary'):
        source = baseline / name
        if not source.exists():
            source = ROOT / 'build/fixed50-admission-retained-fdc-seed1-fit-20261003/work/output_files' / name
        copy(source, 'baseline/' + name, artifacts)
    copy(Path(__file__), 'freeze_fit.py', artifacts)
    result = dict(status='NEW_OSD_RBF_EVIDENCE_ARCHIVED_NOT_HARDWARE_ACCEPTED',
        validation_manifest_sha256=before, rbf=record['rbf'],
        recorder_receipt_sha256=sha(RECORD / 'receipt.json'),
        supplemental_receipt_sha256=sha(SUPPLEMENT / 'receipt.json'),
        artifacts=artifacts, timing_result=supplement['timing_result'],
        scope=supplement['scope'])
    (DEST / 'fit-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    assert sha(validation) == before, 'Original validation manifest changed'
    print(result['status'], 'artifacts', len(artifacts))


if __name__ == '__main__':
    main()
