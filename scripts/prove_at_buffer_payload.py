#!/usr/bin/env python3
"""Prove actual buffer transitions with idle payload independent of admission.

Every handshake/response/state output is compared unconditionally. Only the
outgoing payload is qualified by out_valid, its existing transaction boundary.
Actual FF descriptors and RAM interfaces form a complete one-step invariant;
there are no assumptions about protocol inputs or reachable control states.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = frozenset(('out_owner', 'out_write', 'out_refresh', 'out_code_fetch',
                     'out_burst', 'out_cycle_class', 'out_address',
                     'out_byte_enable', 'out_data_out'))
CASES = (
    ('read-default', 'spk286_at_sdram_read_buffer', {'LINE_COUNT': 64, 'SYNC_TAGS': 0}),
    ('read-production', 'spk286_at_sdram_read_buffer', {'LINE_COUNT': 512, 'SYNC_TAGS': 1}),
    ('read-disabled', 'spk286_at_sdram_read_buffer', {'LINE_COUNT': 512, 'SYNC_TAGS': 1, 'ENABLE': 0}),
    ('data-production', 'spk286_at_sdram_data_buffer', {}),
    ('data-disabled', 'spk286_at_sdram_data_buffer', {'ENABLE': 0}),
    ('posted', 'spk286_at_posted_write_buffer', {}),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(case, name, command, positive=True):
    with (case / (name + '.log')).open('w') as log:
        result = subprocess.run(['timeout', '300', 'yosys', '-Q', '-p', command],
                                cwd=case, stdout=log, stderr=subprocess.STDOUT)
    text = (case / (name + '.log')).read_text()
    if positive:
        assert result.returncode == 0, (case.name, name, result.returncode)
    return result.returncode, text


def cell_span(body, celltype, name):
    escaped = name if name.startswith('$') else '\\' + name
    start = body.index('  cell ' + celltype + ' ' + escaped + '\n')
    while start > 0:
        previous = body.rfind('\n', 0, start - 1) + 1
        if not body[previous:start].startswith('  attribute '):
            break
        start = previous
    return start, body.index('  end\n', start) + len('  end\n')


def identifier(name):
    result = re.sub(r'[^a-zA-Z_0-9]', '_scope_', name)
    assert re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', result), name
    return result


def abstract(case):
    modules = json.loads((case / 'elaborated.json').read_text())['modules']
    rtlil = (case / 'elaborated.il').read_text()
    descriptors, memories = {}, {}
    for label in ('gold', 'gate'):
        name = 'buffer_' + label
        module = modules[name]
        start = rtlil.index('module \\' + name + '\n')
        end = rtlil.index('\nend\n', start)
        body = rtlil[start:end]
        ordinal = max(int(p) for p in re.findall(r'\b(?:input|output) (\d+) ', body))
        extras = []
        descriptors[label], memories[label] = {}, {}
        for cellname, cell in module['cells'].items():
            celltype, ports = cell['type'], cell['connections']
            if celltype != '$mem_v2' and 'Q' not in ports:
                continue
            begin, finish = cell_span(body, celltype, cellname)
            block = body[begin:finish]
            connections = {p: re.search(r'^    connect \\' + re.escape(p) + r' (.+)$', block, re.M).group(1)
                           for p in ports}
            if celltype == '$mem_v2':
                memories[label][cellname] = {'parameters': cell['parameters'],
                                             'port_widths': {p: len(bits) for p, bits in ports.items()}}
                for port, bits in ports.items():
                    ordinal += 1
                    direction = 'input' if port == 'RD_DATA' else 'output'
                    wire = 'memory_' + identifier(cellname) + '_' + port
                    extras.append(f'  wire width {len(bits)} {direction} {ordinal} \\{wire}\n')
                    if direction == 'input':
                        extras.append(f'  connect {connections[port]} \\{wire}\n')
                    else:
                        extras.append(f'  connect \\{wire} {connections[port]}\n')
            else:
                assert celltype in ('$dff', '$adff'), celltype
                qbits = ports['Q']
                names = [n for n, wire in module['netnames'].items()
                         if wire['bits'] == qbits and not n.startswith('$')]
                assert names, cellname
                original_state = next((n for n in names if n.endswith('_q')), sorted(names)[0])
                state = identifier(original_state)
                assert state not in descriptors[label]
                width = len(qbits)
                descriptors[label][state] = {'type': celltype, 'width': width, 'parameters': cell['parameters'],
                                             'original_netname': original_state}
                assert connections['CLK'] == '\\clk' and int(cell['parameters']['CLK_POLARITY'], 2) == 1
                ordinal += 1
                extras.append(f'  wire width {width} input {ordinal} \\previous_{state}\n')
                ordinal += 1
                extras.append(f'  wire width {width} output {ordinal} \\next_{state}\n')
                if celltype == '$adff':
                    assert connections['ARST'] == '\\reset' and int(cell['parameters']['ARST_POLARITY'], 2) == 1
                    value = cell['parameters']['ARST_VALUE']
                    assert len(value) == width
                    extras.append(f'  wire width {width} \\current_{state}\n')
                    for phase, input_value, output_value in (
                        ('current', '\\previous_' + state, '\\current_' + state),
                        ('next', connections['D'], '\\next_' + state)):
                        extras.append(f'  cell $mux \\{phase}_reset_{state}\n'
                                      f'    parameter \\WIDTH {width}\n'
                                      f'    connect \\A {input_value}\n'
                                      f'    connect \\B {width}\'{value}\n'
                                      f'    connect \\S \\reset\n'
                                      f'    connect \\Y {output_value}\n  end\n')
                    extras.append(f'  connect {connections["Q"]} \\current_{state}\n')
                else:
                    extras.append(f'  connect {connections["Q"]} \\previous_{state}\n')
                    extras.append(f'  connect \\next_{state} {connections["D"]}\n')
            body = body[:begin] + body[finish:]
        body = body.rstrip() + '\n' + ''.join(extras)
        rtlil = rtlil[:start] + body + rtlil[end:]
    assert descriptors['gold'] == descriptors['gate'], 'Actual FF/reset descriptors differ'
    assert memories['gold'] == memories['gate'], 'Actual RAM geometry/initialization differs'
    (case / 'state-descriptors.json').write_text(json.dumps(descriptors, indent=2) + '\n')
    (case / 'memory-descriptors.json').write_text(json.dumps(memories, indent=2) + '\n')
    (case / 'one-step.il').write_text(rtlil)
    run(case, 'one-step-elaboration', 'read_rtlil one-step.il; check -assert; write_json one-step.json')
    return descriptors['gold'], memories['gold']


def miter(case):
    modules = json.loads((case / 'one-step.json').read_text())['modules']
    assert modules['buffer_gold']['ports'] == modules['buffer_gate']['ports'] or all(
        p['direction'] == modules['buffer_gate']['ports'][n]['direction'] and
        len(p['bits']) == len(modules['buffer_gate']['ports'][n]['bits'])
        for n, p in modules['buffer_gold']['ports'].items())
    assert modules['buffer_gold']['ports'].keys() == modules['buffer_gate']['ports'].keys()
    ports = modules['buffer_gold']['ports']
    inputs, wires, compares = [], [], []
    connections = {'gold': [], 'gate': []}
    for name, port in ports.items():
        width = len(port['bits'])
        shape = '' if width == 1 else f'[{width - 1}:0] '
        if port['direction'] == 'input':
            inputs.append('input wire ' + shape + name)
            for label in connections:
                connections[label].append(f'.{name}({name})')
        else:
            assert port['direction'] == 'output'
            for label in connections:
                wires.append(f'wire {shape}{name}_{label};')
                connections[label].append(f'.{name}({name}_{label})')
            equal = f'({name}_gold === {name}_gate)'
            if name in PAYLOAD:
                equal = f'(!out_valid_gold || {equal})'
            elif name.startswith('memory_') and name.endswith('_WR_DATA'):
                enable = name[:-len('WR_DATA')] + 'WR_EN'
                assert len(ports[enable]['bits']) == width
                equal = f'(({name}_gold & {enable}_gold) === ({name}_gate & {enable}_gate))'
            compares.append({'port': name, 'comparison': equal})
    (case / 'comparisons.json').write_text(json.dumps(compares, indent=2) + '\n')
    source = 'module invariant(\n' + ',\n'.join(inputs) + ',\noutput wire step_ok\n);\n'
    source += '\n'.join(wires) + '\n'
    for label in connections:
        source += f'buffer_{label} u_{label}(' + ','.join(connections[label]) + ');\n'
    source += 'assign step_ok = ' + ' &&\n'.join(c['comparison'] for c in compares) + ';\nendmodule\n'
    (case / 'invariant.sv').write_text(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--candidate-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    tool = Path(__file__).resolve()
    frozen, results = {tool: tool.read_bytes()}, []
    for name, module, parameters in CASES:
        relative = Path('rtl/spk286_integration') / (module + '.sv')
        paths = [args.reference.resolve() / relative, args.candidate_root.resolve() / relative]
        for path in paths:
            frozen.setdefault(path, path.read_bytes())
        before, after = [frozen[p].decode().replace('\r\n', '\n') for p in paths]
        assert before != after, 'No production change to prove'
        case = output / name
        case.mkdir()
        for label, source in (('gold', before), ('gate', after)):
            (case / (label + '.sv')).write_text(source.replace('module ' + module, 'module buffer_' + label, 1))
        preparation = 'read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
        if parameters:
            preparation += 'chparam ' + ' '.join(f'-set {p} {v}' for p, v in parameters.items()) + ' buffer_gold buffer_gate; '
        preparation += 'hierarchy -check; proc; opt_clean; memory_collect; write_json elaborated.json; write_rtlil elaborated.il'
        run(case, 'elaboration', preparation)
        states, memories = abstract(case)
        miter(case)
        proof = ('read_rtlil one-step.il; read_verilog -sv invariant.sv; prep -top invariant; '
                 'flatten; opt; check -assert; sat -verify -set-def-inputs -prove step_ok 1 '
                 '-show-inputs -show-outputs -dump_json counterexample.json')
        _, text = run(case, 'proof', proof)
        assert 'SUCCESS!' in text
        # Corrupt the actual forwarded address; rejection must be a real
        # qualified-output counterexample, never a timeout or tool error.
        mutant = after.replace('out_address = in_address;', "out_address = in_address ^ 25'd1;", 1)
        if mutant == after:
            mutant = after.replace('out_address       = in_address;', "out_address       = in_address ^ 25'd1;", 1)
        assert mutant != after
        negative = case / 'negative'
        negative.mkdir()
        (negative / 'gold.sv').write_text(before.replace('module ' + module, 'module buffer_gold', 1))
        (negative / 'gate.sv').write_text(mutant.replace('module ' + module, 'module buffer_gate', 1))
        run(negative, 'elaboration', preparation)
        abstract(negative)
        miter(negative)
        rc, text = run(negative, 'proof', proof, positive=False)
        assert rc != 0 and rc != 124 and 'proof did fail' in text
        results.append({'case': name, 'parameters': parameters, 'state_bits': sum(s['width'] for s in states.values()),
                        'memories': memories, 'reference_sha256': sha(paths[0]), 'candidate_sha256': sha(paths[1]),
                        'proof': 'Actual complete one-step state and memory-interface equality; out payload qualified only by unchanged out_valid.',
                        'negative': 'Actual idle forwarded address bit corrupted; SAT rejected with counterexample.'})
        print('BUFFER_PAYLOAD_EQUIVALENCE_PASS ' + name, flush=True)
    for path, data in frozen.items():
        assert path.read_bytes() == data, 'Input changed: ' + str(path)
    receipt = {'status': 'AT_BUFFER_IDLE_PAYLOAD_EQUIVALENCE_PASS', 'cases': results,
               'proof_script_sha256': sha(Path(__file__)), 'source_guard': 'All input bytes unchanged before/after proof.',
               'qualified_outputs': sorted(PAYLOAD), 'unconditional': 'All remaining original outputs, every actual next FF bit, memory read/write address/control, enabled write data.',
               'assumptions': 'None on external protocol or control-state reachability. Common arbitrary actual prior FFs and memory contents provide induction coupling; async reset clamps actual Q/D.',
               'limitations': 'Inactive payload values intentionally change. No STA, fit, hardware or full-regression claim.'}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
