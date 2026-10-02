# P08: stack-offset seed-3 physical checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.252 | +0.192 | +2.113 | +2.432 | +2.404 | +3.344 | +5.130 | +2.975 |
| 7_slow_1100mv_-40c | -0.005 | +0.033 | +2.224 | +2.327 | +2.373 | +3.571 | +5.860 | +2.402 |
| MIN_fast_1100mv_100c | +2.158 | +0.132 | +10.067 | +10.671 | +10.524 | +7.725 | +9.599 | +1.029 |
| MIN_fast_1100mv_-40c | +2.436 | +0.046 | +11.658 | +12.078 | +11.989 | +8.128 | +11.092 | +0.320 |

Evidence: `docs/evidence/stack-offset-seed3-fit-20261002`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## CPU and complete-design qualification

| Corner | CPU setup | CPU hold |
| --- | ---: | ---: |
| 7_slow_1100mv_100c | -0.160 | +0.262 |
| 7_slow_1100mv_-40c | -0.005 | +0.253 |
| MIN_fast_1100mv_100c | +9.019 | +0.138 |
| MIN_fast_1100mv_-40c | +10.648 | +0.120 |

The complete audit returns `MEASURED_TIMING_FAIL`. All frozen RTL,
SDC, 59 directed-cycle source inputs and compiled ROM checks pass.
The original manifest retains the pre-flow build-date macro; the
receipt records the sole controlled generation from 261001 to 261002.
The unchanged generator and the exact logged compiled macro are checked.
Placement changes therefore include both the equivalent arithmetic
structure and the regenerated metadata, rather than proving that the
arithmetic structure alone caused a particular slack improvement.

Reported complete-design failures:
- 7_slow_1100mv_100c global setup: -0.252
- 7_slow_1100mv_-40c global setup: -0.005

These are the global minima, not a census of every failing path.
The seed-2 warm report also contains scaled HDMI output setup -0.214 ns.
No failing selector is excluded from the complete-design closure gate.
The seed-2 fit has positive CPU setup/hold in all four models; seed 3
does not. Production remains seed 2 with all original budgets.

Fresh hardware CheckIT/DOS scores and a complete CPU regression remain
unmeasured. Directed arithmetic equivalence, affected banks and all eight
cycle fixtures are recorded separately in the stack-offset evidence.
