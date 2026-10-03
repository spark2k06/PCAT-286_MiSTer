# P18/P19: combined posted-write and PIT-refresh candidate

Date: 2026-10-02; hardware confirmation updated 2026-10-03. Status:
**RBF generated and verified; user-confirmed hardware throughput observed;
aggregate acceptance and 50 MHz timing closure pending**.
The complete CPU and PCAT regression has
subsequently completed in
`build/full-regression-posted-pit-active-20261002`, with only the active CPU
options, as requested. The earlier two-profile run was interrupted for this
scope correction and retained. All 129 original CPU banks and evaluable
physical cases pass with separately verified replays, but MRBIOS restart and
verification/input gaps prevent aggregate acceptance. See the
[full regression report](P18_P19_FULL_REGRESSION_20261002.md).

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
The old-policy controls subsequently completed with **6138 / 113.6K** versus
**5666 / 106.7K**, both RC0/ALL_DONE, reproducing both P17 MiSTer rates exactly.
The combined candidate subsequently completed with **6906 / 121.6K**, guest
RC0 and `ALL_DONE`. CPU objects/options, initial disk, CHECKNUM, configuration,
CMOS and cache capacities match the old-policy run. The model and profiler
header intentionally differ to enable posting and observe actual PIT OUT1;
their exact hashes and source bytes are retained. The native SDRAM refresh
remains enabled. Host exit timeout/SIGTERM is recorded separately from guest
success. This is a completed platform-model result; the subsequent hardware
observation is recorded below and does not imply aggregate acceptance.

| CHECKNUM reference | Dhrystones/s | K Whetstones/s |
| --- | ---: | ---: |
| Old AT policy, reproducing P17 MiSTer | 5,666 | 106.7 |
| Combined posted writes and PIT OUT1 | 6,906 | 121.6 |
| Same SPK286, immediate-memory reference | 7,709 | 133.3 |
| Native 86Box 286, separate CPU model | 8,287 | 144.9 |

The combined model gains **21.89% / 13.96%** over the old AT policy. It reaches
**89.58% / 91.22%** of the same-CPU immediate-memory reference. Reaching that
reference would require a further **11.63% / 9.62%** rate increase. These are
empirical workload references, not a promise that all physical platform cost
can be eliminated. The native 286 uses a separately qualified CPU timing model;
neither reference supplies a mandatory hardware score.

### Subsequent user hardware observation

The user supplied MiSTer screenshots reporting **6765 / 121.6K** in CheckIT
and **6906 / 121.6K** in CHECKNUM. The latter matches both rates from the
completed combined simulation exactly: +21.89% / +13.96% over P17 hardware,
and 89.58% / 91.22% of the same-SPK286 immediate-memory reference. Compare
CHECKNUM with CHECKNUM; the separate CheckIT integer observation is 2.04%
lower and is retained, not substituted for the matched measurement.

The screenshots and their byte hashes are retained under
`docs/evidence/perf01-posted-write-20261002/hardware-combined`. On 2026-10-03 the
user confirms the delivered RBF. This is user attribution to the exported
artifact, not an independently observed loaded-bitstream hash. This observation
does not establish timing closure or aggregate regression acceptance.

## Next performance experiment

2026-10-03 priority update: the user requests a manufacturer-led AT functional
review, including 86Box, and retains fast operation with optional historical
T-states planned later. The outlines below remain proposals. There is no
requirement to match an ideal memory model or to change peripheral time to
improve a score. See the [functional audit](../AT_FUNCTIONAL_REFERENCE_AUDIT_20261003.md)
and the [P12 mode specification](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md#fast-mode-and-optional-historical-timing).

The completed combined model's function-phase counters identify the next
possible measurement target. Dhrystone reads already hit almost always: code hit
rate **99.9921%**, data hit rate **99.9944%**. There are **18,017,746 code
transfers** at **1.000825 wait clocks** on average and **7,464,837 data reads**
at **1.000414**. Writes average only **1.024723 wait clocks** after posting.
These are bus-service counters; prefetch overlaps execution, so summed wait
clocks are not saved elapsed clocks or a predicted benchmark gain.

A future experiment could investigate instruction-read lookahead and consecutive-hit response
handling: reuse already obtained instruction-line words or start a synchronous
lookup early when the address is demonstrably stable. Keep canonical-address
checks, store invalidation, redirects, reset and external-writer coherence.
Do not replace M10K outputs with unbounded combinational RAM or assume a
zero-wait response is feasible at the configured clock. Compare a private
prototype against this frozen model before RTL adoption or synthesis, with
unchanged CPU/options, work and architectural results. No such prototype or
gain is measured by this documentation update.

For software-floating-point Whetstone, the code/data hit rates are lower,
**98.8652% / 98.5558%**. The existing 8 KiB code shadow predicts **201,126**
misses versus **858,392** actual at 4 KiB; the 4 KiB direct data shadow predicts
**31,318** versus **189,573** actual at 1 KiB two-way. These support a separate
capacity experiment, with fitted RAM/tag/control cost measured before adoption;
they are shadow predictions, not an implemented cache or a throughput result.

Open-row SDRAM service and deeper posted-write buffering remain possible
later experiments. Their marginal value must use physical-owner traffic and
queue-pressure traces, rather than extrapolate the old pre-posting bottleneck.
The current nearly one-clock integer write service makes common read service
the stronger next hypothesis. Timing closure remains a separately deferred task.

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
