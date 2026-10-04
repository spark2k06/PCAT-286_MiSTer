# MiSTer CPU profile measurements

Date: 2026-10-04. The user tested the first synthesized OSD candidate on
MiSTer, selected each of its eight profiles and applied **Reset & apply
settings** each time. All 336 T286REF samples pass the unchanged raw-data
validator, including register signatures and recomputed summaries. MAX
also preserves the previous CHECKNUM result. Historical calibration remains
open: the measured kernels differ from the physical and native references,
and R0 takes longer at 25 MHz than at 20 MHz in these captures.

The user confirms the RBF in
`build/p06-osd-allfeatures-seed1-v2-fit-20261004/work/output_files/PCAT-286.rbf`,
SHA-256 `61337ec247fed74f0ebdeb388c0b86243f9152744f0a5c8debb3f4ffb6b63067`.
BIOS and CheckIT reportedly display the expected nominal MHz. This supports
speed detection by those routines; it does not establish execution timing
for every instruction, prefetch path or board memory access.

## Hardware observations

CHECKNUM numbers are transcribed from the three supplied screenshots. R0,
B0 and M0 are median **elapsed PIT input ticks** from separate T286REF runs
with 256 iterations and seven repetitions per kernel and baseline. R0
exercises register arithmetic, B0 branches and M0 aligned RAM reads,
writes and read/modify/write. Smaller elapsed counts mean quicker execution.

| Profile | CHECKNUM Dhrystones | CHECKNUM Whetstones K | R0 gross | B0 gross | M0 gross |
| --- | ---: | ---: | ---: | ---: | ---: |
| MAX | 6906 | 121.6 | 217 | 272 | 427 |
| 6 MHz | 1674 | 32.2 | 971 | 1429 | 1786 |
| 8 MHz | 2181 | 41.8 | 729 | 1072 | 1387 |
| 10 MHz | 2695 | 52.0 | 584 | 859 | 1132 |
| 12.5 MHz | 3234 | 61.4 | 469 | 688 | 911 |
| 16 MHz | 3854 | 74.6 | 368 | 539 | 749 |
| 20 MHz | 4361 | 84.1 | 298 | 435 | 687 |
| 25 MHz | 5023 | 91.9 | 316 | 390 | 598 |

The eight supplied CSVs contain 336 samples and 48 summaries. Each has the
expected profile metadata, mode-2 PIT status, consistent raw-counter
arithmetic, positive bounded intervals and correct register signatures.
MAX CHECKNUM equals the previous user measurement, **6906 / 121.6K**. This
is auxiliary benchmark preservation; it does not constitute a full regression.

Raw CSV bytes, screenshots, hashes, complete validation receipts and derived
statistics are preserved in the
[evidence manifest](../evidence/p06-mister-reference-20261004/manifest.json)
and [analysis](../evidence/p06-mister-reference-20261004/analysis.json).

## Comparison with existing references

The [physical reference report](P06_PHYSICAL_REFERENCE_RESULTS_20261004.md)
identifies two provisional hardware anchors at nominal 6 and 12 MHz. The
native 86Box controls run at 6 and **12.5 MHz**, with Automatic and visible
0, 1 and 2 waits archived separately. Visible zero is configuration value
one; configuration zero means Automatic.

The table shows **MiSTer elapsed time relative to the reference**:
`100 * (MiSTer_ticks / reference_ticks - 1)`. Negative values indicate that
MiSTer completes the same fixed work earlier. These are time differences,
not percentages of CPU frequency or throughput gain.

| MiSTer profile | Reference | R0 elapsed difference | B0 elapsed difference | M0 elapsed difference |
| --- | --- | ---: | ---: | ---: |
| 6 MHz | Native 86Box 6 MHz visible zero waits | -27.5% | -24.7% | -17.1% |
| 6 MHz | Physical REG6_6 at nominal 6 MHz | -30.3% | -32.9% | -17.7% |
| 12.5 MHz | Native 86Box 12.5 MHz visible zero waits | -27.1% | -24.5% | -11.9% |
| 12.5 MHz | Physical REG12_12 scaled illustratively to 12.5 MHz | -30.8% | -35.5% | -40.0% |

The last row scales physical ticks by `12 / 12.5`. This assumes equal cycle
counts and does not independently scale fixed ISA, timer-port or board delays.
It is not a physical 12.5 MHz measurement. Board identity, actual physical
clocks and the collaborator's executable hash remain unverified. Additional
comparisons against Automatic and visible 1/2 waits are in the analysis.
No measured native T286REF controls at 8/10/16/20/25 MHz are available in this
reference bundle; those profiles must not be described as already aligned
to measured native controls.

The different register, branch and RAM differences do not support a single
benchmark multiplier. They also do not identify one motherboard wait setting.

## The register kernel at 25 MHz

R0 gross takes **315–316 ticks at 25 MHz**, compared with **298–299 at 20 MHz**.
The medians differ by **+6.04% elapsed time**, and every captured 25 MHz
repetition is slower than every 20 MHz repetition. This exceeds variation
within these runs. Baseline LOOP still improves from 142 to 118 ticks; B0
improves from 435 to 390 and M0 from 687 to 598. CHECKNUM also improves from
4361 / 84.1K to 5023 / 91.9K. The anomaly therefore concerns a specific
workload rather than all performance at 25 MHz.

The current interval controller permits functional dependencies to extend
an instruction beyond its nominal minimum. At 25 MHz, a virtual processor
boundary occurs every two 50 MHz fabric edges. At 20 MHz, boundaries have
alternating two/three-edge spacing. **Hypothesis:** a short register operation
may miss a deadline at 25 MHz and wait for a later boundary, or admission and
fetch phases may interact differently. A trace must distinguish those cases
from bus service and other implementation effects. Neither this hypothesis
nor a physical setup failure is established as the cause by the CSVs.

## What the timing source explains

Against the R0 baseline, differences of medians are 509 ticks at 6 MHz and
245 ticks at 12.5 MHz. Conditionally converting those differences using the
nominal frequencies and PIT input gives about **9.998 and 10.026 clocks per
iteration**. This is consistent with the four arithmetic minima in the
[existing Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md),
`2 + 2 + 3 + 3 = 10`. It is a descriptive consistency check, not a measurement
of isolated EU cycles: baseline subtraction does not remove all fetch and
instrumentation effects. The native handler constants also differ from
Intel for immediate forms and LOOP, so native elapsed time alone is not a
reason to change those documented CPU minima.

B0 differences similarly normalize to about **18.99 clocks per iteration**
at 6 and 12.5 MHz, matching `2 + 3 + 7 + 7 = 19` before the taken-transfer
target-length qualification. The production table explicitly marks taken
Jcc/JMP forms estimated; it supplies base seven without an explicit target
instruction length. The existing Intel extraction requires qualifying how
that note and actual refill fit the timeline, avoiding duplicate charges.
These measurements do not yet resolve that qualification.

The production machine ties `timing_read_wait_event` to zero. This means
no selected historical board READ-wait policy contributes through that
interface. The bridge still retains logical Ts/Tc timing and waits for real
backend completion. Physical backend lateness and a chosen board READY wait
policy are distinct. Their absence/presence must be assessed separately
when calibrating M0; an aggregate RAM difference does not specify a wait count.

## Next work and acceptance scope

The first synthesized OSD selector now has hardware fixed-work evidence for
all eight selections. P06/P12 historical calibration remains pending. The
next directed work should trace the exact R0 bytes at 20/25 MHz, recording
instruction starts, qualified metadata, functional completion, deadlines,
retirement, implementation extensions and CODE service. Then qualify B0
taken-target/refill timing and the board-sensitive M0 READ/WRITE timeline
against the retained Intel, native and physical observations.

Keep MAX unchanged and preserve the published workload bytes. Apply justified
timing changes by instruction/bus cause, with the same model across profiles,
rather than making benchmarks match through unrelated multipliers.

This analysis changes documentation and evidence only. It launches no CPU
simulation, regression or synthesis and changes no RTL, config, OSD or RBF.
The [candidate fit](P06_OSD_FIT_20261004.md) still reports setup **-17.001 ns**
and minimum hold **+0.076 ns** on the common 50 MHz physical clock. Lower
nominal profiles do not relax those physical timing requirements, and these
hardware samples do not prove timing closure or general OS compatibility.

Reproduce the data analysis from the committed raw inputs and screenshots:

```powershell
python scripts/analyze_p06_mister_reference.py --input-dir docs/evidence/p06-mister-reference-20261004/raw --output docs/evidence/p06-mister-reference-20261004
```

The unchanged validator recomputes every sample and summary. The analyzer
also revalidates the archived native/physical CSVs and their hashes before
performing comparisons. Existing raw archives cannot be replaced by changed
bytes. This command refreshes derived JSON; screenshot archives remain intact.
