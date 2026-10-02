#!/usr/bin/env python3
"""Retain the completed same-binary CHECKNUM AT-refresh controls."""
import argparse
import json
from pathlib import Path
from retain_posted_followup import retain, sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path); p.add_argument('destination',type=Path)
    a=p.parse_args(); run=a.run.resolve()
    comparison=json.loads((run/'complete-comparison.json').read_text())
    expected=((6138,113.6),(5666,106.7))
    for side,values in zip(('baseline','candidate'),expected):
        item=comparison[side]
        assert (item['dhrystones_per_second'],item['kwhetstones_per_second'])==values
    names=['complete-comparison.json','inputs.json','probe/build-manifest.json',
           'probe/pcat_memory_timing.sv']
    controls=[]
    for arm,values in zip(('pcat-control','pcat-at-refresh'),expected):
        receipt=json.loads((run/arm/'spk50/measurement.json').read_text())
        assert receipt['completion'] and receipt['guest_success']
        assert receipt['binary_sha256']==sha(run/'probe/86Box-memory-probe')
        assert (receipt['dhrystones_per_second'],receipt['kwhetstones_per_second'])==values
        controls.append(json.loads((run/arm/'probe-run.json').read_text())['at_refresh_control'])
        names += [arm+'/'+n for n in ('probe-run.json','profiles.json',
            'spk50/measurement.json','spk50/measurement-start.json','spk50/samples.jsonl',
            'spk50/memory-profile.json','spk50/memory-profile.json.phases.jsonl',
            'spk50/TICKRUN.TXT','spk50/STATUS.TXT','spk50/86box.cfg','spk50/global.cfg')]
        names += [str(f.relative_to(run)) for f in (run/arm/'spk50/nvr-initial').iterdir()]
    assert controls==[0,1]
    retain(run,a.destination.resolve(),names)
    print('AT_REFRESH_COMPLETED_EVIDENCE_PASS')

if __name__=='__main__': main()
