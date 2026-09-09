# Pre-Phase 3 Independent Retrospective Audit

Date: 2026-09-07. Branch: `codex/pre-phase3-audit`.

## 1. Scope and status

This independent review covers the actual Phase 0-2.75 production RTL,
compiler/generated microcode, adapters, testbenches, scripts and documentation.
Handoffs were checked against source, primary references and fresh executions.
The foundation is ready to begin Phase 3 within the constraints below. No open
category A or B finding remains after the supplied Phase 2.75 development and
the verified audit fixes.

No Phase 3 feature was implemented: no ModR/M, EA, memory operands, ISA expansion,
timing profiles or downstream machine integration. No production RTL or generated
control-store change was necessary. Real fixes concern verification and a legacy
scope clarification.

The earlier blocked report is preserved in `4b55a31`. Phase 2.75 was missing then;
the subsequently supplied development resolves that prerequisite. This report
supersedes the earlier incomplete review.

## 2. Repository, phase commits and documentation

Repository: `https://github.com/spark2k06/SPK286.git`.

The resumed checkout was clean on `codex/phase2.75-microcode-foundation` at
`b7eaa46bc4cb9a2fc51f8a63f0f5b3e6f00c60df`, identical to its remote branch.
This is the audited baseline. There was one worktree and no tags. Existing
ignored corpus/build/cache files were preserved.

| Phase | Implementation milestone | Completion/handoff |
| --- | --- | --- |
| 0 | `a1a24ec7afc8181ba7a93cc69d52763823a1426b` | `c021070ade633dea9a4b11e760e1eb9743090588` |
| 1 | State/segments/fetch through `f8676c1b6c4d6961c0a62a65a83c70387e22ac3f` | `5fb70f10bb973c831cf817bbecdebc37f2fcbbe5` |
| 2 | `b7023c763f36f4a6deda0d3eca689b86fc8a62ff` | `829489dfb9b54054114dbd77af2875213cbae6ee` |
| 2.5 | `caa53b4f9fd37c083ab39d193b1750f0190324e5` | `85ab90e8bf8be3b5d1a97ce0c31ba5e4a9e7facf` |
| 2.75 | `10c30f8` compiler/ROM; `ad7b71a` sequencer/execution | `b7eaa46bc4cb9a2fc51f8a63f0f5b3e6f00c60df` |

Related commits: `b7c1622` timing separation, `ac3b3cd` CPU boundary, `4b55a31`
initial blocked audit. Phase 2.75 descends from that audit. After inspecting
status, branches, remotes, recent/all-branch history, tags and worktrees, the
existing audit branch was advanced without a merge or history rewrite:

```text
git merge-base --is-ancestor codex/pre-phase3-audit codex/phase2.75-microcode-foundation
git fetch . codex/phase2.75-microcode-foundation:codex/pre-phase3-audit
git switch codex/pre-phase3-audit
```

Read completely: AGENTS, README, SPEC, ENVIRONMENT, REALMODE_MVP,
MICROCODE_FORMAT, TIMING_MODEL, DECISIONS, Phase 0/1/2/2.5/2.75 handoffs,
SINGLESTEP_INTEGRATION, microcode/README, ARCHITECTURE, STATE_INTERFACE,
BUS_INTERFACE, VERIFICATION, INSTRUCTION_MATRIX, SOURCE_NOTES and relevant
environment/progress/build/CI records. The actual filename is
`SPK286_REALMODE_MVP.md`.

The broad specification's milestones are not the incremental phase numbers
(D-007). Comprehensive microcode examples are not all implemented syntax; the
initial subset is explicitly permitted. Older MVP machine-integration goals
conflicted with the later CPU boundary: a precedence note now identifies them
as downstream validation without redefining architectural behavior.

## 3. Baseline and final validation

The untouched baseline used the previously absent `build/audit275-baseline/`.
Final validation uses the separately created `build/audit275-final/`. No existing
build output was deleted or reused for either initial regression build. The
external corpus remains clean and pinned at
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`, version 1.1.0, Harris N80C286-12
captures. No vectors or upstream reference code were modified or copied into Git.

Commands ran through `wsl -e bash -lc`, in `/mnt/d/GitHub/SPK286`, with
`set -euo pipefail`. Exact baseline sequence:

```bash
test ! -e build/audit275-baseline
mkdir -p build/audit275-baseline
export SPK286_BUILD_DIR="$PWD/build/audit275-baseline"
make microcode > "$SPK286_BUILD_DIR/generation.log" 2>&1
sha256sum microcode/generated/* > "$SPK286_BUILD_DIR/generated-first.sha256"
make microcode >> "$SPK286_BUILD_DIR/generation.log" 2>&1
sha256sum -c "$SPK286_BUILD_DIR/generated-first.sha256" >> "$SPK286_BUILD_DIR/generation.log"
git diff --exit-code -- microcode/generated >> "$SPK286_BUILD_DIR/generation.log"
make microcode-check microcode-test > "$SPK286_BUILD_DIR/compiler.log" 2>&1
make regression > "$SPK286_BUILD_DIR/regression.log" 2>&1
make singlestep-mov > "$SPK286_BUILD_DIR/singlestep-full.log" 2>&1
make verify-failure waveform data-smoke > "$SPK286_BUILD_DIR/extra.log" 2>&1
```

Exact final sequence:

```bash
test ! -e build/audit275-final
mkdir -p build/audit275-final
export SPK286_BUILD_DIR="$PWD/build/audit275-final"
make microcode > "$SPK286_BUILD_DIR/generation.log" 2>&1
sha256sum microcode/generated/* > "$SPK286_BUILD_DIR/generated-first.sha256"
make microcode >> "$SPK286_BUILD_DIR/generation.log" 2>&1
sha256sum -c "$SPK286_BUILD_DIR/generated-first.sha256" >> "$SPK286_BUILD_DIR/generation.log" 2>&1
git diff --exit-code -- microcode/generated >> "$SPK286_BUILD_DIR/generation.log" 2>&1
make microcode-check microcode-test > "$SPK286_BUILD_DIR/compiler.log" 2>&1
/usr/bin/time -p make regression > "$SPK286_BUILD_DIR/regression.log" 2>&1
/usr/bin/time -p make singlestep-mov > "$SPK286_BUILD_DIR/singlestep-full.log" 2>&1
/usr/bin/time -p make singlestep-audit > "$SPK286_BUILD_DIR/corpus-audit.log" 2>&1
make verify-failure waveform data-smoke > "$SPK286_BUILD_DIR/extra.log" 2>&1
```

Focused validation also ran `python3 -m unittest discover -s tests -p
"test_singlestep*.py" -v` (19 final tests), the full runner immediately after
the admission fixes, Windows generation to a separate output directory, and
`python3 -m tools.run_singlestep --opcode B8 --opcode B8` (expected status 2).
Regression includes lint, both simulators, all directed
benches, Python tests, state vectors, available-corpus smoke, and Yosys. The full
SingleStep corpus is a separate explicit gate, not the 80-case smoke sample.

| Check | Untouched baseline | Final tree |
| --- | --- | --- |
| Regeneration, hashes, consistency | Five artifacts identical | Five artifacts identical |
| Compiler tests | 31/31 PASS | 31/31 PASS |
| All Python tests | 42/42 PASS | 54/54 PASS |
| Verilator --Wall lint, top/components | PASS | PASS |
| Directed RTL benches | 10/10 in each simulator | 10/10 in each simulator |
| Reset smoke | Both simulators, FFFFF0 | Both simulators, FFFFF0 |
| State adapter | 1 + 3 initialization/fetch cases | 1 + 3 PASS, no instruction execution |
| Yosys | Nine structural scopes/full generic synthesis PASS | Same scopes and synthesis PASS, zero problems |
| Full inherited regression | PASS | PASS, 123.48 s wall time |
| SingleStep smoke | 80 executed, 80 PASS, 0 FAIL | 80 executed, 80 PASS, 0 FAIL |
| Full SingleStep | 40,000 executed, 40,000 PASS, 0 FAIL | 40,000 executed, 40,000 PASS, 0 FAIL |
| Negative reset, VCD and loader smoke | PASS | PASS, loader explicitly reports execution deferred |
| Independent corpus/fault audit | Supplemental run PASS | 40,000 parser matches; 17 rejected faults; two pristine PASS |

Baseline directed counters, equal in both simulators: registers 200 plus reset/
commit assertions; segments 262,202; fetch 26; core 7; queue 19; sequencer 37;
ROM 4; decoder 256; inherited execution 16 bus transactions, plus uncounted
assertions. Final directed counters match the baseline. The microcode execution
bench covers 48 MOV vectors, eight consecutive
MOVs and four cancellation/reset/resume boundaries: 5,380 checks and 375 observed
underfill cycles. These are directed counters, not exhaustive coverage or corpus
execution counts.

Baseline full accounting: 40,000 discovered/selected, zero revoked, zero skipped,
40,000 executed/passed, zero failed. Each of B8/B9/BA/BB/BC/BD/BE/BF contributes
5,000 cases and 50,000 implementation cycles. Runtime: 4.979 s, 8,033.5 tests/s.
An intermediate full run after the fixes passed 40,000 in 5.276 s, 7,580.9 tests/s.
Runner times include parsing/batching/execution, exclude build, and vary with
host load; they are not historical CPU rates. The final full runner took 5.312 s,
7,529.8 tests/s (5.73 s wall time for its Make target); the independent corpus/
fault audit took 6.61 s including its build check.

Final full totals are exactly 40,000 discovered, 40,000 selected, zero revoked,
zero selection-skipped, 40,000 executed, 40,000 passed, zero failed: 5,000/5,000
for each opcode. The separate smoke selected/executed 80 and reported 39,920
selection-skipped, zero revoked and zero failed. Neither audit fault probes nor
state-initialization vectors are included in these 40,000 corpus executions.

Tools: Python 3.12.3, GNU Make 4.3, Verilator 5.020, Icarus 12.0, G++ 13.3.0,
Yosys 0.33, WSL kernel 6.6.87.2-microsoft-standard-WSL2. Baseline positive-path
logs showed no lint/RTL/synthesis warnings or simulator disagreement. Intentional
FAIL/FATAL output is isolated to negative checks. Final positive-path logs also
contain no lint/RTL/C++/synthesis warnings or simulator discrepancies. Windows
Git emitted line-ending conversion notices while inspecting the working tree;
they are not simulation warnings or generated-byte differences. The final command
sequence returned 0 and printed `FINAL_VALIDATION PASS`. Detailed ignored logs,
hashes, reports, batches and traces remain under the two audit build directories.

## 4. Phase 0: infrastructure

Shell entry points use `set -euo pipefail`; failed Verilator builds propagate
status, as do Yosys pipelines. Both simulators use the same ordered RTL manifest,
with generated package before ROM/consumers. No simulator-only functional path
was found. Python tools use the standard library.

Every RTL entry point checks generated bytes, not just timestamps. An independent
temporary comment added to authoritative `.mc` made all eight targets
`microcode-check`, `lint`, `verilator`, `iverilog`, `unit`, `synth-check`, `test`,
and `regression` exit 2 with `MICROCODE CHECK FAIL`. Generated files stayed
unchanged; the source was restored byte-for-byte in `finally`. Command:
`python3 build/audit275-baseline/probe_build.py`; evidence: `build-audit.log`
and `stale-*.log` there. Normal consistency passed again after restoration.

Negative reset tests prove failure propagation through both simulators. VCD
generation works. Fresh build directories rule out inherited executables. The
external corpus is optional in normal regression/CI; missing data explicitly
prints SKIP. Such a regression alone does not establish SingleStep coverage.
Both audit regressions had the complete supported corpus available.

## 5. Phase 1: architectural state and segments

Independent word GPRs and AL/CL/DL/BL/AH/CH/DH/BH selection are correct. FLAGS
storage fixes reserved bits and masks updates; privilege-specific instruction
rules are future execution behavior. Zeroed reset GPRs are deterministic project
policy, not a claim that Intel guarantees their reset values.

Visible segment selectors and hidden 24-bit base/limit/access state are separate.
CS F000, hidden base FF0000, IP FFF0, FLAGS 0002 and limits FFFF match Intel's
reset table. Ordinary CS reload, even to the same selector, replaces its reset
base. FFFF:FFFF translates to 10FFEF, with no 20-bit truncation or motherboard
A20 gate. Access storage 93 is the documented real-mode cache representation;
protected-mode loading/checks are not implemented.

Architectural IP changes on byte consumption; the distinct 17-bit prefetch
cursor advances on fetch. Its extra bit prevents silent wrap beyond the 64 KiB
fetch limit. `fetch_blocked` is a current stop, not an implemented exception.
Near redirect retains cached CS; coordinated CS/IP redirect replaces it. Invalid
setup transactions are rejected atomically. Debug outputs observe actual state.

## 6. Phase 2: six-byte prefetch and old execution removal

The queue contains six byte elements with pointers wrapping at five. Ordering,
little-endian insertion, consumption, simultaneous refill, underfill, flush and
reset are exercised in both simulators. Refill admission conservatively excludes
same-cycle consume credit; this can reduce throughput but cannot reorder bytes.
Unreset storage is harmless while reset-cleared count marks it invalid.

The sole producer returns one or two bytes; READY and response backpressure hold
them until acceptance. Redirect flush suppresses consumption and stale insertion.
A response held during execution pause is accepted once after resume. There is
no instruction recognizer or larger cache in the queue.

Old `FRONTEND_*` states and hardwired MOV writeback are absent from production
RTL. Inspection of the write mux confirms microcode is the only execution path.
External setup/commit ports are deliberate composition interfaces, not another
MOV decoder. Inherited execution tests run through the new production path.

## 7. Phase 2.5: independent SingleStep audit

The reader, selection, serializer and C++ driver were reviewed end to end.
The pinned upstream parser independently decoded all eight compressed files.
Every index, name, byte stream, initial/final field, hash, exception and decoded
cycle record matched: **40,000 cases, 40,000 globally unique hashes, 519,806 cycle
records**. Header/parser/upstream counts each equal 5,000 per file. The supported
set has zero revocations, prefixes, exceptions or comparison masks. Cycle-parser
agreement is not RTL cycle-accuracy evidence.

Each execution constructs a fresh CPU, resets it, initializes actual architectural
state through commit ports, reloads real-mode caches and gives it separate sparse
memory. The driver stops at target retirement or a bounded failure, reads actual
state, and compares all 14 architectural values with supplied masks. Final RAM
overlays initial RAM; the whole resulting map is compared, including unintended
writes. No expected-state substitution or test-address/index/byte recognition was
found. Suppression after 20 failure diagnostics does not suppress counted failures
or remaining executions.

Upstream runs HLT after the target, then uses NMI/STOREALL and the saved interrupt
frame to obtain final state. Its README explicitly defines IP after HLT. SPK286
compares at END, subtracts the one terminating byte, and validates the sequential
target end. This documented boundary adaptation is common to every destination.
No fake HLT/NMI execution exists. Future control flow must explicitly extend the
sequential validator, not introduce opcode-specific expected-value corrections.

The old 40,000 result was reproducible, but adversarial inputs exposed verification
gaps: an `executed=0` summary for one selected case was accepted, as were certain
inconsistent totals/status, duplicate summaries/identities, malformed MOO metadata,
and unsupported execution state. Exception metadata, unsupported lengths,
declared-byte/RAM discrepancies and unrepresentable initial FLAGS lacked strict
admission. The initial negative run recorded 17 failing assertions/subcases across
11 test methods before fixes.

Strict admission/accounting now rejects those inputs. Prefix combinations,
exceptions and unsupported state are errors, never passes. Synthetic revocation
tests prove skipped/revoked cases are disjoint from execution. Invariants are:

```text
discovered = revoked + selection_skipped + selected
selected = executed = passed + failed
exactly one simulator summary
exit status 0 iff no failures; 1 iff compared executions failed
```

Actual-executable probes change one compared expectation bit in each of the 14
registers, one RAM expectation, one actual immediate byte and one actual opcode.
All **17 fail with status 1 and the intended reason**. Two surrounding pristine
executions pass. Faults remain only in separate ignored batches, never the corpus,
ordinary expectation preparation or RTL. `make singlestep-audit` preserves this
repeatable proof and the independent parser comparison.

## 8. Phase 2.75: compiler/source-to-ROM pipeline

`microcode/source/data_move.mc` is authoritative. Explicit Location/Statement/
Label/Block and Program/MicroOp IR preserves operands, source and assigned address.
Sorted paths and source order make entry allocation deterministic. Scoped labels
name the following operation for debugging; executable branches are deferred.

The 31 compiler tests cover malformed syntax/operations, invalid operands,
duplicates, missing END, unreachable work, TMP0 before definition, dangling/
unresolved symbols, format mismatch, ROM/address overflow, missing/stale outputs
and diagnostics. Expected CLI errors carry file/line/entry, return nonzero and
avoid raw Python tracebacks. Branch, NOP and timing syntax is rejected.

Two official generations, consistency/Git checks, independent hash seeds 1/1729,
and Windows versus WSL Python reproduced all five outputs. Source hashes detect
even comment changes. Identical outputs retain modification times. No generated
artifact was hand-edited.

The complete case ROM has three two-bit words, one entry and invalid-address
signaling. Existing addressed IR plus `encode()` makes deterministic HEX export
straightforward later; no ROM redesign is justified now. Listing and JSON maps
retain source identity without synthesizing source text.

## 9. Phase 2.75: reusable microsequencer

The sequencer owns active/entry/PC, start admission, advancement, dependency hold,
END and invalid-ROM/address faults. It has no x86 opcode, immediate assembly,
register encoding, queue storage or physical bus semantics. Its isolated bench
uses nonzero entries independently of MOV.

Reset/cancel clears PC, entry, active, retire and fault. Busy start is ignored.
Unresolved operations hold PC; completion resumes once; pause suppresses operation
validity. END can wait for permission and produces one retire, clears active and
keeps the last PC observable. Retire clears next edge even while paused. Invalid
entry/ROM/fallthrough faults instead of wrapping or retiring. No speculative
branch/call implementation was added.

## 10. Decoder/microcode contract

All 256 opcodes were tested: exactly B8..BF are supported, destination is the low
three bits, and all share `MC_ENTRY_MOV_R16_IMM16`. Form identity is implicit in
that shared entry for this subset; eight duplicate programs are unnecessary.
Opcode/destination latch on start and queue consumption. Later changing queue
data cannot replace the active destination. TMP0/partial-immediate state clears
at start/reset/cancel, survives stalls and is defined before use. Future operand
descriptors can extend this context without invading sequencer semantics.

## 11. Prefetch/microcode contract

FETCH_IMM16 accepts low then high byte; only the second handshake completes it.
Empty queue stalls PC without consuming or inventing bytes. MOVE subsequently
writes the assembled word once; END is independent of refill and bus idleness.
Prefetch can overlap execution. READY gaps, alignment, partial immediates,
pauses, reset/redirect at every operation boundary and consecutive instructions
are tested independently of the corpus's always-ready memory model.

The audit's pristine VCD holds PC 0 across queue underfill, then reaches PCs 1/2
and one retire edge. At retirement it has three queued bytes and a fetch cursor
ahead of architectural IP: queue fullness and cursor equality are not retirement
conditions. `python3 -m tools.microcode.compile_microcode --pc 1` maps the observed
PC to `data_move.mc:7: instruction MOV_R16_IMM16: TMP0 -> DST`, matching listing
and JSON. Evidence: `build/audit275-baseline/trace-audit.log` and pristine VCD.

## 12. Retirement semantics

END marks successful completion. Isolated and integrated tests establish exactly
one retire, none during reset/cancel, no duplicate after stalls, and next decode
under new context. Unsupported bytes remain unconsumed and do not retire as MOV.
No arbitrary delay, full queue or idle bus is required.

This is not yet precise exception recovery. IP advances during byte acquisition;
MOVE commits one edge before END. A redirect at END cancels retire but does not
undo that prior write, as the bench explicitly verifies. Future faults require
instruction-start context and access/fault ordering before irreversible effects;
interrupts must observe the architectural boundary. The cancel port is not an
instruction rollback mechanism.

## 13. BIU, CPU boundary and conceptual Phase 3 readiness

The minimal fetch module combines fetch bookkeeping and the current physical
transaction driver. It owns one active transaction and one held response with
snapshotted address/lanes/offset/count. READY keeps active bus state stable.
Redirect drains and discards an old transaction, including coincident READY and
repeated redirects; stale bytes do not enter the new stream.

This is normalized CODE/passive transaction behavior, not complete native
Ts/Tc/Ti. LOCK/HLDA are inactive; HOLD/interrupt/INTA behavior remains deferred.
The handoff correctly qualifies this limit. No PC/AT or MiSTer logic was found.

No blocker prevents logical operand services: decoder context can describe
operands, EA can use GPR/segment state, and executor operations can wait for
logical reads/writes. A register or a two-cycle unaligned memory service need
not alter generic PC/END sequencing. Before adding another bus client, Phase 3
must establish explicit arbitration, ownership and completion routing. Data must
never move the fetch cursor or enter the instruction queue. This extension is
necessary Phase 3 work, not already implemented functionality.

## 14. Synthesis/portability

Both simulators accept the same RTL. Combinational defaults, explicit widths,
synchronous state/validity reset and single state owners avoid latches, multiple
drivers or simulator-dependent functional behavior. The generated ROM is a case
statement, not a simulator-dependent array initializer or runtime file load.
Yosys accepts package, ROM and hierarchy. Baseline and final generic mapping: 4,707 cells,
including 607 flip-flop cells, no memories/processes remaining. These are not
FPGA ALM counts or Fmax.

Only unused public package parameter warnings are locally suppressed (D-012);
functional warnings remain fatal. A three-word ROM maps to logic. No unresolved
concrete inference problem required Quartus; Quartus and physical Cyclone V
validation were not run. No FPGA timing closure or block-RAM inference is claimed.

## 15. Findings, severity and fixes

A = blocker before Phase 3; B = should fix before Phase 3;
C = safe documented debt; D = cosmetic/no action.

| ID | Severity | Evidence/disposition |
| --- | --- | --- |
| P-01 | A, resolved externally | Previously missing Phase 2.75 supplied at `b7eaa46` and independently validated |
| V-01 | B, fixed | Simulator summaries/duplicate identities could invalidate totals; enforce unique selection, exact execution counts, one summary and matching status |
| V-02 | B, fixed | MOO metadata/duplicate chunks and unsupported state could be admitted; validate version/CPU/counts and execution stream/state/RAM consistency |
| D-01 | B, fixed | Legacy MVP could reintroduce machine scope; clarify precedence of later CPU-only boundary |
| C-01 | C | Fetch-only normalized bus; data arbitration/native protocol remain staged extensions |
| C-02 | C | Precise fault recovery, interrupt entry and saved instruction-start context deferred |
| C-03 | C | Three-operation compiler/executor subset; branches, operand fields and HEX export deferred |
| C-04 | C | Historical timing profiles and physical FPGA measurements unvalidated |
| C-05 | C | Supported corpus has no prefixes/exceptions/wait states/IF-TF coverage; absent sparse memory reads return zero |
| C-06 | C | Queue fill_count must be 1 or 2; reserved 3 is not rejected and would corrupt count if supplied |
| D-02 | D | Conservative refill credit, unreset invalid storage and minimal ROM size need no style refactor |

No current queue producer can issue 3: fetch derives 1/2, gated by validity.
C-06 is a bounded internal precondition, not a present CPU failure. Any future
queue producer must preserve it or explicitly harden/test admission. Searches
found no unexplained TODO/FIXME/HACK, test-address/index exceptions, production
Verilator-only semantics, old hardwired MOV or duplicate microcode truth.

Changes harden `tools/singlestep.py` and `tools/run_singlestep.py`, add adversarial
tests and the opt-in audit tool/Make target, and update integration/verification
documentation. Two synthetic fixtures now supply the instruction bytes they
already declared; no expected register/IP/FLAGS value was changed. Focused tests
failed before fixes and passed afterward; the complete supported corpus still
passes. No architectural decision or missing reusable rule required DECISIONS
or AGENTS changes.

## 16. Constraints Phase 3 must respect

1. Put ModR/M, operand descriptors, 16-bit EA and DS/SS defaults in decode/EA/
   operand services. BP-based defaults must follow Intel's SS rules. Keep x86
   semantics out of the generic sequencer.
2. Converge register/memory operands on logical completion. Extend compiler/
   executor fields coherently while preserving authoritative `.mc`, deterministic
   generation, versioning and source maps.
3. Establish CPU-owned prefetch/data arbitration and held completions before
   memory operands. Complete an unaligned logical word only after all required
   physical cycles. READY must not duplicate side effects or advance PC early.
4. Keep fetch redirect/draining independent of data completion. Check access
   bounds/faults before irreversible writes; retain instruction-start context
   when introducing faults. END remains an architectural instruction boundary.
5. Coordinate future timing permission with operation acceptance/completion.
   Merely holding PC while repeatedly asserting a write request is unsafe. Do
   not pad microcode with meaningless NOPs to match historical cycle counts.
6. Explicitly extend SingleStep admission, memory policy and retirement adaptation
   for each new form. Keep exclusions visible and counts consistent; run complete
   relevant hardware families plus independent bus/stall tests.
7. Keep PC/AT peripherals, BIOS packaging, A20 motherboard logic and MiSTer
   machine integration in the downstream consumer project.

## 17. Primary evidence and final disposition

Directly consulted evidence:

- Intel [80286 Hardware Reference Manual, 210760-002](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf),
  printed 3-65/3-67 (PDF 115/117), reset and Table 3-6.
- Intel [80286 and 80287 Programmer's Reference Manual, 210498-005](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf),
  B-73 (PDF 281), B8+ MOV and unaffected FLAGS; C-3 (PDF 329), reset base,
  physical address formation and external address-wrap responsibility. Relevant
  pages were rendered and visually inspected with table/timing qualifications.
- Pinned [SingleStepTests/80286 README](https://github.com/SingleStepTests/80286/blob/37c73caf53dcd22d3dd369ff09305d13d117a4fe/README.md)
  and `tools/moo2json.py`: hardware provenance, HLT/NMI/STOREALL, final IP,
  prefix policy, sparse state and cycle layout.

Reference cores were secondary evidence, not imported or allowed to override
Intel semantics. No disputed hardware expected value required alteration.
The handoff's 40,000/40,000 and compiler/sequencer claims were reproduced, but
green output alone did not establish robust admission/count integrity. V-01/V-02
were real gaps and now have negative proof. The final tree passed all required
checks. Phase 3 may begin while respecting section 16 and retaining the documented
non-blocking debt; Phase 3 itself has not begun in this audit.

## 18. Audit revisions

The verified tooling/test/integration changes are committed as
`1b808232fb2d55d61fc7ab011fb1b418bb515fbc`,
`Harden SingleStep corpus admission and execution accounting`.
The following documentation commit contains this final report and the legacy
MVP scope note; it is the final audit repository revision. Its exact ID is
reported in the delivery message and can be recovered with
`git log -1 --format='%H %s' -- docs/PRE_PHASE3_AUDIT.md`.
Only documentation changed after the final execution/synthesis run. No merge,
history rewrite, branch/tag deletion, destructive cleanup or main/master push
was performed.
