# Synchronous microcode ROM physical checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.390 | -0.071 | +3.085 | +2.305 | +2.257 | +2.904 | +5.590 | +3.059 |
| 7_slow_1100mv_-40c | -0.101 | -0.092 | +3.050 | +2.443 | +2.219 | +3.018 | +6.401 | +2.496 |
| MIN_fast_1100mv_100c | +2.097 | +0.010 | +10.773 | +10.716 | +10.457 | +7.730 | +9.728 | +0.970 |
| MIN_fast_1100mv_-40c | +2.380 | -0.011 | +12.186 | +12.125 | +11.892 | +8.126 | +11.253 | +0.362 |

Evidence: `docs/evidence/sync-microcode-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## CPU and remaining machine routes

The complete CPU selector has positive setup and hold in all four corners:

| Corner | CPU setup (ns) | CPU hold (ns) |
| --- | ---: | ---: |
| Slow 100 C | +0.310 | +0.252 |
| Slow -40 C | +0.436 | +0.241 |
| Fast 100 C | +9.557 | +0.137 |
| Fast -40 C | +11.126 | +0.120 |

The warm critical CPU path starts at the prefetch head and passes through
decode, stack-range checking and register write priority. The asynchronous
microcode-ROM decode cone has disappeared from this path. The same-clock
50 MHz Fmax reported by TimeQuest is 50.79 MHz. This does not establish
closure for incoming clock-domain paths or the rest of the machine.

Remaining negative setup paths are HDMI scaled output (-0.390 ns warm),
the held video-statistics payload crossing into 50 MHz (-0.389 ns warm),
and RTC hour conversion/alarm checking (-0.101 ns cold). Negative hold is
in the EGA DAC MLAB write-address path, reaching -0.092 ns cold. These are
still real failed requirements in this fit; none is removed from acceptance.

Compilation succeeded with zero errors. The new RBF is 4,076,140 bytes.
The mapped 1024x9 M10K contents and no-extra-output-register parameters
are checked separately by the compiled-ROM evidence. This checkpoint
preserves the production 20 ns clock and external SDRAM budget unchanged.
