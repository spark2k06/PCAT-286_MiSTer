"""Prepare a full private machine candidate from the measured posting prototype."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def change(path, old, new):
    text = path.read_text()
    assert text.count(old) == 1, (path, old)
    path.write_text(text.replace(old, new, 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    experiment, out = args.experiment.resolve(), args.output.resolve()
    measured = experiment/'candidate'
    receipt = json.loads((experiment/'source-manifest.json').read_text())
    assert all(sha(measured/n) == h for n, h in receipt['variant_sha256']['candidate'].items())
    subprocess.run([sys.executable, str(ROOT/'scripts/p05_snapshot.py'), str(out), '--revision', 'PCAT-286'], check=True)
    work = out/'work'
    frozen = json.loads((out/'manifest.json').read_text())
    copied = ['rtl/spk286_integration/spk286_at_bus_bridge.sv',
              'rtl/spk286_integration/spk286_at_posted_write_buffer.sv',
              'sim/spk286_integration/spk286_checkit_workload_tb.sv',
              'sim/spk286_integration/spk286_checkit_profile.svh', 'scripts/test_checkit_directed.sh']
    for name in copied:
        shutil.copyfile(measured/name, work/name)
    qip = work/'rtl/spk286_integration/spk286_integration.qip'
    change(qip, 'set_global_assignment -name SYSTEMVERILOG_FILE "rtl/spk286_integration/spk286_at_mister_sdram_owner.sv"',
           'set_global_assignment -name SYSTEMVERILOG_FILE "rtl/spk286_integration/spk286_at_posted_write_buffer.sv"\n'
           'set_global_assignment -name SYSTEMVERILOG_FILE "rtl/spk286_integration/spk286_at_mister_sdram_owner.sv"')
    machine = work/'rtl/spk286_integration/spk286_at_machine.sv'
    change(machine, '    input  logic         memory_read_data_valid,',
           '    input  logic         memory_read_data_valid,\n'
           '    // Older posted RAM writes fence I/O, LOCK and external ownership.\n'
           '    input  logic         memory_drain_pending,')
    change(machine, '        .cpu_bus_lock           (cpu_bus_lock),',
           '        .cpu_bus_lock           (cpu_bus_lock),\n'
           '        .memory_drain_pending   (memory_drain_pending),')
    top = work/'PCAT-286.sv'
    change(top, '    spk286_at_mister_sdram_owner u_at_sdram_owner (', '''    // One ordinary CPU store may complete logically after retention. Both
    // coherent buffers have observed it before another hit can complete. Any
    // access reaching SDRAM waits for drain; the bridge fences I/O/LOCK/DMA.
    wire at_posted_write_pending, posted_buffer_idle, posted_buffer_error;
    wire physical_owner_idle;
    wire posted_out_valid, posted_out_command, posted_out_write, posted_out_refresh;
    wire posted_out_code, posted_out_burst;
    wire [1:0] posted_out_owner, posted_out_lanes;
    wire [3:0] posted_out_class;
    wire [24:0] posted_out_address;
    wire [15:0] posted_out_data;
    spk286_at_posted_write_buffer u_at_posted_write_buffer (
        .clk(CLK_50M), .reset(RESET),
        .cancel_cpu(at_machine_reset | at_cpu_reset_request), .cpu_lock(at_cpu_bus_lock),
        .in_valid(ram_out_valid), .in_command_valid(ram_out_command),
        .in_owner(ram_out_owner), .in_write(ram_out_write), .in_refresh(ram_out_refresh),
        .in_code_fetch(ram_out_code), .in_burst(ram_out_burst), .in_cycle_class(ram_out_class),
        .in_address(ram_out_address), .in_byte_enable(ram_out_lanes), .in_data_out(ram_out_data),
        .in_accept(ram_out_accept), .in_ready(ram_out_ready), .in_read_data(ram_out_read_data),
        .in_read_data_valid(ram_out_read_valid),
        .out_valid(posted_out_valid), .out_command_valid(posted_out_command),
        .out_owner(posted_out_owner), .out_write(posted_out_write), .out_refresh(posted_out_refresh),
        .out_code_fetch(posted_out_code), .out_burst(posted_out_burst), .out_cycle_class(posted_out_class),
        .out_address(posted_out_address), .out_byte_enable(posted_out_lanes), .out_data_out(posted_out_data),
        .out_accept(physical_accept), .out_ready(physical_ready), .out_read_data(physical_read_data),
        .out_read_data_valid(physical_read_data_valid),
        .pending_write(at_posted_write_pending), .idle(posted_buffer_idle), .protocol_error(posted_buffer_error),
        .debug_post_count(), .debug_drain_count(), .debug_stall_count()
    );
    wire physical_accept, physical_ready, physical_read_data_valid;
    wire [15:0] physical_read_data;
    // Phase/frequency changes require both the queue and physical owner idle.
    assign physical_idle = physical_owner_idle && posted_buffer_idle;
    spk286_at_mister_sdram_owner u_at_sdram_owner (''')
    text = top.read_text()
    begin = text.index('    spk286_at_mister_sdram_owner u_at_sdram_owner (')
    end = text.index('\n    );', begin) + len('\n    );')
    owner = text[begin:end]
    for old, new in [('ram_out_valid', 'posted_out_valid'), ('ram_out_command', 'posted_out_command'),
                     ('ram_out_refresh', 'posted_out_refresh'), ('ram_out_write', 'posted_out_write'),
                     ('ram_out_code', 'posted_out_code'), ('ram_out_burst', 'posted_out_burst'),
                     ('ram_out_class', 'posted_out_class'), ('ram_out_address', 'posted_out_address'),
                     ('ram_out_lanes', 'posted_out_lanes'), ('ram_out_data', 'posted_out_data'),
                     ('ram_out_accept', 'physical_accept'), ('ram_out_ready', 'physical_ready'),
                     ('ram_out_read_data', 'physical_read_data'), ('ram_out_read_valid', 'physical_read_data_valid'),
                     ('(physical_idle)', '(physical_owner_idle)')]:
        owner = owner.replace(old, new)
    top.write_text(text[:begin] + owner + text[end:])
    change(top, '        .memory_read_data_valid (cpu_memory_read_data_valid),',
           '        .memory_read_data_valid (cpu_memory_read_data_valid),\n'
           '        .memory_drain_pending   (at_posted_write_pending),')
    # Two existing diagnostics combine the physical backend flags.
    text = top.read_text()
    assert text.count('                          memory_port_protocol_error |') == 2
    top.write_text(text.replace('                          memory_port_protocol_error |',
                  '                          memory_port_protocol_error |\n'
                  '                          posted_buffer_error |'))
    tools = ['build_86box_memory_probe.py', 'spk286_memory_probe.hpp']
    for name in tools:
        target = work/'tools/perf01'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(measured/'tools/perf01'/name, target)
    differences = {n: sha(work/n) for n, h in frozen['source_sha256'].items() if sha(work/n) != h}
    expected = {'PCAT-286.sv', 'rtl/spk286_integration/spk286_at_machine.sv',
                'rtl/spk286_integration/spk286_integration.qip', *set(copied) - {'rtl/spk286_integration/spk286_at_posted_write_buffer.sv'}}
    assert set(differences) == expected, differences
    assert sha(work/'config.tcl') == frozen['source_sha256']['config.tcl']
    assert all(sha(work/n) == h for n, h in frozen['source_sha256'].items()
               if n.startswith('vendor/spk286/rtl/') or n in (
                   'rtl/spk286_integration/spk286_at_sdram_read_buffer.sv',
                   'rtl/spk286_integration/spk286_at_sdram_data_buffer.sv',
                   'rtl/spk286_integration/spk286_at_mister_memory_port.sv',
                   'rtl/spk286_integration/spk286_at_mister_sdram_owner.sv',
                   'rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv'))
    (out/'promotion-inputs.json').write_text(json.dumps({'changed_sources': differences,
        'new_sources': {'rtl/spk286_integration/spk286_at_posted_write_buffer.sv': sha(work/copied[1])},
        'measured_bridge_and_queue_match': True, 'cpu_cache_port_controller_config_unchanged': True,
        'production_modified': False}, indent=2)+'\n')
    print('POSTED_PRIVATE_MACHINE_CANDIDATE_READY', work)


if __name__ == '__main__':
    main()
