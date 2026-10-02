"""Exercise posting with production caches/port and physical SDRAM data."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('experiment', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    candidate = args.experiment.resolve()/'candidate'
    out = args.output.resolve()
    assert not out.exists(), 'Preserve previous results'
    out.mkdir(parents=True)
    bench = (candidate/'sim/spk286_integration/spk286_checkit_workload_tb.sv').read_text()
    wires = '    wire at_valid,' + bench.split('    wire at_valid,', 1)[1].split('    spk286_machine_cpu cpu (', 1)[0]
    replacements = {
        'wire at_valid, at_command, at_write, at_code;': 'logic at_valid = 0, at_command = 0, at_write = 0, at_code = 0;',
        'wire [23:0] at_address;': 'logic [23:0] at_address = 0;',
        'wire [1:0] at_lanes;': 'logic [1:0] at_lanes = 3;',
        'wire [15:0] at_out, at_in;': 'logic [15:0] at_out = 0; wire [15:0] at_in;',
        'wire [3:0] at_class;': 'logic [3:0] at_class = 5;',
    }
    for old, new in replacements.items():
        assert wires.count(old) == 1
        wires = wires.replace(old, new, 1)
    chain = '    spk286_at_mister_memory_port memory_port (' + bench.split('    spk286_at_mister_memory_port memory_port (', 1)[1].split('    integer cycles = 0;', 1)[0]
    replacements = {
        '.cpu_valid(at_valid)': '.cpu_valid(at_valid && driver_owner == 0)',
        '.cpu_accept(at_accept)': '.cpu_accept(owner_accept[0])',
        '.cpu_ready(at_ready)': '.cpu_ready(owner_ready[0])',
        '.cpu_read_data(at_in)': '.cpu_read_data(cpu_data)',
        ".loader_valid(1'b0)": '.loader_valid(at_valid && driver_owner == 3)',
        ".loader_write(1'b0)": '.loader_write(at_write)',
        ".loader_address(24'd0)": '.loader_address(at_address)',
        ".loader_byte_enable(2'b00)": '.loader_byte_enable(at_lanes)',
        ".loader_data_out(16'd0)": '.loader_data_out(at_out)',
        '.loader_accept()': '.loader_accept(owner_accept[3])',
        '.loader_ready()': '.loader_ready(owner_ready[3])',
        '.loader_read_data()': '.loader_read_data(loader_data)',
        ".dma_valid(1'b0)": '.dma_valid(at_valid && driver_owner == 1)',
        ".dma_write(1'b0)": '.dma_write(at_write)',
        ".dma_address(25'd0)": '.dma_address(mapped_at_address)',
        ".dma_byte_enable(2'b00)": '.dma_byte_enable(at_lanes)',
        ".dma_data_out(16'd0)": '.dma_data_out(at_out)',
        '.dma_accept()': '.dma_accept(owner_accept[1])',
        '.dma_ready()': '.dma_ready(owner_ready[1])',
        '.dma_read_data()': '.dma_read_data(dma_data)',
        ".refresh_valid(1'b0)": '.refresh_valid(at_valid && driver_owner == 2)',
        ".refresh_address(24'd0)": '.refresh_address(at_address)',
        '.refresh_accept()': '.refresh_accept(owner_accept[2])',
        '.refresh_ready()': '.refresh_ready(owner_ready[2])',
        '.request_valid(posted_out_valid)': '.request_valid(posted_out_valid && !stall)',
        '.request_command_valid(posted_out_command)': '.request_command_valid(posted_out_command && !stall)',
        'dram (': 'pins (',
    }
    for old, new in replacements.items():
        assert chain.count(old) == 1, old
        chain = chain.replace(old, new, 1)
    top = '''`timescale 1ns/1ps
module posted_cache_tb;
    logic clk = 0, reset = 1, cpu_reset = 1, bus_lock = 0, stall = 0;
    always #10 clk = ~clk;
    localparam integer CODE_BUFFER_LINES = 512, POSTED_WRITES = 1;
    integer p03_enable = 1, data_buffer_enable = 1;
    logic [1:0] driver_owner = 0;
    wire [3:0] owner_accept, owner_ready;
    wire [15:0] cpu_data, dma_data, loader_data;
    integer checks = 0, cycles = 0, stores = 0;
''' + wires + chain + '''
    assign at_accept = owner_accept[driver_owner];
    assign at_ready = owner_ready[driver_owner];
    assign at_in = driver_owner == 1 ? dma_data : driver_owner == 3 ? loader_data : cpu_data;
''' + (ROOT/'tools/perf01/prototypes/posted_cache_stimulus.svh').read_text() + '\nendmodule\n'
    generated = out/'posted_cache_tb.sv'
    generated.write_text(top)
    names = ['spk286_at_mister_memory_port', 'spk286_at_sdram_read_buffer',
             'spk286_at_sdram_data_buffer', 'spk286_at_posted_write_buffer', 'spk286_at_mister_sdram_owner']
    sources = [candidate/'rtl/spk286_integration'/f'{name}.sv' for name in names]
    sources += [candidate/'rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv',
                candidate/'sim/spk286_integration/spk286_sdram_pin_model.sv', generated]
    identity = {str(s): sha(s) for s in sources}
    command = ['verilator', '--binary', '--timing', '--assert', '-j', '4', '-Wno-fatal',
               '--top-module', 'posted_cache_tb', '--Mdir', str(out/'obj'), '-o', 'posted_cache', *map(str, sources)]
    (out/'inputs.json').write_text(json.dumps({'command': command, 'sources_sha256': identity}, indent=2)+'\n')
    with (out/'build.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    with (out/'run.log').open('w') as log:
        subprocess.run([str(out/'obj/posted_cache')], check=True, timeout=45, stdout=log, stderr=subprocess.STDOUT)
    assert all(sha(Path(s)) == h for s, h in identity.items())
    print((out/'run.log').read_text(), end='')
    print('POSTED_CACHE_SOURCE_GUARD_PASS')


if __name__ == '__main__':
    main()
