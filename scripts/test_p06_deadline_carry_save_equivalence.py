#!/usr/bin/env python3
"""Prove fused deadline arithmetic and all scheduler state against production.

The actual generator's budget functions and selection expressions bind the
carry-save lane contract. Symbolic metadata includes every ten-bit base/setup/
iteration value, every prefix/EA field, events, late validity, freeze, CPU/READ
boundaries, and all scheduler controls. No architectural or cycle oracle changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from build_p06_profile_cpu import CONNECTION

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / 'rtl/spk286_timing/spk286_instruction_schedule.sv'
REFERENCE = 'a73ab7bc4be304a94ea2270b139c8980cf3d11b2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def budget_function(name):
    marker = '    function automatic logic '
    start = CONNECTION.index(name + '(')
    start = CONNECTION.rfind(marker, 0, start)
    end = CONNECTION.index('    endfunction', start) + len('    endfunction')
    return CONNECTION[start:end]


def expose_state(text):
    anchor = '    output logic implementation_extension\n'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor.rstrip('\n') + ',\n    output wire [36:0] proof_state\n')
    return text.replace('endmodule',
        '    assign proof_state = {active_q, body_q, pending_q, qualified_q, frozen_q,\n'
        '        admission_window_q, elapsed_q, base_q, extra_q, implementation_extension};\nendmodule')


def prove(out, label, sources, top, sequential=False, arbitrary_state=False, reject=False):
    script = out / (label + '.ys')
    temporal = (' -set-assumes -tempinduct -seq 2 -maxsteps 5 -set-init-zero '
                '-set-at 1 reset 1') if sequential else ''
    if arbitrary_state:
        temporal = ' -set-assumes -seq 1 -set-init-def -set-def-inputs'
    script.write_text('read_verilog -formal -sv ' + ' '.join(map(str, sources)) + '\n'
        f'prep -top {top} -flatten\nopt\n'
        f'sat -verify -prove-asserts{temporal} -timeout 60\n', newline='\n')
    run = subprocess.run(['yosys', '-Q', '-s', str(script)], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    log = run.stdout.decode()
    (out / (label + '.log')).write_bytes(run.stdout)
    if reject:
        assert run.returncode and 'proof did fail' in log and 'time out' not in log, label
    else:
        marker = 'Induction step proven: SUCCESS!' if sequential else 'SAT proof finished - no model found: SUCCESS!'
        assert run.returncode == 0 and marker in log, label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True, exist_ok=False)
    inputs = [SCHEDULE, ROOT / 'scripts/build_p06_profile_cpu.py', Path(__file__).resolve()]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    for binding in (
        "spk286_instruction_schedule #(.EXECUTION_METADATA_CARRY_SAVE(1'b1)) profile_schedule (",
        '.execution_metadata_sum_bits(profile_execution_metadata_carry_save[23:12]),',
        '.execution_metadata_carry_bits(profile_execution_metadata_carry_save[11:0]),',
    ):
        assert CONNECTION.count(binding) == 1, binding
    functions = budget_function('profile_metadata_budget') + '\n' + budget_function('profile_metadata_budget_carry_save')
    selection_start = CONNECTION.index('    assign profile_execution_metadata_clocks =')
    selection_end = CONNECTION.index('    // Odd corrections', selection_start)
    selection = CONNECTION[selection_start:selection_end]
    metadata_ports = '''
    input profile_delivery_metadata, profile_execution_repeated, profile_repeat_nonempty_q,
    input [9:0] profile_execution_base, profile_execution_repeat_setup,
    input [9:0] profile_execution_repeat_iteration, profile_event_base,
    input [2:0] profile_execution_ea,
    input [3:0] profile_prefix_count_q'''
    metadata_wires = '''
    wire [9:0] profile_execution_metadata_clocks;
    wire [23:0] profile_execution_metadata_carry_save;
'''
    context = 'module budget_miter (' + metadata_ports + ');\n' + metadata_wires + functions + selection + '''
    wire [12:0] reconstructed = {1'b0, profile_execution_metadata_carry_save[23:12]} +
                                 {profile_execution_metadata_carry_save[11:0], 1'b0};
    wire [3:0] rep_prefixes = profile_prefix_count_q == 0 ? 0 : profile_prefix_count_q - 4'd1;
    // Independent wide arithmetic oracle, not the candidate compressor.
    wire [12:0] ordinary_total = {3'd0, profile_execution_base} +
                                {10'd0, profile_execution_ea} +
                                {8'd0, profile_prefix_count_q, 1'b0};
    wire [12:0] repeated_total = {3'd0, profile_execution_repeat_setup} +
        (profile_repeat_nonempty_q ? {3'd0, profile_execution_repeat_iteration} : 13'd0) +
        {8'd0, rep_prefixes, 1'b0};
    wire [12:0] independent_total = profile_delivery_metadata ? {3'd0, profile_event_base} :
        profile_execution_repeated ? repeated_total : ordinary_total;
    always @* begin
        assert(reconstructed == independent_total);
        assert(reconstructed <= 13'd2076);
        assert(profile_execution_metadata_clocks ==
            (independent_total > 13'd1023 ? 10'd1023 : independent_total[9:0]));
    end
endmodule
'''
    budget = out / 'budget-miter.sv'
    budget.write_text(context, newline='\n')
    prove(out, 'budget', [budget], 'budget_miter')
    bad_budget = out / 'budget-mutant.sv'
    assert context.count('profile_metadata_budget_carry_save = {sum_bits, carry_bits};') == 1
    bad_budget.write_text(context.replace('profile_metadata_budget_carry_save = {sum_bits, carry_bits};',
        "profile_metadata_budget_carry_save = {sum_bits ^ 12'd1, carry_bits};"), newline='\n')
    prove(out, 'budget-mutant', [bad_budget], 'budget_miter', reject=True)

    raw = subprocess.check_output(['git', 'show', f'{REFERENCE}:rtl/spk286_timing/spk286_instruction_schedule.sv'], cwd=ROOT)
    reference_sha = hashlib.sha256(raw).hexdigest()
    (out / 'reference-original.sv').write_bytes(raw)
    reference = out / 'reference.sv'
    reference.write_text(expose_state(raw.decode()).replace('SPK286_INSTRUCTION_SCHEDULE_SV', 'REFERENCE_SCHEDULE_SV')
        .replace('module spk286_instruction_schedule (', 'module reference_schedule ('), newline='\n')
    candidate = out / 'candidate.sv'
    candidate.write_text(expose_state(SCHEDULE.read_text()), newline='\n')
    outputs = ['active', 'body_active', 'retire_pending', 'head_permit', 'deadline_ready', 'retire_fire',
               'elapsed_clocks', 'scheduled_clocks', 'implementation_extension', 'proof_state']
    widths = [1, 1, 1, 1, 1, 1, 10, 10, 1, 37]
    wires = '\n'.join(f'wire [{width-1}:0] {tag}_{name};'
                     for tag in ('carry', 'legacy', 'reference') for name, width in zip(outputs, widths))
    def output_pins(tag):
        return ','.join(f'.{name}({tag}_{name})' for name in outputs)
    miter = '''module schedule_miter (
    input clk, reset, historical_enable, cpu_boundary, cancel, preserve_cancel,
    input start_interval, start_body, metadata_valid, metadata_freeze,
    input execution_metadata_valid, execution_read_wait_event,
    input [9:0] metadata_clocks,
    input target_length_ready, read_wait_event, alignment_event,
    input [3:0] target_length_clocks,
    input functional_retired, repeat_checkpoint,
    input [9:0] repeat_next_clocks,
''' + metadata_ports + '\n);\n' + metadata_wires + functions + selection + wires + '''
    wire [9:0] execution_metadata_clocks = profile_execution_metadata_clocks;
    wire [11:0] execution_metadata_sum_bits = profile_execution_metadata_carry_save[23:12];
    wire [11:0] execution_metadata_carry_bits = profile_execution_metadata_carry_save[11:0];
''' + 'spk286_instruction_schedule #(.EXECUTION_METADATA_CARRY_SAVE(1)) carry(' + output_pins('carry') + ',.*);\n' + \
    'spk286_instruction_schedule legacy(' + output_pins('legacy') + ',.*);\n' + \
    'reference_schedule reference(' + output_pins('reference') + ',.*);\n' + \
    'always @* begin\n' + '\n'.join(
        f'assert({tag}_{name} == reference_{name});' for tag in ('carry', 'legacy') for name in outputs) + '\nend\nendmodule\n'
    miter_path = out / 'schedule-miter.sv'
    miter_path.write_text(miter, newline='\n')
    prove(out, 'schedule', [candidate, reference, miter_path], 'schedule_miter', sequential=True)
    # Supplement induction with every possible equal retained state, including
    # age1023 and saturated extra_q, without waiting1023 symbolic cycles.
    arbitrary_miter = out / 'schedule-arbitrary-state-miter.sv'
    arbitrary_miter.write_text(miter.replace('always @* begin\n',
        'always @* begin\nassume(carry_proof_state == reference_proof_state);\n'
        'assume(legacy_proof_state == reference_proof_state);\n'), newline='\n')
    prove(out, 'schedule-arbitrary-state', [candidate, reference, arbitrary_miter],
        'schedule_miter', arbitrary_state=True)
    bad_schedule = out / 'candidate-mutant.sv'
    candidate_text = candidate.read_text()
    assert candidate_text.count('execution_difference[12] ||') == 1
    bad_schedule.write_text(candidate_text.replace('execution_difference[12] ||',
        '!execution_difference[12] ||'), newline='\n')
    prove(out, 'schedule-mutant', [bad_schedule, reference, miter_path], 'schedule_miter', sequential=True, reject=True)
    bad_saturation = out / 'candidate-saturation-mutant.sv'
    assert candidate_text.count('(execution_elapsed_saturated ||') == 1
    bad_saturation.write_text(candidate_text.replace('(execution_elapsed_saturated ||', '('), newline='\n')
    prove(out, 'schedule-saturation-mutant', [bad_saturation, reference, arbitrary_miter],
        'schedule_miter', arbitrary_state=True, reject=True)
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    receipt = {
        'status': 'DEADLINE_CARRY_SAVE_EQUIVALENCE_PASS',
        'sources_sha256': before, 'reference_revision': REFERENCE, 'reference_sha256': reference_sha,
        'budget_contract': 'Actual production generator functions and event selection; independent full-width sum; bound<=2076 and exact saturation proved for every symbolic base/setup/iteration/EA/prefix/REP/event input',
        'scheduler': 'All public outputs and all 37 retained state bits proved by induction in BOTH legacy and carry-save modes',
        'arbitrary_retained_state': 'One-step proof from every equal37bit retained state additionally covers age1022/1023, saturated alignment and any qualified/frozen/context combination',
        'assumptions': 'Zero initialization and reset at step1 only; all metadata, late validity/freeze/outcomes and scheduler controls arbitrary thereafter',
        'signed_compare_range': 'total-age-1 in -1024..3113; 13-bit sign is exact; productive boundary permits zero; original age1023 saturation override retained',
        'negative_controls': ['Corrupted carry-save budget rejected', 'Inverted deadline sign rejected', 'Missing age-saturation override rejected'],
        'new_state_bits': 0,
        'artifacts_sha256': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    print('DEADLINE_CARRY_SAVE_EQUIVALENCE_PASS', flush=True)


if __name__ == '__main__':
    main()
