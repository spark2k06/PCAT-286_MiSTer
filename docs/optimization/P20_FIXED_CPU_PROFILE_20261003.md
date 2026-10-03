# P20: one fixed CPU implementation at 50 MHz

Date: 2026-10-03. User-requested cleanup before fresh timing closure.

## Implementation

`config.tcl` no longer selects P01/P02/P05/P06/P07, the RAM read buffer,
the hardware observer or the diagnostic CPU /2 clock.
The formerly active RTL branches are now unconditional. The top-level debug
menu, overlay and divider alternatives are removed. Bit 71 remains reserved,
so other OSD settings retain their positions. CPU/bridge/memory stay at 50 MHz.
Boot-splash and sound-card settings remain separate product features.
The required `SPK286_AT_CDC` platform architecture is selected in the QSF,
independently of the CPU configuration; it is not retired. Two initial fits
with that selection accidentally missing are discarded, not timing evidence.

Native CPU setup/trace interfaces and reusable unit-test modules remain
available to verification; they do not create a production debug option.
Leaf-module parameters used by isolated reference tests are not CPU profiles.
The asynchronous microcode ROM remains a compiler/reference-test artifact;
the CPU unconditionally instantiates its synchronous implementation.

`SYSTEM.sdc` removes only the unused observer/divider selection. The active
CPU clock remains `FPGA_CLK2_50`, and SDRAM/device budgets and timing exceptions
are retained. This cleanup does not establish timing closure.

## Validation

Frozen original sources: `build/fixed-cpu-profile-before-20261003/work`.
The original active macros are supplied to Verilator preprocessing and compared
with the new sources without CPU macros, retaining the required platform CDC
macro from the QSF. All **ten** CPU/bridge/top-level, platform CDC and
affected testbench files have identical normalized preprocessor output. The
only additional permitted removal is the exact observer-enable declaration,
which is verified to have no consumer after preprocessing.

Recorded checks:

- `FIXED_CPU_ACTIVE_RTL_EQUIVALENCE_PASS files=10 unchanged=461`, recorded
  against the current clean working sources in `equivalence-clean-current.json`.
  String literals are preserved, including spaces and comment-like text;
  only comments/whitespace outside them are ignored. The only normalized
  declaration removal is the proven unused observer-enable wire.
  Both simulation and `SYNTHESIS` views agree. The audit also scans unchanged
  sources for conditional dependencies on the retired macros.
- All other 461 Verilog/VHDL, ROM/microcode and QIP source files are byte-identical
  to the frozen reference. Changes outside the cleanup are rejected.
- `FIXED_CPU_ASSIGNMENT_CONSTRAINT_EQUIVALENCE_PASS commands=130`:
  configuration/QSF macros agree after retiring the CPU/debug selectors;
  CDC and sound settings are retained. The QSF changes only by selecting CDC
  outside `config.tcl`. Other SDCs are byte-identical. Executing the real
  `SYSTEM.sdc` with symbolic Tcl collections produces the same 130 constraint
  commands, both with and without the optional boot splash. This is a command
  comparison, not a fitted-netlist or path-coverage claim.
- Strict standalone CPU Verilator lint: `LINT PASS`; generated microcode check
  passes with 123 entries, 743 words and a 10-bit address.
- Actual packed OSD configuration: `AT_CONFIG_NO_DEBUG_PASS bytes=1796`;
  selector and profile elaboration pass.
- Bridge and fetch tests pass in Icarus and Verilator, followed by the affected
  memory-arbiter and DMA/PIT checks: `AT_BUS_LATENCY_TEST_PASS`.
- Platform CDC tests pass for coherent snapshots, OSD, video calculation,
  legacy defaults, VHDL snapshots and HDMI PLL observations: `cdc-check.log`.

The first two incomplete fits are discarded after detecting the missing CDC
selection. Their Docker containers were stopped at the user's request. The
QSF now requires that selection, and the project guard rejects its absence.
Windows-created build manifests use portable path separators; the frozen-run
reader also accepts older Windows manifests without changing their contents.

The subsequently corrected DMA/prefetch trial was also stopped and its Docker
container removed when the user requested a cleanup-only baseline commit
before timing changes. Its proposed RTL/tools remain in the frozen
`build/fixed50-dma-prefetch-cdc-fit-20261003` workspace and
`build/fixed50-pending-tools-20261003`; none are in this baseline's production
sources. No RBF or timing result from the stopped trial is accepted.

Negative controls reject a changed source outside the cleanup and detect a
changed SDRAM output-delay budget. The focused bridge/fetch/arbiter/DMA/PIT
checks, profile elaboration and strict CPU lint are rerun on the clean sources.
The unchanged platform CDC sources retain their separately executed CDC tests.
Compact receipts/logs are committed under
`docs/evidence/fixed-cpu-profile-20261003`.

The fresh cleanup-only snapshot is `build/fixed-cpu-clean-baseline-20261003`.
Its prepare-only Quartus check passes with `AT_PROFILE` and `SPK286_AT_CDC`,
without retired CPU/debug macros, retaining the existing SDC set. No mapping,
fit or bitstream generation runs for that preparation. The preparation log
and effective Quartus assignment check are retained with the evidence.

The benches retain their former active assertions; obsolete profile-selection
branches are removed. Simulation runners reject obsolete config overrides,
rather than label identical implementations as different A/B profiles.

Evidence and logs: `build/fixed-cpu-profile-before-20261003`. No full regression
or new hardware benchmark is performed for this source-pruning milestone.
Timing and fitted resource numbers still belong to P18/P19 until a fresh fit.

## Next milestone

The user requires this verified baseline commit before any further timing RTL.
Then perform a fresh full fit and TimeQuest audit at the unchanged physical clocks.
Use actual path reports to select small structural or placement corrections,
with source-bound directed checks and measured whole-design resource cost.
The user requests positive setup and hold without expanding the caches or
introducing a new CPU/SDRAM clock relationship.
