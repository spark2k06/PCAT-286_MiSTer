#!/usr/bin/env python3
"""Audit complete fitted timing against source proofs and unchanged budgets."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from summarize_at_50mhz_timing import table_rows,parse_report
from check_at_net_delay import CORNERS,analyze_report
from check_sync_microcode_image import analyze_compiled_image
parser=argparse.ArgumentParser()
parser.add_argument('run',type=Path)
parser.add_argument('--net-budget',type=float)
parser.add_argument('--output',required=True)
parser.add_argument('--summary-file',type=Path)
parser.add_argument('--integration-cycle-sources',type=Path,
                    help='New directed workload manifest for bridge/SDRAM-owner latency changes only')
args=parser.parse_args()
run=(args.run if args.run.exists() or args.run.is_absolute() else root/'build'/args.run).resolve()
summary=json.loads((args.summary_file or run/'summary.json').read_text())
manifest=json.loads((run/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports=run/'timing'
if set(summary['corners'])!=set(CORNERS):raise ValueError('Incomplete/unexpected timing corners')
groups=('global','clk50_internal','clk50_incoming','cpu','cpu_bridge','bridge_cpu',
        'memory_port','code_buffer','data_buffer','data_buffer_outputs',
        'sdram_owner','sdram_owner_internal','keyboard','prebios_stage2','video',
        'sdram_input','sdram_output')
required={(corner,group,kind) for corner in CORNERS for group in groups for kind in ('setup','hold')}
required|={(corner,'global',kind) for corner in CORNERS for kind in ('recovery','removal')}
path_rows=[line.split() for line in (reports/'path_counts.txt').read_text().splitlines()]
observed=[tuple(row[:3]) for row in path_rows]
if any(len(row)!=5 for row in path_rows) or len(observed)!=len(set(observed)) or set(observed)!=required:
    raise ValueError('Incomplete, duplicate or unexpected timing path-count groups')
if set(summary['report_hashes'])!={str(p.relative_to(reports)) for p in reports.rglob('*') if p.is_file()}:
    raise ValueError('Timing-report inventory differs from summary')
for name,expected in summary['report_hashes'].items():
    if sha(reports/name)!=expected:raise ValueError('Raw timing report changed: '+name)
# Re-read actual report paths and the tool-returned minima. A modified JSON
# summary alone cannot turn negative raw report evidence into a pass.
for corner,group,kind,count,worst in path_rows:
    report_path=reports/corner/f'{group}_{kind}.rpt'
    if group=='global':
        command=report_path.read_text().split('Tcl Command:',1)[1].split('Options:',1)[0]
        if re.search(r'-(from|to)(?:_clock)?\s',command):
            raise ValueError('Global timing report has endpoint/clock filters')
    parsed=parse_report(report_path)
    parsed['tool_path_count']=int(count)
    parsed['tool_worst_slack_ns']=float(worst) if int(count) else None
    if parsed!=summary['corners'][corner][kind][group]:
        raise ValueError(f'Parsed raw report differs from summary: {corner} {group} {kind}')
changed=[]
generated_sources={}
for name,expected in manifest['source_sha256'].items():
    path=run/'work'/name
    if not path.is_file() or sha(path)!=expected:
        if name=='build_id.v' and path.is_file():
            # The unchanged upstream pre-flow hook regenerates only this
            # date macro. Retain both identities rather than rewriting the
            # original frozen manifest or accepting arbitrary generated RTL.
            generator=run/'work/sys/build_id.tcl'
            baseline=subprocess.check_output(['git','show','45e95b4:sys/build_id.tcl'],cwd=root).decode().replace('\r\n','\n')
            if generator.read_text()!=baseline:raise ValueError('Build metadata generator changed')
            start=datetime.datetime.fromisoformat((run/'compile-started.txt').read_text().strip())
            expected_macro=f'`define BUILD_DATE "{start:%y%m%d}"'
            if path.read_bytes()!=expected_macro.encode():raise ValueError('Unexpected generated build metadata')
            if f'Generated: /build/build_id.v: {expected_macro}' not in (run/'compile.log').read_text():
                raise ValueError('Generated build metadata not recorded by pre-flow hook')
            if path.stat().st_mtime < (run/'compile-started.txt').stat().st_mtime:
                raise ValueError('Generated build metadata predates compilation')
            generated_sources[name]={'frozen_sha256':expected,'compiled_sha256':sha(path),
                'value':expected_macro,'generator_sha256':sha(generator),
                'scope':'Only the logged build date macro is generated; original manifest retained'}
        else:changed.append(name)
if changed:raise ValueError('Frozen inputs changed: '+str(changed))
inventory=(run/'timing/collections.txt').read_text()
if 'clock=FPGA_CLK2_50 period=20.000' not in inventory or 'clock=SDRAM_CLK period=20.000' not in inventory:
    raise ValueError('Actual system/SDRAM clocks are not 20 ns')
for macro in ('AT_PROFILE','SPK286_AT_NO_DEBUG','SPK286_P07_SYNC_MICROCODE'):
    if f'macro={macro}\n' not in inventory:raise ValueError('Required macro missing '+macro)
if 'macro=SPK286_AT_DEBUG_CPU_DIV2\n' in inventory:raise ValueError('Divided CPU clock is active')
compile_log=(run/'compile.log').read_text()
if not re.search(r'Full Compilation was successful\. 0 errors',compile_log):
    raise ValueError('No successful complete compilation')
if 'PCAT_AT_PROJECT_PASS' not in (run/'project-check.log').read_text():
    raise ValueError('Project/profile guard did not pass')
for line in (run/'bitstreams.sha256').read_text().splitlines():
    expected,name=line.split(maxsplit=1)
    path=Path(name)
    if sha(path)!=expected:raise ValueError('Bitstream identity mismatch')
    if path.stat().st_mtime <= (run/'compile-started.txt').stat().st_mtime:
        raise ValueError('Bitstream is not newly generated')
reference=subprocess.check_output(['git','show','45e95b4:SYSTEM.sdc'],cwd=root).decode().replace('\r\n','\n')
actual=(run/'work/SYSTEM.sdc').read_text()
if args.net_budget is not None:
    match=re.search(r'        if \{\$instance eq "video_stats"\} \{\n.*?^        \}\n',actual,re.S|re.M)
    if not match:raise ValueError('Narrow video-statistics route bound missing')
    bound=re.search(r'set_net_delay -max (\d+\.\d+) -from \$src -to \$dst',match[0])
    if not bound or abs(float(bound[1])-args.net_budget)>0.0001:
        raise ValueError('Unexpected added physical route bound')
    body=[line.strip() for line in match[0].splitlines()[1:-1]
          if line.strip() and not line.strip().startswith('#')]
    if body!=[bound[0]]:raise ValueError('Extra command inside allowed route-bound block')
    actual=actual.replace(match[0],'')
if actual!=reference:raise ValueError('Original timing budget/constraints changed')
for name in manifest['source_sha256']:
    if not name.endswith('.sdc') or name=='SYSTEM.sdc':continue
    baseline=subprocess.check_output(['git','show',f'45e95b4:{name}'],cwd=root).decode().replace('\r\n','\n')
    if (run/'work'/name).read_text()!=baseline:
        raise ValueError('Inherited timing constraints changed: '+name)
cpu_proof=json.loads((root/'docs/evidence/sync-microcode-20261001/actual-depth-formal/receipt.json').read_text())
if [10,743] not in cpu_proof['sequencer_dimensions']:
    raise ValueError('Actual-depth CPU proof missing')
for name,expected in cpu_proof['source_sha256'].items():
    path=run/'work/vendor/spk286'/name
    data=path.read_bytes()
    if name=='rtl/spk286.sv':
        wrap=b'        .wrap_ip(!protected_msw[0]),\n'
        if data.count(wrap)!=1:raise ValueError('Sole documented fetch integration binding is missing')
        data=data.replace(wrap,b'')
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Compiled CPU source differs from exact proof: '+name)
rtc_proof=json.loads((root/'docs/evidence/rtc-bcd-lookup-20261002/proof.json').read_text())
if sha(run/'work/rtl/spk286_integration/spk286_at_rtc_cmos.sv')!=rtc_proof['candidate_rtc_sha256']:
    raise ValueError('Compiled RTC differs from its functional proof')
offset_dir=root/'docs/evidence/stack-offset-arithmetic-20261002/upstream-formal'
offset_proof=json.loads((offset_dir/'receipt.json').read_text())
if offset_proof['status']!='EXACT_STACK_OFFSET_EQUIVALENCE_PASS':
    raise ValueError('Exact stack-offset source proof missing')
for name,expected in offset_proof['artifacts_sha256'].items():
    if sha(offset_dir/name)!=expected:raise ValueError('Stack-offset proof artifact changed: '+name)
executor_sha=sha(run/'work/vendor/spk286/rtl/spk286_micro_executor.sv')
if executor_sha not in (offset_proof['reference_source_sha256'],offset_proof['candidate_source_sha256']):
    raise ValueError('Compiled executor differs from the exact arithmetic proof')
# Bind every CPU/integration input used by the appropriate directed cycle
# validation to this fitted workspace, not merely five CPU proof files.
if executor_sha==offset_proof['candidate_source_sha256']:
    cycle_sources=root/'docs/evidence/stack-offset-arithmetic-20261002/compiled-cycle-sources.sha256'
else:
    cycle_sources=root/'docs/evidence/sync-microcode-20261001/compiled-sources.sha256'
integration_cycle_binding=None
def read_cycle_manifest(path):
    entries={}
    for line in path.read_text().splitlines():
        match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        if not match or match[2] in entries:
            raise ValueError('Malformed or duplicate directed cycle source: '+str(path))
        entries[match[2]]=match[1]
    if not entries:raise ValueError('Empty directed cycle source manifest: '+str(path))
    return entries
cycle_hashes=read_cycle_manifest(cycle_sources)
if args.integration_cycle_sources:
    new_sources=args.integration_cycle_sources
    new_hashes=read_cycle_manifest(new_sources)
    if set(new_hashes)!=set(cycle_hashes):
        raise ValueError('New cycle validation must cover the identical complete source set')
    changed_cycle_inputs={name for name in cycle_hashes if cycle_hashes[name]!=new_hashes[name]}
    allowed_integration_inputs={'rtl/spk286_integration/spk286_at_bus_bridge.sv',
                                'rtl/spk286_integration/spk286_at_mister_sdram_owner.sv'}
    if not changed_cycle_inputs or not changed_cycle_inputs.issubset(allowed_integration_inputs):
        raise ValueError('Latency validation cannot replace CPU, harness, firmware or configuration proofs: '+
                         str(sorted(changed_cycle_inputs)))
    integration_cycle_binding={'manifest':str(new_sources),'sha256':sha(new_sources),
                               'changed_inputs':sorted(changed_cycle_inputs),
                               'scope':'Only bridge/owner rebound to new directed workload receipts; '
                                       'all CPU, firmware, configuration and harness inputs unchanged'}
    cycle_hashes=new_hashes
validated_source_count=0
for name,expected in cycle_hashes.items():
    relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Expected repository-relative cycle source')
    path=run/'work'/relative
    if sha(path)!=expected:raise ValueError('Fitted source differs from directed cycle validation: '+name)
    validated_source_count+=1
compiled_rom=analyze_compiled_image(run)
failures=[]
corners={}
for corner in CORNERS:
    d=summary['corners'][corner]
    margins={kind:d[kind]['global']['tool_worst_slack_ns'] for kind in ('setup','hold','recovery','removal')}
    for kind,slack in margins.items():
        if slack is None or slack<=0:failures.append(f'{corner} global {kind}: {slack}')
    check_report=(reports/corner/'check_timing.rpt').read_text()
    checks={row[0]:int(row[1]) for row in table_rows(check_report.split('; No Clock',1)[0])
            if len(row)==2 and row[1].isdigit()}
    if checks!=summary['corner_metadata'][corner]['check_timing_issues']:
        raise ValueError('check_timing metadata differs from actual report')
    allowed={'no_clock':3713,'multiple_clock':32,'no_input_delay':20,
             'no_output_delay':85,'partial_min_max_delay':24}
    mandatory={'loops','latches','generated_clock','virtual_clock','partial_multicycle',
               'multicycle_consistency','pll_cross_check','uncertainty'}|set(allowed)
    if not mandatory.issubset(checks):raise ValueError('Required timing coverage checks are missing')
    for name,count in checks.items():
        if name in allowed:
            if count!=allowed[name]:raise ValueError(f'Documented platform issue count changed {corner} {name}: {count}')
        elif count:raise ValueError(f'Unexpected check_timing issue {corner} {name}: {count}')
    families={}
    for row in table_rows(check_report):
        if len(row)==2 and row[1]=="No clock feeds this register's clock port.":
            family=re.split(r'[|~]',row[0],maxsplit=1)[0]
            families[family]=families.get(family,0)+1
    if families!=summary['corner_metadata'][corner]['unclocked_node_families']:
        raise ValueError('Unclocked family metadata differs from actual report')
    if families!={'sysmem_lite:sysmem':1239,'h2f_gp':617,'uart':619,'spi':621,'hdmi_i2c':617}:
        raise ValueError('Unexpected unclocked fabric family '+str(families))
    ucp=(run/'timing'/corner/'unconstrained.rpt').read_text()
    counts={row[0]:[int(v) for v in row[1:]] for row in table_rows(ucp.split('; Clock Status Summary',1)[0])
            if len(row)==3 and row[1].isdigit() and row[2].isdigit()}
    if counts.get('Illegal Clocks')!=[0,0] or counts.get('Unconstrained Clocks')!=[0,0]:
        raise ValueError('Unconstrained/illegal clocks in current fit')
    corners[corner]={'global_margins_ns':margins,'ucp':counts,'check_timing_issues':checks}
    if args.net_budget is not None:
        report=run/'net-delay-timing'/f'{corner}_net_delay.rpt'
        net=analyze_report(report.read_text(),args.net_budget)
        corners[corner]['bounded_payload']={k:v for k,v in net.items() if k!='edges'}
        if net['violated_edges'] or net['worst_slack_ns']<=0:
            failures.append(f'{corner} added net bound: {net["worst_slack_ns"]}')
status='MEASURED_TIMING_PASS_UNDER_DECLARED_SCOPE' if not failures else 'MEASURED_TIMING_FAIL'
result={'status':status,'run_directory':str(run.relative_to(root)),
    'manifest_sha256':sha(run/'manifest.json'),'frozen_source_files_verified':len(manifest['source_sha256']),
    'controlled_generated_sources':generated_sources,
    'directed_cycle_sources_verified':validated_source_count,'compiled_rom':compiled_rom,
    'integration_cycle_binding':integration_cycle_binding,
    'original_constraints_guard':'All frozen SDC inputs match 45e95b4; only the explicitly checked additional video_stats net bound may differ',
    'corners':corners,'failures':failures,
    'scope':'Constrained FPGA fabric and conditional W9825 SDRAM flight/device budget; not certification of inherited platform I/O or HPS hard blocks',
    'functional_validation':'Actual CPU proof sources (sole wrap_ip binding retained), exactly proven stack-offset executor and proven RTC source match this fit; test/compiled-image receipts reviewed separately',
    'hardware':'NOT_RUN','full_cpu_regression':'NOT_RUN'}
output=Path(args.output)
if output.exists():raise FileExistsError(output)
output.write_text(json.dumps(result,indent=2)+'\n')
print(status)
for failure in failures:print(failure)
raise SystemExit(1 if failures else 0)
