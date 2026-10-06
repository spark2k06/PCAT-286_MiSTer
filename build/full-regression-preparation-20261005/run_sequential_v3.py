#!/usr/bin/env python3
"""Source-bound functional regression of the identified timing-open RBF.

Run only in WSL, on a fresh D: owned directory. Preparation freezes inputs and
records tool identities; execution is explicit and sequential. No RTL generator
or source repair is invoked. Missing inputs remain failures of completeness.
The user explicitly requested the complete regression of this candidate despite
its one known -0.063 ns cold HDMI setup path. This does not sign off timing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
IGNORED = {'.git', '.cache', '__pycache__', 'build', 'db', 'incremental_db', 'obj_dir'}
SOURCE_DIRS = ('rtl', 'sys', 'vendor', 'scripts', 'sim', 'SW', 'tests', 'tools')
SUFFIXES = {'.sv', '.v', '.vh', '.vhd', '.qsf', '.qpf', '.qip', '.sdc', '.tcl', '.mif', '.mem', '.hex'}
COMPILER_SUFFIXES = {'.cpp', '.cc', '.c', '.h', '.hpp', '.o', '.a', '.so', '.d', '.mk', '.gch', '.pch', '.vvp'}
PRIVATE_SUFFIXES = {'.rom', '.bin', '.mif', '.mem', '.hex'}
SUPPORT_INPUTS = (
    'docs/evidence/p06-core-register-20261004/observation/receipt.json',
    'docs/evidence/stack-offset-arithmetic-20261002/upstream-formal',
    'docs/evidence/stack-offset-arithmetic-20261002/compiled-cycle-sources.sha256',
    'docs/evidence/sync-microcode-20261001/actual-depth-formal/receipt.json',
    'docs/evidence/sync-microcode-20261001/compiled-sources.sha256',
    'docs/evidence/rtc-bcd-lookup-20261002/proof.json',
)
REFERENCE_PINS = {
    'MRBIOS': '6f936ee53ba58663d1ccc7b80b1f5caba841f3f816c4dca15477ca540f9f252f',
    'LANDMARK_ORIGINAL': 'a8310f83de0f3e6b71e4a3ff82a01ffe3c3b5a957677aed2fad17b96bce2e577',
    'LANDMARK_SKIP_PM_V2': '46e99247c58766b162413e34480b63490aa8f610702d8aa1e98e15b2d921dec6',
    'PHOENIX': '306ac7c3a0ee713385de53f5dd0625ee040f3ea6606b09e9d5fce3c6a00b273e',
}
TIMING_PACKET_PIN = 'd4ab93d1552ee57a9a524da6505ed9fbd49af4a8357ab05603052b2647490b3d'
RBF_PIN = 'd83a6d9494f69e68d9236bf7555c05f2fa344c3f1ab46208c8225a727fef40de'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def require(ok, note):
    if not ok:
        raise ValueError(note)


def inventory(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and not IGNORED.intersection(p.relative_to(folder).parts)}


def metadata(path, ignored=frozenset()):
    """Cheap change detector between complete SHA-256 source checkpoints."""
    path = Path(path)
    def attrs(p):
        stat = p.stat()
        return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_mode
    if path.is_file():
        return {'file': attrs(path)}
    items = {}
    for directory, names, files in os.walk(path, topdown=True, followlinks=False):
        names[:] = sorted(name for name in names if name not in ignored)
        for name in sorted(files):
            p = Path(directory) / name
            if p.is_file():
                items[p.relative_to(path).as_posix()] = attrs(p)
    return items


def owned(path, top):
    path = Path(path)
    require(path.resolve().is_relative_to(top.resolve()) and path.resolve() != top.resolve(), 'Unsafe owned path')
    require(not any(p.is_symlink() for p in [path, *path.parents] if p != top.parent), 'Symlink ancestor in owned path')
    return path


def disk():
    return {name: shutil.disk_usage('/mnt/' + name.lower()).free for name in ('C', 'D')}


def floor():
    free = disk()
    require(free['C'] >= 10 * 2**30 and free['D'] >= 20 * 2**30,
            'Resource floor reached; no next compile allocation: ' + repr(free))
    return free


def check_timing(packet, fitted):
    pm, result = read(packet / 'manifest.json'), read(packet / 'result.json')
    require(sha(packet / pm['archive']) == pm['sha256'] == TIMING_PACKET_PIN,
            'Timing archive identity differs from the user-selected candidate')
    require(result['status'] == 'TIMING_OPEN_CHECK_REPORTED_MARGINS' and
            result['full_regression'] == 'USER_PAUSE_AFTER_CURRENT_FIT_NOT_RUN' and
            result['rbf']['sha256'] == RBF_PIN,
            'This coordinator is restricted to the explicitly resumed timing-open candidate')
    with tarfile.open(packet / pm['archive']) as t:
        require(len(t.getnames()) == len(set(t.getnames())) and
                set(t.getnames()) == set(pm['members_sha256']), 'Timing packet membership differs')
        for entry in t:
            require(entry.isfile(), 'Non-file member in timing packet')
            raw = t.extractfile(entry).read(); expected = pm['members_sha256'][entry.name]
            require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'],
                    'Timing packet member changed: ' + entry.name)
        require(t.extractfile('result.json').read() == (packet / 'result.json').read_bytes(), 'Timing result not sealed')
        summary = json.loads(t.extractfile('fit/summary.json').read())
        require(len(summary['corners']) == 4 and all(v['hold']['global']['tool_worst_slack_ns'] > 0
                for v in summary['corners'].values()), 'Hold not positive in all four corners')
        require({c: v['setup']['global']['tool_worst_slack_ns'] for c, v in summary['corners'].items()} ==
                {'7_slow_1100mv_100c': 0.072, '7_slow_1100mv_-40c': -0.063,
                 'MIN_fast_1100mv_100c': 2.273, 'MIN_fast_1100mv_-40c': 2.583},
                'Unexpected global setup profile')
        require(all(v['setup'][g]['tool_worst_slack_ns'] > 0 and
                    v['hold'][g]['tool_worst_slack_ns'] > 0
                    for v in summary['corners'].values()
                    for g in ('cpu', 'clk50_internal', 'clk50_incoming', 'cpu_bridge',
                              'bridge_cpu', 'memory_port', 'code_buffer', 'data_buffer',
                              'data_buffer_outputs', 'sdram_owner')),
                'CPU/bridge/SDRAM 50 MHz timing changed')
        original = json.loads(t.extractfile('original-sdc/summary.json').read())
        require(len(original['corners']) == 4 and all(
                original['corners'][c][k]['global']['tool_worst_slack_ns'] == v[k]['global']['tool_worst_slack_ns']
                for c, v in summary['corners'].items() for k in ('setup', 'hold')),
                'Original SDC changes the declared HDMI exception or hold')
        after = json.loads(t.extractfile('input-bindings.after.json').read())
        for n, h in after['sources_sha256'].items():
            require(pm['members_sha256']['effective-source/' + n]['sha256'] == h,
                    'Fitted source bytes are not preserved: ' + n)
        rbf = ROOT / result['rbf']['path']
        require(rbf.resolve().is_relative_to(fitted.resolve()) and rbf.is_file() and
                sha(rbf) == result['rbf']['sha256'], 'Accepted RBF identity differs')
    return pm, after


def seal(destination, files):
    """Read back every member before authorizing any object cleanup."""
    require(not destination.exists(), 'Immutable archive already exists')
    manifest = {n: {'sha256': sha(p), 'bytes': p.stat().st_size} for n, p in files.items()}
    with tarfile.open(destination, 'w:gz', compresslevel=6) as tar:
        for n, p in sorted(files.items()):
            raw = p.read_bytes(); require(hashlib.sha256(raw).hexdigest() == manifest[n]['sha256'], 'Archive input drift')
            info = tarfile.TarInfo(n); info.size = len(raw); info.mode = 0o644; info.mtime = 0
            tar.addfile(info, io.BytesIO(raw))
    with tarfile.open(destination) as tar:
        require(set(tar.getnames()) == set(files), 'Archive membership differs')
        for item in tar:
            raw = tar.extractfile(item).read()
            require(len(raw) == manifest[item.name]['bytes'] and hashlib.sha256(raw).hexdigest() == manifest[item.name]['sha256'],
                    'Archive readback differs')
    return {'archive': destination.name, 'sha256': sha(destination), 'bytes': destination.stat().st_size, 'members': manifest}


def reference_inventory(path):
    return {'file': sha(path)} if path.is_file() else {p.relative_to(path).as_posix(): sha(p)
        for p in sorted(path.rglob('*')) if p.is_file() and '.git' not in p.relative_to(path).parts}


def wrappers(out, tools):
    out.mkdir()
    for name in ('verilator', 'docker'):
        if name not in tools:
            continue
        real = tools[name]['path']
        body = """#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:];actual=list(args)
if NAME=='verilator':
    actual=[];i=0
    while i<len(args):
        arg=args[i]
        if arg in ('--build-jobs','-j'):
            actual.extend([arg,'1']);i+=2
        elif arg.startswith('--build-jobs=') or arg.startswith('-j') and arg[2:].isdigit():
            actual.append('--build-jobs=1');i+=1
        else:actual.append(arg);i+=1
elif NAME=='docker' and args and args[0]=='run':
    if any(a.startswith('--pull=') and a!='--pull=never' for a in args):
        raise SystemExit('Only existing Docker images may be used')
    actual=['run','--pull=never','--label','pcat-regression-run='+os.environ['REGRESSION_RUN_LABEL'],*args[1:]]
with open(os.environ['REGRESSION_TOOL_LOG'],'a') as f:
    f.write(json.dumps({'tool':NAME,'real':REAL,'requested':args,'actual':actual})+'\\n')
os.execv(REAL,[REAL,*actual])
""".replace('NAME', repr(name)).replace('REAL', repr(real))
        p = out / name; p.write_text(body); p.chmod(0o755)


def prepare(args):
    require(os.name == 'posix' and str(args.output.resolve()).startswith('/mnt/d/'), 'Use WSL D: storage')
    require(args.output.resolve().is_relative_to(ROOT / 'build') and not args.output.exists(), 'Fresh owned run required')
    floor()
    packet, fitted = args.timing_packet.resolve(), args.fitted_run.resolve()
    tm, after = check_timing(packet, fitted)
    registry = read(args.stage_manifest)
    for name, h in registry['input_registry_sha256'].items():
        require(sha(ROOT / name) == h, 'Registry/helper changed: refresh the versioned manifest before execution: ' + name)
    top = args.output.resolve(); top.mkdir(); work = top / 'work'; work.mkdir()
    for name in SOURCE_DIRS:
        shutil.copytree(ROOT / name, work / name, ignore=shutil.ignore_patterns(*IGNORED))
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix.lower() in SUFFIXES:
            shutil.copy2(p, work / p.name)
    support_inputs = {n: {'path': str(ROOT / n), 'sha256': reference_inventory(ROOT / n)}
                      for n in SUPPORT_INPUTS if (ROOT / n).exists()}
    if args.support_inputs:
        support_inputs.update(read(args.support_inputs))
    for name, spec in support_inputs.items():
        target = owned(work / name, top); src = Path(spec['path']).resolve()
        require(reference_inventory(src) == spec['sha256'], 'Archived support input changed: ' + name)
        require(name.startswith('docs/evidence/'), 'Support copy must be an explicitly named evidence input')
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir(): shutil.copytree(src, target)
        else: shutil.copy2(src, target)
    require((work / SUPPORT_INPUTS[0]).is_file() and (work / SUPPORT_INPUTS[1]).is_dir(),
            'Original profile or stack reference absent')
    # All fitted HDL, includes, data images and settings use the exact accepted bytes.
    # Current test/tool/doc differences are named explicitly, never called fitted RTL.
    fitted_delta = {}; approvals = read(args.tool_overlay_approval) if args.tool_overlay_approval else {}
    with tarfile.open(packet / tm['archive']) as frozen:
        for n, h in after['sources_sha256'].items():
            p = owned(work / n, top)
            if p.is_file() and sha(p) == h: continue
            if n in ('build_id.v', 'PCAT-286.qsf'):
                # These exact post-preflow bytes belong to the fitted candidate.
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(frozen.extractfile('effective-source/' + n).read())
                continue
            require(p.is_file() and n in approvals, 'Unapproved current/fitted input difference: ' + n)
            require(Path(n).suffix.lower() not in SUFFIXES, 'Never overlay fitted HDL/settings: ' + n)
            actual = {'fitted': h, 'regression_tool_or_document': sha(p)}
            require(approvals[n] == actual, 'Named nonfitted transition identity differs: ' + n)
            fitted_delta[n] = actual
    require(set(approvals) == set(fitted_delta), 'Unused or omitted tool overlay approval')
    inputs = inventory(work)
    actual_fitted = {n: sha(work / n) for n in after['sources_sha256'] if Path(n).suffix.lower() in SUFFIXES}
    require(all(h == after['sources_sha256'][n] for n, h in actual_fitted.items()), 'Fitted RTL mismatch')
    references = {'CORPUS': args.corpus.resolve(), 'MCL86': args.corpus.resolve().parent / 'mcl86',
        'MRBIOS': ROOT / 'build/mrbios_1.65_286.bin',
        'LANDMARK_ORIGINAL': ROOT / 'SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_64K.BIN',
        'LANDMARK_SKIP_PM': ROOT / 'SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_64K.BIN',
        'LANDMARK_SKIP_PM_V2': ROOT / 'SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_V2_64K.BIN',
        'PHOENIX': ROOT / 'SW/ROMs/test/Phoenix_AT_Clone_A286_v1.01_64K.ROM'}
    supplied = read(args.references) if args.references else {}
    if supplied:
        for name, item in supplied.items():
            p = Path(item['path']).resolve()
            require(p.exists() and reference_inventory(p) == item['sha256'], 'External reference identity differs: ' + name)
            require(not p.is_relative_to(work) and p != ROOT, 'Candidate cannot be the independent reference')
            references[name] = p
    for name, expected in REFERENCE_PINS.items():
        if references[name].exists(): require(sha(references[name]) == expected, 'Wrong exact firmware: ' + name)
    require(not references['LANDMARK_SKIP_PM'].exists() or 'LANDMARK_SKIP_PM' in supplied,
            'Old SKIP_PM needs independent historical recovery/pin in references JSON; do not infer it from V2')
    external = {n: {'path': str(p), 'status': 'PRESENT' if p.exists() else 'UNAVAILABLE',
                    'sha256': reference_inventory(p) if p.exists() else {}} for n, p in references.items()}
    require(external['CORPUS']['status'] == 'PRESENT', 'Physical corpus absent')
    tools = {}
    versions = {'python3': ['--version'], 'verilator': ['--version'], 'iverilog': ['-V'], 'vvp': ['-V'],
                'yosys': ['-V'], 'ghdl': ['--version'], 'g++': ['--version'], 'make': ['--version'],
                'nasm': ['-v'], 'git': ['--version'], 'timeout': ['--version'], 'docker': ['--version']}
    for name, flags in versions.items():
        p = shutil.which(name)
        if p:
            r = subprocess.run([p, *flags], capture_output=True, text=True)
            tools[name] = {'path': p, 'sha256': sha(Path(p).resolve()), 'exit_status': r.returncode, 'version': r.stdout + r.stderr}
        else: tools[name] = {'unavailable': True}
    if 'path' in tools['verilator']:
        p = Path(tools['verilator']['path']).with_name('verilator_bin')
        if p.exists(): tools['verilator_bin'] = {'path': str(p), 'sha256': sha(p.resolve())}
    images = {}
    if 'path' in tools['docker']:
        tag = 'ghdl/ghdl:ubuntu22-llvm-11'
        r = subprocess.run([tools['docker']['path'], 'image', 'inspect', '--format={{.Id}}', tag],
                           capture_output=True, text=True)
        images[tag] = {'status': 'PRESENT' if r.returncode == 0 else 'UNAVAILABLE',
                       'id': r.stdout.strip(), 'diagnostic': r.stderr}
    wrappers(top / 'tool-wrappers', {k: v for k, v in tools.items() if 'path' in v})
    git = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           'status_porcelain': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines()}
    source = {'status': 'FROZEN_TIMING_OPEN_USER_REQUESTED_REGRESSION_NOT_EXECUTED',
        'timing_acceptance': 'CPU_AND_50MHZ_CLOSE_GLOBAL_HDMI_SETUP_MINUS_0_063_NS',
        'created_utc': now(), 'source_sha256': inputs,
        'current_inputs_sha256': {n: sha(ROOT / n) for n in inputs if (ROOT / n).is_file()},
        'fitted_rtl_sha256': actual_fitted, 'fitted_all_input_sha256': after['sources_sha256'],
        'named_current_nonfitted_changes': fitted_delta, 'timing_packet_sha256': tm['sha256'],
        'timing_packet': str(packet), 'fitted_run': str(fitted), 'rbf': read(packet / 'result.json')['rbf'],
        'registry': registry, 'external_inputs': external, 'tools': tools,
        'support_inputs': support_inputs, 'git': git, 'docker_images': images,
        'wrapper_sha256': inventory(top / 'tool-wrappers'),
        'coordinator_sha256': sha(Path(__file__)), 'stage_manifest_sha256': sha(args.stage_manifest),
        'resource_policy': registry['resource_policy'], 'storage': disk(), 'no_options_off': True}
    write(top / 'inputs.json', source)
    files = {'inputs.json': top / 'inputs.json', 'coordinator.py': Path(__file__), 'stage-manifest.json': args.stage_manifest}
    files.update({'source/' + n: work / n for n in inputs if Path(n).suffix.lower() not in PRIVATE_SUFFIXES})
    write(top / 'source-archive.json', seal(top / 'source-inputs.tar.gz', files))
    print('TIMING_OPEN_REGRESSION_FROZEN_NOT_EXECUTED', len(inputs), top, flush=True)


def cleanup_objects(paths, top, protected):
    removed = []; reclaimed = 0
    for p in paths:
        if not p.exists(): continue
        files = [p] if p.is_file() else list(p.rglob('*'))
        for f in files:
            if f.is_file() and not f.is_symlink() and str(f.resolve()) not in protected and (
                    f.suffix.lower() in COMPILER_SUFFIXES or os.access(f, os.X_OK) and f.suffix not in ('.py', '.sh')):
                owned(f, top); reclaimed += f.stat().st_size; f.unlink(); removed.append(str(f.relative_to(top)))
    return {'removed': removed, 'bytes_unlinked_on_D': reclaimed, 'host_C_reclamation_claim': False}


def cleanup_temp(tmp, top):
    """Only an owned stage temp directory, after archive readback."""
    owned(tmp, top)
    files = list(tmp.rglob('*'))
    require(not any(p.is_symlink() for p in files), 'Refuse temp tree containing symlinks')
    size = sum(p.stat().st_size for p in files if p.is_file())
    shutil.rmtree(tmp)
    return {'path': str(tmp.relative_to(top)), 'bytes_unlinked_on_D': size}


def finish_own_containers(source, label):
    spec = source['tools'].get('docker', {})
    if 'path' not in spec: return {'running': [], 'stopped': []}
    command = [spec['path'], 'ps', '-q', '--filter', 'label=pcat-regression-run=' + label]
    r = subprocess.run(command, capture_output=True, text=True, timeout=30)
    require(r.returncode == 0, 'Cannot inspect own labelled containers')
    found = r.stdout.split(); stopped = []
    for container in found:
        require(re.fullmatch('[a-f0-9]{12,64}', container), 'Invalid Docker container identity')
        r = subprocess.run([spec['path'], 'stop', '-t', '15', container], capture_output=True, text=True, timeout=30)
        require(r.returncode == 0, 'Cannot stop own labelled container: ' + container)
        stopped.append(container)
    r = subprocess.run(command, capture_output=True, text=True, timeout=30)
    require(r.returncode == 0 and not r.stdout.strip(), 'Own labelled container remains active')
    return {'running': found, 'stopped': stopped}


class ResourceStop(RuntimeError):
    pass


def stop_child_tree(child):
    """Kill this child and its current descendants, including private sessions.

    PID start ticks are checked before either signal to prevent PID reuse from
    widening ownership. Docker descendants have a separate run label contract.
    """
    table = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
                table[int(p.name)] = (int(fields[1]), fields[19])
            except (FileNotFoundError, PermissionError, ProcessLookupError): pass
    selected = {child.pid} if child.pid in table else set()
    while True:
        expanded = selected | {pid for pid, (parent, _) in table.items() if parent in selected}
        if expanded == selected: break
        selected = expanded
    def alive(pid):
        try: return (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19] == table[pid][1]
        except (FileNotFoundError, PermissionError, ProcessLookupError): return False
    for sig, delay in ((signal.SIGTERM, 15), (signal.SIGKILL, 0)):
        for pid in sorted(selected, reverse=True):
            if alive(pid):
                try: os.kill(pid, sig)
                except ProcessLookupError: pass
        if delay:
            end = time.monotonic() + delay
            while time.monotonic() < end and any(alive(pid) for pid in selected): time.sleep(0.2)
    child.wait(timeout=15)
    return sorted(selected)


def run(args):
    top = args.output.resolve(); source = read(top / 'inputs.json')
    require(os.name == 'posix' and str(top).startswith('/mnt/d/') and
            top.is_relative_to(ROOT / 'build'), 'Execute only an owned WSL D: run')
    archive = read(top / 'source-archive.json')
    require(sha(top / archive['archive']) == archive['sha256'], 'Frozen source archive changed')
    with tarfile.open(top / archive['archive']) as frozen:
        require(set(frozen.getnames()) == set(archive['members']) and
                len(frozen.getnames()) == len(set(frozen.getnames())), 'Frozen archive membership changed')
        for entry in frozen:
            raw = frozen.extractfile(entry).read(); spec = archive['members'][entry.name]
            require(len(raw) == spec['bytes'] and hashlib.sha256(raw).hexdigest() == spec['sha256'],
                    'Frozen archive member changed: ' + entry.name)
        require(frozen.extractfile('inputs.json').read() == (top / 'inputs.json').read_bytes(), 'Unsealed input receipt')
    require(source['coordinator_sha256'] == sha(Path(__file__)), 'Coordinator changed after freeze')
    work = top / 'work'; build = work / 'build/full-regression'; build.mkdir(parents=True, exist_ok=True)
    check_timing(Path(source['timing_packet']), Path(source['fitted_run']))
    results = []; stopped = False
    mapping = {'FROZEN': str(work), 'RUN': str(build), **{n: v['path'] for n, v in source['external_inputs'].items() if v['status'] == 'PRESENT'}}
    def resolve(value):
        return re.sub(r'\{([A-Z_0-9]+)\}', lambda m: mapping[m[1]], str(value))
    def source_guard():
        require(inventory(work) == source['source_sha256'], 'Frozen source mutated')
        require(all((ROOT / n).is_file() and sha(ROOT / n) == h for n, h in source['current_inputs_sha256'].items()), 'Current source mutated')
        for n, item in source['external_inputs'].items():
            if item['status'] == 'PRESENT': require(reference_inventory(Path(item['path'])) == item['sha256'], 'External input mutated: ' + n)
        require(inventory(top / 'tool-wrappers') == source['wrapper_sha256'], 'Tool wrapper changed')
        for name, tool in source['tools'].items():
            if 'path' in tool: require(sha(Path(tool['path']).resolve()) == tool['sha256'], 'Tool changed: ' + name)
        for tag, expected in source['docker_images'].items():
            if expected['status'] == 'PRESENT':
                actual = subprocess.check_output([source['tools']['docker']['path'], 'image', 'inspect',
                    '--format={{.Id}}', tag], text=True).strip()
                require(actual == expected['id'], 'Docker image changed: ' + tag)
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == source['git']['head'],
                'Repository history changed during source-bound regression')
    def metadata_snapshot():
        return {'frozen': metadata(work, IGNORED),
                'current': {n: metadata(ROOT / n) for n in source['current_inputs_sha256']},
                'external': {n: metadata(Path(item['path']), frozenset({'.git'}))
                             for n, item in source['external_inputs'].items() if item['status'] == 'PRESENT'},
                'wrappers': metadata(top / 'tool-wrappers'),
                'tools': {n: metadata(Path(spec['path']).resolve()) for n, spec in source['tools'].items()
                          if 'path' in spec}}
    source_guard()  # Full bytes at execution start, including all external references.
    frozen_metadata = metadata_snapshot()
    def fast_source_guard():
        require(metadata_snapshot() == frozen_metadata,
                'Source/reference/tool metadata changed between complete hash checkpoints')
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == source['git']['head'],
                'Repository history changed during source-bound regression')
    def terminate(signum, frame):
        raise KeyboardInterrupt('Coordinator signalled ' + str(signum))
    signal.signal(signal.SIGTERM, terminate)
    for stage in source['registry']['stages']:
        record = {'id': stage['id'], 'mandatory': stage['mandatory'], 'start_utc': now(), 'status': 'RUNNING'}
        folder = top / 'stages' / stage['id']; folder.mkdir(parents=True, exist_ok=False)
        log = folder / 'stdout.log'; tool_log = folder / 'tool-arguments.jsonl'
        missing = [n for n in stage['required_placeholders'] if n not in mapping]
        dependencies = {r['id']: r['status'] for r in results}
        if missing or stage.get('unresolved'):
            record.update(status='UNAVAILABLE', missing=missing, reason=stage.get('unresolved', 'Exact prerequisite input absent'))
        elif any(dependencies.get(n) != 'PASS' for n in stage.get('depends', [])):
            record.update(status='NOT_EXECUTED_DEPENDENCY_FAILED', dependencies=stage['depends'])
        else:
            try:
                record['free_before'] = floor()
                fast_source_guard()
                if len(results) and len(results) % 32 == 0:
                    source_guard()
                    record['source_guard'] = 'FULL_SHA256_AFTER_32_STAGES_AND_METADATA_EACH_STAGE'
                else:
                    record['source_guard'] = 'METADATA_EACH_STAGE_WITH_FULL_SHA256_AT_START_EVERY_32_AND_END'
                command, cwd = [resolve(a) for a in stage['argv']], Path(resolve(stage['cwd']))
                b = build / 'cpu' if stage.get('shared_cpu') else Path(resolve(stage['build']))
                tmp = top / 'tmp' / stage['id']; tmp.mkdir(parents=True)
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', SPK286_BUILD_JOBS='1',
                    SPK286_BUILD_DIR=str(b), PCAT_BUILD_DIR=str(b), PCAT_CODE_BUFFER_BUILD_DIR=str(b),
                    SPK286_SINGLESTEP_ROOT=mapping['CORPUS'], TMPDIR=str(tmp), TEMP=str(tmp), TMP=str(tmp),
                    MAKEFLAGS='-j1', CMAKE_BUILD_PARALLEL_LEVEL='1',
                    REGRESSION_TOOL_LOG=str(tool_log), REGRESSION_RUN_LABEL=top.name,
                    PATH=str(top / 'tool-wrappers') + os.pathsep + os.environ['PATH'])
                env.pop('SPK286_EXPAND_DOWN_TERMINATION_SMOKE', None)
                env.update({k: resolve(v) for k, v in stage.get('environment', {}).items()})
                record.update(command=command, cwd=str(cwd), environment={k: env[k] for k in env if k not in os.environ or env[k] != os.environ[k]}, build=str(b))
                write(folder / 'command.json', record)
                with log.open('w') as stream:
                    child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                    record['pid'] = child.pid
                    try:
                        deadline = time.monotonic() + stage['timeout_seconds'] if stage['timeout_seconds'] is not None else None
                        while child.poll() is None:
                            try: child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                if deadline is not None and time.monotonic() >= deadline:
                                    raise subprocess.TimeoutExpired(command, stage['timeout_seconds'])
                                try: floor()
                                except ValueError as exc: raise ResourceStop(str(exc)) from exc
                        code = child.returncode
                        record.update(exit_status=code, status='PASS' if code == 0 else 'FAIL')
                    except (subprocess.TimeoutExpired, KeyboardInterrupt, ResourceStop) as exc:
                        record['terminated_owned_pids'] = stop_child_tree(child)
                        status = 'USER_STOPPED' if isinstance(exc, KeyboardInterrupt) else (
                            'RESOURCE_INTERRUPTED' if isinstance(exc, ResourceStop) else 'TIMEOUT')
                        record.update(exit_status=child.returncode, status=status, diagnostic=str(exc))
                        stopped = isinstance(exc, (KeyboardInterrupt, ResourceStop))
                record['docker_cleanup'] = finish_own_containers(source, top.name)
                if record['status'] == 'PASS' and record['docker_cleanup']['running']:
                    record['status'] = 'FAIL_LINGERING_OWN_CONTAINER'
                fast_source_guard()
                # Named output roots only; never collect or clean external references.
                roots = [b, tmp]
                for i, arg in enumerate(command):
                    p = Path(arg)
                    if p.is_absolute() and p.is_relative_to(build) and (i == 0 or command[i-1] != '--executable'):
                        roots.append(p)
                for default in (work / 'build', work / 'vendor/spk286/build'):
                    if default.exists(): roots += [p for p in default.iterdir() if p.resolve() != build.resolve()]
                roots = list(dict.fromkeys(p for p in roots if p.exists()))
                artifact_files = {}; identities = {}
                for p in roots:
                    owned(p, top)
                    for f in ([p] if p.is_file() else p.rglob('*')):
                        if f.is_file() and not f.is_symlink():
                            n = f.relative_to(top).as_posix(); identities[n] = {'sha256': sha(f), 'bytes': f.stat().st_size}
                            if f.suffix.lower() not in COMPILER_SUFFIXES | PRIVATE_SUFFIXES and not (os.access(f, os.X_OK) and f.suffix not in ('.py', '.sh')):
                                artifact_files['artifacts/' + n] = f
                record['artifact_identity_count'] = len(identities)
                write(folder / 'artifact-identities.json', identities)
                record.update(end_utc=now(), log_sha256=sha(log))
                write(folder / 'receipt.json', record)
                artifact_files.update({p.name: p for p in folder.iterdir() if p.is_file()})
                write(folder / 'archive.json', seal(folder / 'stage-evidence.tar.gz', artifact_files))
                protected = {str((build / 'cpu/verilator/obj_dir/spk286_smoke').resolve())}
                write(folder / 'cleanup.json', cleanup_objects(roots, top, protected))
                record['temp_cleanup'] = cleanup_temp(tmp, top)
                record['free_after_verified_cleanup'] = disk()
            except Exception as exc:
                record.update(status='RESOURCE_OR_INFRASTRUCTURE_FAILURE', error=repr(exc), end_utc=now())
                stopped = True  # Never keep allocating after source/resource/archival failure.
        record.setdefault('end_utc', now()); write(folder / 'final.json', record)
        if not (folder / 'archive.json').exists() and not (folder / 'stage-evidence.tar.gz').exists():
            files = {p.name: p for p in folder.iterdir() if p.is_file()}
            write(folder / 'archive.json', seal(folder / 'stage-evidence.tar.gz', files))
        results.append(record)
        write(top / 'progress.json', {'status': 'RUNNING', 'stages': results, 'expected_stages': len(source['registry']['stages'])})
        print('REGRESSION_STAGE', stage['id'], record['status'], flush=True)
        if stopped: break
    errors = []
    try: source_guard()
    except Exception as exc: errors.append(repr(exc))
    matrices = {}; matrix_data = {}
    for name, path in {'physical': build / 'physical-identity.json',
                       'profiles': build / 'profile-aggregate/receipt.json',
                       'live': build / 'live-speed/receipt.json'}.items():
        if path.is_file():
            matrix_data[name] = read(path)
            matrices[name] = {'path': str(path.relative_to(top)), 'sha256': sha(path)}
        else: errors.append('Mandatory matrix receipt absent: ' + name)
    if 'physical' in matrix_data:
        r = matrix_data['physical']; matrices['physical']['totals'] = r.get('totals')
        if not (r['validation'] == 'PASS' and r['totals'] == dict(discovered=1387000, revoked=3,
                executed=1386996, passed=1386996, failed=0) and r['opcode_files'] == 307 and
                r['required_population'] == 1386997 and r['unexpected_omissions'] == 0 and len(r['not_evaluable']) == 1):
            errors.append('Physical identity matrix incomplete')
    if 'profiles' in matrix_data:
        r = matrix_data['profiles']; matrices['profiles']['counts'] = r.get('counts')
        if not (r['status'] == 'PASS' and r['counts'] == dict(iverilog=208, verilator=56, max_equivalence=26)
                and not r['failures'] and not r['source_changes']): errors.append('Profile compatibility matrix incomplete')
    if 'live' in matrix_data:
        r = matrix_data['live']; matrices['live']['coverage'] = r.get('coverage')
        if not (r['status'] == 'PASS' and r['coverage']['cpu_bridge_cases'] == 192 and
                r['coverage']['profile_pairs'] == 64 and r['coverage']['backend_latencies'] == [0, 7, 20]):
            errors.append('Live CPU/bridge matrix incomplete')
    complete = len(results) == len(source['registry']['stages']) and all(r['status'] == 'PASS' for r in results) and not errors
    write(top / 'summary.json', {'status': 'FUNCTIONAL_PASS_TIMING_OPEN' if complete else 'INCOMPLETE_OR_FAIL',
        'timing_status': 'GLOBAL_HDMI_SETUP_MINUS_0_063_NS_CPU_50MHZ_CLOSED', 'stages': results,
        'mandatory_expected': len(source['registry']['stages']), 'source_sha256': source['source_sha256'],
        'same_fitted_rtl': all((work / n).is_file() and sha(work / n) == h for n, h in source['fitted_rtl_sha256'].items()),
        'errors': errors, 'actual_matrix_receipts': matrices,
        'timing_packet_sha256': source['timing_packet_sha256'], 'external_inputs': source['external_inputs'],
        'full_matrix_expected': {k: source['registry'][k] for k in ('physical_required', 'profile_expected', 'mutation_families', 'live_profile_latency_cases')},
        'source_guard_policy': 'Complete SHA-256 at start, every 32 stages and end; size/mtime/ctime/mode and Git HEAD before and after each stage.',
        'cleanup': 'Only verified compiler objects removed; compact metadata and dependent CPU executable retained',
        'hardware': 'NOT_RUN', 'end_utc': now()})
    print('FULL_REGRESSION', 'FUNCTIONAL_PASS_TIMING_OPEN' if complete else 'INCOMPLETE_OR_FAIL', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--stage-manifest', type=Path, default=OWN / 'stage-manifest.v2.json')
    parser.add_argument('--fitted-run', type=Path)
    parser.add_argument('--timing-packet', type=Path)
    parser.add_argument('--corpus', type=Path, default=Path('/mnt/d/GitHub/SPK286/.cache/singlestep-80286'))
    parser.add_argument('--references', type=Path, help='Exact external reference paths and per-file SHA256 maps')
    parser.add_argument('--support-inputs', type=Path, help='Named archived evidence files or directories with exact SHA256 maps')
    parser.add_argument('--tool-overlay-approval', type=Path, help='Explicit path -> fitted/current SHA256 pair for nonfitted tools/docs only')
    parser.add_argument('--execute-frozen', action='store_true', help='Explicitly run an already gated/frozen run')
    args = parser.parse_args()
    if args.execute_frozen:
        run(args)
    else:
        require(args.fitted_run and args.timing_packet, 'Preparation requires the exact fitted timing packet and run')
        prepare(args)


if __name__ == '__main__':
    main()
