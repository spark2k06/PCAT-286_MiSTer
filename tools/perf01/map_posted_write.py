"""Map the isolated posted-write block with unused diagnostic counters removed."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    assert not out.exists(), 'Preserve prior mappings'
    out.mkdir(parents=True)
    source = ROOT/'tools/perf01/prototypes/spk286_at_posted_write_buffer.sv'
    before = sha(source)
    image = 'raetro/quartus:mister'
    identity = subprocess.check_output(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], text=True).strip()
    header = source.read_text().split('module spk286_at_posted_write_buffer', 1)[1].split(');', 1)[0]
    declarations = header.split(') (', 1)[1]
    signals = [n.strip() for group in re.split(r'(?:input|output)\s+logic\s+(?:\[[^\]]+\]\s*)?', declarations)[1:]
               for n in group.strip().strip(',').split(',')]
    assert len(signals) == len(set(signals))
    ports = ',\n'.join('        .'+n+'('+('' if n.startswith('debug_') else n)+')' for n in signals)
    summaries = {}
    for enabled in (0, 1):
        directory = out/f'enable-{enabled}'
        directory.mkdir()
        shutil.copyfile(source, directory/source.name)
        wrapper_header = header.replace("parameter logic ENABLE = 1'b1", f"parameter logic ENABLE = 1'b{enabled}")
        wrapper_header = re.sub(r',\s*output logic \[31:0\] debug_post_count, debug_drain_count, debug_stall_count', '', wrapper_header)
        (directory/'posted_write_cost.sv').write_text('module posted_write_cost'+wrapper_header+');\n'
            '    spk286_at_posted_write_buffer #(.ENABLE(ENABLE)) dut (\n'+ports+'\n    );\nendmodule\n')
        (directory/'posted_cost.qpf').write_text('QUARTUS_VERSION = "17.0.2"\nPROJECT_REVISION = "posted_cost"\n')
        (directory/'posted_cost.qsf').write_text('''set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEBA6U23I7
set_global_assignment -name TOP_LEVEL_ENTITY posted_write_cost
set_global_assignment -name SYSTEMVERILOG_FILE spk286_at_posted_write_buffer.sv
set_global_assignment -name SYSTEMVERILOG_FILE posted_write_cost.sv
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name NUM_PARALLEL_PROCESSORS 4
''')
        command = ['docker', 'run', '--rm', '-v', str(directory)+':/project', '-w', '/project', image,
                   'quartus_map', 'posted_cost']
        with (directory/'map.log').open('w') as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        report = directory/'output_files/posted_cost.map.rpt'
        text = report.read_text(encoding='latin-1')
        def value(key):
            return int(re.search(re.escape(key)+r'\s*;\s*([\d,]+)', text)[1].replace(',', ''))
        summaries[str(enabled)] = {'registers': value('Total registers'),
                                  'estimated_alms': value('Estimate of Logic utilization (ALMs needed)'),
                                  'combinational_aluts': value('Combinational ALUT usage for logic'),
                                  'block_memory_bits': value('Total block memory bits'),
                                  'report_sha256': sha(report), 'command': command}
        assert sha(directory/source.name) == before
        assert not list((directory/'output_files').glob('*.rbf'))
    assert sha(source) == before
    (out/'mapping.json').write_text(json.dumps({'source_sha256': before, 'quartus_image': identity,
        'arms': summaries, 'scope': 'Isolated Quartus map only; no fitter/timing/RBF or whole-project area claim. All payload outputs retained; debug counters unconnected.'}, indent=2)+'\n')
    print(json.dumps(summaries, indent=2))
    print('POSTED_WRITE_ISOLATED_MAP_PASS')


if __name__ == '__main__':
    main()
