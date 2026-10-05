"""Run one source-bound native control from this archive into a fresh private output."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--disk',type=Path,required=True)
    p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--roms',type=Path,required=True)
    p.add_argument('--profile',choices=['6','8','10','12.5','16','20','25'],required=True)
    p.add_argument('--selection',choices=['auto','ws0'],required=True)
    a=p.parse_args()
    archive=Path(__file__).resolve().parent
    m=json.loads((archive/'manifest.json').read_text())
    for path,expected in [(a.disk,m['source_disk_sha256']),(a.exe,m['binary_sha256']),(archive/'T286REF.COM',m['program_sha256'])]:
        assert sha(path)==expected,('Reference input hash mismatch',str(path))
    frozen=json.loads((archive/'preflight.json').read_text())
    for name,entry in frozen['rom_files'].items():assert sha(a.roms/name)==entry['sha256']
    label=f'native{a.profile}-{a.selection}'
    control=m['selected_controls'][label]
    command=[sys.executable,str(archive/'run_native_reference_allprofiles.py'),
        '--output',str(a.output.resolve()),'--disk',str(a.disk.resolve()),
        '--exe',str(a.exe.resolve()),'--roms',str(a.roms.resolve()),
        '--profile',str(archive/label),'--program',str(archive/'T286REF.COM'),
        '--hz',str(control['hz']),'--seconds','300']
    if a.selection=='ws0':command+=['--memory-wait-states','0']
    raise SystemExit(subprocess.run(command).returncode)
