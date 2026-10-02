"""Describe bounded accepted CHECKNUM bus traces; never infer a benchmark score."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def analyze(path, load_segment):
    status = Counter()
    code = Counter()
    data = Counter()
    writers = Counter()
    pages = Counter()
    first = last = None
    with path.open() as f:
        for row in csv.DictReader(f):
            values = {k:int(v) for k,v in row.items()}
            if first is None: first=values
            last=values
            address, kind = values['address'], values['status']
            status[kind] += 1
            if kind == 13:
                code[address//8] += 1
                pages[address//4096] += 1
            elif kind == 5:
                data[address//2] += 1
            elif kind == 6:
                writers[address//2] += 1
    assert first and sum(status.values()) == 250000
    indices = Counter(block%64 for block in code)
    data_sets = {}
    for word,count in data.items():
        data_sets.setdefault(word%512, []).append((word,count))
    conflicts = [(index,words) for index,words in data_sets.items() if len(words)>1]
    conflicts.sort(key=lambda item:sum(count for _,count in item[1]), reverse=True)
    return {'file':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'accepted_operations':sum(status.values()), 'status_counts':dict(status),
            'clock_span':last['clock']-first['clock'],
            'retired_span':last['retired']-first['retired'],
            'unique_code_8byte_blocks':len(code),
            'unique_code_block_bytes':len(code)*8,
            'unique_data_read_words':len(data), 'unique_written_words':len(writers),
            'data_indices_with_multiple_distinct_words':len(conflicts),
            'maximum_distinct_read_words_per_1KiB_index':max(len(v) for v in data_sets.values()),
            'top_data_index_conflicts':[{'index':index,
                'words':[{'physical_address':word*2, 'read_transfers':count}
                         for word,count in sorted(words,key=lambda item:item[1],reverse=True)]}
                for index,words in conflicts[:8]],
            'code_indices_with_multiple_distinct_blocks':sum(n>1 for n in indices.values()),
            'maximum_distinct_blocks_per_512B_index':max(indices.values()),
            'top_code_pages':[{'physical_base':page*4096,
                'relative_to_checknum_load_base':page*4096-load_segment*16,
                'fetches':count} for page,count in pages.most_common(12)],
            'note':'First 250000 accepted operations in the function phase, including calibration/interrupts. Unique footprint is not simultaneous cache occupancy.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    out=a.arm/'spk50'
    profile=json.loads((out/'memory-profile.json').read_text())
    load=profile['main_cs']-0x1de
    assert load>0, 'Frontend not recognized'
    result={'checknum_load_segment':load, 'traces':[
        analyze(path,load) for path in sorted(out.glob('memory-profile.json.*.csv'))]}
    assert len(result['traces'])==2, 'Both bounded traces required'
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
