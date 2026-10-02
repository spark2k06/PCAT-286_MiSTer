# P18/P19: combined posted-write and PIT-refresh candidate

Date: 2026-10-02. Status: **RBF generated and verified; hardware acceptance and
50 MHz timing closure pending**. A complete CPU and PCAT regression was
subsequently requested and is running in `build/full-regression-posted-pit-20261002`;
no completed result is claimed yet.

## Artifact and inputs

The user requests both improvements in one RBF. Production milestones are
`15ea7cf` (posted writes) and `6b68667` (PIT channel 1 refresh). The latter is
the frozen synthesis HEAD. Subsequent diagnostic-ROM/documentation commits do
not alter production RTL. All 1207 frozen input files retain their hashes;
344 current production files match the snapshot. CPU RTL, code/data cache
capacity, SDRAM timings and CPU configuration remain unchanged from P17.

Windows export: `D:\GitHub\PCAT-286_MiSTer\build\perf01-posted-pit-rbf-20261002\PCAT-286.rbf`.
Original: the same run's `work/output_files/PCAT-286.rbf`.

- CPU/system clock: **50 MHz**, common clock; **NO_DEBUG** active, CPU DIV2 off.
- CPU options P01/P02/P05/P06/P07 and the RAM-read buffer remain active.
- RBF: **4,091,384 bytes**, generated 2026-10-02 20:00:00 Europe/Madrid.
- SHA-256: `fe79d231d6ace5f4bc9ec49449188a43c8cbab2eb08ee24fd633e30b7ebeecff`.
- Quartus 17.0.2 full compile: **0 errors, 854 warnings**, **36 min 48 s**.
- Fresh isolated work/database/output; no reference bitstream/database reused.
- The exported file is byte-identical to the generated RBF.

## Fitted resources

The preserved P17 RBF/hash and reports supply the baseline. These are fitted
totals, not isolated map estimates or a claim that every global reduction is
intrinsic to the new blocks. Quartus packing/replication changes in unchanged
entities also contribute.

| Resource | P17 | Combined candidate | Difference |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 30,832 | 30,039 / 41,910 (72%) | -793 |
| Physically placed ALMs | 36,191 | 35,676 / 41,910 (85.13%) | -515 |
| Registers | 38,198 | 37,931 | -267 |
| M10K | 416 | 416 / 553 (75%) | 0 |
| Block memory bits | 3,301,019 | 3,301,019 | 0 |
| DSP | 39 | 39 | 0 |
| PLL | 3 | 3 | 0 |

The new posted-write block itself uses **52.3 equivalent ALMs, 51 registers,
73 combinational ALUTs and no block memory**. The corrected refresh requester
uses 10.3 equivalent ALMs / 17 registers; the bridge uses 106.5 / 87. These
hierarchy rows are local blocks and must not be added to parent totals.

## Timing at the configured 50 MHz

| Model | P17 setup, ns | Candidate setup, ns | Candidate hold, ns |
| --- | ---: | ---: | ---: |
| Slow 1100 mV, 100 C | -0.979 | **-1.466** | +0.250 |
| Slow 1100 mV, -40 C | -0.958 | **-1.519** | +0.239 |
| Fast 1100 mV, 100 C | +2.570 | +2.571 | +0.135 |
| Fast 1100 mV, -40 C | +2.735 | +2.733 | +0.120 |

These are whole `FPGA_CLK2_50` summary margins, not CPU-only path selections.
CPU/system hold remains positive. Slow setup worsens by 0.487 / 0.561 ns;
TNS is -287.384 / -342.207 ns. Cold-corner reported Fmax is **46.47 MHz**;
the actual configured clock stays **50 MHz**. This candidate is not closed.
The HDMI PLL source clock also has -0.109 ns setup at Slow -40 C. No negative
hold entry appears in the completed summary.

The worst 50 MHz paths now run from CPU BIU `owner_q.01` through I/O admission
to Sound Blaster DSP `len_left[13/15]`. CPU-only cold setup is -0.976 ns on
prefetch `head_q[0]` to GPR logic. These are recorded targets for later closure;
no false-path/multicycle waiver, constraint change or timing optimization is
introduced for this performance candidate.

## Functional and performance evidence

[P18](P18_ONE_ENTRY_POSTED_WRITES_20261002.md) retains physical-data kernels,
495 physical/bridge/arbiter checks, 145 cache-coherence checks, bridge controls
and real-CPU machine tests. [P19](P19_AT_REFRESH_PLATFORM_ATTRIBUTION_20261002.md)
retains real PIT/clock tests, 27 checks in each simulator, DMA/ownership tests,
accepted-store drain ordering and common/divided-clock CPU diagnostics.
The distributed diagnostic ROM is separately updated to initialize channel 1;
all original POST/IRQ/memory expectations remain required.

The completed matched memory-only CHECKNUM controls are **6138 / 113.6K**
versus **6906 / 121.6K** with posting: +12.51% / +7.04%, both RC0/ALL_DONE.
Those rates omit AT refresh ownership and are not hardware acceptance.

Adding the old production 32-clock AT requester reproduces the user's P17
hardware integer rate: **5666**, versus same-binary control **6138**. The new
combined adapter drives corrected RTL from actual 86Box PIT OUT1 and produces
the first integer result **6906**. Thus it is +21.89% over the old-policy
5666 observation, reaching 89.58% of immediate-memory SPK286's 7709 reference.
These two latest integers are still partial formatter captures; their guest
math/exit tests continue. No corrected-policy Whetstone rate or MiSTer gain
is inferred before those observations arrive.

## Reproduction and retained evidence

Use fresh run directories and the committed `scripts/build_at_no_debug.sh`
with `AT_DETAILED_TIMING=1`. Preserve the P17 reports/RBF in `baseline-p17`
inside the run before calling `tools/perf01/report_combined_rbf.py`.
The reporter verifies source hashes, current production, options, artifact
freshness and fitted totals. It reads native Windows Quartus reports without
assuming UTF-8; raw report hashes preserve byte provenance.

Full build inputs, binaries and detailed reports remain in
`build/perf01-posted-pit-rbf-20261002`. Compact immutable reports and inventories
are retained with [the P18/P19 evidence](../evidence/perf01-posted-write-20261002/README.md).
