#!/usr/bin/env python3
"""Build a private 86Box adapter with production AT refresh/HOLD arbitration.

Use PCAT_AT_REFRESH=0/1 with the same binary for future matched controls.
CPU release objects and production sources are never modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def change(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('validated_work', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--build-dir', required=True, type=Path)
    args = parser.parse_args()
    work, out = args.validated_work.resolve(), args.output.resolve()
    assert not out.exists(), 'Keep old experiments intact'
    out.mkdir(parents=True)
    frozen = json.loads((work/'inputs.json').read_text())
    assert all(sha(work/n) == h for n, h in frozen.items())
    source = out/'source'
    shutil.copytree(work, source)
    builder = source/'tools/perf01/build_86box_memory_probe.py'
    text = builder.read_text()
    text = change(text, '    wires = wires[:begin] + wires[end:]', '''    wires = wires[:begin] + wires[end:]
    wires = wires.replace('integer at_refresh_enabled = 0;', 'wire at_refresh_enabled = at_refresh_enable;')
    wires = wires.replace('wire hold_request, cpu_hlda,', 'wire hold_request,')
    wires = wires.replace('    wire [7:0] retiring_opcode;\\n', '')
    wires = wires.replace('    logic final_halt_retired = 0;\\n', '')
    wires = wires.replace("        if (halted && retired && retiring_opcode == 8'hf4) final_halt_retired <= 1;\\n", '')''')
    text = change(text, '    input logic clk, reset, cpu_reset,',
        '    input logic clk, reset, cpu_reset, cpu_hlda, at_refresh_enable,\n'
        '    output wire cpu_hold,\n'
        '    output wire [31:0] stat_hold_clocks, stat_hlda_clocks,\n'
        '    output wire [15:0] stat_at_refresh_count,')
    text = change(text, '    assign pending_write = posted_pending;',
        '    assign cpu_hold = hold_request;\n'
        '    assign stat_hold_clocks = held_clocks;\n'
        '    assign stat_hlda_clocks = hlda_clocks;\n'
        '    assign stat_at_refresh_count = at_refresh_count;\n'
        '    assign pending_write = posted_pending;')
    text = change(text, 'bridge_error || port_error || owner_error || posted_error;',
        'bridge_error || port_error || owner_error || posted_error || refresh_error || arbiter_error;')
    text = change(text, 'bridge.bridge_idle && physical_idle && posted_idle;',
        'bridge.bridge_idle && physical_idle && posted_idle && !refresh_request && !cpu_hlda;')
    text = change(text, 'posted_out_valid && posted_out_command && physical_accept;',
        'posted_out_valid && posted_out_command && physical_accept && !posted_out_refresh;')
    text = change(text, "'spk286_at_mister_sdram_owner', 'spk286_at_posted_write_buffer']",
        "'spk286_at_mister_sdram_owner', 'spk286_at_posted_write_buffer', 'spk286_at_arbiter', 'spk286_at_refresh']")
    builder.write_text(text)
    header = source/'tools/perf01/spk286_memory_probe.hpp'
    text = header.read_text()
    text = change(text, '    const char *path = std::getenv("PCAT_MEMORY_PROFILE");',
        '    bool at_refresh_enabled = std::getenv("PCAT_AT_REFRESH") &&\n'
        '                              std::string(std::getenv("PCAT_AT_REFRESH")) == "1";\n'
        '    const char *path = std::getenv("PCAT_MEMORY_PROFILE");')
    text = change(text, '        caches("shadow_code",code_shadow);',
        r'''        std::fprintf(f,"\"at_refresh_enabled\":%s,\"at_refresh_interval\":32,"
                     "\"hold_clocks\":%u,\"hlda_clocks\":%u,\"at_refresh_count\":%u,",
                     at_refresh_enabled ? "true" : "false", memory.stat_hold_clocks,
                     memory.stat_hlda_clocks, memory.stat_at_refresh_count);
        caches("shadow_code",code_shadow);''')
    text = change(text, '        memory.address=cpu.address;',
        '        memory.cpu_hlda=cpu.hlda;\n'
        '        memory.at_refresh_enable=enabled && at_refresh_enabled;\n'
        '        memory.address=cpu.address;')
    text = change(text, '        cpu.ready = memory.bus_valid ? memory.ready :',
        '        cpu.hold_request = enabled ? memory.cpu_hold : 0;\n'
        '        cpu.ready = memory.bus_valid ? memory.ready :')
    header.write_text(text)
    binary_dir = out/'probe'
    with (out/'build.log').open('w') as log:
        subprocess.run([sys.executable, str(builder), '--build-dir', str(args.build_dir.resolve()),
                        '--output', str(binary_dir), '--code-lines', '512'],
                       check=True, timeout=600, stdout=log, stderr=subprocess.STDOUT)
    assert all(sha(work/n) == h for n, h in frozen.items())
    (out/'inputs.json').write_text(json.dumps({'validated_work_inputs_sha256': sha(work/'inputs.json'),
        'builder_sha256': sha(builder), 'profiler_sha256': sha(header),
        'runtime_control': 'PCAT_AT_REFRESH=0/1; same binary and CPU objects',
        'production_changed': False, 'clock': '50 MHz CPU/system, 32-clock AT requester, native SDRAM refresh unchanged'}, indent=2)+'\n')
    print('AT_REFRESH_86BOX_PROBE_READY', binary_dir/'86Box-memory-probe')


if __name__ == '__main__':
    main()
