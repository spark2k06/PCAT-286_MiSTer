"""Reproduce conditional fixed-work comparisons from selected native receipts and MiSTer analysis."""
from pathlib import Path
import argparse,hashlib,json

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def compare(native_path,mister_path):
    native=json.loads(native_path.read_text())
    mister=json.loads(mister_path.read_text())
    assert native['status']=='ALL_SEVEN_NATIVE_PROFILES_AUTO_AND_VISIBLE_ZERO_GUEST_AND_HOST_PASS'
    assert mister['status']=='EIGHT_MISTER_READY_CHAIN_PROFILES_RAW_PASS_MONOTONIC_CALIBRATION_OPEN'
    observations=[]
    for label in ['6','8','10','12.5','16','20','25']:
        capture=mister['captures'][label]
        validation=capture['validation']
        assert validation['sample_count']==42 and validation['summary_count']==6
        assert validation['status']=='T286REF_RAW_FIXED_WORK_VALIDATION_PASS'
        assert validation['timer_calibrated'] is False
        assert all(validation['controls'].values())
        sm={(s['case'],s['kind']):s for s in validation['summaries']}
        for setting in ['auto','ws0']:
            control=next(r for r in native['runs'] if r['cpu_label']==label and (r['visible_wait_states'] is None)==(setting=='auto'))
            sn={(s['case'],s['kind']):s for s in control['summaries']}
            for case in ['R0','B0','M0']:
                for kind in ['baseline','gross']:
                    v_mister=sm[(case,kind)]['median_ticks']
                    v_native=sn[(case,kind)]['median_ticks']
                    observations.append({'profile':label,'native_hz':control['hz'],
                        'native_selection':setting,'case':case,'kind':kind,
                        'mister_median_ticks':v_mister,'native_median_ticks':v_native,
                        'delta_ticks_mister_minus_native':v_mister-v_native,
                        'mister_elapsed_percent_relative_to_native':100*(v_mister/v_native-1),
                        'mister_min_max':[sm[(case,kind)]['min_ticks'],sm[(case,kind)]['max_ticks']],
                        'native_min_max':[sn[(case,kind)]['min_ticks'],sn[(case,kind)]['max_ticks']],
                        'mister_raw_identity':capture['raw'],
                        'native_csv_sha256':control['csv_sha256'],
                        'native_reused_archive':control['reused_archive']})
    return {'status':'NATIVE_ALL_PROFILES_MISTER_GROSS_AND_BASELINE_COMPARISON_REPRODUCED',
        'inputs':{'native_verification_sha256':sha(native_path),'mister_analysis_sha256':sha(mister_path)},
        'mister_analysis_reference':'docs/evidence/p06-mister-ready-chain-20261005/analysis.json',
        'mister_analysis_status':mister['status'],'mister_candidate':mister['candidate'],
        'units':'Elapsed PIT input ticks conditional on assumed divisor 65536',
        'formula':'100 * (MiSTer median ticks / native median ticks - 1)',
        'positive_means':'MiSTer takes more elapsed ticks for the same fixed work',
        'profile_labels_associated_not_clock_calibrated':True,
        'frequency_normalization_applied':False,
        'baseline_subtraction_applied':False,
        'matched_historical_profiles':7,'comparison_count':84,'observations':observations}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path,required=True)
    p.add_argument('--mister',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=compare(a.native,a.mister)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
