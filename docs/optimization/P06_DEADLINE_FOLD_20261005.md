# P06 — Fused deadline arithmetic, idle memory payload and palette hold

Status: **FORMAL_AND_DIRECTED_PASS; FIT_COMPLETE_TIMING_OPEN**.
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

## Completed all-features fit — seed 1

The frozen `f2ea538` snapshot contains 1,390 files. Quartus 17.0 completes
compilation in 28m57s. The measured result keeps the same RTL, configuration,
clock relationships, seed and SDC as the preceding live-speed fit, apart from
the four verified logic changes above and the existing BUILD_DATE preflow.

| Timing corner | Global setup (ns) | Global hold (ns) | Recovery (ns) | Removal (ns) |
| --- | ---: | ---: | ---: | ---: |
| Slow 1100 mV, 100 C | -0.096 | +0.162 | +3.025 | +0.582 |
| Slow 1100 mV, -40 C | -0.288 | +0.043 | +3.205 | +0.445 |
| Fast 1100 mV, 100 C | +2.078 | +0.048 | +4.737 | +0.361 |
| Fast 1100 mV, -40 C | +2.431 | -0.047 | +4.973 | +0.223 |

Global setup improves from -6.051 to -0.288 ns. The worst CPU setup is now
-0.054 ns at 100 C, with -0.033 ns at -40 C. The former scheduler/descriptor
critical cone is removed; the remaining CPU paths cross prefetch/operand
and event stack-range qualification. CPU hold is positive, minimum +0.121 ns.

All four corners now have positive setup for the bridge (+1.595 ns minimum),
memory port (+2.530), code buffer (+0.243), data buffer (+1.355), data output
cone (+3.799) and SDRAM owner (+1.361). SDRAM pin budgets retain positive
setup/input +5.189 ns, setup/output +4.601 ns, and positive hold.
These scoped figures are minimum margins across the four corners.

The global setup path is now the inherited HDMI scaler's horizontal
terminal decision to vertical counters, at its unchanged 148.5 MHz clock:
`o_hcpt[6] -> o_hcpt+1<o_htotal -> o_vcpt[5]`, four logic levels.
The remaining negative hold is six reported blue-palette MLAB address
endpoints under the additional 0.500 ns route requirement. The XOR encoder
is physically present and all six 256x6 software memories still use MLAB.
No register, memory conversion or cycle was added to the palette.

An independent four-corner STA with the original SDC verifies eleven fitted
artifacts, including the RBF/SOF, unchanged. Its worst global hold is
+0.043 ns. The extra route requirement stays active for the candidate;
its -0.047 ns failure remains open. This is not complete timing closure.
Constraint coverage matches the preceding fit: inherited platform issue
counts are unchanged, with 25 partial min/max assignments under the guard
and 24 under the original SDC. Fitter-time palette selectors cover 8
sources/288 endpoints; mapped duplicates and MLAB address-bit expansion
produce 11 sources/1,440 endpoints, still covered by the same selectors.

| Resource | Live-speed baseline | Deadline-fold seed 1 | Change |
| --- | ---: | ---: | ---: |
| Physical placed ALMs | 37,054 (88.4%) | 36,913 (88.1%) | -141 |
| Equivalent ALMs | 31,895 | 31,602 | -293 |
| Fitted registers | 38,207 | 38,384 | +177 |
| Logical block-memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K blocks | 416 | 416 | 0 |
| DSP blocks | 39 | 39 | 0 |
| PLLs | 3 | 3 | 0 |

The register difference is fitter duplication; the design implementation
register count remains 35,404. The inclusive CPU hierarchy accounts for
8,311.5 placed ALMs, 5,613 registers and one 9,216-bit M10K. Hierarchical
fractional ALM attribution is not a separate device allocation.

Evidence: [source-bound fit, reports and original-SDC audit](../evidence/p06-deadline-fold-fit-20261005/result.json).
The [independent read-only review](../evidence/p06-deadline-fold-review-20261005/review.md)
records all scoped deltas and the exact remaining paths. It does not infer a
standalone posted-write WNS from the data-output or SDRAM-owner selectors.
Every functional receipt is bound to the frozen source inputs. Two historic
mutation files listed by the broad elaboration inventory are explicitly
archived as uncompiled inventory; they are absent from the elaboration
command and Quartus QIPs. BUILD_DATE is the only controlled nonfunctional
source difference from the elaboration receipt.

RBF: `build/p06-deadline-fold-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`,
4,141,940 bytes, SHA-256
`5b809465da95d32150a858bf04db6abc52da630b459307d453df556c91973296`.
The RBF is announced at assembler completion, before the final STA pass.

The next trial changes only placement seed 1 to 2 in another frozen copy of
these same inputs. No functional change or new full regression is needed
for that controlled physical experiment. All features remain enabled.
