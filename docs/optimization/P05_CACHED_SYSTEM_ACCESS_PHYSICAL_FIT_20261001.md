# P05: fitted cached system range timing checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -1.125 | +0.147 | +1.318 | +1.691 | +1.792 | +2.876 | +5.207 | +3.053 |
| 7_slow_1100mv_-40c | -0.723 | +0.032 | +1.324 | +1.471 | +1.625 | +2.739 | +6.098 | +2.443 |
| MIN_fast_1100mv_100c | +2.261 | +0.132 | +9.986 | +10.382 | +10.136 | +7.721 | +9.233 | +0.872 |
| MIN_fast_1100mv_-40c | +2.525 | +0.062 | +11.424 | +11.781 | +11.604 | +8.121 | +10.888 | +0.220 |

Evidence: `docs/evidence/cached-system-access-physical-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Interpretation

This fresh fit measures the CPU optimization from upstream c554585 and
PCAT ba43972. Relative to the preceding cache-range/GPR fit, slow CPU
setup improves by 0.548 ns at 100 C (-1.673 to -1.125) and by 0.986 ns
at -40 C (-1.709 to -0.723). All four global hold and SDRAM input/output
setup/hold minima remain positive; the smallest global hold is +0.032 ns,
and the smallest SDRAM output hold is +0.220 ns.

Both limiting slow CPU paths start at micro_pc, pass three ROM LUT levels,
event-stack offset selection, the stack range predicate, operand completion
and exception selection, then end at event_external. HDMI scaled setup
is -0.398 ns warm and -0.065 ns cold; the cold HDMI parent clock also has
-0.095 ns setup. CPU and HDMI setup still need improvement.

Quartus compiled with zero errors in 26:23 and produced a fresh 4,062,856
byte RBF. The subsequent detailed all-corner audit completed separately.
The P07 synchronous-ROM candidate has its own frozen source/fit directory;
these results do not describe that later candidate.
