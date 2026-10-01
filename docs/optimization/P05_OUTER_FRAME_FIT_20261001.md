# P05: fitted outer-return carry-save checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -2.200 | -2.021 | +1.550 | +0.722 | +0.500 | +1.602 | +5.888 | -2.021 |
| 7_slow_1100mv_-40c | -1.886 | -2.074 | +1.694 | +0.735 | +0.846 | +1.852 | +6.418 | -2.074 |
| MIN_fast_1100mv_100c | +2.187 | -2.007 | +10.362 | +9.756 | +9.434 | +7.717 | +10.208 | -2.007 |
| MIN_fast_1100mv_-40c | +2.446 | -2.099 | +11.691 | +11.181 | +11.005 | +8.129 | +11.530 | -2.099 |

Evidence: `docs/evidence/outer-frame-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.
