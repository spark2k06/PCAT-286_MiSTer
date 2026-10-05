#!/usr/bin/env python3
"""Qualify the software-palette RAM address permutation without new latency."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'a73ab7bc4be304a94ea2270b139c8980cf3d11b2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out, label, command, success=None, reject=False):
    result = subprocess.run(list(map(str, command)), cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    log = result.stdout.decode(errors='replace')
    (out / (label + '.log')).write_bytes(result.stdout)
    if reject:
        assert result.returncode and 'proof did fail' in log and 'time out' not in log, label
    else:
        assert result.returncode == 0 and (success is None or success in log), (label, log[-2500:])
    return log


def prove(out, label, text, reject=False):
    rtl = out / (label + '.sv')
    rtl.write_text(text, newline='\n')
    script = out / (label + '.ys')
    script.write_text(f'read_verilog -formal -sv {rtl}\nprep -top miter -flatten\nopt\n'
                      'sat -verify -prove-asserts -timeout 60\n', newline='\n')
    run(out, label, ['yosys', '-Q', '-s', script],
        'SAT proof finished - no model found: SUCCESS!', reject)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    out = parser.parse_args().output.resolve()
    assert out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True, exist_ok=False)
    dac = ROOT / 'rtl/video/vga_dac.v'
    io = ROOT / 'rtl/video/vga_dac_io.v'
    fallback = ROOT / 'rtl/video/ega_vgaport.v'
    bench = ROOT / 'rtl/video/TESTBENCH/vga_dac_memory_tb.v'
    inputs = [Path(__file__), dac, io, fallback, bench, ROOT / 'SYSTEM.sdc', ROOT / 'PCAT-286.qsf']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    source = dac.read_text()
    raw = subprocess.check_output(['git', 'show', f'{REFERENCE}:rtl/video/vga_dac.v'], cwd=ROOT)
    original = raw.decode()
    frozen_frontend = {}
    for unchanged in (io, fallback, bench):
        frozen = subprocess.check_output(['git', 'show', f'{REFERENCE}:{unchanged.relative_to(ROOT).as_posix()}'], cwd=ROOT)
        # Native checkout uses CRLF whereas Git stores LF. Canonical source
        # bytes must match; the receipt separately binds actual disk bytes.
        canonical = unchanged.read_bytes().replace(b'\r\n', b'\n')
        assert canonical == frozen.replace(b'\r\n', b'\n'), f'Unqualified frontend/expected-data change: {unchanged}'
        frozen_frontend[unchanged.relative_to(ROOT).as_posix()] = hashlib.sha256(canonical).hexdigest()
    block_start = source.index('    // Store software colours through a bijective address transform.')
    block_end = source.index('    wire red_write', block_start)
    recovered = source[:block_start] + source[block_end:]
    for side in ('sample', 'port'):
        for colour in ('red', 'green', 'blue'):
            recovered = recovered.replace(f'{side}_{colour}_ram[encoded_write_index]',
                                          f'{side}_{colour}_ram[ram_write_index]')
            recovered = recovered.replace(f'{side}_{colour}_ram[encoded_{side}_index]',
                                          f'{side}_{colour}_ram[{side}_index]')
    assert recovered == original, 'Unexpected source/state/default/bypass change'
    assert source.count('_ram[encoded_write_index]') == 6
    assert source.count('_ram[encoded_sample_index]') == 3
    assert source.count('_ram[encoded_port_index]') == 3
    function = source[source.index('    function [7:0] palette_ram_address;'):
                      source.index('    endfunction', block_start) + len('    endfunction')]
    formal = '''module miter (
    input [7:0] logical_write, logical_sample, logical_port, watched_index,
    input [2:0] enables,
    input [17:0] old_row, write_data
);
''' + function + '''
    wire [7:0] physical_write = palette_ram_address(logical_write);
    wire [7:0] physical_sample = palette_ram_address(logical_sample);
    wire [7:0] physical_port = palette_ram_address(logical_port);
    wire [7:0] physical_watched = palette_ram_address(watched_index);
    // An arbitrary logical row is related to its encoded physical row.
    // Identical write-decoder decisions preserve that relation at each edge
    // for every row/data/enable; identical read decisions preserve both ports.
    wire [17:0] legacy_next, encoded_next;
    genvar colour;
    generate for (colour = 0; colour < 3; colour = colour + 1) begin : g_row
        assign legacy_next[colour*6 +: 6] = enables[colour] && logical_write == watched_index ?
                                            write_data[colour*6 +: 6] : old_row[colour*6 +: 6];
        assign encoded_next[colour*6 +: 6] = enables[colour] && physical_write == physical_watched ?
                                             write_data[colour*6 +: 6] : old_row[colour*6 +: 6];
    end endgenerate
    always @* begin
        assert((logical_write == watched_index) == (physical_write == physical_watched));
        assert((logical_sample == watched_index) == (physical_sample == physical_watched));
        assert((logical_port == watched_index) == (physical_port == physical_watched));
        assert(legacy_next == encoded_next);
    end
endmodule
'''
    prove(out, 'actual-address-and-row-relation', formal)
    unsafe = formal.replace('logical_index[7] ^ logical_index[0] ^ logical_index[1]', "1'b0")
    assert unsafe != formal
    prove(out, 'unsafe-address-collision', unsafe, reject=True)
    encoding = lambda x: ((x ^ (x >> 1)) & 127) | ((((x >> 7) ^ x ^ (x >> 1)) & 1) << 7)
    permutation = [encoding(x) for x in range(256)]
    assert len(set(permutation)) == 256
    for bit in range(8):
        for operand in range(8):
            dependent = any(((encoding(x) ^ encoding(x ^ (1 << operand))) >> bit) & 1 for x in range(256))
            assert dependent == (operand in ([bit, bit + 1] if bit < 7 else [7, 0, 1]))
    (out / 'permutation.json').write_text(json.dumps(permutation) + '\n', newline='\n')
    strict = out / 'palette_address_encoder.sv'
    strict.write_text('module palette_address_encoder(input wire [7:0] source_index, output wire [7:0] physical_index);\n'
                      + function + '\nassign physical_index = palette_ram_address(source_index);\nendmodule\n', newline='\n')
    run(out, 'encoder-strict-lint', ['verilator', '--lint-only', '--Wall', '--top-module', 'palette_address_encoder', strict])
    old_dac = out / 'reference_vga_dac.v'
    old_dac.write_text(original.replace('module vga_dac(', 'module reference_vga_dac(', 1), newline='\n')
    old_io = out / 'reference_vga_dac_io.v'
    old_io.write_text(io.read_text().replace('module vga_dac_io(', 'module reference_vga_dac_io(', 1)
                      .replace('    vga_dac dac (', '    reference_vga_dac dac (', 1), newline='\n')
    # Full frontend has two pre-existing warning classes. Confirm the exact
    # fatal diagnostics against frozen production before scoped waiver lint.
    lint_base = ['verilator', '--lint-only', '--Wall', '--top-module']
    old_lint = subprocess.run(lint_base + ['reference_vga_dac_io', str(old_dac), str(old_io), str(fallback)], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    new_lint = subprocess.run(lint_base + ['vga_dac_io', str(dac), str(io), str(fallback)], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / 'baseline-full-strict-lint.log').write_bytes(old_lint.stdout)
    (out / 'candidate-full-strict-lint.log').write_bytes(new_lint.stdout)
    warning_counts = lambda data: re.findall(r'%Warning-(\w+):', data.decode())
    assert warning_counts(old_lint.stdout) == warning_counts(new_lint.stdout) == ['DECLFILENAME'] + ['WIDTHTRUNC'] * 9
    def diagnostic_messages(data):
        return re.findall(r'^%Warning-(\w+): [^:\n]+:\d+:\d+: ([^\n]+)', data.decode(), re.M)
    assert diagnostic_messages(old_lint.stdout) == diagnostic_messages(new_lint.stdout)
    # Every width warning belongs to the unchanged default-palette function.
    assert old_lint.stdout.decode().count('position = index -') == new_lint.stdout.decode().count('position = index -') == 9
    anchors = lambda data: re.findall(r'^\s*\d+\s*\|\s*(position = index - [^\n]+)', data.decode(), re.M)
    assert anchors(old_lint.stdout) == anchors(new_lint.stdout)
    run(out, 'frontend-scoped-fatal-lint', lint_base + ['vga_dac_io', '-Wno-DECLFILENAME', '-Wno-WIDTHTRUNC', dac, io, fallback])
    for tag, module in (('candidate', dac), ('reference', old_dac)):
        old_bench = out / f'{tag}-memory-tb.sv'
        old_bench.write_text(bench.read_text().replace('    vga_dac dut (',
            '    reference_vga_dac dut (' if tag == 'reference' else '    vga_dac dut (', 1), newline='\n')
        binary = out / f'{tag}-memory.vvp'
        run(out, tag + '-memory-icarus-build', ['iverilog', '-g2012', '-s', 'vga_dac_memory_tb', '-o', binary, module, old_bench])
        run(out, tag + '-memory-icarus', ['vvp', binary], 'PASS vga_dac_memory_tb')
        obj = out / f'{tag}-memory-verilator'
        run(out, tag + '-memory-verilator-build', ['verilator', '--binary', '--timing', '-Wno-fatal',
            '--top-module', 'vga_dac_memory_tb', '--Mdir', obj, '-o', 'sim', module, old_bench])
        run(out, tag + '-memory-verilator', [obj / 'sim'], 'PASS vga_dac_memory_tb')
    paired = out / 'palette_io_equivalence_tb.sv'
    ports = io.read_text()[io.read_text().index('module vga_dac_io('):io.read_text().index(');')]
    names = re.findall(r'(?:input|output)\s+(?:wire|reg)\s+(?:\[[^]]+\]\s+)?(\w+)', ports)
    output_names = ['io_data_out', 'sample_red', 'sample_green', 'sample_blue',
                    'sample_red_8', 'sample_green_8', 'sample_blue_8', 'sample_valid']
    widths = [8, 6, 6, 6, 8, 8, 8, 1]
    wires = '\n'.join(f'wire [{width-1}:0] {tag}_{name};'
                      for tag in ('candidate', 'reference') for name, width in zip(output_names, widths))
    def pins(tag):
        return ','.join(f'.{name}({tag}_{name})' if name in output_names else f'.{name}({name})' for name in names)
    checks = '\n'.join(f'if(candidate_{name} !== reference_{name}) $fatal(1,"Mismatch {name}");' for name in output_names)
    paired.write_text('''`timescale 1ns/1ps
module palette_io_equivalence_tb;
reg clock = 0; always #5 clock = ~clock;
reg reset=0, load_defaults=0, invalidate=0, palette_64_mode=0;
reg read_index_write=0, write_index_write=0, data_write=0;
reg read_index_read=0, write_index_read=0, data_read=0;
reg [7:0] io_data_in=0, sample_index=0;
integer i, component, cycles=0;
''' + wires + '\nvga_dac_io candidate(' + pins('candidate') + ');\nreference_vga_dac_io reference(' + pins('reference') + ');\n' + '''
task tick; begin
    @(posedge clock); #1;
''' + checks + '''
    cycles=cycles+1;
end endtask
task idle; begin
    read_index_write=0; write_index_write=0; data_write=0;
    read_index_read=0; write_index_read=0; data_read=0;
end endtask
initial begin
    reset=1; tick(); reset=0; load_defaults=1; tick(); load_defaults=0;
    for(i=0;i<256;i=i+1) begin
        idle(); write_index_write=1; io_data_in=i[7:0]; sample_index=i[7:0]; tick();
        for(component=0;component<3;component=component+1) begin
            idle(); data_write=1; io_data_in=(i[7:0] ^ 8'(component*21)); tick();
            idle(); tick();
        end
    end
    for(i=0;i<256;i=i+1) begin
        idle(); read_index_write=1; io_data_in=i[7:0]; sample_index=i[7:0]^8'h5a; tick();
        for(component=0;component<3;component=component+1) begin
            idle(); data_read=1; tick(); tick(); idle(); tick();
        end
    end
    for(i=0;i<768;i=i+1) begin
        {load_defaults,invalidate,palette_64_mode,read_index_write,write_index_write,data_write,
         read_index_read,write_index_read,data_read}=9'(i ^ (i>>3));
        io_data_in=i[7:0]^8'hc5; sample_index=i[7:0]^8'h53;
        reset=(i%101==0); tick();
    end
    idle(); reset=1; tick(); reset=0; tick();
    $display("PALETTE_IO_EQUIVALENCE_PASS %0d cycles",cycles); $finish;
end
endmodule
''', newline='\n')
    all_sources = [dac, io, fallback, old_dac, old_io, paired]
    binary = out / 'paired-io.vvp'
    run(out, 'paired-io-icarus-build', ['iverilog', '-g2012', '-s', 'palette_io_equivalence_tb', '-o', binary, *all_sources])
    io_icarus = run(out, 'paired-io-icarus', ['vvp', binary], 'PALETTE_IO_EQUIVALENCE_PASS')
    obj = out / 'paired-io-verilator'
    run(out, 'paired-io-verilator-build', ['verilator', '--binary', '--timing', '-Wno-fatal',
        '--top-module', 'palette_io_equivalence_tb', '--Mdir', obj, '-o', 'sim', *all_sources])
    io_verilator = run(out, 'paired-io-verilator', [obj / 'sim'], 'PALETTE_IO_EQUIVALENCE_PASS')
    assert re.search(r'PALETTE_IO_EQUIVALENCE_PASS \d+ cycles', io_icarus)[0] == re.search(r'PALETTE_IO_EQUIVALENCE_PASS \d+ cycles', io_verilator)[0]
    assert hashes == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    receipt = {
        'status': 'PALETTE_ADDRESS_ENCODING_EQUIVALENCE_PASS', 'sources_sha256': hashes,
        'reference_revision': REFERENCE, 'reference_sha256': hashlib.sha256(raw).hexdigest(),
        'frozen_frontend_canonical_sha256': frozen_frontend,
        'source_delta': 'Only bijective encoder, six software RAM writes and six software RAM reads; byte-exact undo restores production. All state/defaultROM/bypass/override expressions unchanged.',
        'formal': 'Actual source encoder proves all arbitrary address equality decisions and write/read mapped-row relation for each colour, every enable/data; all256 indices exhaustive; collision mutant rejected',
        'strict_lint': 'Actual encoder --Wall fatal no warnings; whole frontend fatal with only preexisting DECLFILENAME/WIDTHTRUNC classes waived after baseline comparison',
        'existing_memory_bench': 'Candidate and frozen original both PASS under Icarus and Verilator; existing expected data unchanged',
        'io_equivalence': re.search(r'PALETTE_IO_EQUIVALENCE_PASS \d+ cycles', io_icarus)[0],
        'new_state_bits': 0, 'new_cycles': 0, 'physical_acceptance': 'MLAB inference and four-corner setup/hold require combined fit',
        'artifacts_sha256': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    print('PALETTE_ADDRESS_ENCODING_EQUIVALENCE_PASS', flush=True)


if __name__ == '__main__':
    main()
