# P05: first SDRAM output-placement probe and assignment parsing defect

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

## Rejected pin-assignment syntax

The vector targets in this probe were written with Tcl-style braces in the
QSF. Quartus preserved those braces in the assignment target, so
`{SDRAM_A[*]}` did not match `SDRAM_A[*]`. Its assignment query and fitter
packing report confirm that the address/data vector registers remained in
the I/O cells under the generic fast-output assignment. The bare command
targets did not have this defect. This run therefore cannot be treated as
evidence that moving all SDRAM output registers into the core failed.

The corrected experiment uses bare vector targets in the QSF. A project
check rejects literal braces and requires the exact address, bank, data
and data-enable targets. The negative check rejects this frozen probe;
the positive check accepts the corrected frozen project. Physical timing
of that separate run must still be measured before accepting the change.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -2.101 | -2.021 | +1.397 | +1.595 | +1.600 | +3.265 | +5.747 | -2.021 |
| 7_slow_1100mv_-40c | -1.883 | -2.074 | +1.588 | +1.755 | +1.897 | +3.385 | +6.357 | -2.074 |
| MIN_fast_1100mv_100c | +2.224 | -2.007 | +10.353 | +10.198 | +9.921 | +7.717 | +10.138 | -2.007 |
| MIN_fast_1100mv_-40c | +2.484 | -2.099 | +11.739 | +11.579 | +11.396 | +8.127 | +11.495 | -2.099 |

Evidence: `docs/evidence/sdram-output-placement-braced-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.
