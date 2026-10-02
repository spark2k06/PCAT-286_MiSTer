"""Link a private 86Box probe with PCAT memory-control RTL; keep release objects intact."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_top(code_lines):
    # Reuse the already validated directed bench's exact memory-chain wiring.
    bench = (ROOT/'sim/spk286_integration/spk286_checkit_workload_tb.sv').read_text()
    wires = bench.split('    wire at_valid,', 1)[1].split('    spk286_machine_cpu cpu (', 1)[0]
    wires = '    wire at_valid,' + wires
    begin = wires.index('    // This reduced harness')
    end = wires.index('    wire [1:0] at_lanes;', begin)
    wires = wires[:begin] + wires[end:]
    chain = bench.split('    spk286_at_bus_bridge bridge (', 1)[1].split('    spk286_sdram_pin_model dram (', 1)[0]
    chain = '    spk286_at_bus_bridge bridge (' + chain
    chain = chain.replace('width_capable && native_width != 0', "1'b1")
    chain = chain.replace(' && !ideal_selected', '')
    assert 'ideal_selected' not in chain
    counters = ['p03_hits', 'p03_misses', 'p03_fills', 'p03_invalidations',
                'data_buffer_hits', 'data_buffer_misses', 'data_buffer_fills',
                'data_buffer_updates']
    # Native debug counters are exposed directly; no extra counter logic lies
    # in production modules, and NO_DEBUG is deliberately absent in this probe.
    return '''`timescale 1ns/1ps
// Timing/control co-simulation only: guest values remain owned by 86Box.
// Constant SDRAM DQ cannot affect cache tags, arbitration or READY sequencing.
module pcat_memory_timing (
    input logic clk, reset, cpu_reset,
    input logic [23:0] address,
    input logic [24:0] mapped_at_address,
    input logic [15:0] data_out,
    input logic data_oe, bus_valid, bus_write, bus_bhe_n, bus_lock,
    input logic [3:0] bus_status,
    output wire ready,
    output wire [15:0] data_in,
    output wire protocol_error,
    output wire idle,
    output wire owner_accept, owner_refresh,
    output wire [1:0] owner_kind,
    output wire [3:0] bridge_state,
''' + ',\n'.join('    output wire [31:0] stat_'+c for c in counters) + '\n);\n' + '''
    integer p03_enable = 1;
    integer data_buffer_enable = 1;
''' + f'    localparam integer CODE_BUFFER_LINES = {code_lines};\n' + wires + chain + '''
    assign memory_out_accept = physical_accept;
    assign memory_out_ready = physical_ready;
    assign memory_out_read_valid = physical_read_valid;
    assign memory_out_read_data = physical_read_data;
    assign dram_in = 16'd0;
    assign protocol_error = bridge_error || port_error || owner_error;
    assign idle = bridge.bridge_idle && physical_idle;
    assign owner_accept = memory_out_valid && memory_out_command && physical_accept;
    assign owner_refresh = owner.kf_refresh_mode;
    assign owner_kind = memory_out_write ? 2'd2 : memory_out_code ? 2'd0 : 2'd1;
    assign bridge_state = bridge.debug_state;
''' + ''.join('    assign stat_'+c+' = '+c+';\n' for c in counters) + 'endmodule\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-dir', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--code-lines', type=int,
                   help='Explicit comparison capacity; default follows PCAT production top')
    a = p.parse_args()
    build, out = a.build_dir.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    production_top = ROOT/'PCAT-286.sv'
    production_text = production_top.read_text()
    production_instance = production_text.split('spk286_at_sdram_read_buffer #(', 1)[1].split(') u_at_sdram_read_buffer', 1)[0]
    capacity = re.search(r'\.LINE_COUNT\((\d+)\)', production_instance)
    production_lines = int(capacity.group(1)) if capacity else 64
    code_lines = a.code_lines if a.code_lines is not None else production_lines
    assert 1 <= code_lines <= 1024 and code_lines & (code_lines-1) == 0
    generated = out/'pcat_memory_timing.sv'
    generated.write_text(generate_top(code_lines))
    source_names = ['spk286_at_bus_bridge', 'spk286_at_mister_memory_port',
                    'spk286_at_sdram_read_buffer', 'spk286_at_sdram_data_buffer',
                    'spk286_at_mister_sdram_owner']
    sources = [ROOT/'rtl/spk286_integration'/f'{name}.sv' for name in source_names]
    sources += [ROOT/'rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv', generated]
    config = (ROOT/'config.tcl').read_text()
    macros = re.findall(r'^\s*set_global_assignment -name VERILOG_MACRO "(SPK286_P\d\d_\w+|SPK286_AT_RAM_READ_BUFFER)"', config, re.M)
    obj = out/'memory-obj'
    commands = [['verilator', '--cc', '--build', '--assert', '-j', '4', '-Wno-fatal',
                 '--top-module', 'pcat_memory_timing', '--prefix', 'Vpcat_memory',
                 '--Mdir', str(obj), '-CFLAGS', '-O3',
                 *(f'-D{m}' for m in macros), *map(str, sources)]]
    original = build.parents[1]/'src/cpu/spk286_backend.cpp'
    private = out/'spk286_backend.cpp'
    text = original.read_text()
    assert text.count('    if (top.bus_valid) {') == 1
    text = text.replace('namespace {', '#include "spk286_memory_probe.hpp"\n\nnamespace {', 1)
    text = text.replace('    top.reset = 1;\n', '    memory_probe.cpu_reset();\n    top.reset = 1;\n', 1)
    text = text.replace('    if (top.bus_valid) {', '    memory_probe.before_tick(top);\n\n    if (top.bus_valid && top.ready) {', 1)
    text = text.replace('    const bool instruction_retired = top.instruction_retired;',
                        '    memory_probe.observe(top);\n    const bool instruction_retired = top.instruction_retired;', 1)
    text = text.replace('    top.clk = 1;\n    top.eval();\n    const bool event_completed',
                        '    top.clk = 1;\n    top.eval();\n    memory_probe.after_tick();\n    const bool event_completed', 1)
    private.write_text(text)
    header = Path(__file__).with_name('spk286_memory_probe.hpp')
    shutil.copyfile(header, out/header.name)
    backend_obj = 'src/cpu/CMakeFiles/cpu.dir/spk286_backend.cpp.o'
    lines = subprocess.check_output(['ninja', '-t', 'commands', backend_obj], cwd=build, text=True).splitlines()
    compile_cmd = shlex.split(next(l for l in lines if f'-o {backend_obj} ' in l))
    compile_cmd[compile_cmd.index('-c')+1] = str(private)
    compile_cmd[compile_cmd.index('-o')+1] = str(out/'probe.o')
    for flag in ('-MF', '-MT'):
        if flag in compile_cmd:
            compile_cmd[compile_cmd.index(flag)+1] = str(out/('probe.o.d' if flag == '-MF' else 'probe.o'))
    compile_cmd += ['-I'+str(header.parent), '-I'+str(original.parent), '-I'+str(obj)]
    commands.append(compile_cmd)
    lines = subprocess.check_output(['ninja', '-t', 'commands', 'src/86Box'], cwd=build, text=True).splitlines()
    link = shlex.split(next(l for l in lines if ' -o src/86Box ' in l))
    if link[:2] == [':', '&&']: link = link[2:]
    if link[-2:] == ['&&', ':']: link = link[:-2]
    link[link.index(backend_obj)] = str(out/'probe.o')
    link[link.index('-o')+1] = str(out/'86Box-memory-probe')
    link.insert(link.index('-o'), str(obj/'Vpcat_memory__ALL.a'))
    commands.append(link)
    inputs = [*sources, original, header, Path(__file__), ROOT/'config.tcl', production_top]
    before = {str(f):digest(f) for f in inputs}
    cpu_objects = sorted((build/'src/cpu/CMakeFiles/cpu.dir/spk286_verilated').glob('*.o'))
    assert cpu_objects, 'No standalone CPU model objects found'
    cpu_before = {str(f):digest(f) for f in cpu_objects}
    with (out/'build.log').open('w') as log:
        for command in commands:
            subprocess.run(command, cwd=build if command != commands[0] else ROOT,
                           check=True, stdout=log, stderr=subprocess.STDOUT)
    assert all(digest(Path(f)) == h for f,h in before.items()), 'Sources changed while building'
    assert all(digest(Path(f)) == h for f,h in cpu_before.items()), 'CPU objects changed while linking'
    (out/'build-manifest.json').write_text(json.dumps({
        'commands':commands, 'sources_sha256':before, 'cpu_objects_sha256':cpu_before, 'macros':macros,
        'code_buffer_lines':code_lines, 'production_code_buffer_lines':production_lines,
        'code_buffer_sync_tags':code_lines > 128, 'data_buffer_words':512,
        'binary_sha256':digest(out/'86Box-memory-probe'),
        'note':'Private adapter only; CPU model and release objects reused unchanged. Guest memory values stay in 86Box.'}, indent=2)+'\n')
    print('MEMORY_PROBE_READY', out/'86Box-memory-probe', flush=True)


if __name__ == '__main__':
    main()
