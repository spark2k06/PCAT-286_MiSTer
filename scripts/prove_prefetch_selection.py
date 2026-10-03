#!/usr/bin/env python3
"""Prove the actual prefetch read rewrite and legal-pointer induction step."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'vendor/spk286/rtl/spk286_prefetch_queue.sv'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before, after = a.reference.read_text(), (ROOT / SOURCE).read_text()
    reference = re.search(r'    assign consume_data = .*?;\n', before, re.S)[0]
    block = re.search(r'    // Decode the six legal head positions.*?storage_q\[5\]\);\n', after, re.S)[0]
    assert after.replace(block, reference, 1) == before, 'Other queue logic changed'
    pointer = re.search(r'    function automatic \[2:0\] increment_pointer.*?endfunction', after, re.S)[0]
    assert re.findall(r'head_q\s*<=\s*(.*?);', after) == ["3'd0", 'increment_pointer(head_q)']
    assert 'if (reset || flush) begin' in after
    candidate = block[block.index('    (* keep *)'):]
    wrapper = '''module prefetch_selection_miter(
input wire [47:0] contents, input wire [2:0] head_q,
output wire equivalent, output wire legal_step);
wire [7:0] storage_q [0:5];
genvar i;
generate for (i=0;i<6;i=i+1) begin
assign storage_q[i] = contents[i*8 +: 8];
end endgenerate
wire [7:0] consume_data;
'''
    wrapper += pointer + '\n' + candidate
    wrapper += 'wire [7:0] reference_data = storage_q[head_q];\n'
    wrapper += "assign equivalent = (head_q >= 3'd6) || consume_data == reference_data;\n"
    wrapper += "assign legal_step = (head_q >= 3'd6) || increment_pointer(head_q) < 3'd6;\n"
    wrapper += 'endmodule\n'
    (out / 'miter.sv').write_text(wrapper)
    command = ('read_verilog -sv miter.sv; prep -top prefetch_selection_miter; '
               'memory_map; opt; sat -verify -prove equivalent 1 -prove legal_step 1 '
               '-show-inputs -show-outputs')
    with (out / 'proof.log').open('w') as log:
        subprocess.run(['yosys', '-p', command], cwd=out,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    assert 'SUCCESS!' in (out / 'proof.log').read_text()
    mutant = wrapper.replace('& storage_q[0])', '& storage_q[1])', 1)
    assert mutant != wrapper
    (out / 'mutant.sv').write_text(mutant)
    with (out / 'negative-control.log').open('w') as log:
        result = subprocess.run(['yosys', '-p', command.replace('miter.sv', 'mutant.sv')],
                                cwd=out, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode != 0 and 'proof did fail' in (out / 'negative-control.log').read_text()
    result = dict(status='PREFETCH_SELECTION_EQUIVALENCE_PASS',
                  invariant='Reset/flush head=0; actual increment_pointer preserves head<6.',
                  unchanged='All queue state, handshake and storage writes byte-identical.',
                  negative_control='wrong head byte rejected',
                  reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                  proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
