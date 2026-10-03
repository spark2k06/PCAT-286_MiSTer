from pathlib import Path
import hashlib, importlib.util, json, re, shutil

root=Path(__file__).resolve().parents[2]
build=root/'build/p06-waitstates-reference-20261003'
out=root/'docs/evidence/p06-waitstates-reference-20261003'
assert not out.exists() or {p.name for p in out.iterdir()}=={'README.md'}
out.mkdir(parents=True,exist_ok=True)

def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def identity(p):
    return dict(bytes=p.stat().st_size,sha256=sha(p))

def copy(p,name):
    q=out/name
    q.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(p,q)
    assert p.read_bytes()==q.read_bytes()

spec=importlib.util.spec_from_file_location('validator',root/'SW/CPUTIME/validate_t286ref.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
runner=root/'SW/CPUTIME/run_native_reference.py'
validator=root/'SW/CPUTIME/validate_t286ref.py'
program=root/'build/p06-timing-reference-20261003/T286REF.COM'
assert sha(runner)=='ec85e240a9f9b4d2d5996ab0b1a5351a995aeaadb6b2e4cac86ebd63c0bbb1ad'
assert sha(validator)=='71d976caa0c2ee265e42fc3d8feb299537129367a3839647cd1da12715e904b3'
assert sha(program)=='006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643'
files=('measurement.json','REF.CSV','STATUS.TXT','86box.cfg','86box.log','console.log','samples.json','start.json')
selected={}
for tag,hz,ws,isa in (
    ('native6-ws1',6000000,1,6000000),('native6-ws2',6000000,2,6000000),
    ('native12-ws1',12500000,1,8000000),('native12-ws2',12500000,2,8000000),
):
    run=build/(tag+'-paused')
    m=json.loads((run/'measurement.json').read_text())
    assert m['completed'] and m['guest_success'] and m['failure'] is None and m['emulator_returncode']==0
    assert m['hz']==hz and m['requested_visible_wait_states']==ws and m['cpu_waitstates_config']==ws+1
    assert m['runner_sha256']==sha(runner) and m['validator_sha256']==sha(validator)
    assert m['program_sha256']==sha(program) and m['binary_sha256']==sha(run/'86Box-native')
    assert m['source_disk_sha256']==m['source_disk_sha256_after']=='cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f'
    assert m['image_sha256_after']==sha(run/'dos-test.img')
    profile='native6-final' if hz==6000000 else 'native12-final'
    profile_path=root/'docs/evidence/p06-timing-reference-20261003'/profile/'86box.cfg'
    initial=profile_path.read_text()
    initial=re.sub(r'^cpu_speed\s*=.*$',f'cpu_speed = {hz}',initial,flags=re.M)
    initial=re.sub(r'^hdd_01_fn\s*=.*$','hdd_01_fn = dos-test.img',initial,flags=re.M)
    initial=re.sub(r'^cpu_waitstates[ \t]*=.*\n?','',initial,flags=re.M)
    initial=initial.replace('[Machine]\n',f'[Machine]\ncpu_waitstates = {ws+1}\n',1)
    initial_bytes=initial.encode('utf-8')
    assert hashlib.sha256(initial_bytes).hexdigest()==m['initial_config_sha256']
    cfg=(run/'86box.cfg').read_text()
    assert re.search(rf'^cpu_waitstates = {ws+1}$',cfg,re.M)
    assert re.search(rf'^cpu_speed = {hz}$',cfg,re.M)
    assert m['guest_output']['STATUS.TXT']=='BEGIN\r\nRC0\r\nALL_DONE\r\n'
    csv=(run/'REF.CSV').read_bytes().decode('ascii')
    assert m['guest_output']['REF.CSV']==csv
    val=v.validate_csv(csv,'6' if hz==6000000 else '12.5')
    assert val['csv_sha256']==m['csv_validation']['csv_sha256']
    assert val['sample_count']==42 and val['summary_count']==6 and not val['timer_calibrated']
    assert all(val['controls'].values()) and val['metadata']['pit_mode']=='2'
    assert m['samples']
    for s in m['samples']:
        assert s['cpu_waitstates']==ws+1 and s['cpu_hz_actual']==hz and s['dispatcher']==0x4a75b0
        assert s['cpu_prefetch_cycles']==s['cpu_cycles_read']==s['cpu_cycles_write']==ws+2
        assert s['cpu_cache_int_enabled']==s['cpu_cache_ext_enabled']==0
        assert s['cpu_isa_speed']==isa and s['timing_rr']==2
    for name in files:
        copy(run/name,tag+'/'+name)
    (out/tag/'initial-86box.cfg').write_bytes(initial_bytes)
    (out/tag/'initial-config-provenance.json').write_text(json.dumps(dict(
        status='RECONSTRUCTED_EXACT_BYTES_MATCH_PRE_RUN_HASH',
        source_profile=str(profile_path),source_profile_sha256=sha(profile_path),
        initial_config_sha256=m['initial_config_sha256'],
        note='86Box reordered the cpu_waitstates key when saving config on exit; final saved config is retained separately'),indent=2)+'\n',encoding='utf-8')
    for p in (run/'nvr-initial').iterdir():
        assert sha(p)==m['initial_nvr_sha256'][p.name]
        copy(p,tag+'/nvr/'+p.name)
    selected[tag]=dict(status='GUEST_AND_HOST_PASS',hz=hz,visible_wait_states=ws,
        config_value=ws+1,service_cycles=ws+2,cache_flags=[0,0],host_returncode=0,
        guest_returncode=0,sample_count=42,summary_count=6,timer_calibrated=False,
        summaries=val['summaries'],raw_csv_sha256=val['csv_sha256'])

earlier={}
for tag in ('native6-ws1','native6-ws2','native12-ws1','native12-ws2','native6-ws1-final'):
    run=build/tag
    m=json.loads((run/'measurement.json').read_text())
    for name in files:
        if (run/name).exists():
            copy(run/name,'earlier-controls/'+tag+'/'+name)
    earlier[tag]=dict(guest_raw_valid=m['guest_success'],host_returncode=m['emulator_returncode'],
        failure=m['failure'],selected=False,
        status='EARLIER_PASS' if m['guest_success'] and m['emulator_returncode']==0 else 'NOT_ACCEPTED_FULL_RUN')

copy(runner,'runner-used.py')
copy(validator,'validator-used.py')
copy(Path(__file__),'archive-script.py')
original=json.loads((root/'docs/evidence/p06-timing-reference-20261003/manifest.json').read_text())
sources={name:identity(root/name) for name in (
    'SW/CPUTIME/run_native_reference.py','SW/CPUTIME/README.md',
    'docs/optimization/P06_NATIVE_WAITSTATES_RESULTS_20261003.md',
    'docs/optimization/P06_NATIVE_REFERENCE_RESULTS_20261003.md')}
manifest=dict(status='FOUR_NATIVE_WAITSTATE_CONTROLS_GUEST_AND_HOST_PASS',
    selection_semantics='Visible 86Box N wait states: config N+1, effective service cycles N+2',
    automatic_reference_commit='936e7de',automatic_reference_manifest_sha256=sha(root/'docs/evidence/p06-timing-reference-20261003/manifest.json'),
    original_program=identity(program),runner=identity(runner),validator=identity(validator),
    native_executable_sha256='2d87185ff14842a20a2bd0fed1713820dd64eabaa049b08a9827b48948de4dd3',
    selected_controls=selected,earlier_controls=earlier,
    local_source_identity={'src/qt/qt_settingsmachine.cpp':identity(Path('D:/GitHub/86Box_dev/src/qt/qt_settingsmachine.cpp')),
                           'src/cpu/cpu.c':identity(Path('D:/GitHub/86Box_dev/src/cpu/cpu.c'))},
    current_sources=sources,
    limits=['NOT_CALIBRATED timer, assumed divisor/crystal', 'DOS runtime mode2 only',
            'no physical measurements', 'no historical cycle accuracy claim',
            'host heap failure cause not established; selected runs pause only after measurement'],
    raw_files={str(p.relative_to(out)).replace('\\','/'):identity(p) for p in sorted(out.rglob('*')) if p.is_file()})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':manifest['status'],'raw_files':len(manifest['raw_files']),
                  'controls':list(selected),'earlier_controls':earlier},indent=2))
