#!/usr/bin/env python3
"""Retain verified combined-candidate reports without bitstream binaries."""
import argparse
import hashlib
import json
from pathlib import Path
from retain_posted_followup import retain

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('destination', type=Path)
    a = p.parse_args()
    run = a.run.resolve()
    rec = json.loads((run/'rbf-export.json').read_text())
    assert sha(run/'PCAT-286.rbf') == 'fe79d231d6ace5f4bc9ec49449188a43c8cbab2eb08ee24fd633e30b7ebeecff'
    assert sha(run/'PCAT-286.rbf') == sha(run/'work/output_files/PCAT-286.rbf')
    names = ['candidate-report.json', 'rbf-export.json', 'manifest.json',
             'container-image.txt', 'compile-started.txt', 'bitstreams.sha256',
             'rbf-info.txt', 'work/config.tcl']
    names += ['work/output_files/PCAT-286.'+s for s in ('fit.summary', 'sta.summary', 'flow.rpt')]
    names += [str(f.relative_to(run)) for f in sorted((run/'timing').rglob('*'))
              if f.is_file() and (f.name in ('path_counts.txt', 'collections.txt')
                 or 'fmax' in f.name or 'clk50_internal' in f.name or 'cpu_setup' in f.name)]
    retain(run, a.destination.resolve(), names)
    print('COMBINED_RBF_EVIDENCE_PASS export_metadata='+str(bool(rec)))

if __name__ == '__main__':
    main()
