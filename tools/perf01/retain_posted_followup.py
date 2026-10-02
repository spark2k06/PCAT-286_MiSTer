#!/usr/bin/env python3
"""Retain completed machine gates and the private AT-refresh attribution."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain(source, dest, names):
    assert not dest.exists(), 'Keep historical receipts intact'
    for name in names:
        target = dest/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
        assert sha(target) == sha(source/name)
    inventory = {str(p.relative_to(dest)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                 for p in sorted(dest.rglob('*')) if p.is_file()}
    (dest/'retained-files.json').write_text(json.dumps(inventory, indent=2)+'\n')
    print('RETAINED', dest, len(inventory))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('promotion', type=Path)
    parser.add_argument('refresh', type=Path)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    promotion, refresh, run, dest = map(Path.resolve, (args.promotion, args.refresh, args.experiment, args.destination))
    assert 'POSTED_MACHINE_SOURCE_GUARD_PASS' in (promotion/'machine-verified.log').read_text()
    assert 'AT_BRIDGE_RESPONSE_TEST_PASS' in (promotion/'bridge-response.log').read_text()
    assert 'AT_CDC_QUARTUS_FRONTEND_PASS' in (promotion/'frontend.log').read_text()
    inputs = json.loads((promotion/'promotion-inputs.json').read_text())
    assert all(sha(promotion/'work'/n) == h for n, h in inputs['changed_sources'].items() | inputs['new_sources'].items())
    names = ['manifest.json', 'promotion-inputs.json', 'machine-verified.log', 'machine.log',
             'bridge-response.log', 'frontend.log',
             'machine-verified/inputs.json', 'machine-verified/entry.rom',
             'machine-verified/spk286_at_machine_tb.sv', 'machine-verified/nasm.log',
             'machine/spk286_at_machine_tb.sv', 'machine/inputs.json', 'machine/div1/run.log',
             'frontend/frontend-inputs.sha256', 'frontend/project-final.log', 'frontend/quartus-final-elaboration.log']
    for mode in (0, 1):
        names += [f'machine-verified/div{mode}/{n}' for n in ('build.log', 'run.log')]
    names += ['work/'+n for n in inputs['changed_sources'] | inputs['new_sources']]
    names += ['work/tools/perf01/'+n for n in ('build_86box_memory_probe.py', 'spk286_memory_probe.hpp')]
    retain(promotion, dest/'promotion', names)
    assert json.loads((refresh/'comparison.json').read_text())['architectural_signature_and_physical_store_guards_pass']
    names = ['comparison.json']
    for arm in ('baseline', 'candidate'):
        identity = json.loads((refresh/arm/'inputs.json').read_text())
        assert all(sha(refresh/arm/n) == h for n, h in identity.items())
        names += [f'{arm}/inputs.json', f'{arm}/sim/spk286_integration/spk286_checkit_workload_tb.sv',
                  f'{arm}/scripts/test_checkit_directed.sh', f'{arm}-build.log']
        names += [f'{arm}/rtl/spk286_integration/{n}.sv' for n in ('spk286_at_arbiter', 'spk286_at_refresh')]
        for workload in ('dhrystone', 'whetstone', 'working_set', 'dhrystone21'):
            names += [f'{arm}-{workload}-refresh-{enabled}.log' for enabled in (0, 1)]
    retain(refresh, dest/'refresh', names)
    retain(run, dest/'integer-partial', ['partial-baseline.json', 'partial-candidate.json',
        'pcat-baseline/spk50/measurement-start.json', 'pcat-candidate/spk50/measurement-start.json',
        'pcat-baseline/probe-run.json', 'pcat-candidate/probe-run.json'])


if __name__ == '__main__':
    main()
