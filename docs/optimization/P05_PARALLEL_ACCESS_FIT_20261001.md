# P05: parallel protected-access fitted checkpoint

This is a fresh frozen-input fit with the real 20 ns system clock and the
corrected SDRAM budget. It is a measured checkpoint, not timing closure.

The critical CPU path now contains 17 logic levels in the warm slow corner
and 18 in the cold slow corner. Its setup is -2.106 ns and -2.186 ns;
reducing the original late range-check depth has not yet closed timing.
The next bottleneck is the generic operand service's selected cache limit,
`within_limit`, completion and GPR data selection.

This probe still used the ineffective braced SDRAM vector targets described
in `P05_SDRAM_OUTPUT_PLACEMENT_BRACED_20261001.md`. Its negative output hold
therefore does not describe the corrected bare-vector placement experiment.
The separate MAXIMUM-router probe produced the same reported CPU setup and
SDRAM hold in all four corners, with the same RBF SHA-256. That setting alone
does not resolve either violation.

| Corner | Global setup | Global hold | CPU bridge setup | Code buffer setup | Data buffer setup | Owner setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -2.106 | -2.021 | +1.940 | +1.250 | +1.531 | +2.376 | +5.525 | -2.021 |
| 7_slow_1100mv_-40c | -2.186 | -2.074 | +1.962 | +1.054 | +1.440 | +2.411 | +6.108 | -2.074 |
| MIN_fast_1100mv_100c | +2.110 | -2.007 | +10.065 | +10.302 | +10.179 | +7.721 | +9.994 | -2.007 |
| MIN_fast_1100mv_-40c | +2.393 | -2.099 | +11.592 | +11.710 | +11.705 | +8.129 | +11.394 | -2.099 |

Evidence: `docs/evidence/parallel-access-fit-20261001`. Read the complete audit alongside
the external budget and platform coverage qualifications in
`P05_SDRAM_BUDGET_20261001.md` and `P05_TIMING_COVERAGE_20261001.md`.
No hardware run or full CPU regression was performed.
