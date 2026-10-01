# Synchronous microcode ROM seed-three comparison

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.289 | +0.247 | +2.428 | +1.762 | +1.872 | +2.549 | +4.135 | +2.969 |
| 7_slow_1100mv_-40c | -0.469 | +0.062 | +2.402 | +1.612 | +1.739 | +2.360 | +4.957 | +2.360 |
| MIN_fast_1100mv_100c | +2.163 | +0.134 | +10.299 | +10.563 | +10.270 | +7.716 | +8.986 | +0.769 |
| MIN_fast_1100mv_-40c | +2.433 | +0.068 | +11.820 | +11.941 | +11.736 | +8.125 | +10.556 | +0.091 |

Evidence: `docs/evidence/sync-microcode-seed3-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

This run changes the placement seed from 2 to 3; production remains seed 2
until a later measured candidate is selected. Compiled RTL and timing
requirements match the seed-2 P07 candidate. CPU setup is +0.389/+0.416 ns
in the slow warm/cold models, and +9.532/+11.003 ns in the fast models.
Global hold is positive in all four corners, including the EGA DAC address
path which failed in the seed-2 placement. HDMI setup is also positive.

Remaining setup failures are the held video-statistics transfer into
50 MHz (-0.289 ns warm) and RTC conversion/alarm checking (-0.469 ns cold).
Changing placement can move the critical path and margins; this comparison
does not prove that a later changed RTL fit will retain these margins.

The new RBF is 4,035,768 bytes and compilation succeeded with zero errors.
