#!/usr/bin/env python3
"""Prove the execution metadata lane and scheduler against frozen production.

Metadata expressions are extracted from the actual generator. Scheduler state
and all public outputs are proved by induction under the lane equality proved
by the first gate. No timing or architectural expected values are changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from build_p06_profile_cpu import CONNECTION

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT/'rtl/spk286_timing/spk286_instruction_schedule.sv'
POLICY = ROOT/'rtl/spk286_timing/spk286_instruction_timing.sv'
PKG = ROOT/'vendor/spk286/microcode/generated/spk286_microcode_pkg.sv'
REFERENCE = 'd30d476'
REFERENCE_SHA = '40cf0ccb6742cc6f24809cbe3fb4323c228296a3971452f9a773087fb2790c93'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, log, reject=False):
    result = subprocess.run(list(map(str,command)),cwd=ROOT,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    log.write_text(result.stdout,newline='\n')
    if reject:
        assert result.returncode != 0 and 'proof did fail' in result.stdout
        assert 'time out' not in result.stdout
    else:
        assert result.returncode == 0, log
    return result.stdout

def expose_state(text):
    port='    output logic implementation_extension\n'
    assert text.count(port)==1
    text=text.replace(port,port.rstrip('\n')+',\n    output wire [36:0] proof_state\n')
    return text.replace('endmodule',
        '    assign proof_state = {active_q, body_q, pending_q, qualified_q, frozen_q,\n'
        '        admission_window_q, elapsed_q, base_q, extra_q, implementation_extension};\nendmodule')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve()
    assert out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True,exist_ok=False)
    inputs=[SCHEDULE,POLICY,PKG,ROOT/'scripts/build_p06_profile_cpu.py',Path(__file__).resolve()]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    constants='\n'.join(line for line in PKG.read_text().splitlines() if 'localparam' in line)
    flat=POLICY.read_text().replace('spk286_microcode_pkg::MC_ADDR_WIDTH','10')
    flat=flat.replace('import spk286_microcode_pkg::*;',constants)
    policy=out/'policy-constants-expanded.sv';policy.write_text(flat,newline='\n')
    selection=CONNECTION[CONNECTION.index('    wire profile_delivery_metadata'):CONNECTION.index('    // Odd corrections')]
    original_sum=CONNECTION[CONNECTION.index('    assign profile_metadata_clocks'):CONNECTION.index('    assign profile_preserve_cancel')]
    selection=selection.replace('spk286_microcode_pkg::','')
    context='''module context_miter (
    input event_dispatch, event_active, event_software, micro_active, profile_body_active,
    input extended_opcode_active, prefix_accept, operand_context_valid,
    input profile_branch_known_q, profile_branch_taken_q, profile_count_known_q,
    input profile_repeat_nonempty_q,
    input [7:0] queue_consume_data, opcode_q,
    input [9:0] decode_entry, micro_entry,
    input [3:0] protected_msw, profile_prefix_count_q,
    input [1:0] current_cpl, repeat_kind, operand_mode,
    input [2:0] operand_reg, operand_rm,
    input [4:0] profile_count_q,
    input [31:0] register_state
);
    logic profile_metadata_valid, profile_family_estimated;
    logic profile_requires_modrm, profile_requires_outcome, profile_requires_count;
    logic profile_requires_target_length, profile_metadata_read_wait;
    logic [9:0] profile_base_clocks, profile_repeat_setup, profile_repeat_iteration;
    logic [2:0] profile_ea_clocks;
    logic [11:0] profile_metadata_sum;
    logic [9:0] profile_metadata_clocks;
    logic profile_execution_metadata_valid, profile_execution_metadata_read_wait;
    logic [9:0] profile_execution_base, profile_execution_repeat_setup;
    logic [9:0] profile_execution_repeat_iteration, profile_execution_metadata_clocks;
    logic [2:0] profile_execution_ea;
    logic [11:0] profile_execution_metadata_sum;
    logic [4:0] profile_execution_unused;
    logic profile_instruction_metadata_valid, profile_instruction_metadata_read_wait;
    logic profile_event_metadata_valid, profile_event_metadata_read_wait;
    logic [9:0] profile_event_base, profile_event_repeat_setup, profile_event_repeat_iteration;
    logic [4:0] profile_event_unused;
    logic [2:0] profile_event_ea;
'''+constants+'\n'+selection+original_sum+'''
    always @* if (profile_body_active) begin
        assert(profile_execution_metadata_valid == profile_metadata_valid);
        assert(profile_execution_metadata_clocks == profile_metadata_clocks);
        assert(profile_execution_metadata_read_wait == profile_metadata_read_wait);
    end
endmodule
'''
    wrapper=out/'context-miter.sv';wrapper.write_text(context,newline='\n')
    script=out/'context.ys'
    script.write_text(f'read_verilog -formal -sv {policy} {wrapper}\nprep -top context_miter -flatten\nopt\n'
        'sat -verify -prove-asserts -timeout 60\n',newline='\n')
    log=run(['yosys','-Q','-s',script],out/'context.log')
    assert 'SAT proof finished - no model found: SUCCESS!' in log
    mutant=out/'context-mutant.sv'
    assert context.count("profile_execution_opcode = opcode_q;")==1
    mutant.write_text(context.replace("profile_execution_opcode = opcode_q;",
        "profile_execution_opcode = queue_consume_data;"),newline='\n')
    script_mutant=out/'context-mutant.ys'
    script_mutant.write_text(script.read_text().replace(str(wrapper),str(mutant)),newline='\n')
    run(['yosys','-Q','-s',script_mutant],out/'context-mutant.log',reject=True)

    raw=subprocess.check_output(['git','show',f'{REFERENCE}:rtl/spk286_timing/spk286_instruction_schedule.sv'],cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest()==REFERENCE_SHA
    (out/'reference-original.sv').write_bytes(raw)
    reference=out/'reference.sv'
    reference.write_text(expose_state(raw.decode()).replace('SPK286_INSTRUCTION_SCHEDULE_SV','REFERENCE_SCHEDULE_SV')
        .replace('module spk286_instruction_schedule (','module reference_schedule ('),newline='\n')
    candidate=out/'candidate.sv';candidate.write_text(expose_state(SCHEDULE.read_text()),newline='\n')
    miter=out/'schedule-miter.sv'
    ports=['active','body_active','retire_pending','head_permit','deadline_ready','retire_fire',
           'elapsed_clocks','scheduled_clocks','implementation_extension','proof_state']
    widths=[1,1,1,1,1,1,10,10,1,37]
    wires='\n'.join(f'wire [{w-1}:0] a_{n}, b_{n};' for n,w in zip(ports,widths))
    outputs=lambda prefix: ','.join(f'.{n}({prefix}_{n})' for n in ports)
    assertions='\n'.join(f'assert(a_{n} == b_{n});' for n in ports)
    miter.write_text('''module schedule_miter (
    input clk, reset, historical_enable, cpu_boundary, cancel, preserve_cancel,
    input start_interval, start_body, metadata_valid, metadata_freeze,
    input execution_metadata_valid, execution_read_wait_event,
    input [9:0] metadata_clocks, execution_metadata_clocks,
    input target_length_ready, read_wait_event, alignment_event,
    input [3:0] target_length_clocks,
    input functional_retired, repeat_checkpoint,
    input [9:0] repeat_next_clocks
);
'''+wires+'\nspk286_instruction_schedule a('+outputs('a')+',.*);\n'
        +'reference_schedule b('+outputs('b')+',.*);\n'
        +'''always @* begin
    if (a_body_active) begin
        assume(execution_metadata_valid == metadata_valid);
        assume(execution_metadata_clocks == metadata_clocks);
        assume(execution_read_wait_event == read_wait_event);
    end
'''+assertions+'\nend\nendmodule\n',newline='\n')
    script=out/'schedule.ys'
    script.write_text(f'read_verilog -formal -sv {candidate} {reference} {miter}\n'
        'prep -top schedule_miter -flatten\nopt\n'
        'sat -verify -prove-asserts -set-assumes -tempinduct -seq 2 -maxsteps 4 '
        '-set-init-zero -set-at 1 reset 1 -timeout 60\n',newline='\n')
    log=run(['yosys','-Q','-s',script],out/'schedule.log')
    assert 'Induction step proven: SUCCESS!' in log
    assert before=={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    receipt={'status':'EXECUTION_DEADLINE_EQUIVALENCE_PASS','sources_sha256':before,
        'reference_revision':REFERENCE,'reference_sha256':REFERENCE_SHA,
        'context':'Actual generator metadata expressions, all symbolic inputs; execution valid/clocks/READ policy equal whenever body_active',
        'scheduler':'Inductive exact retained state and all public outputs; arbitrary inputs; zero initialization and reset at step 1',
        'assumptions':'Lane equality during body_active, established by the context gate; otherwise lanes arbitrary',
        'negative_control':'Using next queue opcode in execution lane rejected with counterexample',
        'artifacts_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    print('EXECUTION_DEADLINE_EQUIVALENCE_PASS',flush=True)

if __name__=='__main__':main()
