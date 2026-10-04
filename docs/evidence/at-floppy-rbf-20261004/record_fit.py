"""Bind the freshly fitted floppy candidate to its directed tests and raw STA."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from audit_fixed50_fit import resources, fitted_seed, CORNERS, GROUPS
from analyze_pcat_resources import parse, grouped, table, METRICS
from check_sync_microcode_image import analyze_compiled_image

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    run = ROOT/'build/at-floppy-fix-wp-allfeatures-20261004'
    work, out = run/'work', run/'work/output_files'
    manifest = json.loads((run/'manifest.json').read_text())
    assert manifest['head'].startswith('f7587e6') and not manifest['fit_sha256']
    changed = {}
    for name, expected in manifest['source_sha256'].items():
        actual = sha(work/name)
        if actual != expected:
            assert name == 'build_id.v', name
            assert (work/name).read_text().strip() == '`define BUILD_DATE "261004"'
            changed[name] = dict(before=expected,compiled=actual)
    console = (run/'compile.log').read_text(errors='replace')
    completion = re.findall(r'Full Compilation was successful\. 0 errors, (\d+) warnings', console)
    assert len(completion) == 1 and 'PCAT_AT_NEW_RBF' in (run/'driver-console.log').read_text()
    validation = {}
    for label, path, expected_status in [
        ('write', ROOT/'docs/evidence/at-floppy-write-fix-20261004/write/receipt.json', 'AT_FLOPPY_WRITE_COMPOSED_DIRECTED_PASS'),
        ('protection', ROOT/'docs/evidence/at-floppy-write-protect-20261004/matrix/receipt.json', 'AT_FLOPPY_WRITE_PROTECT_MATRIX_PASS'),
        ('profiles', ROOT/'docs/evidence/at-floppy-write-fix-20261004/profiles/receipt.json', 'AT_SPEED_PROFILES_DIRECTED_PASS')]:
        receipt = json.loads(path.read_text())
        assert receipt['status'] == expected_status
        for name, expected in receipt['source_sha256'].items():
            assert sha(work/name) == expected, (label,name)
        if label == 'write':
            assert sha(work/'rtl/spk286_integration/spk286_at_machine.sv') == receipt['machine_sha256']
            assert sha(work/'scripts/test_at_floppy_write.py') == receipt['runner_sha256']
        validation[label] = dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),scope=receipt['scope'])
    # Confirm that the measured pre-fix OSD build and this build use identical
    # CPU, profile, clocks and configuration source bytes.
    previous = ROOT/'docs/evidence/p06-osd-candidate-20261004/fit/record/receipt.json'
    baseline = json.loads(previous.read_text())
    old_manifest = json.loads((ROOT/'build/p06-osd-allfeatures-seed1-v2-fit-20261004/manifest.json').read_text())
    unchanged = [n for n in old_manifest['source_sha256'] if n.startswith('vendor/') or n in
        ('config.tcl','PCAT-286.qsf','PCAT-286.sv','SYSTEM.sdc','sys/sys_top.sdc',
         'rtl/spk286_integration/spk286_at_cpu_profile.sv','rtl/spk286_integration/spk286_machine_cpu.sv')]
    for name in unchanged:
        assert manifest['source_sha256'][name] == old_manifest['source_sha256'][name],name
    counts = [line.split() for line in (run/'timing/path_counts.txt').read_text().splitlines()]
    expected = {(c,g,k) for c in CORNERS for g in GROUPS for k in ('setup','hold')}
    expected |= {(c,'global',k) for c in CORNERS for k in ('recovery','removal')}
    assert {(c,g,k) for c,g,k,_,_ in counts} == expected
    timing = {c:{} for c in CORNERS}
    for c,g,k,count,worst in counts:
        timing[c].setdefault(g,{})[k] = float(worst) if int(count) else None
    closed = all(timing[c]['global'][k] is not None and timing[c]['global'][k] >= 0
                 for c in CORNERS for k in ('setup','hold'))
    closed &= all(timing[c]['global'][k] is None or timing[c]['global'][k] >= 0
                  for c in CORNERS for k in ('recovery','removal'))
    measured = resources(out)
    delta = {key:measured[key]-baseline['resources'][key] for key in measured
             if key != 'placed_alms_percent'}
    rows = parse(out/'PCAT-286.fit.rpt')
    cpus = [r for r in rows if r['entity']=='spk286_profiled']
    assert len(cpus) == 1 and not any(r['entity']=='spk286' for r in rows)
    config = (work/'config.tcl').read_text()
    features = dict(re.findall(r'VERILOG_MACRO "(ENABLE_[A-Z0-9_]+)=([01])"',config))
    assert features and all(value == '1' for value in features.values())
    rom = analyze_compiled_image(run)
    artifacts = [run/'compile.log',run/'container-image.txt',run/'manifest.json',
                 run/'git-status.txt',run/'tracked.patch',
                 run/'compile-started.txt',run/'bitstreams.sha256',run/'rbf-info.txt',
                 run/'project-check.log',run/'profile-check.log',run/'timing.log',
                 out/'PCAT-286.fit.rpt',out/'PCAT-286.fit.summary',out/'PCAT-286.sta.rpt',
                 out/'PCAT-286.sta.summary',out/'PCAT-286.map.summary',work/rom['mif']]
    artifacts += sorted(p for p in (run/'timing').rglob('*') if p.is_file())
    for suffix in ('rbf','sof'):
        artifact = out/('PCAT-286.'+suffix)
        assert artifact.stat().st_mtime > (run/'compile-started.txt').stat().st_mtime
    report = dict(status='FLOPPY_FIX_NEW_RBF_MEASURED_HARDWARE_CONFIRMATION_PENDING',
        source_revision=manifest['head'],source_count=len(manifest['source_sha256']),
        snapshot_git_status=(run/'git-status.txt').read_text(),
        manifest_sha256=sha(run/'manifest.json'),generated_changes=changed,
        validation=validation,unchanged_cpu_clock_config_files=len(unchanged),
        compile_warnings=int(completion[0]),resources=measured,delta_from_previous_osd=delta,
        cpu_resources={key:cpus[0][key]['inclusive'] for key in METRICS},
        feature_configuration=features,placement_seed=fitted_seed((work/'PCAT-286.qsf').read_text(),(out/'PCAT-286.fit.rpt').read_text()),
        timing_ns=timing,global_setup_hold_recovery_removal_nonnegative=closed,
        rbf=dict(path=str(out/'PCAT-286.rbf'),bytes=(out/'PCAT-286.rbf').stat().st_size,sha256=sha(out/'PCAT-286.rbf')),
        sof_sha256=sha(out/'PCAT-286.sof'),compiled_rom=rom,
        scope='New Quartus bitstream with source-bound directed floppy, protection and 8-profile checks. Historical speed calibration, full OS regression and physical DOS COPY/remount are separate.',
        artifacts={p.relative_to(run).as_posix():sha(p) for p in artifacts})
    target = ROOT/'docs/evidence/at-floppy-rbf-20261004'
    target.mkdir(exist_ok=False)
    (target/'.gitattributes').write_text('* -text -whitespace\n')
    frozen = {}
    for source in artifacts:
        name = source.relative_to(run)
        destination = target/'run'/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        if source.stat().st_size > 300000:
            destination = destination.with_name(destination.name+'.gz')
            with destination.open('wb') as stream:
                with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as compressed:
                    compressed.write(source.read_bytes())
            assert hashlib.sha256(gzip.decompress(destination.read_bytes())).hexdigest() == sha(source)
        else:
            shutil.copyfile(source,destination)
        frozen[destination.relative_to(target).as_posix()] = sha(destination)
    (target/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    (target/'blocks.md').write_text(table(grouped(rows),measured['placed_alms']))
    shutil.copyfile(Path(__file__),target/'record_fit.py')
    frozen['receipt.json'] = sha(target/'receipt.json')
    frozen['blocks.md'] = sha(target/'blocks.md')
    frozen['record_fit.py'] = sha(target/'record_fit.py')
    (target/'archive-manifest.json').write_text(json.dumps(dict(status=report['status'],artifacts=frozen),indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','resources','delta_from_previous_osd','rbf','global_setup_hold_recovery_removal_nonnegative')},indent=2))

if __name__ == '__main__':
    main()
