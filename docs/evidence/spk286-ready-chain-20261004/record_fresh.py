"""Archive the frozen standalone extra gates, independently of shared acceptance."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile

DEST = Path(__file__).resolve().parent
ROOT = DEST.parents[2]
RUN = ROOT/'build/spk286-ready-chain-standalone-gates-20261004-v1'
PLAN = ROOT/'build/spk286-ready-chain-port-plan-20261004'
PROBES = ROOT/'build/spk286-ready-chain-port-probes-20261004-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def main():
    manifest = json.loads((RUN/'manifest.json').read_text())
    fresh = json.loads((RUN/'receipt.json').read_text())
    native = json.loads((RUN/'smoke-state-receipt.json').read_text())
    assert fresh['status']=='STANDALONE_DISTINCT_GATES_PASS'
    assert native['status']=='STANDALONE_NATIVE_SMOKE_STATE_PASS'
    for group in (fresh,native):
        assert group['sources_unchanged_after_run'] and group['manifest_sha256']==sha(RUN/'manifest.json')
        for row in group['results'].values():
            assert row['status']=='PASS' and row['exit_code']==0
            assert sha(RUN/row['log'])==row['log_sha256']
    files=[]
    for rel in ('manifest.json','receipt.json','smoke-state-receipt.json','regression-scope-audit.json',
                'external-post-gates-check.json','run_gates.py','run_smoke_state.py','compose_receipt.py','FINAL_REPORT.md'):
        files.append(('fresh/'+rel,RUN/rel))
    # Preliminary composition remains historical; final shared acceptance is
    # archived separately only after the actual v3 pass and independent review.
    files.append(('preliminary/composed-receipt.json',RUN/'composed-receipt.json'))
    for path in sorted((RUN/'logs').glob('*.log')):
        files.append(('fresh/logs/'+path.name,path))
    profile=RUN/'snapshot/build/profile-focused'
    for path in sorted(profile.glob('*.log')):
        files.append(('profile/'+path.name,path))
    files.append(('profile/receipt.json',profile/'receipt.json'))
    for dirname in ('generated','repeated','metadata'):
        for path in sorted((profile/dirname).rglob('*')):
            if path.is_file() and path.suffix in ('.sv','.json','.log') and not any('verilator' in p for p in path.relative_to(profile).parts):
                files.append(('profile/'+path.relative_to(profile).as_posix(),path))
    for path in sorted((RUN/'snapshot/build/native-driver/state-vectors').rglob('*')):
        if path.is_file():files.append(('native-state/'+path.relative_to(RUN/'snapshot/build/native-driver/state-vectors').as_posix(),path))
    for path in sorted((RUN/'snapshot/build/native-microcode-audit').rglob('*')):
        if path.is_file():files.append(('native-microcode-audit/'+path.relative_to(RUN/'snapshot/build/native-microcode-audit').as_posix(),path))
    for path in sorted((RUN/'snapshot/build').rglob('*.txt')):
        parts=path.relative_to(RUN/'snapshot/build').parts
        if path.is_file() and not any(part in ('verilator','iverilog','prefix-verilator','obj_dir') for part in parts) and parts[0]!='native-driver':
            files.append(('fresh-vectors/'+path.relative_to(RUN/'snapshot/build').as_posix(),path))
    for rel in ('stage-manifest.json','functional-closure-bridge.json','header-declarations-bridge.json','apply-receipt.json','prepare_plan.py','PLAN.md'):
        files.append(('proposal/'+rel,PLAN/rel))
    for path in sorted(PLAN.glob('*.patch')):files.append(('proposal/'+path.name,path))
    for rel in ('manifest.json','receipt.json','focused-summary.json','evidence-manifest.json','run_probes.py'):
        files.append(('focused/'+rel,PROBES/rel))
    pr=json.loads((PROBES/'receipt.json').read_text())
    for row in pr['results'].values():files.append(('focused/'+row['log'],PROBES/row['log']))
    for rel in ('build/spk286-ready-chain-sentinel-independent-review-20261004.json',
                'build/spk286-ready-chain-sentinel-independent-review-20261004.py'):
        path=ROOT/rel
        if path.is_file():files.append(('review/'+path.name,path))
    rows=[]
    for logical,path in files:
        data=path.read_bytes()
        target=DEST/'raw'/(logical+'.gz')
        target.parent.mkdir(parents=True,exist_ok=True)
        packed=gzip.compress(data,compresslevel=9,mtime=0)
        target.write_bytes(packed)
        assert gzip.decompress(target.read_bytes())==data
        rows.append({'path':logical,'stored_path':target.relative_to(DEST).as_posix(),
                     'source_path':path.relative_to(ROOT).as_posix(),'sha256':digest(data),
                     'stored_sha256':digest(packed),'bytes':len(data)})
    # Complete tracked/source inventory only; simulator objects and executable
    # binaries are intentionally excluded from this reproducible source bundle.
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as archive:
        for rel,expected in sorted(manifest['source_sha256'].items()):
            data=(RUN/'snapshot'/rel).read_bytes()
            assert digest(data)==expected,rel
            info=tarfile.TarInfo(rel)
            info.size=len(data);info.mode=0o644;info.mtime=0
            archive.addfile(info,io.BytesIO(data))
    data=gzip.compress(buffer.getvalue(),compresslevel=9,mtime=0)
    (DEST/'standalone-source.tar.gz').write_bytes(data)
    with tarfile.open(DEST/'standalone-source.tar.gz','r:gz') as archive:
        observed={item.name:digest(archive.extractfile(item).read()) for item in archive.getmembers() if item.isfile()}
    assert observed==manifest['source_sha256']
    output={'status':'STANDALONE_FRESH_GATES_ARCHIVED_SHARED_ACCEPTANCE_SEPARATE',
            'artifact_count':len(rows),'source_count':len(observed),'artifacts':rows,
            'source_sha256':observed,'source_bundle_sha256':sha(DEST/'standalone-source.tar.gz'),
            'record_fresh_sha256':sha(Path(__file__)),
            'scope':'33 fresh standalone stages plus four first focused sentinel runs, exact source inventory and profile/state artifacts. Preliminary shared composition is not acceptance; final vendor pass and review must be bound separately.'}
    (DEST/'fresh-archive-manifest.json').write_text(json.dumps(output,indent=2)+'\n',newline='\n')
    print(output['status'])
    print('Artifacts',len(rows),'sources',len(observed))
    print('fresh-archive-manifest SHA256',sha(DEST/'fresh-archive-manifest.json'))


if __name__=='__main__':main()
