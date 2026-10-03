#!/usr/bin/env python3
"""Prove actual queue RTL transition with only the head representation changed."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

SOURCE = 'vendor/spk286/rtl/spk286_prefetch_queue.sv'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def run(case, log_name, command, must_pass=True):
    with (case/log_name).open('w') as log:
        result = subprocess.run(['timeout','300','yosys','-p',command], cwd=case,
            stdout=log, stderr=subprocess.STDOUT)
    if must_pass:
        assert result.returncode == 0, (log_name, result.returncode)
    return result.returncode

def materialize(case, before, after):
    for label, source in [('gold',before),('gate',after)]:
        source = source.replace('module spk286_prefetch_queue (','module queue_'+label+' (',1)
        (case/(label+'.sv')).write_text(source)
    run(case,'elaboration.log','read_verilog -sv -DSYNTHESIS gold.sv gate.sv; '
        'hierarchy -check; proc; memory; opt -full -keepdc; dffunmap; opt_clean; check -assert; '
        'write_json prepared.json; write_rtlil prepared.il')

def make(case):
    modules = json.loads((case/'prepared.json').read_text())['modules']
    rtlil = (case/'prepared.il').read_text()
    states = {}
    descriptors = {}
    for label in ('gold','gate'):
        module=modules['queue_'+label]
        mi=rtlil.index('module \\queue_'+label+'\n')
        me=rtlil.index('\nend\n',mi)
        body=rtlil[mi:me]
        port_number=max(int(p) for p in re.findall(r'\b(?:input|output) (\d+) ',body))
        extra=[]
        states[label]={}
        descriptors[label]={}
        for cellname,cell in module['cells'].items():
            if 'Q' not in cell['connections']:
                continue
            assert cell['type']=='$dff',cell['type']
            qbits=cell['connections']['Q']
            names=[name for name,n in module['netnames'].items()
                   if n['bits']==qbits and not name.startswith('$')]
            assert names,(label,cellname,qbits)
            actual_name=next((n for n in names if n.endswith('_q')),sorted(names)[0])
            name=actual_name.replace('[','_').replace(']','')
            assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name),name
            assert name not in states[label]
            states[label][name]=len(qbits)
            descriptors[label][name]=dict(actual_name=actual_name,type=cell['type'],
                parameters=cell['parameters'],width=len(qbits))
            header='  cell '+cell['type']+' '+('\\' if not cellname.startswith('$') else '')+cellname+'\n'
            start=body.index(header)
            while start>0:
                previous=body.rfind('\n',0,start-1)+1
                if not body[previous:start].startswith('  attribute '): break
                start=previous
            finish=body.index('  end\n',start)+len('  end\n')
            block=body[start:finish]
            connections={p:re.search(r'^    connect \\'+p+r' (.+)$',block,re.M).group(1)
                         for p in cell['connections']}
            assert connections['CLK']=='\\clk'
            assert int(cell['parameters']['CLK_POLARITY'],2)==1
            port_number+=1
            extra.append(f'  wire width {len(qbits)} input {port_number} \\previous_{name}\n')
            port_number+=1
            extra.append(f'  wire width {len(qbits)} output {port_number} \\next_{name}\n')
            extra.append(f'  connect {connections["Q"]} \\previous_{name}\n')
            extra.append(f'  connect \\next_{name} {connections["D"]}\n')
            body=body[:start]+body[finish:]
        body=body.rstrip()+'\n'+''.join(extra)
        rtlil=rtlil[:mi]+body+rtlil[me:]
    common={n:w for n,w in states['gold'].items() if n!='head_q'}
    assert common=={n:w for n,w in states['gate'].items() if n!='head_onehot_q'},states
    assert common==dict(tail_q=3,count_q=4,**{'storage_q_'+str(i):8 for i in range(6)}),common
    assert states['gold']['head_q']==3 and states['gate']['head_onehot_q']==6
    for name in common:
        assert descriptors['gold'][name]==descriptors['gate'][name]
    (case/'states.json').write_text(json.dumps(states,indent=2)+'\n')
    (case/'state-descriptors.json').write_text(json.dumps(descriptors,indent=2)+'\n')
    (case/'one-step.il').write_text(rtlil)
    run(case,'one-step-elaboration.log','read_rtlil one-step.il; check -assert; '
        'write_json one-step.json; write_verilog one-step.v')
    modules=json.loads((case/'one-step.json').read_text())['modules']
    original={'clk','reset','flush','fill_valid','fill_data','fill_count','fill_ready',
              'consume_valid','consume_data','consume_ready','count'}
    for name in original:
        a=modules['queue_gold']['ports'][name]
        b=modules['queue_gate']['ports'][name]
        assert a['direction']==b['direction'] and len(a['bits'])==len(b['bits'])
    inputs,wires,connections,comparisons,next_comparisons=[],[],{'gold':[],'gate':[]},[],[]
    seen=set()
    for label in ('gold','gate'):
        for name,port in modules['queue_'+label]['ports'].items():
            width=len(port['bits'])
            shape='' if width==1 else f'[{width-1}:0] '
            if port['direction']=='input':
                if name not in seen:
                    inputs.append(f'    input wire {shape}{name}')
                    seen.add(name)
                connections[label].append(f'.{name}({name})')
            else:
                wires.append(f'    wire {shape}{name}_{label};')
                connections[label].append(f'.{name}({name}_{label})')
                if label=='gold':
                    if name.startswith('next_'):
                        if name!='next_head_q':
                            next_comparisons.append(f'({name}_gold === {name}_gate)')
                    else:
                        assert name in original,name
                        comparisons.append(f'({name}_gold === {name}_gate)')
    assert len(comparisons)==4,comparisons
    assert len(next_comparisons)==8,next_comparisons
    wrapper='module invariant(\n'+',\n'.join(inputs)+',\n    output wire step_ok, reset_ok, flush_ok\n);\n'
    wrapper+='\n'.join(wires)+'\n'
    for label in ('gold','gate'):
        wrapper+=f'    queue_{label} u_{label}(\n        '+',\n        '.join(connections[label])+'\n    );\n'
    wrapper+="    wire relation = (previous_head_q < 3'd6) && (previous_head_onehot_q == (6'b000001 << previous_head_q));\n"
    wrapper+='    wire outputs_equal = '+' &&\n        '.join(comparisons)+';\n'
    wrapper+='    wire common_next_equal = '+' &&\n        '.join(next_comparisons)+';\n'
    wrapper+="    wire head_next_relation = (next_head_q_gold < 3'd6) && (next_head_onehot_q_gate == (6'b000001 << next_head_q_gold));\n"
    wrapper+='    wire next_relation = common_next_equal && head_next_relation;\n'
    wrapper+='    assign step_ok = !relation || (outputs_equal && next_relation);\n'
    wrapper+="    assign reset_ok = !reset || (next_relation && next_head_q_gold==0 && next_head_onehot_q_gate==1 && next_tail_q_gold==0 && next_count_q_gold==0);\n"
    wrapper+="    assign flush_ok = !flush || (next_relation && next_head_q_gold==0 && next_head_onehot_q_gate==1 && next_tail_q_gold==0 && next_count_q_gold==0);\n"
    wrapper+='endmodule\n'
    (case/'invariant.sv').write_text(wrapper)
    (case/'comparisons.json').write_text(json.dumps(dict(public=comparisons,next_state=next_comparisons),indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_root',type=Path)
    parser.add_argument('--candidate-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    reference=args.reference_root.resolve()/SOURCE
    candidate=args.candidate_file.resolve()
    frozen={p:p.read_bytes() for p in (reference,candidate,Path(__file__))}
    before=frozen[reference].decode().replace('\r\n','\n')
    after=frozen[candidate].decode().replace('\r\n','\n')
    # Exact allowed replacement set is part of this tool, not supplied by a caller.
    edits=[('    logic [2:0] head_q, tail_q;','    logic [5:0] head_onehot_q;\n    logic [2:0] tail_q;'),
        ('    // The pointer resets to zero and increment_pointer wraps at five.','    // The one-hot head resets to byte zero and rotates at consumption.'),
        ("    assign consume_head_select = 6'b000001 << head_q;",'    assign consume_head_select = head_onehot_q;'),
        ("            head_q <= 3'd0;","            head_onehot_q <= 6'b000001;"),
        ('                head_q <= increment_pointer(head_q);','                head_onehot_q <= {head_onehot_q[4:0], head_onehot_q[5]};')]
    expected=before
    for old,new in edits:
        assert expected.count(old)==1
        expected=expected.replace(old,new,1)
    assert after==expected,'Unexpected source delta'
    out=args.output.resolve()
    out.mkdir(exist_ok=False)
    # Swap two consumed bytes so the negative control retains all six actual
    # storage registers; neither architectural state nor proof scope is dropped.
    mutant=after.replace('& storage_q[0])','& storage_q[MUTANT])',1)
    mutant=mutant.replace('& storage_q[1])','& storage_q[0])',1)
    mutant=mutant.replace('& storage_q[MUTANT])','& storage_q[1])',1)
    assert mutant!=after
    command=('read_verilog -sv one-step.v invariant.sv; hierarchy -top invariant; '
        'proc; flatten; wreduce; opt -full -keepdc; check -assert; '
        'sat -verify -set-def-inputs -prove step_ok 1 -show relation -show outputs_equal '
        '-show common_next_equal -show head_next_relation -show reset -show flush '
        '-show previous_head_q -show previous_head_onehot_q -dump_json counterexample.json')
    for name,source in [('positive',after),('negative',mutant)]:
        case=out/name
        case.mkdir()
        materialize(case,before,source)
        make(case)
        result=run(case,'step-proof.log',command,must_pass=name=='positive')
        if name=='positive':
            assert 'SUCCESS!' in (case/'step-proof.log').read_text()
            for prop in ('reset_ok','flush_ok'):
                run(case,prop+'-proof.log',command.replace('-prove step_ok 1','-prove '+prop+' 1'))
                assert 'SUCCESS!' in (case/(prop+'-proof.log')).read_text()
        else:
            assert result not in (0,124)
            assert 'proof did fail' in (case/'step-proof.log').read_text()
            signals={s['name']:s for s in json.loads((case/'counterexample.json').read_text())['signal']}
            assert signals['relation']['wave'].startswith('1')
            assert signals['outputs_equal']['wave'].startswith('0')
    for p,raw in frozen.items():
        assert p.read_bytes()==raw,'Input changed: '+str(p)
    states=json.loads((out/'positive/states.json').read_text())
    receipt=dict(status='PREFETCH_ONEHOT_RELATIONAL_EQUIVALENCE_PASS',
        reference_sha256=sha(reference),candidate_sha256=sha(candidate),proof_script_sha256=sha(Path(__file__)),
        state_bits={k:sum(v.values()) for k,v in states.items()},state_registers={k:len(v) for k,v in states.items()},
        reference_path=str(reference),candidate_path=str(candidate),
        source_guard='Exact intrinsic five normalized replacements only: binary head declaration, explanatory comment, selection alias, reset and consume rotation. Caller cannot supply edits.',
        relation='head_gold<6 and head_onehot==(1<<head_gold). All tail/count/storage current bits are common arbitrary inputs.',
        transition='All four public outputs including consume_data when empty compared without masks; complete next state and legal head relation preserved for arbitrary defined inputs and common storage.',
        reset_flush_base='Each independently forces head=0/onehot=1, tail=0 and count=0 while retaining identical arbitrary storage.',
        assumptions='No fill_count or external protocol assumptions. No occupancy constraints. Common initial storage is the equivalence coupling; illegal pre-reset binary/one-hot head states are outside the relation.',
        negative_control='Actual wrong storage byte selection rejected with relation true and public outputs differing.',
        limitations='Two-state/defined-input sampled transitions; no power-on head equivalence before reset, 4-state X semantics, STA, hardware validation or full regression claim.',
        artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'])
if __name__=='__main__':main()
