"""Freeze the READY-chain candidate's measured fit and four-corner STA.

Run once from the repository. Keep the original RBF/SOF in build; archive
their identities, every raw report, all frozen sources and the actual ROM MIF.
This is measurement evidence, not timing closure or hardware acceptance.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(__file__).resolve().parent
RUN = ROOT / 'build/p06-ready-chain-allfeatures-20261004-v1'
BASELINE = ROOT / 'build/at-floppy-fix-wp-allfeatures-20261004'
BINDING = ROOT / 'docs/evidence/p06-ready-chain-20261004/functional-sources.json'
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_pcat_resources import parse, grouped, table, METRICS
from check_sync_microcode_image import analyze_compiled_image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (TARGET / 'archive-manifest.json').exists(), 'Archive already exists'
    manifest = json.loads((RUN / 'manifest.json').read_text())
    audit = json.loads((RUN / 'fixed50-fit-audit.json').read_text())
    binding = json.loads(BINDING.read_text())
    assert audit['status'] == 'MEASURED_FIXED50_TIMING_FAIL'
    assert audit['manifest_sha256'] == sha(RUN / 'manifest.json')
    assert audit['functional_binding_sha256'] == sha(BINDING)
    assert binding['status'] == 'FIXED50_DIRECTED_VALIDATION_PASS'
    assert len(binding['source_sha256']) == 331
    for name, expected in binding['source_sha256'].items():
        assert sha(RUN / 'work' / name) == expected, name
    rom = analyze_compiled_image(RUN)
    assert rom == audit['compiled_rom']
    for name, expected in audit['raw_reports_sha256'].items():
        assert sha(RUN / 'timing' / name) == expected, name
    rows = parse(RUN / 'work/output_files/PCAT-286.fit.rpt')
    cpus = [row for row in rows if row['entity'] == 'spk286_profiled']
    assert len(cpus) == 1
    costs = json.loads((RUN / 'fitted-resources.json').read_text())
    assert costs['resources'] == audit['resources']
    cpu = {key: cpus[0][key]['inclusive'] for key in METRICS}
    assert cpu == costs['cpu_resources']
    artifacts = {}

    def preserve(source, name):
        source = Path(source)
        destination = TARGET / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        original_sha = sha(source)
        compressed = source.stat().st_size > 300000
        if compressed:
            destination = destination.with_name(destination.name + '.gz')
            with destination.open('wb') as stream:
                with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as zipped:
                    zipped.write(source.read_bytes())
            assert hashlib.sha256(gzip.decompress(destination.read_bytes())).hexdigest() == original_sha
        else:
            shutil.copyfile(source, destination)
            assert sha(destination) == original_sha
        artifacts[destination.relative_to(TARGET).as_posix()] = dict(
            sha256=sha(destination), raw_sha256=original_sha,
            bytes=destination.stat().st_size,
            raw_bytes=source.stat().st_size, compression='gzip' if compressed else 'none')

    names = [
        'manifest.json', 'compile-started.txt', 'compile.log', 'driver-console.log',
        'container-image.txt', 'git-status.txt', 'tracked.patch', 'project-check.log',
        'profile-check.log', 'timing.log', 'bitstreams.sha256', 'rbf-info.txt',
        'candidate.json', 'baseline-resources.json', 'fitted-resources.json',
        'fitted-entities.json', 'fitted-blocks.md', 'watchdog-receipt.json',
        'compiled-rom-final-check.json', 'fixed50-fit-audit.json',
        'work/output_files/PCAT-286.fit.rpt', 'work/output_files/PCAT-286.fit.summary',
        'work/output_files/PCAT-286.map.rpt', 'work/output_files/PCAT-286.map.summary',
        'work/output_files/PCAT-286.sta.rpt', 'work/output_files/PCAT-286.sta.summary',
        'work/' + rom['mif'].replace('\\', '/'),
    ]
    for name in names:
        preserve(RUN / name, 'run/' + name)
    for source in sorted((RUN / 'timing').rglob('*')):
        if source.is_file():
            preserve(source, 'run/' + source.relative_to(RUN).as_posix())
    preserve(BINDING, 'functional-sources.json')
    preserve(BASELINE / 'manifest.json', 'baseline/manifest.json')
    # Include each auditor/tool input used by the final measurement.
    for name in ['audit_fixed50_fit.py', 'summarize_at_50mhz_timing.py',
                 'check_sync_microcode_image.py', 'analyze_pcat_resources.py']:
        preserve(ROOT / 'scripts' / name, 'tools/' + name)

    # A deterministic complete compiled snapshot makes source checks replayable
    # after removing Quartus's nonessential caches. Generated build_id is recorded.
    source_entries = {}
    snapshot = TARGET / 'compiled-source.tar.gz'
    with snapshot.open('wb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|') as archive:
                for name, expected in sorted(manifest['source_sha256'].items()):
                    source = RUN / 'work' / name
                    actual = sha(source)
                    if actual != expected:
                        assert name == 'build_id.v' and name in audit['generated_sources']
                    posix_name = name.replace('\\', '/')
                    contents = source.read_bytes()
                    info = tarfile.TarInfo(posix_name)
                    info.size, info.mode, info.mtime = len(contents), 0o644, 0
                    info.uid = info.gid = 0
                    archive.addfile(info, io.BytesIO(contents))
                    source_entries[posix_name] = dict(frozen_sha256=expected, compiled_sha256=actual)
    with tarfile.open(snapshot, 'r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(source_entries)
        for member in members:
            assert member.isfile() and member.name in source_entries
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == source_entries[member.name]['compiled_sha256']
    (TARGET / 'compiled-source-manifest.json').write_text(json.dumps(source_entries, indent=2) + '\n')
    (TARGET / 'blocks.md').write_text(table(grouped(rows), audit['resources']['placed_alms']))
    (TARGET / 'cpu.json').write_text(json.dumps(cpu, indent=2) + '\n')
    (TARGET / '.gitattributes').write_text('* -text -whitespace\n')
    timing_rows = [line.split() for line in (RUN / 'timing/path_counts.txt').read_text().splitlines()]
    minima = {}
    for corner, group, check, count, margin in timing_rows:
        if int(count):
            candidate = dict(corner=corner, margin_ns=float(margin))
            if check not in minima.setdefault(group, {}) or float(margin) < minima[group][check]['margin_ns']:
                minima[group][check] = candidate
    receipt = dict(
        status='READY_CHAIN_NEW_RBF_MEASURED_TIMING_FAIL_HARDWARE_PENDING',
        source_revision_at_snapshot=manifest['head'],
        source_commit_pending=True, source_count=len(source_entries),
        manifest_sha256=sha(RUN / 'manifest.json'),
        functional_binding_sha256=sha(BINDING), functional_source_count=len(binding['source_sha256']),
        functional_scope=binding['scope'], functional_receipts=binding['receipts'],
        placement_seed=audit['placement_seed'],
        feature_configuration=json.loads((RUN / 'candidate.json').read_text())['feature_configuration'],
        physical_clock_mhz=50, resources=audit['resources'], cpu_resources=cpu,
        resource_delta_vs_floppy=costs['resource_delta_vs_floppy'],
        cpu_delta_vs_floppy=costs['cpu_delta_vs_floppy'],
        timing_ns=audit['margins_ns'], worst_group_margins_ns=minima,
        timing_failures=audit['failures'], timing_closed=False,
        compiled_rom=rom, rbf=audit['rbf'], sof_sha256=audit['sof_sha256'],
        baseline=dict(run=BASELINE.relative_to(ROOT).as_posix(),
                      manifest_sha256=sha(BASELINE / 'manifest.json'),
                      archived_evidence='docs/evidence/at-floppy-rbf-20261004'),
        hardware_accepted=False, full_standalone_regression_complete=False,
        retained_build_artifacts=['work/output_files/PCAT-286.rbf', 'work/output_files/PCAT-286.sof'],
        removable_cache_scope='Only after archive verification: db contents except the actual ROM MIF; incremental_db. No sources, bitstreams or reports.',
        scope='Source-bound directed fetch/R0/all-profile CPU compatibility/AT checks and actual full-machine Quartus measurement. No native cycle accuracy, physical timing closure, guest OS, hardware performance or completed standalone regression claim.')
    (TARGET / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    for name in ['record_fit.py', 'compiled-source.tar.gz', 'compiled-source-manifest.json',
                 'blocks.md', 'cpu.json', '.gitattributes', 'receipt.json']:
        source = TARGET / name
        artifacts[name] = dict(sha256=sha(source), bytes=source.stat().st_size,
                               compression='tar+gzip' if name.endswith('.tar.gz') else 'none')
    for name, identity in artifacts.items():
        assert sha(TARGET / name) == identity['sha256']
    archive_receipt = dict(status='READY_CHAIN_FIT_ARCHIVE_HASH_VERIFIED',
                          artifact_count=len(artifacts), source_count=len(source_entries),
                          archive_bytes=sum(identity['bytes'] for identity in artifacts.values()),
                          artifacts=artifacts)
    (TARGET / 'archive-manifest.json').write_text(json.dumps(archive_receipt, indent=2) + '\n')
    print(json.dumps({key: archive_receipt[key] for key in ['status', 'artifact_count', 'source_count', 'archive_bytes']}))


if __name__ == '__main__':
    main()
