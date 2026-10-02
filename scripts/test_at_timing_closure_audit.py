#!/usr/bin/env python3
"""Bounded negative controls for the source-linked fitted timing auditor."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
CHECKER=ROOT/'scripts/check_at_timing_closure.py'


class ClosureAuditTests(unittest.TestCase):
    def command(self,run,output,summary=None):
        command=[sys.executable,str(CHECKER),str(run),'--output',str(output)]
        if summary:command+=['--summary-file',str(summary)]
        result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        output.with_suffix('.log').write_text(result.stdout)
        return result

    def test_negative_actual_fit_is_retained(self):
        output=OUT/'negative-actual-fit.json'
        result=self.command(RUN,output)
        self.assertEqual(result.returncode,1,result.stdout)
        receipt=json.loads(output.read_text())
        self.assertEqual(receipt['status'],'MEASURED_TIMING_FAIL')
        self.assertTrue(any('global setup: -' in s for s in receipt['failures']))
        self.assertEqual(receipt['directed_cycle_sources_verified'],59)
        self.assertEqual(receipt['compiled_rom']['valid_words'],743)

    def optimistic(self,kind):
        source=copy.deepcopy(SUMMARY)
        for corner in source['corners'].values():
            corner[kind]['global']['tool_worst_slack_ns']=1.0
        path=OUT/f'optimistic-{kind}-summary.json'
        path.write_text(json.dumps(source,indent=2)+'\n')
        result=self.command(RUN,OUT/f'optimistic-{kind}-audit.json',path)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Parsed raw report differs from summary',result.stdout)

    def test_optimistic_setup_is_rejected(self):self.optimistic('setup')
    def test_optimistic_hold_is_rejected(self):self.optimistic('hold')

    def test_missing_corner_is_rejected(self):
        source=copy.deepcopy(SUMMARY)
        source['corners'].pop(next(iter(source['corners'])))
        path=OUT/'missing-corner-summary.json'
        path.write_text(json.dumps(source,indent=2)+'\n')
        result=self.command(RUN,OUT/'missing-corner-audit.json',path)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Incomplete/unexpected timing corners',result.stdout)

    def report_variant(self,name,relative,change):
        variant=OUT/name
        reports=variant/'timing'
        reports.mkdir(parents=True,exist_ok=False)
        for original in (RUN/'timing').rglob('*'):
            if not original.is_file():continue
            rel=original.relative_to(RUN/'timing')
            target=reports/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            if str(rel)==relative:target.write_text(change(original.read_text()))
            else:target.symlink_to(original)
        (variant/'manifest.json').write_bytes((RUN/'manifest.json').read_bytes())
        source=copy.deepcopy(SUMMARY)
        source['report_hashes'][relative]=hashlib.sha256((reports/relative).read_bytes()).hexdigest()
        (variant/'summary.json').write_text(json.dumps(source,indent=2)+'\n')
        return variant

    def test_missing_global_path_count_is_rejected(self):
        def change(text):
            return '\n'.join(line for line in text.splitlines() if ' global setup ' not in line)+'\n'
        variant=self.report_variant('missing-global-counts','path_counts.txt',change)
        result=self.command(variant,OUT/'missing-global-counts-audit.json')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Incomplete, duplicate or unexpected timing path-count groups',result.stdout)

    def test_duplicate_path_count_is_rejected(self):
        variant=self.report_variant('duplicate-count','path_counts.txt',lambda text:text+text.splitlines()[0]+'\n')
        result=self.command(variant,OUT/'duplicate-count-audit.json')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Incomplete, duplicate or unexpected timing path-count groups',result.stdout)

    def test_filtered_global_report_is_rejected(self):
        corner=next(iter(SUMMARY['corners']))
        relative=f'{corner}/global_setup.rpt'
        variant=self.report_variant('filtered-global',relative,
            lambda text:text.replace('report_timing -setup -file','report_timing -setup -from filtered_nodes -file',1))
        result=self.command(variant,OUT/'filtered-global-audit.json')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Global timing report has endpoint/clock filters',result.stdout)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    RUN=args.run.resolve()
    OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=False)
    SUMMARY=json.loads((RUN/'summary.json').read_text())
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ClosureAuditTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (OUT/'receipt.json').write_text(json.dumps({'status':'PASS' if result.wasSuccessful() else 'FAIL',
        'test_count':result.testsRun,'reference_run':str(RUN),
        'reference_manifest_sha256':hashlib.sha256((RUN/'manifest.json').read_bytes()).hexdigest(),
        'checker_sha256':hashlib.sha256(CHECKER.read_bytes()).hexdigest(),
        'scope':'Expected failing real fit and six rejection controls; no timing closure claim'},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
