#!/usr/bin/env python3
"""Rebind the original stack-offset contract to actual current CPU cones.

The reference is the original independently archived October 2 offset_old
module, whose full miter and proof artifacts are checked. Extract the current
raw/timed helper assignments and their actual widths. All 101 two-state mux
boundary bits are arbitrary, including simultaneous selectors and wraps.
This proves the offset cone, not unchanged surrounding RTL or a full CPU.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path('docs/evidence/stack-offset-arithmetic-20261002/upstream-formal')
ARCHIVE_MITER_SHA256 = 'e2f88b673b37c1c24d4ca1316e394884b2ca89f863178cd5f1f6dfa13d2bb256'
ORIGINAL_REFERENCE_SHA256 = '0d1098372509e4456fbefc05352957a0771dce6d4dfb9004537c19687b482dc5'
HELPERS = ('call_parameter_write_offset', 'iret_parameter_bytes', 'iret_outer_stack_offset')
WIDTHS = {name:1 for name in ('call_parameter_read', 'call_parameter_write',
                              'iret_outer_pop', 'read_frame_address', 'allocation_valid_q')}
WIDTHS.update({name:16 for name in ('call_parameter_source_sp_q', 'stack_cursor_q',
    'return_stack_pointer', 'allocation_q', 'frame_address_q', 'stack_native_offset')})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assignment(text, name):
    matches = re.findall(r'^    assign '+name+r'\s*=.*?;', text, re.M | re.S)
    assert len(matches) == 1, ('Actual assignment anchor changed', name)
    return matches[0]


def types(text):
    result = {}
    for width,names in re.findall(r'\b(?:logic|wire)\s*(\[[^]\n]+\])?\s*'
            r'([A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)', text):
        if width:
            match = re.fullmatch(r'\[(\d+):0\]', width)
            if not match:
                continue
            bits = int(match[1])+1
        else:
            bits = 1
        for name in re.split(r'\s*,\s*', names):
            assert name not in result or result[name] == bits, name
            result[name] = bits
    return result


def build(source, reference):
    actual = '\n'.join(assignment(source,n) for n in HELPERS+('stack_offset',))
    tokens = re.sub(r"\d*'[sS]?[bdhoBDHO][0-9a-fA-F_xXzZ?]+", '', actual)
    leaves = set(re.findall(r'\b[A-Za-z_]\w*\b',tokens)) - set(HELPERS) - {'assign','stack_offset'}
    assert leaves == set(WIDTHS), ('Offset cone boundary changed', sorted(leaves ^ set(WIDTHS)))
    declared = types(source)
    for name,bits in {**WIDTHS,**{n:16 for n in HELPERS+('stack_offset',)}}.items():
        assert declared.get(name) == bits, ('Actual cone width changed', name, declared.get(name), bits)
    portlist = ',\n'.join('input wire '+(f'[{bits-1}:0] ' if bits>1 else '')+name
                         for name,bits in WIDTHS.items())
    candidate = 'module offset_candidate(\n'+portlist+',\noutput wire [15:0] stack_offset\n);\n'
    candidate += '\n'.join('wire [15:0] '+n+';' for n in HELPERS)+'\n'+actual+'\nendmodule\n'
    wrapper = 'module miter(\n'+portlist+',\noutput wire equivalent\n);\n'
    wrapper += 'wire [15:0] expected, observed;\n'
    for name,module in (('expected','offset_old'),('observed','offset_candidate')):
        wrapper += module+' u_'+name+'('+','.join('.'+n+'('+n+')' for n in WIDTHS)+',.stack_offset('+name+'));\n'
    wrapper += 'assign equivalent = expected == observed;\nendmodule\n'
    return reference+'\n'+candidate+'\n'+wrapper, candidate


def replace_once(text,before,after):
    assert text.count(before) == 1, ('Mutation anchor changed',before)
    return text.replace(before,after,1)


def prove(out,name,text,reject=False):
    rtl=out/(name+'.sv'); rtl.write_text(text,newline='\n')
    command=('read_verilog -sv '+rtl.name+'; hierarchy -top miter; proc; flatten; opt; '
             'sat -verify -prove equivalent 1 -show-inputs -show-outputs -timeout 60')
    with (out/(name+'.log')).open('w') as log:
        result=subprocess.run(['yosys','-Q','-p',command],cwd=out,
            stdout=log,stderr=subprocess.STDOUT,timeout=90)
    log=(out/(name+'.log')).read_text()
    if reject:
        assert result.returncode != 0 and 'proof did fail' in log, ('Missing SAT counterexample',name)
    else:
        assert result.returncode == 0 and 'SUCCESS!' in log, ('Equivalence failed',name)
    assert 'Warning:' not in log, ('Unexpected proof diagnostic',name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    archive=ROOT/ARCHIVE
    receipt_path=archive/'receipt.json'; miter=archive/'miter.v'
    original=json.loads(receipt_path.read_text())
    assert original['status']=='EXACT_STACK_OFFSET_EQUIVALENCE_PASS'
    assert original['reference']=='792f652a9712ed34738472869aaa9b8d78ad1d96'
    assert original['reference_source_sha256']==ORIGINAL_REFERENCE_SHA256
    assert original['artifacts_sha256']['miter.v']==ARCHIVE_MITER_SHA256
    assert original['negative_controls']=={'wrong_decrement':'REJECTED','missing_allocation':'REJECTED'}
    archives=[receipt_path]
    for name,expected in original['artifacts_sha256'].items():
        assert Path(name).name==name and (archive/name).is_file(), 'Invalid archived artifact'
        assert sha(archive/name)==expected, ('Original proof artifact changed',name)
        archives.append(archive/name)
    assert sha(miter)==ARCHIVE_MITER_SHA256, 'Original independent miter changed'
    matches=re.findall(r'(module offset_old\(.*?\nendmodule)',miter.read_text(),re.S)
    assert len(matches)==1, 'Original contract module anchor changed'
    reference=matches[0]
    raw=ROOT/'vendor/spk286/rtl/spk286_micro_executor.sv'
    timed=ROOT/'vendor/spk286/rtl/timed/spk286_profiled_micro_executor.sv'
    inputs=[raw,timed,Path(__file__).resolve()]+archives
    before={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    results={}
    for flavor,path in (('raw',raw),('timed',timed)):
        wrapper,candidate=build(path.read_text(),reference)
        prove(out,flavor+'-actual',wrapper)
        mutations={
            'wrong-decrement':("stack_cursor_q - 16'd2","stack_cursor_q - 16'd1"),
            'missing-allocation':('return_stack_pointer + iret_parameter_bytes','return_stack_pointer'),
            'missing-allocation-valid':("allocation_valid_q ? allocation_q : 16'd0",'allocation_q'),
            'wrong-priority':('call_parameter_read ? call_parameter_source_sp_q :\n'
                              '                          call_parameter_write ? call_parameter_write_offset :',
                              'call_parameter_write ? call_parameter_write_offset :\n'
                              '                          call_parameter_read ? call_parameter_source_sp_q :'),
        }
        for name,(old,new) in mutations.items():
            mutant=replace_once(candidate,old,new)
            # Only the current candidate region changes; reference is frozen.
            assert wrapper.count(candidate)==1
            prove(out,flavor+'-'+name,wrapper.replace(candidate,mutant,1),reject=True)
        results[flavor]={'source':path.relative_to(ROOT).as_posix(),'input_bits':sum(WIDTHS.values()),
            'arbitrary_inputs':WIDTHS,'actual_assignments':list(HELPERS)+['stack_offset'],
            'negative_controls':{name:'SAT_COUNTEREXAMPLE_REJECTED' for name in mutations}}
    assert before=={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}, 'Proof input changed'
    (out/'receipt.json').write_text(json.dumps({'schema':1,
        'status':'CURRENT_STACK_OFFSET_CONTRACT_EQUIVALENCE_PASS','sources_sha256':before,
        'original_reference_source_sha256':ORIGINAL_REFERENCE_SHA256,
        'original_independent_miter_sha256':ARCHIVE_MITER_SHA256,'results':results,
        'scope':'Actual raw/timed four-assignment offset cones against original archived offset_old, all 101 binary mux boundary bits, all simultaneous selects, 16-bit wrap and allocation-valid choices; no assumptions; surrounding RTL/state is outside this cone proof',
        'tool_version':subprocess.check_output(['yosys','-V'],text=True).strip(),
        'artifacts_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n')
    print('CURRENT_STACK_OFFSET_CONTRACT_EQUIVALENCE_PASS input_bits=101 raw_timed=1 mutants=8')


if __name__=='__main__':
    main()
