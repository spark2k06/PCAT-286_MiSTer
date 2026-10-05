from pathlib import Path
import hashlib,json,subprocess,sys,time
from validate_t286ref import validate_csv

root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
runner=out/'run_native_reference_allprofiles.py'
program=root/'docs/evidence/p06-timing-reference-20261003/T286REF.COM'
disk=Path('/mnt/d/ISOs/MiSTer/286_win3.1.vhd')
exe=root/'build/p06-timing-reference-20261003/native6-final/86Box-native'
roms=Path('/mnt/d/Desktop/86Box/roms')
profiles=root/'docs/evidence/p06-physical-reference-20261004/native'
expected_service={6000000:2,8000000:2,10000000:2,12500000:3,16000000:3,20000000:4,25000000:4}
reports=[]

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def verify(target,previous=False):
    m=json.loads((target/'measurement.json').read_text())
    assert m['completed'] and m['guest_success'] and m['failure'] is None and m['emulator_returncode']==0,(target,m['failure'],m['emulator_returncode'])
    hz=m['hz']; visible=m.get('requested_visible_wait_states')
    config=0 if visible is None else visible+1
    assert m['cpu_waitstates_config']==config
    assert m['program_sha256']==sha(program)
    assert m['binary_sha256']==sha(exe)
    assert m['source_disk_sha256']==m['source_disk_sha256_after']==sha(disk)
    if not previous:
        assert m['runner_sha256']==sha(runner)
        assert not Path(f"/proc/{m['pid']}").exists(),'Owned emulator process remains after runner exit'
    assert m['samples']
    for s in m['samples']:
        assert s['dispatcher']==0x4a75b0 and s['cpu_hz_actual']==hz
        assert s['cpu_waitstates']==config
        service=expected_service[hz] if visible is None else visible+2
        assert s['cpu_prefetch_cycles']==s['cpu_cycles_read']==s['cpu_cycles_write']==service
        assert s['cpu_cache_int_enabled']==s['cpu_cache_ext_enabled']==0
        assert s['timing_rr']==2
    text=(target/'REF.CSV').read_bytes().decode('cp437')
    v=validate_csv(text,m['cpu_label'])
    assert v==m['csv_validation']
    assert v['sample_count']==42 and v['summary_count']==6 and not v['timer_calibrated']
    assert all(v['controls'].values())
    assert m['guest_output']['STATUS.TXT']=='BEGIN\r\nRC0\r\nALL_DONE\r\n'
    report={'label':target.name,'hz':hz,'cpu_label':m['cpu_label'],'visible_wait_states':visible,
        'config':config,'service':service,'cache_flags':[0,0], 'guest_rc':0,'host_rc':0,
        'runtime_samples':m['samples'], 'csv_sha256':v['csv_sha256'],
        'summaries':v['summaries'],'metadata':v['metadata'],
        'program_sha256':m['program_sha256'],'binary_sha256':m['binary_sha256'],
        'runner_sha256':m['runner_sha256'],'validator_sha256':m['validator_sha256'],
        'source_disk_sha256':m['source_disk_sha256'],
        'initial_config_sha256':m['initial_config_sha256'],
        'initial_nvr_sha256':m['initial_nvr_sha256'],
        'host_elapsed_seconds':m['host_elapsed_seconds'],'keyboard_events':m['keyboard_events'],
        'source_directory':str(target),'reused_archive':previous,
        'process_alive_after_runner':False if not previous else 'PRIOR_RECEIPT',
        'artifacts':{name:sha(target/name) for name in ['measurement.json','REF.CSV','STATUS.TXT','samples.json','start.json','86box.cfg','86box.log','console.log','initial-86box.cfg']}}
    print('PASS',target.name, 'service',service, 'ISA',m['samples'][-1]['cpu_isa_speed'],json.dumps(v['summaries']),flush=True)
    return report

subprocess.run([sys.executable,str(out/'preflight.py')],check=True)
reports.append(verify(out/'native8-auto-observed'))
for hz,label in [(6000000,'6'),(8000000,'8'),(10000000,'10'),(12500000,'12.5'),(16000000,'16'),(20000000,'20'),(25000000,'25')]:
    for selection in ['auto','ws0']:
        if label=='8' and selection=='auto':continue
        if label in ('6','12.5') and selection=='ws0':
            reports.append(verify(profiles/('native6-ws0' if label=='6' else 'native12-ws0'),previous=True))
            continue
        target=out/f'native{label}-{selection}'
        profile=profiles/('native6-ws0' if hz<=10000000 else 'native12-ws0')
        command=[sys.executable,str(runner),'--output',str(target),'--disk',str(disk),'--profile',str(profile),'--program',str(program),'--exe',str(exe),'--roms',str(roms),'--hz',str(hz),'--seconds','150']
        if selection=='ws0':command+=['--memory-wait-states','0']
        print('RUN',target.name,flush=True)
        with (out/(target.name+'-run.log')).open('w') as log:
            result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        if result.returncode:
            print('FAIL',target.name, 'runner_rc',result.returncode,(out/(target.name+'-run.log')).read_text(),flush=True)
            (out/'progress.json').write_text(json.dumps({'status':'INCOMPLETE_CONTROL_FAILED','runs':reports,'failed':target.name},indent=2)+'\n')
            raise SystemExit(1)
        reports.append(verify(target))
        (out/'progress.json').write_text(json.dumps({'status':'NATIVE_CONTROLS_IN_PROGRESS','runs':reports},indent=2)+'\n')
assert len(reports)==14
(out/'verification.json').write_text(json.dumps({'status':'ALL_SEVEN_NATIVE_PROFILES_AUTO_AND_VISIBLE_ZERO_GUEST_AND_HOST_PASS','sample_count':588,'summary_count':84,'runs':reports},indent=2)+'\n')
print('ALL_PROFILES_PASS no owned processes remaining',flush=True)
