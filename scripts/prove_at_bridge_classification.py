#!/usr/bin/env python3
"""Prove the actual bridge's retained I/O/INTA classification rewrite."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'rtl/spk286_integration/spk286_at_bus_bridge.sv'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--candidate-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before_path = args.reference.resolve() / SOURCE
    after_path = args.candidate_root.resolve() / SOURCE
    before = before_path.read_text()
    after = after_path.read_text()
    changes = [
        ('    // Early memory is confined to IDLE; I/O and INTA use retained phases.\n'
         '    // Keep their qualifiers independent of the live memory-width decode.\n'
         '    wire retained_transaction_valid = (state_q == STATE_ADDRESS) ||\n'
         '                                      (state_q == STATE_COMMAND) ||\n'
         '                                      (state_q == STATE_WAIT);\n'
         '    assign at_valid          = early_memory_address || retained_transaction_valid;',
         '    assign at_valid          = early_memory_address || (state_q == STATE_ADDRESS) ||\n'
         '                               (state_q == STATE_COMMAND) ||\n'
         '                               (state_q == STATE_WAIT);'),
        ('assign at_io             = retained_transaction_valid && request_is_io;',
         'assign at_io             = at_valid && !early_memory_address && request_is_io;'),
        ('assign at_inta           = retained_transaction_valid && request_is_inta;',
         'assign at_inta           = at_valid && !early_memory_address && request_is_inta;')]
    recovered = after
    for candidate, reference in changes:
        assert recovered.count(candidate) == 1
        recovered = recovered.replace(candidate, reference, 1)
    assert recovered == before, 'Other bridge source changed'
    modes = []
    for sample in (0, 1):
        case = out / f'sample-{sample}'
        case.mkdir()
        for label, source in [('gold', before), ('gate', after)]:
            source = source.replace('module spk286_at_bus_bridge', 'module bridge_' + label, 1)
            (case / (label + '.sv')).write_text(source)
        preparation = (f'read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
            f'chparam -set COMPLETE_ON_CPU_SAMPLE {sample} bridge_gold bridge_gate; '
            'hierarchy -check; proc; memory; flatten; opt_clean; ')
        with (case / 'elaboration.log').open('w') as log:
            subprocess.run(['yosys', '-p', preparation + 'write_json elaborated.json; write_rtlil elaborated.il'],
                           cwd=case, stdout=log, stderr=subprocess.STDOUT, check=True)
        modules = json.loads((case / 'elaborated.json').read_text())['modules']
        blacklist = set()
        for label in ('gold', 'gate'):
            module = modules['bridge_' + label]
            state_bits = set()
            for cell in module['cells'].values():
                if cell['type'] in ('$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe'):
                    state_bits.update(cell['connections']['Q'])
            for name, wire in module['netnames'].items():
                if name not in module['ports'] and not set(wire['bits']).issubset(state_bits):
                    blacklist.add(name)
        (case / 'blacklist.txt').write_text('\n'.join(sorted(blacklist)) + '\n')
        command = ('read_rtlil elaborated.il; equiv_make -blacklist blacklist.txt bridge_gold bridge_gate miter; '
                   'hierarchy -top miter; async2sync; opt_clean; equiv_simple; '
                   'equiv_induct -seq 4; equiv_status -assert')
        with (case / 'proof.log').open('w') as log:
            subprocess.run(['yosys', '-p', command], cwd=case, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        assert 'Equivalence successfully proven!' in (case / 'proof.log').read_text()
        good = (case / 'gate.sv').read_text()
        mutant = good.replace('assign at_io             = retained_transaction_valid && request_is_io;',
                              'assign at_io             = at_valid && request_is_io;', 1)
        assert mutant != good
        (case / 'mutant.sv').write_text(mutant)
        negative_command = (preparation.replace('gate.sv', 'mutant.sv') +
            'equiv_make -blacklist blacklist.txt bridge_gold bridge_gate miter; '
            'hierarchy -top miter; async2sync; opt_clean; equiv_simple; '
            'equiv_induct -seq 4; equiv_status -assert')
        with (case / 'negative-control.log').open('w') as log:
            negative = subprocess.run(['yosys', '-p', negative_command], cwd=case,
                                      stdout=log, stderr=subprocess.STDOUT)
        assert negative.returncode != 0 and 'unproven $equiv cells' in (case / 'negative-control.log').read_text()
        modes.append(dict(complete_on_cpu_sample=sample,
                          proof='Whole actual bridge; all public outputs unmasked and actual register comparisons.',
                          negative='Actual I/O qualifier without early-memory exclusion is rejected.'))
    result = dict(status='AT_BRIDGE_CLASSIFICATION_EQUIVALENCE_PASS', modes=modes,
        reference_sha256=hashlib.sha256(before_path.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(after_path.read_bytes()).hexdigest(),
        proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        unchanged='All bridge source except the retained-valid Boolean factorization and I/O/INTA qualifiers. No registers, timing parameters, states, reset declarations, payload, acceptance or completion changes.',
        scope='Whole production bridge for both completion modes, sampled-clock reset through async2sync, same inputs and matched actual registers. No protocol assumption or output masking.')
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
