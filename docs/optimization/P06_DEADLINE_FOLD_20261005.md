# P06 — Fused deadline arithmetic, idle memory payload and palette hold

Status: **FORMAL_AND_DIRECTED_PASS; FIT_NOT_RUN**.
Full regression remains **USER_DEFERRED**. No hardware result is claimed.

## Starting point

The preceding all-features live-speed RBF at `a73ab7b` has worst four-corner
setup -6.051 ns, from `micro_entry[2]` through execution timing and descriptor
selection to `gpr_q[70]` (SP bit6). Original-SDC hold is +0.015 ns; the
additional 0.500 ns palette route requirement still misses by 0.065 ns.
Physical placed ALMs are 37,054 (88.4%).

## Changes

1. The executor generator localizes four more positive opcode-qualified OR
   branches, including call-gate CS validation. The count rises from 133 to
   137. The actual permission formula is unchanged; two REP checkpoints and
   all three stateful subservice enables retain their permission. No state
   or cycle is added. The actual descriptor-selector cone and SP write
   qualifier are proved equal for arbitrary state/data under the independently
   proved permission contract.
2. The execution metadata provider preserves its unsigned budget as a
   carry-save pair. The scheduler combines it with the retained alignment,
   target and elapsed context in a single final carry-propagating comparison.
   Admission/reporting still uses the original saturated budget. The signed
   13-bit difference is `budget + extra + target - age - 1`, bounded to
   -1024..3113. Negative means due; zero also means due at a productive CPU
   boundary. The original saturated-age override is preserved. Metadata
   arriving late, event selection and freeze behavior are unchanged.
3. In each idle memory buffer, outgoing payload follows the current input
   independently of request classification. Existing `out_valid` and
   `out_command_valid` still qualify consumption. The code buffer preserves
   its asynchronous-tag miss expansion; production synchronous tags accept
   locally and have no idle miss expansion. Retained payload still governs
   every owned transaction. Handshake, response, cache state, write posting,
   cancellation and drain behavior are unchanged.
4. The six software palette RAMs use a shared bijective address permutation:
   bits6:0 are `index[6:0] XOR index[7:1]`; bit7 is
   `index[7] XOR index[0] XOR index[1]`. The same permutation governs every
   software RAM read and write, so logical colours remain unchanged. Default
   ROMs, validity/override maps and last-write bypass comparisons keep their
   original logical indices. Every physical address bit now requires XOR
   logic, targeting the short MLAB write-address hold paths. No delay cell,
   register or cycle is introduced; actual inference and margins must be
   checked in the fit.

The physical CPU/bridge/SDRAM clock remains 50 MHz. All features, including
OPL2, remain enabled. No SDC requirement is relaxed or path excluded by these
changes. No additional RTL register, pipeline cycle or PLL is introduced.

## Verification boundaries

The new deadline proof couples actual production provider functions and
event selection to both scheduler modes, comparing every public output and
all 37 retained state bits against `a73ab7b`. It additionally checks every
equal retained state, including elapsed1022/1023, without a long symbolic
warm-up. Budget corruption, inverted sign and missing saturation are rejected.
The previous execution-deadline proof also passes after wiring-only updates.

The buffer proof compares actual one-step FF transitions and RAM interfaces
with common arbitrary previous state/content, without protocol or reachable-
state assumptions. Only inactive outgoing payload is intentionally different;
handshake, responses and next-state bits are compared unconditionally.
Enabled RAM write data and address/control interfaces are also compared.
All six buffer configurations pass, and six corrupted-address variants are
rejected with SAT counterexamples. Four existing/new buffer banks pass both
simulators; the existing composed data pipeline passes Verilator (its
pre-existing Icarus delta-loop limitation remains documented).

The palette proof uses the actual encoder and an arbitrary mapped memory row
to prove every write/read equality decision and retained colour relation.
All 256 addresses are unique; a collision mutant is rejected. The original
memory bench passes with both old and new RTL in both simulators. Paired
complete DAC I/O frontends match for 5,124 cycles in each simulator. The
encoder has strict warning-free lint. Historical frontend and buffer lint
diagnostics are checked against the frozen baseline; no new warning is
allowed. These narrowly scoped existing exceptions are recorded in receipts.

Directed CPU validation passes for all eight profiles, handoff/deadline
probes, REP, stack frames, protected call gates/returns and live profile
changes in both simulators. The six affected lifecycle units produce 48
Icarus and 48 Verilator passes, plus six MAX/raw-equivalence passes. Live
switching exercises 192 CPU/production-bridge cases and 6,400 clock cases in
each simulator. The preceding complete 17 handoff/event result entries and
51 common lifecycle result entries remain exactly equal, including their
cycle traces. The complete CPU lint and project/top elaboration also pass.
These checks do not replace the deferred full regression or board testing.

The combined receipts and read-back-verified archive are preserved in
`../evidence/p06-deadline-fold-20261005`. They bind the actual source bytes
used by the tests. The subsequent fit must match those bindings.

## Physical acceptance

The consolidated fit must bind these verified sources, retain the current
clock/constraints and report all four timing corners. Generic cell counts
are not Cyclone V ALMs. A positive margin claim requires the actual fitted
setup/hold/recovery/removal results; formal equivalence alone does not prove
timing closure. Compiler and simulation temporaries are cleaned only after
sealed evidence is read back, preserving the RBF and reports.
