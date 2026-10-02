# RTC lookup: original constraints, seed 2

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.273 | +0.155 | +2.193 | +2.434 | +2.316 | +2.499 | +5.097 | +2.944 |
| 7_slow_1100mv_-40c | -0.239 | +0.029 | +2.251 | +2.594 | +2.478 | +2.941 | +5.894 | +2.358 |
| MIN_fast_1100mv_100c | +2.267 | +0.101 | +10.227 | +10.862 | +10.509 | +7.730 | +9.597 | +0.664 |
| MIN_fast_1100mv_-40c | +2.494 | +0.025 | +11.642 | +12.157 | +11.983 | +8.126 | +11.128 | +0.042 |

Evidence: `docs/evidence/rtc-bcd-seed2-fit-20261002`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Complete CPU and machine video paths

| Corner | CPU setup | CPU hold | Video setup |
| --- | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.141 | +0.251 | +2.555 |
| 7_slow_1100mv_-40c | -0.239 | +0.242 | +2.848 |
| MIN_fast_1100mv_100c | +9.474 | +0.132 | +5.685 |
| MIN_fast_1100mv_-40c | +10.919 | +0.118 | +6.276 |

The completion audit reparses the raw timing reports and verifies all frozen
source hashes, the unchanged original timing budget, exact CPU proof inputs,
the proven RTC source, and a newly generated bitstream. Its failure is retained.
The compiled ROM is M10K 1024x9; all 743 valid and 281 invalid words match.

No additional route constraint was used. Remaining global setup includes
the held video-statistics payload; the cold global path is within the CPU.
Global hold and the conditional SDRAM budgets are positive in all four corners.
