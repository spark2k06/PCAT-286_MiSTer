"""Compare fixed-work entry overlap and measure a simulation-only write ceiling."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from report_checkit_profile import read_run, WORKLOADS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equivalent(first, second, physical_writes=True):
    for field in ('gpr', 'flags', 'memory'):
        assert first['signature'][field] == second['signature'][field], field
    for field in ('retired', 'writes'):
        assert first['result'][field] == second['result'][field], field
    if physical_writes:
        assert first['result']['sdram_writes'] == second['result']['sdram_writes']
    assert first['misc']['consumed_bytes'] == second['misc']['consumed_bytes']
    assert first['misc']['redirects'] == second['misc']['redirects']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = json.loads((run / 'source-manifest.json').read_text())
    rows = []
    for variant in ('baseline', 'candidate'):
        root = run / variant
        for name, digest in manifest['variant_sha256'][variant].items():
            assert sha(root / name) == digest, (variant, name)
    for workload in WORKLOADS:
        arms = {}
        for variant in ('baseline', 'candidate'):
            directed = run / ('directed-' + variant)
            arms[variant] = read_run(directed / (workload + '-p03-1.log'))
            # Existing counterfactual bypasses only physical writes. Cache,
            # CPU and read path remain unchanged. No hardware implementation
            # or safe write posting is demonstrated by this experiment.
            target = directed / 'ideal-writes'
            target.mkdir(exist_ok=True)
            log = target / (workload + '.log')
            assert not log.exists(), 'Preserve prior ceiling measurements'
            command = [str(directed / 'obj/checkit_workload'),
                       '+ROM=' + str(directed / ('checkit-' + workload + '.rom')),
                       '+NAME=' + workload, '+NATIVE=1', '+P03=1',
                       '+PROFILE=1', '+IDEAL_OWNER=5']
            with log.open('w') as stream:
                subprocess.run(command, cwd=run / variant, check=True, timeout=120,
                               stdout=stream, stderr=subprocess.STDOUT)
            arms[variant + '_ideal_writes'] = read_run(log)
            equivalent(arms[variant], arms[variant + '_ideal_writes'], False)
            arms[variant + '_ideal_writes']['command'] = command
        equivalent(arms['baseline'], arms['candidate'])
        before = arms['baseline']['result']['cycles']
        after = arms['candidate']['result']['cycles']
        gain = before / after - 1
        ideal = arms['candidate_ideal_writes']['result']['cycles']
        rows.append({'workload': workload, 'arms': arms,
                     'entry_gain_fraction': gain,
                     'entry_fewer_clocks_fraction': 1 - after / before,
                     'ideal_writes_extra_gain_fraction': after / ideal - 1,
                     'entry_plus_ideal_writes_gain_fraction': before / ideal - 1})
        print('ENTRY_OVERLAP_DIRECTED', workload, 'cycles', before, after,
              'gain_percent', round(100 * gain, 4),
              'ideal_writes_extra_percent', round(100 * (after / ideal - 1), 4), flush=True)
    assert all(sha(ROOT / name) == digest
               for name, digest in manifest['original_sha256'].items())
    report = {'source_manifest_sha256': sha(run / 'source-manifest.json'),
              'clock_mhz': 50, 'code_bytes': 4096, 'data_bytes': 1024,
              'data_ways': 2, 'production_rtl_modified': False, 'runs': rows,
              'limitations': [
                  'Fixed-work kernels; no DOS CHECKNUM score or hardware result.',
                  'The whetstone kernel uses fixed-point operations, not CheckIT software floating point.',
                  'Ideal writes bypass physical service and do not establish correct write posting.',
                  'No DMA, HPS or interrupts in these kernels; independent ordering tests are required.',
                  'No synthesis, resource estimate or timing closure is implied.',
                  'Bus wait overlaps execution; compare elapsed clocks, not sums of latency savings.',
                  'The legacy kernel code-hit/miss latency labels assume asynchronous tags; use aggregate code transfers and native buffer counters with synchronous tags.',
              ]}
    (run / 'directed-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ENTRY_OVERLAP_REVIEW_PASS source_guards signatures accounting', flush=True)


if __name__ == '__main__':
    main()
