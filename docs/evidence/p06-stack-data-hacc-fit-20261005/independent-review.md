# Independent actual fit review

Status: **PASS for evidence integrity; global timing remains open**. No test, fit, STA or regression was launched by this review.

All 2475 archived members were read back. The fitted snapshot contains 2,073 sources and 1,249 canonical vendor imports, with seed 2.

| Check | Worst margin (ns) |
| --- | ---: |
| setup | -0.063 |
| hold | +0.027 |
| recovery | +1.710 |
| removal | +0.197 |

The remaining setup path is scaler `o_ihsize[3]` to `o_hacc_next[12]` at the cold slow corner. CPU, common 50 MHz paths, buffers and SDRAM selectors are positive.

All features, clocks and constraints match the accepted parent; original-SDC STA uses the same eleven fitted DB/RBF/SOF artifacts. Actual mapped ROM contents and read-alignment parameters match the frozen contract.

The only live/frozen physical-setting difference is the declared single-line placement seed 1 to 2 overlay; every other QSF byte is identical. No active HDL/config/SDC drift is present.

Resources: 31,445 equivalent ALMs, 36,701 placed ALMs; 38,376 registers, 416 M10Ks, 39 DSP blocks and 3 PLLs.

The latest user instruction remains **pause after this fit**. Full regression and hardware validation are unrun; no global closure is claimed.
