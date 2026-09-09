# Independent Phase 3 Architectural Review

Review date: 2026-09-08. Scope: completed Phase 3, before ALU/FLAGS work.

## 1. Provenance and review boundary

Audited delivery: `f3fe32bc550f4cf4d04000fafde26c0e2e728bfd` on
`codex/phase3-modrm-operands`. Review branch:
`codex/phase3-architectural-review`, created directly from that delivery.
The actual predecessor is `9657a1307f2e5bd27957745e4a611dc813d0f6ee`;
addressing is `66e3c5d`, integration is
`1714783a41652546f7247eb407b37d2a604335d7`.

Initial status was clean, including untracked files. Local/all remote branches,
remotes, recent history, tags, delivery diffs and live `git ls-remote` were
inspected. There were no tags; the live remote Phase 3 tip matched the audited
hash. No main/master change, merge, force push, history rewrite or cleanup was
performed. Existing ignored builds and the external corpus were preserved.
The GitHub Actions anonymous API returned 404 and `gh` was not available;
remote CI results were not observable. Local release evidence below is independent
of any claimed hosted CI result.

Production RTL, authoritative microcode, compiler and generated artifacts are
unchanged by this review. Changes strengthen verification and clarify contracts.
No Phase 4 instruction, temporary register, ALU, FLAGS generator, exception,
prefix, timing policy or downstream machine functionality was implemented.

## 2. Documents and agreement

Read AGENTS, README, SPEC, ENVIRONMENT, REALMODE_MVP, MICROCODE_FORMAT,
TIMING_MODEL, DECISIONS (including D-014 through D-017), PRE_PHASE3_AUDIT,
Phase 2.75/2.80/3 handoffs, ARCHITECTURE, STATE_INTERFACE, BUS_INTERFACE,
INSTRUCTION_MATRIX, VERIFICATION, SINGLESTEP_INTEGRATION, SOURCE_NOTES,
microcode/README and the build/CI/release scripts. Inspected every production
RTL module, generated control words/source mapping, compiler/auditor, corpus
parser/runner, C++ comparison and relevant directed/Python tests.

The broad specification's milestone numbers differ from incremental delivery
phases (D-007). The MVP's initial precedence note explicitly supersedes its older
machine-integration goals. The microcode specification permits a staged subset;
its future ALU/branch examples are not currently accepted syntax. No normative
requirement was rewritten to fit the implementation.

Two current descriptions needed precision: the operand service returns a word
to the executor, which owns TMP0; and final RAM equality cannot establish every
write event. ARCHITECTURE and SINGLESTEP_INTEGRATION now say so explicitly.
BUS_INTERFACE states the client hold/cancel preconditions already obeyed by the
integration. These clarify existing D-013/D-015/D-016/D-017, without changing
architectural decisions. AGENTS and DECISIONS therefore remain unchanged.

## 3. Untouched release-gate reproduction

Before edits, a previously absent directory was used from the authoritative
WSL checkout `/mnt/d/GitHub/SPK286`:

```bash
test ! -e build/phase3-review-baseline
mkdir -p build/phase3-review-baseline
SPK286_BUILD_DIR="$PWD/build/phase3-review-baseline" make phase3-check \
  > build/phase3-review-baseline/validation.log 2>&1
```

The process returned 0 with `PHASE3_VALIDATION_PASS`. Reproduced: 47 compiler/
audit tests, 97 total Python tests, all 16 directed benches in both simulators,
lint, reset/waveform/state smoke, MCL86 reference checks, full supported
SingleStep, Yosys, regression, 50,000-record parser audit, 20 rejected comparison
faults, four pristine probes, negative simulator propagation and traced replays.
All five generated hashes matched after two generations and the generated Git
diff was empty. No unexplained count discrepancy or inherited failure occurred.

## 4. ModR/M ownership

`spk286_modrm` alone extracts mode/REG/RM, register-direct and displacement
length. All 256 encodings are independently enumerated. Mode 01 requires one
byte, mode 10 two, mode 11 none, and mode 00 two only for RM=110.
`spk286_operand_decode` latches these outputs and performs the sole stream
disp8 sign extension and low/high disp16 assembly.

Searching production RTL found no 89/8B-specific ModR/M logic. The direct-address
predicate occurs in ModR/M for byte length and EA for a zero base/DS; these are
distinct responsibilities, not two competing decoders. Repeated slices inside
the ModR/M module are cosmetic. Python's length validator and test reference
tables intentionally interpret the external encoding independently of RTL.

## 5. EA and segment defaults

`spk286_effective_address` owns all eight base/index forms and direct disp16.
Its 16-bit sum wraps before translation; disp8 arrives sign-extended. BP+SI,
BP+DI and displaced BP use SS. Direct mode-00/RM-110 uses DS without BP.
There is no SIB, address-size prefix or opcode input. Segment storage separately
adds the selected cached base on a 24-bit path, preserving A20 carry.

Evidence includes 25,056 component checks, all addressing forms integrated
with distinct DS/SS and distinct BX/BP/SI/DI, and the new dependent stream in
section 19. A load into BX retains its previously resolved EA after BX changes.
Future ALU operand direction does not change this address contract.

## 6. Stable instruction context

Opcode, immediate destination and microcode entry latch on opcode acceptance.
ModR/M and displacement latch only on byte handshakes. RESOLVE subsequently
captures offset/segment on the same edge that completes DECODE_MODRM. The last
displacement byte is already stored before this edge; next queue data is not an
EA input. RESOLVE is required context storage, not timing padding.

After resolution the context service is disabled by the next micro-operation.
REG/RM selection, direction and entry do not depend on live stream signals.
Direction is the chosen microprogram, not a live opcode bit. Existing 1,280
context tests poison future bytes and change an EA register after resolution;
integrated tests cover refill, partial acquisition, pause and cancellation.
External setup writes require coordinated redirect when changing an executing
stream; they are not transparent edits to an active instruction's state.

## 7. Operand abstraction and temporary ownership

`spk286_operand` has independent `request_write` and `select_rm` inputs and a
caller-supplied word. REG always means the REG field; RM may name a register or
memory. The same register-state vector and indexed mux serve both identities.
Writeback has a separate enable/index/data interface into existing storage.
The module has no opcode, MOV direction, micro-PC or TMP0 dependency.

The new direct service bench reads RM memory, reads REG in the same context,
then writes a separately supplied word to RM and another word to REG. It also
checks all register selectors, request backpressure, held response and limits.
No new instruction or CPU temporary is needed for this API test.

The executor currently routes all reads to TMP0 and all writes from TMP0.
Adding temporary selection/storage and ALU result routing there is an expected
datapath/compiler extension. The operand service's word ports already permit
such values; replacing decode, address, register or memory service is unnecessary.
Operation identity/context must be held until completion or canceled before reuse.

## 8. BIU arbitration and physical ownership

All external address/data/valid/write/BHE/status outputs are driven by the single
BIU instance. Fetch remains an internal code client; no physical bypass exists.
Data acceptance snapshots address, direction and value. Accepted data wins at a
free physical boundary. A code cycle observed with READY low records code
ownership even if data is accepted on that same edge.

The BIU retains owner identity; the fetch client's registered metadata retains
code address and lane information until code_ready, including across redirects.
Only the selected client receives completion. Odd data retains ownership across
the pair because data_active remains set after the first cycle. Code resumes
while a data response is held, without consuming or changing that response.
New same-edge arbitration and continuous-READY tests, plus an ownership mutant,
exercise these boundaries independently of instruction results.

## 9. READY semantics

READY qualifies physical completion only when a bus cycle is valid. Waiting
code and data retain owner, address, direction, BHE/status and write data. The
operand pending bit prevents repeated logical acceptance while the micro-PC is
stalled. Read capture and write completion use retained responses; END follows
completed writeback. Pausing gates semantic acceptance, while physical work
may finish into the response slot.

Existing tests exercise 0..4 waits independently on both odd subcycles, aligned
words and code. The review adds continuous READY, coincident owner acquisition,
coincident cancellation/completion and explicit accepted-request/response counts.
A duplicate-request mutant is rejected. These prove the normalized synchronous
contract, not historical READY pin sampling or Ts/Tc/Ti timing.

## 10. Unaligned words and physical boundaries

Even words use A0=0/BHE_n=0 in one physical cycle. Odd words put the first
logical low byte on D15:8 at N and the high byte on D7:0 at N+1 with BHE_n=1.
Read assembly is `{second_low_lane, first_high_lane}`. Write data is snapshotted
before splitting. The executor/microcode sees one logical completion.

Tests poison inactive lanes, check surrounding bytes, count one/two physical
transfers and stall each independently. Added canceled read/write pairs cross
physical 0FFFFF to 100000 without A20 truncation. That is a BIU arithmetic/API
probe, not a claim of executing a word at segment offset FFFF. Legal EA wrapping
and the illegal whole-word boundary are tested separately.

## 11. Segment-limit FFFF

The precheck is a 17-bit `offset+1 <= limit`, before a request can be accepted.
FFFF cannot wrap to zero, and a rejected write issues neither byte. Blocked
state is sticky and stops retirement until reset/redirect. The new service
test adds FFFE acceptance and a short-limit rejection as port-level checks;
it does not add protected-mode segment loading. A truncated-arithmetic mutant
fails before any request is accepted.

Intel 210498-005, table 2-2/p. 2-19, Appendix B p. B-7 and MOV pp. B-73/B-74
were checked from the cached PDF, including freshly rendered pages. B-7 states
the second byte is at 10000, not zero; B-74 specifies interrupt 13. Pinned
hardware cases 89/520 and 8B/536 independently contain unprefixed `[DS:SI]`
with SI=FFFF and exception 13. They are diagnostic evidence only, absent from
RTL/tests' architectural logic. No exception delivery was added.

## 12. Prefetch coexistence

Git confirms `spk286_fetch` and the six-byte queue are unchanged from the Phase 3
base. Normal data access does not assert queue_flush. Fetch responses alone
produce queue bytes; data responses have no queue path. Fetch cursor movement
is tied to code completion, while IP movement is tied to consumed bytes.

Existing queue/fetch tests cover refill/consume ordering, capacity, held responses
and stale code. Both continuous MOV streams execute without reset/redirect
between instructions. The expanded MOV bench observes 1,559 populated-queue/data
coexistence cycles and 908 data wait cycles. These are actual exercised counters,
not exhaustive queue-state or hardware prefetch-timing coverage.

## 13. Redirect, reset and cancellation

Valid redirect suppresses semantic work and retirement on that edge, clears
instruction context and pending operand state, and discards the old BIU response.
Accepted logical words drain, including both halves of a store. Reset inhibits
bus_valid immediately and clears physical/pending/response state at the edge.
Already accepted external writes are not rolled back by either control.

Lifecycle checks cover partial ModR/M/displacement, first/second physical cycles,
held response, pause and malformed controls. Added READY/redirect coincidences
verify exactly two old plus two new read/write cycles and no stale CX commit.
Register-only cancellation at writeback suppresses that commit; at END it
preserves the earlier commit and suppresses retirement. The new stream retires
exactly once. No stale response is allowed to commit after cancel/reset.

This is coherent development cancellation, not precise exception serialization.
Later exception/interrupt control must precheck faults, retain instruction-start
state and serialize irreversible effects. The BIU's acceptance and retained
completion provide usable boundaries for that policy; its API need not be
replaced. This is non-blocking debt, not an implemented exception guarantee.

## 14. Microcode source, compiler and ROM

The only production programs are MOV_R16_IMM16, MOV_RM16_R16 and MOV_R16_RM16.
The latter two are DECODE_MODRM, read one operand, write the other, END. Format 2
adds five reusable operand operations, without bus lanes, EA tables or delays.
Format 1 independently retains words [1,2,3]. The active 11-word/four-bit ROM,
three entry symbols, invalid addresses 11..15 and all five generated artifacts
match their versioned contract.

The compiler rejects missing END, trailing work, missing/duplicate context,
undefined TMP0, unsupported operands/versions, invalid symbols and overflow.
The emitted-ROM auditor independently decodes the documented operation numbers
and round-trips through canonical DSL. It is intentionally a generated-template
reader, with complete byte-consistency checks as its prerequisite. It does not
prove arbitrary SystemVerilog semantics. Generation and both historical/current
fixtures pass; no manually maintained microcode or MOV-specific compiler control
was found. Additional temporaries will require explicit versioned syntax/encoding.

## 15. Generic microsequencer

`git diff 9657a13 f3fe32b -- rtl/spk286_microsequencer.sv` is empty, as are the
register storage, segment storage, fetch and queue diffs. The sequencer owns
start/entry/PC, active/fault, dependency hold, END and retirement. It contains
no opcode, operand direction, address or byte assembly. New semantics live in
the decoder, reusable executor/services and readable microcode, not a hidden
parallel hardwired MOV controller.

## 16. Retirement and IP

One successful instruction produces one registered END pulse. A memory write
must complete its entire logical operation first. Blocked words, canceled
instructions and reset do not retire; the pulse clears even if paused afterward.
Register, aligned/odd memory, READY, pause and cancellation checks cover this
contract. The C++ target stops at the first retirement, while continuous directed
tests independently check instruction count, per-retirement state and bus counts.

IP advances once for each accepted opcode/ModR/M/displacement/immediate byte,
not by fetch address or physical cycle count. It is the next instruction byte,
not a retained instruction-start IP. Writeback precedes END, so this stage does
not provide arbitrary mid-instruction rollback. That limitation is explicit and
compatible with the current phase; precise faults remain future work.

## 17. SingleStep honesty and exact accounting

Corpus: clean pinned `37c73caf53dcd22d3dd369ff09305d13d117a4fe`, version 1.1.0,
Harris N80C286-12 captures, external under `.cache/singlestep-80286`.

| Family | Discovered | Revoked | Prefix excluded | Exception excluded | Selected | Executed | Passed | Failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B8..BF | 40,000 | 0 | 0 | 0 | 40,000 | 40,000 | 40,000 | 0 |
| 89 | 5,000 | 0 | 1,016 | 29 | 3,955 | 3,955 | 3,955 | 0 |
| 8B | 5,000 | 0 | 1,031 | 29 | 3,940 | 3,940 | 3,940 | 0 |
| Total | 50,000 | 0 | 2,047 | 58 | 47,895 | 47,895 | 47,895 | 0 |

Full selection skips are zero. Revocation precedes prefix, exception and sample
selection, making the categories disjoint. The parser's raw 68 exceptions include
ten prefixed cases already excluded. All 50,000 identities/state/bytes and
680,905 cycles match the independent upstream parser. No comparison masks occur
in this pinned set; generic supplied masks remain supported and tested.

Preparation does not replace expected registers/memory based on test identity,
opcode, address or captured operand bytes. It overlays sparse final state and
applies the documented common final-IP-minus-one HLT boundary, validating exact
sequential length. MEMR requires supplied active bytes; unspecified CODE alone
may zero-fill. No expected operand feeds the CPU.

Real CLI selections for prefix/exception cases of both opcodes, by index and
hash, returned status 2 without simulator execution (eight probes). The normal
adversarial audit changes compared registers, actual instruction/operand bytes,
missing read data and expected RAM: 20 intended failures and four pristine passes.

## 18. Limits of previous claims

The original headline counts and architectural ownership claims are reproducible.
The handoff's unqualified "extra memory writes fail comparison" is too broad:
final map equality cannot detect same-value writes to existing addresses, repeated
writes, or transient changes restored before retirement. Directed RTL transaction
monitors cover duplicate/early/wrong-lane traffic independently. Full hardware
bus-event comparison remains deferred. The current integration document now
states this distinction; the historical handoff is preserved.

The delivery commit also changes the acquisition helper's docstring, besides
adding the handoff. It does not change acquisition or CPU behavior; calling the
delivery documentation-only is semantically reasonable. Test/check counters
must not be described as exhaustive state-space proofs. No cycle-accurate,
Quartus resource or precise-exception claim is supported by this release.

## 19. Adversarial additions and falsification

| Check | Added evidence |
| --- | --- |
| Logical operand API | 206 checks; independent REG/RM read/write, repeated context, arbitrary caller word, backpressure, limits, cancel |
| BIU | Same-edge code/data acceptance, continuous READY, cancel on either READY completion, A20-crossing odd read/write, held response and preaccept cancel; 2,419 total checks |
| Lifecycle | Six new coincident READY/redirect cases, four register writeback/END cancellations; 46 total cases, 2,440 checks |
| Continuous stream | Eight dependent MOVs, wrapped DS EA, updated BX/BP/SI, load into BX, signed SS EA, direct DS; 47,468 total MOV checks |
| Negative RTL audit | Four isolated compiled mutants rejected for intended assertions; two pristine benches pass |
| Real excluded selections | Eight index/hash invocations reject prefix/exception cases with status 2 |

`tools/audit_phase3_boundaries.py` never edits production sources. It substitutes
one copied RTL file in an ignored build, requires successful Icarus compilation,
then requires a specific failing assertion. Mutations remove owner retention,
drop same-edge cancel suppression, remove pending-request suppression and truncate
the width check. The cancel/READY mutation specifically exercises the newly
added coincidence case; it would evade the old cancellation-with-READY-low tests.
The audit records source hashes and verifies source bytes remain unchanged.

The review's first held-response assertion initially checked request readiness
while cancel was still high. RTL correctly inhibited admission; the test now
checks inhibition, then readiness after deassertion. This was a test error,
not a reason to change RTL. Two initial nested-shell probe invocations failed
before running their intended commands; direct WSL invocations/scripts resolved
quoting. WSL lacked Poppler, so the bundled PDFium renderer was used read-only
without installing tools. No failed architectural check was waived.

## 20. Synthesis and portability

Both simulators compile and execute the same production modules. Verilator
--Wall lint passes for top and components. Yosys performs 14 structural scopes
plus full generic synthesis/check: 6,223 mapped cells, including 733 sequential
cells, no remaining processes/memories or reported structural problems.
These reproduce Phase 3 and are not ALMs, block-RAM usage or Fmax.

Inspection found explicit 16/17/24-bit arithmetic, bounded indexes, combinational
defaults and single sequential owners. No inferred latch, multiple driver,
combinational loop, X-dependent functional choice or simulator-specific CPU
initialization was found. Invalid queue bytes are harmless behind the reset
count. The ROM uses a portable case statement; only unused public package
constants are locally exempted from UNUSEDPARAM. Quartus's existing Docker image
was observed, but implementation was not run without a concrete inference issue.
Physical Cyclone V timing/resource validation remains unclaimed.

## 21. Findings and severity

A = blocker before Phase 4; B = should fix before Phase 4;
C = documented non-blocking debt; D = cosmetic/no action.

| ID | Severity | Finding and disposition |
| --- | --- | --- |
| R-01 | B, resolved | Important API/coincident-edge properties lacked direct negative proof; focused tests and mandatory isolated-mutant audit added |
| R-02 | B, resolved | Unqualified extra-write comparison claim overstated final-state coverage; current documentation corrected, transaction tests retained/strengthened |
| R-03 | C | Precise exceptions/interrupt serialization and instruction-start context remain deferred; cancel cannot roll back writes |
| R-04 | C | Hardware bus-event/timing comparison, native pin sampling and HOLD/LOCK/INTA not implemented |
| R-05 | C | Executor/compiler currently expose one temporary and word operands; byte operations, extra temporaries and FLAGS are future explicit extensions |
| R-06 | C | Queue producer contract requires fill_count 1 or 2; current sole producer proves it, reserved 3 remains unsupported |
| R-07 | C | Physical FPGA synthesis/timing and arbitrary hidden-cache/Protected Mode behavior remain unvalidated |
| R-08 | D | Local duplicate bit slices, indexed architectural-state read mux, conservative refill and tiny combinational ROM need no refactor |

No category A finding or unresolved category B finding remains. No CPU defect,
corpus count/admission defect, expected-state patch, hidden MOV controller or
Phase 4 architectural dependency requiring replacement was demonstrated.

## 22. Fixes and verification changes

The review changes no production RTL or microcode. It adds the operand-service
bench, strengthens three existing benches, adds an isolated negative RTL audit,
registers the bench in both simulators, and includes the audit in the release
gate. Current interface/verification documentation now states ownership,
preconditions and comparison limits precisely. Normative specifications,
hardware expected values, AGENTS and DECISIONS remain unchanged.

## 23. Final reproducible validation

Verified implementation/verification commit:
`8326d951bd6a4bfe3393424fff26f06e46c0c119`
(`Strengthen Phase 3 operand and BIU boundary verification`). The working tree
was clean before and after the final gate. Its initial status and commit are
recorded in the build directory. This report is a subsequent documentation-only
commit; it does not change any executable source, test, script or generated file.

The focused changes first passed their individual dual-simulator benches and
lint, then the complete release gate in `build/phase3-review-focused`. The final
gate compiled afresh in another previously absent directory. Exact final commands,
from `/mnt/d/GitHub/SPK286` in Ubuntu-24.04 WSL:

```bash
test ! -e build/phase3-review-final
mkdir -p build/phase3-review-final
git status --porcelain > build/phase3-review-final/initial-status.txt
git rev-parse HEAD > build/phase3-review-final/commit.txt
env SPK286_BUILD_DIR=/mnt/d/GitHub/SPK286/build/phase3-review-final \
  make phase3-check > build/phase3-review-final/validation.log 2>&1
git diff --exit-code -- microcode/generated
git status --porcelain
```

Exit status was 0, ending with `PHASE3_VALIDATION_PASS`. Both Git checks were
empty. The authoritative [release script](../scripts/validate_phase3.sh) checks
the pinned clean corpus, regenerates twice and compares SHA-256 for all five
generated files. It then executes these checks in order, with the build variable
exported to every child:

```bash
make microcode-check microcode-test microcode-audit
make mcl86-check
python3 -m unittest discover -s tests -p 'test_*.py' -v
make lint
bash scripts/test_units.sh both
make waveform iverilog state-smoke
make singlestep-smoke
make singlestep-operands singlestep-mov
make synth-check
make regression
make singlestep-audit
make phase3-boundary-audit
make verify-failure data-smoke
python3 -m tools.run_singlestep --opcode 89 --index 0 --trace "$SPK286_BUILD_DIR/traces/mov-89-0.vcd"
python3 -m tools.run_singlestep --opcode 8B --index 3 --trace "$SPK286_BUILD_DIR/traces/mov-8B-3.vcd"
make microcode-check
git diff --exit-code -- microcode/generated
```

| Final check | Observed result |
| --- | --- |
| Deterministic generation and emitted-ROM audit | PASS; all five hashes unchanged |
| Compiler/auditor Python subset | 47 tests PASS |
| All Python tests, including that subset | 97 tests PASS |
| Verilator lint | PASS |
| Directed RTL | 17 benches PASS in each simulator; baseline had 16 |
| Reset, waveform, initialized state and SingleStep smoke | PASS |
| Full hardware-derived supported set | 47,895 / 47,895 PASS; 0 FAIL; section 17 accounting unchanged |
| MCL86 inherited reconstruction | Original 4,096 / 4,096 identical; both 4,096-word round-trips identical |
| Yosys structural checks and mapped synthesis | PASS; 6,223 cells, 733 sequential cells |
| Full regression | PASS |
| Independent upstream corpus cross-check | 50,000 records, 680,905 cycles, all equal |
| Comparison fault injection | 20 intended failures; four pristine executions PASS |
| New operand/BIU RTL mutation audit | Four intended failures; two pristine benches PASS; source bytes unchanged |
| Deliberately incorrect reset expectation | Both simulators correctly return failure |
| Traced 89/0 and 8B/3 replays | Both PASS |
| Generated Git diff and working-tree status | Empty |

The deliberate negative probes are expected failures, separately reported from
the zero-failure supported execution result. The new RTL bench accounts for the
increase from 16 to 17; compiler, Python and corpus counts did not change.

Local, ignored evidence is retained under `build/phase3-review-baseline`,
`build/phase3-review-focused` and `build/phase3-review-final`. Final evidence includes
`validation.log`, `generated.sha256`, `singlestep/full-reports/*.json`,
`reports/yosys_mapped.log`, `phase3-boundary-audit/*/{build,run}.log` and the two
VCD replays. Full reports are copied before smoke/explicit selections overwrite
the ordinary per-opcode report directory. Supplemental excluded-selection logs
and rendered Intel pages are in the focused directory.

Observed tools: Python 3.12.3, Verilator 5.020, Icarus 12.0, Yosys 0.33,
GNU Make 4.3 and g++ 13.3.0. This is portable simulation/generic synthesis
evidence, not a Quartus implementation or hosted-CI result.

## 24. Phase 4 readiness conclusion

The operand architecture is reusable: REG/RM identity, access direction and
caller word are independent; decoding, EA/segment choice, register commit,
logical memory completion, physical arbitration and queue storage have separate
owners. A future READ_RM, READ_REG, ALU result and WRITE_RM sequence requires
extra executor temporaries/operations and explicit FLAGS routing, not replacement
of these mechanisms. The inverse direction uses the same interfaces.

The normalized BIU/prefetch/READY contract and current successful-instruction
retirement boundary withstand the reviewed adversarial tests. Later precise
exceptions must add serialization and saved instruction-start state above these
primitives. This qualification does not block ALU/FLAGS development.

Phase 4 may begin without redesigning Phase 3. Phase 4 was not started here.

Primary evidence: Intel [80286/80287 Programmer's Reference Manual, 210498-005](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf),
printed 2-19, B-7, B-73/B-74 (PDF pages 45, 215, 281/282), cached PDF SHA-256
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`;
and the pinned [SingleStepTests/80286 methodology](https://github.com/SingleStepTests/80286/blob/37c73caf53dcd22d3dd369ff09305d13d117a4fe/README.md).
Reference CPU implementations did not override Intel/hardware evidence and no
external CPU code was reused.

PHASE 3 ARCHITECTURAL REVIEW READY — SPK286's ModR/M, operand and BIU foundation is independently validated and ready for Phase 4.
