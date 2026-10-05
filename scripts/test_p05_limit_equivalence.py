#!/usr/bin/env python3
"""Prove the actual CPU protection expression against the pre-P05 contract.

Pure combinational SAT proof: no FPGA synthesis, timing or RBF generation.
The original expected expression is frozen below. The fixed production CPU
now compares each cache/offset before its selectors, so extract those actual
assignments and the four-cache generate block instead of a retired opt-in.
All boundary inputs are unconstrained; no reachable-state assumptions apply.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

REFERENCE = """
operand_request && operand_select_rm && !operand_register_direct &&
!protected_descriptor_access && !protected_tss_access && !protected_event_access &&
!io_transfer && !vector_request &&
(protected_call_stack_access ?
 (service_segment != 2'd2 ||
  (protected_call_stack_expand_down ?
   ({1'b0, service_offset} <= {1'b0, protected_call_stack_limit} ||
    ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > 17'h0FFFF)) :
   ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > {1'b0, protected_call_stack_limit}))) :
 (protected_segment_is_loaded &&
  (!protected_segment_is_valid || !protected_segment_is_present ||
   (protected_segment_is_code ? (!protected_segment_is_readable || operand_write) :
    (stack_request ? (!protected_segment_is_writable || service_segment != 2'd2) :
     (operand_write && !protected_segment_is_writable))) ||
   (protected_segment_is_expand_down ?
    ({1'b0, service_offset} <= {1'b0, selected_segment_limit} ||
     ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > 17'h0FFFF)) :
    ({1'b0, service_offset} + (operand_byte ? 17'd0 : 17'd1) > {1'b0, selected_segment_limit})))))
"""


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA256 = '520e5e444252f3a5d871afd339a7d43ebdf867a9d5df1686b1bc30a4b257908f'
NODES = ('service_segment service_offset selected_segment_index selected_segment_limit '
         'selected_segment_access protected_segment_is_loaded protected_segment_is_valid '
         'protected_segment_is_present protected_segment_is_code protected_segment_is_readable '
         'protected_segment_is_writable protected_segment_is_expand_down '
         'protected_selected_range_fault parallel_operand_within_limit protected_call_range_fault '
         'protected_access_fault protected_access_ss_fault').split()
ARRAYS = ('operand_io_ranges operand_address_ranges operand_stack_ranges '
          'operand_regular_ranges operand_vector_ranges operand_system_ranges').split()
# Reviewed cone boundary. A new helper cannot silently become a free input.
LEAF_WIDTHS = {name: 1 for name in (
    'operand_request operand_select_rm operand_register_direct protected_descriptor_access '
    'protected_tss_access protected_event_access io_transfer vector_request '
    'protected_call_stack_access operand_write stack_request operand_byte '
    'protected_call_stack_expand_down execute_enable string_request string_destination '
    'segment_override address_override').split()}
LEAF_WIDTHS.update({name: 16 for name in (
    'operand_offset address_offset stack_offset vector_offset protected_call_stack_limit protected_msw').split()})
LEAF_WIDTHS.update({name: 2 for name in ('segment_read_index override_segment operand_segment').split()})
LEAF_WIDTHS.update({'protected_segment_access': 32, 'real_segment_access_state': 32,
                   'protected_segment_limits': 64, 'real_segment_limits': 64,
                   'protected_segment_valid': 4, 'protected_segment_present': 4,
                   'protected_segment_protected': 4})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(text):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)


def identifiers(text):
    text = re.sub(r"\d*'[sS]?[bdhoBDHO][0-9a-fA-F_xXzZ?]+", '', clean(text))
    return set(re.findall(r'\b[A-Za-z_]\w*\b', text))


def assignment(text, name):
    matches = re.findall(r'^    assign '+name+r'\s*=.*?;', text, re.M | re.S)
    assert len(matches) == 1, ('Expected exactly one actual assignment', name)
    return matches[0]


def types(text):
    result = {}
    for width, names in re.findall(r'\b(?:logic|wire)\s*(\[[^]\n]+\])?\s*'
            r'([A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)', clean(text)):
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


def span(text, pattern):
    matches = re.findall(pattern, text, re.S)
    assert len(matches) == 1, 'Actual range cone anchor changed'
    return matches[0]


def build(text):
    function = span(text, r'(    function automatic logic protected_range_exceeded\(.*?    endfunction)')
    generate = span(text, r'(    generate\s+    for \(operand_cache_index = 0;.*?    endgenerate)')
    statements = '\n'.join(assignment(text, name) for name in NODES)
    body = statements+'\n'+function+'\n'+generate
    internal = set(NODES+ARRAYS) | {'assign', 'function', 'automatic', 'logic', 'wire',
        'input', 'endfunction', 'generate', 'for', 'begin', 'end', 'endgenerate',
        'operand_cache_index', 'g_operand_cache_range', 'cache_limit', 'cache_expand_down',
        'protected_range_exceeded', 'offset_value', 'limit_value', 'expand_down', 'is_byte'}
    leaves = identifiers(body) - internal
    assert leaves == set(LEAF_WIDTHS), ('Range cone boundary changed', sorted(leaves ^ set(LEAF_WIDTHS)))
    widths = types(text)
    for name, bits in LEAF_WIDTHS.items():
        assert widths.get(name) == bits, ('Actual boundary width changed', name, widths.get(name), bits)
    expected = {'service_segment': 2, 'service_offset': 16, 'selected_segment_index': 2,
                'selected_segment_limit': 16, 'selected_segment_access': 8}
    for name in NODES:
        assert widths.get(name) == expected.get(name, 1), ('Actual helper width changed', name)
    for name in ARRAYS:
        assert widths.get(name) == 4, ('Actual cache range array width changed', name)
    ports = ['input wire '+(f'[{bits-1}:0] ' if bits>1 else '')+name
             for name,bits in sorted(LEAF_WIDTHS.items())]+['output wire equivalent']
    declarations = '\n'.join('wire '+(f'[{widths[name]-1}:0] ' if widths[name]>1 else '')+name+';'
                             for name in NODES+ARRAYS)
    wrapper = 'module p05_limit_miter(\n'+',\n'.join(ports)+'\n);\n'+declarations+'\ngenvar operand_cache_index;\n'+body
    # Reference remains exactly the original pre-P05 expression. Its shared
    # metadata/selectors are actual source assignments, not assumptions.
    wrapper += '\nwire reference = '+REFERENCE+';\n'
    wrapper += 'assign equivalent = protected_access_fault == reference &&\n'
    wrapper += "                    protected_access_ss_fault == (reference && service_segment == 2'd2);\nendmodule\n"
    return wrapper, function


def prove(output, name, text, reject=False):
    rtl = output/(name+'.sv')
    rtl.write_text(text, newline='\n')
    command = ('read_verilog -sv '+rtl.name+'; prep -top p05_limit_miter -flatten; opt; '
               'sat -verify -prove equivalent 1 -show-inputs -show-outputs -timeout 120')
    with (output/(name+'.log')).open('w') as log:
        result = subprocess.run(['yosys','-Q','-p',command], cwd=output,
                                stdout=log, stderr=subprocess.STDOUT, timeout=150)
    log = (output/(name+'.log')).read_text()
    if reject:
        assert result.returncode != 0 and 'proof did fail' in log, ('Expected real SAT counterexample', name)
    else:
        assert result.returncode == 0 and 'SUCCESS!' in log, ('SAT equivalence failed', name)
    assert 'Warning:' not in log, ('Unexpected proof diagnostic', name)


def replace_once(text, before, after):
    assert text.count(before) == 1, ('Mutation anchor changed', before)
    return text.replace(before, after, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert hashlib.sha256(REFERENCE.encode()).hexdigest() == REFERENCE_SHA256, 'Original contract changed'
    paths = [ROOT/'vendor/spk286/rtl/spk286.sv',
             ROOT/'vendor/spk286/rtl/timed/spk286_profiled.sv', Path(__file__).resolve()]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    results = {}
    for flavor, path in zip(('raw','timed'), paths[:2]):
        wrapper, function = build(path.read_text())
        prove(output, flavor+'-actual', wrapper)
        mutations = {
            'word-at-limit': ('(!is_byte && offset_value == limit_value)', "1'b0"),
            'word-overflow': ("(!is_byte && offset_value == 16'hFFFF)", "1'b0"),
            'expand-down-equality': ('offset_value <= limit_value', 'offset_value < limit_value'),
            'wrong-cache-index': ('operand_regular_ranges[selected_segment_index]',
                                  "operand_regular_ranges[selected_segment_index ^ 2'd1]"),
        }
        for name, (old,new) in mutations.items():
            prove(output, flavor+'-'+name, replace_once(wrapper,old,new), reject=True)
        # Independently prove the actual optimized primitive against the two
        # original 17-bit addition expressions, including FFFF word wrap.
        primitive = '''module p05_limit_miter(
input [15:0] offset_value, limit_value, input expand_down, is_byte,
output equivalent);
'''+function+'''
wire reference = expand_down ?
 (offset_value <= limit_value || ({1'b0,offset_value} + (is_byte ? 17'd0 : 17'd1) > 17'h0FFFF)) :
 ({1'b0,offset_value} + (is_byte ? 17'd0 : 17'd1) > {1'b0,limit_value});
assign equivalent = protected_range_exceeded(offset_value,limit_value,expand_down,is_byte) == reference;
endmodule
'''
        prove(output, flavor+'-primitive', primitive)
        results[flavor] = {'source':path.relative_to(ROOT).as_posix(),
            'input_bits':sum(LEAF_WIDTHS.values()), 'arbitrary_inputs':LEAF_WIDTHS,
            'actual_nodes':NODES, 'actual_arrays':ARRAYS,
            'negative_controls':{name:'SAT_COUNTEREXAMPLE_REJECTED' for name in mutations},
            'primitive_input_bits':34, 'outputs':['protected_access_fault','protected_access_ss_fault']}
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}, 'Proof input changed'
    (output/'receipt.json').write_text(json.dumps({'schema':2,
        'status':'P05_LIMIT_EQUIVALENCE_PASS','sources_sha256':before,
        'frozen_pre_p05_contract_sha256':REFERENCE_SHA256,
        'scope':'Actual raw/timed combinational fault/cache/offset cones and optimized range primitive; all binary boundary inputs, no assumptions, no whole-CPU or timing claim',
        'results':results, 'tool_version':subprocess.check_output(['yosys','-V'],text=True).strip(),
        'artifacts_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}, indent=2)+'\n')
    print(f'P05_LIMIT_EQUIVALENCE_PASS input_bits={sum(LEAF_WIDTHS.values())} all_inputs=1 raw_timed=1')
    print('P05_LIMIT_NEGATIVE_CONTROL_PASS word_at_limit_rejected=1 mutants=8')


if __name__ == '__main__':
    main()
