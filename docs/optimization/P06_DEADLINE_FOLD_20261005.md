# P06 — Fused deadline arithmetic, idle memory payload and palette hold

Status: **FORMAL_AND_DIRECTED_PASS; FIT_COMPLETE_TIMING_OPEN**.
Full regression is **AUTHORIZED_AFTER_TIMING_CLOSURE_NOT_RUN** following the
user's latest instruction. Earlier sealed receipts retain their then-current
**USER_DEFERRED** disposition. No hardware result is claimed.

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

## Completed placement retry — seed 2

The second frozen fit changes only QSF `SEED 1` to `SEED 2`; all 1,390
inputs are checked, with the controlled BUILD_DATE preflow retained.
Compilation takes 28m39s. The additional 0.500 ns palette minimum-route
requirement remains active and hold is now positive at every corner.

| Timing corner | Global setup (ns) | Global hold (ns) | Recovery (ns) | Removal (ns) |
| --- | ---: | ---: | ---: | ---: |
| Slow 1100 mV, 100 C | -0.312 | +0.189 | +3.110 | +0.498 |
| Slow 1100 mV, -40 C | -0.248 | +0.073 | +3.304 | +0.462 |
| Fast 1100 mV, 100 C | +2.286 | +0.133 | +4.648 | +0.301 |
| Fast 1100 mV, -40 C | +2.626 | +0.034 | +4.978 | +0.228 |

The remaining hot setup path is CPU prefetch/service permission through
the descriptor selector and pre-fault qualification to SP. The cold CPU
setup margin is -0.106 ns through protected return stack-range logic;
the cold global path remains the HDMI horizontal-to-vertical decision.
CPU hold is +0.121 ns minimum. Bridge, buffers and SDRAM retain positive
scoped margins. The same fitted artifacts checked with the original SDC
have minimum hold +0.073 ns. Neither constraint set closes setup yet.

Placed ALMs are 36,854 / 41,910 (87.94%); equivalent ALMs 31,633;
registers 38,333. RAM, M10K, DSP and PLL totals match seed 1. The inclusive
CPU accounts for 8,295.1 placed ALMs and 5,606 registers. Constraint coverage
and the mapped palette scope remain unchanged.

[The sealed seed-2 fit evidence](../evidence/p06-deadline-fold-seed2-fit-20261005/result.json)
binds all verified sources, four-corner reports and original-SDC audit.
After archive readback, 321,128,264 bytes of owned source copies and compiler
databases are removed; RBF/SOF and reports remain available.

RBF: `build/p06-deadline-fold-seed2-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`,
4,146,272 bytes, SHA-256
`05aa2f73c75c3b36dfb2d0fba579f5afe82a77d0036cd800f66ec6580d5d9492`.
It was announced at assembler availability before the final custom STA.

### Prepared scaler fallback — private proof only

The actual `sys/ascal.vhd` OSWEEP process has been extracted and checked with
the candidate horizontal predicate `o_htotal>0 AND o_hcpt<o_htotal-1`.
The operand type is VHDL `natural range 0..4095`; intermediate expressions
are integers, so this preserves `4095+1=4096` and `0-1=-1` semantics.
No production source is changed by preparing this option.

Native GHDL checks all 16,777,216 counter/total pairs and 40,000 complete
process transitions against an independent edge oracle. GHDL-synthesized
actual processes also pass an arbitrary-state/context one-step Yosys
equivalence proof for all 22 retained state fields. A wrong off-by-one
predicate is rejected by native and formal checks. The final native log
has no warnings. This is an OSWEEP proof, not whole-scaler regression or a
claim that a future placement improves timing.

[The private proof and source bindings](../evidence/p06-scaler-compare-proof-20261005/receipt.json)
are archived and read back before its 4 MB of owned temporaries are deleted.
It is available if the unchanged-RTL placement retry still needs an HDMI
logic correction.

### Applied scaler terminal correction

The seed-2 retry leaves the HDMI setup path open. The proved predicate is
therefore applied as the sole change in `sys/ascal.vhd`. Its reusable
checker is `scripts/test_ascal_terminal_equivalence.py`.
The installed source passes the exhaustive 16,777,216-pair predicate check,
40,000 complete OSWEEP transitions and arbitrary-state/context actual-process
equivalence. An off-by-one mutant fails both native and formal checks.
Full-file GHDL analysis passes VHDL-93 and VHDL-2008 for both versions.
Ten inherited declaration-hiding warnings per analysis are compared by
exact source anchor and normalized diagnostic; no new warning is accepted.
Extracted native and synthesis checks are warning-free.

[Applied source-bound evidence](../evidence/p06-scaler-terminal-applied-20261005/receipt.json)
includes the complete files, helper and diagnostic trials. The candidate
file SHA-256 is `412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186`;
reversing the sole predicate reconstructs the original file byte for byte.
Archive readback precedes deletion of 23,841,296 bytes of owned temporaries.
No register, cycle or clock changes. FPGA timing benefit is not yet measured.

### Rejected descriptor comparator rewrite

A private exact-equivalence experiment replaces descriptor-end comparison
with split index/low-bit comparison. Every selector output is equivalent,
but generic mapped comparator depth increases from 9 to 12 despite two fewer
gates. It is not applied; production selector RTL remains unchanged.
[The rejected experiment](../evidence/p06-selector-entry-bound-proof-20261005/mapping-comparison.json)
is preserved to avoid repeating it. Generic depths are not Cyclone V timing.

### Applied CPU null-segment commit specialization

The hot seed-2 path crosses descriptor selection/pre-fault qualification to
SP. One assignment now specializes the protected DS/ES null-selector commit:
`!descriptor_active_q && segment_reload_operation && tmp0_q[15:2] == 14'd0 && segment_index != 2'd2`.
The existing reload qualifier retains permission, opcode, PE and temporary
validity. Null fixes TI/index to zero, so the general address-carry and table
limit checks are redundant for this commit. General descriptor outputs and
pre-fault consumers remain intact; SS and descriptor-active guards are explicit.
No register, cycle, microcode word, clock or architectural result changes.

The portable source is committed in SPK286 at `3001de76db5e47612274b3d9473e524dba1654a3`
and the complete vendor mirror is synchronized to that revision. The PCAT
generator adds only the named new raw-source hash, preserving the historical
pilot. Regeneration leaves top/events byte-identical; the timed executor has
only the same single assignment changed. The repeat-local contract is unchanged.

The installed raw and timed qualifier/selector cones prove all ten observable
outputs for every binary input and arbitrary retained state, with no protocol
or reachable-state assumptions. Four faulty guard/slice/opcode variants per
source are rejected. Independent review binds the exact seed-2 fitted path.
Generic mapping changes 485 to 446 gates; permission-to-result depth falls
35 to 6. These figures do not predict Cyclone V ALMs or final slack.

Strict actual-upstream executor lint and full PCAT profiled-CPU lint pass.
Protected-foundation and segment-lifecycle pass both simulators; lifecycle
checks 42 cases / 3,677 assertions per simulator. The existing directed
expand-down bank, including DS/ES null acceptance and SS fault/no-write,
passes Icarus. Its costly Verilator frontend is stopped with its evidence
retained; that result and the longer matrix are not represented as PASS.
Scheduler and full-top prefix oracles also pass both simulators. No test
expectation is changed.

[Source-bound applied proof, review and directed evidence](../evidence/p06-null-segment-specialization-20261005/receipt.json)
is sealed before compiler/simulation temporaries are removed. The next frozen
all-features fit uses these two applied logic changes and seed 2. Physical
closure is still pending; complete regression starts after positive setup
and hold at all four corners, against the selected candidate.

### Completed null-segment / scaler-terminal fit

The frozen all-features seed-2 candidate at `3d1fd8d4c5433c8f4194c6b13b300362e24d4e68`
finishes compilation in 29 min 40 s. Its 2,062 actual source inputs and the
1,241-file canonical vendor import at `3001de76` are bound before and after
compilation. The later standalone generator maintenance at `c9239dc3` is
not a source change to this fit. The generated build date is the only
declared preflow source transition. All features and physical clocks remain
identical to the preceding seed-2 fit.

| Corner | Global setup ns | Global hold ns | CPU setup ns | Recovery ns | Removal ns |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow 100 C | -0.337 | +0.248 | -0.337 | +3.032 | +0.477 |
| Slow -40 C | -0.197 | +0.036 | +0.026 | +3.219 | +0.396 |
| Fast 100 C | +2.422 | +0.119 | +9.270 | +4.548 | +0.279 |
| Fast -40 C | +2.724 | +0.050 | +10.895 | +4.909 | +0.198 |

Hold is positive at all four corners with the retained 0.500 ns palette route
requirement. Setup remains open. A separate four-corner audit overlays only
the original SDC on the same fitted database; all eleven bound fitted/RBF/SOF
artifacts are unchanged. It confirms the same setup failures. No constraint
is relaxed to declare closure.

The old null-descriptor and horizontal-terminal routes no longer lead the
reported paths. The hot CPU path now crosses replay selection, service start,
the stack offset selector, a protected range comparison and SP writeback:
16 logic levels, 19.623 ns data delay (12.911 ns interconnect). A separate
prefetch-to-synchronous-microcode-address path reaches -0.213 ns. Cold HDMI
now crosses `o_hsize` through two arithmetic chains to `o_hacc_next`, three
reported logic levels and 6.566 ns data delay. These actual remaining paths
guide the next private experiments; a proof alone is not a measured timing
improvement.

Placement uses 36,896 / 41,910 ALMs (88.04%), equivalent ALMs 31,609,
38,374 registers, 3,301,019 RAM bits, 416 M10K blocks, 39 DSP blocks and
three PLLs. Relative to the preceding seed-2 fit, placed ALMs rise by 42
and equivalent ALMs fall by 24; physical register duplication accounts for
the changed register total, without additional RTL state. The inclusive CPU
uses 8,191.4 placed ALMs and 5,606 registers, down 103.7 placed ALMs.

[Sealed fit, sources, reports and original-SDC evidence](../evidence/p06-null-segment-fit-20261005/result.json)
retains exact inputs, actual microcode RAM contents, proof references and
readback-verified reports. The full regression is explicitly authorized after
positive setup and hold at all four corners, and has not started on this
failing candidate. The two stale fixed-CPU verification adapters have been
[repaired and checked independently](../evidence/verification-adapters-fixed-source-20261005/README.md),
preserving their original references and directed expected values.

This non-closing fit is not eligible for the authorized full regression.
After committed archive readback and independent review, 331,261,570 bytes
of its owned compiler database and source copies are removed. The archive
retains all 2,062 effective sources; RBF/SOF, output reports and both STA
inventories remain available. Its `--rm` containers have already exited.
The later positive candidate will be frozen separately for the regression.

RBF: `build/p06-null-segment-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`,
4,114,900 bytes, SHA-256
`083c91a21a1d21ef9cf1be61aebd1c8a5ebeca0ebc873415271635b6bfd415bd`.
It was announced at assembler availability before the custom STA completed.
