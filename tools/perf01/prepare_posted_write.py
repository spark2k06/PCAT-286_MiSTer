"""Freeze matched P17/one-entry-posting experiments, without changing production RTL."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def replace(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new, 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists(), 'Keep earlier experiments intact'
    qip = 'rtl/spk286_integration/spk286_integration.qip'
    names = ['PCAT-286.sv', 'config.tcl', qip]
    names += re.findall(r'SYSTEMVERILOG_FILE "(vendor/[^\"]+\.sv)"', (ROOT/qip).read_text())
    names += [str(p.relative_to(ROOT)) for p in (ROOT/'tests/firmware').glob('checkit_*.asm')]
    names += [
        'rtl/spk286_integration/spk286_machine_cpu.sv',
        'rtl/spk286_integration/spk286_at_memory_decode.sv',
        'rtl/spk286_integration/spk286_at_bus_bridge.sv',
        'rtl/spk286_integration/spk286_at_mister_memory_port.sv',
        'rtl/spk286_integration/spk286_at_sdram_read_buffer.sv',
        'rtl/spk286_integration/spk286_at_sdram_data_buffer.sv',
        'rtl/spk286_integration/spk286_at_mister_sdram_owner.sv',
        'rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv',
        'sim/spk286_integration/spk286_checkit_workload_tb.sv',
        'sim/spk286_integration/spk286_checkit_profile.svh',
        'sim/spk286_integration/spk286_checkit_ideal_owner.svh',
        'sim/spk286_integration/spk286_sdram_pin_model.sv',
        'scripts/test_checkit_directed.sh', 'scripts/at_performance_flags.sh',
        'tools/perf01/build_86box_memory_probe.py',
        'tools/perf01/spk286_memory_probe.hpp',
    ]
    prototype = 'tools/perf01/prototypes/spk286_at_posted_write_buffer.sv'
    before = {n: sha(ROOT/n) for n in names + [prototype]}
    for arm, enabled in (('baseline', 0), ('candidate', 1)):
        directory = out/arm
        for name in names:
            target = directory/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
        shutil.copyfile(ROOT/prototype, directory/'rtl/spk286_integration/spk286_at_posted_write_buffer.sv')
        bridge = directory/'rtl/spk286_integration/spk286_at_bus_bridge.sv'
        replace(bridge, '    input  logic         cpu_bus_lock,',
                '    input  logic         cpu_bus_lock,\n'
                '    input  logic         memory_drain_pending,')
        replace(bridge, '    logic [23:0] beat_address;',
                "    wire drain_pending = memory_drain_pending === 1'b1;\n"
                '    wire drain_barrier = drain_pending &&\n'
                '                         (cpu_bus_lock || !memory_native_word_request);\n\n'
                '    logic [23:0] beat_address;')
        replace(bridge, 'memory_native_word_request && live_request_valid;',
                'memory_native_word_request && live_request_valid && !drain_barrier;')
        replace(bridge, 'if (cpu_bus_valid) begin', 'if (cpu_bus_valid && !drain_barrier) begin')
        replace(bridge, 'assign bridge_idle       = (state_q == STATE_IDLE) && !early_memory_address;',
                'assign bridge_idle       = (state_q == STATE_IDLE) && !early_memory_address && !drain_pending;')

        bench = directory/'sim/spk286_integration/spk286_checkit_workload_tb.sv'
        replace(bench, 'parameter integer CODE_BUFFER_LINES = 64',
                f'parameter integer CODE_BUFFER_LINES = 64,\n    parameter integer POSTED_WRITES = {enabled}')
        replace(bench, '    wire [31:0] data_buffer_hits, data_buffer_misses, data_buffer_fills, data_buffer_updates;',
                '''    wire [31:0] data_buffer_hits, data_buffer_misses, data_buffer_fills, data_buffer_updates;
    wire posted_pending, posted_idle, posted_error;
    wire posted_out_valid, posted_out_command, posted_out_write, posted_out_refresh;
    wire posted_out_code, posted_out_burst;
    wire [1:0] posted_out_owner, posted_out_lanes;
    wire [3:0] posted_out_class;
    wire [24:0] posted_out_address;
    wire [15:0] posted_out_data;
    wire [31:0] posted_count, drained_count, posted_stalls;''')
        replace(bench, '.cpu_bus_status(bus_status), .cpu_bus_lock(bus_lock),',
                '.cpu_bus_status(bus_status), .cpu_bus_lock(bus_lock),\n'
                '        .memory_drain_pending(posted_pending),')
        marker = '    spk286_at_mister_sdram_owner #(.SDRAM_INIT_WAIT(16\'d8)) owner ('
        queue = '''    spk286_at_posted_write_buffer #(.ENABLE(POSTED_WRITES != 0)) posted_buffer (
        .clk(clk), .reset(reset), .cancel_cpu(cpu_reset), .cpu_lock(bus_lock),
        .in_valid(memory_out_valid), .in_command_valid(memory_out_command),
        .in_owner(memory_out_owner), .in_write(memory_out_write),
        .in_refresh(memory_out_refresh), .in_code_fetch(memory_out_code),
        .in_burst(memory_out_burst), .in_cycle_class(memory_out_class),
        .in_address(memory_out_address), .in_byte_enable(memory_out_lanes),
        .in_data_out(memory_out_data), .in_accept(memory_out_accept),
        .in_ready(memory_out_ready), .in_read_data(memory_out_read_data),
        .in_read_data_valid(memory_out_read_valid),
        .out_valid(posted_out_valid), .out_command_valid(posted_out_command),
        .out_owner(posted_out_owner), .out_write(posted_out_write),
        .out_refresh(posted_out_refresh), .out_code_fetch(posted_out_code),
        .out_burst(posted_out_burst), .out_cycle_class(posted_out_class),
        .out_address(posted_out_address), .out_byte_enable(posted_out_lanes),
        .out_data_out(posted_out_data), .out_accept(physical_accept),
        .out_ready(physical_ready), .out_read_data(physical_read_data),
        .out_read_data_valid(physical_read_valid),
        .pending_write(posted_pending), .idle(posted_idle), .protocol_error(posted_error),
        .debug_post_count(posted_count), .debug_drain_count(drained_count),
        .debug_stall_count(posted_stalls)
    );

'''
        replace(bench, marker, queue + marker)
        text = bench.read_text()
        begin = text.index(marker)
        end = text.index('    spk286_sdram_pin_model dram (', begin)
        owner = text[begin:end].replace('memory_out_', 'posted_out_').replace(' && !ideal_selected', '')
        text = text[:begin] + owner + text[end:]
        bench.write_text(text)
        replace(bench, '`include "sim/spk286_integration/spk286_checkit_ideal_owner.svh"',
                'integer ideal_owner_mode = 0;\n    integer data_cache_hits = 0;\n'
                '    integer data_cache_misses = 0;\n    integer data_cache_write_updates = 0;')
        replace(bench, 'if (bridge_error || port_error || owner_error || control_error ||',
                'if (bridge_error || port_error || owner_error || posted_error || control_error ||')
        replace(bench, '            if (halted) begin',
                '            if (halted && posted_idle && physical_idle) begin')
        replace(bench, '                report_stage();\n                if (profile_enable',
                '                $display("POSTED_RESULT enabled=%0d posted=%0d drained=%0d blocked=%0d",\n'
                '                    POSTED_WRITES, posted_count, drained_count, posted_stalls);\n'
                '                report_stage();\n                if (profile_enable')
        replace(bench, 'if (ideal_owner_mode < 0 || ideal_owner_mode > 6)', 'if (ideal_owner_mode != 0)')
        profile = directory/'sim/spk286_integration/spk286_checkit_profile.svh'
        # Owner counters follow physical completion, not the new logical ACK.
        replace(profile, 'if (memory_out_command && memory_out_accept) begin',
                'if (posted_out_command && physical_accept) begin')
        replace(profile, 'profile_owner_kind = memory_out_write ? 2 : memory_out_burst ? 0 : 1;',
                'profile_owner_kind = posted_out_write ? 2 : posted_out_burst ? 0 : 1;')
        replace(profile, 'if (memory_out_ready) begin', 'if (physical_ready) begin')
        runner = directory/'scripts/test_checkit_directed.sh'
        replace(runner, '  rtl/spk286_integration/spk286_at_mister_sdram_owner.sv',
                '  rtl/spk286_integration/spk286_at_posted_write_buffer.sv\n'
                '  rtl/spk286_integration/spk286_at_mister_sdram_owner.sv')

        builder = directory/'tools/perf01/build_86box_memory_probe.py'
        replace(builder, "    chain = '    spk286_at_bus_bridge bridge (' + chain",
                "    chain = '    spk286_at_bus_bridge bridge (' + chain\n"
                "    posted = int(re.search(r'POSTED_WRITES = (\\d+)', bench).group(1))\n"
                "    chain = chain.replace('POSTED_WRITES != 0', str(posted))")
        replace(builder, '    output wire idle,',
                '    output wire idle, pending_write,\n'
                '    output wire [31:0] stat_posted_count, stat_drained_count, stat_posted_stalls,')
        replace(builder, '''    assign memory_out_accept = physical_accept;
    assign memory_out_ready = physical_ready;
    assign memory_out_read_valid = physical_read_valid;
    assign memory_out_read_data = physical_read_data;
''', '''    assign pending_write = posted_pending;
    assign stat_posted_count = posted_count;
    assign stat_drained_count = drained_count;
    assign stat_posted_stalls = posted_stalls;
''')
        replace(builder, 'assign protocol_error = bridge_error || port_error || owner_error;',
                'assign protocol_error = bridge_error || port_error || owner_error || posted_error;')
        replace(builder, 'assign idle = bridge.bridge_idle && physical_idle;',
                'assign idle = bridge.bridge_idle && physical_idle && posted_idle;')
        replace(builder, 'assign owner_accept = memory_out_valid && memory_out_command && physical_accept;',
                'assign owner_accept = posted_out_valid && posted_out_command && physical_accept;')
        replace(builder, "assign owner_kind = memory_out_write ? 2'd2 : memory_out_code ? 2'd0 : 2'd1;",
                "assign owner_kind = posted_out_write ? 2'd2 : posted_out_code ? 2'd0 : 2'd1;")
        replace(builder, "                    'spk286_at_mister_sdram_owner']",
                "                    'spk286_at_mister_sdram_owner', 'spk286_at_posted_write_buffer']")
        header = directory/'tools/perf01/spk286_memory_probe.hpp'
        replace(header, 'cpu.ready = memory.bus_valid ? memory.ready : 1;',
                'cpu.ready = memory.bus_valid ? memory.ready :\n'
                '                    enabled && memory.pending_write ? 0 : 1;')
        replace(header, '        caches("shadow_code",code_shadow);',
                '        std::fprintf(f,"\\\"posted_writes\\\":%u,\\\"posted_drains\\\":%u,\\\"posted_blocked\\\":%u,",\n'
                '                     memory.stat_posted_count, memory.stat_drained_count, memory.stat_posted_stalls);\n'
                '        caches("shadow_code",code_shadow);')

    variants = {v: {str(p.relative_to(out/v)): sha(p) for p in sorted((out/v).rglob('*')) if p.is_file()}
                for v in ('baseline', 'candidate')}
    changed = [n for n in variants['baseline'] if variants['baseline'][n] != variants['candidate'][n]]
    assert changed == ['sim/spk286_integration/spk286_checkit_workload_tb.sv'], changed
    assert all(sha(ROOT/n) == h for n, h in before.items())
    receipt = {'created_from_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'original_sha256': before, 'variant_sha256': variants,
               'changed_between_variants': changed, 'production_rtl_modified': False,
               'scope': 'Same P17 CPU/cache/SDRAM inputs; matched one-entry posting enable control; physical pin data in kernels.'}
    (out/'source-manifest.json').write_text(json.dumps(receipt, indent=2)+'\n')
    patch = ''.join(''.join(difflib.unified_diff((ROOT/n).read_text().splitlines(True),
                 (out/'candidate'/n).read_text().splitlines(True), fromfile='production/'+n,
                 tofile='candidate/'+n)) for n in names if sha(ROOT/n) != sha(out/'candidate'/n))
    (out/'candidate.patch').write_text(patch)
    print('POSTED_WRITE_PRIVATE_SOURCES_READY', out, flush=True)


if __name__ == '__main__':
    main()
