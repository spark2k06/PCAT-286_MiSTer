#!/usr/bin/env python3
"""Prove the actual CPU protection expression against the pre-P05 contract.

Pure combinational SAT proof: no FPGA synthesis, timing or RBF generation.
All controls, both 16-bit limits and the 16-bit offset are unconstrained.
The expected expression is frozen below, independent of the candidate RHS.
"""
import argparse
import hashlib
import re
import subprocess
from pathlib import Path

REFERENCE = """
operand_request && operand_select_rm && !operand_register_direct &&
!protected_descriptor_access && !protected_tss_access && !protected_event_access &&
!io_transfer && !vector_request &&
(protected_call_stack_access ?
 (service_segment != 2'd2 ||
  (protected_call_stack_expand_down ?
   ({1'b0, service_offset} <= {1'b0, protected_call_stack_limit} ||
    ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > 17'h0FFFF)) :
   ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > {1'b0, protected_call_stack_limit}))) :
 (protected_segment_is_loaded &&
  (!protected_segment_is_valid || !protected_segment_is_present ||
   (protected_segment_is_code ? (!protected_segment_is_readable || operand_write) :
    (stack_request ? (!protected_segment_is_writable || service_segment != 2'd2) :
     (operand_write && !protected_segment_is_writable))) ||
   (protected_segment_is_expand_down ?
    ({1'b0, service_offset} <= {1'b0, selected_segment_limit} ||
     ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > 17'h0FFFF)) :
    ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > {1'b0, selected_segment_limit})))))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / 'vendor/spk286/rtl/spk286.sv'
    text = source.read_text()
    block = re.search(r'`ifdef SPK286_P05_PARALLEL_LIMIT_CHECK(.*?)`else(.*?)`endif', text, re.S)
    if not block:
        raise SystemExit('Expected isolated P05 opt-in block')
    matches = re.findall(r'assign\s+protected_access_fault\s*=\s*(.*?);', block[1], re.S)
    if len(matches) != 1:
        raise SystemExit('Expected one actual CPU protected_access_fault assignment')
    candidate = matches[0]
    unchanged = re.search(r'assign\s+protected_access_fault\s*=\s*(.*?);', block[2], re.S)
    if not unchanged or re.sub(r'\s', '', unchanged[1]) != re.sub(r'\s', '', REFERENCE):
        raise SystemExit('Non-P05 protection expression differs from the frozen contract')
    widths = {'service_segment': 2, 'service_offset': 16,
              'protected_call_stack_limit': 16, 'selected_segment_limit': 16}
    # Strip numeric literals before inferring identifier ports. A new helper
    # net cannot silently become an independent input and make a proof pass.
    def identifiers(expr):
        return set(re.findall(r'\b[a-zA-Z_]\w*\b',
                   re.sub(r"\d+'[bdhoBDHO][0-9a-fA-F_xXzZ]+", '', expr)))
    names = identifiers(REFERENCE)
    if identifiers(candidate) != names:
        raise SystemExit('CPU expression inputs changed; review the proof harness')
    ports = ['input wire ' + (f'[{widths[n]-1}:0] ' if n in widths else '') + n
             for n in sorted(names)] + ['output wire equivalent']
    wrapper = 'module p05_limit_miter(\n' + ',\n'.join(ports) + ');\n'
    wrapper += f'wire candidate = {candidate};\nwire reference = {REFERENCE};\n'
    wrapper += 'assign equivalent = (candidate == reference);\nendmodule\n'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'miter.sv').write_text(wrapper)
    (output / 'source.sha256').write_text(hashlib.sha256(source.read_bytes()).hexdigest() + '\n')
    commands = ('read_verilog -sv miter.sv; prep -top p05_limit_miter; '
                'sat -verify -prove equivalent 1 -show-inputs -show-outputs')
    with (output / 'proof.log').open('w') as log:
        subprocess.run(['yosys', '-p', commands], cwd=output,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    if 'SUCCESS!' not in (output / 'proof.log').read_text():
        raise SystemExit('SAT success marker missing')
    # Negative control: allow a word to begin exactly at the selected limit.
    # The prover must find a counterexample, not accept a vacuous harness.
    boundary = '(!operand_byte && service_offset == selected_segment_limit)'
    if candidate.count(boundary) != 1:
        raise SystemExit('Negative-control anchor changed; review the harness')
    mutant = wrapper.replace(candidate, candidate.replace(boundary, "1'b0"), 1)
    (output / 'mutant.sv').write_text(mutant)
    with (output / 'negative-control.log').open('w') as log:
        result = subprocess.run(['yosys', '-p', commands.replace('miter.sv', 'mutant.sv')],
                                cwd=output, stdout=log, stderr=subprocess.STDOUT)
    negative_log = (output / 'negative-control.log').read_text()
    if result.returncode == 0 or 'proof did fail' not in negative_log:
        raise SystemExit('Expected SAT counterexample for the word-limit mutation')
    print(f'P05_LIMIT_EQUIVALENCE_PASS input_bits={sum(widths.get(n, 1) for n in names)} all_inputs=1')
    print('P05_LIMIT_NEGATIVE_CONTROL_PASS word_at_limit_rejected=1')


if __name__ == '__main__':
    main()
