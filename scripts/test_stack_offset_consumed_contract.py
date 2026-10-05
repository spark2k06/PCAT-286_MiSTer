"""Prove current consumed stack addresses and preserve the historical flat contract.

The payload mux can differ while idle. All actual request/permission controls,
top address/protection/fault consumers and original operand outputs/two next
state bits are proved for arbitrary binary inputs, without assumptions. The
immutable pre-transform flat checker is replayed against the historical
producer; current idle differences are explicitly retained as counterexamples.
This is a coupled cone/interface proof, not full CPU induction or timing.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('p05_contract',ROOT/'scripts/test_p05_limit_equivalence.py')
P05=importlib.util.module_from_spec(spec); spec.loader.exec_module(P05)
flat_spec=importlib.util.spec_from_file_location('historical_flat_contract',ROOT/'scripts/test_stack_offset_contract.py')
FLAT=importlib.util.module_from_spec(flat_spec); flat_spec.loader.exec_module(FLAT)
SOURCE_PINS={
    'raw':('325f51e6a91ae9c309786c17da8c22aa3264b3084314008b43b7cc41fd44f6db',
           '8d41e0187bef3081728780e4683c9e312b1f4beb1f3c40a6244d465c32799710'),
    'timed':('19882c7b14c1dd8dde73ff97ead3e47a66ba394ef474713085b468d1ad735af4',
             '2b5ca85c5939dcce3984439f8d5d9c67d590f70ad99faaa08cf139d65a33a123'),
}

PNODES=('allowed copy_call_parameters read_frame_address call_gate_outer_required '
        'call_parameter_read call_parameter_write iret_outer_frame_operation iret_outer_required '
        'iret_outer_pop push_operation push_event_error push_transfer push_event_error_transfer '
        'call_gate_stack_switch_operation call_gate_stack_write pop_operation stack_request '
        'call_parameter_write_offset iret_parameter_bytes return_stack_pointer iret_outer_stack_offset '
        'stack_offset protected_call_stack_access protected_call_stack_address '
        'protected_call_stack_limit protected_call_stack_expand_down').split()
EXTRA=('parallel_system_cache_fault selected_segment_base segment_address loadall_fault_has_error system_fault_has_error '
       'fault_request fault_vector fault_error_valid fault_error_code').split()
DATA=('call_parameter_read_data_select','call_parameter_write_data_select',
      'iret_outer_data_select','frame_address_data_select')
COMMON_OUTPUTS=('stack_request protected_call_stack_access protected_call_stack_limit '
    'protected_call_stack_expand_down service_offset parallel_operand_within_limit '
    'parallel_system_cache_fault protected_access_fault protected_access_ss_fault '
    'selected_segment_index selected_segment_limit selected_segment_access selected_segment_base '
    'segment_address operand_physical_address fault_request fault_vector fault_error_valid fault_error_code').split()
OPERAND_OUTPUTS=('done unlimited_memory_done read_data blocked gpr_write_en gpr_write_byte '
    'gpr_write_index gpr_write_data memory_request memory_write memory_byte memory_address '
    'memory_write_data memory_response_ready timing_wait pending_next blocked_next').split()

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def actual(text,name):
    return P05.assignment(text,name)


def constants(text,packages):
    for package,name in set(re.findall(r'(spk286_\w+_pkg)::(\w+)',text)):
        source=packages[package]
        values=re.findall(r'\b'+name+r'\s*=\s*(\d+\s*\'[dDhHbBoO][0-9a-fA-F]+)\s*;',source)
        assert len(values)==1,('Package constant changed',package,name)
        text=re.sub(r'\b'+re.escape(package+'::'+name)+r'\b',values[0],text)
    return text


def private_candidate(source):
    old=actual(source,'stack_offset')
    assert old.count('call_parameter_read ?')==1 and old.count('call_parameter_write ?')==1
    new=old.replace('call_parameter_read ?','call_parameter_read_data_select ?')
    new=new.replace('call_parameter_write ?','call_parameter_write_data_select ?')
    new=new.replace('iret_outer_pop ?','iret_outer_data_select ?')
    new=new.replace('read_frame_address ?','frame_address_data_select ?')
    nl='\r\n' if '\r\n' in old else '\n'
    added='    logic '+', '.join(DATA)+';'+nl
    added+='    assign call_parameter_read_data_select = operation == spk286_microcode_pkg::MC_COPY_CALL_PARAMETERS &&'+nl
    added+='                                            call_gate_outer_required && call_parameter_active_q && call_parameter_phase_q == 2\'d0;'+nl
    added+='    assign call_parameter_write_data_select = operation == spk286_microcode_pkg::MC_COPY_CALL_PARAMETERS &&'+nl
    added+='                                             call_gate_outer_required && call_parameter_active_q && call_parameter_phase_q == 2\'d1;'+nl
    added+='    assign iret_outer_data_select = operation == spk286_microcode_pkg::MC_IRET_OUTER_FRAME &&'+nl
    added+='                                    iret_outer_required && iret_outer_phase_q < 2\'d2;'+nl
    added+='    assign frame_address_data_select = operation == spk286_microcode_pkg::MC_READ_STACK_ADDRESS_TMP0 && frame_address_valid_q;'+nl
    candidate=source.replace(old,added+new,1)
    assert candidate.replace(added+new,old,1)==source
    assert candidate.count(added)==1 and candidate.count(new)==1
    return candidate,{'old':old,'new':new,'added':added}


def reviewed_pair(installed,flavor):
    digest=hashlib.sha256(installed.encode()).hexdigest()
    old_pin,new_pin=SOURCE_PINS[flavor]
    assert digest in (old_pin,new_pin), ('Unreviewed full executor source',flavor,digest)
    if digest==old_pin:
        reference=installed;variant='reference'
    else:
        actual_offset=actual(installed,'stack_offset')
        reverse=actual_offset
        for old,new in zip(('call_parameter_read','call_parameter_write','iret_outer_pop','read_frame_address'),DATA):
            assert reverse.count(new+' ?')==1
            reverse=reverse.replace(new+' ?',old+' ?',1)
        blocks=re.findall(r'    logic call_parameter_read_data_select, call_parameter_write_data_select, iret_outer_data_select, frame_address_data_select;.*?'+re.escape(actual_offset),installed,re.S)
        assert len(blocks)==1, 'Reviewed DATA block changed'
        reference=installed.replace(blocks[0],reverse,1);variant='candidate'
    assert hashlib.sha256(reference.encode()).hexdigest()==old_pin
    candidate,delta=private_candidate(reference)
    assert hashlib.sha256(candidate.encode()).hexdigest()==new_pin
    assert candidate.replace(delta['added']+delta['new'],delta['old'],1)==reference
    assert installed==(reference if variant=='reference' else candidate)
    return reference,candidate,delta,variant


def historical_flat_inputs():
    archive=ROOT/FLAT.ARCHIVE;receipt_path=archive/'receipt.json';miter=archive/'miter.v'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['status']=='EXACT_STACK_OFFSET_EQUIVALENCE_PASS'
    assert receipt['reference']=='792f652a9712ed34738472869aaa9b8d78ad1d96'
    assert receipt['reference_source_sha256']==FLAT.ORIGINAL_REFERENCE_SHA256
    assert receipt['artifacts_sha256']['miter.v']==FLAT.ARCHIVE_MITER_SHA256
    paths=[receipt_path]
    for name,expected in receipt['artifacts_sha256'].items():
        assert Path(name).name==name and sha(archive/name)==expected
        paths.append(archive/name)
    assert sha(miter)==FLAT.ARCHIVE_MITER_SHA256
    matches=re.findall(r'(module offset_old\(.*?\nendmodule)',miter.read_text(),re.S)
    assert len(matches)==1
    return matches[0],paths


def port_expression(block,name):
    matches=list(re.finditer(r'\.'+name+r'\(',block));assert len(matches)==1,name
    start=matches[0].end();level=1
    for end in range(start,len(block)):
        level+=(block[end]=='(')-(block[end]==')')
        if level==0:return block[start:end]
    raise ValueError(name)


def model(top,producer,label,packages,*,include_frontier=None):
    base,_=P05.build(top)
    body=base.split(');\n',1)[1].split('\nwire reference = ',1)[0]
    widths=P05.types(top)
    producer_widths=P05.types(producer)
    assert re.search(r'input\s+logic\s+\[spk286_microcode_pkg::MC_WORD_WIDTH-1:0\]\s+operation\b',producer)
    assert re.search(r'MC_WORD_WIDTH\s*=\s*8\s*;',packages['spk286_microcode_pkg'])
    producer_widths['operation']=8
    nodes=PNODES+(['implementation_allowed'] if 'implementation_allowed' in producer_widths else [])
    data_nodes=list(DATA) if all(name in producer_widths for name in DATA) else []
    statements='\n'.join(actual(producer,n) for n in nodes+data_nodes)
    # Real host bindings, checked against the actual micro_executor instance.
    instance=re.search(r'    spk286_(?:profiled_)?micro_executor #\(.*?    \);',top,re.S).group(0)
    binding={name:port_expression(instance,name) for name in ('cancel','start','operation')}
    assert binding=={'cancel':'semantic_cancel','start':'service_start','operation':'micro_word'},binding
    if 'implementation_allowed' in nodes:
        binding['implementation_operation_valid']=port_expression(instance,'implementation_operation_valid')
        assert binding['implementation_operation_valid']=='profile_raw_operation_valid'
    for name,bound in binding.items():
        statements=re.sub(r'\b'+name+r'\b',bound,statements)
        producer_widths[bound]=producer_widths[name]
    all_widths={**widths,**producer_widths}
    for name in nodes+data_nodes:
        assert name in producer_widths,name
        body+='\nwire '+(f'[{producer_widths[name]-1}:0] ' if producer_widths[name]>1 else '')+name+';'
    body+='\n'+statements
    for name in EXTRA:
        assert name in widths,name
        body+='\nwire '+(f'[{widths[name]-1}:0] ' if widths[name]>1 else '')+name+';\n'+actual(top,name)
    physical=re.findall(r'(    always_comb begin\n        operand_physical_address = segment_address;.*?    end)',top,re.S)
    assert len(physical)==1
    body+='\nlogic [23:0] operand_physical_address;\n'+physical[0]
    for name in COMMON_OUTPUTS:
        assert name == 'operand_physical_address' or len(re.findall(r'\bassign\s+'+name+r'\s*=',body)) == 1, ('Observable lacks an actual source driver',name)
    body=constants(body,packages)
    internal=set(P05.NODES+P05.ARRAYS+nodes+data_nodes+EXTRA+['operand_physical_address'])
    local={'assign','wire','logic','function','automatic','input','endfunction','generate','for','begin','end','endgenerate',
        'always_comb','if','genvar','operand_cache_index','g_operand_cache_range','cache_limit','cache_expand_down',
        'protected_range_exceeded','offset_value','limit_value','expand_down','is_byte'}
    frontier=P05.identifiers(body)-internal-local
    assert all(name in all_widths for name in frontier),('Unbound actual input',sorted(frontier-set(all_widths)))
    if include_frontier is not None:
        # A negative control can remove a dependency, but must retain the
        # original typed port so both instances share the same arbitrary input.
        assert frontier <= include_frontier, ('Mutant introduced a new free input',frontier-include_frontier)
        assert all(name in all_widths for name in include_frontier)
        frontier=set(include_frontier)
    # No consumer observes raw idle stack_offset except the separate address
    # payload. Both valid qualifiers are ACTUAL producer assignments above.
    outputs={name:all_widths[name] for name in COMMON_OUTPUTS}
    outputs.update({'stack_offset':16,'protected_call_stack_address':24})
    ports=['input wire '+(f'[{all_widths[n]-1}:0] ' if all_widths[n]>1 else '')+n for n in sorted(frontier)]
    ports+=['output wire '+(f'[{bits-1}:0] ' if bits>1 else '')+'observed_'+n for n,bits in outputs.items()]
    observing='\n'.join('assign observed_'+n+' = '+n+';' for n in outputs)
    return 'module cone_'+label+'(\n'+',\n'.join(ports)+'\n);\n'+body+'\n'+observing+'\nendmodule\n',frontier,outputs,all_widths


def actual_operand_step(source):
    assert source.count('module spk286_operand #')==1 and source.count('always_ff')==1
    step=source.replace('module spk286_operand #','module operand_step #',1)
    anchor='    input  logic clk, reset, cancel,';assert step.count(anchor)==1
    step=step.replace(anchor,anchor+'\n    input logic pending_state, blocked_state,\n    output logic pending_next, blocked_next,',1)
    anchor='    logic pending_q, is_memory, allowed, within_limit;';assert step.count(anchor)==1
    step=step.replace(anchor,'    wire pending_q = pending_state;\n    assign blocked = blocked_state;\n    logic is_memory, allowed, within_limit;',1)
    ff=re.findall(r'    always_ff @\(posedge clk\) begin(.*?)\n    end\nendmodule',step,re.S)
    assert len(ff)==1
    assert set(re.findall(r'(\w+)\s*<=',ff[0]))=={'pending_q','blocked'}
    body=re.sub(r'\bpending_q\s*<=','pending_next =',ff[0])
    body=re.sub(r'\bblocked\s*<=','blocked_next =',body)
    replacement='    always @* begin\n        pending_next = pending_state; blocked_next = blocked_state;'+body+'\n    end\nendmodule'
    old='    always_ff @(posedge clk) begin'+ff[0]+'\n    end\nendmodule'
    assert step.count(old)==1
    return step.replace(old,replacement,1)


def wrapper(top,models,frontier,outputs,widths,operand,*,flat=False):
    block=re.findall(r'    spk286_operand #\(.*?    \);',top,re.S);assert len(block)==1
    block=block[0]
    parameter=re.findall(r'\.USE_PARALLEL_RANGE\((.*?)\)',block);assert parameter==["1'b1"]
    inputs=('clk reset cancel request_valid request_byte request_write request_check select_rm write_data '
            'register_state reg_index rm_index register_direct physical_address offset segment_limit '
            'segment_expand_down parallel_within_limit memory_request_ready memory_response_valid memory_read_data').split()
    input_names=set()
    for names in re.findall(r'\binput\s+logic\s*(?:\[[^]\n]+\])?\s*'
            r'([A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)',operand.split(');',1)[0]):
        input_names.update(re.split(r'\s*,\s*',names))
    assert input_names-set(('pending_state','blocked_state'))==set(inputs), ('Missing actual operand input',input_names^set(inputs))
    actual_bindings={n:port_expression(block,n) for n in inputs}
    operand_types=P05.types(operand)
    extra=set()
    for expression in actual_bindings.values():
        extra|=P05.identifiers(expression)-set(outputs)
    all_inputs=set(frontier)|extra|{'pending_state','blocked_state'}
    widths={**widths,'pending_state':1,'blocked_state':1}
    assert all(n in widths for n in all_inputs),('Operand binding lacks actual type',sorted(all_inputs-set(widths)))
    ports=['input wire '+(f'[{widths[n]-1}:0] ' if widths[n]>1 else '')+n for n in sorted(all_inputs)]
    text='module miter(\n'+',\n'.join(ports)+'\n);\n'
    for label in ('reference','candidate'):
        for name,bits in outputs.items():
            text+='wire '+(f'[{bits-1}:0] ' if bits>1 else '')+label+'_'+name+';\n'
        for name in OPERAND_OUTPUTS:
            bits=operand_types.get(name,1)
            text+='wire '+(f'[{bits-1}:0] ' if bits>1 else '')+label+'_operand_'+name+';\n'
        text+='cone_'+label+' '+label+'_instance('+','.join('.'+n+'('+n+')' for n in sorted(frontier))+','
        text+=','.join('.observed_'+n+'('+label+'_'+n+')' for n in outputs)+');\n'
        connections=[]
        for name,expression in actual_bindings.items():
            for output in outputs:
                expression=re.sub(r'\b'+output+r'\b',label+'_'+output,expression)
            connections.append('.'+name+'('+expression+')')
        connections+=['.pending_state(pending_state)','.blocked_state(blocked_state)']
        connections+=['.'+n+'('+label+'_operand_'+n+')' for n in OPERAND_OUTPUTS]
        text+='operand_step #(.USE_PARALLEL_RANGE(1\'b1)) '+label+'_operand('+','.join(connections)+');\n'
    text+='always @* begin\n'
    if flat:
        text+='assert(reference_stack_offset == candidate_stack_offset);\n'
    else:
        text+='if(reference_stack_request) assert(reference_stack_offset == candidate_stack_offset);\n'
        text+='if(reference_protected_call_stack_access) assert(reference_protected_call_stack_address == candidate_protected_call_stack_address);\n'
        for name in COMMON_OUTPUTS:
            text+='assert(reference_'+name+' == candidate_'+name+');\n'
        for name in OPERAND_OUTPUTS:
            text+='assert(reference_operand_'+name+' == candidate_operand_'+name+');\n'
    text+='end\nendmodule\n'
    return operand+'\n'+models['reference']+'\n'+models['candidate']+'\n'+text,all_inputs


def run(out,name,source,*,reject=False,synth=False):
    path=out/(name+'.sv');path.write_text(source,newline='\n')
    if synth:
        label=name.split('-')[-1]
        script=f'read_verilog -sv {path}\nsynth -top cone_{label} -flatten\nstat\nwrite_json {out/(name+".json")}\n'
    else:
        script=f'read_verilog -formal -sv {path}\nprep -top miter -flatten\nopt\nsat -verify -prove-asserts -show-inputs -timeout 120\n'
    ys=out/(name+'.ys');ys.write_text(script,newline='\n')
    result=subprocess.run(['yosys','-Q','-s',str(ys)],cwd=ROOT,capture_output=True,timeout=180)
    log=result.stdout+result.stderr;(out/(name+'.log')).write_bytes(log)
    if reject:
        assert result.returncode !=0 and b'proof did fail' in log,('Missing actual SAT counterexample',name)
    else:
        assert result.returncode==0 and (synth or b'SUCCESS!' in log),('Proof/build failed',name)
    assert b'Warning:' not in log,('Unexpected proof diagnostic',name)


def depth(module,source,target):
    start=set(module['ports'][source]['bits'])
    levels={b:None for port in module['ports'].values() if port['direction']=='input'
            for b in port['bits'] if isinstance(b,int)}
    levels.update({b:0 for b in start});pending=list(module['cells'].values())
    while pending:
        progress=False
        for cell in pending[:]:
            inp={bit for n,v in cell['connections'].items() if cell['port_directions'][n]=='input' for bit in v if isinstance(bit,int)}
            if not inp.issubset(levels):continue
            related=[levels[b] for b in inp if levels[b] is not None]
            level=max(related)+1 if related else None
            for n,v in cell['connections'].items():
                if cell['port_directions'][n]=='output':
                    for b in v:
                        if isinstance(b,int):levels[b]=level
            pending.remove(cell);progress=True
        assert progress,'Unresolved or cyclic mapped combinational graph'
    return max((levels[b] for b in module['ports'][target]['bits']
                if isinstance(b,int) and levels[b] is not None),default=None)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    out=parser.parse_args().output.resolve()
    assert out.is_relative_to((ROOT/'build').resolve()), 'Output must remain in repository build'
    out.mkdir(parents=True,exist_ok=False)
    historical_reference,historical_paths=historical_flat_inputs()
    packages={name:(ROOT/path).read_text() for name,path in {
        'spk286_microcode_pkg':'vendor/spk286/microcode/generated/spk286_microcode_pkg.sv',
        'spk286_protected_pkg':'vendor/spk286/rtl/spk286_protected_pkg.sv'}.items()}
    operand_path=ROOT/'vendor/spk286/rtl/spk286_operand.sv';operand=operand_path.read_text();step=actual_operand_step(operand)
    sources=[Path(__file__).resolve(),ROOT/'scripts/test_p05_limit_equivalence.py',ROOT/'scripts/test_stack_offset_contract.py',operand_path]+historical_paths
    sources += [ROOT/'vendor/spk286/microcode/generated/spk286_microcode_pkg.sv',ROOT/'vendor/spk286/rtl/spk286_protected_pkg.sv']
    flavors=[]
    for flavor,directory,stem in [('raw','rtl','spk286'),('timed','rtl/timed','spk286_profiled')]:
        top_path=ROOT/'vendor/spk286'/directory/(stem+'.sv')
        executor_path=ROOT/'vendor/spk286'/directory/(stem+'_micro_executor.sv')
        sources += [top_path,executor_path];flavors.append((flavor,top_path,executor_path))
    before={p.relative_to(ROOT).as_posix():sha(p) for p in sources};results={}
    for flavor,top_path,executor_path in flavors:
        top=top_path.read_text();installed_bytes=executor_path.read_bytes()
        original,candidate,delta,variant=reviewed_pair(installed_bytes.decode(),flavor)
        historical_wrapper,_=FLAT.build(original,historical_reference)
        FLAT.prove(out,flavor+'-historical-flat-unchanged-PASS',historical_wrapper)
        # Exhaustive lexical consumer inventory; no hidden state/alias consumer.
        # Five source lines / six tokens: named port and bound net both count.
        assert len(re.findall(r'\bstack_offset\b',P05.clean(top)))==6
        assert len(re.findall(r'\bstack_offset\b',P05.clean(original)))==3
        (out/(flavor+'-executor.candidate.sv')).write_bytes(candidate.encode())
        models={};boundaries=[];outputs=None;widths=None
        for label,body in [('reference',original),('candidate',candidate)]:
            m,frontier,observed,current_widths=model(top,body,label,packages)
            models[label]=m;boundaries.append(frontier)
            if outputs is not None:assert outputs==observed
            outputs=observed;widths=current_widths
        assert boundaries[0]==boundaries[1],('Boundary changed',flavor)
        full,inputs=wrapper(top,models,boundaries[0],outputs,widths,step)
        run(out,flavor+'-consumer-next-state',full)
        flat,_=wrapper(top,models,boundaries[0],outputs,widths,step,flat=True)
        run(out,flavor+'-idle-flat-offset-DIFFERS',flat,reject=True)
        mutations={
            'wrong-decrement':("stack_cursor_q - 16'd2","stack_cursor_q - 16'd1"),
            'wrong-write-phase':("call_parameter_active_q && call_parameter_phase_q == 2'd1;", "call_parameter_active_q && call_parameter_phase_q == 2'd0;"),
            'missing-read-guards':('call_gate_outer_required && call_parameter_active_q && call_parameter_phase_q == 2\'d0;',"1'b1;"),
            'unsafe-permission':(' && !cancel && !start &&',' && !start &&'),
        }
        for name,(old,new) in mutations.items():
            if name=='unsafe-permission':
                # Raw has one permission, timed has two. Mutate the actual
                # implementation permission only in the latter.
                permission='implementation_allowed' if flavor=='timed' else 'allowed'
                statement=actual(candidate,permission);assert statement.count(old)==1
                mutant=candidate.replace(statement,statement.replace(old,new,1),1)
            else:
                region=delta['added'] if name in ('wrong-write-phase','missing-read-guards') else actual(candidate,'call_parameter_write_offset')
                assert region.count(old)==1,(name,region)
                mutant=candidate.replace(region,region.replace(old,new,1),1)
            m,frontier,observed,current_widths=model(top,mutant,'candidate',packages,include_frontier=boundaries[0])
            assert frontier==boundaries[0] and observed==outputs
            paired,_=wrapper(top,{'reference':models['reference'],'candidate':m},frontier,observed,current_widths,step)
            run(out,flavor+'-mutant-'+name,paired,reject=True)
        mapped={}
        for label in ('reference','candidate'):
            run(out,flavor+'-mapping-'+label,models[label],synth=True)
            module=json.loads((out/(flavor+'-mapping-'+label+'.json')).read_text())['modules']['cone_'+label]
            mapped[label]={'generic_gates':len(module['cells']),
                'depth_from_service_start_to_stack_data':depth(module,'service_start','observed_stack_offset'),
                'depth_from_service_start_to_access_fault':depth(module,'service_start','observed_protected_access_fault')}
        results[flavor]={'source':executor_path.relative_to(ROOT).as_posix(),'installed_variant':variant,'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
            'source_delta':delta,'primary_inputs':sorted(inputs),'input_bits':sum(widths.get(n,1) for n in inputs),
            'top_observable_outputs':COMMON_OUTPUTS,'qualified_payloads':['stack_offset under actual stack_request','protected_call_stack_address under actual protected_call_stack_access'],
            'operand_observable_outputs_and_next_state':OPERAND_OUTPUTS,'operand_prestate_bits':2,
            'negative_controls':{name:'SAT_COUNTEREXAMPLE_REJECTED' for name in mutations},
            'immutable_flat_offset_contract':'Historical producer against independently archived original contract PASS; current candidate flat idle payload DIFFERS with actual SAT counterexample. Original checker/evidence unchanged.',
            'generic_mapping':mapped}
    assert before=={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    installed=all(value['installed_variant']=='candidate' for value in results.values())
    status='CURRENT_STACK_OFFSET_CONSUMED_CONTRACT_EQUIVALENCE_PASS' if installed else 'PRIVATE_STACK_DATA_SELECT_CONSUMER_NEXT_STATE_EQUIVALENCE_PASS'
    (out/'receipt.json').write_text(json.dumps({'status':status,
        'scope':'Source-extracted raw/timed permission/select/request producer, actual four-cache top offset/address/fault consumers and complete original operand outputs/two FF next-state equations; all binary common inputs/states, no assumptions. Only idle stack payloads differ; full CPU induction, dual simulation, strict candidate lint, fit and hardware are not performed.',
        'sources_sha256':before,'results':results,'state_bits_added':0,'clocks_added':0,'cycles_added':0,
        'physical_cost':'Generic gates only; not CycloneV ALMs or fitted slack.',
        'artifacts_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n')
    print(status)
    print(json.dumps({k:v['generic_mapping'] for k,v in results.items()}))


if __name__=='__main__':main()
