from pathlib import Path
import hashlib,json,shutil,sys
from validate_t286ref import validate_csv
from compare_native_mister import compare

root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
archive=root/'docs/evidence/p06-native-allprofiles-20261005'
report=root/'docs/optimization/P06_NATIVE_ALL_PROFILES_20261005.md'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

verification=json.loads((work/'verification.json').read_text())
assert verification['status']=='ALL_SEVEN_NATIVE_PROFILES_AUTO_AND_VISIBLE_ZERO_GUEST_AND_HOST_PASS'
preflight=json.loads((work/'preflight.json').read_text())
for group in ['source_files','rom_files','identities']:
    assert all(sha(Path(entry['path']))==entry['sha256'] for entry in preflight[group].values())
assert not archive.exists(),'Use a fresh archive; no existing evidence may be replaced'
archive.mkdir()
manifest={'status':verification['status'],'sample_count':588,'summary_count':84,
          'actual_profiles_hz':[6000000,8000000,10000000,12500000,16000000,20000000,25000000],
          'board':'[ISA] MR BIOS 286 clone','machine':'mr286','ram_kib':2048,
          'program_sha256':preflight['identities']['program']['sha256'],
          'binary_sha256':preflight['identities']['native_executable']['sha256'],
          'source_disk_sha256':preflight['identities']['source_dos_disk']['sha256'],
          'source_base_commit':preflight['source_base_commit'],
          'selected_controls':{},'source_rom_hashes_before_and_after_match':True,
          'timer_qualification':'NOT_CALIBRATED','pit_divisor':'65536_ASSUMED_STANDARD_BIOS',
          'emulator_and_disk_copies_archived':False,'artifacts':{}}
canonical_exe=Path('/mnt/d/GitHub/86Box_dev/build/spk286/native-50mhz-reference/86Box-native')
assert sha(canonical_exe)==manifest['binary_sha256']
manifest['canonical_original_native_executable']={'path':str(canonical_exe),'sha256':sha(canonical_exe)}
for control in verification['runs']:
    source=Path(control['source_directory'])
    selection='auto' if control['visible_wait_states'] is None else 'ws0'
    label=f"native{control['cpu_label']}-{selection}"
    dest=archive/label
    dest.mkdir()
    for name,expected in control['artifacts'].items():
        assert sha(source/name)==expected,(source,name)
        shutil.copy2(source/name,dest/name)
    shutil.copytree(source/'nvr-initial',dest/'nvr-initial')
    assert {p.name:sha(p) for p in (dest/'nvr-initial').iterdir()}==control['initial_nvr_sha256']
    if (source/'nvr').is_dir() and not control['reused_archive']:
        shutil.copytree(source/'nvr',dest/'nvr-final')
    if (source/'screenshots').is_dir():
        shutil.copytree(source/'screenshots',dest/'screenshots')
    receipt=json.loads((dest/'measurement.json').read_text())
    parsed=validate_csv((dest/'REF.CSV').read_bytes().decode('cp437'),receipt['cpu_label'])
    assert parsed==receipt['csv_validation'] and parsed['sample_count']==42 and parsed['summary_count']==6
    assert receipt['emulator_returncode']==0 and receipt['guest_success'] and receipt['failure'] is None
    entry=dict(control)
    entry['archive_directory']=label
    manifest['selected_controls'][label]=entry
    log=work/(source.name+'-run.log')
    if log.exists():shutil.copy2(log,dest/'runner.log')
for name in ['preflight.json','verification.json','run_native_reference_allprofiles.py','run_all.py','preflight.py','seal_native.py','validate_t286ref.py','compare_native_mister.py','reproduce_native.py','disk-allocation-before-cleanup.json']:
    shutil.copy2(work/name,archive/name)
sources=archive/'source'
sources.mkdir()
for name in ['t286ref.asm','build_t286ref.py','check_t286ref_math.py','run_native_reference.py']:
    shutil.copy2(root/'SW/CPUTIME'/name,sources/name)
shutil.copy2(root/'docs/evidence/p06-timing-reference-20261003/T286REF.COM',archive/'T286REF.COM')
shutil.copy2(root/'docs/evidence/p06-timing-reference-20261003/T286REF.lst',archive/'T286REF.lst')
for name,entry in preflight['source_files'].items():
    dest=sources/'86box'/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(Path(entry['path']),dest)
    assert sha(dest)==entry['sha256']

comparison=compare(work/'verification.json',root/'docs/evidence/p06-mister-ready-chain-20261005/analysis.json')
(archive/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
manifest['mister_comparison_input_sha256']=comparison['inputs']['mister_analysis_sha256']
preparation=archive/'preparation-only'
preparation.mkdir()
attempt=work/'native8-auto-calibration'
for name in ['initial-86box.cfg','86box.cfg','global.cfg']:
    shutil.copy2(attempt/name,preparation/name)
(preparation/'receipt.json').write_text(json.dumps({
    'status':'PREPARATION_FAILED_BEFORE_EMULATOR_LAUNCH',
    'reason':'Archived profile had nvr-initial rather than nvr; private runner corrected to select nvr-initial when present',
    'failed_operation':'shutil.copytree(a.profile / nvr, out / nvr)',
    'exception':'FileNotFoundError', 'emulator_launched':False,
    'source_profile':'docs/evidence/p06-physical-reference-20261004/native/native6-ws0',
    'private_disk_logical_bytes':(attempt/'dos-test.img').stat().st_size,
    'private_disk_sha256':sha(attempt/'dos-test.img'),
    'private_disk_archived':False},indent=2)+'\n')
comparison_rows=[]
for label in ['6','8','10','12.5','16','20','25']:
    gross=[r for r in comparison['observations'] if r['profile']==label and r['kind']=='gross']
    zero=[next(r for r in gross if r['case']==case and r['native_selection']=='ws0') for case in ['R0','B0','M0']]
    auto=[next(r for r in gross if r['case']==case and r['native_selection']=='auto') for case in ['R0','B0','M0']]
    ticks='/'.join(str(r['mister_median_ticks']) for r in zero)
    pct_zero=' / '.join(f"{r['mister_elapsed_percent_relative_to_native']:+.2f}%" for r in zero)
    pct_auto=' / '.join(f"{r['mister_elapsed_percent_relative_to_native']:+.2f}%" for r in auto)
    comparison_rows.append(f'| {label} | {ticks} | {pct_zero} | {pct_auto} |')

rows=[]
for hz in manifest['actual_profiles_hz']:
    for selection in ['auto','ws0']:
        control=next(r for r in verification['runs'] if r['hz']==hz and (r['visible_wait_states'] is None)==(selection=='auto'))
        sums={(s['case'],s['kind']):s for s in control['summaries']}
        gross=[sums[(case,'gross')]['median_ticks'] for case in ['R0','B0','M0']]
        baseline='/'.join(str(sums[(case,'baseline')]['median_ticks']) for case in ['R0','B0','M0'])
        last=control['runtime_samples'][-1]
        setting='Automatic' if selection=='auto' else 'Visible 0 waits'
        service='/'.join([str(control['service'])]*3)
        origin='Archived 2026-10-04' if control['reused_archive'] else 'New 2026-10-05'
        rows.append(f"| {control['cpu_label']} | {setting} | {control['config']} | {service} | {last['cpu_isa_speed']:,} / {last['isa_cycles']} | {baseline} | {gross[0]} | {gross[1]} | {gross[2]} | {origin} |")

readme='''# P06 native all-profile evidence, 2026-10-05

Fourteen selected controls cover actual 6/8/10/12.5/16/20/25 MHz with Automatic
and the visible zero-wait override. All have guest and host exit 0, 42 valid
samples and six recomputed summaries. The 6 and 12.5 MHz visible-zero receipts
are reused unchanged from the 2026-10-04 physical-reference native bundle.
All Automatic controls have newly sampled disabled internal/external caches.

`verification.json` contains the selected statistics, runtime fields, hashes
and provenance. `preflight.json` freezes source, executable, ROM and DOS-disk
identity. Each control retains byte-exact CSV/status/receipts, initial/final
configuration, startup/runtime samples, logs and initial CMOS. New controls
also retain final CMOS. The emulator executable and private disks are excluded.
The initial preparation-only error is retained without its temporary disk.

`T286REF.COM` is the same frozen 2,840-byte program. Source snapshots and the
private diagnostic runner are retained; production RTL and DOS program were
not changed. Native-source files and ROM hashes match the earlier archive.
`run_all.py` is the exact orchestration source used for the original captures.
Use the relocatable `reproduce_native.py` for a fresh control, with Python,
pyfatfs and nm installed. The named original binary, ROM directory and DOS VHD
must remain available; the wrapper checks their expected hashes and the runner
refuses to overwrite existing output directories.

```text
python3 reproduce_native.py --output /mnt/d/GitHub/PCAT-286_MiSTer/build/p06-native-reproduce/native8-auto --disk /mnt/d/ISOs/MiSTer/286_win3.1.vhd --exe /mnt/d/GitHub/86Box_dev/build/spk286/native-50mhz-reference/86Box-native --roms /mnt/d/Desktop/86Box/roms --profile 8 --selection auto
```

Each selected profile retains its initial CMOS. For 20/25 MHz, an observed MR
BIOS speed-change prompt can require Enter and then F10 in setup. The runner's
explicit `control.json` interface accepts `{"screenshot":true}` and, after
observing the prompt, `{"key":"enter"}` or `{"key":"f10"}`. These operate only
the owned emulator. Record and retain the reproduction receipts and raw CSV.

Owned-emulator BIOS acknowledgment screenshots, when needed, remain with the
corresponding control alongside the runner's recorded keyboard events.

`comparison.json` records 84 direct gross/baseline comparisons with the
already committed MiSTer ready-chain analysis, whose complete source hash is
recorded. The user captures are not copied into this native evidence bundle.
Reproduce with:

```text
python compare_native_mister.py --native verification.json --mister ../p06-mister-ready-chain-20261005/analysis.json --output reproduced-comparison.json
```

Times are gross PIT input ticks for fixed 256-iteration work, including timer,
setup, loop and signature-store overhead. Baselines are independent samples.
The PIT remains NOT_CALIBRATED with nominal 1,193,182 Hz and assumed divisor
65536. This bundle is an emulator reference, not physical instruction timing
or certification of the historical FPGA profiles.
'''
(archive/'README.md').write_text(readme)
for path in sorted(archive.rglob('*')):
    if path.is_file():manifest['artifacts'][path.relative_to(archive).as_posix()]={'sha256':sha(path),'bytes':path.stat().st_size}
(archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
text='''# P06/P12: native original-286 controls for all historical frequencies

Date: 2026-10-05. All seven actual native CPU frequencies now have Automatic
and visible-zero controls using the unchanged `T286REF2` program. Fourteen
selected controls have **guest exit 0 and host exit 0**, 588 validated samples
and 84 independently recomputed summaries. Twelve controls were executed in
this session; the strong visible-zero 6/12.5 MHz receipts were reused from
2026-10-04. Automatic 6/12.5 MHz were repeated because the older Automatic
runner had not sampled the cache flags.

## Native results

Elapsed **PIT input ticks**, medians of seven samples per case/kind with 256
iterations. Gross includes instrumentation, setup, LOOP and signature stores;
no baseline is subtracted. Lower ticks mean less elapsed time for this work.
All samples observed binary PIT mode 2 and disabled internal/external caches.

| Actual CPU MHz | Selection | Stored config | Prefetch/read/write service cycles | ISA Hz / ISA cycles | Baselines R0/B0/M0 | R0 gross | B0 gross | M0 gross | Receipt |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
'''+ '\n'.join(rows)+'''

`cpu_waitstates=0` is **Automatic**. The visible zero-wait override stores 1
and selects service costs 2/2/2. Automatic selects 2/2/2 at 6/8/10 MHz,
3/3/3 at 12.5/16 MHz and 4/4/4 at 20/25 MHz. These are native model service
costs, not the number of extra READY waits on physical pins. Intrinsic
instruction and prefetch timing remain active. The ordinary table entry
labelled `12` runs at **12,500,000 Hz**; this report does not call it 12 MHz.

The visible-zero controls provide a consistent memory-service comparison
across CPU clocks. Automatic changes the service cost at two frequency
boundaries, so its elapsed-time curve is not a pure frequency scaling curve.
Full min/median/max and every raw repetition remain in the evidence bundle.

## Direct comparison with the new MiSTer captures

The [2026-10-05 MiSTer analysis](../evidence/p06-mister-ready-chain-20261005/analysis.json)
associates the captures with the ready-chain candidate RBF. Its independently
loaded RBF identity remains unobserved, the clocks remain uncalibrated, and
the candidate's recorded fixed-50-MHz fit timing remains failed. The following
descriptive comparison pairs matching profile labels and identical fixed
work; it does not prove equal measured oscillators or identical board waits.
Native 12.5 MHz is compared directly with the MiSTer 12.5 profile; no physical
12 MHz scaling is used here.

Percentages are `100 * (MiSTer ticks / native ticks - 1)` for gross medians.
A positive value means MiSTer takes more elapsed time. Triplets are R0/B0/M0.
Each native reference retains its recorded service cost and ISA cadence.

| Profile MHz | MiSTer gross ticks R0/B0/M0 | Relative to native visible zero R0/B0/M0 | Relative to native Automatic R0/B0/M0 |
| --- | --- | --- | --- |
'''+ '\n'.join(comparison_rows)+'''

Relative to the common two-service-cycle native controls, R0 and B0 take
less elapsed time in every MiSTer profile. M0 also takes less through 16 MHz,
then takes more at 20 and 25 MHz. This is workload-specific disagreement;
matching one headline throughput value would leave the other cases different.
Automatic's extra service costs at higher frequencies make its elapsed times
larger and therefore change the descriptive percentage comparison.

All 84 case/kind/selection comparisons, baseline medians, spreads, CSV hashes
and the MiSTer analysis hash are recorded in
[comparison.json](../evidence/p06-native-allprofiles-20261005/comparison.json).
The percentages use raw fixed-work gross values, with no baseline subtraction
or conversion into isolated CPU instruction cycles.

## Identity, environment and execution

Runtime samples verify the native `exec386_2386` dispatcher, actual CPU Hz,
wait-state config, all three service fields, both disabled cache flags,
`timing_rr=2`, ISA speed and ISA cycles. Each new run cloned the input VHD
into its own private image under `build/p06-native-allprofiles-20261005`,
booted plain DOS with `FILES=20, BUFFERS=10`, and ran the program from AUTOEXEC
without the source image's memory managers or TSRs. The board was
`[ISA] MR BIOS 286 clone` (`mr286`), 2 MiB RAM and IBM EGA.

The 2,840-byte DOS program SHA-256 is
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.
The original native executable SHA-256 is
`2d87185ff14842a20a2bd0fed1713820dd64eabaa049b08a9827b48948de4dd3`.
Its existing unused 50 MHz test entry remains part of that binary. Source base
is `fa3343da5b551bc937114c1e3ab3a8e16aed9e79`; all frozen backend-source and
selected ROM hashes match the 2026-10-03 archive before and after these runs.
The readonly input DOS VHD SHA-256 remained
`cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f`.

Only a private diagnostic runner copy was extended to accept all seven Hz
values, record the initial config immediately, and accept archived initial
CMOS directories. The unchanged validator recomputes every CSV. Each owned
emulator was paused after guest completion and exited; process absence and
host code 0 were checked after every new run. No user VHD, unrelated emulator
instance, production CPU/RTL, historical policy, clock or Quartus output was
changed. No commits were made.

The 20/25 MHz controls required the observed MR BIOS oscillator-change
acknowledgment followed by F10 in setup before DOS boot. Each corresponding
receipt records those keyboard events; the native screenshots remain archived.
Both the selected guest CSV and host teardown subsequently passed. A first
8 MHz preparation attempt pointed at an archive containing `nvr-initial`
rather than `nvr`, and stopped before any emulator was launched; its receipt
and configs are preserved without the temporary disk. No measured control in this session failed
guest validation or host teardown.

## Evidence and limits

The [native evidence bundle](../evidence/p06-native-allprofiles-20261005/README.md)
contains raw CSVs, guest status, runtime/start/measurement receipts, hashes,
logs, initial/final configs, initial CMOS, new-run final CMOS, frozen source
and private runner. Its [manifest](../evidence/p06-native-allprofiles-20261005/manifest.json)
and [verification](../evidence/p06-native-allprofiles-20261005/verification.json)
identify reused versus newly executed controls. Executable/VHD copies were
temporary in the private build workspace and are excluded from this archive.
The temporary workspace is removed after archive verification; the original
native binary is retained outside it at
`D:/GitHub/86Box_dev/build/spk286/native-50mhz-reference/86Box-native`.

The PIT/crystal and reload are not independently calibrated: nominal input
1,193,182 Hz and divisor 65536 are recorded assumptions. Endpoints cannot
exclude whole-period stalls. No MHz inference, isolated instruction-cycle
claim, physical-board READY model or historical-profile certification is
made from these fixed-work measurements. The existing native BIOS diagnostic
at F000:C3D4 and host library warnings remain visible in the logs; clean guest
and host exits do not imply warning-free logs. The physical 6/12 MHz anchors
remain separately qualified in the prior physical report.
'''
report.write_text(text)
print('SEALED',archive,report,flush=True)
