#!/usr/bin/env python3
"""Measure missing AT HOLD/refresh arbitration in frozen physical-data kernels.

No production change. The SDRAM controller's own refresh remains enabled in
both controls; only the production AT requester/arbitration path is varied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from report_checkit_profile import read_run, WORKLOADS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    experiment, out = args.experiment.resolve(), args.output.resolve()
    assert not out.exists(), 'Preserve earlier evidence'
    out.mkdir(parents=True)
    manifest = json.loads((experiment/'source-manifest.json').read_text())
    rows = []
    for arm in ('baseline', 'candidate'):
        original = experiment/arm
        assert all(sha(original/n) == h for n, h in manifest['variant_sha256'][arm].items())
        work = out/arm
        shutil.copytree(original, work)
        for name in ('spk286_at_arbiter', 'spk286_at_refresh'):
            shutil.copyfile(ROOT/'rtl/spk286_integration'/f'{name}.sv', work/'rtl/spk286_integration'/f'{name}.sv')
        bench = work/'sim/spk286_integration/spk286_checkit_workload_tb.sv'
        text = bench.read_text()
        declarations = '''    integer at_refresh_enabled = 0;
    wire [7:0] retiring_opcode;
    logic final_halt_retired = 0;
    wire hold_request, cpu_hlda, cpu_grant, refresh_grant, bridge_idle, bridge_lock;
    wire refresh_request, refresh_valid, refresh_accept, refresh_ready, refresh_complete;
    wire [23:0] refresh_address;
    wire refresh_error, arbiter_error;
    wire [15:0] at_refresh_count;
    integer held_clocks = 0, hlda_clocks = 0;
    always @(posedge clk) if (!cpu_reset) begin
        if (halted && retired && retiring_opcode == 8'hf4) final_halt_retired <= 1;
        if (hold_request) held_clocks++;
        if (cpu_hlda) hlda_clocks++;
        if (refresh_error || arbiter_error) $fatal(1, "REFRESH_PROBE_PROTOCOL_ERROR");
    end
    spk286_at_refresh at_refresh (
        .clk(clk), .reset(reset), .refresh_enable(at_refresh_enabled != 0),
        .refresh_grant(refresh_grant), .refresh_accept(refresh_valid && refresh_accept),
        .refresh_ready(refresh_valid && refresh_ready), .refresh_request(refresh_request),
        .refresh_bus_valid(refresh_valid), .refresh_address(refresh_address),
        .refresh_complete(refresh_complete), .refresh_count(at_refresh_count), .protocol_error(refresh_error)
    );
    spk286_at_arbiter arbiter (
        .clk(clk), .reset(reset), .cpu_hlda(cpu_hlda), .cpu_bridge_idle(bridge_idle),
        .cpu_lock(bridge_lock), .cpu_odd_word_active(1'b0), .cpu_inta_lock_chain(1'b0),
        .cpu_response_pending(at_valid), .dma_request(1'b0), .refresh_request(refresh_request),
        .loader_request(1'b0), .loader_reset_owner(1'b0),
        .external_done(refresh_grant && refresh_complete), .cpu_hold_request(hold_request),
        .cpu_grant(cpu_grant), .external_grant(), .bus_owner_valid(), .bus_owner(),
        .dma_grant(), .refresh_grant(refresh_grant), .loader_grant(), .protocol_error(arbiter_error)
    );
'''
        text = replace(text, '    spk286_machine_cpu cpu (', declarations+'\n    spk286_machine_cpu cpu (')
        text = replace(text, ".hold_request(1'b0), .address(address)", '.hold_request(hold_request), .hlda(cpu_hlda), .address(address)')
        text = replace(text, '.debug_instruction_retired(retired)',
                       '.debug_opcode(retiring_opcode), .debug_instruction_retired(retired)')
        text = replace(text, '.protocol_error(bridge_error)', '.bridge_idle(bridge_idle), .at_lock(bridge_lock), .protocol_error(bridge_error)')
        text = replace(text, '.cpu_valid(at_valid)', '.cpu_valid(at_valid && cpu_grant)')
        text = replace(text, ".refresh_valid(1'b0)", '.refresh_valid(refresh_valid && refresh_grant)')
        text = replace(text, ".refresh_address(24'd0)", '.refresh_address(refresh_address)')
        text = replace(text, '.refresh_accept(), .refresh_ready()', '.refresh_accept(refresh_accept), .refresh_ready(refresh_ready)')
        text = replace(text, '    integer cycles = 0;', '''    initial begin
        if (!$value$plusargs("AT_REFRESH=%d", at_refresh_enabled)) at_refresh_enabled = 0;
    end
    integer cycles = 0;''')
        # HALT can become visible one edge before its retirement pulse. The
        # old physical-idle-only stop happened to include that pulse in one
        # arm but not the other. Wait for actual F4 retirement in both; do not
        # waive the identical retired-instruction count or architectural work.
        text = replace(text, 'if (halted && posted_idle && physical_idle) begin',
                       'if (halted && final_halt_retired && posted_idle && physical_idle) begin')
        text = replace(text, '                report_stage();\n                if (profile_enable',
            '                $display("AT_REFRESH_COST enabled=%0d interval=32 completions=%0d hold=%0d hlda=%0d",\n'
            '                    at_refresh_enabled, at_refresh_count, held_clocks, hlda_clocks);\n'
            '                report_stage();\n                if (profile_enable')
        bench.write_text(text)
        script = work/'scripts/test_checkit_directed.sh'
        text = script.read_text()
        text = replace(text, '  rtl/spk286_integration/spk286_at_mister_sdram_owner.sv',
            '  rtl/spk286_integration/spk286_at_arbiter.sv\n'
            '  rtl/spk286_integration/spk286_at_refresh.sv\n'
            '  rtl/spk286_integration/spk286_at_mister_sdram_owner.sv')
        # Compile once using the existing directed runner. Its ordinary 8
        # controls remain as evidence; the added paired probes reuse the binary.
        script.write_text(text)
        identities = {str(p.relative_to(work)): sha(p) for p in work.rglob('*') if p.is_file()}
        (work/'inputs.json').write_text(json.dumps(identities, indent=2)+'\n')
        build = out/('compiled-'+arm)
        env = os.environ | {'PCAT_BUILD_DIR': str(build), 'PCAT_CODE_BUFFER_LINES': '512', 'PCAT_PROFILE': '1'}
        with (out/(arm+'-build.log')).open('w') as log:
            subprocess.run(['bash', str(script)], env=env, cwd=work, check=True,
                timeout=600, stdout=log, stderr=subprocess.STDOUT)
        for workload in WORKLOADS:
            pair = {}
            for enabled in (0, 1):
                log_path = out/f'{arm}-{workload}-refresh-{enabled}.log'
                command = [str(build/'obj/checkit_workload'), '+ROM='+str(build/f'checkit-{workload}.rom'),
                    '+NAME='+workload, '+NATIVE=1', '+P03=1', '+PROFILE=1', '+AT_REFRESH='+str(enabled)]
                with log_path.open('w') as log:
                    subprocess.run(command, cwd=work, check=True, timeout=60, stdout=log, stderr=subprocess.STDOUT)
                pair[enabled] = read_run(log_path)
            before, after = pair[0], pair[1]
            for field in ('gpr', 'flags', 'memory'):
                assert before['signature'][field] == after['signature'][field], (arm, workload, field)
            for field in ('retired', 'writes', 'sdram_writes'):
                assert before['result'][field] == after['result'][field], (arm, workload, field)
            for field in ('consumed_bytes', 'redirects'):
                assert before['misc'][field] == after['misc'][field], (arm, workload, field)
            b, a = before['result']['cycles'], after['result']['cycles']
            row = {'arm': arm, 'workload': workload, 'without_at_refresh_clocks': b,
                   'with_at_refresh_clocks': a, 'throughput_loss_fraction': 1-b/a, 'runs': pair}
            rows.append(row)
            print('AT_REFRESH_COST', arm, workload, b, a, 'loss_percent', round(100*(1-b/a), 3), flush=True)
        assert all(sha(work/n) == h for n, h in identities.items())
    (out/'comparison.json').write_text(json.dumps({'runs': rows,
        'architectural_signature_and_physical_store_guards_pass': True,
        'production_modified': False, 'scope': 'Fixed-work physical-data kernels with exact production 32-clock AT refresh/HOLD/arbiter; not DOS rates or hardware acceptance.'}, indent=2)+'\n')
    print('AT_REFRESH_COST_SIGNATURE_SOURCE_GUARDS_PASS')


if __name__ == '__main__':
    main()
