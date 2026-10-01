# P05: fitted protected completion and operand range checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -2.145 | -2.022 | +1.223 | +0.555 | +0.984 | +1.432 | +5.388 | -2.022 |
| 7_slow_1100mv_-40c | -2.002 | -2.075 | +1.265 | +0.342 | +0.856 | +1.373 | +6.023 | -2.075 |
| MIN_fast_1100mv_100c | +2.292 | -2.007 | +9.922 | +9.893 | +9.913 | +7.718 | +9.870 | -2.007 |
| MIN_fast_1100mv_-40c | +2.534 | -2.099 | +11.451 | +11.358 | +11.357 | +8.129 | +11.297 | -2.099 |

Evidence: `docs/evidence/completion-limit-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

Compared with the DDR-clock-only fit, the warm/cold CPU setup improves from
-3.765/-3.632 ns to -2.145/-2.002 ns. The two CPU rewrites are fitted together;
do not attribute that full gain to either one individually. The code buffers
have +0.555/+0.342 ns setup and owner entry has +1.432/+1.373 ns. The slowest
CPU path still uses the original consecutive outer-return SP/allocation/+3
adders and then normal operand completion. The carry-save outer-frame change
and new SDRAM phase PLL are absent from this checkpoint. External hold remains
negative and the scaled HDMI setup includes a small -0.068 ns violation in
the warm corner; later global acceptance must address all timed clock domains.
