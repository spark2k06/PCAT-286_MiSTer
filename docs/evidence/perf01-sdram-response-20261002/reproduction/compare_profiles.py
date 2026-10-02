#!/usr/bin/env python3
"""Compare owner-only workload runs after both complete successfully."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path('/mnt/d/GitHub/PCAT-286_MiSTer')
EXP = ROOT / 'build/perf01-owner-experiment'
BASE = ROOT / 'build/perf01-response-baseline-20261002/profile'
CAND = EXP / 'profile'

def fields(line):
    return dict(word.split('=', 1) for word in line.split()[1:] if '=' in word)

def load(path):
    lines = path.read_text().splitlines()
    result = [fields(line) for line in lines if line.startswith('CHECKIT_DIRECTED_PASS ')]
    sig = [fields(line) for line in lines if line.startswith('PROFILE_SIGNATURE ')]
    assert len(result) == len(sig) == 1, f'Missing/duplicate completion in {path}'
    return {'result': result[0], 'signature': sig[0],
            'latencies': [fields(line) for line in lines if line.startswith('PROFILE_LATENCY ')],
            'owner': [fields(line) for line in lines if line.startswith('PROFILE_OWNER ')],
            'ram_buffer': [fields(line) for line in lines if line.startswith('RAM_BUFFER_RESULT ')],
            'sha256': sha256(path.read_bytes()).hexdigest()}

pairs = []
for workload in ('dhrystone', 'whetstone', 'working_set', 'dhrystone21'):
    for p03 in (0, 1):
        name = f'{workload}-p03-{p03}.log'
        before, after = load(BASE / name), load(CAND / name)
        assert before['signature'] == after['signature'], f'Architectural state mismatch: {name}'
        for counter in ('retired', 'writes', 'sdram_writes'):
            assert before['result'][counter] == after['result'][counter], f'{counter} mismatch: {name}'
        old, new = int(before['result']['cycles']), int(after['result']['cycles'])
        pairs.append({'workload': workload, 'p03': p03, 'baseline': before, 'candidate': after,
                      'cycles_saved': old - new, 'speedup': old / new,
                      'percent_fewer_cycles': 100 * (old - new) / old})
        print(f'OWNER_COMPARISON_PASS workload={workload} p03={p03} '
              f'baseline={old} candidate={new} saved={old-new} '
              f'fewer_cycles={100*(old-new)/old:.4f}%')

(EXP / 'profile-comparison.json').write_text(json.dumps({
    'status': 'PASS', 'baseline': str(BASE), 'candidate': str(CAND),
    'acceptance': 'GPR/FLAGS/full backing-memory signatures, retired count and write counts agree',
    'read_counter_policy': 'Speculative instruction traffic may differ; retained explicitly',
    'pairs': pairs,
}, indent=2) + '\n')
