#!/usr/bin/env python3
"""Audit the fixed-profile fit, raw STA, source identities and compiled ROM.

Physical timing acceptance remains conditional on the inherited platform I/O
coverage and SDRAM board/device budget. This does not certify guest software.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from summarize_at_50mhz_timing import parse_report, table_rows, parse_fmax
from check_sync_microcode_image import analyze_compiled_image

ROOT = Path(__file__).resolve().parents[1]
CORNERS = ('7_slow_1100mv_100c', '7_slow_1100mv_-40c',
           'MIN_fast_1100mv_100c', 'MIN_fast_1100mv_-40c')
GROUPS = ('global', 'clk50_internal', 'clk50_incoming', 'cpu', 'cpu_bridge',
          'bridge_cpu', 'memory_port', 'code_buffer', 'data_buffer',
          'data_buffer_outputs', 'sdram_owner', 'sdram_owner_internal',
          'keyboard', 'prebios_stage2', 'video', 'sdram_input', 'sdram_output')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resources(out):
    summary = (out / 'PCAT-286.fit.summary').read_text(encoding='latin-1')
    assert 'Fitter Status : Successful' in summary
    labels = dict(equivalent_alms='Logic utilization (in ALMs)',
                  registers='Total registers', memory_bits='Total block memory bits',
                  m10k='Total RAM Blocks', dsp='Total DSP Blocks', plls='Total PLLs')
    result = {}
    for name, label in labels.items():
        result[name] = int(re.search(r'^' + re.escape(label) + r'\s*:\s*([\d,]+)',
                                    summary, re.M)[1].replace(',', ''))
    fit = (out / 'PCAT-286.fit.rpt').read_text(encoding='latin-1')
    result['placed_alms'] = int(re.search(
        r'ALMs used in final placement \[=a\+b\+c\+d\]\s*;\s*([\d,]+)', fit)[1].replace(',', ''))
    result['placed_alms_percent'] = 100 * result['placed_alms'] / 41910
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--functional-sources', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run, baseline = a.run.resolve(), a.baseline.resolve()
    work, reports, out = run / 'work', run / 'timing', run / 'work/output_files'
    m = json.loads((run / 'manifest.json').read_text())
    bm = json.loads((baseline / 'manifest.json').read_text())
    sources = {n.replace('\\', '/'): h for n, h in m['source_sha256'].items()}
    base_sources = {n.replace('\\', '/'): h for n, h in bm['source_sha256'].items()}
    generated = {}
    started = datetime.fromisoformat((run / 'compile-started.txt').read_text().strip())
    compile_log = (run / 'compile.log').read_text(errors='replace')
    assert re.search(r'Full Compilation was successful\. 0 errors', compile_log)
    for n, h in sources.items():
        f = work / n
        if sha(f) != h:
            assert n == 'build_id.v', 'Frozen source changed: ' + n
            expected = '`define BUILD_DATE "' + started.strftime('%y%m%d') + '"'
            assert f.read_text() == expected and 'Generated: /build/build_id.v: ' + expected in compile_log
            assert sha(work / 'sys/build_id.tcl') == base_sources['sys/build_id.tcl']
            generated[n] = dict(before=h, compiled=sha(f), value=expected)
    # No constraint relaxation: the baseline is already the fixed 50 MHz
    # profile, with only the retired diagnostic selection removed.
    for n, h in sources.items():
        if n.endswith('.sdc') or n == 'config.tcl':
            assert base_sources[n] == h, 'SDC/config changed: ' + n
    config = (work / 'config.tcl').read_text()
    assert not re.search(r'SPK286_(?:P\d\d_|AT_(?:NO_DEBUG|DEBUG_CPU_DIV2|CDC|RAM_READ_BUFFER))', config)
    assert 'VERILOG_MACRO "SPK286_AT_CDC"' in (work / 'PCAT-286.qsf').read_text()
    inventory = (reports / 'collections.txt').read_text()
    assert 'clock=FPGA_CLK2_50 period=20.000' in inventory
    assert 'clock=SDRAM_CLK period=20.000' in inventory
    assert 'fixed_cpu_profile=1 observers=0' in inventory
    assert 'AT_DEBUG_CPU_CLK' not in inventory
    # Bind directed functional evidence to every actually compiled source
    # listed by the verification receipt, rather than only a module name.
    binding = json.loads(a.functional_sources.read_text())
    assert binding['status'] == 'FIXED50_DIRECTED_VALIDATION_PASS'
    for n, h in binding['source_sha256'].items():
        assert sha(work / n) == h, 'Fit differs from validation: ' + n
    expected = {(c, g, k) for c in CORNERS for g in GROUPS for k in ('setup', 'hold')}
    expected |= {(c, 'global', k) for c in CORNERS for k in ('recovery', 'removal')}
    rows = [line.split() for line in (reports / 'path_counts.txt').read_text().splitlines()]
    assert len(rows) == len(expected) and {tuple(r[:3]) for r in rows} == expected
    failures, margins, coverage = [], {}, {}
    for c, g, k, count, slack in rows:
        f = reports / c / (g + '_' + k + '.rpt')
        parsed = parse_report(f)
        assert parsed['reported_paths'] == int(count)
        if int(count):
            assert abs(parsed['top_paths'][0]['slack_ns'] - float(slack)) < 0.00001
        if g == 'global':
            command = f.read_text().split('Tcl Command:', 1)[1].split('Options:', 1)[0]
            assert not re.search(r'-(from|to)(?:_clock)?\s', command)
            assert int(count) > 0
            margins.setdefault(c, {})[k] = float(slack)
            if float(slack) <= 0:
                failures.append(f'{c} global {k}: {slack}')
    allowed = dict(no_clock=3713, multiple_clock=32, no_input_delay=20,
                   no_output_delay=85, partial_min_max_delay=24)
    families = dict(**{'sysmem_lite:sysmem': 1239, 'h2f_gp': 617,
                       'uart': 619, 'spi': 621, 'hdmi_i2c': 617})
    for c in CORNERS:
        check = (reports / c / 'check_timing.rpt').read_text()
        checks = {r[0]: int(r[1]) for r in table_rows(check.split('; No Clock', 1)[0])
                  if len(r) == 2 and r[1].isdigit()}
        mandatory = set(allowed) | {'loops', 'latches', 'generated_clock', 'virtual_clock',
                                   'partial_multicycle', 'multicycle_consistency',
                                   'pll_cross_check', 'uncertainty'}
        assert mandatory.issubset(checks)
        for name, count in checks.items():
            assert count == allowed.get(name, 0), (c, name, count)
        found = {}
        for row in table_rows(check):
            if len(row) == 2 and row[1] == "No clock feeds this register's clock port.":
                family = re.split(r'[|~]', row[0], maxsplit=1)[0]
                found[family] = found.get(family, 0) + 1
        assert found == families
        ucp = (reports / c / 'unconstrained.rpt').read_text()
        counts = {r[0]: [int(x) for x in r[1:]] for r in table_rows(ucp.split('; Clock Status Summary', 1)[0])
                  if len(r) == 3 and r[1].isdigit() and r[2].isdigit()}
        assert counts.get('Illegal Clocks') == [0, 0] and counts.get('Unconstrained Clocks') == [0, 0]
        coverage[c] = dict(checks=checks, unclocked_families=found, unconstrained=counts,
                           fmax_mhz=parse_fmax((reports / c / 'fmax.rpt').read_text()))
    # Check the STA summary as well, including minimum pulse width.
    sta = (out / 'PCAT-286.sta.summary').read_text(encoding='latin-1')
    summary_rows = [(m[1], float(m[2])) for m in re.finditer(
        r'Type\s*:\s*(.+?)\nSlack\s*:\s*(-?[\d.]+)\nTNS\s*:\s*(-?[\d.]+)', sta)]
    assert len(summary_rows) > 50
    failures.extend(f'STA summary {name}: {slack}' for name, slack in summary_rows if slack <= 0)
    rbf, sof = out / 'PCAT-286.rbf', out / 'PCAT-286.sof'
    for f in (rbf, sof):
        assert f.is_file() and f.stat().st_mtime > (run / 'compile-started.txt').stat().st_mtime
    result = dict(status='MEASURED_FIXED50_TIMING_FAIL' if failures else 'MEASURED_FIXED50_TIMING_PASS_UNDER_DECLARED_SCOPE',
                  failures=failures, margins_ns=margins, coverage=coverage,
                  resources=resources(out), generated_sources=generated,
                  functional_binding_sha256=sha(a.functional_sources),
                  source_count=len(sources), manifest_sha256=sha(run / 'manifest.json'),
                  rbf=dict(path=str(rbf), bytes=rbf.stat().st_size, sha256=sha(rbf)),
                  sof_sha256=sha(sof), compiled_rom=analyze_compiled_image(run),
                  raw_reports_sha256={f.relative_to(reports).as_posix(): sha(f) for f in reports.rglob('*') if f.is_file()},
                  scope='Inherited platform I/O coverage and conditional SDRAM device/flight budget; no hardware or full regression claim.')
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])
    print(json.dumps(dict(margins_ns=margins, resources=result['resources'], failures=failures), indent=2))


if __name__ == '__main__':
    main()
