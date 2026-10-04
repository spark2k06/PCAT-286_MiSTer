#!/usr/bin/env python3
"""Prove all original bridge outputs unchanged when the new policy is MAX.

Use an immutable pre-profile source tree. New timing inputs are tied to MAX;
every original input/output and actual original state register is compared.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAME = 'rtl/spk286_integration/spk286_at_bus_bridge.sv'


def run(directory, script, filename, required=True):
    with (directory / filename).open('w') as log:
        result = subprocess.run(['yosys', '-p', script], cwd=directory,
                                stdout=log, stderr=subprocess.STDOUT)
    if required and result.returncode:
        raise RuntimeError(f'Yosys failed: {directory / filename}')
    return result.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before_path, after_path = a.reference.resolve() / NAME, ROOT / NAME
    before, after = before_path.read_text(), after_path.read_text()
    # These are constant input connections for the proof, not a synthesized
    # RTL optimization or a replacement transaction implementation.
    for declaration in ('    input  logic         timing_historical,\n',
                        '    input  logic         timing_cpu_boundary,\n',
                        '    output logic         timing_deadline_miss,\n'):
        assert after.count(declaration) == 1, declaration
        after = after.replace(declaration, '')
    after = after.replace('wire historical = timing_historical === 1\'b1;',
                          "wire historical = 1'b0;\n    wire timing_cpu_boundary = 1'b1;\n    wire timing_deadline_miss;")
    assert 'timing_historical' not in after
    modes = []
    for sample in (0, 1):
        directory = output / f'sample-{sample}'
        directory.mkdir()
        for label, source in (('gold', before), ('gate', after)):
            source = source.replace('module spk286_at_bus_bridge', f'module bridge_{label}', 1)
            (directory / f'{label}.sv').write_text(source)
        prepare = ('read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
                   f'chparam -set COMPLETE_ON_CPU_SAMPLE {sample} bridge_gold bridge_gate; '
                   'hierarchy -check; proc; memory; flatten; opt; ')
        run(directory, prepare + 'write_json elaborated.json; write_rtlil elaborated.il;', 'elaboration.log')
        modules = json.loads((directory / 'elaborated.json').read_text())['modules']
        blacklist = set()
        for label in ('gold', 'gate'):
            m = modules['bridge_' + label]
            state_bits = set()
            for cell in m['cells'].values():
                if cell['type'] in ('$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe'):
                    state_bits.update(cell['connections']['Q'])
            for name, net in m['netnames'].items():
                if name not in m['ports'] and not set(net['bits']).issubset(state_bits):
                    blacklist.add(name)
        (directory / 'blacklist.txt').write_text('\n'.join(sorted(blacklist)) + '\n')
        proof = ('equiv_make -blacklist blacklist.txt bridge_gold bridge_gate miter; '
                 'hierarchy -top miter; async2sync; opt_clean; equiv_simple; '
                 'equiv_induct -seq 4; equiv_status -assert')
        run(directory, 'read_rtlil elaborated.il; ' + proof, 'proof.log')
        assert 'Equivalence successfully proven!' in (directory / 'proof.log').read_text()
        gate = (directory / 'gate.sv').read_text()
        assert gate.count('assign cpu_ready         = at_response_valid;') == 1
        mutant = gate.replace('assign cpu_ready         = at_response_valid;',
                              'assign cpu_ready         = !at_response_valid;')
        (directory / 'mutant.sv').write_text(mutant)
        failed = run(directory, prepare.replace('gate.sv', 'mutant.sv') + proof,
                     'negative-control.log', required=False)
        assert failed and 'unproven $equiv cells' in (directory / 'negative-control.log').read_text()
        modes.append({'complete_on_cpu_sample': sample, 'proof': 'PASS', 'negative_control': 'rejected'})
    receipt = dict(status='AT_PROFILE_BRIDGE_MAX_EQUIVALENCE_PASS', modes=modes,
        scope='Whole actual bridge, all original inputs/outputs and matching original registers; historical input tied to MAX. No protocol assumptions, output masks or artificial replacement FSM.',
        reference_sha256=hashlib.sha256(before_path.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(after_path.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
