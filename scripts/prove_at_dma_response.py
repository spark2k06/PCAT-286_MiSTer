#!/usr/bin/env python3
"""Prove DMA response qualification using the actual memory-port logic.

No reset/state/input assumptions: even arbitrary memory-port state cannot
accept and complete a DMA command concurrently. The negative control must fail.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PORT = 'rtl/spk286_integration/spk286_at_mister_memory_port.sv'
MACHINE = 'rtl/spk286_integration/spk286_at_machine.sv'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    text = (ROOT / PORT).read_text()
    ports = re.findall(r'^\s*(input|output)\s+logic\s*(\[[^\]]+\])?\s*(\w+)\s*[,)]', text, re.M)
    assert len(ports) > 40
    machine = (ROOT / MACHINE).read_text()
    expression = re.search(r'wire dma_memory_response_valid\s*=\s*(.*?);', machine, re.S)[1]
    assert machine.count('(dma_memory_response_valid)') == 1
    assert '.DMA_REGISTERED_MEMORY_COMPLETION(1\'b1)' in (ROOT / 'PCAT-286.sv').read_text()
    signals, connections, inputs = [], [], []
    for direction, width, name in ports:
        signals.append(f'wire {width or ""} {name};')
        connections.append(f'.{name}({name})')
        if direction == 'input':
            inputs.append(f'input wire {width or ""} {name}')
    wrapper = 'module dma_response_miter(\n' + ',\n'.join(inputs + [
        'input wire dma_memory_accept_q', 'output wire equivalent',
        'output wire mutually_exclusive']) + ');\n'
    # Inputs already occur in the wrapper's port declarations.
    wrapper += '\n'.join(s for s in signals if not any(
        re.search(r'\b' + n + r';$', s) for d, w, n in ports if d == 'input')) + '\n'
    wrapper += 'spk286_at_mister_memory_port dut(' + ','.join(connections) + ');\n'
    wrapper += "localparam DMA_REGISTERED_MEMORY_COMPLETION = 1'b1;\n"
    wrapper += 'wire dma_memory_ready = dma_ready;\nwire dma_memory_accept = dma_accept;\n'
    wrapper += 'wire candidate = ' + expression + ';\n'
    wrapper += 'wire reference = dma_ready && (dma_accept || dma_memory_accept_q);\n'
    wrapper += 'assign equivalent = candidate == reference;\n'
    wrapper += 'assign mutually_exclusive = !(dma_accept && dma_ready);\nendmodule\n'
    (out / 'miter.sv').write_text(wrapper)
    (out / 'memory_port.sv').write_bytes((ROOT / PORT).read_bytes())
    commands = ('read_verilog -sv -DSYNTHESIS memory_port.sv miter.sv; '
                'prep -top dma_response_miter; flatten; '
                'sat -seq 1 -verify -prove equivalent 1 -prove mutually_exclusive 1 '
                '-show-inputs -show-outputs')
    with (out / 'proof.log').open('w') as log:
        subprocess.run(['yosys', '-p', commands], cwd=out,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    assert 'SUCCESS!' in (out / 'proof.log').read_text()
    # A same-cycle acceptance must not itself advertise completed read data.
    mutant = wrapper.replace('wire candidate = ' + expression + ';',
                             'wire candidate = dma_ready && dma_memory_accept_q || dma_accept;')
    (out / 'mutant.sv').write_text(mutant)
    with (out / 'negative-control.log').open('w') as log:
        result = subprocess.run(['yosys', '-p', commands.replace('miter.sv', 'mutant.sv')],
                                cwd=out, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode != 0 and 'proof did fail' in (out / 'negative-control.log').read_text()
    sources = (PORT, MACHINE, 'PCAT-286.sv', 'scripts/prove_at_dma_response.py')
    receipt = dict(status='AT_DMA_REGISTERED_RESPONSE_EQUIVALENCE_PASS',
                   assumptions=[], negative_control='counterexample required and observed',
                   source_sha256={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources})
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
