# P05: fitted GPR priority timing checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -1.792 | +0.190 | +1.952 | +1.564 | +1.398 | +2.719 | +5.214 | +3.094 |
| 7_slow_1100mv_-40c | -1.537 | +0.072 | +1.457 | +1.274 | +1.238 | +2.542 | +5.876 | +2.485 |
| MIN_fast_1100mv_100c | +2.084 | +0.132 | +10.380 | +10.302 | +10.446 | +7.730 | +9.970 | +0.819 |
| MIN_fast_1100mv_-40c | +2.429 | +0.045 | +11.769 | +11.684 | +11.762 | +8.126 | +11.236 | +0.189 |

Evidence: `docs/evidence/gpr-priority-physical-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Interpretation

This isolates the complete GPR priority reduction on the earlier parallel
access CPU. Compared with the correctly parsed SDRAM core-placement fit,
CPU setup improves from -1.978 to -1.792 ns at slow 100 C, and from -1.742
to -1.537 ns at slow -40 C. All four SDRAM input/output setup/hold minima
and global hold remain positive under the unchanged external budget.

The slow warm limiting CPU path now starts at micro_pc, crosses three
microcode-ROM LUT levels, then the return-stack offset and ordinary range
selection, and ends at micro_pc. The slow cold path also starts through
the ROM and reaches descriptor/GPR selection. The HDMI scaled clock has
setup -0.693/-0.327 ns; the parent HDMI clock is also negative. Placement
has changed; these results do not establish full system closure.

Quartus 17 rejected two preliminary elaborations of the generate-loop
syntax. This successful fit uses the explicit external genvar declaration
and generate block subsequently committed in upstream a1bc502. No timing
claim is based on the two failed elaborations.
