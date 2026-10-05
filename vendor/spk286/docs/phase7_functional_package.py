"""Build the final recovery package from committed sources and verified results."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.phase7_validation_receipt import verify


def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--delivery-receipt',type=Path,required=True)
    args=parser.parse_args()
    assert not args.archive.exists(), 'Archive must be new'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT), 'Commit delivery first'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
    build=ROOT/'build/phase7-functional-full-1'
    result=verify(build/'execution-receipt.json')
    receipt=json.loads((build/'execution-receipt.json').read_text())
    delivery=json.loads(args.delivery_receipt.read_text())
    assert delivery['delivery_commit']==commit, 'Delivery receipt must name HEAD'
    payload={};modes={};source_manifest={}
    def add(name,value,mode=0o644):
        assert name not in payload and name.casefold() not in {n.casefold() for n in payload}
        payload[name]=(value,mode)
    # Read Git blobs directly.  `git archive` applies checkout attributes and
    # can transform an unlisted text extension (for example `.asm`) to CRLF,
    # which would no longer match the executed input manifest.
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0')
    for raw_name in tracked:
        if not raw_name:continue
        name=raw_name.decode()
        data=subprocess.check_output(['git','cat-file','blob','HEAD:'+name],cwd=ROOT)
        tree_line=subprocess.check_output(['git','ls-tree','HEAD','--',name],cwd=ROOT,text=True)
        mode=int(tree_line.split(None,1)[0],8)
        mode=0o755 if mode&0o111 else 0o644
        add('source/'+name,data,mode)
        source_manifest[name]=hashlib.sha256(data).hexdigest();modes[name]=mode
    for kind,source_name in (('executable-inputs.json','inputs.json'),('policy-inputs.json','policy-inputs.json')):
        inputs=json.loads((build/source_name).read_text())
        assert all(source_manifest.get(name)==digest for name,digest in inputs.items()), 'Canonical Git input mismatch'
        add(kind,(build/source_name).read_bytes())
    add('source-manifest.json',encoded(source_manifest));add('file-modes.json',encoded(modes))
    for name in sorted(set(receipt['artifacts'])|{'execution-receipt.json'}):
        path=build/name
        executable=path.name=='spk286_smoke' or (not path.suffix and path.name.endswith('_tb'))
        add('evidence/phase7-functional-full-1/'+name,path.read_bytes(),0o755 if executable else 0o644)
    # Supporting experiments and rejected attempts retain separate provenance.
    for directory in ('phase7-functional-freeze-20260909','phase7-functional-review-20260909',
                      'phase7-functional-emulator-2','phase7-functional-synthetic-1','phase7-functional-synthetic-2'):
        base=ROOT/'build'/directory
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:continue
            if path.suffix not in {'.json','.md','.log','.py','.sv','.svh','.vvp','.c','.bin','.txt','.zip'} and path.name!='86Box-COPYING':continue
            add('evidence/'+directory+'/'+path.relative_to(base).as_posix(),path.read_bytes())
    for path in sorted((ROOT/'build').glob('phase7-functional-*')):
        if path.is_file() and path.suffix in {'.log','.exit','.json'}:
            add('evidence/session/'+path.name,path.read_bytes())
    for name in ('collect_phase7_functional_facts.py','finalize_phase7_functional_docs.py',
                 'check_phase7_functional_recovery.py','freeze_phase7_functional.py',
                 'integrate_phase7_functional.py','PHASE7_FUNCTIONAL_CLOSURE.template.md',
                 'PHASE7_FUNCTIONAL_RECOVERY.draft.md','check_phase7_strict_evidence.py',
                 'record_phase7_launcher_incident.py','run_phase7_finalization.py'):
        path=ROOT/'build'/name
        add('evidence/preparation/'+name,path.read_bytes())
    add('evidence/delivery-receipt.json',args.delivery_receipt.read_bytes())
    for path in sorted((ROOT/'.cache/phase7-86box-3a8953d0').rglob('*')):
        if path.is_file():add('references/86Box/'+path.relative_to(ROOT/'.cache/phase7-86box-3a8953d0').as_posix(),path.read_bytes())
    corpus=ROOT/'.cache/phase7-clean-corpus-307'
    for path in sorted(corpus.rglob('*')):
        if not path.is_file() or '.git' in path.relative_to(corpus).parts:continue
        if path.name in {'E7.MOO.gz','revocation_list.txt'} or path.suffix in {'.py','.json','.md'} or path.name.startswith('LICENSE'):
            add('references/SingleStepTests-80286/'+path.relative_to(corpus).as_posix(),path.read_bytes())
    add('package-provenance.json',encoded(dict(schema_version=1,base_commit='e2bc4a7839cd0aa594b543d8dcaaf253c310a63a',
        implementation_commit=commit,delivery_commit=commit,git_tree=tree,
        execution_manifest_sha256=result['execution_manifest_sha256'],policy_manifest_sha256=result['policy_manifest_sha256'],
        prior_archive_sha256='83b339bc38437255091b2e486a9d481c21d3d36091c40e265cb3797b7e705c8c',
        complete_corpus_included=False,corpus_revision='37c73caf53dcd22d3dd369ff09305d13d117a4fe')))
    sums={name:hashlib.sha256(data).hexdigest() for name,(data,_) in sorted(payload.items())}
    add('SHA256SUMS',''.join(digest+'  '+name+'\n' for name,digest in sums.items()).encode())
    args.archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as output:
        for name,(data,mode) in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,9,9,0,0,0));info.create_system=3
            info.external_attr=(stat.S_IFREG|mode)<<16;info.compress_type=zipfile.ZIP_DEFLATED
            output.writestr(info,data)
    with args.archive.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    args.archive.with_suffix(args.archive.suffix+'.sha256').write_text(digest+'  '+args.archive.name+'\n')
    report=dict(status='PASS',archive=str(args.archive),archive_sha256=digest,archive_bytes=args.archive.stat().st_size,
                payloads=len(sums),source_files=len(source_manifest),git_tree=tree,delivery_commit=commit,
                manifests={name:hashlib.sha256(payload[name][0]).hexdigest() for name in
                           ('source-manifest.json','executable-inputs.json','policy-inputs.json','file-modes.json')})
    (ROOT/'build/phase7-functional-package.json').write_bytes(encoded(report))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
