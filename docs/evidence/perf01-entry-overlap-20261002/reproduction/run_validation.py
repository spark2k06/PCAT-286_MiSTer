"""Retain bounded validation of the private entry-overlap prototype."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

run = Path(__file__).resolve().parent
root = run.parents[1]
out = run / 'validation'
out.mkdir(exist_ok=True)
candidate = run / 'candidate'
rtl = candidate / 'rtl/spk286_integration'
flags = ['-DSPK286_P01_FAST_MEMORY_START', '-DSPK286_P06_EARLY_MEMORY_ADDRESS']
records = []


def execute(name, command, cwd=candidate, timeout=180, expected_failure=None):
    log = out / (name + '.log')
    with log.open('w') as stream:
        result = subprocess.run(list(map(str, command)), cwd=cwd, timeout=timeout,
                                stdout=stream, stderr=subprocess.STDOUT)
    records.append({'name': name, 'command': list(map(str, command)),
                    'cwd': str(cwd), 'exit_code': result.returncode,
                    'expected_rejection': expected_failure,
                    'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    if expected_failure:
        assert result.returncode != 0 and expected_failure in log.read_text(), name
    else:
        assert result.returncode == 0, (name, log.read_text()[-2500:])
    print('ENTRY_VALIDATION_PASS', name, flush=True)


for sample in (0, 1):
    execute('bridge-lint-' + str(sample), [
        'verilator', '--lint-only', '--assert', '-Wall', *flags,
        '--top-module', 'spk286_at_bus_bridge',
        "-GCOMPLETE_ON_CPU_SAMPLE=1'b" + str(sample), rtl / 'spk286_at_bus_bridge.sv'])
execute('port-lint', ['verilator', '--lint-only', '--assert', '-Wall',
                     '--top-module', 'spk286_at_mister_memory_port',
                     rtl / 'spk286_at_mister_memory_port.sv'])
port_tb = root / 'sim/spk286_integration/spk286_at_mister_memory_port_tb.sv'
shutil.copyfile(port_tb, out / port_tb.name)
for compiler in ('iverilog', 'verilator'):
    sources = [rtl / 'spk286_at_mister_memory_port.sv', out / port_tb.name]
    if compiler == 'iverilog':
        executable = out / 'port_iv'
        command = ['iverilog', '-g2012', '-s', 'spk286_at_mister_memory_port_tb',
                   '-o', executable, *sources]
        invocation = ['timeout', '30s', 'vvp', executable]
    else:
        obj = out / 'port-obj'
        command = ['verilator', '--binary', '--timing', '--assert', '-j', '2',
                   '-Wno-fatal', '--top-module', 'spk286_at_mister_memory_port_tb',
                   '--Mdir', obj, '-o', 'port_vlt', *sources]
        invocation = ['timeout', '30s', obj / 'port_vlt']
    execute(compiler + '-port-build', command)
    execute(compiler + '-port-run', invocation)
    assert 'AT_MISTER_MEMORY_PORT_PASS' in (out / (compiler + '-port-run.log')).read_text()

# Repeat the complete cancellation scoreboard at production tag geometry.
# This private copy changes capacity only; all functional assertions remain.
cancel_name = 'spk286_at_bridge_cancel_pipeline_tb.sv'
cancel_text = (candidate / 'sim/spk286_integration' / cancel_name).read_text()
old = '    spk286_at_sdram_read_buffer code_buffer ('
assert cancel_text.count(old) == 1
cancel_text = cancel_text.replace(old,
    '    spk286_at_sdram_read_buffer #(.LINE_COUNT(512)) code_buffer (')
old_counter = 'code_fetch != 0 ? code_hits == before_hits + 1 : data_buffer.tag_hit'
assert cancel_text.count(old_counter) == 1
original = out / 'original-counter-tb.sv'
original.write_text(cancel_text)
cancel = out / cancel_name
cancel.write_text(cancel_text.replace(old_counter,
    'code_fetch != 0 ? (code_buffer.request_tag_hit && code_hits == before_hits) : data_buffer.tag_hit'))

for variant in ('baseline', 'candidate'):
    private_rtl = run / variant / 'rtl/spk286_integration'
    sources = [private_rtl / (name + '.sv') for name in (
        'spk286_at_bus_bridge', 'spk286_at_mister_memory_port',
        'spk286_at_sdram_read_buffer', 'spk286_at_sdram_data_buffer')]
    # Prove that the unchanged counter check also fails on the control.
    # Synchronous tags count on hit completion; this test cancels before it.
    benches = [('original-counter-control', original)] if variant == 'baseline' else []
    benches += [('cancel-512-' + variant, cancel)]
    for name, bench in benches:
        obj = out / (name + '-obj')
        execute(name + '-build', [
            'verilator', '--binary', '--timing', '--assert', '-j', '2', '-Wno-fatal',
            *flags, '--top-module', 'spk286_at_bridge_cancel_pipeline_tb',
            '--Mdir', obj, '-o', 'cancel_vlt', *sources, bench])
        failure = 'cancellation case was not a cache hit' if bench == original else None
        execute(name + '-run', ['timeout', '30s', obj / 'cancel_vlt'], expected_failure=failure)
        if not failure:
            assert 'AT_BRIDGE_CANCEL_PIPELINE_PASS' in (out / (name + '-run.log')).read_text()
manifest = json.loads((run / 'source-manifest.json').read_text())
assert all(hashlib.sha256((run / variant / name).read_bytes()).hexdigest() == digest
           for variant, names in manifest['variant_sha256'].items()
           for name, digest in names.items())
(out / 'validation.json').write_text(json.dumps({
    'commands': records, 'frozen_sources_unchanged': True,
    'port_tb_sha256': hashlib.sha256(port_tb.read_bytes()).hexdigest(),
    'production_capacity_cancel_tb_sha256': hashlib.sha256(cancel.read_bytes()).hexdigest(),
    'full_regression': False, 'production_rtl_modified': False,
}, indent=2) + '\n')
