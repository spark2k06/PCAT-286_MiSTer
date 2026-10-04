#!/usr/bin/env python3
"""Bind a new public-selector bitstream to directed evidence and fitted cost.

This records measured physical timing separately from functional validation.
It does not certify hardware operation or historical cycle accuracy.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from analyze_pcat_resources import parse, grouped, table, METRICS
from audit_fixed50_fit import CORNERS, GROUPS, resources, fitted_seed
from check_sync_microcode_image import analyze_compiled_image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--machine', type=Path, required=True)
    p.add_argument('--compatibility', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run, output = a.run.resolve(), a.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    work, reports, out = run/'work', run/'timing', run/'work/output_files'
    assert sha(work/'scripts/record_p06_osd_fit.py') == sha(Path(__file__))
    manifest = json.loads((run/'manifest.json').read_text())
    started = datetime.fromisoformat((run/'compile-started.txt').read_text().strip())
    log = (run/'compile.log').read_text()
    assert re.search(r'Full Compilation was successful\. 0 errors', log)
    generated = {}
    for name, expected in manifest['source_sha256'].items():
        name = name.replace('\\', '/')
        actual = sha(work/name)
        if actual != expected:
            assert name == 'build_id.v', 'Frozen source changed: ' + name
            value = '`define BUILD_DATE "' + started.strftime('%y%m%d') + '"'
            assert (work/name).read_text() == value
            assert 'Generated: /build/build_id.v: ' + value in log
            generated[name] = dict(before=expected, compiled=actual, value=value)
    bindings = {}
    for name, path, status in (
            ('machine', a.machine, 'AT_SPEED_PROFILES_DIRECTED_PASS'),
            ('compatibility', a.compatibility, 'PASS')):
        receipt = json.loads(path.read_text())
        assert receipt['status'] == status, name
        for source, expected in receipt['source_sha256'].items():
            assert sha(work/source) == expected, 'Fit differs from ' + name + ': ' + source
        bindings[name] = dict(path=str(path), sha256=sha(path), scope=receipt['scope'])
    compatibility = json.loads(a.compatibility.read_text())
    assert len(compatibility['units']) == 26 and compatibility['profiles'] == list(range(8))
    assert not compatibility['failures'] and not compatibility['source_changes']
    assert len(json.loads(a.machine.read_text())['results']) == 8

    counts = [line.split() for line in (reports/'path_counts.txt').read_text().splitlines()]
    expected = {(c, g, k) for c in CORNERS for g in GROUPS for k in ('setup', 'hold')}
    expected |= {(c, 'global', k) for c in CORNERS for k in ('recovery', 'removal')}
    assert {(c, g, k) for c, g, k, _, _ in counts} == expected
    timing = {c: {} for c in CORNERS}
    for corner, group, kind, count, worst in counts:
        timing[corner].setdefault(group, {})[kind] = float(worst) if int(count) else None
    global_closed = all(timing[c]['global'][k] is not None and
                        timing[c]['global'][k] >= 0 for c in CORNERS for k in ('setup', 'hold'))
    # Recovery/removal are also part of the recorded global timing conclusion.
    global_closed &= all(timing[c]['global'][k] is None or timing[c]['global'][k] >= 0
                         for c in CORNERS for k in ('recovery', 'removal'))
    rbf, sof = out/'PCAT-286.rbf', out/'PCAT-286.sof'
    for artifact in (rbf, sof):
        assert artifact.stat().st_size and artifact.stat().st_mtime > (run/'compile-started.txt').stat().st_mtime
    measured = resources(out)
    baseline = json.loads((ROOT/'docs/evidence/pcat-resources-20261004/resources.json').read_text())
    mapping = dict(equivalent_alms='alm_needed', placed_alms='alm_placed',
                   memory_bits='memory_bits', m10k='m10k', dsp='dsp')
    delta = {name: measured[name]-baseline['global'][key] for name, key in mapping.items()}
    delta['registers'] = measured['registers']-baseline['global']['registers']-baseline['global']['io_registers']
    delta['plls'] = measured['plls']-3
    report = out/'PCAT-286.fit.rpt'
    rows = parse(report)
    assert sum(row['entity'] == 'spk286_profiled' for row in rows) == 1
    assert not any(row['entity'] == 'spk286' for row in rows), 'Unexpected second CPU'
    blocks = grouped(rows)
    cpu = next(row for row in rows if row['entity'] == 'spk286_profiled' and
               row['path'].endswith('|spk286_profiled:cpu'))
    cpu_resources = {name: cpu[name]['inclusive'] for name in METRICS}
    seed = fitted_seed((work/'PCAT-286.qsf').read_text(), report.read_text())
    config = (work/'config.tcl').read_text()
    features = dict(re.findall(r'VERILOG_MACRO "(ENABLE_[A-Z0-9_]+)=([01])"', config))
    compiled_rom = analyze_compiled_image(run)
    result = dict(status='NEW_OSD_RBF_MEASURED_NOT_HARDWARE_ACCEPTED',
        run=str(run), source_revision=manifest['head'], source_count=len(manifest['source_sha256']),
        manifest_sha256=sha(run/'manifest.json'), generated_sources=generated,
        validation=bindings, resources=measured, delta_from_selected_fixed50=delta,
        cpu_resources=cpu_resources, feature_configuration=features, placement_seed=seed,
        timing_ns=timing, global_setup_hold_recovery_removal_nonnegative=global_closed,
        rbf=dict(path=str(rbf), bytes=rbf.stat().st_size, sha256=sha(rbf)),
        sof_sha256=sha(sof), compiled_rom=compiled_rom,
        artifact_sha256={str(path.relative_to(run)):sha(path) for path in
            [run/'compile.log', run/'container-image.txt', run/'profile-check.log',
             run/'project-check.log', report, out/'PCAT-286.fit.summary',
             *sorted(path for path in reports.rglob('*') if path.is_file())]},
        scope='New fitted bitstream, all 8 functional profiles and selected full-CPU directed units. Physical STA is measured, historical intervals remain provisional, hardware and complete OS regression remain separate.',
        auditor_sha256=sha(Path(__file__)))
    output.mkdir(parents=True)
    (output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    (output/'blocks.md').write_text(table(blocks, measured['placed_alms']))
    (output/'entities.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(result['status'])
    print(json.dumps(dict(resources=measured, delta=delta, cpu=cpu_resources,
                         timing=timing, rbf=result['rbf']), indent=2))


if __name__ == '__main__':
    main()
