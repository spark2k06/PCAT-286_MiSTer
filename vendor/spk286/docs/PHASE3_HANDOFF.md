# Phase 3 Handoff — ModR/M, EA16 and Word MOV Operands

## Objective and repository provenance

Phase 3 establishes reusable 16-bit ModR/M decoding, effective addressing,
register/memory operands and a shared data/code BIU through microcoded word
MOV `89 /r` and `8B /r`. No ALU, FLAGS arithmetic or Phase 4 instruction has
been added. Functional scheduling remains separate from historical timing.

- Base: `9657a13`, the verified merge of Phase 2.80 into `codex/pre-phase3-audit`.
- Dedicated branch: `codex/phase3-modrm-operands`.
- Addressing commit: `66e3c5d` — Add verified 16-bit ModRM decoding and effective addressing.
- Final tested implementation commit: `1714783a41652546f7247eb407b37d2a604335d7`
  — Add microcoded MOV operands and shared READY-aware data bus.
- Delivery commit: the documentation commit introducing this handoff; resolve
  its exact hash with `git log -1 --format=%H -- docs/PHASE3_HANDOFF.md`.
- Remote: `https://github.com/spark2k06/SPK286.git`.

The initial tree was clean. Status, all branches/remotes, forty recent commits
and tags were inspected rather than inferred from the supplied phase summary.
There were no tags. Phase 2.75 completion and the retrospective/Phase 2.80
audits were present in the actual base. Only the dedicated branch is published;
main, tags and published history are not rewritten.

The actual MVP document is `SPK286_REALMODE_MVP.md`. AGENTS, all prior relevant
handoffs, PRE_PHASE3_AUDIT, specification, environment, microcode, timing,
architecture, interface and verification documents were read before RTL edits.
The full Phase 3 request superseded the initially truncated request. The CPU-only
boundary and the audit's strict adapter/ROM requirements are preserved.

## Received baseline verification

WSL Ubuntu-24.04 ran in `/mnt/d/GitHub/SPK286`, using the authoritative Windows
checkout, with Python 3.12.3, Verilator 5.020, Icarus 12.0, Yosys 0.33 and
g++ 13.3. A previously absent `build/phase3-baseline` retained all output.
Commands before architectural implementation were:

```bash
git status
git branch -a
git remote -v
git log --oneline --decorate -n 40
git tag --list
bash scripts/env_check.sh
SPK286_BUILD_DIR=build/phase3-baseline make regression
SPK286_BUILD_DIR=build/phase3-baseline make singlestep-smoke singlestep-mov
SPK286_BUILD_DIR=build/phase3-baseline make microcode microcode-check microcode-test microcode-audit mcl86-check
```

The normal regression already checks generated consistency before compilation.
Explicit regeneration also produced no Git difference. Baseline results:
43 compiler/audit tests, 90 total Python tests, ten directed benches in both
simulators, reset/state/vector smoke, lint and synthesis all passed. SingleStep
smoke passed 80/80; full B8..BF passed 40,000/40,000, zero revoked/skipped/failed,
5.303 seconds and 7,542.5 tests/second. Each opcode used 50,000 implementation
cycles for 5,000 tests. There was no unexplained baseline regression.

Inherited MCL86 comparison also passed: original 4,096/4,096 words identical,
431 differences in the separately documented rewrite, both full round-trips
identical. The audit reference material remains separate from CPU RTL.

## Implementation and ownership

| Area / files | Responsibility |
| --- | --- |
| `rtl/spk286_modrm.sv` | Decode mode, REG, RM, direct-register flag and displacement length |
| `rtl/spk286_effective_address.sv` | Single base/index and DS/SS table, 16-bit offset arithmetic |
| `rtl/spk286_operand_decode.sv` | Streaming byte acquisition and stable instruction context |
| `rtl/spk286_operand.sv` | Shared REG/RM word selection, register commit, whole-word limit check, logical request/completion |
| `rtl/spk286_biu.sv` | Sole physical bus arbiter, READY, word lanes, odd splits and retained completion |
| `rtl/spk286.sv` | Compose existing storage/prefetch and new operand/BIU services; numeric debug outputs |
| `rtl/spk286_decoder.sv`, `rtl/spk286_micro_executor.sv` | Generated entry selection and reusable functional operations |
| `microcode/source/data_move.mc`, compiler/auditor and all five generated artifacts | Three readable MOV programs, minimal format 2, explicit independent contract |
| `sim/unit/*operand*_tb.sv`, ModR/M/EA/BIU benches, decoder/ROM benches | Directed functional and lifecycle verification in both simulators |
| `tools/run_singlestep.py`, `tools/fetch_singlestep.py`, `tools/audit_singlestep.py`, `sim/verilator/singlestep.cpp` | Real corpus admission, execution, strict RAM comparison and adversarial audit |
| Python tests, Makefile, scripts, CI | Portable builds, scope accounting, mandatory full hardware families and release gate |

The generic microsequencer, register storage, segment-cache storage, fetch client
and six-byte queue RTL are unchanged. No parallel hardwired MOV controller or
duplicate architectural register storage was introduced.

### ModR/M, displacement and segment selection

All 256 ModR/M encodings are decoded. Mode 11 selects an RM register; mode 01
consumes and sign-extends disp8, mode 10 consumes little-endian disp16, and mode
00 consumes no displacement except RM=110, which takes direct disp16. The
captured displacement is always 16 bits. Every EA sum wraps modulo 65,536.

| RM | Normal base/index | Default segment |
| --- | --- | --- |
| 000 | BX+SI | DS |
| 001 | BX+DI | DS |
| 010 | BP+SI | SS |
| 011 | BP+DI | SS |
| 100 | SI | DS |
| 101 | DI | DS |
| 110, mode != 00 | BP | SS |
| 111 | BX | DS |
| 110, mode = 00 | Direct disp16, no base | DS |

The context service latches fields as bytes are accepted, then captures offset
and segment on the resolution edge. It remains stable while following bytes
are prefetched. The segment translation port selects this context during
execution and reverts to external setup queries when paused. Physical address
is the existing cached 24-bit base plus 16-bit offset, retaining A20 carry.
There is no 386 addressing/SIB or downstream motherboard address mask.

### Register and memory operations

REG16 selects the ModR/M REG field. RM16 selects RM from the same architectural
word-register mux when mode=11, otherwise the captured segmented memory operand.
Both directions reuse this service and the original GPR write port. Register
forms issue no data transaction and preserve all unrelated state and FLAGS.

A memory operation first checks the entire word using 17-bit `offset+1 <=
segment_limit`. A rejected word sets sticky `operand_blocked` before either
byte can access memory, does not retire and clears on reset/redirect. This is a
development indication, not implemented exception delivery. Intel 210498-005,
Appendix B and MOV page B-74 specify a real-mode interrupt 13 for a word at
FFFF; the second byte does not wrap to offset zero. See D-014/D-016 and
SOURCE_NOTES for the primary reference.

Once accepted by the BIU, the operand pending bit suppresses duplicate requests.
Reads return a full word to TMP0 only on response acceptance. Writes wait for
logical completion before END. Pauses and malformed controls hold micro-PC,
context and semantic effects; physical work may finish into the held response.

### BIU, READY and prefetch coexistence

The BIU snapshots one logical data request. At a free physical-cycle boundary,
accepted data has priority over code. A visible cycle waiting for READY keeps
its owner, address, direction, BHE, status and write data until completion;
new data cannot steal a code cycle. Only the selected client sees READY.

Even words use both lanes in one cycle. Odd words use the upper lane for the
low byte at N, then the lower lane for the high byte at N+1. Each subcycle may
stall independently, with ownership retained across the pair. One held logical
response acknowledges the complete word, and writes affect only selected lanes.
Statuses are CODE=D, MEMR=5, MEMW=6, passive=F.

The fetch client retains cursor/response/stale-stream management. The queue
retains storage/refill/order. Ordinary data access never flushes it; queued
instruction bytes remain available and prefetch resumes when the BIU is free.

Redirect cancels semantic execution and discards stale data responses, while
an already accepted logical word drains, including remaining odd write bytes.
Reset aborts pending physical work. Neither rolls back external writes already
accepted. This deliberate extension of the development redirect contract is
not precise interruption/exception delivery; future exception entry must
serialize memory side effects appropriately.

### Microcode and retirement

The compiler retains format 1 and adds format/encoding 2 only for reusable
operand operations. Control grows from two to four bits. The active ROM has
11 words, four address bits, and invalid addresses 11..15:

| Entry | PC | Functional sequence |
| --- | ---: | --- |
| MOV_R16_IMM16 | 0 | FETCH_IMM16, MOVE TMP0 to DST, END |
| MOV_RM16_R16 | 3 | DECODE_MODRM, READ_REG16, WRITE_RM16, END |
| MOV_R16_RM16 | 7 | DECODE_MODRM, READ_RM16, WRITE_REG16, END |

Reads define TMP0; writes require it. REG/RM operations require prior context,
duplicate decoding is rejected, and END remains mandatory. The immutable
Phase 2.75 contract is still tested against frozen format 1 source; the separate
Phase 3 fixture pins new versions, widths, words, labels and entries. All five
artifacts are generated by the deterministic compiler and checked byte-for-byte.
The emitted-ROM auditor supports both versions and canonical recompilation.

The microsequencer RTL did not change. It advances only on functional completion
and emits one retirement at END. IP advances once per consumed instruction byte,
independently of the fetch cursor: B8..BF length 3; 89/8B length 2, 3 or 4.
No writeback or END consumes a byte. No idle/NOP padding or timing scheduler
was introduced; implementation cycle counts are not historical 80286 timing.

## Directed and tool verification

Focused development checks ran before broader regression and each RTL commit.
The first addressing commit passed independent units, lint, full dual-simulator
regression, Yosys and B8..BF 40,000/40,000. Integration then passed early 89/8B
smoke, focused tests, full supported families, inherited full coverage and audit.

| Focused bench | Result per simulator, Verilator and Icarus |
| --- | --- |
| ModR/M | 256/256 encodings |
| EA | 25,056 checks |
| Operand decode | 1,280 streaming contexts plus partial cancellation; 12,099 checks |
| BIU | 104 word/reset/cancel cases plus arbitration; 2,326 checks |
| MOV operands | 128 register pairs, 480 memory/boundary cases, four-instruction stream; 47,003 checks |
| Operand lifecycle | 36 pause/redirect/reset cases at six boundaries; 1,971 checks |
| Decoder | All 256 opcodes, exactly three MOV forms |
| Generated ROM | 16 semantic/range checks |
| Inherited microcoded immediate MOV | 48 vectors, eight-instruction stream, four lifecycle boundaries; 5,380 checks |

Tests deliberately distinguish DS/SS and all base/index values, exhaust disp8
in component checks, use 0000/0001/7FFF/8000/FFFF disp16, exercise wrap and A20
carry, poison inactive read lanes and check neighboring write bytes. READY
tests cover zero through four waits independently on both odd subcycles.
The integrated MOV bench records 876 data wait cycles and 1,522 coexistence
cycles with queued bytes. Lifecycle tests include partial ModR/M/displacement,
first/second physical cycles and held response boundaries.

## Final clean validation

Validation began from clean implementation commit `1714783`, with the previously
absent `build/phase3-final` directory, after the serial development regression
passed. No source implementation changed during this run. The only subsequent
commit records this handoff. Exact release command:

```bash
SPK286_BUILD_DIR="$PWD/build/phase3-final" make phase3-check
```

The checked-in script expands to:

```bash
make microcode
sha256sum microcode/generated/* > "$SPK286_BUILD_DIR/generated.sha256"
make microcode
sha256sum -c "$SPK286_BUILD_DIR/generated.sha256"
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
make verify-failure data-smoke
python3 -m tools.run_singlestep --opcode 89 --index 0 --trace "$SPK286_BUILD_DIR/traces/mov-89-0.vcd"
python3 -m tools.run_singlestep --opcode 8B --index 3 --trace "$SPK286_BUILD_DIR/traces/mov-8B-3.vcd"
make microcode-check
git diff --exit-code -- microcode/generated
```

The gate requires the pinned clean external corpus and all ten opcode files.
It preserves full JSON reports before smoke/replay can overwrite current ones.
Missing data or an optional daily-regression corpus skip cannot pass the gate.

Completed on 2026-09-08 with process status 0 and terminal marker
`PHASE3_VALIDATION_PASS`. Regeneration matched all five SHA-256 values, and
the final generated Git diff was empty. The compiler consistency check also
passed using the native Windows Python runtime.

| Gate | Final result |
| --- | --- |
| Compiler / emitted-ROM audit | 47/47 tests; active contract and round-trip PASS |
| All Python / vector / inherited tool tests | 97/97 PASS |
| Verilator lint | PASS, no reported warnings |
| Directed RTL | All 16 benches PASS in each simulator, 32 bench executions per suite |
| Reset / waveform | Verilator and Icarus PASS; initial physical fetch FFFFF0 |
| Architectural state vectors | 4/4 initialization/fetch cases PASS, zero instructions executed |
| SingleStep smoke | B8..BF 80/80 and 89/8B 20/20 PASS |
| Full SingleStep | 47,895/47,895 supported cases PASS, zero failures |
| Yosys | 14 component/integrated structural checks plus full generic synthesis PASS |
| Complete normal regression | REGRESSION PASS |
| MCL86 inherited reference check | Original 4,096/4,096; both full round-trips PASS |
| Corpus / adversarial audit | 50,000 records and 680,905 cycles equal upstream; 20 rejected faults, 4 pristine passes |
| Negative simulator propagation | Both simulators reject deliberately wrong reset expectation |
| Data-loader smoke | 1/1 parsed/selected PASS; execution correctly reported deferred |
| Traced memory replay | 89 index 0 and 8B index 3 PASS, 15 implementation cycles each |

The final Yosys map contains 6,223 generic cells including 733 sequential cells,
versus 4,707 / 607 at the inherited baseline. There are no remaining processes
or memories after generic mapping, and `check -assert` reports no structural
problems. These counts are not Cyclone V ALMs, block RAM usage or Fmax estimates.
No latch, width, multi-driver or other HDL warning was reported. The intentional
negative-reset FAIL/FATAL lines are required evidence of status propagation.
An intermittent WSL systemd-user-session message did not prevent shell commands
or validation from completing; no HDL check was suppressed for it.

`build/phase3-final/validation.log` retains the complete run. Subdirectories
contain per-bench builds, Yosys reports, state vectors, microcode/MCL86 audit
reports, full SingleStep JSON, negative batches and VCDs. The later official
`make singlestep-fetch` acquisition command also passed with all ten files and
the same clean pinned commit; see `corpus-acquisition.log`.

## Hardware-vector results and scope

Upstream: SingleStepTests/80286 commit
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`, version 1.1.0, MIT-licensed Harris
N80C286-12 captures. The corpus remains clean and external under
`.cache/singlestep-80286`; only 89/8B were added to its sparse working set.

| Family | Discovered | Revoked | Prefix excluded | Exception excluded | Selected | Executed | Passed | Failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B8..BF | 40,000 | 0 | 0 | 0 | 40,000 | 40,000 | 40,000 | 0 |
| 89 | 5,000 | 0 | 1,016 | 29 | 3,955 | 3,955 | 3,955 | 0 |
| 8B | 5,000 | 0 | 1,031 | 29 | 3,940 | 3,940 | 3,940 | 0 |

Full runs have zero sample-selection skips. Prefix exclusions include all known
286 overrides/LOCK/REP forms; none is claimed supported. Revocation, prefix,
exception and sampling categories are disjoint in that order. The raw parser
audit sees 68 exception records, ten of which also have prefixes, giving 58
additional exception exclusions and 2,105 total excluded cases. Per-case
index/hash/reason is retained in full reports. Explicitly selecting an excluded
case fails; unexpected formats/state and in-scope failures are never filtered.

Architectural comparison covers all 14 exposed registers with masks and the
entire resulting sparse RAM map. Every MEMR byte must be supplied; unspecified
CODE prefetch alone retains the original zero-fill policy. MEMW requires READY
and affects only selected lanes. Extra memory writes fail comparison. The target
retires before trailing HLT; the inherited final-IP-minus-one convention remains
unchanged, with exact sequential instruction-length validation.

All 50,000 discovered records and 680,905 captured cycles agree with the upstream
parser. The real simulator rejects 20 deliberate faults and passes four pristine
probes, including memory read/write with traces. These checks validate parsing
and architectural comparison, not historical bus-cycle equivalence.

Final full-run host throughput was 6,159.7 tests/second for 89/8B (7,895 cases,
1.282 seconds) and 7,427.1 tests/second for B8..BF (40,000 cases, 5.386 seconds).
Immediate MOV throughput is approximately 1.5% below the single inherited
measurement; all eight opcodes retain exactly 50,000 implementation cycles per
5,000 cases. Thus there is no added B8..BF implementation-cycle cost. Wall time
includes parsing/batching and host variability and is not emulated CPU MHz.
The new families use 52,758 implementation cycles for 89 and 52,420 for 8B.

## Issues resolved and architectural decisions

- No inherited functional regression required repair.
- A directed test initially used a 24-bit address to index its smaller test
  memory. Verilator rejected width truncation; explicit bounded indexing fixed
  the test harness without changing expectations or CPU behavior.
- One development regression overlapped an independent build of the same MOV
  executable and failed with `Text file busy` (tooling/build-directory ownership).
  The failed log is retained as `regression-build-overlap.log`. The full serial
  regression passed; final validation uses an independent directory. No failing
  check was waived and no CPU change was made for this tooling issue.
- The old audit fixture intentionally describes a three-word/two-bit ROM. The
  five additional reusable operations require a separately versioned active
  contract, preserving historical evidence rather than weakening old checks.
- Word offset FFFF was resolved from Intel documentation before bus behavior
  was implemented. Neither segment wrap nor partial write is accepted.
- No hardware-vector architectural mismatch required an opcode/case patch.
  No corpus expected result, register value or memory value was changed.

Durable decisions D-014 through D-017 document EA ownership, captured context,
format 2, shared BIU arbitration/cancellation, word limits and honest corpus
scope. README, ARCHITECTURE, BUS_INTERFACE, STATE_INTERFACE, INSTRUCTION_MATRIX,
VERIFICATION, SINGLESTEP_INTEGRATION and microcode/README describe the active
implementation. CI now requires the complete supported hardware families and
adversarial audit, in addition to the inherited CPU and MCL86 checks.

## Remaining boundaries and Phase 4 readiness

Phase 4 may safely reuse decode/context, REG/RM acquisition, EA/segmentation,
word read/write, BIU completion and writeback. Its ALU and FLAGS extension will
need additional temporary storage and explicit microcode operations; it does
not need to duplicate or replace the operand path. Phase 4 has not begun.

Non-blocking future work remains explicit: prefix execution, exception delivery
and precise interrupt serialization, protected-mode permissions/descriptors,
byte operand micro-operations, stack/control flow/strings/I/O, HOLD/HLDA/LOCK
and INTA, final native pin timing and Accurate/Fast/Max policy. FLAGS arithmetic
is absent. External setup controls require coordinated stream changes; they
are not an architectural exception interface. Exact captured bus timing,
Quartus placement, Cyclone V ALM/Fmax and physical FPGA validation are not claimed.
No downstream PC/AT or MiSTer machine logic is present.

The source tree is clean at delivery and the dedicated branch is pushed when
authentication is available. Build logs, traces, reports, cached manual and
external corpus remain ignored and outside Git.
