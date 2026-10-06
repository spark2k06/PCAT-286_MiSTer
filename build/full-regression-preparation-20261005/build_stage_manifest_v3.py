#!/usr/bin/env python3
"""Create a command registry from existing source registries; execute no stage."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent


def main():
    plan = json.loads((OWN / 'plan.json').read_bytes())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OWN / 'stage-manifest.v3.json')
    out = parser.parse_args().output.resolve()
    if out.parent != OWN.resolve():
        raise ValueError('Versioned preparation manifest must remain in this owned preparation folder')
    if out.exists():
        raise ValueError('Versioned manifest already exists')
    stages = []
    def add(name, argv, cwd='{FROZEN}', **kw):
        stages.append(dict(id=name, argv=argv, cwd=cwd, mandatory=True,
                           build='{RUN}/stage-build/' + name, timeout_seconds=3600, **kw))
    cpu = '{FROZEN}/vendor/spk286'
    core = '{RUN}/cpu'
    add('cpu-compile-smoke', ['bash', 'scripts/build_verilator.sh'], cpu, shared_cpu=True)
    add('cpu-microcode-consistency', ['python3', '-B', '-m', 'tools.microcode.compile_microcode', '--check'], cpu)
    add('cpu-microcode-audit', ['python3', '-B', '-m', 'tools.microcode.audit_microcode', '--output', '{RUN}/microcode-audit'], cpu)
    add('cpu-python-all', ['python3', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], cpu, shared_cpu=True)
    add('cpu-lint', ['bash', 'scripts/lint.sh'], cpu)
    registry = (ROOT / 'vendor/spk286/scripts/test_units.sh').read_text()
    part = registry.split('tests=(', 1)[1].split('if [[ "$unit" != all ]]', 1)[0]
    units = list(dict.fromkeys(re.findall(r'\bspk286_[a-z0-9_]+\b', part)))
    supplement = [] if 'spk286_event_arbitration' in units else ['spk286_event_arbitration']
    for unit in units + supplement:
        add('cpu-unit-' + unit, ['bash', 'scripts/test_units.sh', 'both', unit], cpu)
    for name, argv in [
        ('verilator-smoke', ['bash', 'scripts/test_verilator.sh', '--trace']),
        ('iverilog-smoke', ['bash', 'scripts/test_iverilog.sh']),
        ('state-default', ['python3', '-B', '-m', 'tools.state_vectors']),
        ('state-fixtures', ['python3', '-B', '-m', 'tools.state_vectors', '--source', 'tests/fixtures/state_vectors.json']),
        ('data-loader', ['python3', '-B', 'tools/run_tests.py', '--smoke']),
        ('failure-propagation', ['bash', 'scripts/verify_failure_path.sh']),
        ('yosys-synthesis', ['bash', 'scripts/synth_check.sh']),
        ('mcl86-tests', ['python3', '-B', '-m', 'unittest', 'discover', '-s', 'research/mcl86/tests', '-v']),
        ('mcl86-roundtrip', ['python3', '-B', '-m', 'research.mcl86.mcl86_uccheck', '--directory', '{MCL86}', '--output', '{RUN}/mcl86'])]:
        add('cpu-' + name, argv, cpu, shared_cpu=True)
    # Every registered test.sh SST smoke is retained, not inferred from the full population.
    for name, flags in [('mov', []), ('operands', ['--opcode', '89', '--opcode', '8B']),
                        ('alu', ['--alu']), ('stack-control', ['--stack-control'])]:
        add('cpu-sst-smoke-' + name, ['python3', '-B', '-m', 'tools.run_singlestep',
            '--repo', '{CORPUS}', '--executable', core + '/verilator/obj_dir/spk286_smoke', '--smoke', *flags],
            cpu, shared_cpu=True, depends=['cpu-compile-smoke'])
    add('physical-required', ['python3', '-B', '-m', 'tools.run_phase7_physical', '--repo', '{CORPUS}',
        '--executable', core + '/verilator/obj_dir/spk286_smoke', '--build-dir', '{RUN}/physical-required'],
        cpu, shared_cpu=True, depends=['cpu-compile-smoke'], corpus_full=True)
    add('physical-identity', ['python3', '-B', '-m', 'tools.phase7_complete_reports', '--repo', '{CORPUS}',
        '--directory', '{RUN}/physical-required/singlestep', '--output', '{RUN}/physical-identity.json'],
        cpu, depends=['physical-required'])
    for op in ('D6', 'D8'):
        add('physical-' + op, ['python3', '-B', '-m', 'tools.run_singlestep', '--repo', '{CORPUS}',
            '--executable', core + '/verilator/obj_dir/spk286_smoke', '--build-dir', '{RUN}/physical-' + op,
            '--opcode', op, '--full', '--include-prefixes', '--include-exceptions'],
            cpu, depends=['cpu-compile-smoke'], corpus_full=True)
    for audit in plan['mutation_audit_families']:
        option = '--output' if audit in ('double_fault', 'task_late', 'null_ldtr') else '--build-dir'
        add('mutation-' + audit, ['python3', '-B', '{FROZEN}/tools/perf01/run_with_host_budget.py',
            '--seconds', '600', 'tools.audit_' + audit, option, '{RUN}/audits/' + audit], cpu)
    for name in ('muldiv_adapter', 'combined_adapter'):
        add('audit-' + name, ['python3', '-B', '-m', 'tools.audit_' + name, '--repo', '{CORPUS}',
            '--executable', core + '/verilator/obj_dir/spk286_smoke', '--build-dir', '{RUN}/audits/' + name],
            cpu, depends=['cpu-compile-smoke'], corpus_full=True)
    for name in ('singlestep', 'scalar_io'):
        add('audit-' + name, ['python3', '-B', '-m', 'tools.audit_' + name, '--repo', '{CORPUS}',
            '--build-dir', core], cpu, shared_cpu=True, depends=['cpu-compile-smoke'])
    add('audit-synthetic-io', ['python3', '-B', '-m', 'tools.phase7_synthetic_io', '--executable',
        core + '/verilator/obj_dir/spk286_smoke', '--build-dir', '{RUN}/audits/synthetic-io'],
        cpu, depends=['cpu-compile-smoke'])
    shell = sorted(p.name for p in (ROOT / 'scripts').glob('test_*.sh'))
    firmware = {'test_at_landmark_cmos.sh': 'LANDMARK_ORIGINAL',
        'test_at_landmark_dma.sh': 'LANDMARK_SKIP_PM', 'test_at_landmark_floppy.sh': 'LANDMARK_SKIP_PM',
        'test_at_landmark_peripherals.sh': 'LANDMARK_SKIP_PM',
        'test_at_phoenix_fdc_post.sh': 'PHOENIX', 'test_at_phoenix_pm87.sh': 'PHOENIX',
        'test_at_mrbios_restart.sh': 'MRBIOS'}
    for name in shell:
        if name == 'test_at_code_buffer_equivalence.sh':
            continue
        env = {}
        if name in firmware:
            env['AT_MRBIOS_ROM' if name.endswith('mrbios_restart.sh') else
                'AT_PHOENIX_ROM' if 'phoenix' in name else 'AT_SYSTEM_ROM'] = '{' + firmware[name] + '}'
        argv = ['bash', 'scripts/' + name]
        if name == 'test_at_stack_offset_arithmetic.sh':
            argv.append('{RUN}/stage-build/' + name.removesuffix('.sh'))
        add('root-shell-' + name.removesuffix('.sh'), argv, environment=env)
    covered = set()
    hacc = (ROOT / 'scripts/test_ascal_hacc_equivalence.py').exists()
    if hacc:
        add('test_ascal_hacc_equivalence', ['python3', '-B',
            'scripts/test_ascal_hacc_equivalence.py', '--output', '{RUN}/ascal-hacc'])
        covered.add('test_ascal_hacc_equivalence.py')
    for template in plan['execution_command_templates']:
        stage = template['stage']
        if stage in ('missing-event-arbitration-full', 'current-stack-offset-contract'):
            continue
        if stage == 'profile-compatibility-leaf':
            for unit in template['repeat']:
                add('profile-' + unit, [a.replace('{UNIT}', unit) for a in template['argv']],
                    keep_metadata=True)
        else:
            kw = {'depends': ['profile-' + unit for unit in plan['compatibility_units']]} if stage == 'profile-aggregate' else {}
            if stage == 'retained-fdc-directed': kw['depends'] = ['retained-fdc-proof']
            argv = list(template['argv'])
            if stage == 'test_p06_length_fault_boundary':
                argv.append('--dual')
            if stage == 'test_ascal_terminal_equivalence' and hacc:
                argv.extend(['--hacc-proof-receipt', '{RUN}/ascal-hacc/receipt.json'])
                kw['depends'] = ['test_ascal_hacc_equivalence']
            add(stage, argv, template['cwd'], **kw)
        for arg in template['argv']:
            if arg.startswith('scripts/test_') and arg.endswith('.py'):
                covered.add(Path(arg).name)
    covered.add('test_stack_offset_contract.py')  # Exact 12-case shell executes this contract itself.
    add('stack-offset-consumed-contract', ['python3', '-B',
        'scripts/test_stack_offset_consumed_contract.py',
        '--output', '{RUN}/stack-offset-consumed'])
    covered.add('test_stack_offset_consumed_contract.py')
    ordinary = ('test_check_at_net_delay.py', 'test_summarize_at_50mhz_timing.py',
                'test_at_scaler_luminance.py', 'test_xtsergey_at_keyboard.py')
    for name in ordinary:
        add(name.removesuffix('.py'), ['python3', '-B', 'scripts/' + name])
        covered.add(name)
    artifact = {
        'test_at_timing_closure_audit.py': ['{TIMING_NEGATIVE_RUN}', '{RUN}/timing-audit-negatives'],
        'test_at_video_register_placement.py': ['{VIDEO_INVENTORY}', '{RUN}/video-placement-negatives'],
        'test_supersoft_landmark_patch.py': ['{LANDMARK_ORIGINAL}', '{LANDMARK_SKIP_PM_V2}'],
    }
    for name, args in artifact.items():
        add(name.removesuffix('.py'), ['python3', '-B', 'scripts/' + name, *args],
            original_input_required=True)
        covered.add(name)
    python_registry = sorted(p.name for p in (ROOT / 'scripts').glob('test_*.py'))
    for name in sorted(set(python_registry) - covered):
        add('unconfigured-' + name.removesuffix('.py'), [], unresolved='Current Python gate requires explicit CLI classification')
    add('distributed-rom-check', ['python3', '-B', 'scripts/build_event_diag_rom.py', '--check'])
    add('pit-refresh-directed', ['bash', 'tools/perf01/test_pit_refresh.sh', '{FROZEN}', '{RUN}/pit-refresh-directed'])
    add('posted-machine', ['python3', '-B', 'tools/perf01/test_posted_machine.py',
        '{FROZEN}', '{RUN}/posted-machine', '--pit-refresh'])
    add('distributed-posted-rom', ['python3', '-B', 'tools/perf01/test_distributed_pit_diag.py', '{RUN}/posted-machine'],
        depends=['posted-machine'])
    ids = [s['id'] for s in stages]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate stage IDs: ' + repr(sorted(n for n in set(ids) if ids.count(n) > 1)))
    for s in stages:
        if s.get('corpus_full'):
            s['timeout_seconds'] = None  # Preserve workload; no short timeout for 1.39M cases.
        placeholders = set(re.findall(r'\{([A-Z_0-9]+)\}',
            ' '.join(s['argv'] + [s['cwd']] + list(s.get('environment', {}).values()))))
        s['required_placeholders'] = sorted(placeholders - {'RUN', 'FROZEN'})
    inputs = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [OWN / 'plan.json', Path(__file__), ROOT / 'tools/perf01/run_full_regression.py',
              ROOT / 'vendor/spk286/scripts/test_units.sh', *sorted((ROOT / 'scripts').glob('test_*.py')),
              *sorted((ROOT / 'scripts').glob('test_*.sh'))]}
    result = {'schema': 1, 'status': 'PREPARED_NOT_EXECUTED', 'stages': stages,
        'input_registry_sha256': inputs, 'registered_cpu_units': units, 'cpu_unit_supplement': supplement,
        'expected_cpu_icarus': len(units) + len(supplement), 'expected_cpu_verilator': len(units) + len(supplement) - 1,
        'registered_root_shell': shell, 'registered_root_python': python_registry,
        'excluded_historical': {'test_at_code_buffer_equivalence.sh': 'Historical Git-counterfactual; production capacity/coherence and integration run'},
        'coverage_alias': {'test_stack_offset_contract.py': 'test_at_stack_offset_arithmetic.sh: fresh raw/timed SAT + unchanged 12 dual cases'},
        'physical_required': plan['physical_required'], 'profile_expected': plan['compatibility_expected'],
        'mutation_families': plan['mutation_audit_families'], 'live_profile_latency_cases': 192,
        'entry': 'Exact RBF timing-open functional regression explicitly requested on 2026-10-06; global HDMI setup -0.063 ns remains open; all performance options on',
        'resource_policy': {**plan['resource_policy'], 'all_temp_and_objects': 'owned D: run root', 'stage_order': 'sequential'},
        'no_execution_performed': True}
    ast.parse(Path(__file__).read_text())
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('STAGE_MANIFEST_PREPARED', len(stages), len(units), len(supplement))


if __name__ == '__main__':
    main()
