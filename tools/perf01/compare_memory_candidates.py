"""Compare completed CHECKNUM runs using two explicitly identified PCAT memory builds."""
import argparse
import json
from pathlib import Path
import re

from summarize_memory_probe import sha, summarize


def identity(arm):
    receipt=json.loads((arm/'spk50/measurement.json').read_text())
    binary=Path(receipt['command'][0])
    manifest=json.loads((binary.parent/'build-manifest.json').read_text())
    assert sha(binary)==manifest['binary_sha256']==receipt['binary_sha256']
    source=manifest['sources_sha256']
    header=next(value for path,value in source.items() if path.endswith('/spk286_memory_probe.hpp'))
    backend=next(value for path,value in source.items() if path.endswith('/src/cpu/spk286_backend.cpp'))
    generated=binary.parent/'pcat_memory_timing.sv'
    assert sha(generated)==source[str(generated)]
    lines=int(re.search(r'CODE_BUFFER_LINES\s*=\s*(\d+)',generated.read_text()).group(1))
    return {'build_manifest_file':str(binary.parent/'build-manifest.json'),
            'build_manifest_sha256':sha(binary.parent/'build-manifest.json'),
            'code_buffer_lines':lines, 'code_buffer_bytes':lines*8,
            'data_buffer_words':manifest.get('data_buffer_words',512),
            'data_buffer_ways':manifest.get('data_buffer_ways',1),
            'profiler_header_sha256':header,'original_backend_sha256':backend,
            'cpu_objects_sha256':manifest['cpu_objects_sha256'],
            'macros':manifest['macros']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-arm',required=True,type=Path)
    p.add_argument('--candidate-arm',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--allow-host-teardown-issue',action='store_true')
    a=p.parse_args()
    arms=[path.resolve() for path in (a.baseline_arm,a.candidate_arm)]
    baseline,candidate=[summarize(path,a.allow_host_teardown_issue) for path in arms]
    assert baseline['pcat_timing'] and candidate['pcat_timing']
    assert baseline['image_sha256_before']==candidate['image_sha256_before']
    runs=[json.loads((path/'probe-run.json').read_text()) for path in arms]
    for key in ('checknum_sha256','config_sha256','nvr_sha256'):
        assert runs[0][key]==runs[1][key], f'Mismatched {key}'
    identities=[identity(path) for path in arms]
    for key in ('profiler_header_sha256','original_backend_sha256','cpu_objects_sha256','macros'):
        assert identities[0][key]==identities[1][key],f'Mismatched {key}'
    result={'baseline':baseline,'candidate':candidate,
        'build_identities':identities,
        'integer_gain_fraction':candidate['dhrystones_per_second']/baseline['dhrystones_per_second']-1,
        'math_gain_fraction':candidate['kwhetstones_per_second']/baseline['kwhetstones_per_second']-1,
        'limitations':['Memory timing/control co-simulation; guest values and peripherals remain in 86Box.',
            'Single completed run per build; no hardware speedup or FPGA timing is established.',
            'Adaptive iteration counts differ; compare rates and per-transfer behavior, not absolute phase work.',
            'Bus wait totals overlap internal CPU execution.']}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'baseline_scores':[baseline['dhrystones_per_second'],baseline['kwhetstones_per_second']],
        'candidate_scores':[candidate['dhrystones_per_second'],candidate['kwhetstones_per_second']],
        'integer_gain_fraction':result['integer_gain_fraction'],'math_gain_fraction':result['math_gain_fraction']},indent=2))


if __name__=='__main__':
    main()
