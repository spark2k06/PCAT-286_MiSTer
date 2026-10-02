"""Retain the completed posting prototype checks, excluding live DOS runs."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    run, dest = args.experiment.resolve(), args.destination.resolve()
    assert not dest.exists(), 'Preserve the old receipt'
    manifest = json.loads((run/'source-manifest.json').read_text())
    assert all(sha(ROOT/n) == h for n, h in manifest['original_sha256'].items())
    for arm in ('baseline', 'candidate'):
        assert all(sha(run/arm/n) == h for n, h in manifest['variant_sha256'][arm].items())
    names = ['source-manifest.json', 'candidate.patch', 'directed-comparison.json',
             'review-final.log', 'lint.log', 'directed-copy-receipt.json']
    for arm in ('baseline', 'candidate'):
        names += [str(p.relative_to(run)) for p in (run/('directed-'+arm)).iterdir() if p.is_file()]
        names += [f'probe-{arm}/{n}' for n in ('build-manifest.json', 'pcat_memory_timing.sv',
                                             'spk286_backend.cpp', 'spk286_memory_probe.hpp', 'build.log')]
    names += ['validation-physical/sources.sha256', 'validation-physical/run.log',
              'validation-physical/verified.log', 'validation-physical/build.log',
              'validation-cache/inputs.json', 'validation-cache/run.log',
              'validation-cache/build.log', 'validation-cache/posted_cache_tb.sv',
              'isolated-map-verified/mapping.json', 'isolated-map.log', 'isolated-map-final.log']
    for enabled in (0, 1):
        names += [f'isolated-map-verified/enable-{enabled}/{n}' for n in (
            'map.log', 'posted_write_cost.sv', 'posted_cost.qsf', 'posted_cost.qpf',
            'spk286_at_posted_write_buffer.sv', 'output_files/posted_cost.map.rpt',
            'output_files/posted_cost.map.summary')]
    for name in names:
        target = dest/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run/name, target)
        assert sha(target) == sha(run/name)
    receipt = {'source_guard_pass': True, 'strict_module_lint_pass': True,
               'physical_checks': 495, 'cache_checks': 145,
               'scope': 'Completed directed controls and isolated map. No completed DOS score, full regression, fitter/timing or hardware acceptance.',
               'initial_launch_output_note': 'Shell expansion resolved directed output paths before changing directory. Original D:/GitHub/directed-* outputs were left intact; files copied byte for byte into the private experiment.',
               'mapping_parser_note': 'First two attempts mapped the control successfully but rejected report field names; final parser uses the verified Quartus 17.0.2 labels. No RTL expectation changed.'}
    (dest/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    inventory = {str(p.relative_to(dest)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                 for p in sorted(dest.rglob('*')) if p.is_file()}
    (dest/'retained-files.json').write_text(json.dumps(inventory, indent=2)+'\n')
    print('POSTED_PROTOTYPE_EVIDENCE_RETAINED', len(inventory))


if __name__ == '__main__':
    main()
