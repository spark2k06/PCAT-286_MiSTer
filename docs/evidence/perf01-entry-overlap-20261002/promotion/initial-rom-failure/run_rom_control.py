from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import subprocess

run = Path(__file__).resolve().parent
root = run.parents[1]
bench = (root/'sim/spk286_integration/spk286_at_machine_tb.sv').read_text()
trace = '''
    always @(posedge clk) begin
        if ($test$plusargs("ENTRY_TRACE") && !reset && cpu_ready && cpu_bus_valid && $time < 15000)
            $display("ENTRY_BUS cs_ip=%04h:%04h op=%02h class=%h raw=%06h mapped=%07h W=%b out=%04h in=%04h sink=%b",
                     debug_cs, debug_ip, debug_opcode, cpu_bus_status, cpu_address,
                     memory_address, cpu_bus_write, cpu_data_out, cpu_data_in, dut.rom_write_sink_ready);
    end
'''
bench = bench.rsplit('endmodule',1)[0] + trace + 'endmodule\n'
(run/'rom-diagnostic/trace_tb.sv').write_text(bench)
script = (root/'scripts/test_at_machine_boundary.sh').read_text()
script = script.replace('root=$(cd "$(dirname "$0")/.." && pwd)', 'root=' + str(root))
script = script.replace('sim/spk286_integration/spk286_at_machine_tb.sv', str(run/'rom-diagnostic/trace_tb.sv'))
script = script.replace('"+MAX_CYCLES=${AT_SYSTEM_MAX_CYCLES:-2000000}"',
                        '"+ENTRY_TRACE" "+MAX_CYCLES=10000"')
def execute(variant):
    text = script
    if variant == 'baseline':
        for name in ('spk286_at_bus_bridge.sv', 'spk286_at_mister_memory_port.sv'):
            text = text.replace('  rtl/spk286_integration/' + name,
                                '  ' + str(run/'baseline/rtl/spk286_integration'/name))
    wrapper = run/'rom-diagnostic'/('run-' + variant + '.sh')
    wrapper.write_text(text)
    with (run/'rom-diagnostic'/(variant + '-trace.log')).open('w') as stream:
        result = subprocess.run(['bash',str(wrapper)], cwd=root,
            env=dict(os.environ, PCAT_BUILD_DIR=str(run/'rom-diagnostic'/variant),
                     AT_SYSTEM_ROM=str(run/'promotion-entry/test_at_memory_entry/entry.rom')),
            stdout=stream,stderr=subprocess.STDOUT,timeout=240)
    print('ROM_TRACE_COMPLETE',variant,result.returncode,flush=True)
    return dict(variant=variant, exit_code=result.returncode)
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(execute, ('baseline','candidate')))
(run/'rom-diagnostic/control.json').write_text(json.dumps(results,indent=2)+'\n')
