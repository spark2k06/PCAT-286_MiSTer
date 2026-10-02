# RTC lookup: rejected 0.6 ns route-bound experiment, seed 3

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.534 | -0.079 | +2.583 | +2.453 | +2.327 | +3.287 | +3.937 | +3.047 |
| 7_slow_1100mv_-40c | -0.755 | -0.101 | +2.429 | +2.172 | +2.285 | +3.064 | +4.754 | +2.301 |
| MIN_fast_1100mv_100c | +2.293 | +0.006 | +10.920 | +11.266 | +10.827 | +7.716 | +8.957 | +0.981 |
| MIN_fast_1100mv_-40c | +2.526 | -0.016 | +12.149 | +12.330 | +12.112 | +8.127 | +10.503 | +0.300 |

Evidence: `docs/evidence/rtc-bcd-net-bound-seed3-fit-20261002`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Complete CPU and machine video paths

| Corner | CPU setup | CPU hold | Video setup |
| --- | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.534 | +0.257 | +2.530 |
| 7_slow_1100mv_-40c | -0.755 | +0.247 | +2.835 |
| MIN_fast_1100mv_100c | +8.781 | +0.134 | +5.655 |
| MIN_fast_1100mv_-40c | +10.452 | +0.118 | +6.253 |

The completion audit reparses the raw timing reports and verifies all frozen
source hashes, the unchanged original timing budget, exact CPU proof inputs,
the proven RTC source, and a newly generated bitstream. Its failure is retained.
The compiled ROM is M10K 1024x9; all 743 valid and 281 invalid words match.

The additional route bound is experimental and fails the all-edge audit.
It is not selected in production. The complete 163-edge/four-corner reports
and the failing checker receipt are retained in this evidence directory.
