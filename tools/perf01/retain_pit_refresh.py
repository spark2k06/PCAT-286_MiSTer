#!/usr/bin/env python3
"""Retain bounded PIT-refresh validation, including original fixture failures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('initial',type=Path); p.add_argument('verified',type=Path)
    p.add_argument('destination',type=Path); a=p.parse_args()
    assert not a.destination.exists()
    assert 'PIT_REFRESH_PASS checks=27 periods=9' in (a.verified/'pit-directed.log').read_text()
    assert 'A4_DMA_REFRESH_PIT_TEST_PASS' in (a.verified/'a4.log').read_text()
    assert 'POSTED_MACHINE_SOURCE_GUARD_PASS' in (a.initial/'machine-directed.log').read_text()
    groups={a.initial:['inputs.json','pit-directed.log','pit-observation.log','a4.log',
        'machine-directed.log','machine-directed/inputs.json','machine-directed/entry-pit.asm',
        'machine-directed/entry.rom','machine-directed/spk286_at_machine_tb.sv',
        'machine-directed/div0/run.log','machine-directed/div1/run.log'],
        a.verified:['inputs.json','pit-directed.log','pit-directed/sources.sha256',
        'pit-directed/strict-lint.log','pit-directed/iverilog-run.log',
        'pit-directed/verilator-run.log','pit-directed/source-guard.log',
        'a4.log','a4/iverilog-run.log','a4/verilator-run.log',
        'work/rtl/spk286_integration/spk286_at_refresh.sv',
        'work/rtl/spk286_integration/spk286_at_machine.sv',
        'work/sim/spk286_integration/spk286_at_dma_refresh_pit_tb.sv']}
    for src,names in groups.items():
        label='initial' if src==a.initial else 'verified'
        for n in names:
            dst=a.destination/label/n; dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src/n,dst); assert sha(src/n)==sha(dst)
    for n in ('test_pit_refresh.sh','prototypes/spk286_at_pit_refresh_tb.sv',
              'test_posted_machine.py','prepare_pit_refresh_candidate.py'):
        dst=a.destination/'tools'/n; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'tools/perf01'/n,dst)
    inventory={str(f.relative_to(a.destination)):{'sha256':sha(f),'bytes':f.stat().st_size}
               for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'retained-files.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('PIT_REFRESH_EVIDENCE_RETAINED',len(inventory))
if __name__=='__main__': main()
