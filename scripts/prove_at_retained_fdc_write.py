#!/usr/bin/env python3
"""Prove the retained FDC write change at its exact composed boundary.

Usage: prove_at_retained_fdc_write.py REFERENCE_ROOT --candidate-root ROOT
       --output NEW_DIRECTORY

Guards exactly six source deltas. Compares actual bridge/FDC/FIFO public
outputs and full next state, both CPU completion modes, active1 and default0.
Actual small arrays are fully mapped; actual FIFO remains1024x8. This is a
source-extracted delivery/FDC fragment proof, not global machine equivalence.
Each Yosys operation is bounded to300s; real negatives must fail, not timeout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

fields='    input  logic        retained_io_command,\n    input  logic [23:0] retained_io_address,\n    input  logic        retained_io_write,\n    input  logic [1:0]  retained_io_byte_enable,\n    input  logic [15:0] retained_io_data_out,'
view_ports='    // Retained transaction view: no new registers or stages.\n    output logic         retained_io_command,\n    output logic [23:0]  retained_io_address,\n    output logic         retained_io_write,\n    output logic [1:0]   retained_io_byte_enable,\n    output logic [15:0]  retained_io_data_out,\n    output logic         retained_io_data_oe,\n'
view_assignments="    assign retained_io_command = (state_q == STATE_COMMAND) && request_is_io;\n    assign retained_io_address = beat_address;\n    assign retained_io_write = request_write_q;\n    assign retained_io_byte_enable = beat_byte_enable;\n    assign retained_io_data_out = request_native_word_q ? request_data_q :\n                                  beat_byte_enable[1] ?\n                                  {request_data_q[15:8], 8'h00} :\n                                  {8'h00, request_data_q[7:0]};\n    assign retained_io_data_oe = request_write_q &&\n                                 ((state_q == STATE_COMMAND) || (state_q == STATE_WAIT));\n"
port_anchor='    output logic         protocol_error\n);'

def rep(t, old, new, count=1):
    assert t.count(old) == count, (old[:80], t.count(old), count)
    return t.replace(old, new)

def addfields(t, nl='\n'):
    anchor = '    input  logic [15:0] request_data_out,'
    return rep(t, anchor, anchor + nl + fields.replace('\n', nl))

def addbinding(t, anchor, nl='\n'):
    names = ['retained_io_command', 'retained_io_address', 'retained_io_write', 'retained_io_byte_enable', 'retained_io_data_out']
    extra = nl.join((f'        .{n:<24}({n}),' for n in names))
    return rep(t, anchor, anchor + nl + extra)

def cm(t):
    t = rep(t, '    logic        at_valid;', '    // Dedicated retained FDC write record; general/read buses remain intact.\n    logic        retained_io_command;\n    logic [23:0] retained_io_address;\n    logic        retained_io_write;\n    logic [1:0]  retained_io_byte_enable;\n    logic [15:0] retained_io_data_out;\n    logic        at_valid;')
    t = rep(t, '        .at_valid               (at_valid),', '        .retained_io_command    (retained_io_command),\n        .retained_io_address    (retained_io_address),\n        .retained_io_write      (retained_io_write),\n        .retained_io_byte_enable(retained_io_byte_enable),\n        .retained_io_data_out   (retained_io_data_out),\n        .retained_io_data_oe    (),\n        .at_valid               (at_valid),')
    t = rep(t, '    spk286_at_device_router u_devices (', "    spk286_at_device_router #(\n        .RETAINED_FDC_WRITE(1'b1)\n    ) u_devices (")
    t = rep(t, '        .request_valid          (device_request_candidate),', '        // Pure I/O COMMAND ownership, independent of the early memory mux.\n        .retained_io_command    (cpu_grant && retained_io_command),\n        .retained_io_address    (retained_io_address),\n        .retained_io_write      (retained_io_write),\n        .retained_io_byte_enable(retained_io_byte_enable),\n        .retained_io_data_out   (retained_io_data_out),\n        .request_valid          (device_request_candidate),')
    return t

def cr(t):
    nl = '\r\n'
    t = rep(t, 'module spk286_at_device_router (', 'module spk286_at_device_router #(' + nl + "    parameter logic RETAINED_FDC_WRITE = 1'b0" + nl + ') (')
    t = addfields(t, nl)
    t = rep(t, '    spk286_at_storage_video u_storage_video (', '    spk286_at_storage_video #(' + nl + '        .RETAINED_FDC_WRITE(RETAINED_FDC_WRITE)' + nl + '    ) u_storage_video (')
    return addbinding(t, '        .request_valid(device_storage_candidate),', nl)

def cs(t):
    t = rep(t, 'module spk286_at_storage_video (', "module spk286_at_storage_video #(\n    parameter logic RETAINED_FDC_WRITE = 1'b0\n) (")
    t = addfields(t)
    t = rep(t, '    spk286_at_fdc u_fdc (', '    spk286_at_fdc #(\n        .RETAINED_FDC_WRITE(RETAINED_FDC_WRITE)\n    ) u_fdc (')
    return addbinding(t, '        .request_valid          (request_valid && floppy_selected),')

def cf(t):
    t = rep(t, '// The controller itself is rtl/common/floppy.v, shared byte-for-byte with the\n// working XT profile and with ao486/z486.  This wrapper only translates the\n// normalized AT I/O, DMA and hps_ext management handshakes.', '// The controller is rtl/common/floppy.v, shared with the XT and ao486/z486\n// profiles. Its optional write-address input isolates write decoding while\n// io_address preserves the existing read path. This wrapper translates the\n// normalized AT I/O, DMA and hps_ext management handshakes.')
    t = rep(t, 'module spk286_at_fdc (', "module spk286_at_fdc #(\n    parameter logic RETAINED_FDC_WRITE = 1'b0\n) (")
    t = addfields(t)
    t = rep(t, '    assign request_accept = (io_state_q == IO_IDLE) && selected && lane_valid;', "    // Reads preserve the old general address/pulse/read-wait path exactly.\n    // Writes use only retained I/O COMMAND, CPU grant and retained payload.\n    wire retained_write_selected = retained_io_command && retained_io_write &&\n                                   (retained_io_address[15:0] >= 16'h03F0) &&\n                                   (retained_io_address[15:0] <= 16'h03F7) &&\n                                   (retained_io_address[15:0] != 16'h03F6);\n    wire retained_lane_valid = (!retained_io_address[0] &&\n                                 (retained_io_byte_enable == 2'b01)) ||\n                                (retained_io_address[0] &&\n                                 (retained_io_byte_enable == 2'b10));\n    wire read_accept = (io_state_q == IO_IDLE) && selected && lane_valid &&\n                       !request_write;\n    wire write_accept = (io_state_q == IO_IDLE) &&\n                        (RETAINED_FDC_WRITE ?\n                         retained_write_selected && retained_lane_valid :\n                         selected && lane_valid && request_write);\n    wire [1:0] accepted_byte_enable = (RETAINED_FDC_WRITE && write_accept) ?\n                                      retained_io_byte_enable : request_byte_enable;\n    wire [2:0] write_address = RETAINED_FDC_WRITE ?\n                               retained_io_address[2:0] : request_address[2:0];\n    wire [7:0] write_byte = RETAINED_FDC_WRITE ?\n                            (retained_io_byte_enable[1] ?\n                             retained_io_data_out[15:8] : retained_io_data_out[7:0]) :\n                            request_byte;\n    assign request_accept = read_accept || write_accept;")
    t = rep(t, '    assign fdc_io_read = request_accept && !request_write;', '    assign fdc_io_read = read_accept;')
    t = rep(t, '    assign fdc_io_write = request_accept && request_write;', '    assign fdc_io_write = write_accept;')
    t = rep(t, '                    io_byte_enable_q <= request_byte_enable;', '                    io_byte_enable_q <= accepted_byte_enable;')
    t = rep(t, '                        if (request_write) begin', '                        if (fdc_io_write) begin')
    t = rep(t, "                            if (request_address[2:0] == 3'd5)", "                            if (write_address == 3'd5)")
    t = rep(t, '    floppy u_fdc (', '    floppy #(\n        .SEPARATE_IO_WRITE_ADDRESS(RETAINED_FDC_WRITE)\n    ) u_fdc (')
    t = rep(t, '        .io_address      (request_address[2:0]),', '        .io_address      (request_address[2:0]),\n        .io_write_address(write_address),')
    return rep(t, '        .io_writedata    (request_byte),', '        .io_writedata    (write_byte),')

def cfl(t):
    nl = '\r\n'
    t = rep(t, 'module floppy', 'module floppy' + nl + '#(' + nl + '    parameter SEPARATE_IO_WRITE_ADDRESS = 0' + nl + ')')
    m = re.search('^[ \\t]*output[^\\r\\n]*\\brequest[ \\t]*(?=\\r?$)', t, re.M)
    assert m, 'Original final request port not found'
    old = m.group(0)
    t = rep(t, old, old + ',' + nl + '    input       [2:0] io_write_address')
    anchor = '//------------------------------------------------------------------------------ io read'
    t = rep(t, anchor, '// Separate only write decoding; io_address still feeds every read clock.' + nl + 'wire [2:0] write_address = SEPARATE_IO_WRITE_ADDRESS ? io_write_address : io_address;' + nl + nl + anchor)
    t, n = re.subn('(io_write\\s*&&\\s*)io_address', '\\1write_address', t)
    assert n == 12, n
    return t

def run(case, filename, command, must_pass=True):
    with (case / filename).open('w') as log:
        r = subprocess.run(['timeout', '300', 'yosys', '-p', command], cwd=case,
                           stdout=log, stderr=subprocess.STDOUT)
    if must_pass:
        assert r.returncode == 0, (filename, r.returncode)
    return r.returncode


def materialize(case, before, after):
    for label, source in [('gold', before), ('gate', after)]:
        (case / (label + '.sv')).write_text(source)
    run(case, 'elaboration.log', 'read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
        'hierarchy -check; proc; flatten; opt_clean; memory_collect; '
        'write_json memory.json; write_rtlil memory.il')
    original_modules = json.loads((case / 'memory.json').read_text())['modules']
    original_memories = {}
    small = []
    for label in ('gold', 'gate'):
        original_memories[label] = {}
        for name, cell in original_modules['buffer_' + label]['cells'].items():
            if cell['type'] != '$mem_v2':
                continue
            original_memories[label][name] = dict(parameters=cell['parameters'],
                port_widths={p: len(b) for p,b in cell['connections'].items()})
            size = int(cell['parameters']['SIZE'], 2)
            assert size in (2, 1024), (name, size)
            if size == 2:
                small.append('buffer_' + label + '/' + name)
    assert original_memories['gold'] == original_memories['gate']
    (case / 'original-full-memory-geometry.json').write_text(json.dumps(original_memories, indent=2) + '\n')
    run(case, 'small-memory-map.log', 'read_rtlil memory.il; memory_map ' + ' '.join(small) +
        '; opt_clean; write_json memory-mapped.json; write_rtlil memory-mapped.il')
    modules = json.loads((case / 'memory-mapped.json').read_text())['modules']
    rtlil = (case / 'memory-mapped.il').read_text()
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
    names = {m['memory'] for m in geometry if m['module'] == 'gold'}
    assert names == {m['memory'] for m in geometry if m['module'] == 'gate'}
    fifo_found = False
    for name in names:
        gold = next(m for m in geometry if m['module'] == 'gold' and m['memory'] == name)
        gate = next(m for m in geometry if m['module'] == 'gate' and m['memory'] == name)
        assert gold['parameters'] == gate['parameters'], name
        assert gold['port_widths'] == gate['port_widths'], name
        if name.endswith('fifo_to_floppy_inst.mem'):
            assert int(gold['parameters']['SIZE'], 2) == 1024
            assert int(gold['parameters']['WIDTH'], 2) == 8
            fifo_found = True
    assert fifo_found, 'Actual production FIFO memory absent'
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
                     if n['bits'] == qbits]
            names = [name for name in names if not name.startswith('$')] or names
            assert names, cellname
            name = next((name for name in names if name.endswith('_q')), sorted(names)[0])
            name = re.sub(r'\$unnamed_block\$[0-9]+', '$unnamed_block', name)
            name = re.sub(r'[^a-zA-Z_0-9]', '_', name) + '_' + hashlib.sha256(name.encode()).hexdigest()[:8]
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
    assert sum(states['gold'].values()) > 500
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
            inputs.append(f'    input wire {shape}{name}')
            for label in ('gold', 'gate'):
                connections[label].append(f'.{name}({name})')
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
                next_compares.append(equality)
            else:
                compares.append(equality)
    next_equal = ' &&\n        '.join(next_compares)
    public_equal = ' &&\n        '.join(compares)
    (case / 'output-comparisons.json').write_text(json.dumps(compares, indent=2) + '\n')
    wrapper = 'module invariant(\n' + ',\n'.join(inputs) + ',\n    output wire step_ok, reset_ok\n);\n'
    wrapper += '\n'.join(wires) + '\n'
    for label in ('gold', 'gate'):
        wrapper += f'    buffer_{label} u_{label}(\n        ' + ',\n        '.join(connections[label]) + '\n    );\n'
    wrapper += "    wire relation = 1'b1;\n"
    wrapper += f'    wire next_relation = ({next_equal});\n'
    wrapper += f'    wire [{len(compares)-1}:0] output_matches = {{' + ', '.join(compares) + '};\n'
    wrapper += '    wire outputs_equal = &output_matches;\n'
    wrapper += '    assign step_ok = !relation || (outputs_equal && next_relation);\n'
    wrapper += '    assign reset_ok = !(bridge_reset || fdc_reset) || next_relation;\nendmodule\n'
    (case / 'invariant.sv').write_text(wrapper)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_root',type=Path)
    parser.add_argument('--candidate-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    REF=args.reference_root.resolve()
    GATE=args.candidate_root.resolve()
    HERE=args.output.resolve()
    tool=Path(__file__).resolve()
    names=['rtl/spk286_integration/spk286_at_bus_bridge.sv',
           'rtl/spk286_integration/spk286_at_machine.sv',
           'rtl/spk286_integration/spk286_at_device_router.sv',
           'rtl/spk286_integration/spk286_at_storage_video.sv',
           'rtl/spk286_integration/spk286_at_fdc.sv','rtl/common/floppy.v',
           'rtl/common/simple_fifo.v']
    frozen={p:p.read_bytes() for p in [tool]+[folder/n for folder in (REF,GATE) for n in names]}
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    norm=lambda p:frozen[p].decode('utf-8').replace('\r\n','\n')
    source_guard={}
    original_bridge=norm(REF/names[0])
    candidate_bridge=norm(GATE/names[0])
    expected=original_bridge.replace(port_anchor,view_ports+port_anchor,1)
    expected=expected.replace('\nendmodule','\n'+view_assignments+'\nendmodule',1)
    assert original_bridge.count(port_anchor)==1 and original_bridge.count('\nendmodule')==1
    assert expected==candidate_bridge, 'Bridge delta must be exactly the six retained output additions'
    transforms=[cm,cr,cs,cf,cfl]
    for rel,fn in zip(names[1:6],transforms):
        expected=fn(norm(REF/rel)).replace('\r\n','\n')
        assert expected==norm(GATE/rel), 'Unexpected source change: '+rel
    assert norm(REF/names[6])==norm(GATE/names[6]), 'Actual FIFO source changed'
    for rel in names:
        source_guard[rel]={'reference':hashlib.sha256(frozen[REF/rel]).hexdigest(),
                          'candidate':hashlib.sha256(frozen[GATE/rel]).hexdigest()}
    HERE.mkdir(parents=True,exist_ok=False)
    (HERE/'source-guard.json').write_text(json.dumps({'status':'EXACT_SIX_DELTA_SOURCE_GUARD_PASS',
        'files':source_guard,'delta':'Bridge six retained combinational outputs; machine grant-qualified transport; router/storage additive transport; FDC separated writes with default0; common floppy12 write-address predicate substitutions with default0. Exact retained-view and shared-FDC header comments included. All other normalized source text unchanged. Actual FIFO unchanged.'},indent=2)+'\n')
    def ports(source):
        header = source[:source.index('\n);')]
        return [(m[1], (m[2] or '').strip(), m[3]) for m in
                re.finditer(r'^\s*(input|output)\s+(?:logic|wire|reg)?\s*(\[[^\]]+\]\s+)?(\w+)\s*,?\s*$', header, re.M)]

    def assignment(text, name):
        m = re.search(r'\b' + re.escape(name) + r'\s*=.*?;', text, re.S)
        assert m, name
        return m[0]

    machine = norm(REF / 'rtl/spk286_integration/spk286_at_machine.sv')
    router = norm(REF / 'rtl/spk286_integration/spk286_at_device_router.sv')
    storage = norm(REF / 'rtl/spk286_integration/spk286_at_storage_video.sv')
    fdc = norm(REF / 'rtl/spk286_integration/spk286_at_fdc.sv')

    # Exact source fragments, not assumed output values of unrelated decoders.
    a5 = re.search(r'function automatic logic is_a5_io_port\(.*?endfunction', machine, re.S).group(0)
    mapped = re.search(r'    always_comb begin\n        at_memory_address = at_address;.*?    end', machine, re.S).group(0)
    machine_assignments = [assignment(machine,n) for n in ('a5_io_candidate','sound_io_candidate','device_request_candidate')]
    other_names = ['device_8042_candidate','device_rtc_candidate','device_storage_candidate','device_at286ctl_candidate',
                   'device_gameport_candidate','device_mpu401_candidate','device_uart1_candidate','device_uart2_candidate',
                   'device_ems_candidate','device_sound_candidate']
    router_assignments = [assignment(router,n) for n in other_names]
    floppy_selected = assignment(storage, 'floppy_selected').replace('request_valid','storage_request_valid')
    xtide_selected = assignment(storage, 'xtide_selected').replace('request_valid','storage_request_valid')
    fragments = dict(a5=a5, mapped=mapped, machine_assignments=machine_assignments,
                     router_assignments=router_assignments, floppy_selected=floppy_selected, xtide_selected=xtide_selected,
                     storage_fdc_binding={'request_valid':'request_valid && floppy_selected',
                                          'request_command_valid':'request_command_valid && floppy_selected'})
    for signal, expr in fragments['storage_fdc_binding'].items():
        assert re.search(r'\.'+signal+r'\s*\('+re.escape(expr)+r'\)', storage), signal
    (HERE / 'exact-decode-fragments.json').write_text(json.dumps(fragments, indent=2) + '\n')

    feature_ports = [('feature_opl2',''), ('feature_cms',''), ('feature_tandy',''), ('feature_sb',''), ('feature_midi',''),
                     ('at286ctl_eff_opl2','[1:0]'), ('at286ctl_eff_cms',''), ('at286ctl_eff_tandy',''),
                     ('at286ctl_eff_sb',''), ('at286ctl_eff_mpu401',''), ('ems_runtime_enabled',''), ('a20_enable',''),
                     ('video_aperture_select','')]
    features = {'ENABLE_OPL2':'feature_opl2','ENABLE_CMS':'feature_cms','ENABLE_TANDY_AUDIO':'feature_tandy','ENABLE_SB':'feature_sb','ENABLE_MIDI':'feature_midi'}
    def features_expand(s):
        for old,new in features.items():
            s = s.replace('`'+old,new)
        return s

    route_header = '''module fdc_route(
        input wire cpu_grant, at_valid, at_command_valid, at_write, at_io,
        input wire [23:0] at_address,
    '''+',\n'.join('    input wire '+(width+' ' if width else '')+name for name,width in feature_ports)+''',
        output wire fdc_valid, fdc_command,
        output wire [23:0] fdc_address,
        output wire exclusive
    );
        wire cpu_owner_active = cpu_grant && at_valid;
        logic [23:0] at_memory_address;
        logic a5_io_candidate, sound_io_candidate, device_request_candidate;
        wire request_valid = device_request_candidate;
        wire request_command_valid = at_command_valid;
        wire request_write = at_write;
        wire request_io = at_io;
        wire [23:0] request_address = at_memory_address;
    '''
    route = route_header + features_expand(a5) + '\n' + mapped + '\n'
    route += '    logic '+', '.join(other_names)+', floppy_selected, xtide_selected;\n'
    route += '    wire storage_request_valid = device_storage_candidate;\n'
    route += '    always_comb begin\n'+ '\n'.join(features_expand(s) for s in machine_assignments + router_assignments)+ '\n'+floppy_selected+'\n'+xtide_selected+'\n    end\n'
    route += '''    assign fdc_valid = storage_request_valid && floppy_selected;
        assign fdc_command = request_command_valid && floppy_selected;
        assign fdc_address = request_address;
        assign exclusive = !floppy_selected || !(''' + ' || '.join(n for n in other_names if n != 'device_storage_candidate') + ''' || xtide_selected);
    endmodule
    '''
    (HERE / 'fdc_route.sv').write_text(route)

    bridge_ports = ports(original_bridge)
    fdc_ports = ports(fdc)
    assert len(bridge_ports) == 41
    retained = [('retained_io_command',''), ('retained_io_address','[23:0]'), ('retained_io_write',''),
                ('retained_io_byte_enable','[1:0]'), ('retained_io_data_out','[15:0]'), ('retained_io_data_oe','')]
    observations = [('proof_core_dma_req',''),('proof_core_dma_writedata','[7:0]'),('proof_core_irq',''),
                    ('proof_core_io_readdata','[7:0]'),('proof_core_fdd0_inserted',''),
                    ('proof_core_mgmt_readdata','[15:0]'),('proof_core_request','[1:0]')]

    def observe_fdc(source):
        anchor='    output logic        protocol_error\n);'
        assert source.count(anchor)==1
        extra='\n'.join('    output wire '+(w+' ' if w else '')+n+',' for n,w in observations)
        source=source.replace(anchor,extra+'\n'+anchor,1)
        source=source.replace('.fdd0_inserted   ()', '.fdd0_inserted   (proof_core_fdd0_inserted)',1)
        assigns='\n'.join('    assign '+n+' = '+expr+';' for n,expr in
            [('proof_core_dma_req','fdc_dma_request'),('proof_core_dma_writedata','fdc_dma_writedata'),
             ('proof_core_irq','fdc_irq'),('proof_core_io_readdata','fdc_io_readdata'),
             ('proof_core_mgmt_readdata','fdc_mgmt_readdata'),('proof_core_request','fdc_request')])
        return source.replace('\nendmodule','\n'+assigns+'\nendmodule',1)

    def construct(label, mode, legacy=False, mutant=False):
        root=REF if label=='gold' else GATE
        b=norm(root/'rtl/spk286_integration/spk286_at_bus_bridge.sv')
        f=observe_fdc(norm(root/'rtl/spk286_integration/spk286_at_fdc.sv'))
        core=norm(root/'rtl/common/floppy.v')
        fifo=norm(root/'rtl/common/simple_fifo.v')
        if mutant:
            assert label=='gate'
            needle='wire [2:0] write_address = SEPARATE_IO_WRITE_ADDRESS ? io_write_address : io_address;'
            assert core.count(needle)==1
            core=core.replace(needle, "wire [2:0] write_address = SEPARATE_IO_WRITE_ADDRESS ? (io_write_address ^ 3'b100) : (io_address ^ 3'b100);", 1)
        sources=b+'\n'+f+'\n'+core+'\n'+fifo+'\n'+route
        for old in ('spk286_at_bus_bridge','spk286_at_fdc','floppy','simple_fifo','fdc_route'):
            sources=re.sub(r'\b'+old+r'\b',old+'_'+label,sources)
        top_ports=[]
        bconn=[]
        for direction,width,name in bridge_ports:
            mappedname='bridge_reset' if name=='reset' else 'bridge_protocol_error' if name=='protocol_error' else name
            top_ports.append((direction,width,mappedname))
            bconn.append('.'+name+'('+mappedname+')')
        fconn=[]
        for direction,width,name in fdc_ports:
            if name=='clk':
                expression='clk'
            elif name=='reset':
                expression='fdc_reset'; top_ports.append(('input','',expression))
            elif name.startswith('request_') and direction=='input':
                expression={'request_valid':'route_valid','request_command_valid':'route_command','request_write':'at_write',
                            'request_io':'at_io','request_address':'route_address','request_byte_enable':'at_byte_enable','request_data_out':'at_data_out'}[name]
            else:
                expression='fdc_'+name
                top_ports.append((direction,width,expression))
            fconn.append('.'+name+'('+expression+')')
        for name,width in feature_ports:
            top_ports.append(('input',width,name))
        top_ports.append(('input','','cpu_grant'))
        for name,width in observations:
            top_ports.append(('output',width,name)); fconn.append('.'+name+'('+name+')')
        if legacy:
            top_ports += [('input',w,n) for n,w in retained]
        top_ports.append(('output','','proof_route_exclusive'))
        declaration=',\n'.join('    '+d+' wire '+(w+' ' if w else '')+n for d,w,n in top_ports)
        top='module buffer_'+label+'(\n'+declaration+'\n);\n'
        top+='    wire route_valid, route_command; wire [23:0] route_address;\n'
        if label=='gate':
            if legacy:
                bconn += ['.'+n+'()' for n,_ in retained]
                fconn += ['.'+n+'('+n+')' for n,_ in retained if n!='retained_io_data_oe']
            else:
                top+='\n'.join('    wire '+(w+' ' if w else '')+n+';' for n,w in retained)+'\n'
                bconn += ['.'+n+'('+n+')' for n,_ in retained]
                fconn += ['.'+n+'('+('cpu_grant && '+n if n=='retained_io_command' else n)+')' for n,_ in retained if n!='retained_io_data_oe']
        top+='    spk286_at_bus_bridge_'+label+f' #(.COMPLETE_ON_CPU_SAMPLE({mode})) u_bridge('+',\n'.join(bconn)+');\n'
        route_connections=['.cpu_grant(cpu_grant)']+['.'+n+'('+n+')' for n in ('at_valid','at_command_valid','at_write','at_io','at_address')]
        route_connections += ['.'+n+'('+n+')' for n,_ in feature_ports]
        route_connections += ['.fdc_valid(route_valid)','.fdc_command(route_command)','.fdc_address(route_address)','.exclusive(proof_route_exclusive)']
        top+='    fdc_route_'+label+' u_route('+',\n'.join(route_connections)+');\n'
        param=(" #(.RETAINED_FDC_WRITE(1'b0))" if legacy else " #(.RETAINED_FDC_WRITE(1'b1))") if label=='gate' else ''
        top+='    spk286_at_fdc_'+label+param+' u_fdc('+',\n'.join(fconn)+');\nendmodule\n'
        return sources+'\n'+top

    source = candidate_bridge
    anchor = '    output logic         protocol_error\n);'
    assert source.count(anchor) == 1
    source = source.replace(anchor, '''    input wire proof_cpu_grant,
        input wire proof_fdc_idle,
        output wire proof_contract,
    '''+anchor,1)
    properties='''
        wire proof_old_lane = (!at_address[0] && at_byte_enable == 2'b01) ||
                              (at_address[0] && at_byte_enable == 2'b10);
        wire proof_ret_lane = (!retained_io_address[0] && retained_io_byte_enable == 2'b01) ||
                              (retained_io_address[0] && retained_io_byte_enable == 2'b10);
        wire proof_old_fdc_write = proof_cpu_grant && at_valid && at_io && at_command_valid &&
                                  at_write && proof_fdc_idle && proof_old_lane &&
                                  at_address[15:0] >= 16'h03F0 && at_address[15:0] <= 16'h03F7 &&
                                  at_address[15:0] != 16'h03F6;
        wire proof_new_fdc_write = proof_cpu_grant && retained_io_command && retained_io_write &&
                                  proof_fdc_idle && proof_ret_lane &&
                                  retained_io_address[15:0] >= 16'h03F0 && retained_io_address[15:0] <= 16'h03F7 &&
                                  retained_io_address[15:0] != 16'h03F6;
        assign proof_contract =
            ((at_io && at_command_valid) == retained_io_command) &&
            (!at_io || (at_address == retained_io_address && at_write == retained_io_write &&
                        at_byte_enable == retained_io_byte_enable && at_data_out == retained_io_data_out &&
                        at_data_oe == retained_io_data_oe)) &&
            (proof_old_fdc_write == proof_new_fdc_write) &&
            (!proof_new_fdc_write || (at_address == retained_io_address &&
                                     (at_byte_enable[1] ? at_data_out[15:8] : at_data_out[7:0]) ==
                                     (retained_io_byte_enable[1] ? retained_io_data_out[15:8] : retained_io_data_out[7:0])));
    '''
    source=source.replace('\nendmodule','\n'+properties+'\nendmodule',1)
    negative=source.replace('assign retained_io_address = beat_address;',"assign retained_io_address = beat_address ^ 24'h000004;",1)
    assert negative!=source
    out=HERE/'bridge-contract'
    out.mkdir(exist_ok=False)
    for mode in (0,1):
        case=out/f'mode-{mode}'
        case.mkdir()
        for name,text in [('positive',source),('negative',negative)]:
            (case/(name+'.sv')).write_text(text)
            command=(f'read_verilog -sv -DSYNTHESIS {name}.sv; chparam -set COMPLETE_ON_CPU_SAMPLE {mode} spk286_at_bus_bridge; '
                     'hierarchy -top spk286_at_bus_bridge; proc; flatten; async2sync; opt_clean; '
                     'sat -seq 1 -verify -set-def-inputs -set-init-def -prove proof_contract 1 -show-inputs '
                     '-show at_io,at_command_valid,at_address,retained_io_address,proof_old_fdc_write,proof_new_fdc_write,proof_contract '
                     f'-dump_json {name}-counterexample.json')
            with (case/(name+'.log')).open('w') as log:
                result=subprocess.run(['timeout','300','yosys','-p',command],cwd=case,stdout=log,stderr=subprocess.STDOUT)
            if name=='positive':
                assert result.returncode==0 and 'SUCCESS!' in (case/(name+'.log')).read_text()
            else:
                assert result.returncode not in (0,124) and 'proof did fail' in (case/(name+'.log')).read_text()

    receipt=dict(status='ACTUAL_BRIDGE_RETAINED_FDC_WRITE_CONTRACT_PASS',
        bridge_path=str(GATE/names[0]),bridge_sha256=hashlib.sha256(frozen[GATE/names[0]]).hexdigest(),
        proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        modes=[0,1],scope='Actual bridge. All defined external inputs and arbitrary initial real registers/state, including every state encoding, no reset or protocol assumption. FDC idle and CPU grant arbitrary. Both complete modes. Pure observations added; no combinational cuts.',
        properties='Retained IO fields equal general IO fields; COMMAND qualifier exact; bare FDC range/lane/write pulse exact; accepted write address and byte exact.',
        limitation='Bare bridge delivery contract, not machine/router integration. The separately composed fragment proof must establish old delivery qualifier through the actual source decodes.',
        negative='Actual retained address bit2 inversion rejected with real SAT counterexample, no timeout accepted.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

    source=HERE/'fdc_route.sv'
    raw=source.read_bytes()
    out=HERE/'route-exclusion'
    out.mkdir(exist_ok=False)
    text=source.read_text()
    needle="(request_address[15:0] >= 16'h03F8)"
    assert text.count(needle)==1
    mutant=text.replace(needle,"(request_address[15:0] >= 16'h03F0)",1)
    for name,t in [('positive',text),('negative',mutant)]:
        (out/(name+'.sv')).write_text(t)
        command=(f'read_verilog -sv {name}.sv; hierarchy -top fdc_route; proc; flatten; opt; '
                 f'sat -verify -set-def-inputs -prove exclusive 1 -show-inputs -show-outputs -dump_json {name}-counterexample.json')
        with (out/(name+'.log')).open('w') as log:
            result=subprocess.run(['timeout','300','yosys','-p',command],cwd=out,stdout=log,stderr=subprocess.STDOUT)
        if name=='positive':
            assert result.returncode==0 and 'SUCCESS!' in (out/(name+'.log')).read_text()
        else:
            assert result.returncode not in (0,124) and 'proof did fail' in (out/(name+'.log')).read_text()
    assert source.read_bytes()==raw
    receipt=dict(status='SOURCE_EXTRACTED_FDC_ENDPOINT_EXCLUSION_PASS',
        extracted_decode_sha256=hashlib.sha256(raw).hexdigest(),
        proof_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Actual source-extracted A5/sound/device/storage predicates, with all input bits, compile features and runtime config arbitrary. FDC selected implies no other device decode or ATA3F6 target. No other-candidate=false assumption.',
        outside='Untouched memory decoder video_aperture_select supplied as common arbitrary input. No machine-global or arbitration equivalence assertion.',
        negative='Actual UART1 decode enlarged to3F0..3FF instead3F8..3FF; SAT rejects the resulting overlap with FDC.')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


    results=[]
    command=('read_verilog -sv one-step.v invariant.sv; hierarchy -top invariant; proc; flatten; wreduce; opt -full -keepdc; check -assert; '
             'sat -verify -set-def-inputs -prove step_ok 1 -show relation -show outputs_equal -show next_relation '
             '-show output_matches -show bridge_reset -show fdc_reset -dump_json counterexample.json')
    for profile,legacy in (('active1',False),('default0',True)):
        for mode in (0,1):
            for negative in (False,True):
                case=HERE/profile/f'mode-{mode}'/('negative' if negative else 'positive')
                case.mkdir(parents=True)
                materialize(case,construct('gold',mode,legacy),construct('gate',mode,legacy,negative))
                make(case)
                result=run(case,'transition-proof.log',command,must_pass=not negative)
                if negative:
                    assert result not in (0,124), 'Timeout/success is not a rejected negative control'
                    assert 'proof did fail' in (case/'transition-proof.log').read_text()
                    signals={s['name']:s for s in json.loads((case/'counterexample.json').read_text())['signal']}
                    assert signals['relation']['wave'].startswith('1')
                    assert signals['outputs_equal']['wave'].startswith('0') or signals['next_relation']['wave'].startswith('0')
                else:
                    assert 'SUCCESS!' in (case/'transition-proof.log').read_text()
                    run(case,'reset-proof.log',command.replace('-prove step_ok 1','-prove reset_ok 1'))
                    states=json.loads((case/'one-step-state.json').read_text())['gold']
                    results.append({'profile':profile,'complete_on_cpu_sample':mode,
                                    'state_registers':len(states),'state_bits':sum(states.values())})
    for p,raw in frozen.items():
        assert p.read_bytes()==raw, 'Frozen source or tool changed: '+str(p)
    receipt=dict(status='RETAINED_FDC_WRITE_PORTABLE_EQUIVALENCE_PASS',profiles=results,
        reference_root=str(REF),candidate_root=str(GATE),proof_script_sha256=hashlib.sha256(frozen[tool]).hexdigest(),
        source_sha256=source_guard,
        source_guard='Intrinsic exact six normalized-source deltas, including all routing bindings, default parameters and exact production comments; unchanged actual FIFO. Every frozen original/candidate/tool read remains identical after proving.',
        actual_boundary='Actual bridge plus source-extracted machine/A5/sound/device/storage FDC delivery decodes, actual AT FDC wrapper/common-floppy/simple_fifo. CPU grant and fabric response inputs arbitrary; compile/runtime features arbitrary. Untouched memory decoder video_aperture_select is a common arbitrary boundary input. No global machine or whole-core equivalence claim.',
        original_public_outputs='Every original bridge/wrapper/common-FDC output compared without masks, including unconditional io_readdata. Complete real FF next state compared with common arbitrary current state; type/width/clock/reset descriptors agree. No internal combinational cuts.',
        state_base='Unreset registers and memories have common arbitrary initial contents; source initialization and reset logic unchanged under exact source guards. Bridge/FDC resets independent; reset proofs compare full next-state relation without external protocol assumptions.',
        memory='Full geometry/init/config guards on every actual memory. Eight actual two-entry arrays completely memory-mapped, without downsizing. Actual FIFO1024x8 retained: all clock/reset/enables/read/write addresses compared, WR_DATA per enabled bit with no reset qualifier. Actual FIFO writes during rst_n0 preserved.',
        default0='Both new parameters compiled0; all six new retained inputs are arbitrary shared primary inputs, disconnected from bridge output. No relation or protocol assumption on them. Both COMPLETE modes proved.',
        bridge_contract='Separately proved on actual bridge for every binary initial state/register and input, including invalid state encodings, both modes; actual retained-address negative rejected.',
        decode_exclusion='Separately proved with exact real source predicates for arbitrary features; FDC excludes all other endpoint candidates and IDE3F6. Actual UART1 overlap negative rejected.',
        composed_negative='Actual separate core write-address bit2 inverted in both parameter arms. Real SAT mismatch required for active1/default0 and both completion modes; timeout never accepted.',
        limitations='Defined-input/two-state sampled transitions and stated common-initial-state equivalence coupling. No global machine/arbitration/response-router/CPU/video/ATA equivalence, STA, resource fit, hardware or regression claim.',
        artifacts={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'])

if __name__=='__main__':
    main()
