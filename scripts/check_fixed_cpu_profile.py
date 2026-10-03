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
    # Once the observer is preprocessed out, its OSD enable has no consumer.
    # Permit removal only of that exact unreferenced declaration.
    if name == 'PCAT-286.sv' and 'at_debug_enable' in text:
        if len(re.findall(r'\bat_debug_enable\b', text)) != 1:
            raise SystemExit('Retired observer enable still has a consumer')
        text = re.sub(r'wire\s+at_debug_enable\s*=\s*hps_status\[71\];', '', text)
    # Preserve complete string literals, including spaces and comment-like
    # text in OSD strings. Remove comments/whitespace only outside strings.
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|\s+|[^\s]', text)
    return tuple(t for t in tokens if not t.isspace() and
                 not t.startswith(('/*', '//')))


def unchanged_sources(reference, candidate):
    suffixes = {'.sv', '.v', '.vh', '.vhd', '.qip', '.mif', '.mem', '.hex', '.mc'}
    excluded = {'build', 'db', 'incremental_db', 'obj_dir', '__pycache__'}
    def inventory(root):
        return {p.relative_to(root).as_posix() for directory in ('rtl', 'sys', 'vendor')
                for p in (root / directory).rglob('*')
                if p.is_file() and p.suffix.lower() in suffixes and
                not excluded.intersection(p.relative_to(root).parts)} | {
                    p.name for p in root.iterdir()
                    if p.is_file() and p.suffix.lower() in suffixes}
    before, after = inventory(reference), inventory(candidate)
    if before != after:
        raise SystemExit('RTL/source inventory differs: ' + str(sorted(before ^ after)))
    rows = {}
    for name in sorted(before - set(FILES)):
        old = (reference / name).read_bytes()
        new = (candidate / name).read_bytes()
        if old != new:
            raise SystemExit('Source outside cleanup changed: ' + name)
        rows[name] = hashlib.sha256(new).hexdigest()
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('--candidate', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reference, candidate = a.reference.resolve(), a.candidate.resolve()
    untouched = unchanged_sources(reference, candidate)
    # Byte identity alone does not establish identity if a preserved source
    # responds to a removed macro. Check every such conditional dependency.
    dependencies = set(FILES)
    for name in untouched:
        if Path(name).suffix in {'.sv', '.v', '.vh'}:
            source = (reference / name).read_text()
            if any(re.search(r'`(?:ifdef|ifndef|elsif)\s+' + re.escape(m) + r'\b', source)
                   for m in ACTIVE):
                dependencies.add(name)
    rows = {}
    for name in sorted(dependencies):
        views = {}
        for synthesis in (False, True):
            extra = ['-DSYNTHESIS'] if synthesis else []
            before = normalized_preprocess(reference, name, ['-D' + m for m in ACTIVE] + extra)
            after = normalized_preprocess(candidate, name, ['-DSPK286_AT_CDC'] + extra)
            if before != after:
                raise SystemExit('Active preprocessed RTL differs: ' + name + ' SYNTHESIS=' + str(synthesis))
            views['synthesis' if synthesis else 'simulation'] = hashlib.sha256(json.dumps(after).encode()).hexdigest()
        rows[name] = dict(
            reference_sha256=hashlib.sha256((reference / name).read_bytes()).hexdigest(),
            candidate_sha256=hashlib.sha256((candidate / name).read_bytes()).hexdigest(),
            preprocessed_sha256=views,
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
                  unchanged_source_sha256=untouched,
                  note='Identical preprocessor tokens, preserving string literals, except the proven unused observer enable; all other RTL/ROM/QIP sources byte-identical. No later timing RTL covered.')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'files=' + str(len(rows)), 'unchanged=' + str(len(untouched)), 'views=simulation,synthesis')


if __name__ == '__main__':
    main()
