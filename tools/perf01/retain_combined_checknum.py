#!/usr/bin/env python3
"""Verify and retain completed P18/P19 CHECKNUM platform-model evidence."""
import argparse
import json
from pathlib import Path

from compare_memory_candidates import identity
from retain_posted_followup import retain, sha
from summarize_memory_probe import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--combined-run', type=Path, required=True)
    parser.add_argument('--old-refresh-run', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    combined = args.combined_run.resolve()
    old = args.old_refresh_run.resolve()
    arm = combined/'pcat-posted-pit'
    baseline_arm = old/'pcat-at-refresh'
    baseline = summarize(baseline_arm, allow_host_teardown_issue=True)
    candidate = summarize(arm, allow_host_teardown_issue=True)
    contexts = [json.loads((p/'probe-run.json').read_text())
                for p in (baseline_arm, arm)]
    for key in ('initial_image_sha256', 'checknum_sha256', 'config_sha256', 'nvr_sha256'):
        assert contexts[0][key] == contexts[1][key], f'Mismatched {key}'
    assert [p['at_refresh_control'] for p in contexts] == [1, 1]
    identities = [identity(p) for p in (baseline_arm, arm)]
    for key in ('original_backend_sha256', 'cpu_objects_sha256', 'macros',
                'code_buffer_lines', 'data_buffer_words', 'data_buffer_ways'):
        assert identities[0][key] == identities[1][key], f'Mismatched {key}'
    # These experiments deliberately change the platform model and profiler
    # header to observe PIT OUT1. Record their different hashes explicitly.
    assert identities[0]['profiler_header_sha256'] != identities[1]['profiler_header_sha256']
    inputs = json.loads((combined/'inputs.json').read_text())
    assert inputs['at_refresh_source'] == 'real 86Box PIT OUT1'
    assert inputs['posted_writes'] is True
    manifest = json.loads((combined/'probe/build-manifest.json').read_text())
    assert manifest['binary_sha256'] == candidate['binary_sha256']
    assert sha(combined/'probe/86Box-memory-probe') == candidate['binary_sha256']
    for name, digest in manifest['sources_sha256'].items():
        assert sha(Path(name)) == digest, f'Changed model input: {name}'
    comparison = {
        'baseline': baseline, 'candidate': candidate, 'build_identities': identities,
        'matched_context': {key: contexts[0][key] for key in
                            ('initial_image_sha256', 'checknum_sha256', 'config_sha256', 'nvr_sha256')},
        'intentional_changes': ['One-entry posted RAM writes enabled',
                                'AT request source changed from 32-clock timer to real PIT OUT1',
                                'Profiler header observes and drives actual PIT OUT1'],
        'integer_gain_fraction': candidate['dhrystones_per_second']/baseline['dhrystones_per_second']-1,
        'math_gain_fraction': candidate['kwhetstones_per_second']/baseline['kwhetstones_per_second']-1,
        'limitations': ['Guest values and peripherals remain in 86Box; this is a partial platform model.',
                       'One completed run per arm; hardware acceptance and timing closure remain pending.',
                       'Host exit timeout/SIGTERM is classified separately from complete guest RC0/ALL_DONE.'],
    }
    (combined/'complete-comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
    names = ['complete-comparison.json', 'inputs.json', 'probe/build-manifest.json',
             'probe/pcat_memory_timing.sv']
    names += ['pcat-posted-pit/'+name for name in
              ('probe-run.json', 'profiles.json', 'spk50/measurement.json', 'spk50/measurement-start.json',
               'spk50/samples.jsonl', 'spk50/memory-profile.json', 'spk50/memory-profile.json.phases.jsonl',
               'spk50/TICKRUN.TXT', 'spk50/STATUS.TXT', 'spk50/86box.cfg', 'spk50/global.cfg')]
    names += [str(p.relative_to(combined)) for p in (arm/'spk50/nvr-initial').iterdir()]
    names += [str(Path(name).relative_to(combined)) for name in manifest['sources_sha256']
              if Path(name).is_relative_to(combined)]
    retain(combined, args.destination.resolve(), sorted(set(names)))
    print('COMBINED_CHECKNUM_EVIDENCE_PASS',
          candidate['dhrystones_per_second'], candidate['kwhetstones_per_second'])


if __name__ == '__main__':
    main()
