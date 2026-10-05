#!/usr/bin/env python3
"""Run bounded directed checks of idle payload factoring on frozen sources."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = 'rtl/spk286_integration/'
SIM = 'sim/spk286_integration/'
SOURCES = [RTL + name + '.sv' for name in (
    'spk286_at_sdram_read_buffer', 'spk286_at_sdram_data_buffer',
    'spk286_at_posted_write_buffer', 'spk286_at_mister_memory_port')]
SOURCES += [SIM + name + '_tb.sv' for name in (
    'spk286_at_sdram_read_buffer', 'spk286_at_multiline_code_buffer',
    'spk286_at_sdram_data_buffer', 'spk286_at_posted_write_buffer')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path,
                        help='Frozen pre-change source root for exact isolated lint comparison')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / 'source'
    frozen = {ROOT / p: (ROOT / p).read_bytes() for p in SOURCES}
    tool = Path(__file__).resolve()
    frozen[tool] = tool.read_bytes()
    for path, data in frozen.items():
        dest = snapshot / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    references = {}
    for module in ('spk286_at_sdram_read_buffer', 'spk286_at_sdram_data_buffer', 'spk286_at_posted_write_buffer'):
        path = args.reference.resolve() / RTL / (module + '.sv')
        references[path] = path.read_bytes()
        dest = snapshot / '_reference' / (module + '.sv')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(references[path])
    receipt = {'status': 'RUNNING', 'sources_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(data).hexdigest()
                                                     for p, data in frozen.items()}, 'runs': [],
               'scope': 'Strict isolated lint, existing code/data directed benches and new posted contract bank; no full regression, CPU or Quartus build.',
               'exceptions': ['Only lint category waiver is pre-existing SYNCASYNCNET: unreset RAM/control-reset split. Other diagnostics must exactly equal the frozen baseline, with zero new warnings.',
                              'Full composed data pipeline uses Verilator; its pre-existing Icarus delta-loop limitation is not retested.'],
               'reference_sha256': {str(p): hashlib.sha256(data).hexdigest() for p, data in references.items()},
               'lint_warning_matches': [], 'compile_reuse': 'None; fresh source snapshot and simulator outputs.'}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    own_temp = output / 'tmp'
    own_temp.mkdir()
    env.update(TMPDIR=str(own_temp), TEMP=str(own_temp), TMP=str(own_temp))

    def run(name, command, marker=None):
        started = time.time()
        log = output / (name + '.log')
        with log.open('w') as stream:
            result = subprocess.run(list(map(str, command)), cwd=snapshot, env=env,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        text = log.read_text()
        receipt['runs'].append({'name': name, 'command': list(map(str, command)),
                                'exit_code': result.returncode, 'elapsed_seconds': round(time.time() - started, 3),
                                'log_sha256': sha(log), 'marker': marker})
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        assert result.returncode == 0 and (marker is None or marker in text), name
        print('BUFFER_DIRECTED_PASS ' + name, flush=True)

    for module, parameters in (('spk286_at_sdram_read_buffer', []),
                               ('spk286_at_sdram_read_buffer', ['-GLINE_COUNT=512']),
                               ('spk286_at_sdram_data_buffer', []),
                               ('spk286_at_posted_write_buffer', [])):
        suffix = '-production' if parameters else ''
        warning_sets = []
        for label, source in (('reference', '_reference/' + module + '.sv'),
                              ('candidate', RTL + module + '.sv')):
            name = 'lint-' + module + suffix + '-' + label
            run(name, ['verilator', '--lint-only', '--Wall', '-Wno-fatal', '-Wno-SYNCASYNCNET',
                       '--top-module', module, *parameters, source])
            log = (output / (name + '.log')).read_text()
            warning_sets.append(sorted(re.findall(r'%Warning-([A-Z0-9_]+): [^\n]+?:\d+:\d+: ([^\n]+)', log)))
        assert warning_sets[0] == warning_sets[1], 'New isolated lint diagnostic: ' + module + suffix
        receipt['lint_warning_matches'].append({'module': module, 'parameters': parameters,
                                                'reference': warning_sets[0], 'candidate': warning_sets[1]})
    cases = [
        ('code-basic', 'spk286_at_sdram_read_buffer_tb',
         [RTL + 'spk286_at_sdram_read_buffer.sv', SIM + 'spk286_at_sdram_read_buffer_tb.sv'], {}, [], 'P03_BUFFER_PASS'),
        ('code-production', 'spk286_at_multiline_code_buffer_tb',
         [RTL + 'spk286_at_sdram_read_buffer.sv', SIM + 'spk286_at_multiline_code_buffer_tb.sv'],
         {'LINE_COUNT': 512}, ['PCAT_PRODUCTION_CODE_BUFFER'], 'MULTILINE_COHERENCE_PASS'),
        ('data', 'spk286_at_sdram_data_buffer_tb',
         [RTL + 'spk286_at_sdram_data_buffer.sv', RTL + 'spk286_at_mister_memory_port.sv',
          RTL + 'spk286_at_sdram_read_buffer.sv', SIM + 'spk286_at_sdram_data_buffer_tb.sv'], {}, [], 'RAM_BUFFER_UNIT_PASS'),
        ('data-pipeline', 'spk286_at_sdram_data_buffer_tb',
         [RTL + 'spk286_at_sdram_data_buffer.sv', RTL + 'spk286_at_mister_memory_port.sv',
          RTL + 'spk286_at_sdram_read_buffer.sv', SIM + 'spk286_at_sdram_data_buffer_tb.sv'],
         {'FULL_PIPELINE': 1, 'CODE_BUFFER_LINES': 512}, [], 'RAM_BUFFER_PIPELINE_PASS'),
        ('posted', 'spk286_at_posted_write_buffer_tb',
         [RTL + 'spk286_at_posted_write_buffer.sv', SIM + 'spk286_at_posted_write_buffer_tb.sv'], {}, [], 'POSTED_WRITE_BUFFER_PASS'),
    ]
    for name, top, files, parameters, defines, marker in cases:
        for simulator in ('iverilog', 'verilator'):
            if name == 'data-pipeline' and simulator == 'iverilog':
                continue
            prefix = name + '-' + simulator
            if simulator == 'iverilog':
                binary = output / (prefix + '.vvp')
                command = ['iverilog', '-g2012', '-s', top, '-o', binary]
                command += ['-P' + top + '.' + p + '=' + str(v) for p, v in parameters.items()]
                command += ['-D' + d for d in defines] + files
                run(prefix + '-build', command)
                run(prefix + '-run', ['vvp', binary], marker)
            else:
                mdir = output / (prefix + '-obj')
                command = ['verilator', '--binary', '--timing', '--assert', '-j', '2', '-Wno-fatal',
                           '--top-module', top, '--Mdir', mdir, '-o', 'run']
                command += ['-G' + p + '=' + str(v) for p, v in parameters.items()]
                command += ['-D' + d for d in defines] + files
                run(prefix + '-build', command)
                for pch in mdir.glob('*.gch'):
                    assert not pch.is_symlink() and pch.resolve().parent == mdir.resolve()
                    pch.unlink()
                run(prefix + '-run', [mdir / 'run'], marker)
    for path, data in frozen.items():
        assert path.read_bytes() == data, 'Input changed: ' + str(path)
    for path, data in references.items():
        assert path.read_bytes() == data, 'Reference changed: ' + str(path)
    receipt['status'] = 'AT_BUFFER_IDLE_PAYLOAD_DIRECTED_PASS'
    receipt['source_guard'] = 'Every source and runner byte identical before/after directed checks.'
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
