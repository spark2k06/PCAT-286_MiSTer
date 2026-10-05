#!/usr/bin/env python3
"""Check registered-head replay against the immutable RAM-addressed reference.

The interface and existing oracle are unchanged. This is a CPU-local storage
check, not whole-core functional qualification or fitted FPGA timing evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / 'rtl/spk286_timing/spk286_target_replay.sv'
BENCH = ROOT / 'sim/spk286_timing/spk286_target_replay_tb.sv'
REFERENCE = '6307f5b60e9db21b7964946a859cb42746009c95'
REFERENCE_SHA = 'df3bca94f471863d05cbd505b8b927634d5049b53da1f2092f7e872f8fd02921'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, timeout=120):
    result = subprocess.run(list(map(str, command)), cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    log.write_text(result.stdout, newline='\n')
    if result.returncode:
        raise RuntimeError(f'command failed {result.returncode}: {log}')
    return result.stdout


def synthesize(directory, name, source):
    script = directory / f'{name}.ys'
    net = directory / f'{name}.json'
    script.write_text(f'read_verilog -sv {source}\nsynth -top spk286_target_replay -flatten\ncheck -assert\nwrite_json {net}\n', newline='\n')
    run(['yosys', '-Q', '-s', script], directory / f'{name}.log')
    design = json.loads(net.read_text())['modules']['spk286_target_replay']
    return {'generic_cells': len(design['cells']),
            'register_bits': sum(len(cell['connections'].get('Q', []))
                                 for cell in design['cells'].values()
                                 if 'DFF' in cell['type'].upper()),
            'scope': 'Yosys generic logic, not fitted FPGA ALMs'}


def instrument(text, reference=False):
    """Expose storage for induction without changing either sequential body."""
    port = '    output logic [3:0] count\n'
    assert text.count(port) == 1
    text = text.replace(port, port.rstrip('\n') + ',\n'
                        '    output wire [3:0] proof_write, proof_read,\n'
                        '    output wire [79:0] proof_bytes\n')
    read = 'read_q' if reference else '(write_q - count_q)'
    extra = (f'    assign proof_write = write_q;\n    assign proof_read = {read};\n'
             '    for (genvar i = 0; i < 10; i = i + 1) begin\n'
             '        assign proof_bytes[i*8 +: 8] = bytes_q[i];\n    end\n')
    assert text.count('endmodule') == 1
    return text.replace('endmodule', extra + 'endmodule')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to((ROOT / 'build').resolve()):
        parser.error('output must be a fresh directory under workspace build')
    out.mkdir(parents=True, exist_ok=False)
    inputs = [RTL, BENCH, Path(__file__).resolve()]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    raw = subprocess.check_output(['git', 'show', f'{REFERENCE}:{RTL.relative_to(ROOT).as_posix()}'], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == REFERENCE_SHA
    reference = out / 'reference-original.sv'
    reference.write_bytes(raw)
    renamed = out / 'reference.sv'
    renamed.write_text(raw.decode().replace('SPK286_TARGET_REPLAY_SV', 'SPK286_TARGET_REPLAY_REFERENCE_SV')
                       .replace('module spk286_target_replay (', 'module spk286_target_replay_reference ('), newline='\n')
    run(['verilator', '--lint-only', '--Wall', '--top-module', RTL.stem, RTL], out / 'lint.log')
    run(['iverilog', '-g2012', '-s', BENCH.stem, '-o', out / 'test.vvp', RTL, BENCH], out / 'icarus-build.log')
    run(['verilator', '--binary', '--timing', '--assert', '-j', '2', '--top-module', BENCH.stem,
         '--Mdir', out / 'obj', '-o', 'replay-test', RTL, BENCH], out / 'verilator-build.log')
    actual = [run(['vvp', out / 'test.vvp'], out / 'icarus-run.log'),
              run([out / 'obj/replay-test'], out / 'verilator-run.log')]
    markers = [[line for line in text.splitlines() if 'TARGET_REPLAY_PASS' in line] for text in actual]
    assert markers[0] == markers[1] == ['TARGET_REPLAY_PASS checks=246']
    miter = out / 'miter.sv'
    miter.write_text('''module replay_miter (
    input clk, reset, cancel, start, capture, consume,
    input [7:0] capture_data
);
    wire valid_a, valid_b;
    wire [7:0] data_a, data_b;
    wire [3:0] count_a, count_b;
    wire [3:0] write_a, write_b, read_a, read_b;
    wire [79:0] bytes_a, bytes_b;
    spk286_target_replay a(.clk(clk),.reset(reset),.cancel(cancel),.start(start),
        .capture(capture),.consume(consume),.capture_data(capture_data),
        .valid(valid_a),.data(data_a),.count(count_a),
        .proof_write(write_a),.proof_read(read_a),.proof_bytes(bytes_a));
    spk286_target_replay_reference b(.clk(clk),.reset(reset),.cancel(cancel),.start(start),
        .capture(capture),.consume(consume),.capture_data(capture_data),
        .valid(valid_b),.data(data_b),.count(count_b),
        .proof_write(write_b),.proof_read(read_b),.proof_bytes(bytes_b));
    always @* begin
        assert(write_a == write_b);
        assert(write_b <= 10);
        assert(read_b <= write_b);
        assert(read_a == read_b);
        assert(valid_a == valid_b);
        assert(data_a == data_b);
        assert(count_a == count_b);
    end
    for (genvar slot = 0; slot < 10; slot = slot + 1) begin
        wire [4:0] reference_slot = {1'b0, read_b} + slot;
        always @* if (slot < count_a)
            assert(bytes_a[slot*8 +: 8] == bytes_b[reference_slot*8 +: 8]);
    end
endmodule
''', newline='\n')
    candidate_formal = out / 'candidate-instrumented.sv'
    reference_formal = out / 'reference-instrumented.sv'
    candidate_formal.write_text(instrument(RTL.read_text()), newline='\n')
    reference_formal.write_text(instrument(renamed.read_text(), reference=True), newline='\n')
    formal = out / 'equivalence.ys'
    formal.write_text(f'read_verilog -formal -sv {candidate_formal} {reference_formal} {miter}\n'
                      'prep -top replay_miter -flatten\nmemory_map\nopt\n'
                      'sat -verify -prove-asserts -tempinduct -seq 2 -maxsteps 4 '
                      '-set-init-zero -set-at 1 reset 1 -timeout 60\n', newline='\n')
    proof = run(['yosys', '-Q', '-s', formal], out / 'equivalence.log', timeout=90)
    assert 'Induction step proven: SUCCESS!' in proof
    # Check that the same unchanged output oracle rejects corrupted bytes and
    # a broken pop. These are temporary proof inputs, never production edits.
    negative = []
    for name, old, new in [
            ('capture-byte', '<= capture_data;', "<= capture_data ^ 8'd1;"),
            ('pop-head', '<= bytes_q[slot + 1];', '<= bytes_q[slot];')]:
        text = candidate_formal.read_text()
        assert text.count(old) == 1
        mutant = out / f'mutant-{name}.sv'
        mutant.write_text(text.replace(old, new), newline='\n')
        script = out / f'mutant-{name}.ys'
        script.write_text(f'read_verilog -formal -sv {mutant} {reference_formal} {miter}\n'
                          'prep -top replay_miter -flatten\nmemory_map\nopt\n'
                          'sat -verify -prove-asserts -seq 6 -set-init-zero '
                          '-set-at 1 reset 1 -timeout 30\n', newline='\n')
        result = subprocess.run(['yosys', '-Q', '-s', str(script)], cwd=ROOT, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        (out / f'mutant-{name}.log').write_text(result.stdout, newline='\n')
        assert result.returncode != 0 and 'proof did fail' in result.stdout
        assert 'time out' not in result.stdout
        negative.append({'mutation': name, 'status': 'REJECTED_WITH_COUNTEREXAMPLE'})
    cost = {'reference': synthesize(out, 'reference-cost', reference),
            'candidate': synthesize(out, 'candidate-cost', RTL)}
    assert before == {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs}
    receipt = {'status': 'PASS', 'source_sha256': before, 'reference_revision': REFERENCE,
               'reference_sha256': REFERENCE_SHA, 'unit_each_simulator': markers[0][0],
               'formal': {'status': 'INDUCTIVE_EQUIVALENCE_PASS',
                          'inputs': 'arbitrary control/data after reset at step 1; initialization zero',
                          'scope': 'exact valid/data/count every cycle; unchanged sequential bodies with additional observation ports',
                          'invariant': 'equal total writes/read offset and ordered unread bytes; legal pointer bounds'},
               'negative_controls': negative,
               'generic_cost': cost,
               'logs_sha256': {p.name: sha(p) for p in out.glob('*.log')}}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    print('REPLAY_REGISTERED_HEAD_DUAL_EQUIVALENCE_PASS', json.dumps(cost), flush=True)


if __name__ == '__main__':
    main()
