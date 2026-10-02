#!/usr/bin/env python3
"""Adopt only measured P18 files, checking the original production hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('promotion',type=Path)
    args=parser.parse_args()
    source=args.promotion.resolve()
    original=json.loads((source/'manifest.json').read_text())['source_sha256']
    measured=json.loads((source/'promotion-inputs.json').read_text())
    for n,h in measured['changed_sources'].items():
        assert sha(ROOT/n)==original[n], ('Production changed since snapshot',n)
        assert sha(source/'work'/n)==h
    for n,h in measured['new_sources'].items():
        assert not (ROOT/n).exists()
        assert sha(source/'work'/n)==h
    for n in measured['changed_sources'] | measured['new_sources']:
        shutil.copyfile(source/'work'/n,ROOT/n)
    for n in ('build_86box_memory_probe.py','spk286_memory_probe.hpp'):
        shutil.copyfile(source/'work/tools/perf01'/n,ROOT/'tools/perf01'/n)
    print('POSTED_CANDIDATE_ADOPTED')

if __name__=='__main__': main()
