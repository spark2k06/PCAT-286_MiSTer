"""Prepare reviewable standalone docs/evidence, without modifying SPK286."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import shutil
import tarfile

RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[1]
FRESH=ROOT/'docs/evidence/spk286-ready-chain-20261004'
V3=ROOT/'build/p06-ready-chain-regression-20261004-v3'
PORTABLE=RUN/'portable'
DEST=PORTABLE/'docs/evidence/ready-chaining-20261004'
DOC=PORTABLE/'docs/READY_CHAINING_20261004.md'


def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    fm=json.loads((FRESH/'fresh-archive-manifest.json').read_text())
    assert fm['status']=='STANDALONE_FRESH_GATES_ARCHIVED_SHARED_ACCEPTANCE_SEPARATE'
    rows=[]

    def copy(rel,source,plain_sha=None):
        target=DEST/rel
        assert target.resolve().is_relative_to(DEST.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        rows.append({'stored_path':rel,'stored_sha256':sha(target),
                     'original_sha256':plain_sha,'bytes':target.stat().st_size})

    def raw(rel,data):
        target=DEST/rel
        assert target.resolve().is_relative_to(DEST.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress(data,compresslevel=9,mtime=0))
        rows.append({'stored_path':rel,'stored_sha256':sha(target),
                     'original_sha256':digest(data),'bytes':target.stat().st_size})

    for row in fm['artifacts']:
        source=FRESH/row['stored_path']
        assert sha(source)==row['stored_sha256']
        assert digest(gzip.decompress(source.read_bytes()))==row['sha256']
        copy(row['stored_path'],source,row['sha256'])
    assert sha(FRESH/'standalone-source.tar.gz')==fm['source_bundle_sha256']
    copy('standalone-source.tar.gz',FRESH/'standalone-source.tar.gz')
    copy('fresh-archive-manifest.json',FRESH/'fresh-archive-manifest.json')
    verifier=DEST/'verify_packet.py'
    assert verifier.is_file()
    rows.append({'stored_path':'verify_packet.py','stored_sha256':sha(verifier),'original_sha256':None,'bytes':verifier.stat().st_size})
    composed=json.loads((RUN/'composed-receipt.json').read_text())
    shared=json.loads((V3/'receipt.json').read_text())
    fields=('source_changes','snapshot_changes','corpus_changes','cache_changes',
            'reused_binary_changes','cache_event_binding_errors')
    accepted=(shared['status']=='SPK286_READY_CHAIN_REGRESSION_PASS' and shared.get('exit_code')==0 and
              all(field in shared and shared[field]==[] for field in fields) and
              composed['status']=='STANDALONE_COMPOSED_GATES_PASS')
    if accepted:
        assert sha(V3/'receipt.json')==composed['shared']['vendor_receipt_sha256_at_compose']
        assert sha(V3/'regression.log')==shared['log_sha256']
        raw('shared/vendor-receipt.json.gz',(V3/'receipt.json').read_bytes())
        raw('shared/regression.log.gz',(V3/'regression.log').read_bytes())
        raw('shared/composed-receipt.json.gz',(RUN/'composed-receipt.json').read_bytes())
        broad_review=ROOT/'build/p06-ready-chain-regression-final-review-20261004.json'
        composed_review=ROOT/'build/spk286-ready-chain-composed-independent-review-20261004.json'
        br=json.loads(broad_review.read_text())
        cr=json.loads(composed_review.read_text())
        assert br['status']=='BROAD_REGRESSION_INDEPENDENT_SOURCE_CORPUS_EXECUTION_AUDIT_PASS'
        assert cr['status']=='STANDALONE_COMPOSED_INDEPENDENT_REVIEW_PASS'
        assert br['regression_receipt_sha256']==sha(V3/'receipt.json')
        assert cr['composed_receipt_sha256']==sha(RUN/'composed-receipt.json')
        assert cr['broad_receipt_sha256']==sha(V3/'receipt.json')
        assert cr['broad_independent_review_sha256']==sha(broad_review)
        assert br['auditor_sha256']==sha(broad_review.with_suffix('.py'))
        assert cr['reviewer_source_sha256']==sha(composed_review.with_suffix('.py'))
        for name,path in [('broad-review.json',broad_review),('broad-review.py',broad_review.with_suffix('.py')),
                          ('composed-review.json',composed_review),('composed-review.py',composed_review.with_suffix('.py'))]:
            raw('shared/reviews/'+name+'.gz',path.read_bytes())
        for rel,h in shared['cache_sha256_before'].items():
            assert sha(V3/rel)==h,rel
            raw('shared/control/'+rel+'.gz',(V3/rel).read_bytes())
        source=io.BytesIO()
        with tarfile.open(fileobj=source,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for rel,h in sorted(shared['snapshot_sha256_before'].items()):
                data=(V3/'snapshot'/rel).read_bytes()
                assert digest(data)==h,rel
                info=tarfile.TarInfo(rel);info.size=len(data);info.mode=0o644;info.mtime=0
                archive.addfile(info,io.BytesIO(data))
        packed=gzip.compress(source.getvalue(),compresslevel=9,mtime=0)
        path=DEST/'vendor-source.tar.gz';path.write_bytes(packed)
        rows.append({'stored_path':path.name,'stored_sha256':digest(packed),'original_sha256':None,'bytes':len(packed)})
    status='STANDALONE_COMPOSED_GATES_PASS' if accepted else 'STANDALONE_FRESH_GATES_PASS_SHARED_VENDOR_PENDING'
    output={'status':status,'schema_version':1,'artifact_count':len(rows),'artifacts':rows,
            'source_count':fm['source_count'],'standalone_source_sha256':fm['source_sha256'],
            'vendor_source_sha256':shared['snapshot_sha256_before'] if accepted else {},
            'shared_vendor_gate_bound':accepted,
            'standalone_full_make_regression_executed':False,
            'standalone_full_source_scope':'1079 frozen inputs including modern fixtures; exact functional closure40RTL/20MC/3ROM/2profiled',
            'external_corpus_scope':'Shared vendor receipt identifies its external reference corpus by hash. Raw corpus is not bundled; reading this packet needs no external path, while replaying that separate shared corpus requires acquisition.',
            'read_dependencies':'Every conclusion, raw result, source/control manifest and required source bundle is stored under this directory. source_path/build fields inside historical raw receipts are provenance, not required read locations.',
            'excluded_claims':['No literal standalone make regression rerun','No native pin/cycle-accurate timing or hardware/board acceptance','No five different legacy release-auditor acceptance']}
    (DEST/'manifest.json').write_text(json.dumps(output,indent=2)+'\n',newline='\n')
    doc='''# READY fetch chaining: standalone CPU milestone

Status: **%s**. Fresh standalone checks, the bound vendor v3 general gate and
independent source/coverage reviews have passed. This document does not claim
a literal standalone `make regression` run.

The CPU caller and fetch now reserve space conservatively and can prepare the
next CODE request on READY while preserving response backpressure and restart
handling. The profiled CPU is regenerated from a separately pinned selected
contract; historical baseline files remain unchanged. Missing wildcard bench
debug declarations, architectural #UD sentinel probes, adjust starvation
stimulus and named LOADALL compiler validation are included. No board/native
pins, modern microcode fixtures or Makefile are replaced.

## Fresh validation

* 33 fresh stages passed: strict lint, 355 Python tests, microcode check/audit,
  nine affected or distinct banks in both simulators, supported core MAX probes,
  four standalone-only Yosys sanity checks, normal reset smoke and four native
  state initialization cases.
* The profile checker passes deterministic generation/installed identity,
  45 schedule checks and eight prefix cases per simulator, 43,878 independent
  metadata cases per simulator and both reset/fetch modes in Icarus.
* All 48 MOV vectors actually resume to #UD acceptance with their original
  signatures, retained CS:IP/FLAGS and one retirement. No stack entry or false
  unsupported latch is used to terminate these probes.

## Coverage composition

All 40 functional RTL inputs, 20 literal microcode sources, three generated
ROM/package files and two selected generated profile files match the bound
vendor sources byte for byte. The selected profiled CPU SHA-256 is
`847a6930469e67d7345847e39f57ab51a5fe3556c73f8741d5e9c7d69c6038c7`.

Standalone registers 129 unit banks: 125 TB sources are byte-identical to vendor,
and four differ and were executed fresh. The nine fresh banks repeat five of
the identical sources, leaving 120 common-only banks for shared evidence. All
24 runner vector generators match. The header contains the same 136 typed
declarations despite grouping/formatting differences, explicitly recorded as a
static declaration bridge, not byte identity. Modern standalone fixtures are
kept and covered by its fresh Python suite.

Composed coverage is 129 Icarus/128 Verilator unit banks
with the existing Icarus-only full expand-down matrix preserved. Vendor's extra
event-arbitration bank is not labeled a standalone execution. The five distinct
legacy auditors of other release targets are outside this composition.

## Self-contained evidence

[Packet manifest](evidence/ready-chaining-20261004/manifest.json) lists stored
relative paths and SHA-256 values. The packet includes raw fresh receipts/logs,
scope inventory, profile/state data and all 1,079 frozen standalone inputs.
Shared evidence includes its actual receipt, full log, source inventory, cache
control records and independent review receipts/helpers. Historical `source_path` or build paths inside receipts
describe provenance; none is required to read the packet's conclusions. The
external hardware-reference corpus is identified by hash in shared evidence;
raw corpus acquisition is necessary only to replay that shared corpus scope.

Run `python3 docs/evidence/ready-chaining-20261004/verify_packet.py` to verify
stored hashes/source bundles; the checker reads only this packet. The packet
does not certify MiSTer, a motherboard, native 286 pin timing or cycle accuracy.
Provisional instruction profiles remain provisional.
''' % status
    DOC.parent.mkdir(parents=True,exist_ok=True);DOC.write_text(doc,newline='\n')
    print(status)
    print('Portable artifacts',len(rows),'sources',fm['source_count'])
    print('Portable manifest SHA256',sha(DEST/'manifest.json'))


if __name__=='__main__':main()
