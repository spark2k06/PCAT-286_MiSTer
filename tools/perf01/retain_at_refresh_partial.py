#!/usr/bin/env python3
"""Retain first real CHECKNUM AT-refresh attribution, without final-score claims."""
import argparse
import json
from pathlib import Path
from retain_posted_followup import retain,sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path); p.add_argument('destination',type=Path)
    a=p.parse_args(); run=a.run.resolve()
    control=json.loads((run/'partial-control.json').read_text())
    refresh=json.loads((run/'partial-refresh32.json').read_text())
    assert control['dhrystone_partial']==6138 and refresh['dhrystone_partial']==5666
    assert control['binary_sha256']==refresh['binary_sha256']==sha(run/'probe/86Box-memory-probe')
    names=['partial-control.json','partial-refresh32.json','inputs.json','build.log',
           'probe/build-manifest.json','probe/pcat_memory_timing.sv',
           'source/rtl/spk286_integration/spk286_at_refresh.sv',
           'source/rtl/spk286_integration/spk286_at_arbiter.sv',
           'source/tools/perf01/build_86box_memory_probe.py',
           'source/tools/perf01/spk286_memory_probe.hpp']
    receipts=[]
    for arm in ('pcat-control','pcat-at-refresh'):
        receipts.append(json.loads((run/arm/'probe-run.json').read_text()))
        names += [arm+'/probe-run.json',arm+'/spk50/measurement-start.json']
    for key in ('checknum_sha256','initial_image_sha256','config_sha256','nvr_sha256'):
        assert receipts[0][key]==receipts[1][key]
    assert [r['at_refresh_control'] for r in receipts]==[0,1]
    retain(run,a.destination.resolve(),names)
if __name__=='__main__': main()
