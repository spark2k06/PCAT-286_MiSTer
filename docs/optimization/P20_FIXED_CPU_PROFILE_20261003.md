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

- `FIXED_CPU_ACTIVE_RTL_EQUIVALENCE_PASS files=10`, recorded in
  `equivalence-cdc.json`. The cleanup-only control preserves the original
  prefetch and DMA response logic; later timing prototypes are not covered.
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

The benches retain their former active assertions; obsolete profile-selection
branches are removed. Simulation runners reject obsolete config overrides,
rather than label identical implementations as different A/B profiles.

Evidence and logs: `build/fixed-cpu-profile-before-20261003`. No full regression
or new hardware benchmark is performed for this source-pruning milestone.
Timing and fitted resource numbers still belong to P18/P19 until a fresh fit.

## Next milestone

Perform a fresh full fit and TimeQuest audit at the unchanged physical clocks.
Use actual path reports to select small structural or placement corrections,
with source-bound directed checks and measured whole-design resource cost.
The user requests positive setup and hold without expanding the caches or
introducing a new CPU/SDRAM clock relationship.
