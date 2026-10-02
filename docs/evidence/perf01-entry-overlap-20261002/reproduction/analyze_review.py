"""Derive throughput-review observations from completed P16 evidence only."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json

run = Path(__file__).resolve().parent
root = run.parents[1]
old = root / 'build/perf01-write-admission-20261002'
comparison = json.loads((old / 'comparison.json').read_text())
sample = comparison['candidate']
observations = {}
for phase, counts in sample['phase_counters'].items():
    if phase not in ('dhrystone', 'whetstone'):
        continue
    transfers = counts['transfers_by_status']
    waits = counts['latency_by_status']
    trace = old / 'pcat-write-admission/spk50' / ('memory-profile.json.' + phase + '.csv')
    histogram = Counter()
    same_row = 0
    writes = 0
    previous = None
    with trace.open() as stream:
        for event in csv.DictReader(stream):
            if int(event['status']) != 6:
                continue
            address = int(event['address'])
            word = address >> 1
            row = ((word >> 22) & 3, (word >> 9) & 8191)
            histogram[row] += 1
            same_row += previous == row
            previous = row
            writes += 1
    observations[phase] = {
        'complete_phase_clocks': counts['clocks'],
        'retired': counts['retired'], 'cpi': counts['clocks'] / counts['retired'],
        'code_transfers': transfers[13], 'code_misses': counts['code_misses'],
        'data_read_transfers': transfers[5], 'data_misses': counts['data_misses'],
        'writes': transfers[6],
        'code_hit_fraction': counts['code_hits'] / (counts['code_hits'] + counts['code_misses']),
        'data_hit_fraction': counts['data_hits'] / (counts['data_hits'] + counts['data_misses']),
        'wait_mean_code': waits[13] / transfers[13],
        'wait_mean_data_read': waits[5] / transfers[5],
        'wait_mean_write': waits[6] / transfers[6],
        'raw_one_clock_per_read_budget': transfers[13] + transfers[5],
        'raw_one_clock_per_read_budget_fraction': (transfers[13] + transfers[5]) / counts['clocks'],
        'trace_file_sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
        'bounded_trace_write_events': writes,
        'bounded_trace_write_banks': sorted(set(bank for bank, row in histogram)),
        'bounded_trace_write_rows': len(histogram),
        'adjacent_write_row_repeat_fraction': same_row / (writes - 1) if writes > 1 else None,
        'top_write_rows': [{'bank': row[0], 'row': row[1], 'events': count}
                           for row, count in histogram.most_common(5)],
    }
report = {
    'source_comparison_sha256': hashlib.sha256((old / 'comparison.json').read_bytes()).hexdigest(),
    'completed_pcat_rates': [sample['dhrystones_per_second'], sample['kwhetstones_per_second']],
    'completed_immediate_ready_rates': [7709, 133.3],
    'ideal_over_pcat_gain_fraction': [7709 / sample['dhrystones_per_second'] - 1,
                                    133.3 / sample['kwhetstones_per_second'] - 1],
    'phases': observations,
    'limitations': [
        'Raw read-clock budget is not saved elapsed time; CPU prefetch overlaps execution.',
        'Trace is only the first 250000 accepted CPU events including calibration and interrupts.',
        'Adjacent-write locality ignores intervening physical reads, refresh and other owners.',
        'No SDRAM row-hit rate or open-row throughput gain has been measured.',
    ]}
(run / 'completed-baseline-review.json').write_text(json.dumps(report, indent=2) + '\n')
for phase, counts in observations.items():
    print('THROUGHPUT_REVIEW', phase, 'hit_percent',
          round(100 * counts['code_hit_fraction'], 5),
          round(100 * counts['data_hit_fraction'], 5),
          'write_row_repeat_percent', round(100 * counts['adjacent_write_row_repeat_fraction'], 3),
          'write_banks', counts['bounded_trace_write_banks'])
