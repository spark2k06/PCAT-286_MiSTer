"""Freeze an isolated bridge/port entry-overlap prototype for PERF01 review."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def change(path, replacements):
    text = path.read_text()
    for old, new in replacements:
        assert text.count(old) == 1, (path, old)
        text = text.replace(old, new, 1)
    path.write_text(text)


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline-source', type=Path, default=ROOT,
                        help='P16 source tree (before P17 adoption), or retained frozen baseline')
    args = parser.parse_args()
    ROOT = args.baseline_source.resolve()
    out = args.output.resolve()
    assert not out.exists(), 'Preserve previous experiment directories'
    qip = 'rtl/spk286_integration/spk286_integration.qip'
    names = ['PCAT-286.sv', 'config.tcl', qip]
    names += re.findall(r'SYSTEMVERILOG_FILE "(vendor/[^\"]+\.sv)"',
                        (ROOT / qip).read_text())
    names += [str(p.relative_to(ROOT)).replace('\\', '/')
              for p in (ROOT / 'tests/firmware').glob('checkit_*.asm')]
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
        'sim/spk286_integration/spk286_at_bridge_cancel_pipeline_tb.sv',
        'scripts/test_checkit_directed.sh', 'scripts/at_performance_flags.sh',
        'scripts/test_at_bridge_cancel_pipeline.sh',
        'tools/perf01/build_86box_memory_probe.py',
        'tools/perf01/spk286_memory_probe.hpp',
        'tools/perf01/memory_probe_smoke.cpp',
    ]
    before = {name: sha(ROOT / name) for name in names}
    for variant in ('baseline', 'candidate'):
        for name in names:
            target = out / variant / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
    bridge = 'rtl/spk286_integration/spk286_at_bus_bridge.sv'
    port = 'rtl/spk286_integration/spk286_at_mister_memory_port.sv'
    change(out / 'candidate' / bridge, [
        ('    wire [1:0] early_byte_enable',
         '    // Private prototype: accept from the initial address edge.\n'
         '    // The backend and bridge both retain the same request on that edge.\n'
         '    wire early_memory_command = early_memory_address && !COMPLETE_ON_CPU_SAMPLE;\n'
         '    wire [1:0] early_byte_enable'),
        ('assign at_command_valid  = (state_q == STATE_COMMAND);',
         'assign at_command_valid  = early_memory_command || (state_q == STATE_COMMAND);'),
        ("assign at_data_oe        = at_valid && request_write_q &&\n                               ((state_q == STATE_COMMAND) ||\n                                (state_q == STATE_WAIT));",
         "assign at_data_oe        = early_memory_command ? cpu_data_oe :\n                               at_valid && request_write_q &&\n                               ((state_q == STATE_COMMAND) ||\n                                (state_q == STATE_WAIT));"),
        ('assign at_accepted       = (state_q == STATE_COMMAND) && at_accept;',
         'assign at_accepted       = at_command_valid && at_accept;'),
        ('state_q <= early_memory_address ? STATE_COMMAND :',
         'state_q <= early_memory_command && at_accept ? STATE_WAIT :\n                                       early_memory_address ? STATE_COMMAND :'),
    ])
    change(out / 'candidate' / port, [
        ('    assign selected_accept =',
         '    wire cpu_entry_command = !active_q && !loader_valid &&\n'
         '                             cpu_candidate && cpu_command_valid && !reset;\n\n'
         '    assign selected_accept ='),
        ('        end else begin\n        end\n    end',
         '''        end else if (cpu_entry_command) begin
            // Private prototype: arbitration, address capture and backend
            // command acceptance share one edge. Completion is still qualified
            // by the retained active/accepted record on a later edge.
            backend_valid         = 1'b1;
            backend_command_valid = 1'b1;
            backend_owner         = OWNER_CPU;
            backend_write         = cpu_write;
            backend_refresh       = 1'b0;
            backend_code_fetch    = cpu_code_fetch;
            backend_cycle_class   = cpu_cycle_class;
            backend_address       = cpu_address;
            backend_byte_enable   = cpu_byte_enable;
            backend_data_out      = cpu_data_out;
            cpu_accept            = backend_accept;
        end
    end'''),
        ("                end else if (cpu_candidate) begin\n                    active_q      <= 1'b1;",
         "                end else if (cpu_candidate) begin\n                    accepted_q    <= cpu_entry_command && backend_accept;\n                    active_q      <= 1'b1;"),
    ])
    # This is an explicit timing comparison, not an architectural expectation
    # change: the production control continues to require two wait clocks.
    smoke = out / 'candidate/tools/perf01/memory_probe_smoke.cpp'
    change(smoke, [('require(hit==2 && miss>hit', 'require(hit==1 && miss>hit'),
                   ('require(read_hit==2 && read_miss>read_hit',
                    'require(read_hit==1 && read_miss>read_hit')])
    versions = {v: {n: sha(out / v / n) for n in names}
                for v in ('baseline', 'candidate')}
    changed = [n for n in names if versions['baseline'][n] != versions['candidate'][n]]
    assert set(changed) == {bridge, port, 'tools/perf01/memory_probe_smoke.cpp'}
    assert all(sha(ROOT / n) == h for n, h in before.items())
    retained_manifest = ROOT.parent / 'source-manifest.json'
    if retained_manifest.exists():
        original = json.loads(retained_manifest.read_text())
        assert all(before[n] == original['variant_sha256']['baseline'][n] for n in names)
        source_commit = original['created_from_commit']
    else:
        assert (ROOT / '.git').exists(), 'Use a P16 checkout or verified retained baseline'
        source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                                cwd=ROOT, text=True).strip()
    (out / 'source-manifest.json').write_text(json.dumps({
        'created_from_commit': source_commit,
        'baseline_source': str(ROOT),
        'source_names': names, 'original_sha256': before,
        'variant_sha256': versions, 'changed_between_variants': changed,
        'production_rtl_modified': False,
        'scope': 'Entry overlap only; unchanged CPU, cache geometry and physical SDRAM timing.',
    }, indent=2) + '\n')
    patch = ''
    for name in changed:
        patch += ''.join(difflib.unified_diff(
            (out / 'baseline' / name).read_text().splitlines(True),
            (out / 'candidate' / name).read_text().splitlines(True),
            fromfile='baseline/' + name, tofile='candidate/' + name))
    (out / 'candidate.patch').write_text(patch)
    print('EARLY_COMMAND_PRIVATE_SOURCES_READY', out, flush=True)


if __name__ == '__main__':
    main()
