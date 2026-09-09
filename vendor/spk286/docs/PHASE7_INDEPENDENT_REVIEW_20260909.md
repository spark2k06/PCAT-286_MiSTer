# Independent Phase 7 review — frozen candidate

Review date: 2026-09-09. Reviewer: separate agent context
`/root/independent_phase7_review`, requested explicitly by the user and delegated
by the coordinating agent. This reviewer did not implement the candidate, did
not modify production or frozen candidate source, and wrote only in
`build/phase7-closure-20260909-review/`. The assessment below concerns the original
snapshot. Any subsequent fix requires a separately identified changed-boundary
assessment. This is an actual independent review, not implementation self-review.

## Identity and disposition

- Production HEAD observed: `74c0b53ffe0fc212e0c8b70c3a780901b69def29`.
- Reviewed source: `build/phase7-ordered-combined-prototype`.
- Exact manifest: `build/phase7-preparation/ordered-combined-full-frozen-source.json`.
- Manifest SHA256: `04ccc181a8951a66b49fc282ba9baf6471ef40ef6f1807a3b2a6bdb027030b98`.
- All 409 listed file hashes independently rechecked after the review experiments;
  zero mismatches. Runtime executable-input helper selects 328 files; its scope
  excludes ordinary documentation and the complete gate separately fingerprints
  the form/admission and completion records. These are distinct manifests.
- Human microcode source is formats 15/16/17 in order; active image is 100 entries,
  612 words, ten address bits and eight control bits. Fresh consistency check passed.
- Exact environment and verified historical log identities:
  [review-identity.json](../build/phase7-closure-20260909-review/review-identity.json).

**Disposition: changes requested; complete Phase 7 development approval withheld.**
No unmodified RTL functional failure was demonstrated. Two concrete local issues
require correction: missing arithmetic target wiring and repeated-INS temporal
input coverage. The candidate is a technically coherent functional development
increment on the provisional baseline, but the original snapshot is not ready
for complete integration/delivery. REP initial-zero-count event ordering and E7
capture admission remain independent external-evidence blockers even after the
two local issues are corrected. Reviewer agreement supplies no waiver.

## Actionable findings

Paths and line numbers below are relative to the frozen candidate root, except
where explicitly labelled production documentation or reviewer scratch.

| ID | Severity/class | Location | Finding and required action |
| --- | --- | --- | --- |
| R1 | P2, confirmed tooling defect | `Makefile:224-233`; `scripts/validate_phase7_strings.sh:17` | Restore `phase7-arithmetic-check`, which the string increment invokes and the I/O increment reaches transitively. `scripts/validate_phase7_arithmetic.sh` exists but has no Make target. A dry run returns status 2 before any tests. The complete gate uses a different path, so this is broken incremental validation/recovery, not proof of a false full-gate success. Initially identified by the coordinator; independently reproduced here. |
| R2 | P2, demonstrated verification gap | `sim/unit/spk286_string_io_tb.sv:32-40`; `sim/unit/spk286_string_io_lifecycle_tb.sv:26`; `tools/audit_io.py:106` | Existing INS stimuli change by port address or test case, but remain constant across repeated reads of the same port. A general fault that retains the first input value while still issuing every IOR passes both current string-I/O benches. Add accepted-access-dependent input data and retain the stale-input mutant. The unchanged RTL passes the discriminating test; no RTL repair is indicated by this finding. |
| R3 | P3, optional retained-test improvement | `tests/test_phase7_completion.py:7-16` | Existing negative variants fail before reaching the independent-review branch. Preserve a valid synthetic fixture plus separate changed-manifest/reviewer/report negatives so that those checks cannot regress unnoticed. Fresh scratch tests reached these branches and found correct behavior, so this is not a demonstrated validator defect. |

R1 reproduction: run `make -n phase7-arithmetic-check` in the frozen candidate.
Actual result is `No rule to make target 'phase7-arithmetic-check'`, exit 2;
see [missing-arithmetic-target.log](../build/phase7-closure-20260909-review/missing-arithmetic-target.log).

R2 reproduction is fully isolated. In a scratch copy of
`rtl/spk286_micro_executor.sv:410`, change only the ordinary TMP0 operand-capture
assignment to condition it on `!io_read || !temporary_valid_q[0]`. This keeps the
first input response but still performs each real IOR handshake. It is a general
stale-response ownership fault; there are no test addresses, record identities,
opcodes or expected payloads in the mutation. Both pristine benches pass. The
mutated `spk286_string_io` passes all 11,520 cases and the mutated
`spk286_string_io_lifecycle` passes all 376 cases. These surviving mutations are
**failed verification experiments**, not successful mutation detections.

The reviewer-only temporal-input bench passes 24 unchanged-RTL cases spanning
byte/word widths, even/odd ports, both DF directions and three READY delays. Its
stimulus changes deterministically for each completed logical input, independently
of expected CPU memory. The same mutation fails on the second stored input byte
with the intended message, `each repeated input commits its own accepted sample
low byte`. Relevant files: [review_checks.py](../build/phase7-closure-20260909-review/review_checks.py),
[checks.json](../build/phase7-closure-20260909-review/checks.json), [temporal_input.py](../build/phase7-closure-20260909-review/temporal_input.py),
[checks-temporal.json](../build/phase7-closure-20260909-review/checks-temporal.json), and
[spk286_review_temporal_input_tb.sv](../build/phase7-closure-20260909-review/spk286_review_temporal_input_tb.sv).
The new bench is a discriminating review experiment, not a claimed physical capture
or a production test until the coordinator integrates and validates it.

R3 scratch validation accepted only the valid synthetic record shape and rejected
seven intended alterations at their relevant validation branch: unapproved,
non-independent, empty reviewer, changed input manifest, changed report hash,
missing report and changed evidence hash. The helper's root constant was redirected
in the scratch process solely to keep synthetic fixtures outside the frozen source.
These explicitly labelled fixtures do not resolve any question or approve any
actual input. See [completion_contract.py](../build/phase7-closure-20260909-review/completion_contract.py) and
[completion-contract-results.json](../build/phase7-closure-20260909-review/completion-contract-results.json).

## Boundary 1 — arithmetic, byte aliases, FLAGS and D-036

Inspected the single register owner and byte-register mapping
(`rtl/spk286_registers.sv:31-57`, `rtl/spk286_operand.sv:34-49`), captured operand
and arithmetic result paths, flag masks and delayed arithmetic fault checks.
Encoded byte register bit 2 selects AH/CH/DH/BH within the correct word owner;
no parallel architectural alias storage was introduced. DIV/IDIV capture operands
before result writes and only emit result ownership after their actual iterative
computation. The explicit arithmetic-fault check precedes AX/DX writeback.

`rtl/spk286_muldiv.sv:28-43,66-108` implements D-036 as a bounded signed-byte
negative-overflow condition. It does not indiscriminately adopt a reference
emulator's finite quotient as architectural arithmetic. Legal divisions use the
ordinary quotient and remainder; zero divisors, unsigned overflow, word overflow
and positive signed-byte overflow retain divide errors. The finite result is
consulted only for negative signed-byte overflow whose corrected quotient is 80.
There are no corpus identity/address special cases. The separate positive-overflow
predictions remain unsupported and are correctly excluded from the CPU rule.

The four pinned successful overflow observations, all 5,000 F6.7 results and
reported exhaustive agreement over mathematically legal byte divisions support
the recorded compatibility policy. Four captures do not prove every silicon
revision or every unobserved overflowing input. The broader negative-overflow
condition remains a documented generalization from physical observations; this
review accepts its bounded development use under recorded D-036, not a claim
that Intel's mathematical quotient limits explicitly describe it.

Defined, preserved and undefined arithmetic flags remain separable. MUL/IMUL's
additional SZP policy is explicitly physical compatibility; DIV/IDIV preserves
undefined arithmetic bits in RTL. `tools/run_singlestep.py:355-366` permits only
original mask bits at the EXCP-identified saved FLAGS word for divide faults;
it checks the stack address and forbids masking defined bits. CS:IP and all other
frame bytes stay exact. Fresh five-test divide-admission/batch validation passed.
No confirmed functional defect found in this boundary.

## Boundary 2 — segment, far pointer, stack and redirect effects

Inspected authoritative segment/far/frame microprograms and the common executor,
segment cache, operand and fetch services. LDS/LES read both pointer words before
cache/GPR commits; address calculation uses a captured EA so destination aliases
cannot change the second read. POP SS completes through old SS and updates SP
before its new cache is committed. Segment state has one owner with explicit
normal Real Mode reload semantics. Far CALL obtains its pointer before return
stack writes; RETF acquires the complete return frame before CS:IP commit. RETF
does not clear NMI blocking. Far commit reuses coordinated CS:IP redirection.

ENTER uses a transient stack cursor rather than committing architectural SP/BP
after each write. Accepted parent/link writes survive a later fault while original
architectural restart registers feed the exception frame. PUSHA's original SP and
POPA's discarded SP slot remain explicit. BOUND/far pointer even modular word
wraps are documented physical refinements of the printed limit rule; odd FFFD/FFFF
range failures retain checks before pointer acquisition. The corresponding raw
observation and complete-family results are evidence, rather than a rewritten
claim about the manual.

`rtl/spk286_fetch.sv:69-99` retains a visible READY-stalled fetch after redirection,
marks its response canceled and starts from the new cache only after the drain.
Architectural CS:IP commit does not rely on treating discarded queued code as a
valid new instruction. No second bus owner or 386 size behavior was introduced.
No confirmed defect found. Full family/regression results here are reused historical
evidence; they were not re-executed by this reviewer.

## Boundary 3 — REP partial effects, restart and IRET

Inspected all five memory-string microprograms, four I/O-string programs,
`rtl/spk286_micro_executor.sv:82-106,334-338,360-366`, the instruction context and
event owner. Source/destination offsets are captured before SI/DI movement and
the transfer uses that old offset. Comparison operations read destination before
source; their first element is independent of initial ZF, and subsequent repetition
uses newly committed comparison flags. The source segment can be overridden;
the destination remains ES. Each completed macro retires once.

The physical fault contract is deliberately not an atomic element commit. Its
pre-access index/count effects, per-form order, and extra repeated-store fault
decrement are represented explicitly. The full physical string cohort and directed
fault cases constrain these unusual partial results; one universal end-of-element
commit rule would contradict the retained captures. Faulting attempted elements
are not confused with successful repetition boundaries.

At a nonfinal boundary, saved CS:IP comes from the first prefix and completed
SI/DI/CX survive cancellation. IRET refetch restores the remaining work; END is
reached normally only at completion. The reviewed lifecycle tests check exact
unmasked frames and resumed memory/port access counts. Input event arrival is
tested at active transfer and entry boundaries. These are executable checks of
the contract, not independent hardware proof of every event policy.

## Boundary 4 — SS/STI, TF, competing events and evidence adjudication

`rtl/spk286_events.sv:36-51,74-95,108-118` keeps fault/trap/NMI/INTR priority in
the shared event owner. SS inhibition sampled at the protected opcode persists
through nonfinal REP boundaries; prefixes do not prematurely consume it. Whole
instruction completion can then expose the owed TF boundary. STI captures its
inhibition separately and does not suppress NMI/TF by borrowing the SS rule.
The existing D-026 old-IF STI policy is retained. Candidate tests include complete
REP protection after MOV SS and distinguish STI with TF already set.

IBM's *Hardware Interface Technical Reference, Compatibility*, October 1990,
printed p.9 (PDF p.13), explicitly names the 80286 when saying repeated MOVS
single-steps after every iteration. The reviewer visually inspected retained p.13
and independently verified PDF SHA256
`cceffa6a769877fe20041700b7fe86933789d69d248cae6724dc6955e1211303`.
This is an explicit 286 statement in a section contrasting 386 behavior; it is
not a 386-only policy inferred to the 286.

**Nonzero REP TF disposition:** MOVS granularity is directly supported. Applying
the same boundary to the other string primitives is a reasonable, clearly marked
architectural inference from Intel 210498-005 section 3.7.2 and the common REP
iteration mechanism in Appendix B pp.B-92–B-93. Intel section 5.2 gives the common
event context and prefix-preserving restart behavior. Nonfinal restart at the
first prefix is consistent with resuming the documented remaining CX/SI/DI work;
the final boundary saves next IP. This inference is sufficient for the bounded
development contract when its inferential nature is preserved. It is not a claim
of a controlled physical TF capture for every primitive or chip revision. Faulting
elements remain separate under inherited `fault-tf`.

**Initial CX=0 disposition: unresolved new evidence, blocking complete Phase 7.**
Intel 210498-005 section 3.7.2 (printed 3-22) checks pending interrupts first;
Appendix B p.B-93 checks CX first. The earlier 210498-003 (1985) edition retains
the same difference (section 3.7.2 versus Appendix B printed B-90); edition age
does not supply a discriminating correction. The candidate explicitly suppresses
the REP entry boundary when CX=0 (`rtl/spk286_micro_executor.sv:90,135`) and accepts
eligible events at ordinary completion with next IP. Neither the IBM nonzero
iteration sentence nor agreement among models settles which competing-event
frame is physically produced. No automatic preference for prose or appendix is
justified by the reviewed evidence.

The independently checked no-element invariant is strong: the initial empty
branch precedes memory, accumulator and port acquisition. Existing directed tests
exercise zero count and no element accesses. That invariant holds under either
manual ordering and must remain distinct from event-frame adjudication. Needed
evidence is a controlled CX=0/1/3 event-phase sweep with eligibility/shadow state,
complete frames, handler/IRET observations and accepted marker writes. No such
capture was executed here. This issue cannot be added to D-026 by this review.

## Boundary 5 — irreversible I/O, READY, HOLD/LOCK and cancellation

INS acquires the port before destination validation and retains that accepted
read if the destination subsequently faults. OUTS reads source memory before
output; a source fault cannot create an IOW. The BIU captures type, width, port,
payload and owner on request acceptance. Odd words retain the physical second
half (including the recorded A16 carry from port FFFF) and only READY completes
each visible half. Operand response ownership prevents double consumption.

Cancellation clears semantic ownership while accepted visible transfers drain;
reset cannot undo previously accepted external effects. HOLD waits for current
word ownership; explicit LOCK retains ownership over the current repeated macro.
These are normalized transaction guarantees, not Ts/Tc/Ti cycle-accuracy claims.
The reviewer freshly ran both current Icarus string-I/O benches and the temporal
input experiment described in R2. The unmodified implementation passed all three.
R2 is a meaningful hole in retained verification, not a demonstrated wrong result
in the unmodified RTL.

## Boundary 6 — microcode authority and generic sequencing

The authoritative `.mc` programs express functional operations and genuine waits.
The generic microsequencer has no x86 opcode decoder. Branches validate their
target and valid bit, consume operation completion, and preserve macro entry.
The executor reuses common operand, arithmetic, FLAGS, register and bus services.
New source formats follow the preserved append order; frozen/active literal audits
and source maps remain wired. Fresh deterministic consistency check found no
stale generated output. No manually edited ROM or semantic NOP timing delay was
identified. Existing historical compiler/literal tests passed on the frozen
snapshot; these passes are not substitutes for the final fixed-input gate.

## Boundary 7 — physical oracle/accounting and complete gate

Inspected `tools/run_phase7_physical.py`, `tools/phase7_complete_reports.py`, scope,
completion and Phase 6 development/evidence helpers, Makefile and nested validation
scripts. The complete gate calls inherited Phase 6 executable checks (including
compiler/literal/lint/regression/dual simulators/mutations/synthesis), all required
physical files, strict disjoint report validation, all twelve Phase 7 mutation
families, arithmetic and port comparator negatives, input/disposition consistency,
then new evidence and exact-input independent review. `phase6-check` remains
architecturally strict. R1 breaks bounded increment gates but does not silently
remove a step from this different complete path.

Required counts remain 307 files, 1,387,000 discovered records and the three
original revocations, giving 1,386,997 required executions. The frozen historical
combined physical run attempted all files: 306 prepared, 1,381,997 executed and
passed, zero execution failures, E7 preparation failed and all 5,000 E7 records
were unexecuted **in that historical run**. There is no invented local exclusion.
Any later 4,999-record E7 diagnostic is a separate cohort and cannot replace
strict E7 admission or rewrite that historical statement.

E7 index 1100 / hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e`
has an incomplete IOW observation. `captured_io_cycles` requires a latched
address and captured matching completion/payload and rejects pending unfinished
I/O. It does not infer missing output from AX. The Verilator input responder
supplies its documented FF input independently; expected port records are used
only for comparison (`sim/verilator/singlestep.cpp:327-345,387-389`). V5 carries
both frame masks and port expectations without treating either as CPU stimulus.
Fresh parser/admission tests passed. No corrected raw capture or admissible
revocation was independently established in this review. Publication remains held.

The archived ordinary regression reports 254 ordinary tests, 88 compiler tests,
57 benches per simulator, lint and synthesis; retained mutation audits report
136 detections, plus 53 new detections in the successful retry. All related
`prototype-ordered-combined-*-result.json` log hashes were independently verified.
`audits-1` actually failed on a 60-second pristine timeout; `audits-2` separately
records statuses 0/0/0/0. The timeout is preserved as a failed run and is never
counted as a successful mutation detection. R2's additional surviving mutant
shows why those 189 retained detections do not imply exhaustive verification.

## Executed review checks and limitations

Fresh execution under WSL Ubuntu 24.04: Python 3.12.3, Icarus 12.0, GNU Make 4.3.
Commands, timestamps, statuses and log hashes are in the linked JSON records.

- 409-file source/hash check and historical result-log hash verification.
- Deterministic microcode consistency; 100 entries / 612 words.
- 17 existing focused Python tests: scalar/string I/O and arithmetic admission,
  combined batch representation, strict complete physical reports and completion.
- Two current Icarus string-I/O pristine benches and their stale-input mutations.
- 24 reviewer-only changing-input cases on pristine RTL, then intended mutant
  rejection with an explicit functional assertion (no timeout).
- Eight synthetic completion-helper shapes, with seven intended rejections.
- Missing arithmetic Make target dry-run reproduction.

This reviewer did not rerun the full physical corpus, full ordinary regression,
Verilator suite or synthesis. Existing exact-source records were inspected and
reused transparently. No physical processor was available or tested. No historical
pin timing, complete 80286, protected-mode, WAIT/ESC/NPX or consumer-machine support
is approved. No external message, issue or publication was sent.

The only inherited provisional questions remain `failed-iret-nmi`, `sti-old-if`
and `fault-tf`. They alone do not block Phase 7 development under D-026 and their
architectural evidence remains open. R1/R2, zero-count REP evidence, E7 admission,
final combined validation and actual integration/Git delivery are separate
obligations. Correcting R1/R2 can earn a changed-boundary review disposition;
it cannot by itself earn Phase 7 READY or architectural release approval.
