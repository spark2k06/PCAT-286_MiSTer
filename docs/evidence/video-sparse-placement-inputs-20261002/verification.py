from pathlib import Path
import hashlib,json,subprocess
root=Path('/mnt/d/GitHub/PCAT-286_MiSTer')
reference=root/'build/stack-offset-seed2-fit-20261002'
baseline=json.loads((reference/'manifest.json').read_text())
proposal=root/'build/video-stats-sparse-pair-placement-20261002'
records=[]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for variant in ('stats','stats-hdmi'):
    run=root/'build'/f'sparse-pair-placement-{variant}-seed2-fit-20261002'
    manifest=json.loads((run/'manifest.json').read_text())
    suffix=(proposal/'stats-assignments.qsf').read_bytes()
    if variant=='stats-hdmi':suffix+=(proposal/'hdmi-assignments.qsf').read_bytes()
    assert (run/'work/PCAT-286.qsf').read_bytes()==(reference/'work/PCAT-286.qsf').read_bytes()+b'\n'+suffix
    assert (root/'PCAT-286.qsf').read_bytes()==(reference/'work/PCAT-286.qsf').read_bytes()
    relevant=[name for name in baseline['source_sha256'] if
        name.startswith(('rtl/','sys/','vendor/')) or name in ('config.tcl','files.qip','PCAT-286.sv','SYSTEM.sdc')]
    for name in relevant:
        assert name in manifest['source_sha256']
        assert manifest['source_sha256'][name]==baseline['source_sha256'][name],name
        assert sha(run/'work'/name)==manifest['source_sha256'][name],name
    changed=[name for name in baseline['source_sha256'] if
        manifest['source_sha256'].get(name)!=baseline['source_sha256'][name]]
    assert changed==['PCAT-286.qsf','scripts/check_sync_microcode_image.py'],changed
    checker='scripts/check_sync_microcode_image.py'
    committed=subprocess.check_output(['git','show','c7419eb:'+checker],cwd=root)
    assert (run/'work'/checker).read_bytes().replace(b'\r\n',b'\n')==committed
    records.append({'run':str(run.relative_to(root)),'status':'PURE_PLACEMENT_INPUT_IDENTITY_PASS',
        'unchanged_rtl_sys_vendor_and_clock_budget_inputs':len(relevant),
        'unchanged_original_snapshot_inputs':len(baseline['source_sha256'])-2,
        'sole_changed_compiled_input':'PCAT-286.qsf',
        'qsf_change':'Exact append of requested FF locations only',
        'changed_nonfunctional_checker':{'name':checker,'baseline_sha256':baseline['source_sha256'][checker],
             'candidate_sha256':manifest['source_sha256'][checker],
             'committed_version':'c7419eb: actual ROM audit refactor with optimized-Python guard retention'},
        'added_nonfunctional_tools':sorted(set(manifest['source_sha256'])-set(baseline['source_sha256'])),
        'baseline_manifest_sha256':sha(reference/'manifest.json'),
        'candidate_manifest_sha256':sha(run/'manifest.json'),
        'requested_registers':326 if variant=='stats' else 328,
        'compiled_build_date':'Existing unchanged pre-flow macro generation, independently audited after compilation',
        'production_changed':False,'timing_acceptance':'PENDING_COMPLETE_ALL_CORNER_REPORTS_AND_BINDINGS'})
out=root/'build/sparse-pair-placement-input-identity-20261002.json'
assert not out.exists()
out.write_text(json.dumps(records,indent=2)+'\n')
print('PURE_PLACEMENT_INPUT_IDENTITY_PASS',json.dumps(records,indent=2))
