# P05: rejected SDRAM phase probe

A physical 50 MHz PLL output advanced the SDRAM DDR clock by 3 ns. The CPU,
SDRAM controller and memory owner retained their original 50 MHz clock.
Startup gated memory/CPU reset until the PLL lock passed a two-register
synchronizer. The clock's derived 20 ns period and actual PLL output phase
were checked in the SDC; the SDRAM input/output budgets were unchanged.

The fresh fit completed with zero errors. It made SDRAM output hold positive
in all corners, but input setup became negative. This is a rejected probe,
not an accepted production change. The production top/SDC/QIP were restored
to the committed phase-zero DDR clock; no input multicycle exception was
added to suppress the failing paths.

| Corner | SDRAM output setup | SDRAM output hold | SDRAM input setup |
| --- | ---: | ---: | ---: |
| Slow 100 C | +3.060 ns | +2.555 ns | -9.964 ns |
| Slow -40 C | +3.318 ns | +2.750 ns | -9.429 ns |
| Fast 100 C | +8.227 ns | +1.900 ns | -8.215 ns |
| Fast -40 C | +8.946 ns | +1.788 ns | -7.849 ns |

The existing pin-level entry bench now supports a clock advance parameter.
At zero and 3 ns advance it passed the same 79 checks and six beats in
Icarus and Verilator. The separate PLL/lock model passed 603 checks and 400
DDR output edges; the official Quartus DDR simulation library also passed
2,000 edges. The PLL model tests nominal phase and reset/lock sequencing,
not analog PLL behavior or post-fit timing. Their passing functional results
do not override the physical STA failure.

Evidence, the frozen source manifest and the reproducible prototype patch
and additional source files are retained in
`docs/evidence/sdram-phase-probe-20261001`. No MiSTer run or full CPU
regression was performed. External memory qualifications remain those in
`P05_SDRAM_BUDGET_20261001.md`.
