#!/usr/bin/env python3
"""Prove compressed metadata arithmetic against the frozen actual generator."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from build_p06_profile_cpu import CONNECTION

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'c38898c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True, exist_ok=False)
    raw = subprocess.check_output(['git', 'show', f'{REFERENCE}:scripts/build_p06_profile_cpu.py'], cwd=ROOT)
    (out / 'reference-builder.py').write_bytes(raw)
    tree = ast.parse(raw.decode())
    original = next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == 'CONNECTION'
                        for target in node.targets))
    old_sum = original[original.index('    always_comb begin\n        profile_metadata_sum'):
                       original.index('    assign profile_preserve_cancel')]
    function = CONNECTION[CONNECTION.index('    function automatic logic [9:0] profile_metadata_budget'):
                          CONNECTION.index('    endfunction') + len('    endfunction')]
    source = '''module budget_miter (
    input [9:0] profile_base_clocks, profile_repeat_setup, profile_repeat_iteration,
    input [2:0] profile_ea_clocks,
    input profile_repeated_string, profile_candidate_body, profile_repeat_nonempty_q,
    input profile_delivery_metadata,
    input [3:0] profile_prefix_count_q,
    input [31:0] register_state
);
    logic [11:0] profile_metadata_sum;
    logic [9:0] profile_metadata_clocks, candidate;
''' + function + '\n' + old_sum + '''
    assign candidate = profile_metadata_budget(profile_base_clocks,
        profile_repeat_setup, profile_repeat_iteration, profile_ea_clocks,
        profile_repeated_string,
        profile_candidate_body ? register_state[16 +: 16] != 0 : profile_repeat_nonempty_q,
        profile_delivery_metadata, profile_prefix_count_q);
    always @* assert(candidate == profile_metadata_clocks);
endmodule
'''
    assertions = {}
    for label, text, reject in (
            ('candidate', source, False),
            ('zero-prefix-underflow', source.replace(
                "prefixes == 0 ? 4'd0 : prefixes - 4'd1", "prefixes - 4'd1"), True),
            ('missing-ea', source.replace("{9'd0, ea}", "12'd0"), True)):
        path = out / (label + '.sv')
        path.write_text(text, newline='\n')
        script = out / (label + '.ys')
        script.write_text(f'read_verilog -formal -sv {path}\nprep -top budget_miter -flatten\nopt\n'
                          'sat -verify -prove-asserts -timeout 60\n', newline='\n')
        result = subprocess.run(['yosys', '-Q', '-s', script], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        log = result.stdout.decode()
        (out / (label + '.log')).write_bytes(result.stdout)
        if reject:
            assert result.returncode and 'proof did fail' in log and 'time out' not in log
        else:
            assert result.returncode == 0 and 'SAT proof finished - no model found: SUCCESS!' in log
        assertions[label] = 'REJECTED_WITH_COUNTEREXAMPLE' if reject else 'PROVED_ALL_SYMBOLIC_INPUTS'
    inputs = [Path(__file__), ROOT / 'scripts/build_p06_profile_cpu.py']
    receipt = {'status': 'METADATA_BUDGET_EQUIVALENCE_PASS', 'reference_revision': REFERENCE,
               'reference_builder_sha256': digest(raw), 'scope': 'Actual old admission arithmetic versus actual new function; all symbolic inputs, no lifecycle assumption',
               'gates': assertions,
               'sources_sha256': {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in inputs},
               'artifacts_sha256': {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file()}}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    print('METADATA_BUDGET_EQUIVALENCE_PASS', flush=True)


if __name__ == '__main__':
    main()
