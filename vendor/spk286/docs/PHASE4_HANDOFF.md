# Phase 4 Handoff - Reusable Word ALU and Architectural FLAGS

## Objective and provenance

Phase 4 adds one reusable 16-bit ALU, instruction-specific architectural FLAGS
commit, executor temporaries and result routing, exercised by eight binary
instruction families. It builds directly on the independently reviewed Phase 3
operand and bus architecture. Phase 5 has not been started.

- Branch: `codex/phase4-alu-flags`.
- Exact reviewed base: `e040229ad4e363a833f9dc74b414cdb2217cf664`.
- Prior review verification: `8326d951bd6a4bfe3393424fff26f06e46c0c119`.
- Prior Phase 3 delivery: `f3fe32bc550f4cf4d04000fafde26c0e2e728bfd`.
- Verified implementation commit: `011c75cc309f5ba0c328770b7add2dbd74415be5`.
- Final delivery commit: the documentation commit introducing this handoff;
  resolve its exact hash with `git log -1 --format=%H -- docs/PHASE4_HANDOFF.md`.
  This avoids a self-referential commit hash. The final user report gives the
  literal delivery hash, also verified against the remote branch.
- Remote: `https://github.com/spark2k06/SPK286.git`.

The initial checkout was clean. Git branches, remotes, history and tags were
inspected, and the actual review branch/remote resolved to the supplied base.
The specifications, reviewed handoffs, interfaces, compiler, tests and release
scripts were inspected before implementation. Scope was written in
[PHASE4_SCOPE.md](PHASE4_SCOPE.md) before instruction RTL/microcode changes.
Only the dedicated branch is published; main and existing history are untouched.

## Received baseline

A previously absent `build/phase4-baseline` ran `make phase3-check` before
implementation. It returned status 0 and `PHASE3_VALIDATION_PASS`, including:

- 97 Python tests, including 47 compiler/auditor tests;
- deterministic double regeneration, five matching artifact hashes and empty
  generated-file Git diff;
- all 17 inherited directed benches in both Verilator and Icarus;
- lint, reset/state/trace smoke and failure-status propagation;
- B8..BF 40,000/40,000, 89 3,955/3,955, 8B 3,940/3,940, zero failures;
- independent upstream parser comparison for 50,000 records/680,905 cycles;
- 20 rejected comparator faults/four pristine executions and four rejected
  operand/BIU mutants/two pristine benches;
- pinned MCL86 reconstruction/round-trip checks and the complete regression;
- Yosys structural checks and generic mapping: 6,223 cells, 733 sequential.

No Phase 3 production defect was found or corrected in this phase.

## Exact admitted ISA

All forms are unprefixed word operations, including register-direct and memory
ModR/M. Immediate sign extension applies only to 83's source byte; displacement
sign extension remains owned by the inherited operand decoder.

| Family | r/m16,r16 | r16,r/m16 | AX,imm16 | r/m16,imm16 | r/m16,sign-extended imm8 |
| --- | --- | --- | --- | --- | --- |
| ADD | 01 /r | 03 /r | 05 iw | 81 /0 iw | 83 /0 ib |
| OR | 09 /r | 0B /r | 0D iw | 81 /1 iw | 83 /1 ib |
| ADC | 11 /r | 13 /r | 15 iw | 81 /2 iw | 83 /2 ib |
| SBB | 19 /r | 1B /r | 1D iw | 81 /3 iw | 83 /3 ib |
| AND | 21 /r | 23 /r | 25 iw | 81 /4 iw | 83 /4 ib |
| SUB | 29 /r | 2B /r | 2D iw | 81 /5 iw | 83 /5 ib |
| XOR | 31 /r | 33 /r | 35 iw | 81 /6 iw | 83 /6 ib |
| CMP | 39 /r | 3B /r | 3D iw | 81 /7 iw | 83 /7 ib |

The incremental Phase 4 contract, SPEC/REALMODE_MVP dependency order and D-007
phase-number distinction support these eight families. TEST was conditional in
the task and is not explicitly assigned here by the project documents. CMP
supplies the required reusable no-write path. TEST, byte operands, unary ALU,
flag-control instructions and all later-phase families remain deferred.

## Architecture and durable decisions

D-018/D-019 in [DECISIONS.md](DECISIONS.md) record ownership and sequencing.

`spk286_alu` is the only arithmetic engine. It receives 16-bit A/B, carry input
and a three-bit functional operation: ADD=0, OR=1, ADC=2, SBB=3, AND=4, SUB=5,
XOR=6. It emits a result and candidate FLAGS. There is no opcode, ModR/M, EA,
bus or micro-PC interpretation inside the ALU. Arithmetic uses explicit
17-bit zero-extended operands and carry; the unused operation 7 is not admitted.

`spk286_alu_decode` resolves semantic operation, write permission and flag masks
from the captured opcode and captured ModR/M extension. The initial decoder
selects one of five form-specific microprograms and DST=AX for accumulator
forms. Future queue bytes cannot change the captured instruction's controls.

The executor owns TMP0=A (original destination), TMP1=B (source), TMP2=result,
three validity bits and pending candidate FLAGS/mask. Noncommutative operations
always compute A-B or A-B-CF. One ALU instance serves all instructions. The
operand service receives ordinary caller words and never learns temporary
identities. Immediate words arrive low byte then high byte; sign-extended
immediates consume one byte. Missing instruction bytes stall the micro-operation.

CMP selects the same SUB operation, followed by IF_WRITE result disposition
with write permission disabled. The result is discarded without a GPR/data
write. This is functional result handling, not artificial timing padding.
Every writing operation completes its register or entire logical memory write
before COMMIT_FLAGS. Odd-word writeback includes both BIU subcycles. END then
retires exactly once through the unchanged generic microsequencer.

The existing `spk286_registers` FLAGS storage is the sole architectural owner.
Candidate flags cannot update it until the explicit masked commit. No unrelated
control/system bit is an ALU side effect; fixed/reserved bits retain the
inherited storage contract.

| Class | Updated mask | Undefined mask | Stored behavior |
| --- | --- | --- | --- |
| ADD/ADC/SUB/SBB/CMP | 08D5 | 0000 | Commit CF/PF/AF/ZF/SF/OF |
| AND/OR/XOR | 08C5 | 0010 | Clear CF/OF, derive PF/ZF/SF; preserve stored AF |

Preserving undefined logical AF is an explicit implementation policy, not a
claim that all physical 286 parts preserve it. The mask excludes undefined
bits from architectural candidate commit. Defined/preserved/undefined are
separate decisions, so later instruction families can select other masks.

CF is unsigned carry for addition and unsigned borrow for subtraction; SBB
subtracts incoming CF. The B=FFFF, borrow=1 boundary is covered. OF means the
signed mathematical total lies outside -32768..32767. AF is nibble carry or
borrow; PF is even parity of the low eight result bits only; ZF/SF describe the
16-bit result. Intel 210498-005 table 3-1 (printed page 3-6), sections 3.3.1/3.3.2
and Appendix B are the normative evidence. Table 3-1 resolves the reversed PF
wording in the earlier section 2.3 prose. The independent Python model uses
signed range checks, nibble arithmetic and bit counting rather than copying RTL
sign-bit equations. Eleven hand-derived arithmetic cases anchor that model.
The cached manual hash and physical corpus provenance are in PHASE4_SCOPE and
SOURCE_NOTES. No external CPU implementation code has been reused.

## Microcode and preserved boundaries

Compiler 3.0 supports source formats 1, 2 and 3. Format 3 adds ten generic
functional controls (9..18), expanding the active word from four to five bits.
Its 45-word ROM has six-bit addresses and eight entries. All eleven inherited
MOV words/entry values remain unchanged; frozen format-1/2 fixtures and the
independent active format-3 contract are tested separately.

| Entry | Address | Words |
| --- | ---: | ---: |
| MOV_R16_IMM16 | 0 | 3 |
| MOV_RM16_R16 | 3 | 4 |
| MOV_R16_RM16 | 7 | 4 |
| ALU_RM16_R16 | 11 | 7 |
| ALU_R16_RM16 | 18 | 7 |
| ALU_AX_IMM16 | 25 | 6 |
| ALU_RM16_IMM16 | 31 | 7 |
| ALU_RM16_IMM8S | 38 | 7 |

Human-readable `.mc` remains authoritative. ALU DECODED, IF_WRITE disposition
and COMMIT_FLAGS express acquisition/compute/write/commit/END sequencing.
Compiler dataflow validation rejects undefined temporaries, invalid operation
or destination, absent context, pending-result overwrite, premature/missing
FLAGS commit and work after END/commit. Emitted-ROM auditing, source locations,
round-trip checks and deterministic generated artifacts remain mandatory.
Generated outputs are never hand-edited.

No changes were needed in the generic microsequencer, ModR/M, EA, operand decode,
operand service, register/segment storage, BIU, fetch or queue RTL. Their diff
against the reviewed base is empty. Existing data access handles DS/SS defaults,
word limit precheck, READY, odd splitting, arbitration and prefetch coexistence.
Register-direct forms issue no data transaction. A blocked whole word performs
no partial access, result/FLAGS commit or retirement. Exception delivery is
still deferred. Normal ALU data access does not flush prefetch.

Reset, redirect and instruction start clear all new temporary/valid/pending
state. Pause and malformed controls prevent semantic acceptance while accepted
BIU work may drain into a held response. Redirect retains Phase 3's documented
non-rollback contract: already committed GPR/FLAGS or external writes are not
undone, but canceled work cannot later commit stale state or retire. Precise
exception rollback is not introduced. There are no historical delay states,
timing NOPs, Accurate/Fast/Max modes or Phase 5 implementation.

## Verification and failure evidence

On 2026-09-08, a previously absent `build/phase4-final` ran the complete
`make phase4-check` from implementation commit
`011c75cc309f5ba0c328770b7add2dbd74415be5`. It returned status 0 with
`PHASE3_VALIDATION_PASS` and `PHASE4_VALIDATION_PASS`. Double regeneration
matched all five SHA-256 artifacts. Final generated Git diff and the tested
implementation working tree were empty. All mandatory gates below passed.
The final documentation commit changes only this handoff and README.

The ALU smoke passed 400/400. The full new corpus took 28.401 seconds
(5,847.9 tests/second); these host measurements are not historical CPU timing.

The new benches run in both Verilator and Icarus, alongside every inherited
bench (20 distinct benches per simulator in total):

- ALU: 29,912 model vectors; 14 edge values, both carry inputs, all 256 low-byte
  parities under four high-byte patterns, exhaustive nibble operands and
  20,000 deterministic random cases (seed 286).
- Full instructions: 10,240 cases / 1,028,099 checks, including 1,536 immediate
  starvation cycles. Eight families/five forms cover every register pair/EA,
  DS versus SS, disp8/disp16, both operand directions, signed immediates,
  aligned/odd memory, READY delays, whole-word blocking, exact GPR/FLAGS/IP/RAM,
  preservation of neighbors, no CMP writes and exactly-once retirement.
- Lifecycle: 110 pause/malformed-control/redirect/reset scenarios (92 operand
  and 18 immediate cases), plus an eight-instruction dependent mixed stream;
  5,830 checks. Boundaries include partial context, reads, ALU, pending result,
  writeback subcycles, FLAGS, END and partial immediate acquisition.

All 113 Python tests pass, including 52 compiler/auditor tests. Model tests
include hand-derived flags, algebraic properties and mask/preservation checks.
New admission tests verify all 40 forms and 256 ModR/M encodings, group/file
identity, immediate lengths, unsupported widths, prefixes and exceptions.

Eight copied-input RTL mutants are rejected for their intended assertion:
CF inversion, accidental word parity, missing OF, missing AF, reversed SUB,
dropped carry input, CMP writeback and all-FLAGS update. Two pristine benches
pass and production source hashes remain unchanged. Inherited four boundary
mutants/two pristine benches and 20 comparator faults/four pristine executions
also pass. Compilation errors cannot count as successful mutation detection.

Important failures found and fixed during development:

1. The initial component bench read vector fields directly into DUT inputs via
   `$fscanf`. Verilator generated a static/Slow evaluation path, leaving the
   ALU output stale on the second vector (0+1). Reading into staging variables
   and explicitly assigning DUT inputs corrected this test-harness/tool issue.
   Neither the mathematical expectations nor ALU behavior was changed to pass.
2. A wildcard package import in the extended executor passed both simulators
   but failed Yosys parsing. Explicit package-qualified controls, matching the
   inherited source convention, fixed portability. Focused tests, lint,
   synthesis and the complete regression were repeated on the corrected RTL.
3. Expanding the upstream-parser audit to logical opcodes exposed that the
   pinned moo2json converter omits RMSK. The first OR record differed only by
   the valid wire-derived F7EE mask. The MOO 1.1 specification and binary fields
   establish that mask. An independent audit-only RMSK reader now checks every
   production mask before comparing the converter's represented state. Three
   fixture/negative tests prove missing/changed/extra masks and changed state
   fail. Neither production parsing, the corpus nor comparison masks changed.
   This was an inherited audit coverage gap, not a Phase 3 CPU defect.
4. The fetch tool retains its original direct-script invocation as well as
   module invocation after adding the shared opcode inventory. The release
   gate preserves only the 40 full ALU reports separately from smoke reports.

No hardware vector required case-specific handling, modified expected state,
relaxed masks or a Phase 3 production correction. Development evidence remains
under `build/phase4-dev`, including the failed portability run and subsequent
verified run. Icarus's informational constant-select sensitivity message is
not suppressed; both simulators execute the same expectations.

## Hardware-derived accounting

The unchanged pinned SingleStepTests/80286 commit is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. There are 40 new files, each with
5,000 discovered records. Every full-run selected record executes and passes.
All rows have zero revocations, sampling exclusions and failures. Prefix
exclusions are classified first; exception exclusions are among remaining
unprefixed records. Exclusions are never counted as passes.

| Family | Discovered | Prefix excluded | Exception excluded | Selected / executed / passed |
| --- | ---: | ---: | ---: | ---: |
| ADD | 25,000 | 4,119 | 127 | 20,754 |
| OR | 25,000 | 4,119 | 126 | 20,755 |
| ADC | 25,000 | 4,108 | 126 | 20,766 |
| SBB | 25,000 | 4,102 | 124 | 20,774 |
| AND | 25,000 | 4,111 | 128 | 20,761 |
| SUB | 25,000 | 4,115 | 128 | 20,757 |
| XOR | 25,000 | 4,117 | 126 | 20,757 |
| CMP | 25,000 | 4,113 | 126 | 20,761 |
| **New total** | **200,000** | **32,904** | **1,011** | **166,085** |

Per opcode/form (5,000 discovered each):

| Opcode | Prefix excluded | Exception excluded | Selected / executed / passed |
| --- | ---: | ---: | ---: |
| 01 | 1,030 | 34 | 3,936 |
| 03 | 1,030 | 35 | 3,935 |
| 05 | 0 | 0 | 5,000 |
| 81.0 | 1,029 | 29 | 3,942 |
| 83.0 | 1,030 | 29 | 3,941 |
| 09 | 1,029 | 34 | 3,937 |
| 0B | 1,032 | 34 | 3,934 |
| 0D | 0 | 0 | 5,000 |
| 81.1 | 1,029 | 29 | 3,942 |
| 83.1 | 1,029 | 29 | 3,942 |
| 11 | 1,024 | 34 | 3,942 |
| 13 | 1,025 | 34 | 3,941 |
| 15 | 0 | 0 | 5,000 |
| 81.2 | 1,029 | 29 | 3,942 |
| 83.2 | 1,030 | 29 | 3,941 |
| 19 | 1,022 | 33 | 3,945 |
| 1B | 1,022 | 33 | 3,945 |
| 1D | 0 | 0 | 5,000 |
| 81.3 | 1,029 | 29 | 3,942 |
| 83.3 | 1,029 | 29 | 3,942 |
| 21 | 1,025 | 35 | 3,940 |
| 23 | 1,025 | 35 | 3,940 |
| 25 | 0 | 0 | 5,000 |
| 81.4 | 1,030 | 29 | 3,941 |
| 83.4 | 1,031 | 29 | 3,940 |
| 29 | 1,028 | 35 | 3,937 |
| 2B | 1,028 | 35 | 3,937 |
| 2D | 0 | 0 | 5,000 |
| 81.5 | 1,029 | 29 | 3,942 |
| 83.5 | 1,030 | 29 | 3,941 |
| 31 | 1,029 | 34 | 3,937 |
| 33 | 1,028 | 34 | 3,938 |
| 35 | 0 | 0 | 5,000 |
| 81.6 | 1,030 | 29 | 3,941 |
| 83.6 | 1,030 | 29 | 3,941 |
| 39 | 1,027 | 34 | 3,939 |
| 3B | 1,027 | 34 | 3,939 |
| 3D | 0 | 0 | 5,000 |
| 81.7 | 1,029 | 29 | 3,942 |
| 83.7 | 1,030 | 29 | 3,941 |

The inherited B8..BF coverage passes 40,000/40,000; 89 passes 3,955/3,955 and
8B passes 3,940/3,940. Total inherited: 47,895/47,895, zero failures, with 2,047
prefix and 58 exception exclusions. Combined admitted hardware coverage is
213,980/213,980, zero failures; 250,000 discovered, 34,951 prefix exclusions,
1,069 exception exclusions and no revocations or full-run sampling skips.

The upstream parser is independently cross-checked over all 250,000 records
(including excluded records) and captured cycles. Since the pinned converter
omits RMSK, a separate independent wire audit verifies every mask using the
[MOO 1.1 specification](https://github.com/dbalsom/moo/blob/main/doc/moo_format_v1.md).
All 4,409,540 cycles and 250,000 unique hashes agree; 75,000 records have masks.
The raw corpus has 1,399 exception records; 330 also have excluded prefixes,
so the disjoint exception-exclusion count is 1,069.
The target-instruction retirement/trailing-HLT final-IP convention is retained.
Architectural registers and complete sparse final RAM remain strict; no expected
values are patched. Logical captures use upstream FLAGS mask F7EE, omitting
CF/AF/OF. That exact mask is preserved. Separate model/directed checks establish
defined logical CF=OF=0; captured logical AF=0 is not an architectural guarantee.
Results establish architectural functionality, not captured bus-cycle or
historical timing equivalence.

## Synthesis and reproducibility

Verilator lint passes. Yosys passes 16 structural scopes plus full generic
mapping, with no unresolved process/memory or check-assert error.

| Generic resource | Reviewed Phase 3 | Phase 4 | Delta |
| --- | ---: | ---: | ---: |
| Cells | 6,223 | 7,326 | +1,103 |
| Sequential cells | 733 | 806 | +73 |

These are generic Yosys cells, not Cyclone V ALMs or Fmax. No Quartus device
resource/timing result is claimed. WSL Ubuntu-24.04 uses Python 3.12, Verilator
5.020, Icarus 12.0 and Yosys 0.33. Native Windows Python also checks the compiler.

From the committed implementation, use a previously absent build directory:

```bash
make singlestep-fetch mcl86-fetch
SPK286_BUILD_DIR="$PWD/build/phase4-reproduce" make phase4-check
```

Missing, dirty, wrongly pinned or incomplete required corpus fails the release
gate. The phase4-check target retains the entire reviewed phase3-check, then
adds new smoke/full hardware families and ALU mutations. CI invokes the same
gate. Daily optional corpus skips cannot satisfy release.

Final artifacts are retained under `build/phase4-final`: `validation.log`,
`generated.sha256`, `reports/yosys_mapped.log`, `microcode-audit`, `mcl86`,
`singlestep/full-reports` (inherited full reports),
`singlestep/phase4-full-reports` (exactly 40 new full reports), parser/comparator
audit output, mutation logs, and inherited traced replays. These generated
artifacts and the external cache remain outside repository history.

## Handoff and remaining debt

The instruction matrix, architecture/state interface, microcode format notes,
verification, source notes, SingleStep integration and DECISIONS document the
new contracts. Scope has not been expanded into machine integration, timing or
later instruction families. CPU-only boundaries remain unchanged.

Phase 5 can begin using the existing operand acquisition, ALU, FLAGS, result
routing, register/memory writeback and retirement owners. New functional selectors or
policies may be added deliberately without replacing these components. The
current executor supports one binary result and one FLAGS commit per admitted
instruction; it is not a speculative general micro-register file.

Remaining work includes byte operands, TEST/unary operations when admitted,
shifts/rotates, stack/control flow, exception delivery and prefixes, interrupts,
protected mode, bus ownership features and historical timing policy in their
assigned phases. Precise cancellation rollback, complete native-bus timing and
Quartus device-specific area/Fmax remain deferred. No claim of full 80286 ISA,
BIOS/OS boot or cycle accuracy is made.
