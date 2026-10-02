# RTC and held video payload placement comparison - 2026-10-02

All three candidates contain the formally proven RTC binary-to-BCD lookup.
They are separate fresh frozen-source fits at the real 50 MHz system clock.
No timing closure is claimed; every measured failure is retained.

| Candidate | Slow corner | Global setup | CPU setup | Global hold |
| --- | --- | ---: | ---: | ---: |
| RTC lookup: original constraints, seed 2 | 7_slow_1100mv_100c | -0.273 | -0.141 | +0.155 |
| RTC lookup: original constraints, seed 2 | 7_slow_1100mv_-40c | -0.239 | -0.239 | +0.029 |
| RTC lookup: rejected 0.6 ns route-bound experiment, seed 3 | 7_slow_1100mv_100c | -0.534 | -0.534 | -0.079 |
| RTC lookup: rejected 0.6 ns route-bound experiment, seed 3 | 7_slow_1100mv_-40c | -0.755 | -0.755 | -0.101 |
| RTC lookup: rejected 1.0 ns route-bound experiment, seed 3 | 7_slow_1100mv_100c | -0.337 | -0.286 | +0.228 |
| RTC lookup: rejected 1.0 ns route-bound experiment, seed 3 | 7_slow_1100mv_-40c | -0.420 | -0.272 | +0.031 |

## Interpretation

The original-constraint seed-2 fit has positive hold and SDRAM setup/hold
in all four corners, but CPU setup is -0.141 ns/-0.239 ns in the slow corners.
The earlier P07 fits had positive CPU setup. Changing the RTC logic reshuffles
placement, so its functional optimization does not imply uniform CPU improvement.

The seed-3 fits additionally constrain only the 163 held video-statistics
payload edges to 0.6 ns or 1.0 ns. Neither satisfies its added bound.
The 0.6 ns fit also reintroduces an EGA DAC address hold violation.
The 1.0 ns fit has positive hold, but negative CPU/FDC/HDMI setup paths.
The original 5 ns held-payload requirement and conditional SDRAM budgets remain
unchanged in every fit. No failed bound has been selected in production.

## Next bounded implementation

The seed-2 CPU route contains late operation qualification followed by stack
offset selection/arithmetic, protected range checking, completion and GPR
priority logic. The next candidate isolates the independent arithmetic before
the stack-offset mux with preserved combinational nets. It must first prove
exact stack-offset equivalence and pass affected call/return tests. This is
a physical optimization hypothesis; no instruction cycle reduction is claimed.

Evidence directories and individual fit documents use the three run names
above. The source/bitstream identities and all-corner results are recorded.
No fresh CheckIT hardware measurement or full CPU regression was performed.
