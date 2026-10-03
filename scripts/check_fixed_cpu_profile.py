#!/usr/bin/env python3
"""Compare fixed RTL with the former active profile after real preprocessing.

The reference directory must contain a frozen pre-cleanup source tree. This
checks removal of inactive alternatives, not equivalence of later RTL changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = (
    'SPK286_P01_FAST_MEMORY_START', 'SPK286_P02_FETCH_CHAIN',
    'SPK286_P05_PARALLEL_LIMIT_CHECK', 'SPK286_P06_EARLY_MEMORY_ADDRESS',
    'SPK286_P07_SYNC_MICROCODE', 'SPK286_AT_RAM_READ_BUFFER',
    'SPK286_AT_NO_DEBUG', 'SPK286_AT_CDC',
)
FILES = (
    'vendor/spk286/rtl/spk286.sv',
    'vendor/spk286/rtl/spk286_fetch.sv',
    'rtl/spk286_integration/spk286_at_bus_bridge.sv',
    'PCAT-286.sv',
    'sim/spk286_integration/spk286_at_config_tb.sv',
    'sim/spk286_integration/spk286_at_bus_bridge_tb.sv',
    'sim/spk286_integration/spk286_at_bus_bridge_response_tb.sv',
    'vendor/spk286/sim/unit/spk286_fetch_tb.sv',
    'sys/hps_io.sv',
    'sys/sys_top.v',
)


def normalized_preprocess(root, name, flags):
    result = subprocess.run(
        ['verilator', '-E', '--language', '1800-2012', *flags, name],
        cwd=root, text=True, capture_output=True, check=True,
    )
    text = re.sub(r'^\s*`line\b.*$', '', result.stdout, flags=re.M)
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    # Once the observer is preprocessed out, its OSD enable has no consumer.
    # Permit removal only of that exact unreferenced declaration.
    if name == 'PCAT-286.sv' and 'at_debug_enable' in text:
        if len(re.findall(r'\bat_debug_enable\b', text)) != 1:
            raise SystemExit('Retired observer enable still has a consumer')
        text = re.sub(r'wire\s+at_debug_enable\s*=\s*hps_status\[71\];', '', text)
    return re.sub(r'\s+', '', text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--candidate', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reference, candidate = a.reference.resolve(), a.candidate.resolve()
    rows = {}
    for name in FILES:
        before = normalized_preprocess(reference, name, ['-D' + m for m in ACTIVE])
        after = normalized_preprocess(candidate, name, ['-DSPK286_AT_CDC'])
        if before != after:
            raise SystemExit('Active preprocessed RTL differs: ' + name)
        rows[name] = dict(
            reference_sha256=hashlib.sha256((reference / name).read_bytes()).hexdigest(),
            candidate_sha256=hashlib.sha256((candidate / name).read_bytes()).hexdigest(),
            preprocessed_sha256=hashlib.sha256(after.encode()).hexdigest(),
        )
    config = (candidate / 'config.tcl').read_text()
    if any(m in config for m in (*(m for m in ACTIVE if m != 'SPK286_AT_CDC'), 'SPK286_AT_DEBUG_CPU_DIV2')):
        raise SystemExit('Retired CPU/debug option remains in config.tcl')
    if 'VERILOG_MACRO "SPK286_AT_CDC"' not in (candidate / 'PCAT-286.qsf').read_text():
        raise SystemExit('Required platform CDC selection is missing')
    result = dict(status='FIXED_CPU_ACTIVE_RTL_EQUIVALENCE_PASS',
                  reference=str(reference), candidate=str(candidate), files=rows,
                  retired_active_macros=[m for m in ACTIVE if m != 'SPK286_AT_CDC'],
                  required_platform_macro='SPK286_AT_CDC',
                  note='Exact normalized preprocessor output except the proven unused observer enable; no later timing RTL covered.')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'files=' + str(len(rows)))


if __name__ == '__main__':
    main()
