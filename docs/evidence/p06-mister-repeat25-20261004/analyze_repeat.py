import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'SW/CPUTIME'))
from analyze_p06_physical_reference import stats
from validate_t286ref import validate_csv, VALIDATOR_SHA256

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
new = Path('D:/Desktop/REF_25.CSV')
old = ROOT/'docs/evidence/p06-mister-reference-20261004/raw/REF_25.CSV'
twenty = ROOT/'docs/evidence/p06-mister-reference-20261004/raw/REF_20.CSV'
new_validation = validate_csv(new.read_text(encoding='ascii'), '25')
old_validation = validate_csv(old.read_text(encoding='ascii'), '25')
twenty_validation = validate_csv(twenty.read_text(encoding='ascii'), '20')
ns, os, ts = stats(new_validation), stats(old_validation), stats(twenty_validation)
rows = []
for case in ('R0','B0','M0'):
    for kind in ('baseline','gross'):
        before, after = os[case][kind]['median_ticks'], ns[case][kind]['median_ticks']
        assert before == after
        rows.append(dict(case=case,kind=kind,old_median_ticks=before,
                         repeated_median_ticks=after,delta_ticks=after-before,
                         delta_percent=100*(after/before-1)))
dest = ROOT/'docs/evidence/p06-mister-repeat25-20261004'
dest.mkdir(exist_ok=False)
(dest/'.gitattributes').write_text('* -text -whitespace\n')
(dest/'REF_25.CSV').write_bytes(new.read_bytes())
assert sha(dest/'REF_25.CSV') == sha(new)
record = dict(status='MISTER_REPEAT25_RAW_VALIDATION_PASS_ANOMALY_CONFIRMED',
    source_path=str(new),source_sha256=sha(new),old_source_sha256=sha(old),
    twenty_source_sha256=sha(twenty),validator_sha256=VALIDATOR_SHA256,
    user_confirmation='Same p06-osd-allfeatures-seed1-v2-fit-20261004 RBF; selected 25 MHz and reset. Repeated capture explicitly confirmed by user.',
    validation=new_validation,statistics=ns,comparisons=rows,
    r0_vs20=dict(median25=ns['R0']['gross']['median_ticks'],
        median20=ts['R0']['gross']['median_ticks'],
        elapsed_percent_difference=100*(ns['R0']['gross']['median_ticks']/ts['R0']['gross']['median_ticks']-1)),
    scope='Raw fixed-work validation under existing nominal PIT assumptions, not calibrated CPU cycles or timing closure. No native 86Box 25 MHz T286REF measurement available. No RTL or profile retuning.')
(dest/'analysis.json').write_text(json.dumps(record,indent=2)+'\n')
(dest/'analyze_repeat.py').write_bytes(Path(__file__).read_bytes())
manifest = dict(status=record['status'],artifacts={p.name:sha(p) for p in dest.iterdir() if p.is_file()})
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(record['status'], len(new_validation['samples']), record['r0_vs20'])
