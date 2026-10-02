#!/usr/bin/env python3
"""Freeze current inputs and run CPU, physical-corpus and AT regression lanes.

No production source is edited. Each independent check has its own receipt
and log; a failure never prevents later independent checks from running.
Run inside WSL. The output directory must be new.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[2]
AUDITS = ('phase3_boundaries alu stack_control events byte_prefix scalar shift '
          'data unary adjust segment stack_frame far strings io muldiv '
          'double_fault phase8 task_late null_ldtr').split()
# Historical counterfactual tests require a Git baseline and are separate
# experiments. Physical timing extraction requires Quartus databases and is
# outside a functional regression. All other shell regression entry points run.
EXCLUDED_SHELL = {'test_at_code_buffer_equivalence.sh'}

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(p, value):
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n')
    temp.replace(p)

class Regression:
    def __init__(self, output, corpus, production_only=False):
        self.production_only = production_only
        self.out, self.corpus = output.resolve(), corpus.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.work = self.out/'work'
        ignore = shutil.ignore_patterns('.git', '.cache', '__pycache__', 'build',
                                       'db', 'incremental_db', 'obj_dir')
        for name in ('rtl', 'sys', 'vendor', 'scripts', 'sim', 'SW', 'tests', 'tools'):
            shutil.copytree(ROOT/name, self.work/name, ignore=ignore)
        # This machine check consumes an existing source-bound SAT receipt.
        # Freeze its exact evidence along with the implementation, without
        # importing unrelated fits or proprietary BIOS binaries from build/.
        proof = Path('docs/evidence/stack-offset-arithmetic-20261002/upstream-formal')
        if (ROOT/proof).is_dir():
            shutil.copytree(ROOT/proof, self.work/proof)
        for p in ROOT.iterdir():
            if p.is_file() and p.suffix.lower() in (
                    '.sv', '.v', '.vh', '.qsf', '.qpf', '.qip', '.sdc', '.tcl',
                    '.mif', '.mem', '.hex'):
                shutil.copy2(p, self.work/p.name)
        self.inputs = {p.relative_to(self.work).as_posix(): sha(p)
                       for p in self.work.rglob('*') if p.is_file()}
        self.macros = re.findall(r'VERILOG_MACRO "(SPK286_P\d\d_[A-Z0-9_]+)"',
                                (self.work/'config.tcl').read_text())
        self.cpu = self.work/'vendor/spk286'
        wrappers = self.out/'production-tools'
        wrappers.mkdir()
        for tool in ('verilator', 'iverilog', 'yosys'):
            flags = ['-D'+m for m in self.macros]
            if tool == 'yosys':
                # Yosys accepts defines on read_verilog, not its command line.
                body = ("args=sys.argv[1:]\n"
                        "args=[a.replace('read_verilog -sv ', 'read_verilog -sv "
                        + ' '.join(flags) + " ') if i and args[i-1]=='-p' else a "
                        "for i,a in enumerate(args)]\n")
            else:
                body = 'args='+repr(flags)+'+sys.argv[1:]\n'
            path = wrappers/tool
            path.write_text('#!/usr/bin/env python3\nimport os,sys\n'+body+
                            f"os.execv('/usr/bin/{tool}', ['/usr/bin/{tool}']+args)\n")
            path.chmod(0o755)
        self.wrappers = wrappers
        self.results = []
        self.lock = threading.Lock()
        self.started = now()
        self.compiled = {mode: threading.Event() for mode in ('reference', 'production')}
        self.head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        with (self.out/'git-diagnostics.log').open('wb') as diagnostics:
            env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
            (self.out/'working-changes.patch').write_bytes(subprocess.check_output(
                ['git', '-C', str(ROOT), 'diff', '--binary', 'HEAD'], stderr=diagnostics, env=env))
            (self.out/'git-status.txt').write_bytes(subprocess.check_output(
                ['git', '-C', str(ROOT), 'status', '--short'], stderr=diagnostics, env=env))
        write_json(self.out/'inputs.json', dict(start_utc=self.started, head=self.head,
            source_sha256=self.inputs, cpu_macros=self.macros,
            production_only=production_only,
            corpus=str(self.corpus), corpus_revision=subprocess.check_output(
                ['git', '-C', str(self.corpus), 'rev-parse', 'HEAD'], text=True).strip(),
            excluded_shell_tests={n:'Historical Git-baseline equivalence experiment; production capacity/coherence tests run.' for n in EXCLUDED_SHELL}))
        self.persist()
        print(f'FULL_REGRESSION_STARTED source_files={len(self.inputs)} head={self.head}', flush=True)

    def persist(self):
        write_json(self.out/'progress.json', dict(status='RUNNING', start_utc=self.started,
            updated_utc=now(), stages=self.results))

    def env(self, mode, build):
        env = dict(os.environ, SPK286_SINGLESTEP_ROOT=str(self.corpus),
                   SPK286_BUILD_DIR=str(build), PCAT_BUILD_DIR=str(build),
                   PCAT_CODE_BUFFER_BUILD_DIR=str(build), SPK286_BUILD_JOBS='2',
                   PYTHONUNBUFFERED='1')
        if mode == 'production':
            env['PATH'] = str(self.wrappers)+os.pathsep+env['PATH']
        return env

    def stage(self, lane, name, command, cwd, mode='reference', build=None, timeout=3600):
        build = build or self.out/lane/name
        # Some validation entry points intentionally require an absent output.
        logdir = self.out/'logs'/lane
        logdir.mkdir(parents=True, exist_ok=True)
        log = logdir/(name+'.log')
        record = dict(lane=lane, stage=name, command=list(map(str, command)),
                      cwd=str(cwd), build=str(build), status='RUNNING', start_utc=now(),
                      log=str(log.relative_to(self.out)))
        with self.lock:
            self.results.append(record)
            self.persist()
        with log.open('w') as stream:
            child = subprocess.Popen(record['command'], cwd=cwd, env=self.env(mode, build),
                                     stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            record['pid'] = child.pid
            try:
                code = child.wait(timeout=timeout)
                status = 'PASS' if code == 0 else 'FAIL'
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=15)
                status, code = 'TIMEOUT', child.returncode
        with self.lock:
            record.update(status=status, exit_status=code, end_utc=now(), log_sha256=sha(log))
            self.persist()
        print(f'REGRESSION_STAGE {lane}/{name} {status} rc={code}', flush=True)
        return code == 0

    def cpu_lane(self, mode):
        build = self.out/mode/'cpu'
        build.parent.mkdir(parents=True, exist_ok=True)
        native = Path('/tmp')/(self.out.name+'-'+mode+'-cpu')
        assert not native.exists(), 'Use fresh native compiler storage'
        native.mkdir()
        build.symlink_to(native, target_is_directory=True)
        run = lambda name, command, **kw: self.stage(mode, name, command, self.cpu,
            mode, build=build, **kw)
        ready = run('compile-smoke', ['bash', 'scripts/build_verilator.sh'])
        self.compiled[mode].set()
        if ready:
            exe = build/'verilator/obj_dir/spk286_smoke'
            physical = self.out/mode/'physical-required'
            run('physical-complete', ['python3', '-m', 'tools.run_phase7_physical',
                '--repo', self.corpus, '--executable', exe, '--build-dir', physical])
            run('physical-identity', ['python3', '-m', 'tools.phase7_complete_reports',
                '--repo', self.corpus, '--directory', physical/'singlestep',
                '--output', self.out/mode/'physical-summary.json'])
            for op in ('D6', 'D8'):
                run('physical-'+op, ['python3', '-m', 'tools.run_singlestep',
                    '--repo', self.corpus, '--executable', exe, '--build-dir',
                    self.out/mode/('physical-'+op), '--opcode', op, '--full',
                    '--include-prefixes', '--include-exceptions'])
        for name, command in (
            ('microcode-consistency', ['python3', '-m', 'tools.microcode.compile_microcode', '--check']),
            ('microcode-audit', ['python3', '-m', 'tools.microcode.audit_microcode', '--output', build/'microcode-audit']),
            ('python-all', ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']),
            ('lint', ['bash', 'scripts/lint.sh'])):
            run(name, command)
        text = (self.cpu/'scripts/test_units.sh').read_text()
        part = text.split('tests=(', 1)[1].split('if [[ "$unit" != all ]]', 1)[0]
        units = list(dict.fromkeys(re.findall(r'\bspk286_[a-z0-9_]+\b', part)))
        write_json(self.out/mode/'registered-units.json', units)
        for unit in units:
            run(unit, ['bash', 'scripts/test_units.sh', 'both', unit])
        for name, command in (
            ('verilator-smoke', ['bash', 'scripts/test_verilator.sh', '--trace']),
            ('iverilog-smoke', ['bash', 'scripts/test_iverilog.sh']),
            ('state-default', ['python3', '-m', 'tools.state_vectors']),
            ('state-fixtures', ['python3', '-m', 'tools.state_vectors', '--source', 'tests/fixtures/state_vectors.json']),
            ('data-loader', ['python3', 'tools/run_tests.py', '--smoke']),
            ('failure-propagation', ['bash', 'scripts/verify_failure_path.sh']),
            ('yosys-synthesis', ['bash', 'scripts/synth_check.sh']),
            ('mcl86-tests', ['python3', '-m', 'unittest', 'discover', '-s', 'research/mcl86/tests', '-v']),
            ('mcl86-roundtrip', ['python3', '-m', 'research.mcl86.mcl86_uccheck',
                '--directory', self.corpus.parent/'mcl86', '--output', build/'mcl86'])):
            run(name, command)

    def audit_lane(self):
        for name in AUDITS:
            option = '--output' if name in ('double_fault', 'task_late', 'null_ldtr') else '--build-dir'
            self.stage('audits', name, ['python3', self.work/'tools/perf01/run_with_host_budget.py',
                '--seconds', '600', 'tools.audit_'+name,
                option, self.out/'audits'/name], self.cpu,
                mode='production' if self.production_only else 'reference')
        self.compiled['production'].wait()
        exe = self.out/'production/cpu/verilator/obj_dir/spk286_smoke'
        if exe.is_file():
            for name in ('muldiv_adapter', 'combined_adapter'):
                self.stage('audits', name, ['python3', '-m', 'tools.audit_'+name,
                    '--repo', self.corpus, '--executable', exe, '--build-dir',
                    self.out/'audits'/name], self.cpu, mode='production')
            for name in ('singlestep', 'scalar_io'):
                self.stage('audits', name, ['python3', '-m', 'tools.audit_'+name,
                    '--repo', self.corpus, '--build-dir', self.out/'production/cpu'],
                    self.cpu, mode='production')
            self.stage('audits', 'synthetic-io', ['python3', '-m', 'tools.phase7_synthetic_io',
                '--executable', exe, '--build-dir', self.out/'audits/synthetic-io'], self.cpu, mode='production')

    def machine_lane(self):
        scripts = sorted((self.work/'scripts').glob('test_*.sh'))
        write_json(self.out/'registered-machine-scripts.json', [p.name for p in scripts])
        # Ordered core-boundary checks first, then the remaining complete registry.
        priority = ('test_i1_cpu_package.sh', 'test_a1_at_bridge.sh', 'test_a2_memory_arbiter.sh',
                    'test_a3_interrupts.sh', 'test_a4_dma_refresh_pit.sh', 'test_a5_at_devices.sh',
                    'test_at_machine_boundary.sh')
        scripts.sort(key=lambda p: (priority.index(p.name) if p.name in priority else len(priority), p.name))
        for p in scripts:
            if p.name not in EXCLUDED_SHELL:
                if self.production_only and p.name == 'test_at_bus_latency.sh':
                    # This experiment explicitly disables P01/P02/P06. The
                    # active bridge and fetch paths have their direct banks.
                    print('SCOPE_EXCLUSION test_at_bus_latency.sh CPU-options-off experiment', flush=True)
                    continue
                self.stage('machine', p.stem, ['bash', p.relative_to(self.work)], self.work,
                    mode='production' if self.production_only else 'reference')
        for name in ('test_check_at_net_delay', 'test_summarize_at_50mhz_timing', 'test_at_scaler_luminance'):
            self.stage('machine', name, ['python3', 'scripts/'+name+'.py'], self.work)
        self.stage('machine', 'p05-limit-equivalence', ['python3', 'scripts/test_p05_limit_equivalence.py',
            '--output', self.out/'machine/p05-limit-equivalence'], self.work)
        self.stage('machine', 'distributed-rom-check', ['python3', 'scripts/build_event_diag_rom.py', '--check'], self.work)
        self.stage('machine', 'pit-refresh-directed', ['bash', 'tools/perf01/test_pit_refresh.sh',
            self.work, self.out/'machine/pit-refresh-directed'], self.work)
        posted = self.out/'machine/posted-machine'
        ok = self.stage('machine', 'posted-machine', ['python3', 'tools/perf01/test_posted_machine.py',
            self.work, posted, '--pit-refresh'], self.work)
        if ok:
            self.stage('machine', 'distributed-posted-rom', ['python3',
                'tools/perf01/test_distributed_pit_diag.py', posted], self.work)

    def run(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            modes = ('production',) if self.production_only else ('reference', 'production')
            jobs = [pool.submit(self.cpu_lane, mode) for mode in modes]
            jobs += [pool.submit(self.audit_lane), pool.submit(self.machine_lane)]
            for job in jobs:
                try:
                    job.result()
                except Exception as exc:
                    with self.lock:
                        self.results.append(dict(stage='lane-exception', status='FAIL', error=repr(exc)))
                        self.persist()
                    print('REGRESSION_LANE_EXCEPTION '+repr(exc), flush=True)
        changed = [n for n, h in self.inputs.items() if not (self.work/n).is_file() or sha(self.work/n) != h]
        current_changed = [n for n, h in self.inputs.items() if not (ROOT/n).is_file() or sha(ROOT/n) != h]
        summary = dict(status='PASS' if not changed and all(r['status']=='PASS' for r in self.results) else 'FAIL',
            start_utc=self.started, end_utc=now(), stages=self.results,
            frozen_inputs_changed=changed, current_inputs_changed=current_changed)
        write_json(self.out/'summary.json', summary)
        write_json(self.out/'progress.json', summary)
        print('FULL_REGRESSION_'+summary['status'], flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--corpus', type=Path, required=True)
    p.add_argument('--production-only', action='store_true',
                   help='Run only the active CPU options from config.tcl')
    p.add_argument('--prepare-only', action='store_true',
                   help='Freeze and inspect inputs without executing checks')
    a = p.parse_args()
    regression = Regression(a.output, a.corpus, a.production_only)
    if a.prepare_only:
        write_json(regression.out/'progress.json', dict(status='PREPARED_NOT_EXECUTED',
            start_utc=regression.started, end_utc=now(), stages=[]))
        print('FULL_REGRESSION_PREPARED_NOT_EXECUTED', flush=True)
    else:
        regression.run()

if __name__ == '__main__':
    main()
