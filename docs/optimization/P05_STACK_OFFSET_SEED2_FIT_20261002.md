# P08: stack-offset seed-2 physical checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.255 | +0.152 | +3.416 | +2.039 | +2.569 | +2.514 | +4.822 | +2.951 |
| 7_slow_1100mv_-40c | -0.033 | +0.033 | +3.449 | +1.976 | +2.603 | +2.701 | +5.485 | +2.456 |
| MIN_fast_1100mv_100c | +2.277 | +0.090 | +11.498 | +10.775 | +10.880 | +7.731 | +9.643 | +0.977 |
| MIN_fast_1100mv_-40c | +2.506 | +0.062 | +12.672 | +12.050 | +12.214 | +8.124 | +11.025 | +0.362 |

Evidence: `docs/evidence/stack-offset-seed2-fit-20261002`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## CPU and complete-design qualification

| Corner | CPU setup | CPU hold |
| --- | ---: | ---: |
| 7_slow_1100mv_100c | +0.540 | +0.261 |
| 7_slow_1100mv_-40c | +0.467 | +0.247 |
| MIN_fast_1100mv_100c | +9.272 | +0.141 |
| MIN_fast_1100mv_-40c | +10.789 | +0.123 |

The complete audit returns `MEASURED_TIMING_FAIL`. All frozen RTL,
SDC, 59 directed-cycle source inputs and compiled ROM checks pass.
The original manifest retains the pre-flow build-date macro; the
receipt records the sole controlled generation from 261001 to 261002.
The unchanged generator and the exact logged compiled macro are checked.
Placement changes therefore include both the equivalent arithmetic
structure and the regenerated metadata, rather than proving that the
arithmetic structure alone caused a particular slack improvement.

Reported complete-design failures:
- 7_slow_1100mv_100c global setup: -0.255
- 7_slow_1100mv_-40c global setup: -0.033

These are the global minima, not a census of every failing path.
The seed-2 warm report also contains scaled HDMI output setup -0.214 ns.
No failing selector is excluded from the complete-design closure gate.
The seed-2 fit has positive CPU setup/hold in all four models; seed 3
does not. Production remains seed 2 with all original budgets.

Fresh hardware CheckIT/DOS scores and a complete CPU regression remain
unmeasured. Directed arithmetic equivalence, affected banks and all eight
cycle fixtures are recorded separately in the stack-offset evidence.
