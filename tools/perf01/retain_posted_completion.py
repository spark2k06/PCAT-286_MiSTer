#!/usr/bin/env python3
"""Retain complete matched guest receipts and the strict P18 comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('experiment',type=Path); p.add_argument('destination',type=Path)
    a=p.parse_args(); root=a.experiment.resolve(); dest=a.destination.resolve()
    assert not dest.exists()
    comparison=json.loads((root/'complete-comparison.json').read_text())
    assert comparison['baseline']['dhrystones_per_second']==6138
    assert comparison['candidate']['dhrystones_per_second']==6906
    paths=['complete-comparison.json']
    for arm in ('pcat-baseline','pcat-candidate'):
        receipt=json.loads((root/arm/'spk50/measurement.json').read_text())
        assert receipt['completion'] and receipt['guest_success']
        paths += [arm+'/'+n for n in ('probe-run.json','profiles.json',
            'spk50/measurement.json','spk50/measurement-start.json','spk50/samples.jsonl',
            'spk50/memory-profile.json','spk50/memory-profile.json.phases.jsonl',
            'spk50/TICKRUN.TXT','spk50/STATUS.TXT','spk50/86box.cfg','spk50/global.cfg')]
        paths += [str(f.relative_to(root)) for f in (root/arm/'spk50/nvr-initial').iterdir()]
        probe=Path(receipt['command'][0]).parent
        paths += [str((probe/n).relative_to(root)) for n in ('build-manifest.json','pcat_memory_timing.sv')]
    for n in paths:
        dst=dest/n; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/n,dst); assert sha(root/n)==sha(dst)
    inventory={str(f.relative_to(dest)):{'sha256':sha(f),'bytes':f.stat().st_size}
               for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'retained-files.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('POSTED_COMPLETED_EVIDENCE_RETAINED',len(inventory))
if __name__=='__main__': main()
