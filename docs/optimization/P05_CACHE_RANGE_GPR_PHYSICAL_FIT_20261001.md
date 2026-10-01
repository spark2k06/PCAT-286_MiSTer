# P05: fitted generic cache range and GPR timing checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -1.673 | +0.136 | +0.544 | +0.720 | +1.549 | +2.202 | +4.505 | +2.940 |
| 7_slow_1100mv_-40c | -1.709 | +0.031 | +0.493 | +0.890 | +1.686 | +2.584 | +5.094 | +2.409 |
| MIN_fast_1100mv_100c | +2.182 | +0.088 | +9.921 | +9.687 | +10.325 | +7.730 | +9.474 | +0.856 |
| MIN_fast_1100mv_-40c | +2.443 | +0.014 | +11.325 | +11.210 | +11.691 | +8.126 | +10.900 | +0.169 |

Evidence: `docs/evidence/cache-range-gpr-physical-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.

## Interpretation

This measures the combined CPU changes committed in upstream a1bc502 and
integrated by 0d41106. Slow CPU setup is -1.673 ns at 100 C and -1.709 ns
at -40 C. The warm improvement over the prior core-placement fit is
0.305 ns; the cold improvement is only 0.033 ns. All four SDRAM
input/output setup/hold minima and global hold remain positive. The
smallest global hold is +0.014 ns; the smallest SDRAM output hold is
+0.169 ns. The cold parent HDMI domain retains setup -0.132 ns.

Both slow CPU limiting paths start at micro_pc, cross three microcode
ROM LUT levels and operation decoding, then the operation-selected
16-bit stack offset, the early range predicate, operand completion and
GPR priority/data reduction. The cache-limit mux was removed from this
path, but the stack-offset mux and combinational ROM remain. The next
candidate checks cached six-byte system bounds and shares ordinary
protected-access range predicates; its fit is independent and pending.

The eight physical-owner CheckIT simulation fixtures retain every cycle,
stall, bus, retirement and signature metric, as recorded in
docs/evidence/cache-range-gpr-20261001. These fixtures establish cycle
preservation for their workloads, not a new CheckIT hardware score.
