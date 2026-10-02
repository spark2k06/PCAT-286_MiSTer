# RTC lookup: rejected 1.0 ns route-bound experiment, seed 3

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.337 | +0.228 | +1.635 | +1.667 | +1.136 | +1.963 | +4.550 | +2.991 |
| 7_slow_1100mv_-40c | -0.420 | +0.031 | +1.610 | +1.579 | +1.309 | +2.165 | +5.291 | +2.357 |
| MIN_fast_1100mv_100c | +2.292 | +0.132 | +9.915 | +10.123 | +9.384 | +7.716 | +9.076 | +0.915 |
| MIN_fast_1100mv_-40c | +2.565 | +0.058 | +11.464 | +11.612 | +11.091 | +8.125 | +10.715 | +0.257 |

Evidence: `docs/evidence/rtc-bcd-net-one-seed3-fit-20261002`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Complete CPU and machine video paths

| Corner | CPU setup | CPU hold | Video setup |
| --- | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.286 | +0.252 | +2.162 |
| 7_slow_1100mv_-40c | -0.272 | +0.243 | +2.506 |
| MIN_fast_1100mv_100c | +9.024 | +0.137 | +5.373 |
| MIN_fast_1100mv_-40c | +10.687 | +0.119 | +6.041 |

The completion audit reparses the raw timing reports and verifies all frozen
source hashes, the unchanged original timing budget, exact CPU proof inputs,
the proven RTC source, and a newly generated bitstream. Its failure is retained.
The compiled ROM is M10K 1024x9; all 743 valid and 281 invalid words match.

The additional route bound is experimental and fails the all-edge audit.
It is not selected in production. The complete 163-edge/four-corner reports
and the failing checker receipt are retained in this evidence directory.
