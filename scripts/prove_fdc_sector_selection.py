#!/usr/bin/env python3
"""Prove the exact FDC sector-preparation rewrite for all two-state inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'rtl/common/floppy.v'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--candidate-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    reference_path = args.reference.resolve() / SOURCE
    candidate_path = args.candidate_root.resolve() / SOURCE
    reference = reference_path.read_text()
    candidate = candidate_path.read_text()
    match = re.search(r'else if\(state == S_PREPARE_COUNT\)\s+logical_sector <= (.+);', reference)
    assert match, 'Production preparation assignment missing'
    expression = match[1]
    expected = "(head[selected_drive[0]] ? {8'd0, media_sectors_per_track[selected_drive[0]]} : 16'd0) + {8'd0, sector[selected_drive[0]]} - 16'd1"
    assert expression == expected, 'Reference arithmetic changed'
    expressions = [expression.replace('selected_drive[0]', str(drive))
                   for drive in (0, 1)]
    declarations = ''.join(f'wire [15:0] logical_sector_prepare{drive} = {expr};\n'
                           for drive, expr in enumerate(expressions))
    comment = ('// Calculate each drive\'s sector before the late command-drive selection.\n'
               '// Preserve the capture edge without adding a register or cycle.\n')
    selection = 'selected_drive[0] ? logical_sector_prepare1 : logical_sector_prepare0'
    reconstructed = candidate.replace(comment + declarations, '', 1).replace(
        'logical_sector <= ' + selection + ';',
        'logical_sector <= ' + expression + ';', 1)
    assert reconstructed == reference, 'Other controller source changed'
    assert candidate.count(comment + declarations) == 1
    assert candidate.count('logical_sector <= ' + selection + ';') == 1

    # The only sequential change is replacing an RHS by a universally equal
    # combinational expression. The source guard keeps every register, update
    # condition, reset, command, FIFO and public connection unchanged.
    header = '''module miter(input [1:0] head, input [7:0] spt0, spt1, sec0, sec1,
input drive, output same, output [15:0] gold, gate);
wire [1:0] selected_drive = {1'b0, drive};
wire [7:0] media_sectors_per_track [0:1];
wire [7:0] sector [0:1];
assign media_sectors_per_track[0] = spt0;
assign media_sectors_per_track[1] = spt1;
assign sector[0] = sec0;
assign sector[1] = sec1;
'''
    harness = (header + declarations + f'assign gold = {expression};\n'
               f'assign gate = {selection};\nassign same = gold == gate;\nendmodule\n')
    (out / 'math.sv').write_text(harness)
    command = ('read_verilog -sv math.sv; prep -top miter; flatten; memory_map; '
               'opt; sat -verify -prove same 1 -show-inputs -show-outputs')
    with (out / 'proof.log').open('w') as log:
        subprocess.run(['yosys', '-p', command], cwd=out, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    assert 'SAT proof finished - no model found: SUCCESS!' in (out / 'proof.log').read_text()
    mutant = harness.replace('wire [15:0] logical_sector_prepare1 = ' + expressions[1],
        'wire [15:0] logical_sector_prepare1 = (' + expressions[1] + ") ^ 16'd1", 1)
    assert mutant != harness
    (out / 'mutant.sv').write_text(mutant)
    with (out / 'negative-control.log').open('w') as log:
        negative = subprocess.run(['yosys', '-p', command.replace('math.sv', 'mutant.sv')],
                                  cwd=out, stdout=log, stderr=subprocess.STDOUT)
    assert negative.returncode != 0 and 'proof did fail' in (out / 'negative-control.log').read_text()
    result = dict(status='FDC_PREPARE_SECTOR_COMBINATIONAL_EQUIVALENCE_PASS',
        reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        unchanged='All controller source except two combinational preparations and the final drive mux, including every register, reset, capture condition, state, command, FIFO and public connection.',
        scope='Actual production expression; all known two-state drive/head/sector/geometry inputs, including zero and 16-bit wrap. Universally equal RHS plus an exact source guard; not a whole-module formal proof or physical fit.',
        negative_control='Actual drive-1 preparation expression with low output bit inverted is rejected.')
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
