"""Parse the user's completed P17 fit and compare it to the preserved P16 fit."""
from pathlib import Path
import hashlib
import json
import re

run = Path(__file__).resolve().parent
root = run.parents[1]
baseline_run = root/'build/perf01-write-admission-fit-20261002'
baseline = baseline_run/'work/output_files'
output = root/'output_files'
freeze = root/'build/perf01-entry-overlap-fit-20261002'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def table(text, title):
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().strip(';').strip() == title)
    rows = []
    for line in lines[start+1:]:
        if not line.startswith(';'):
            continue
        cells = [item.strip() for item in line.strip().strip(';').split(';')]
        if len(cells) == 1:
            break
        rows.append(cells)
    return rows

def number(text):
    return int(re.search(r'[\d,]+', text)[0].replace(',', ''))

def resources(directory):
    text = (directory/'PCAT-286.fit.rpt').read_text(encoding='latin-1')
    rows = table(text, 'Fitter Resource Usage Summary')
    usage = {r[0]: r[1] for r in rows[1:] if r[0]}
    summary = (directory/'PCAT-286.fit.summary').read_text(encoding='latin-1')
    assert 'Fitter Status : Successful' in summary
    def summary_value(key):
        return number(re.search(r'^'+re.escape(key)+r'\s*:\s*(.+)$',summary,re.M)[1])
    record = {'equivalent_alms': number(usage['ALMs needed [=A-B+C]']),
              'physical_alms': number(usage['[A] ALMs used in final placement [=a+b+c+d]']),
              'registers': summary_value('Total registers'),
              'm10k_blocks': summary_value('Total RAM Blocks'),
              'block_memory_bits': summary_value('Total block memory bits'),
              'block_memory_implementation_bits': number(usage['Total block memory implementation bits']),
              'dsp_blocks': summary_value('Total DSP Blocks'), 'plls': summary_value('Total PLLs')}
    entity_rows = table(text, 'Fitter Resource Utilization by Entity')
    selected = {'spk286_at_bus_bridge','spk286_at_mister_memory_port',
                'spk286_at_sdram_data_buffer','spk286_at_sdram_read_buffer',
                'spk286_at_mister_sdram_owner','KFSDRAM'}
    entities = [dict(zip(entity_rows[0], r)) for r in entity_rows[1:] if r[-2] in selected]
    assert {r['Entity Name'] for r in entities} == selected
    return record, entities, rows

def timing(directory):
    text = (directory/'PCAT-286.sta.summary').read_text(encoding='latin-1')
    pattern = r"Type\s*:\s*(.+?) Model (.+?) '(.+?)'\s*\nSlack\s*:\s*([-\d.]+)\s*\nTNS\s*:\s*([-\d.]+)"
    rows = [{'model':m,'type':k,'clock':c,'slack_ns':float(s),'tns_ns':float(t)}
            for m,k,c,s,t in re.findall(pattern,text)]
    assert rows
    cpu = {}
    for r in rows:
        if r['clock'] == 'FPGA_CLK2_50' and r['type'] in ('Setup','Hold'):
            cpu.setdefault(r['model'],{})[r['type'].lower()+'_slack_ns'] = r['slack_ns']
    assert len(cpu) == 4 and all(len(v) == 2 for v in cpu.values())
    report = (directory/'PCAT-286.sta.rpt').read_text(encoding='latin-1')
    fmax = {corner: [r for r in table(report, corner+' Model Fmax Summary') if len(r)>=3 and r[2]=='FPGA_CLK2_50'][0][:2]
            for corner in ('Slow 1100mV 100C','Slow 1100mV -40C')}
    return cpu, [r for r in rows if r['slack_ns'] < 0], fmax

before_manifest = json.loads((baseline_run/'manifest.json').read_text())
before_verified = json.loads((baseline_run/'post-source-verification.json').read_text())
for name,h in before_verified['artifacts'].items():
    assert sha(baseline/name) == h
frozen = json.loads((freeze/'manifest.json').read_text())
source_changes = [n for n,h in frozen['source_sha256'].items() if sha(root/n)!=h]
# Files are frozen before the user's compilation; this does not by itself
# attest the compiler read those bytes. Keep that provenance limitation.
compiled_names = [n for n in frozen['source_sha256']
                  if not n.startswith(('scripts/','sim/','SW/','tests/','vendor/spk286/tools/','vendor/spk286/tests/','vendor/spk286/sim/'))
                  and Path(n).suffix in ('.sv','.v','.svh','.vh','.qsf','.qpf','.sdc','.tcl','.qip','.mif','.mem','.hex')]
compiled_changes = [n for n in compiled_names if before_manifest['source_sha256'].get(n) != frozen['source_sha256'][n]]
assert set(compiled_changes) == {'rtl/spk286_integration/spk286_at_bus_bridge.sv',
                                 'rtl/spk286_integration/spk286_at_mister_memory_port.sv'},compiled_changes
assert not source_changes, source_changes
before,eb,rb = resources(baseline)
after,ea,ra = resources(output)
tb,nb,fb = timing(baseline)
ta,na,fa = timing(output)
entities = {}
for r in ea:
    name = r['Entity Name']
    old = next(r for r in eb if r['Entity Name']==name)
    decimal = lambda value: float(re.match(r'[\d,.]+',value)[0].replace(',',''))
    entities[name] = {'alms_before':decimal(old['ALMs needed [=A-B+C]']),
                      'alms_after':decimal(r['ALMs needed [=A-B+C]']),
                      'registers_before':number(old['Dedicated Logic Registers']),
                      'registers_after':number(r['Dedicated Logic Registers']),
                      'm10k_before':number(old['M10Ks']),'m10k_after':number(r['M10Ks'])}
flow = (output/'PCAT-286.flow.rpt').read_text(encoding='latin-1')
flow_summary = dict((r[0],r[1]) for r in table(flow,'Flow Summary') if len(r)==2)
flow_elapsed = next(r[1] for r in table(flow,'Flow Elapsed Time') if r[0]=='Total')
assert 'Successful' in flow_summary['Flow Status']
artifacts = {n:{'sha256':sha(output/n),'bytes':(output/n).stat().st_size}
             for n in ('PCAT-286.rbf','PCAT-286.fit.rpt','PCAT-286.fit.summary',
                       'PCAT-286.map.rpt','PCAT-286.map.summary','PCAT-286.sta.rpt',
                       'PCAT-286.sta.summary','PCAT-286.flow.rpt')}
observation = {'date':'2026-10-02','implementation_commit':'3168ba0',
    'scope':'User compilation; existing report and fitted netlist analysis, no synthesis or new regression.',
    'resources_before':before,'resources_after':after,
    'delta':{k:after[k]-before[k] for k in before},
    'entities':entities,'full_entity_rows_before':eb,'full_entity_rows_after':ea,
    'cpu_50mhz_before':tb,'cpu_50mhz_after':ta,'cpu_fmax_before':fb,'cpu_fmax_after':fa,
    'negative_sta_rows_before':nb,'negative_sta_rows_after':na,
    'all_design_timing_closed':not na,
    'flow_summary':flow_summary,'flow_elapsed':flow_elapsed,'artifacts':artifacts,
    'frozen_input_manifest_sha256':sha(freeze/'manifest.json'),
    'current_sources_match_pre_user_compile_freeze':not source_changes,
    'production_input_changes_vs_P16':compiled_changes,
    'provenance_limit':'Pre-user-build frozen inputs match current sources and fit hierarchy has P17 logic; no compiler-side input manifest or loaded-RBF hash attestation is available.',
    'hardware':{'integer_before':5139,'integer_after':5666,'math_before':97.1,'math_after':106.7,
        'integer_gain':5666/5139-1,'math_gain':106.7/97.1-1,
        'original_integer_baseline':3584,'original_integer_gain':5666/3584-1,
        'original_math_baseline':72.2,'original_math_gain':106.7/72.2-1,
        'origin':'User screenshots; CheckIT and CHECKNUM agree. Associated with latest P17 user build by session context.',
        'repeated_distribution_available':False,'loaded_rbf_hash_verified':False,
        'actual_hardware_cpu_osd_speed_reconfirmed':False}}
(run/'user-fit-observation.json').write_text(json.dumps(observation,indent=2)+'\n')
(run/'user-fit-resource-summary.txt').write_text('\n'.join(' | '.join(r) for r in ra)+'\n')
print(json.dumps({k:observation[k] for k in ('resources_after','delta','entities',
                                          'cpu_50mhz_after','negative_sta_rows_after',
                                          'flow_elapsed','hardware')},indent=2))
