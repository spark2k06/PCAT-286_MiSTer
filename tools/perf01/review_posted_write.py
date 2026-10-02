"""Compare the physical-data P17/one-entry-posting controls, without ideal writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from report_checkit_profile import read_run, WORKLOADS
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('experiment', type=Path)
    args = p.parse_args()
    run = args.experiment.resolve()
    manifest = json.loads((run/'source-manifest.json').read_text())
    assert all(sha(ROOT/n) == h for n, h in manifest['original_sha256'].items())
    for arm in ('baseline', 'candidate'):
        assert all(sha(run/arm/n) == h for n, h in manifest['variant_sha256'][arm].items())
    rows = []
    for workload in WORKLOADS:
        for p03 in (0, 1):
            arms = {arm: read_run(run/('directed-'+arm)/f'{workload}-p03-{p03}.log')
                    for arm in ('baseline', 'candidate')}
            before, after = arms['baseline'], arms['candidate']
            for field in ('gpr', 'flags', 'memory'):
                assert before['signature'][field] == after['signature'][field], (workload, p03, field)
            for field in ('retired', 'writes', 'sdram_writes'):
                assert before['result'][field] == after['result'][field], (workload, p03, field)
            for field in ('consumed_bytes', 'redirects'):
                assert before['misc'][field] == after['misc'][field], (workload, p03, field)
            receipts = {}
            for arm in arms:
                log = run/('directed-'+arm)/f'{workload}-p03-{p03}.log'
                match = re.search(r'POSTED_RESULT enabled=(\d+) posted=(\d+) drained=(\d+) blocked=(\d+)', log.read_text())
                assert match
                receipts[arm] = dict(zip(('enabled', 'posted', 'drained', 'blocked'), map(int, match.groups())))
                assert receipts[arm]['posted'] == receipts[arm]['drained']
                assert receipts[arm]['posted'] == (arms[arm]['result']['writes'] if arm == 'candidate' else 0)
            b, c = before['result']['cycles'], after['result']['cycles']
            gain = b/c - 1
            rows.append({'workload': workload, 'p03': p03, 'arms': arms, 'posting': receipts,
                         'throughput_gain_fraction': gain, 'elapsed_reduction_fraction': 1-c/b})
            print('POSTED_DIRECTED', workload, 'p03', p03, 'clocks', b, c, 'gain_percent', round(100*gain, 4))
    result = {'source_manifest_sha256': sha(run/'source-manifest.json'), 'runs': rows,
              'production_rtl_modified': False,
              'limitations': ['Fixed-work kernels, not DOS CHECKNUM rates or hardware acceptance.',
                  'The whetstone fixture is fixed point, not CheckIT software floating point.',
                  'Both arms wait for physical idle after HLT: ten additional drain clocks versus the old P17 stop boundary.',
                  'Prefetch traffic and refresh phase can vary; consumed bytes and architectural/physical writes match.',
                  'No full regression or FPGA timing closure is established.']}
    (run/'directed-comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print('POSTED_DIRECTED_SOURCE_SIGNATURE_DRAIN_GUARDS_PASS')


if __name__ == '__main__':
    main()
