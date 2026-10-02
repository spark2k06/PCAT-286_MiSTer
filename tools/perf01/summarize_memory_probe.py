"""Summarize completed unchanged CHECKNUM arms and their phase-boundary counters."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def difference(end, start):
    result = {}
    for key, value in end.items():
        old = start.get(key)
        if isinstance(value, bool) or isinstance(value, str) or old is None:
            continue
        if isinstance(value, dict):
            result[key] = difference(value, old)
        elif isinstance(value, list):
            result[key] = [a-b for a,b in zip(value, old)]
        elif isinstance(value, int):
            # Debug counts are 32-bit; benchmark intervals here are shorter
            # than one wrap. CPU resets are outside the recognized phases.
            result[key] = value-old
    return result


def summarize(arm, allow_host_teardown_issue=False):
    out = arm/'spk50'
    measurement = json.loads((out/'measurement.json').read_text())
    assert measurement['completion'] and measurement['guest_success'], 'Incomplete run is not a score'
    assert 'RC TICKRUN 0' in measurement['guest_status'] and 'ALL_DONE' in measurement['guest_status']
    match = re.fullmatch(r'TICKS_BEGIN=(\d+)\s+(\d+)\s+(\d+\.\d+)\s+TICKS_END=(\d+)\s*',
                         measurement['guest_output'])
    assert match, 'Missing complete guest output'
    assert int(match[2]) == measurement['dhrystones_per_second']
    assert float(match[3]) == measurement['kwhetstones_per_second']
    assert measurement['samples'], 'Missing coherent CPU configuration samples'
    host_issue = measurement['emulator_returncode'] != 0
    if host_issue:
        assert allow_host_teardown_issue, 'Host exit problem requires explicit classification/opt-in'
        assert measurement.get('host_teardown', '') not in ('', 'normal'), 'Unclassified host exit problem'
    assert all(s['cpu_hz_actual']==50000000 and s['isa_hz']==8000000 for s in measurement['samples'])
    profile = out/'memory-profile.json'
    final = json.loads(profile.read_text())
    assert final['final'], 'Missing final profile publication'
    records = [json.loads(line) for line in profile.with_name(profile.name+'.phases.jsonl').read_text().splitlines()]
    edges = {record['phase']:record for record in records}
    assert len(edges) == len(records), 'Unexpected repeated frontend/benchmark phase'
    phases = {}
    for name, preceding in [('dhrystone','frontend'), ('whetstone','integer_format')]:
        start, end = edges[preceding], edges[name]
        counts = difference(end, start)
        counts.pop('phase_clocks', None)
        counts.pop('phase_retired', None)
        counts['clocks_per_retired'] = counts['clocks']/counts['retired']
        counts['bus_wait_fraction'] = counts['wait']/counts['clocks']
        for kind, status in [('code',13),('data_read',5),('data_write',6)]:
            count = counts['transfers_by_status'][status]
            counts[kind+'_transfers'] = count
            counts[kind+'_average_wait'] = counts['wait_by_status'][status]/count if count else 0
        for name_key in ('code', 'data'):
            total = counts[name_key+'_hits']+counts[name_key+'_misses']
            counts[name_key+'_hit_fraction'] = counts[name_key+'_hits']/total if total else None
        phases[name] = counts
    files = [profile, profile.with_name(profile.name+'.phases.jsonl'), out/'measurement.json',
             arm/'probe-run.json', out/'samples.jsonl']
    traces = []
    for path in sorted(out.glob('memory-profile.json.*.csv')):
        lines = sum(1 for _ in path.open())-1
        assert lines == 250000, 'Trace sample incomplete'
        traces.append({'file':str(path), 'accepted_operations':lines, 'sha256':sha(path)})
    return {'arm':str(arm), 'pcat_timing':final['pcat_timing'],
            'dhrystones_per_second':measurement['dhrystones_per_second'],
            'kwhetstones_per_second':measurement['kwhetstones_per_second'],
            'guest_application_ticks':measurement['guest_application_ticks'],
            'host_elapsed_seconds':measurement['host_elapsed_seconds'],
            'emulator_returncode':measurement['emulator_returncode'],
            'host_teardown':measurement.get('host_teardown', 'normal'),
            'reconstructed_receipt':measurement.get('reconstructed_receipt', False),
            'binary_sha256':measurement['binary_sha256'],
            'image_sha256_before':measurement['image_sha256_before'],
            'phase_counters':phases, 'traces':traces,
            'receipts_sha256':{str(path):sha(path) for path in files}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ideal-arm', required=True, type=Path)
    p.add_argument('--pcat-arm', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--allow-host-teardown-issue', action='store_true',
                   help='Retain explicitly classified cleanup failures after complete guest RC0')
    a = p.parse_args()
    ideal = summarize(a.ideal_arm.resolve(), a.allow_host_teardown_issue)
    pcat = summarize(a.pcat_arm.resolve(), a.allow_host_teardown_issue)
    assert not ideal['pcat_timing'] and pcat['pcat_timing']
    assert ideal['image_sha256_before'] == pcat['image_sha256_before']
    hardware = {'dhrystones_per_second':4361, 'kwhetstones_per_second':83.7,
                'origin':'User-attested maximum-speed MiSTer observation, P10 candidate'}
    result = {'ideal':ideal, 'pcat':pcat, 'hardware_observation':hardware,
        'pcat_over_ideal_integer':pcat['dhrystones_per_second']/ideal['dhrystones_per_second'],
        'pcat_over_ideal_math':pcat['kwhetstones_per_second']/ideal['kwhetstones_per_second'],
        'pcat_over_hardware_integer':pcat['dhrystones_per_second']/hardware['dhrystones_per_second'],
        'pcat_over_hardware_math':pcat['kwhetstones_per_second']/hardware['kwhetstones_per_second'],
        'limitations':[
            'Memory timing/control co-simulation; 86Box owns data values and peripheral behavior.',
            'No external SDRAM electrical margin, DMA/loader or abstract AT refresh arbitration.',
            'Different READY timing can change adaptive iteration counts and interrupt placement.',
            'Bus wait counts overlap internal CPU execution; do not add them to CPU clock totals.',
            'Shadow capacities/associativity are accepted-stream tag estimates, not measured implementation speedups.',
            'Shadow models omit aborted fills and CPU reset flushes during boot; bounded phase traces include calibration and interrupts.',
            'Single complete run per arm; hardware observation has no repeat distribution.']}
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('ideal','pcat')}, indent=2))


if __name__ == '__main__':
    main()
