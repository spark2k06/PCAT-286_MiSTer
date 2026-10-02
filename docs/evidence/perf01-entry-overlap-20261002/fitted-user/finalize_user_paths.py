"""Verify immutable user artifacts and summarize bounded TimeQuest paths."""
from pathlib import Path
import hashlib
import json
import sys

run=Path(__file__).resolve().parent
root=run.parents[1]
review=root/'build/perf01-entry-overlap-userfit-review-20261002'
work=review/'work'
reports=work/'review-paths'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((review/'manifest.json').read_text())
assert all(sha(work/n)==h for n,h in manifest['source_sha256'].items())
changed=[n for n,h in manifest['fit_sha256'].items() if sha(work/n)!=h]
assert changed==['db/PCAT-286.cmp.rdb'],changed
# TimeQuest regenerated this private database while adding reports. All 22
# other preserved artifacts and every original project artifact remain intact.
assert all(sha(root/n)==h for n,h in manifest['fit_sha256'].items())
verification={'original_fitted_artifacts_unchanged':True,
 'unchanged_private_fitted_artifacts':len(manifest['fit_sha256'])-len(changed),
 'changed_private_database_files':{n:{'before':manifest['fit_sha256'][n],'after':sha(work/n)} for n in changed},
 'source_files_unchanged':True,'source_file_count':len(manifest['source_sha256']),
 'scope':'Bounded TimeQuest extraction; no synthesis, fitting, RTL/SDC change or regression.',
 'original_wrapper_guard':'Rejected .cmp.rdb mutation; final verifier explicitly records it and verifies original project plus all other artifacts.',
 'reports_sha256':{str(p.relative_to(reports)):sha(p) for p in sorted(reports.rglob('*')) if p.is_file()}}
(review/'path-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
sys.path.insert(0,str(root/'scripts'))
from summarize_at_50mhz_timing import parse_report
summaries={}
for directory in sorted(p for p in reports.iterdir() if p.is_dir()):
    summaries[directory.name]={}
    for p in directory.glob('*.rpt'):
        if not p.stem.endswith(('_setup','_hold')):
            continue
        parsed=parse_report(p)
        summaries[directory.name][p.stem]=parsed
        if p.stem in ('clk50_setup','global_hold','code_setup','data_setup','bridge_setup','port_setup'):
            first=parsed['top_paths'][0]
            print(directory.name,p.stem,first['slack_ns'],
                  first['from'].rsplit('|',1)[-1],'->',first['to'].rsplit('|',1)[-1],
                  'levels=',parsed.get('logic_levels'), 'cell=',parsed.get('data_cell_delay_ns'),
                  'IC=',parsed.get('data_ic_delay_ns'),flush=True)
(review/'path-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
print('P17_USER_ORIGINAL_ARTIFACTS_VERIFIED',len(manifest['fit_sha256']),flush=True)
