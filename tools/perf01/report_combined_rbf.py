#!/usr/bin/env python3
"""Verify the fresh combined RBF and report fitted cost/timing without waivers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def numeric(text,label):
    match=re.search(r'^'+re.escape(label)+r'\s*:\s*([\d,]+)',text,re.M)
    assert match,label
    return int(match[1].replace(',',''))
def resource(directory):
    summary=(directory/'PCAT-286.fit.summary').read_text(encoding='latin-1')
    assert 'Fitter Status : Successful' in summary
    fit=(directory/'PCAT-286.fit.rpt').read_text(encoding='latin-1')
    placed=re.search(r'ALMs used in final placement \[=a\+b\+c\+d\]\s*;\s*([\d,]+)',fit)
    assert placed
    return {'equivalent_alms':numeric(summary,'Logic utilization (in ALMs)'),
        'placed_alms':int(placed[1].replace(',','')),
        'registers':numeric(summary,'Total registers'),
        'memory_bits':numeric(summary,'Total block memory bits'),
        'm10k':numeric(summary,'Total RAM Blocks'),
        'dsp':numeric(summary,'Total DSP Blocks'),'plls':numeric(summary,'Total PLLs')}
def timing(directory):
    text=(directory/'PCAT-286.sta.summary').read_text(encoding='latin-1')
    rows=[]
    for match in re.finditer(r'Type\s*:\s*(.+?)\nSlack\s*:\s*(-?[\d.]+)\nTNS\s*:\s*(-?[\d.]+)',text):
        rows.append({'type':match[1], 'slack_ns':float(match[2]), 'tns_ns':float(match[3])})
    assert len([r for r in rows if "Setup 'FPGA_CLK2_50'" in r['type']])==4
    assert len([r for r in rows if "Hold 'FPGA_CLK2_50'" in r['type']])==4
    return rows
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); run=a.run.resolve(); out=a.output.resolve()
    assert not out.exists()
    work=run/'work'; directory=work/'output_files'
    manifest=json.loads((run/'manifest.json').read_text())
    changed=[]
    for n,h in manifest['source_sha256'].items():
        if not (work/n).exists() or sha(work/n)!=h: changed.append(n)
    assert not changed, ('Frozen compilation inputs changed',changed)
    critical=[n for n in manifest['source_sha256'] if
              n.startswith(('rtl/','sys/','vendor/spk286/rtl/','vendor/spk286/microcode/generated/'))
              or ('/' not in n and Path(n).suffix in ('.sv','.v','.qsf','.qip','.sdc','.tcl'))]
    assert all(sha(ROOT/n)==manifest['source_sha256'][n] for n in critical), 'Current production differs from frozen RBF inputs'
    config=(work/'config.tcl').read_text()
    macros=re.findall(r'^\s*set_global_assignment -name VERILOG_MACRO "([^"]+)"',config,re.M)
    assert 'SPK286_AT_NO_DEBUG' in macros and 'SPK286_AT_DEBUG_CPU_DIV2' not in macros
    assert 'PIT' in (work/'rtl/spk286_integration/spk286_at_refresh.sv').read_text()
    assert '.timer_1_out            (pit_counter_out[1])' in (work/'rtl/spk286_integration/spk286_at_machine.sv').read_text()
    baseline=run/'baseline-p17'
    assert sha(baseline/'PCAT-286.rbf')=='94f210cbaa590e3e80e210e661bea5eb9ba34772a6c8d04f797620359ba27ad0', 'Different P17 baseline'
    b,c=resource(baseline),resource(directory)
    assert b=={'equivalent_alms':30832,'placed_alms':36191,'registers':38198,
               'memory_bits':3301019,'m10k':416,'dsp':39,'plls':3}
    rbf=directory/'PCAT-286.rbf'; sof=directory/'PCAT-286.sof'
    assert rbf.stat().st_mtime>(run/'compile-started.txt').stat().st_mtime
    for f in (rbf,sof): assert f.stat().st_size>0
    compile_text=(run/'compile.log').read_text()
    assert 'Full Compilation was successful' in compile_text
    rows=timing(directory)
    hierarchy=[]
    for line in (directory/'PCAT-286.fit.rpt').read_text(encoding='latin-1').splitlines():
        columns=[c.strip() for c in line.split(';')]
        if len(columns)>17 and columns[-3] in ('spk286_at_posted_write_buffer','spk286_at_refresh','spk286_at_bus_bridge'):
            hierarchy.append(columns[1:-1])
    result={'source_snapshot_head':manifest['head'],
        'source_guard_files':len(manifest['source_sha256']), 'source_guard_pass':True,
        'current_production_guard_files':len(critical),'current_production_matches_snapshot':True,
        'configuration_macros':macros,'configured_cpu_mhz':50,'no_debug':True,
        'rbf':{'path':str(rbf),'bytes':rbf.stat().st_size,'sha256':sha(rbf),
               'modified_utc':datetime.fromtimestamp(rbf.stat().st_mtime,timezone.utc).isoformat()},
        'sof_sha256':sha(sof),'baseline_resources':b,'candidate_resources':c,
        'resource_delta':{k:c[k]-b[k] for k in b},'hierarchy_rows':hierarchy,
        'timing_summary':rows, 'whole_design_nonnegative_summary':all(r['slack_ns']>=0 for r in rows),
        'hardware_validation':'pending','full_regression':'not run; user deferred',
        'timing_closure':'user deferred; reports describe the generated fit',
        'reports_sha256':{n:sha(directory/n) for n in ('PCAT-286.fit.summary','PCAT-286.fit.rpt',
            'PCAT-286.sta.summary','PCAT-286.flow.rpt')},
        'compile_log_sha256':sha(run/'compile.log'),'manifest_sha256':sha(run/'manifest.json')}
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('rbf','candidate_resources','resource_delta','whole_design_nonnegative_summary')},indent=2))
if __name__=='__main__': main()
