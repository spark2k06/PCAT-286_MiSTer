#!/usr/bin/env python3
"""Prove eager IDLE metadata capture at the actual 512-word buffer geometry.

The proof checks a complete one-step relational invariant of the actual FFs
and the exact enabled-write memory interface. Memories remain two 256x32 arrays
with unchanged parameters and initialization. Original public outputs are never
masked. Common arbitrary initial RAM/lookup contents provide the equivalence
coupling; no assumptions are made about the external transaction protocol.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess

SOURCE = 'rtl/spk286_integration/spk286_at_sdram_data_buffer.sv'
FIELDS = [('lookup_valid0_q', 'valid0_q[input_index]'),
          ('lookup_valid1_q', 'valid1_q[input_index]'),
          ('replace_way_q', 'replace_q[input_index]')]
PRIVATE = tuple(name for name, _ in FIELDS)

def run(case, filename, command, must_pass=True):
    with (case / filename).open('w') as log:
        r = subprocess.run(['timeout', '300', 'yosys', '-p', command], cwd=case,
                           stdout=log, stderr=subprocess.STDOUT)
    if must_pass:
        assert r.returncode == 0, (filename, r.returncode)
    return r.returncode


def materialize(case, before, after):
    relations = ''.join(f'    assign phase_{name} = (state_q == STATE_IDLE) ? 1\'b0 : {name};\n'
                        for name, _ in FIELDS)
    for label, source in [('gold', before), ('gate', after)]:
        source = source.replace('module spk286_at_sdram_data_buffer', 'module buffer_' + label, 1)
        port_end = source.index(');')
        ports = ',\n' + ',\n'.join('    output wire phase_' + name for name, _ in FIELDS) + '\n'
        source = source[:port_end] + ports + source[port_end:]
        source = source.replace('endmodule', relations + 'endmodule')
        (case / (label + '.sv')).write_text(source)
    run(case, 'elaboration.log', 'read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
        'hierarchy -check; proc; opt_clean; memory_collect; '
        'write_json memory.json; write_rtlil memory.il')
    modules = json.loads((case / 'memory.json').read_text())['modules']
    rtlil = (case / 'memory.il').read_text()
    geometry = []
    for label in ('gold', 'gate'):
        module = modules['buffer_' + label]
        mi = rtlil.index('module \\buffer_' + label + '\n')
        me = rtlil.index('\nend\n', mi)
        body = rtlil[mi:me]
        # Original public ports keep their original indices and directions.
        max_port = max(port.get('port_id', 0) for port in module['netnames'].values())
        # JSON ports do not include IDs: read existing RTLIL declarations.
        max_port = max(int(p) for p in re.findall(r'\b(?:input|output) (\d+) ', body))
        extra = []
        for memname, cell in module['cells'].items():
            if cell['type'] != '$mem_v2':
                continue
            geometry.append({'module': label, 'memory': memname,
                             'parameters': cell['parameters'],
                             'port_widths': {p: len(b) for p, b in cell['connections'].items()}})
            header = '  cell $mem_v2 \\' + memname + '\n'
            start = body.index(header)
            while start > 0:
                previous = body.rfind('\n', 0, start - 1) + 1
                if not body[previous:start].startswith('  attribute '):
                    break
                start = previous
            finish = body.index('  end\n', start) + len('  end\n')
            block = body[start:finish]
            for port, bits in cell['connections'].items():
                expression = re.search(r'^    connect \\' + re.escape(port) + r' (.+)$', block, re.M).group(1)
                direction = 'input' if port == 'RD_DATA' else 'output'
                max_port += 1
                name = 'memory_' + memname + '_' + port
                extra.append(f'  wire width {len(bits)} {direction} {max_port} \\{name}\n')
                if direction == 'input':
                    extra.append(f'  connect {expression} \\{name}\n')
                else:
                    extra.append(f'  connect \\{name} {expression}\n')
            body = body[:start] + body[finish:]
        body = body.rstrip() + '\n' + ''.join(extra)
        rtlil = rtlil[:mi] + body + rtlil[me:]
    assert len(geometry) == 4
    # Exact memory geometry/init/configuration is part of the proof premise.
    for name in ('words0_q', 'words1_q'):
        gold = next(m for m in geometry if m['module'] == 'gold' and m['memory'] == name)
        gate = next(m for m in geometry if m['module'] == 'gate' and m['memory'] == name)
        assert gold['parameters'] == gate['parameters']
        assert gold['port_widths'] == gate['port_widths']
        assert int(gold['parameters']['SIZE'], 2) == 256
        assert int(gold['parameters']['WIDTH'], 2) == 32
    (case / 'memory-geometry.json').write_text(json.dumps(geometry, indent=2) + '\n')
    (case / 'abstracted.il').write_text(rtlil)
    run(case, 'abstraction-elaboration.log', 'read_rtlil abstracted.il; opt_clean; '
        'check -assert; write_json abstracted.json; write_rtlil prepared.il')

def make(case):
    module_json = json.loads((case / 'abstracted.json').read_text())['modules']
    rtlil = (case / 'prepared.il').read_text()
    states = {}
    descriptors = {}
    for label in ('gold', 'gate'):
        module = module_json['buffer_' + label]
        mi = rtlil.index('module \\buffer_' + label + '\n')
        me = rtlil.index('\nend\n', mi)
        body = rtlil[mi:me]
        port_number = max(int(p) for p in re.findall(r'\b(?:input|output) (\d+) ', body))
        extra = []
        states[label] = {}
        descriptors[label] = {}
        for cellname, cell in module['cells'].items():
            if 'Q' not in cell['connections']:
                continue
            assert cell['type'] in ('$dff', '$adff'), cell['type']
            qbits = cell['connections']['Q']
            names = [name for name, n in module['netnames'].items()
                     if n['bits'] == qbits and not name.startswith('$')]
            assert names, cellname
            name = next((name for name in names if name.endswith('_q')), sorted(names)[0])
            assert re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', name), name
            assert name not in states[label]
            states[label][name] = len(qbits)
            descriptors[label][name] = dict(type=cell['type'], width=len(qbits),
                                            parameters=cell['parameters'])
            header = '  cell ' + cell['type'] + ' ' + ('\\' if not cellname.startswith('$') else '') + cellname + '\n'
            start = body.index(header)
            while start > 0:
                previous = body.rfind('\n', 0, start - 1) + 1
                if not body[previous:start].startswith('  attribute '):
                    break
                start = previous
            finish = body.index('  end\n', start) + len('  end\n')
            block = body[start:finish]
            connections = {port: re.search(r'^    connect \\' + port + r' (.+)$', block, re.M).group(1)
                           for port in cell['connections']}
            assert connections['CLK'] == '\\clk'
            assert int(cell['parameters']['CLK_POLARITY'], 2) == 1
            port_number += 1
            extra.append(f'  wire width {len(qbits)} input {port_number} \\previous_{name}\n')
            port_number += 1
            extra.append(f'  wire width {len(qbits)} output {port_number} \\next_{name}\n')
            if cell['type'] == '$adff':
                assert connections['ARST'] == '\\reset'
                assert int(cell['parameters']['ARST_POLARITY'], 2) == 1
                reset_value = cell['parameters']['ARST_VALUE']
                assert len(reset_value) == len(qbits)
                extra.append(f'  wire width {len(qbits)} \\current_{name}\n')
                extra.append(f'  cell $mux \\current_reset_{name}\n'
                             f'    parameter \\WIDTH {len(qbits)}\n'
                             f'    connect \\A \\previous_{name}\n'
                             f'    connect \\B {len(qbits)}\'{reset_value}\n'
                             f'    connect \\S \\reset\n'
                             f'    connect \\Y \\current_{name}\n  end\n')
                extra.append(f'  connect {connections["Q"]} \\current_{name}\n')
                extra.append(f'  cell $mux \\next_reset_{name}\n'
                             f'    parameter \\WIDTH {len(qbits)}\n'
                             f'    connect \\A {connections["D"]}\n'
                             f'    connect \\B {len(qbits)}\'{reset_value}\n'
                             f'    connect \\S \\reset\n'
                             f'    connect \\Y \\next_{name}\n  end\n')
            else:
                extra.append(f'  connect {connections["Q"]} \\previous_{name}\n')
                extra.append(f'  connect \\next_{name} {connections["D"]}\n')
            body = body[:start] + body[finish:]
        body = body.rstrip() + '\n' + ''.join(extra)
        rtlil = rtlil[:mi] + body + rtlil[me:]
    assert states['gold'] == states['gate']
    assert descriptors['gold'] == descriptors['gate']
    assert sum(states['gold'].values()) > 1000
    (case / 'one-step.il').write_text(rtlil)
    (case / 'one-step-state.json').write_text(json.dumps(states, indent=2) + '\n')
    (case / 'one-step-state-descriptors.json').write_text(json.dumps(descriptors, indent=2) + '\n')
    run(case, 'one-step-elaboration.log', 'read_rtlil one-step.il; check -assert; '
        'write_json one-step.json; write_verilog one-step.v')
    modules = json.loads((case / 'one-step.json').read_text())['modules']
    assert modules['buffer_gold']['ports'].keys() == modules['buffer_gate']['ports'].keys()
    for name, port in modules['buffer_gold']['ports'].items():
        other = modules['buffer_gate']['ports'][name]
        assert port['direction'] == other['direction'], name
        assert len(port['bits']) == len(other['bits']), name
    ports = modules['buffer_gold']['ports']
    inputs, wires, connections, compares, next_compares = [], [], {'gold': [], 'gate': []}, [], []
    for name, port in ports.items():
        width = len(port['bits'])
        shape = '' if width == 1 else f'[{width-1}:0] '
        if port['direction'] == 'input':
            private = name.startswith('previous_') and name[len('previous_'):] in PRIVATE
            for suffix in ('_gold', '_gate') if private else ('',):
                inputs.append(f'    input wire {shape}{name}{suffix}')
            for label in ('gold', 'gate'):
                signal = name + ('_' + label if private else '')
                connections[label].append(f'.{name}({signal})')
        else:
            assert port['direction'] == 'output'
            for label in ('gold', 'gate'):
                wires.append(f'    wire {shape}{name}_{label};')
                connections[label].append(f'.{name}({name}_{label})')
            equality = f'({name}_gold === {name}_gate)'
            if name.startswith('memory_') and name.endswith('_WR_DATA'):
                enable = name[:-len('WR_DATA')] + 'WR_EN'
                assert len(ports[enable]['bits']) == width
                equality = (f'(({name}_gold & {enable}_gold) === '
                            f'({name}_gate & {enable}_gate))')
            if name.startswith('next_'):
                if name[len('next_'):] not in PRIVATE:
                    next_compares.append(equality)
            else:
                compares.append(equality)
    prior_private = ' && '.join(f'(previous_{n}_gold == previous_{n}_gate)' for n in PRIVATE)
    next_private = ' && '.join(f'(next_{n}_gold == next_{n}_gate)' for n in PRIVATE)
    next_equal = ' &&\n        '.join(next_compares)
    public_equal = ' &&\n        '.join(compares)
    (case / 'output-comparisons.json').write_text(json.dumps(compares, indent=2) + '\n')
    wrapper = 'module invariant(\n' + ',\n'.join(inputs) + ',\n    output wire step_ok, reset_ok\n);\n'
    wrapper += '\n'.join(wires) + '\n'
    for label in ('gold', 'gate'):
        wrapper += f'    buffer_{label} u_{label}(\n        ' + ',\n        '.join(connections[label]) + '\n    );\n'
    wrapper += f'    wire relation = reset || (previous_state_q == 0) || ({prior_private});\n'
    wrapper += f'    wire next_relation = ({next_equal}) && ((next_state_q_gold == 0) || ({next_private}));\n'
    wrapper += f'    wire [{len(compares)-1}:0] output_matches = {{' + ', '.join(compares) + '};\n'
    wrapper += '    wire outputs_equal = &output_matches;\n'
    wrapper += '    assign step_ok = !relation || (outputs_equal && next_relation);\n'
    wrapper += '    assign reset_ok = !reset || next_relation;\nendmodule\n'
    (case / 'invariant.sv').write_text(wrapper)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(raw):
    return raw.decode('utf-8').replace('\r\n', '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('--candidate-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference_path = args.reference.resolve() / SOURCE
    candidate_path = args.candidate_file.resolve()
    tool_path = Path(__file__).resolve()
    frozen = {path: path.read_bytes() for path in (reference_path, candidate_path, tool_path)}
    before = text(frozen[reference_path])
    after = text(frozen[candidate_path])
    expected = before
    for name, expression in FIELDS:
        statement = f'                        {name} <= {expression};\n'
        assert expected.count(statement) == 1
        expected = expected.replace(statement, '', 1)
    needle = '                STATE_IDLE: begin\n                    if (in_accept) begin'
    assert expected.count(needle) == 1
    eager = ''.join(f'                    {name} <= {expression};\n' for name, expression in FIELDS)
    expected = expected.replace(needle, '                STATE_IDLE: begin\n' + eager + '                    if (in_accept) begin', 1)
    old_assert = '            assert (!(tag_hit0 && tag_hit1))'
    guarded_assert = ('            // Eager metadata can follow a new index in IDLE while tag/data is\n'
                      '            // still retained. Check duplicate tags only in consuming phases.\n'
                      '            assert (state_q == STATE_IDLE || !(tag_hit0 && tag_hit1))')
    assert expected.count(old_assert) == 1
    phase_assert_qualified = after == expected.replace(old_assert, guarded_assert, 1)
    assert after == expected or phase_assert_qualified, 'Unexpected source changes beyond the three eager metadata captures and optional exact assertion-domain correction'
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    mutant = after.replace('lookup_valid0_q <= valid0_q[input_index];',
                           'lookup_valid0_q <= valid1_q[input_index];', 1)
    assert mutant != after
    command = ('read_verilog -sv one-step.v invariant.sv; hierarchy -top invariant; '
               'proc; flatten; wreduce; opt -full -keepdc; check -assert; '
               'sat -verify -set-def-inputs -prove step_ok 1 -show relation -show outputs_equal -show next_relation '
               '-show output_matches -show reset -show previous_state_q '
               '-dump_json counterexample.json')
    for case_name, candidate in (('positive', after), ('negative', mutant)):
        case = out / case_name
        case.mkdir()
        materialize(case, before, candidate)
        modules = json.loads((case / 'memory.json').read_text())['modules']
        for port, record in modules['buffer_gold']['ports'].items():
            other = modules['buffer_gate']['ports'].get(port)
            assert other is not None and record['direction'] == other['direction']
            assert len(record['bits']) == len(other['bits'])
        assert modules['buffer_gold']['ports'].keys() == modules['buffer_gate']['ports'].keys()
        make(case)
        result = run(case, 'one-step-proof.log', command, must_pass=case_name == 'positive')
        if case_name == 'negative':
            assert result != 0 and result != 124, 'Timeout or success is not a rejected negative control'
            assert 'proof did fail' in (case / 'one-step-proof.log').read_text()
            counter = json.loads((case / 'counterexample.json').read_text())['signal']
            signals = {s['name']: s for s in counter}
            assert signals['relation']['wave'].startswith('1')
            assert signals['next_relation']['wave'].startswith('0')
        else:
            assert 'SUCCESS!' in (case / 'one-step-proof.log').read_text()
            reset_command = command.replace('-prove step_ok 1', '-prove reset_ok 1')
            run(case, 'reset-relation-proof.log', reset_command)
            assert 'SUCCESS!' in (case / 'reset-relation-proof.log').read_text()
    for path, raw in frozen.items():
        assert path.read_bytes() == raw, f'Input changed while proving: {path}'
    artifacts = {str(path.relative_to(out)).replace('\\', '/'): sha(path)
                 for path in sorted(out.rglob('*')) if path.is_file()}
    states = json.loads((out / 'positive/one-step-state.json').read_text())['gold']
    result = dict(status='AT_DATA_CAPTURE_RELATIONAL_EQUIVALENCE_PASS',
        reference_path=str(reference_path), candidate_path=str(candidate_path),
        reference_sha256=hashlib.sha256(frozen[reference_path]).hexdigest(),
        candidate_sha256=hashlib.sha256(frozen[candidate_path]).hexdigest(),
        proof_script_sha256=hashlib.sha256(frozen[tool_path]).hexdigest(),
        state_bits=sum(states.values()), state_registers=len(states),
        source_guard='All normalized source unchanged except moving exactly the three metadata assignments from IDLE&&in_accept to IDLE, and the separately recorded optional simulation assertion-domain correction.',
        phase_assert_qualified=phase_assert_qualified,
        original_public_outputs='All compared without masks; every original name, direction and width checked.',
        state_relation='All unchanged actual registers equal. Three lookup metadata bits equal outside IDLE; IDLE values may differ. Every current and next ADFF Q explicitly clamps to its original reset value. FF widths, types, polarity and reset descriptors match.',
        transition='For every defined input and arbitrary state satisfying the relation, all original public outputs match and the complete next-state relation holds.',
        reset_base='Active reset establishes the next-state relation without prior equality of the three metadata bits. Unreset lookup0/lookup1 and memories use common arbitrary initial contents for source equivalence; valid arrays reset invalid.',
        memories='Actual two 256x32 memories, all parameters and initialization identical. Async read data are common arbitrary inputs. Read clock/reset/enable/address and write clock/enable/address ports compared completely. Write data compared per bit only where its corresponding write enable is asserted, proving identical RAM updates by induction.',
        negative='Actual lookup_valid0 capture changed to valid1. SAT rejects with a real prior-relation-true, next-relation-false counterexample. This detects incorrect internal capture; it does not claim an immediate public-output difference. No timeout accepted.',
        scope='Actual production default geometry and complete sampled transition relation. No external protocol assumptions, original output masking, downsized RAM, RTL timing changes, or arbitrary internal combinational cuts.',
        limitations='No STA, hardware or full regression claim. The optional simulation-only assertion-domain correction is excluded by SYNTHESIS and requires a separate directed IDLE witness; this proof establishes equivalence in consuming phases.',
        artifacts=artifacts)
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
