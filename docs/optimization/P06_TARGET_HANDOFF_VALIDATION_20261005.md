# P06/P12: source-retained target handoff validation

Date: 2026-10-05. This closes the directed source timing and replay checks for
the Intel branch-to-target allowance. Complete architectural regression,
event/fault integration qualification and fitted FPGA cost/timing remain
separate acceptance steps.

## Timing rule and controller

Intel 210498-005 Appendix B requires an additional clock per byte of the next
executed instruction for taken Jcond/JMP and documented CALL/RET forms. The
source table exposes potential form eligibility; the successful architectural
redirect qualifies the actual handoff. Not-taken conditions never create a
target token. LOOP/LOOPE/LOOPNE and IRET do not acquire this allowance.

The rendered B-54/PDF262 scan also explicitly gives JCXZ **7 taken / 4 not
taken**. Its previous shared LOOP8/4 row is corrected to7/4; ordinary LOOP
remains8/4. JCXZ has the Jcond target-length note. The source scan and manual
identity are preserved in the earlier
[timing audit](P06_HISTORICAL_TIMING_AUDIT_20261005.md).

The retained handoff owns seven state bits: pending, qualified, estimated-fault
and four length bits. Its ordinary length is1..10 including all encoded bytes.
The scheduler keeps the source's base after functional END, accepts a later
target qualification through a separate channel, and publishes only at a
processor boundary satisfying both the source dependencies and the saturated
`base + odd-reference corrections + target length` budget. Actual memory READ
waits still count productive processor boundaries; bus service is not charged
again as a guessed refill constant.

Only registered pending/qualified state feeds deadline readiness. The live
redirect is not fed back into the EU permit. A stale parser terminal on a new
redirect edge cannot qualify the new source. The caller must enforce that
successful redirect precedes functional END; the complete CPU branch probes
assert that no redirect overlaps its raw or public retirement.

Invalid, truncated, overlength or unavailable successor encodings use an
explicit estimated policy: they release the source at its ordinary minimum
with zero target-length allowance. This does not inject a source fault. The
CPU must retain successor bytes/fault IP and use ordinary successor fault
handling after the source event boundary. This policy is not a documented
historical fault duration. MAX bypasses the handoff channels and state.

## Focused checks

Final accepted unit receipts are in the
[sealed packet](../evidence/p06-target-handoff-20261005/README.md).

| Check | Icarus | Verilator |
| --- | ---: | ---: |
| Scheduler assertions, including late length after frozen END and saturation |54|54|
| Retained handoff assertions, lengths1..10, cancellation, lateness and MAX |398|398|
| Replay storage assertions, lengths1..10/order, holds, capacity and epoch priority |246|246|
| Exhaustive timing metadata caller cases |43,878|43,878|

Five deliberate controller/scheduler mutations fail the independent unit
oracles: missing target allowance, premature publication, fixed target penalty,
MAX pending leakage, and11-bit saturated-total overflow. Nine metadata mutations
and the include-guard mutation also fail. The JCXZ mutation is checked against
the published B-54 row; no architectural oracle was changed to obtain a pass.

The full sum needs12 bits before clamping: `1023 + 1023 + 10 = 2056` would
otherwise wrap an11-bit temporary. Base/elapsed/odd retained state widths are
unchanged. The explicit maximal-operand test protects this corner.

## Original B0 and branch probes

The original COM and its exact baseline/B0 bytes are unchanged. The new builder
is derived from the archived previous audit builder; only source bindings,
passive safety assertions and comparison reporting are added. All38 original
cases run at6/12.5/20/25MHz in each simulator: **304 runs**, with all**152**
complete applicable traces agreeing (**208,327 paired rows**). The3,724 declared
empty-head X/zero rows are retained raw and excluded only where no head is
valid or consumed. No architecture or accepted transfer is normalized.

| Nominal profile | Prior baseline | Candidate baseline | Prior B0 | Candidate B0 | Prior net/iteration | Candidate net/iteration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
|6MHz|2044|2044|6909|7932|19.00390625|23|
|12.5MHz|2044|2044|6909|7932|19.00390625|23|
|20MHz|2044|2044|6910|7932|19.0078125|23|
|25MHz|2044|2044|7420|8188|21|24|

The Intel no-added-wait reference for B0 is
`256*(CMP2 + JNE3 + JE9 + JMP9 + LOOP8)-4 = 7932`. The first three candidate
profiles reach that lower bound exactly; the unchanged baseline stays2044.
At25MHz the exact B0 JMP interval is10 clocks with a scheduled minimum9,
while CMP/JNE/JE/LOOP remain2/3/9/8. This is a measured implementation/dependency
extension, not an additional table charge or justification to retune MHz.
The existing extension flag stays zero because the target-length dependency
qualifies after the earlier source minimum; it must not be interpreted as
proof that no such extension occurred.

For equal two-clock targets of lengths1/2/3, JE/JMP now have scheduled source
minima8/9/10 and pair minima10/11/12. At6/12.5/20MHz both alignments reach
those minima. At25MHz some two/three-byte placements extend beyond them;
actual target availability and implementation work still gate execution.
LOOP stays at its eight-clock source budget for all target lengths. Prefix
targets4..6 retain the earlier explicitly provisional prefix policy; this
change qualifies their encoding length, not every prefix execution duration.

## Isolated resource measurement

These are Yosys generic cells from the same package constants and immutable
parent RTL, not fitted FPGA ALMs. Separate-module counts must not be summed as
a fitted system estimate because integration can share or remove logic.

| Block | Before generic cells | Candidate generic cells | Before FF bits | Candidate FF bits |
| --- | ---: | ---: | ---: | ---: |
| Instruction timing metadata |1073|1104|0|0|
| Instruction scheduler |358|383|37|37|
| Retained target handoff |0|50|0|7|

The encoding classifier, target replay storage, whole-CPU optimization and
actual Quartus fit are outside this table. The packet preserves the generic
netlists, tool logs and unchanged-parent RTL hashes so the local deltas can be
recomputed. These results do not establish50MHz setup/hold closure or a final
RBF resource cost.
