"""Recover an already completed guest receipt after the old runner's teardown timeout."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

import argparse
p=argparse.ArgumentParser()
p.add_argument('--arm', required=True, type=Path)
arm=p.parse_args().arm.resolve()
out=arm/'spk50'
sys.path.insert(0, '/mnt/d/GitHub/86Box_dev/tools/spk286_cpu')
from run_pharlap import extract_results
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((out/'measurement-start.json').read_text())
assert not Path(f"/proc/{receipt['pid']}").exists(), 'Do not reconstruct while owned process exists'
assert not (out/'measurement.json').exists(), 'Never overwrite a measurement'
profile=json.loads((out/'memory-profile.json').read_text())
assert profile['final']
results=extract_results(out/'dos-test.img',out)
status=results.get('STATUS.TXT','')
value=results.get('TICKRUN.TXT','')
assert 'ALL_DONE' in status and 'RC TICKRUN 0' in status
match=re.fullmatch(r'TICKS_BEGIN=(\d+)\s+(\d+)\s+(\d+\.\d+)\s+TICKS_END=(\d+)\s*',value)
assert match
begin,score,math,end=match.groups()
samples=[json.loads(s) for s in (out/'samples.jsonl').read_text().splitlines()]
profiles=json.loads((arm/'profiles.json').read_text())
assert sha(Path(profiles['source']))==profiles['source_sha256_before']
delta=(int(end)-int(begin))%1573040
receipt.update(completion=True,guest_success=True,guest_status=status,guest_output=value,
    samples=samples,dhrystones_per_second=int(score),kwhetstones_per_second=float(math),
    bios_ticks_begin=int(begin),bios_ticks_end=int(end),guest_application_ticks=delta,
    guest_application_seconds=delta*65536/1193182,
    host_elapsed_seconds=samples[-1]['host_elapsed_seconds'],
    host_elapsed_seconds_scope='Through final coherent ALL_DONE sample, before teardown',
    emulator_returncode=None,host_teardown='old_runner_timeout_host_exit_status_unavailable',
    stop_reason='all_done',finished=datetime.datetime.now().astimezone().isoformat(),
    image_sha256_after=sha(out/'dos-test.img'),
    source_sha256_after=sha(Path(profiles['source'])),
    reconstructed_receipt=True,
    reconstruction_note='Old runner observed complete guest RC0 then timed out in both exit and SIGTERM waits. Process was absent when recovered; final profile already published. Original exit status was not captured.')
(out/'measurement.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('samples','command')},indent=2))

