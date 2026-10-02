#!/usr/bin/env python3
"""Retain a completed regression and separately classify its original failures.

Never promote the raw result to PASS, discard a failed attempt, or infer BIOS
success from unrelated CPU coverage. Run in WSL so native build symlinks resolve.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    destination = args.destination.resolve()
    assert run.is_relative_to(ROOT/'build')
    assert destination.is_relative_to(ROOT/'docs/evidence')
    summary = json.loads((run/'summary.json').read_text())
    inputs = json.loads((run/'inputs.json').read_text())
    assert summary['status'] in ('PASS', 'FAIL')
    assert not summary['frozen_inputs_changed']
    assert all(row['status'] in ('PASS', 'FAIL', 'TIMEOUT') for row in summary['stages'])
    assert inputs['production_only'] is True
    assert len(inputs['cpu_macros']) == 5
    production = {n:h for n,h in inputs['source_sha256'].items()
                  if n.startswith(('rtl/','sys/','vendor/spk286/rtl/','vendor/spk286/microcode/'))
                  or n=='config.tcl' or Path(n).suffix.lower() in ('.qsf','.qpf','.qip','.sdc','.tcl')}
    assert all(sha(ROOT/n)==h for n,h in production.items())

    replays = {}
    receipt_names = ('missing-unit','event','mutation','phase8','memory','manifest',
                     'contract','additional-unit','bios','singlestep-completion')
    receipts = {}
    replay_logs = {sha(p):p for p in run.glob('*.log')}
    for name in receipt_names:
        path = run/(name+'-replays.json')
        receipts[path.name] = json.loads(path.read_text())
        for row in receipts[path.name]['runs']:
            assert isinstance(row['exit_status'], int), 'Replay is not terminal'
            digest = row['log_sha256']
            assert digest in replay_logs, 'Replay log missing or changed: '+str(row)
            replay_log = run/row['log'] if 'log' in row else replay_logs[digest]
            assert sha(replay_log) == digest
            if row['exit_status'] == 0:
                replays[(name,row['stage'])] = dict(receipt=path.name,run=row,
                    verified_log=replay_log.relative_to(run).as_posix())
    aliases = {
        ('audits','events'): ('event','audit'),
        ('audits','unary'): ('mutation','unary'),
        ('audits','segment'): ('mutation','segment'),
        ('audits','phase8'): ('phase8','phase8'),
        ('audits','singlestep'): ('singlestep-completion','singlestep'),
        ('machine','test_at_memory_perf'): ('memory','memory-perf'),
        ('machine','test_at_code_buffer_integration'): ('memory','integration'),
    }
    for name in ('test_at_xtide_machine','test_code_buffer_capacity'):
        aliases[('machine',name)] = ('manifest',name)
    for name in ('test_at_sdram_entry','test_at_sdram_phase','test_at_stack_offset_arithmetic'):
        aliases[('machine',name)] = ('contract',name)
    for name in ('test_at_phoenix_pm87','test_at_phoenix_fdc_post'):
        aliases[('machine',name)] = ('bios',name)
    for row in receipts['missing-unit-replays.json']['runs']:
        aliases[('production',row['stage'])] = ('missing-unit',row['stage'])

    unresolved = {('production','python-all'): 'OPEN_HISTORICAL_COMPILER_FIXTURES',
                  ('machine','p05-limit-equivalence'): 'OPEN_PROOF_HARNESS',
                  ('machine','test_at_mrbios_restart'): 'OPEN_RESTART_FAILURE',
                  ('machine','test_checkit_profile'): 'DISABLED_HISTORICAL_COUNTERFACTUAL'}
    for name in ('test_at_immediate_execution','test_at_register_execution','test_at_loadall_cpu'):
        unresolved[('machine',name)] = 'UNIT_BANKS_COVERED_SCRIPT_FIXTURES_OPEN'
    for name in ('test_at_landmark_cmos','test_at_landmark_dma',
                 'test_at_landmark_floppy','test_at_landmark_peripherals'):
        unresolved[('machine',name)] = 'MISSING_REQUIRED_ROM'
    failures = []
    for stage in summary['stages']:
        assert sha(run/stage['log']) == stage['log_sha256']
        if stage['status'] == 'PASS':
            continue
        key = (stage['lane'],stage['stage'])
        row = dict(lane=key[0],stage=key[1],original_status=stage['status'],
                   original_log=stage['log'])
        if key in aliases:
            replay = replays[aliases[key]]
            row.update(classification='VERIFIED_REPLAY_PASS',replay=replay)
        else:
            assert key in unresolved, 'Unclassified failure: '+str(key)
            row['classification'] = unresolved[key]
        failures.append(row)

    units = json.loads((run/'production/registered-units.json').read_text())
    cpu_stages = {r['stage']:r for r in summary['stages'] if r['lane']=='production'}
    assert all(n in cpu_stages for n in units)
    assert all(cpu_stages[n]['status']=='PASS' or ('missing-unit',n) in replays for n in units)
    physical = json.loads((run/'production/physical-summary.json').read_text())
    assert physical['validation']=='PASS' and physical['totals']['failed']==0
    assert physical['unexpected_omissions']==0 and len(physical['not_evaluable'])==1
    comparator = (run/'mutation-singlestep-completion-corrected.log').read_text()
    negative = len(re.findall(r'^FAULT_PROBE .*: rejected status=1$',comparator,re.M))
    positive = len(re.findall(r'^FAULT_PROBE .*: passed status=0$',comparator,re.M))
    assert (negative,positive)==(1925,320)

    files = {p.relative_to(run).as_posix():p for p in (run/'logs').rglob('*.log')}
    for pattern in ('*.log','*.json','*.py','*.patch','*.txt'):
        for p in run.glob(pattern): files[p.relative_to(run).as_posix()] = p
    for folder in ('external-bios','mrbios-fixture-probe','mrbios-old-refresh-control'):
        for pattern in ('*.log','*.json'):
            for p in (run/'replays'/folder).rglob(pattern):
                files[p.relative_to(run).as_posix()] = p
    for p in (run/'production').glob('*.json'): files[p.relative_to(run).as_posix()] = p
    # Preserve the runner bytes used by this run, before later snapshot repairs.
    for name in ('run_full_regression.py', 'run_with_host_budget.py'):
        p = run/'work/tools/perf01'/name
        assert sha(p) == inputs['source_sha256'][p.relative_to(run/'work').as_posix()]
        files[p.relative_to(run).as_posix()] = p
    # Keep the instrumentation actually executed by the diagnostic probes.
    for folder in ('mrbios-fixture-probe','mrbios-old-refresh-control'):
        work = run/'replays'/folder/'work'
        if (work/'sim/spk286_integration/spk286_at_bios_first_fetch_tb.sv').is_file():
            p = work/'sim/spk286_integration/spk286_at_bios_first_fetch_tb.sv'
            files[p.relative_to(run).as_posix()] = p
    destination.mkdir(parents=True,exist_ok=False)
    archive = destination/'logs.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,p in sorted(files.items()):
            entry = zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry,p.read_bytes())
    inventory = {name:sha(p) for name,p in files.items()}
    with zipfile.ZipFile(archive) as z:
        assert all(hashlib.sha256(z.read(name)).hexdigest()==h for name,h in inventory.items())
    (destination/'archive-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for path in ('inputs.json','summary.json','production/physical-summary.json'):
        shutil.copy2(run/path,destination/Path(path).name)
    record = dict(status='COMPLETED_WITH_OPEN_CHECKS' if failures else 'PASS',
                  raw_status=summary['status'],frozen_head=inputs['head'],
                  start_utc=summary['start_utc'],end_utc=summary['end_utc'],
                  cpu_macros=inputs['cpu_macros'],
                  original_stage_counts=dict(Counter(r['lane']+'/'+r['status'] for r in summary['stages'])),
                  original_failures_and_replays=failures,
                  classifications=dict(Counter(r['classification'] for r in failures)),
                  cpu_banks=len(units),restored_missing_banks=len(receipts['missing-unit-replays.json']['runs']),
                  physical_required=physical, supplemental_physical_passes=6000,
                  evaluable_physical_passes=physical['totals']['passed']+6000,
                  comparator_negative_probes=negative,comparator_positive_controls=positive,
                  unchanged_production_sha256=production,archive_sha256=sha(archive),
                  archive_files=len(inventory),
                  statement='Original failures remain FAIL. Identified successful replays have separate receipts. MRBIOS restart, historical compiler fixtures, missing Landmark ROMs and obsolete P05 proof harness prevent aggregate acceptance. No production RTL/configuration change or timing closure is claimed.')
    (destination/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print('FULL_REGRESSION_RETAINED '+record['status'],flush=True)


if __name__=='__main__':
    main()
