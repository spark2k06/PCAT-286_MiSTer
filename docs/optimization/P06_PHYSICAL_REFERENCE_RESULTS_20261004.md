# P06/P12: physical 6/12 MHz fixed-work reference

Date: 2026-10-04. Four collaborator CSV captures pass the existing raw
`T286REF2` validator: 168 samples, four terminal `PASS_RAW_FIXED_WORK` records
and 24 recomputed summaries. These are physical fixed-work observations with
an **uncalibrated** PIT/CPU clock, not native-pin or isolated instruction-cycle
validation. No production RTL, profile, clock or RMW source changes were made.

The user states that the first filename number is the hardware speed selector
and the second is the argument passed to the DOS program. The primary captures
are `REG6_6.CSV` and `REG12_12.CSV`. The other two are separate executions at
those same hardware settings with different metadata labels.

## Raw observations and integrity

All times below are elapsed **PIT input ticks**, conditional on the program's
assumed standard BIOS divisor 65536. Each baseline/gross group contains seven
samples of exactly 256 iterations. Gross includes the common LOOP, dispatch,
register setup, signature stores and timer instrumentation. It is not
baseline-subtracted.

| Capture | Hardware selector | Program argument | R0 register gross | B0 branch gross | M0 aligned-RAM gross |
| --- | ---: | --- | ---: | ---: | ---: |
| **REG6_6.CSV, primary** | **6 MHz nominal** | **6** | **1394** | **2131** | **2170** |
| REG6_12.CSV, repetition | 6 MHz nominal | 12 | 1397 | 2127 | 2167 |
| REG12_6.CSV, repetition | 12 MHz nominal | 6 | 707 | 1111 | 1583 |
| **REG12_12.CSV, primary** | **12 MHz nominal** | **12** | **706** | **1111** | **1582** |

Primary min/median/max and corresponding baseline medians are:

| Primary hardware setting | R0 gross min/median/max | B0 gross min/median/max | M0 gross min/median/max | Baseline medians R0/B0/M0 |
| --- | --- | --- | --- | --- |
| 6 MHz nominal | 1393 / 1394 / 1397 | 2124 / 2131 / 2133 | 2151 / 2170 / 2180 | 656 / 654 / 658 |
| 12 MHz nominal | 706 / 706 / 709 | 1111 / 1111 / 1113 | 1578 / 1582 / 1583 | 354 / 355 / 355 |

Validation checks the complete schema, unique repetitions, work count,
mode/status/OUT agreement, start window, bounded positive phase interval,
counter arithmetic and AX/BX/CX/DX/DI signatures. Physical records use binary
PIT **mode 3**, status without OUT 54 and OUT high at both endpoints. Every
physical sample satisfies `raw_delta == 2 * ticks`. The counter decreases by
two in this mode; comparing `raw_delta` directly with the mode-2 native
reference would introduce a false factor of two. The native controls use
mode 2 and satisfy `raw_delta == ticks`.

The maximum count probes are near 65536 and satisfy the existing compatibility
guard. They do not reveal the actual reload register or calibrate the crystal.
All physical captures retain `timer_qualification=NOT_CALIBRATED`.

Physical program CS is 4647 decimal; native CS is 3858. Both record an aligned
four-word fixture offset of 2832 decimal. These are conventional RAM locations
with the same offsets, not an assertion that the unknown physical board and
the MR BIOS native machine have identical memory/ROM maps or wait policies.

## Effect of the program argument and secondary pooling

`SW/CPUTIME/t286ref.asm:33` copies the first command token only into the nominal
metadata string. `ITERATIONS=256` and `REPETITIONS=7` are compile-time constants.
The argument never changes CPU speed, workload, timer programming or an
adaptive calibration loop. Changing it from 6 to 12 changes gross medians by
at most 0.22%, and baseline medians by at most 0.46%, in these captures.

As a secondary descriptive check, the two executions per hardware setting can
be pooled into 14 samples per case/kind. They are **not paired trials** and do
not independently identify the oscillator frequency. These pooled medians do
not replace the source medians in the primary comparison.

| Hardware selector | Pooled R0 gross (min–max) | Pooled B0 gross (min–max) | Pooled M0 gross (min–max) |
| --- | --- | --- | --- |
| 6 MHz nominal | 1396 (1392–1398) | 2130 (2124–2133) | 2168.5 (2148–2180) |
| 12 MHz nominal | 706.5 (705–709) | 1111 (1109–1113) | 1582.5 (1578–1584) |

The pooled comparisons support the same conclusions. The observed ranges
describe these small captures, not a statistical confidence interval or all
possible operating conditions of the board.

## Comparison with native 86Box

The six existing controls and two new visible-zero controls use the original
native 286 dispatcher, the frozen
2,840-byte program (SHA-256
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`), and
guest/host-successful receipts. All eight CSVs (336 samples) and runtime
receipts are revalidated and copied into this evidence bundle.

| Actual native CPU clock | Selection | Stored config | Prefetch/read/write service cycles | R0 gross | B0 gross | M0 gross |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 6 MHz | Automatic | 0 | 2 / 2 / 2 | 1339 | 1899 | 2153 |
| 6 MHz | Visible 0 wait states | 1 | 2 / 2 / 2 | 1339 | 1899 | 2154 |
| 6 MHz | Visible 1 wait state | 2 | 3 / 3 / 3 | 2119 | 2221 | 2882 |
| 6 MHz | Visible 2 wait states | 3 | 4 / 4 / 4 | 2492 | 2645 | 3510 |
| 12.5 MHz | Automatic | 0 | 3 / 3 / 3 | 1017 | 1066 | 1384 |
| 12.5 MHz | Visible 0 wait states | 1 | 2 / 2 / 2 | 643 | 911 | 1034 |
| 12.5 MHz | Visible 1 wait state | 2 | 3 / 3 / 3 | 1017 | 1066 | 1384 |
| 12.5 MHz | Visible 2 wait states | 3 | 4 / 4 / 4 | 1196 | 1270 | 1685 |

Config zero is **Automatic**, not the visible zero-wait selection. The latter
stores config 1 and selects two service cycles. Both new visible-zero controls
have guest/host exit 0, the native dispatcher, actual requested CPU speed,
service costs 2/2/2 and both cache flags disabled. At6 their gross values
reproduce Automatic within one tick. At12.5 they differ substantially because
Automatic selects service costs 3/3/3. Visible-zero baseline medians are
728/728/728 at6 and 349/349/349 at12.5. These controls complement the original
automatic comparisons, which remain recorded below.

### Frequency normalization and magnitude

The ordinary native entry labelled `12` runs at **12.5 MHz**, while the physical
selector is reported as nominal **12 MHz**. For a descriptive equal-cycle-count
comparison, scale native elapsed ticks by `12.5/12 = 25/24`. The percentage is:

`100 * (physical_ticks / (native_ticks * native_hz / physical_nominal_hz) - 1)`.

A positive value means more elapsed time for the physical capture; a negative
value means less elapsed time. This is a frequency normalization, not a
measured native-12-MHz run. It does not independently rescale ISA, PIT access,
refresh or other fixed board delays. Native ISA is 6 MHz at CPU6 and 8 MHz at
CPU12.5; the physical ISA/memory cadence is unknown.

| Primary physical setting | Native selection | R0 elapsed difference | B0 elapsed difference | M0 elapsed difference |
| --- | --- | ---: | ---: | ---: |
| 6 MHz | Automatic, same nominal frequency | +4.11% | +12.22% | +0.79% |
| 6 MHz | Visible 0 waits, same nominal frequency | +4.11% | +12.22% | +0.74% |
| 6 MHz | Visible 1 wait, same nominal frequency | −34.21% | −4.05% | −24.71% |
| 6 MHz | Visible 2 waits, same nominal frequency | −44.06% | −19.43% | −38.18% |
| 12 MHz | Automatic 12.5, frequency-normalized | −33.36% | +0.05% | +9.73% |
| 12 MHz | Visible 0 waits at 12.5, frequency-normalized | +5.41% | +17.08% | +46.88% |
| 12 MHz | Visible 1 wait at 12.5, frequency-normalized | −33.36% | +0.05% | +9.73% |
| 12 MHz | Visible 2 waits at 12.5, frequency-normalized | −43.33% | −16.02% | −9.87% |

At physical6, the automatic native reference is close for aligned RAM and
register work, with a larger branch difference. At physical12, branches are
close to automatic/visible1, registers finish substantially sooner and RAM
takes longer. The explicit visible-zero reference brings R0 within roughly
4–5% of both physical settings. The initially observed −33.36% R0 difference
against Automatic12.5 is therefore largely explained by the native service
cost selection 3 versus2, rather than evidence of different intrinsic EU
timing. The same change leaves physical12 branches about17% slower and RAM
about47% slower than frequency-normalized visible-zero native execution.
No one global multiplier or one native wait selection explains all three
cases. This remains true after the secondary pooling.

The two primary hardware-selector ratios, elapsed6 / elapsed12, are 1.97 for
R0, 1.92 for B0 and 1.37 for M0. Doubling the nominal selector therefore brings
much less benefit to this RAM-sensitive workload. Code prefetch, data service,
refresh, ISA/PIT instrumentation, and the unknown board's clock/wait policy
are candidate contributors. These three kernels do not identify a unique
cause or a physical READY wait count.

An exploratory two-point description `T(f)=A/f+B`, using MHz and the primary
gross medians only, has intercepts B of 18 ticks (R0), 91 (B0), and 994 (M0).
That illustrates why a non-scaling component could matter, especially for
M0. Two points determine this model exactly with no residual degrees of
freedom: B is **not** a measured RAM/ISA latency, an instruction timing or a
validated prediction for faster profiles. No profile table is generated from
these intercepts.

## How these data guide P06/P12 and the remaining profiles

Use the physical6/12 observations as provisional **behavioral calibration
anchors**. Intel instruction/bus contracts remain authoritative; 86Box supplies
the functional and model reference, while these physical captures constrain
the expected behavior of a real, partly unidentified system. The immediate
result is a more specific calibration plan, not an RTL retune from three
aggregate medians.

1. Preserve intrinsic Intel EU timings and real dependencies. Refine CODE
   prefetch/queue, branch flush/restart, and DATA read/write scheduling through
   the actual CPU services. Existing Ts/Tc and raw READY retention must remain
   causal; a benchmark target must not bypass those dependencies.
2. Model motherboard-facing READY separately for code/RAM access classes and
   for the recorded bus cadence. Keep ISA/PIT and refresh effects explicit.
   Simulate overlap between EU and BIU rather than summing delays that occur
   concurrently. Do not apply a workload-specific multiplier to instructions.
3. Use the now-completed native Automatic and explicit visible0/1/2 controls at
   known 6/12.5 clocks. They isolate the emulator's selectable service-cost
   contribution; they do not identify the collaborator's physical wait
   configuration. Visible0 is the useful low-wait EU/prefetch comparison;
   memory/branch residuals need their own causal investigation.
4. Use R0/B0/M0 plus their separate LOOP baselines to rank sensitivity to EU,
   queue/branches and aligned RAM. Add directed straight-line versus short-loop
   code cases, aligned versus odd words, and separate READ, WRITE and RMW cases
   before choosing between competing prefetch/RAM models. The existing M0
   kernel deliberately mixes loads, ADD from RAM, a store and memory XOR.
5. Accept a coherent model against both 6/12 anchors, raw variation and the
   native controls, then predict the other clocks through that same model.
   Record estimates and residuals. Preserve unsuccessful alternatives rather
   than selecting one hidden correction per benchmark.
6. Refine the board policy after CPU marking, board/BIOS, RAM/waits, speed
   switch, actual clocks and DOS/TSR environment become known, or after more
   physical observations discriminate models. Those details can justify a
   board-specific policy; they must not redefine intrinsic CPU timing.

| Profile/reference point | Evidence for approximation | Current status |
| --- | --- | --- |
| 6 MHz | Native controls plus physical selector6 | Provisional behavioral anchor; clock/board uncalibrated |
| Physical nominal12 MHz | Physical selector12 plus native12.5 comparison | Provisional behavioral anchor, distinct from native12.5 |
| 8 / 10 MHz | Native/Intel model between the physical anchors | Estimated until profile and physical validation |
| 12.5 MHz | Native actual12.5 plus a nearby physical12 anchor | Estimated physical behavior; not a measured physical12.5 system |
| 16 / 20 / 25 MHz | The same causal model beyond the anchors | Estimated until validation; avoid assuming board waits scale linearly |
| MAX | Existing dependency-driven accelerated behavior | Separate mode; no historical frequency calibration target |

This supports the agreed user-facing speed profiles without adding a confusing
global T-state adjustment. A historical profile's internal READY/prefetch policy
must reflect the selected model, and unmeasured profiles remain estimates.

## Provenance, reproducibility and limits

The new [evidence bundle](../evidence/p06-physical-reference-20261004/manifest.json)
contains byte-exact physical/native CSV copies, native runtime receipts,
source SHA-256 values, complete validated samples, per-capture statistics,
secondary pooling and all percentage calculations in
[analysis.json](../evidence/p06-physical-reference-20261004/analysis.json).

| Physical source | SHA-256 |
| --- | --- |
| REG6_6.CSV | `6c2875f57e4ce60900e658c2db98b92fbed4cbf2edf2fe0c958f5fe9110591bc` |
| REG6_12.CSV | `2911c5ba24470982023eea254681dc10a45128c3bbfbfb3898965895d59337a2` |
| REG12_6.CSV | `c088d454f56fdb68b6aa0c02322c5530e4f37ce78335d32538fdd6029bafadce` |
| REG12_12.CSV | `3e24ee85dd6280b0b02d77889dbd14e365cd31afe266906d385c3055da121186` |

The analyzer uses Python stdlib and the unchanged existing validator. A second
run using the bundled Windows Python independently reproduces the complete
analysis JSON after removing only source/archive path fields. This checks
numeric/parser reproducibility across the two runtimes, not clock calibration.
The reproduction receipt is archived beside the analysis.

For reconstruction from the archived CSV copies:

```text
python scripts/analyze_p06_physical_reference.py --input-dir docs/evidence/p06-physical-reference-20261004/physical --output build/p06-physical-reference-reproduction --zero-wait-bundle docs/evidence/p06-physical-reference-20261004/native
```

The final analysis includes `--zero-wait-bundle
build/p06-native-zero-wait-20261004`; the archive also retains the zero-wait
verification receipt, guest status, logs, startup/runtime samples, initial/final
profiles and initial CMOS. It contains no VHD or emulator executable copy.
The optional input accepts only complete native6-ws0 and native12-ws0
directories with successful host/guest/runtime/hash checks. Existing
raw archives are never replaced with changed bytes during `--refresh-report`.

Physical CPU/board/BIOS/RAM identity, wait configuration, DOS/TSRs, actual
oscillator/PIT frequency, reload and the SHA of the executable used by the
collaborator have not been provided. The format/signatures match `T286REF2`,
but that does not prove executable byte identity. Physical terminal PASS is
not an externally recorded process exit code. Whole-period stalls and unknown
NMI/bus activity are not excluded by endpoint-only timer checks. Mode-specific
timer instrumentation adds another small comparability difference. These
limits qualify the anchors; they do not make the observations irrelevant.
