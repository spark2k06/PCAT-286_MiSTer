# P05: SDRAM output placement closes the modeled hold paths

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

Bare vector targets now correctly override the generic fast-output packing
assignment. Address, bank, data, command and data-enable registers can be
placed in the core; the dedicated DDR clock output remains in its I/O cell.
The timing-driven router can then satisfy the modeled SDRAM minimum delay.
No RTL, clock phase, system frequency or SDRAM transfer cycle is changed.

Both SDRAM input and output setup/hold are positive in all four models.
Worst output hold is +0.139 ns in the fast -40 C corner, compared with
-2.099 ns in the braced-target probe. Output setup remains at least
+5.324 ns. Global hold is also positive in all four models, with a
+0.033 ns minimum. These are margins under the documented SDRAM component
and flight-time assumptions, not a measurement of the physical board.

CPU setup remains -1.978 ns / -1.742 ns in the slow corners. HDMI also has
small remaining setup violations. This checkpoint does not close the
complete design at 50 MHz. Subsequent CPU RTL fits must recheck the layout
and all four models, since they can change these measured margins.

The project checker rejects literal braces in SDRAM vector targets and
requires explicit fast-output/data-enable OFF assignments. Its negative
test rejects the earlier frozen probe, and its positive test accepts this
frozen project. Separate failed PLL-phase probing is retained as rejected
evidence; the production SDRAM clock remains at phase zero.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -1.978 | +0.142 | +1.467 | +0.747 | +0.706 | +1.991 | +5.324 | +3.020 |
| 7_slow_1100mv_-40c | -1.742 | +0.033 | +1.868 | +1.053 | +1.156 | +2.293 | +6.142 | +2.372 |
| MIN_fast_1100mv_100c | +2.221 | +0.120 | +10.344 | +9.597 | +9.491 | +7.730 | +9.517 | +0.831 |
| MIN_fast_1100mv_-40c | +2.475 | +0.047 | +11.676 | +11.163 | +11.115 | +8.126 | +11.143 | +0.139 |

Evidence: `docs/evidence/sdram-output-placement-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.
