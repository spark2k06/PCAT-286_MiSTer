#!/usr/bin/env python3
"""Directed real-CPU machine test for posted writes, common and divided clocks.

The existing A20/ROM-sink/IRQ firmware runs through the real machine, port,
queue and physical owner. Cache coherence has its separate directed fixture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, cwd, log, timeout=180):
    with log.open('w') as output:
        subprocess.run(command, cwd=cwd, check=True, timeout=timeout,
                       stdout=output, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pit-refresh', action='store_true',
                        help='Program real PIT channel 1 before the original IRQ diagnostic')
    args = parser.parse_args()
    work, out = args.work.resolve(), args.output.resolve()
    assert not out.exists(), 'Preserve prior checks'
    out.mkdir(parents=True)
    text = (work/'sim/spk286_integration/spk286_at_machine_tb.sv').read_text()
    text = text.replace('module spk286_at_machine_tb;',
        'module spk286_at_machine_tb #(parameter bit CPU_DIV2 = 0);\n'
        '    logic cpu_phase = 0;\n'
        '    always @(posedge clk) cpu_phase <= !cpu_phase;\n'
        '    wire cpu_clock = CPU_DIV2 ? cpu_phase : clk;')
    text = text.replace('    spk286_at_machine dut (',
        '    spk286_at_machine #(.CPU_USES_SAMPLE_EDGE(CPU_DIV2)) dut (')
    text = text.replace('.clk_cpu(clk), .cpu_sample_edge(1\'b1)',
        ".clk_cpu(cpu_clock), .cpu_sample_edge(!CPU_DIV2 || !cpu_phase)")
    # The original fixture observes READY on every parent edge. In /2 mode
    # READY legitimately spans two parent edges, but the CPU samples once.
    # Count I/O acknowledgements only on that sampling edge; retain the exact
    # four POST codes and all original firmware/data success requirements.
    text = text.replace('cpu_ready && cpu_bus_valid',
                        '(!CPU_DIV2 || !cpu_phase) && cpu_ready && cpu_bus_valid')
    text = text.replace('.memory_read_data_valid(memory_read_data_valid),\n        .dma_memory',
        '.memory_read_data_valid(memory_read_data_valid),\n'
        '        .memory_drain_pending(posted_pending),\n        .dma_memory')
    assert '.memory_drain_pending(posted_pending)' in text
    begin = text.index('    spk286_at_mister_sdram_owner #(')
    end = text.index('\n    );', begin) + len('\n    );')
    physical = text[begin:end]
    fields = {'valid':'valid', 'command_valid':'command_valid', 'owner':'owner',
        'write':'write', 'refresh':'refresh', 'code_fetch':'code_fetch',
        'cycle_class':'cycle_class', 'address':'address', 'byte_enable':'byte_enable',
        'data_out':'data_out', 'accept':'accept', 'ready':'ready',
        'read_data':'read_data', 'read_data_valid':'read_data_valid'}
    for field in fields:
        physical = re.sub(r'\bbackend_'+field+r'\b', 'posted_'+field, physical)
    queue = '''
    wire posted_valid, posted_command_valid, posted_write, posted_refresh, posted_code_fetch;
    wire [1:0] posted_owner, posted_byte_enable;
    wire [3:0] posted_cycle_class;
    wire [24:0] posted_address;
    wire [15:0] posted_data_out, posted_read_data;
    wire posted_accept, posted_ready, posted_read_data_valid, posted_pending, posted_error;
    wire [31:0] posted_count, drained_count;
    spk286_at_posted_write_buffer posted (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset_request | cpu_local_reset),
        .cpu_lock(cpu_bus_lock), .in_valid(backend_valid), .in_command_valid(backend_command_valid),
        .in_owner(backend_owner), .in_write(backend_write), .in_refresh(backend_refresh),
        .in_code_fetch(backend_code_fetch), .in_burst(1'b0), .in_cycle_class(backend_cycle_class),
        .in_address(backend_address), .in_byte_enable(backend_byte_enable), .in_data_out(backend_data_out),
        .in_accept(backend_accept), .in_ready(backend_ready), .in_read_data(backend_read_data),
        .in_read_data_valid(backend_read_data_valid),
        .out_valid(posted_valid), .out_command_valid(posted_command_valid), .out_owner(posted_owner),
        .out_write(posted_write), .out_refresh(posted_refresh), .out_code_fetch(posted_code_fetch),
        .out_burst(), .out_cycle_class(posted_cycle_class), .out_address(posted_address),
        .out_byte_enable(posted_byte_enable), .out_data_out(posted_data_out),
        .out_accept(posted_accept), .out_ready(posted_ready), .out_read_data(posted_read_data),
        .out_read_data_valid(posted_read_data_valid), .pending_write(posted_pending), .idle(),
        .protocol_error(posted_error), .debug_post_count(posted_count), .debug_drain_count(drained_count),
        .debug_stall_count()
    );
    always @(posedge clk) if (!reset) begin
        if (posted_error) $fatal(1, "POSTED_MACHINE_QUEUE_ERROR");
        if (posted_pending && (dma_grant || refresh_grant))
            $fatal(1, "POSTED_MACHINE_EXTERNAL_OWNERSHIP_BEFORE_DRAIN");
        if (posted_pending && dut.at_valid && (dut.at_io || dut.at_inta))
            $fatal(1, "POSTED_MACHINE_IO_BEFORE_DRAIN");
    end
'''
    text = text[:begin] + queue + physical + text[end:]
    text = text.replace('                $finish;', '''                if (posted_count == 0 || posted_count != drained_count || posted_pending)
                    $fatal(1, "POSTED_MACHINE_NOT_DRAINED posts=%0d drains=%0d", posted_count, drained_count);
                $display("POSTED_MACHINE_PASS div2=%0d posts=%0d drains=%0d", CPU_DIV2, posted_count, drained_count);
                $finish;''')
    bench = out/'spk286_at_machine_tb.sv'
    bench.write_text(text)
    script = (work/'scripts/test_at_machine_boundary.sh').read_text()
    fixed = script.split('sources+=(\n', 1)[1].split('\n)', 1)[0].splitlines()
    names = ['vendor/spk286/microcode/generated/spk286_microcode_pkg.sv',
             'vendor/spk286/microcode/generated/spk286_microcode_rom.sv',
             'vendor/spk286/microcode/generated/spk286_microcode_sync_rom.sv',
             'vendor/spk286/rtl/spk286_protected_pkg.sv', 'vendor/spk286/rtl/spk286_tss_pkg.sv']
    names += [str(p.relative_to(work)) for p in sorted((work/'vendor/spk286/rtl').glob('*.sv'))
              if str(p.relative_to(work)) not in names]
    names += [line.strip() for line in fixed if line.strip()]
    names += [str(p.relative_to(work)) for p in sorted((work/'rtl/video').iterdir()) if p.suffix in ('.sv', '.v')]
    names += ['rtl/spk286_integration/spk286_at_posted_write_buffer.sv',
              'sim/spk286_integration/spk286_at_machine_pic_model.sv']
    sources = [work/name for name in names] + [bench]
    flags = ['-D'+m for m in re.findall(r'VERILOG_MACRO "(SPK286_P\d\d_[A-Z0-9_]+|SPK286_AT_RAM_READ_BUFFER)"', (work/'config.tcl').read_text())]
    rom = out/'entry.rom'
    firmware = work/'tests/firmware/pcat286_event_diag.asm'
    if args.pit_refresh:
        firmware = out/'entry-pit.asm'
        original = (work/'tests/firmware/pcat286_event_diag.asm').read_text()
        marker = '    ; Program PIT channel 0, mode 2, divisor 0020h.'
        assert original.count(marker) == 1
        firmware.write_text(original.replace(marker, '''    ; Match BIOS initialization of the AT refresh timer.
    mov dx, 0x0043
    mov al, 0x74
    out dx, al
    mov dx, 0x0041
    mov al, 18
    out dx, al
    xor al, al
    out dx, al

'''+marker))
    run(['nasm', '-DENTRY_MEMORY_PROBE=1', '-f', 'bin', '-o', str(rom),
         str(firmware)], work, out/'nasm.log')
    identities = {str(p): sha(p) for p in sources + [rom, work/'config.tcl',
                 firmware, work/'tests/firmware/pcat286_event_diag.asm', ROOT/'tools/perf01/test_posted_machine.py']}
    commands = []
    for div2 in (0, 1):
        directory = out/f'div{div2}'
        directory.mkdir()
        command = ['verilator', '--binary', '--timing', '--assert', '-j', '4', '-Wno-fatal',
            *flags, '-DAT_MACHINE_PIC_MODEL', '-DSPK286_AT_SIM_MODEL',
            '-I'+str(work/'rtl/KFPC-XT/HDL/KF8253/HDL'), '-I'+str(work/'rtl/KFPC-XT/HDL/KF8259/HDL'),
            '--top-module', 'spk286_at_machine_tb', f'-GCPU_DIV2={div2}',
            '--Mdir', str(directory/'obj'), '-o', 'posted_machine', *map(str, sources)]
        commands.append(command)
        (out/'inputs.json').write_text(json.dumps({'sources_sha256': identities, 'commands': commands}, indent=2)+'\n')
        run(command, work, directory/'build.log', 600)
        run([str(directory/'obj/posted_machine'), '+ROM='+str(rom), '+MAX_CYCLES=2000000'],
            work/'rtl/video', directory/'run.log', 120)
        result = (directory/'run.log').read_text()
        assert f'POSTED_MACHINE_PASS div2={div2}' in result
        print(result, end='', flush=True)
    assert all(sha(Path(p)) == h for p, h in identities.items())
    print('POSTED_MACHINE_SOURCE_GUARD_PASS')


if __name__ == '__main__':
    main()
