"""Package only normal diagnostics, documentation and measured transcripts."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from research.pm_diag.build import ROOT, SOURCE


def package(directory, destination):
    manifest = json.loads((directory/'manifest.json').read_text())
    if manifest['injected_fault'] != 0:
        raise ValueError('Refusing to package an injected-fault build')
    for name, details in manifest['files'].items():
        data = (directory/name).read_bytes()
        if len(data) != details['bytes'] or hashlib.sha256(data).hexdigest() != details['sha256']:
            raise ValueError(f'Stale/mismatched binary: {name}')
    for name, digest in manifest['sources'].items():
        if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Stale source: {name}')
    files = {name: (directory/name).read_bytes() for name in manifest['files']}
    files['manifest.json'] = (directory/'manifest.json').read_bytes()
    for name in ('README.md', 'VALIDATION.md', 'RESULT_TEMPLATE.md'):
        files[name] = (SOURCE/name).read_bytes()
    evidence = ROOT/'build/pm-diag-validation'
    for case, log in [('bochs-control', 'console.log'), ('bochs-rom', 'console.log'),
                      ('bochs-relocated', 'console.log'), ('bochs-negative-data', 'console.log'),
                      ('bochs-negative-cs', 'console.log'), ('qemu-control', 'debug.log')]:
        result = json.loads((evidence/case/'result.json').read_text())
        text = (evidence/case/log).read_text(errors='replace')
        if case in ('bochs-control', 'bochs-rom', 'bochs-relocated'):
            if not result['complete'] or 'COMPLETE failures=0000' not in text or text.count(' PASS ') != 17:
                raise ValueError(f'Missing all-pass evidence: {case}')
        if case in ('bochs-control', 'bochs-rom'):
            name = 'PM286.IMG' if case=='bochs-control' else 'PMROM.IMG'
            if result['image_sha256'] != manifest['files'][name]['sha256']:
                raise ValueError(f'Evidence does not match distribution: {case}')
        if case=='bochs-negative-data' and 'FAIL FFFF/0000' not in text:
            raise ValueError('Missing expected negative-data failure')
        if case=='bochs-negative-cs' and 'EXCEPTION vector=000B error=0004' not in text:
            raise ValueError('Missing expected absent-CS exception')
        files[f'evidence/{case}.log'] = text.encode('utf-8')
        files[f'evidence/{case}.json'] = (evidence/case/'result.json').read_bytes()
    for name in ('control.log', 'com.log', 'rom-boot.log', 'control1379.log', 'control1378.log'):
        files[f'evidence/spk286-{name}'] = (evidence/'rtl'/name).read_bytes()
    files['evidence/qemu-control-screen.png'] = (evidence/'qemu-control/screen.png').read_bytes()
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP integrity failure')
    print(f'PACKAGE_PASS {destination} files={len(files)} bytes={destination.stat().st_size}')
    print('SHA256 '+hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'build/pm-diag')
    parser.add_argument('--output', type=Path, default=ROOT/'build/PM286_DIAG_v0.1.zip')
    args = parser.parse_args()
    package(args.directory, args.output)
