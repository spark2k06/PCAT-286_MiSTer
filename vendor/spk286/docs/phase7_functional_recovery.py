"""Verify a functional-delivery ZIP and restore into an absent workspace/build child."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

from phase7_closure_recovery import digest, safe_name


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON manifest key')
        result[key]=value
    return result


def restore(archive, expected, workspace, destination):
    workspace=workspace.resolve(strict=True)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination must be absent; recovery never overlays files')
    destination=destination.resolve()
    if destination==workspace/'build' or not destination.is_relative_to(workspace/'build'):
        raise ValueError('Destination must be an absent child of the selected workspace/build')
    with archive.open('rb') as stream:
        actual=digest(stream)
    if actual!=expected:
        raise ValueError('Archive SHA256 mismatch')
    with zipfile.ZipFile(archive) as package:
        entries=package.infolist();names=[]
        for entry in entries:
            safe_name(entry.filename);mode=entry.external_attr>>16
            if entry.is_dir() or stat.S_IFMT(mode) not in (0,stat.S_IFREG):
                raise ValueError('Only regular payload files are allowed')
            names.append(entry.filename)
        if len(names)!=len({name.casefold() for name in names}):
            raise ValueError('Duplicate or case-colliding archive paths')
        checksums={}
        for line in package.read('SHA256SUMS').decode().splitlines():
            checksum,name=line.split('  ',1);safe_name(name)
            if name in checksums or len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):
                raise ValueError('Invalid checksum inventory')
            checksums[name]=checksum
        if set(checksums)!=set(names)-{'SHA256SUMS'}:
            raise ValueError('Payload/checksum inventories differ')
        for name,checksum in checksums.items():
            with package.open(name) as stream:
                if digest(stream)!=checksum:raise ValueError('Changed payload: '+name)
        manifests={name:json.loads(package.read(name),object_pairs_hook=unique_object) for name in
                   ('source-manifest.json','executable-inputs.json','policy-inputs.json','file-modes.json')}
        sources=manifests['source-manifest.json'];modes=manifests['file-modes.json']
        if set(sources)!=set(modes):raise ValueError('Source/mode inventory differs')
        if {name for name in names if name.startswith('source/')}!={'source/'+name for name in sources}:
            raise ValueError('Source payload inventory differs from the source manifest')
        for name,checksum in sources.items():
            safe_name(name)
            if checksums.get('source/'+name)!=checksum:raise ValueError('Changed source manifest: '+name)
            if modes[name] not in (0o644,0o755):raise ValueError('Unsafe source mode')
        for kind in ('executable-inputs.json','policy-inputs.json'):
            for name,checksum in manifests[kind].items():
                if sources.get(name)!=checksum:raise ValueError('Changed '+kind+': '+name)
        for name in names:
            if not (destination/name).resolve().is_relative_to(destination):
                raise ValueError('Resolved destination escape')
        destination.mkdir(parents=True,exist_ok=False)
        for entry in entries:
            output=destination/entry.filename;output.parent.mkdir(parents=True,exist_ok=True)
            with package.open(entry.filename) as source,output.open('xb') as target:
                for block in iter(lambda:source.read(1024*1024),b''):target.write(block)
            mode=modes.get(entry.filename.removeprefix('source/'),
                           0o644|((entry.external_attr>>16)&0o111))
            output.chmod(mode)
    # On native POSIX storage this verifies actual mode retention. DrvFS without
    # metadata may report 0777 for every file; the Git mode manifest stays exact.
    mode_mismatches=[name for name,mode in modes.items()
                     if stat.S_IMODE((destination/'source'/name).stat().st_mode)!=mode]
    return dict(status='PASS',archive_sha256=actual,payloads=len(checksums),
                source_files=len(sources),executable_inputs=len(manifests['executable-inputs.json']),
                policy_inputs=len(manifests['policy-inputs.json']),destination=str(destination),
                actual_file_modes_match=not mode_mismatches,mode_mismatch_count=len(mode_mismatches),
                overlay_performed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--require-native-modes',action='store_true')
    args=parser.parse_args();result=restore(args.archive,args.sha256,args.workspace,args.destination)
    if args.require_native_modes and not result['actual_file_modes_match']:
        raise ValueError('Filesystem did not retain the recorded source modes')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
