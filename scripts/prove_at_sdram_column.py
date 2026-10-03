#!/usr/bin/env python3
"""Prove the whole actual SDRAM owner/controller against a frozen reference."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'rtl/spk286_integration/spk286_at_mister_sdram_owner.sv'
CONTROLLER = 'rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--candidate-root', type=Path, default=ROOT)
    p.add_argument('--rewrite', choices=('column', 'active-address'), default='column')
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before_owner = (a.reference.resolve() / OWNER).read_text()
    candidate_root = a.candidate_root.resolve()
    after_owner = (candidate_root / OWNER).read_text()
    before_controller = (a.reference.resolve() / CONTROLLER).read_text()
    after_controller = (candidate_root / CONTROLLER).read_text()
    owner_changes = [
        ('.sdram_force_refresh  (SDRAM_FORCE_REFRESH),\n        .use_column_address_input(1\'b1)',
         '.sdram_force_refresh  (SDRAM_FORCE_REFRESH)'),
        ('        // READ/WRITE cannot admit a new command: request_accept requires\n'
         '        // KFSDRAM IDLE. Their column base is the retained address, so this\n'
         '        // removes the late live-command mux without a new register/cycle.\n'
         '        .column_address (address_q[9:1]),\n', '')]
    controller_changes = [
        ("parameter sdram_force_refresh   = 16'd00400,\n"
         '    // The AT owner supplies its retained transaction column separately\n'
         '    // from the live row address used for write admission. Other clients\n'
         '    // retain the original single-address interface behavior.\n'
         "    parameter use_column_address_input = 1'b0",
         "parameter sdram_force_refresh   = 16'd00400"),
        ('    input   logic   [sdram_col_width-1:0]       column_address,\n', ''),
        ('    wire [sdram_col_width-1:0] column_base = use_column_address_input\n'
         '        ? column_address : address[sdram_col_width-1:0];\n', ''),
        ('column_base + access_counter', 'address[sdram_col_width-1:0] + access_counter')]
    if a.rewrite == 'active-address':
        owner_changes = [
            ('    // An idle inactive owner uses the live payload for immediate write\n'
             '    // admission; launched commands use the retained record. Outside IDLE,\n'
             '    // retain the address even after early read completion.\n'
             '    assign kf_address = (kf_idle && !active_q)\n'
             '                      ? request_address[24:1] : address_q[24:1];',
             '    assign kf_address = write_admission ? request_address[24:1] : address_q[24:1];')]
        controller_changes = []
    for candidate, reference, changes in ((after_owner, before_owner, owner_changes),
                                           (after_controller, before_controller, controller_changes)):
        for old, new in changes:
            assert old in candidate, 'Expected column rewrite missing'
            candidate = candidate.replace(old, new)
        assert candidate == reference, 'Other controller/owner behavior changed'
    sources = {}
    for label, root in (('gold', a.reference.resolve()), ('gate', candidate_root)):
        for kind, name in (('owner', OWNER), ('controller', CONTROLLER)):
            source = (root / name).read_text()
            source = re.sub(r'\bKFSDRAM\b', 'KFSDRAM_' + label, source)
            source = source.replace('module spk286_at_mister_sdram_owner',
                                    'module owner_' + label)
            (out / (label + '_' + kind + '.sv')).write_text(source)
            sources[label + '/' + name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    preparation = ('read_verilog -sv -DSYNTHESIS gold_controller.sv gold_owner.sv '
                   'gate_controller.sv gate_owner.sv; hierarchy -check; proc; memory; flatten; opt_clean; ')
    # Match registers and ports, not arbitrary intermediate expressions. For
    # example, cutting kf_idle loses its actual relation to controller state.
    with (out / 'elaboration.log').open('w') as log:
        subprocess.run(['yosys', '-p', preparation + 'write_json elaborated.json; write_rtlil elaborated.il'],
                       cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    modules = json.loads((out / 'elaborated.json').read_text())['modules']
    blacklist = set()
    for label in ('gold', 'gate'):
        module = modules['owner_' + label]
        state_bits = set()
        for cell in module['cells'].values():
            if cell['type'] in ('$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe'):
                state_bits.update(cell['connections']['Q'])
        for name, wire in module['netnames'].items():
            if name not in module['ports'] and not set(wire['bits']).issubset(state_bits):
                blacklist.add(name)
    (out / 'blacklist.txt').write_text('\n'.join(sorted(blacklist)) + '\n')
    command = ('read_rtlil elaborated.il; equiv_make -blacklist blacklist.txt owner_gold owner_gate miter; '
               'hierarchy -top miter; async2sync; opt_clean; equiv_simple; '
               'equiv_induct -seq 5; equiv_status -assert')
    with (out / 'proof.log').open('w') as log:
        subprocess.run(['yosys', '-p', command], cwd=out,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    assert 'Equivalence successfully proven!' in (out / 'proof.log').read_text()
    # Break the actual production binding, not a handwritten model.
    gate_owner = out / 'gate_owner.sv'
    good_source = gate_owner.read_text()
    if a.rewrite == 'column':
        mutant = good_source.replace('.column_address (address_q[9:1])',
                                    ".column_address (address_q[9:1] ^ 9'd1)", 1)
    else:
        mutant = good_source.replace('.address        (kf_address)',
                                    ".address        (kf_address ^ 24'h800000)", 1)
    assert mutant != good_source
    (out / 'mutant_owner.sv').write_text(mutant)
    mutant_command = (preparation.replace('gate_owner.sv', 'mutant_owner.sv') +
                      'equiv_make -blacklist blacklist.txt owner_gold owner_gate miter; '
                      'hierarchy -top miter; async2sync; opt_clean; equiv_simple; '
                      'equiv_induct -seq 5; equiv_status -assert')
    with (out / 'negative-control.log').open('w') as log:
        negative = subprocess.run(['yosys', '-p', mutant_command], cwd=out,
                                  stdout=log, stderr=subprocess.STDOUT)
    assert negative.returncode != 0 and 'unproven $equiv cells' in (out / 'negative-control.log').read_text()
    result = dict(status=('AT_SDRAM_OWNER_COLUMN_EQUIVALENCE_PASS' if a.rewrite == 'column'
                          else 'AT_SDRAM_OWNER_ADDRESS_EQUIVALENCE_PASS'),
                  source_sha256=sources,
                  proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  rewrite=a.rewrite,
                  negative_control='Actual controller binding with an address bit inverted is rejected.',
                  unchanged='All owner/controller source except the explicit address selection rewrite, including reset declarations, counters, timings, states and all other pins.',
                  scope='Whole actual owner and controller sampled-clock sequential equivalence; same public inputs and matched registers. async2sync models sampled reset; asynchronous reset declarations are unchanged. No new pipeline stage or timing assumption.')
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
