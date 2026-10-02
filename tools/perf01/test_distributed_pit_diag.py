#!/usr/bin/env python3
"""Reuse the verified machine fixture to check the distributed AT diagnostic ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('compiled_fixture',type=Path); a=p.parse_args()
    out=a.compiled_fixture.resolve(); rec=out/'default-rom-verified.json'
    assert not rec.exists()
    rom=ROOT/'tests/firmware/pcat286_event_diag.rom'; rows=[]
    for d in (0,1):
        command=[str(out/f'div{d}/obj/posted_machine'),'+ROM='+str(rom),'+MAX_CYCLES=2000000']
        result=subprocess.check_output(command,cwd=ROOT/'rtl/video',text=True,timeout=60)
        assert f'POSTED_MACHINE_PASS div2={d} posts=12 drains=12' in result
        log=out/f'default-div{d}.log'; log.write_text(result)
        rows.append({'div2':d,'command':command,'log_sha256':sha(log)})
    rec.write_text(json.dumps({'rom_sha256':sha(rom),'runs':rows,
        'all_original_expectations_pass':True},indent=2)+'\n')
    print('DISTRIBUTED_PIT_DIAGNOSTIC_PASS')
if __name__=='__main__': main()
