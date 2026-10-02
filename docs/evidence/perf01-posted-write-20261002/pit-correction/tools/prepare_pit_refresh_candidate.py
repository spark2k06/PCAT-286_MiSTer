#!/usr/bin/env python3
"""Prepare a fresh combined posting/PIT-refresh hardware candidate, privately."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('promotion', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    promotion, out = args.promotion.resolve(), args.output.resolve()
    assert not out.exists()
    original = promotion/'work'
    identities = json.loads((promotion/'promotion-inputs.json').read_text())
    assert all(sha(original/n) == h for n, h in identities['changed_sources'].items() | identities['new_sources'].items())
    work = out/'work'
    shutil.copytree(original, work, ignore=shutil.ignore_patterns('__pycache__', 'build', 'db', 'incremental_db', 'obj'))
    before = {str(p.relative_to(work)): sha(p) for p in work.rglob('*') if p.is_file()}
    module = 'rtl/spk286_integration/spk286_at_refresh.sv'
    shutil.copyfile(ROOT/'tools/perf01/prototypes/spk286_at_pit_refresh.sv', work/module)
    machine = work/'rtl/spk286_integration/spk286_at_machine.sv'
    text = machine.read_text()
    old = '        .refresh_enable         (refresh_enable),'
    assert text.count(old) == 1
    machine.write_text(text.replace(old, old+'\n        .timer_1_out            (pit_counter_out[1]),'))
    # The old A4 unit uses a deliberately accelerated four-clock source to
    # test ownership, not PIT timing. Preserve that stimulus in the fixture;
    # the new dedicated test programs the real PIT and measures its cadence.
    bench = work/'sim/spk286_integration/spk286_at_dma_refresh_pit_tb.sv'
    text = bench.read_text()
    old = '    spk286_at_refresh #(.REFRESH_INTERVAL(4)) refresh ('
    assert text.count(old) == 1
    text = text.replace(old, '''    logic [1:0] test_refresh_phase = 0;
    always @(posedge clk)
        if(reset || !refresh_enable) test_refresh_phase <= 0;
        else if(test_refresh_phase != 3) test_refresh_phase <= test_refresh_phase + 1'b1;
    spk286_at_refresh refresh (''')
    old = '        .clk(clk), .reset(reset), .refresh_enable(refresh_enable),'
    assert text.count(old) == 1
    text = text.replace(old, old+'\n        .timer_1_out(test_refresh_phase == 3),')
    bench.write_text(text)
    changed = {n: sha(work/n) for n, h in before.items() if sha(work/n) != h}
    assert set(changed) == {module, str(machine.relative_to(work)), str(bench.relative_to(work))}
    (out/'inputs.json').write_text(json.dumps({'changed_from_posted_candidate': changed,
        'posted_promotion_inputs_sha256': sha(promotion/'promotion-inputs.json'),
        'baseline_source_sha256': before, 'cpu_config_caches_controller_unchanged': True,
        'production_modified': False}, indent=2)+'\n')
    print('COMBINED_PRIVATE_CANDIDATE_READY', work)


if __name__ == '__main__':
    main()
