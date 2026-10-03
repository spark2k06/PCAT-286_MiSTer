#!/usr/bin/env python3
"""Compare fixed-profile assignments and active SYSTEM.sdc command traces.

Uses a Tcl interpreter with symbolic collection handles. This establishes
unchanged constraint commands for the selected profile, not fitted timing.
Run with the bundled native Python/Tcl runtime; no Quartus fit is required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tkinter

ROOT = Path(__file__).resolve().parents[1]
RETIRED = {
    'SPK286_P01_FAST_MEMORY_START', 'SPK286_P02_FETCH_CHAIN',
    'SPK286_P05_PARALLEL_LIMIT_CHECK', 'SPK286_P06_EARLY_MEMORY_ADDRESS',
    'SPK286_P07_SYNC_MICROCODE', 'SPK286_AT_RAM_READ_BUFFER',
    'SPK286_AT_NO_DEBUG',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def macros(root):
    config = (root / 'config.tcl').read_text()
    lines = [line.strip() for line in config.splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    pattern = r'set_global_assignment -name VERILOG_MACRO "([^"]+)"'
    assert all(re.fullmatch(pattern, line) for line in lines), 'Unexpected config statement'
    return set(re.findall(r'^' + pattern + r'\s*$',
                          config + '\n' + (root / 'PCAT-286.qsf').read_text(), re.M))


def trace(path, selected):
    t = tkinter.Tcl()
    t.eval('''
set trace {}
set at_cdc_enabled 1
set ::env(P05_REFERENCE_FIT) 0
proc get_clocks {args} {return [list [list clocks [lindex $args end]]]}
proc get_ports {args} {return [list [list ports [lindex $args end]]]}
proc get_pins {args} {return [list [list pins [lindex $args end]]]}
proc get_registers {args} {
    set pattern [lindex $args end]
    if {[string match {*u_at_debug_overlay*} $pattern]} {return {}}
    return [list [list registers $pattern]]
}
proc get_collection_size {collection} {return [llength $collection]}
proc get_all_global_assignments {args} {return $::assignments}
proc foreach_in_collection {var collection body} {
    uplevel 1 [list foreach $var $collection $body]
}
proc post_message {args} {}
foreach cmd {derive_pll_clocks derive_clock_uncertainty create_clock
             create_generated_clock set_input_delay set_output_delay
             set_false_path set_max_delay set_clock_groups} {
    proc $cmd {args} [format {lappend ::trace [linsert $args 0 %s]} $cmd]
}
''')
    assignments = tuple(('unused', 'unused', m) for m in sorted(selected))
    t.call('set', 'assignments', assignments)
    t.call('source', path.as_posix())
    assert t.eval('set AT_CPU') == '{clocks FPGA_CLK2_50}'
    result = t.eval('set trace')
    assert 'AT_DEBUG_CPU_CLK' not in result
    return result, int(t.eval('llength $trace'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--candidate', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reference, candidate = a.reference.resolve(), a.candidate.resolve()
    before, after = macros(reference), macros(candidate)
    assert RETIRED.issubset(before)
    assert 'SPK286_AT_DEBUG_CPU_DIV2' not in before
    assert not RETIRED.intersection(after)
    assert 'SPK286_AT_DEBUG_CPU_DIV2' not in after
    assert before - RETIRED == after, 'Other effective project macros changed'
    assert 'SPK286_AT_CDC' in after
    old_qsf = (reference / 'PCAT-286.qsf').read_text()
    new_qsf = (candidate / 'PCAT-286.qsf').read_text()
    insertion = ('# Required platform clock-crossing implementation; independent of CPU options.\n'
                 'set_global_assignment -name VERILOG_MACRO "SPK286_AT_CDC"\n')
    assert new_qsf == old_qsf.replace('set_global_assignment -name TOP_LEVEL_ENTITY sys_top\n',
                                     'set_global_assignment -name TOP_LEVEL_ENTITY sys_top\n' + insertion, 1)
    rows = {}
    for path in reference.rglob('*.sdc'):
        name = path.relative_to(reference).as_posix()
        if any(part in {'build', 'db', 'incremental_db', 'obj_dir'} for part in path.relative_to(reference).parts):
            continue
        if name != 'SYSTEM.sdc':
            assert path.read_bytes() == (candidate / name).read_bytes(), name
            rows[name] = sha(path)
    traces = {}
    for splash in (False, True):
        optional = {'SPK286_AT_BOOT_SPLASH'} if splash else set()
        old_trace, count = trace(reference / 'SYSTEM.sdc', before | optional)
        new_trace, new_count = trace(candidate / 'SYSTEM.sdc', after | optional)
        assert old_trace == new_trace and count == new_count, 'Constraint commands changed'
        traces[str(splash)] = dict(command_count=count,
                                  command_trace_sha256=hashlib.sha256(new_trace.encode()).hexdigest())
    result = dict(status='FIXED_CPU_ASSIGNMENT_CONSTRAINT_EQUIVALENCE_PASS',
                  reference=str(reference), candidate=str(candidate),
                  reference_macros=sorted(before), candidate_macros=sorted(after),
                  unchanged_sdc_sha256=rows, traces=traces,
                  inputs_sha256={name: dict(reference=sha(reference / name), candidate=sha(candidate / name))
                                 for name in ('config.tcl', 'PCAT-286.qsf', 'SYSTEM.sdc')},
                  scope='Exact QSF delta, effective config/QSF macros and active Tcl constraint commands with symbolic collections; not fitted timing or path coverage.')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'commands=' + str(traces['False']['command_count']))


if __name__ == '__main__':
    main()
