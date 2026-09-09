# PHASE 2.75 — Microcode and Microsequencer Foundation

Phase 2.75 is READY. The clean final validation preserves 40,000/40,000 B8..BF
executions with zero failures through the generated microcode path.

## Provenance and scope

- Branch: `codex/phase2.75-microcode-foundation`.
- Base: `4b55a3175ad958d7eb85b23bcad5459b0bbb0848`.
- Phase 2.5 integration: `caa53b4`; final Phase 2.5 handoff: `85ab90e`.
- Later documentation: timing architecture `b7c1622`, CPU boundary `ac3b3cd`,
  blocked pre-Phase 3 audit `4b55a31`. All were already published, confirmed
  against live remote branch tips before changes. The working tree was clean.
- Implementation commits: `10c30f8` (compiler/generated ROM), `ad7b71a`
  (microsequencer, decoder/executor migration, tests and build/debug integration).
- Final validation/handoff commit: the commit containing this document.
- Validation date: 2026-09-07.

The mandatory specifications, AGENTS, decisions, environment/MVP documents and
Phase 2/2.5 handoffs were read before migration. This phase implements the
small initial subset of the broader microcode specification, including scoped
debug labels. Executable branches and later ISA/timing features are deferred.
The current CPU-only specification and active phase scope govern older MVP
text describing eventual system integration. No normative specification was
rewritten, and no motherboard logic was introduced.

`docs/PRE_PHASE3_AUDIT.md` remains a historical report about the previously
missing Phase 2.75 implementation. This phase supplies that implementation;
it does not claim to perform every independent audit proposed by that report.

## Received baseline, reproduced before RTL changes

After `make clean`, all checks used a fresh `build/phase2.75-baseline` directory.
The inherited regression, explicit SingleStep smoke and full corpus returned 0.

| Baseline check | Observed result |
| --- | --- |
| Python unit tests | 11/11 PASS |
| Verilator lint | PASS, top and four components |
| Directed RTL benches | 6/6 PASS in Verilator and 6/6 in Icarus |
| Reset smoke | PASS in both, first fetch FFFFF0 |
| State vectors | 1 + 3 initialization/fetch cases PASS |
| Yosys | 5 structural checks PASS, 0 problems |
| Complete inherited regression | PASS |
| B8..BF smoke | 80 executed, 80 passed, 0 failed |
| B8..BF full | 40,000 executed, 40,000 passed, 0 failed |
| Full-run throughput | 5.048 s, 7,923.8 tests/s |

The eight full batches each executed 5,000 tests with 40,000 implementation
cycles. The unchanged, clean external corpus is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`, published version 1.1.0,
MIT, Harris N80C286-12 hardware captures. It remains ignored under `.cache/`.
No corpus refresh, exclusions or expected-result changes were made.

Baseline tools: Python 3.12.3, Verilator 5.020, Icarus 12.0, Yosys 0.33,
GNU Make 4.3, G++ 13.3.0, WSL kernel 6.6.87.2-microsoft-standard-WSL2.
An initial WSL systemd-user-session warning did not prevent tool execution;
no host configuration or tool installation was changed.

## Compiler and language

Authoritative source: `microcode/source/data_move.mc`.

```text
microcode_format 1
instruction MOV_R16_IMM16:
    FETCH_IMM16 -> TMP0
writeback:
    TMP0 -> DST
    END
```

The standard-library Python compiler lives at
`tools/microcode/compile_microcode.py`. It parses source into explicit
`Location`, `Statement`, `Label` and `Block` dataclasses, resolves symbols and
validates semantics, expands to addressed `MicroOp` records in `Program`, then
encodes and emits outputs. Each current source statement expands to one
functional ROM operation. File, line, entry, operands, statement text and
micro-address survive into the machine-readable map.

Source paths sort deterministically; entries retain source order. Labels are
scoped as `ENTRY.label`, name the following operation and consume no ROM words.
They are source/debug symbols only. No executable label references, branches,
calls, macros, arithmetic expressions or loops exist in this subset. Unsupported
syntax is rejected. Symbol queries reject unresolved names.

Validation rejects malformed declarations, duplicate entries/labels, invalid
operands/operations, dangling labels, missing END, unreachable trailing work,
TMP0 use before definition, wrong/missing format version, ROM overflow and
address-width overflow. Expected source errors include file, line and entry,
without a Python traceback. Address width/depth default to the required minimum;
optional limits can be tested independently. Current numeric debug PCs permit
up to 12 bits.

## Generated artifacts and representation

All five deterministic artifacts in `microcode/generated/` are committed:

| Artifact | Contents |
| --- | --- |
| `spk286_microcode_pkg.sv` | Dimensions, operation and entry constants |
| `spk286_microcode_rom.sv` | Synthesizable combinational ROM and validity output |
| `spk286_microcode.lst` | Symbolic address/word/source listing |
| `spk286_microcode_symbols.json` | Schema 1 entries, labels and per-PC source/operand/word records |
| `spk286_microcode_validation.json` | Compiler/format/encoding versions, source SHA-256, dimensions, usage and validation |

Initial control is two bits: 0 INVALID, 1 FETCH_IMM16, 2 MOVE, 3 END. There are
three used words, two address bits and no timing bits. The complete combinational
`case` ROM returns invalid outside used addresses. No vendor primitive or
runtime initialization file is required. This tiny ROM maps to logic; block
RAM, Cyclone V utilization and Fmax are not claimed.

Format 1 and encoding 1 are independent of future ALU/source/destination/bus/
branch/timing fields. The IR and versioned schemas can grow without assigning
historical latency to operation count. A separate HEX/MIF image is deferred;
the current package/ROM are self-contained deterministic CPU inputs.

`make microcode` regenerates; `make microcode-check` compares all bytes without
writing; `make microcode-test` runs compiler tests independently. Every RTL
build/lint/synthesis script sources `scripts/rtl_sources.sh`, which checks
consistency and lists package, ROM and CPU RTL in compilation order. A stale
artifact is a failure, not an implicit repair. Unchanged generation preserves
file timestamps. Logs, traces, caches and batches remain ignored.

## Sequencer, decoder and datapath contracts

`spk286_microsequencer` owns micro-PC, entry, active/fault state and retirement.
An idle `start/start_ready` handshake loads an entry; active starts are ignored.
`operation_valid` permits functional work. A required operation holds its PC
until `operation_done` is asserted on an enabled edge. Sequential advancement
cannot wrap at the ROM boundary. Invalid entry/ROM/fallthrough latches a
development `microcode_fault`, suppressing retirement until reset/cancel.

`spk286_decoder` recognizes B8..BF and supplies the one generated
`MOV_R16_IMM16` entry plus `opcode[2:0]`: AX/CX/DX/BX/SP/BP/SI/DI. Entry loading,
opcode consumption and destination latching occur together. No ModR/M,
displacement, prefix or effective-address behavior was added.

`spk286_micro_executor` owns one 16-bit TMP0 and one low/high acquisition bit.
FETCH_IMM16 accepts low then high bytes through FIFO valid/ready. Empty FIFO
stalls the operation without changing micro-PC or losing the low byte. After
the high byte, MOVE writes TMP0 to the decoder-derived word destination.
The external setup byte-mode input cannot change that width. MOV never writes
FLAGS, unrelated GPRs or segment state.

The existing six-byte FIFO and physical fetch implementation were reused;
their RTL was not redesigned. The FIFO consumes one byte per accepted opcode/
immediate handshake, advancing architectural IP by exactly one each time.
Writeback/END consume no bytes. Prefetch cursor and architectural IP remain
distinct, including uninterrupted multi-MOV programs. READY, lanes, capacity,
refill and stale-response/redirect handling retain their existing owners.

END generates a one-clock retirement pulse after writeback, independent of
queue refill and the next bus completion. The next opcode is still unconsumed
at this boundary. The pulse clears even if execution is then paused. There is
no old production hardwired MOV FSM or parallel execution path.

Reset/valid redirect cancel outstanding functional work and clear temporary
acquisition; a redirect on MOVE/END suppresses that edge's write/retirement.
A prior completed write is not rolled back: external redirect is a development
composition control, not a precise exception facility. Pauses hold microstate
and partial immediates. FIFO fill is qualified by autonomous execution so a
held setup response cannot be inserted repeatedly. Malformed control
transactions freeze semantic progress and architectural writes together.

Unsupported opcodes remain unconsumed with deterministic `unsupported_opcode`
and `debug_opcode`; architectural #UD delivery is still deferred.

## Debug and timing boundary

Numeric `debug_micro_pc`, `debug_micro_entry`, `debug_micro_instruction`,
`debug_micro_active` and `microcode_fault` observe actual execution control.
The last PC/entry remain visible while inactive. Source text is not synthesized.
The SingleStep C++ failure report now includes these values and queue count;
its expected-state and HALT/IP comparison rules are unchanged.

```text
python3 -m tools.microcode.compile_microcode --pc 0x1
python3 -m tools.microcode.compile_microcode --lookup MOV_R16_IMM16.writeback
```

Functional scheduling is not historical 80286 timing. `enable` and completion
are a clean future integration boundary; a later timing policy must coordinate
acceptance/advancement or retain completed responses without repeating side
effects. All real dependencies remain mandatory. No Accurate/Fast/Max modes,
MHz profiles, cycle tables, timing scheduler, NOP padding or arbitrary waits
were implemented. Intel MOV evidence was read/visually checked; its timing
column was not encoded as mandatory semantic delay.

## Verification before the final clean run

- Compiler tests: 31 PASS; all Python tests: 42 PASS.
- Directed RTL: ten benches PASS in both simulators.
- New sequencer: 37 checks; decoder: 256 opcode checks; ROM: 4 checks.
- New CPU bench: 48 MOV vectors, uninterrupted eight-MOV stream and four
  cancellation/reset/resume boundaries, 5,380 counted checks and 375 observed
  queue-underfill cycles. Counters are directed checks, not ISA coverage claims.
- Inherited benches unchanged: registers 200, segments 262,202, fetch 26,
  core 7 counted bus checks, queue 19, execution 16 bus transactions plus
  their uncounted assertions; all PASS in both simulators.
- Reset smoke, Python/state vectors, Verilator lint and normal regression PASS.
- Nine Yosys hierarchy/component checks and full generic synthesis PASS.
  Mapped integrated design: 4,707 generic cells, including 607 flip-flop cells;
  zero memories/processes after mapping. These are not FPGA ALM/Fmax figures.
- SingleStep smoke: 80/80; per-opcode sample: 800/800; full: 40,000/40,000,
  zero failures. Migration full throughput: 5.598 s, 7,145.4 tests/s.
- Full batches now report 50,000 implementation cycles per 5,000 executions,
  versus 40,000 before migration. This is implementation scheduling only.

## Final clean validation

The implementation at `ad7b71a` was rebuilt after deleting transient build
output with `make clean`. No previously compiled simulator executable was
reused for the initial checks. Generated committed source remained unchanged
after regeneration. All commands completed successfully; the final sequence
reported `FINAL_CLEAN_VALIDATION_PASS`.

Commands ran in WSL from the repository root, with
`SPK286_BUILD_DIR=$PWD/build/phase2.75-final` and `MAKEFLAGS=-j4`:

```text
make clean
make microcode microcode-check microcode-test
make lint
bash scripts/test_units.sh both spk286_microsequencer
bash scripts/test_units.sh both spk286_microcode_rom
bash scripts/test_units.sh both spk286_decoder
bash scripts/test_units.sh both spk286_microcode_execution
bash scripts/test_units.sh both spk286_execution
make waveform iverilog
python3 -m unittest discover -s tests -p 'test_*.py' -v
make state-smoke
make synth-check
make regression
make singlestep-smoke
python3 -m tools.run_singlestep --sample 100
make singlestep-mov
make verify-failure data-smoke
python3 -m tools.run_singlestep --opcode B8 --index 0 --trace build/phase2.75-final/traces/microcode-B8-0.vcd
python3 -m tools.microcode.compile_microcode --pc 0x1
make microcode-check
git diff --exit-code -- microcode/generated
```

| Final check | Result |
| --- | --- |
| Generation/consistency | PASS, all five committed artifacts byte-identical |
| Independent compiler tests | 31/31 PASS |
| All Python tests | 42/42 PASS |
| Directed RTL benches | 10/10 Verilator, 10/10 Icarus PASS |
| New control/CPU counters | 37 sequencer, 4 ROM, 256 decoder, 5,380 CPU checks; 375 underfill cycles |
| Reset smoke | PASS in both simulators, FFFFF0 |
| State vectors | 4 initialization/fetch cases PASS |
| Verilator --Wall lint | PASS for integrated core and all components |
| Yosys | Nine structural scopes plus full generic synthesis PASS, zero reported problems |
| Normal complete regression | PASS |
| B8..BF smoke | 80/80, zero failures |
| B8..BF sample | 800/800, zero failures |
| B8..BF full | 40,000/40,000, zero failures |
| Exact case replay | B8 index 0 PASS with VCD |
| Waveform/source mapping | All three generated PCs observed; PC 1 maps to data_move.mc:7, TMP0 -> DST |
| Negative reset verification | Both simulators reject the deliberately wrong expectation |
| Data-loader smoke | PASS, one parsed/selected fixture, execution correctly reported deferred |

Full SingleStep accounting: 40,000 discovered; 0 revoked; 0 selection-skipped;
40,000 executed; 40,000 passed; 0 failed. Every opcode contributes 5,000/5,000.
The full clean run took **5.324 s**, or **7,513.3 tests/s**, versus the received
**5.048 s / 7,923.8 tests/s**. This observed rate is about 5% lower; timings
include runner parsing/batching/process startup and execution, exclude build,
and are subject to host variation. They are not historical CPU cycle rates.

Supplemental checks reproduced all five generated artifacts byte-for-byte
using Windows Python as well as WSL. An ignored, one-case diagnostic probe
deliberately inverted one expected bit in a separately generated batch; the
simulator returned status 1 and printed actual microstate. Neither the corpus
nor production expected-value preparation was modified. The normal exact case
replay passed, and its VCD showed micro-PC values 0, 1 and 2.

Final lint/RTL/synthesis logs contain no meaningful warnings or unexplained
failures. Nested Make reported unavailable jobserver tokens and fell back to
serial compilation; this affects build parallelism only. The deliberate
negative-test failures are confined to their diagnostic logs. Generic mapped
cell counts match the earlier 4,707-cell result; Quartus/Fmax are not claimed.

Logs, generated Windows comparison output, batches and traces remain ignored
under `build/phase2.75-final/`. No temporary compiler/cache/VCD/FST files are
tracked. The external corpus remains clean and pinned at the same revision.
The final tracked change after validation is this handoff documentation.

## Known limits and deferred work

- Only B8..BF MOV executes; the ISA was not expanded.
- Debug labels exist; executable branches/conditions/calls do not.
- One temporary and three functional operations; additional operands/ALU/bus
  controls will extend the compiler/executor when required by a functional phase.
- No ModR/M, EA, data-memory operand transactions, stack/control flow, protected
  mode, exceptions, interrupts or I/O were added.
- The inherited bus remains a normalized fetch transaction interface, not
  native Ts/Tc/Ti or HOLD/HLDA/LOCK/INTA implementation.
- SingleStep acceptance compares architectural register/sparse-RAM state;
  bus/cycle trace equivalence and historical timing remain unverified.
- The sparse adapter's unspecified reads return zero; memory operand work must
  establish its own explicit access policy.
- Quartus and physical FPGA validation were unnecessary for the portable ROM
  question and were not run. No resource inference or frequency claim is made.
- Public package constants locally suppress only UNUSEDPARAM for isolated
  consumers; meaningful RTL lint warnings remain fatal (D-012).

## Source tree changes

New source/compiler/generated files are under `microcode/` and `tools/microcode/`.
New RTL: `spk286_decoder.sv`, `spk286_microsequencer.sv`,
`spk286_micro_executor.sv`; `spk286.sv` integrates them. Four new directed benches
and compiler tests cover the new contracts. Existing state/prefetch/fetch RTL
and historical tests remain intact. Scripts, Make targets and CI enforce the
ordered source manifest and consistency; the SingleStep harness adds numeric
debug diagnostics. README, architecture/state/verification/status documents,
microcode README, source notes and decisions D-012/D-013 explain the result.

## Recommended Phase 3 Starting Point

Add ModR/M decode, 16-bit effective-address generation and reusable register/
memory operand services, then validate `89 /r` and `8B /r`. Begin with all
register-direct forms; add a separate BIU data request/completion path before
memory forms, preserving READY and prefetch arbitration.

The intended future microprograms are `READ_RM16 -> TMP0; TMP0 -> REG; END`
and `REG -> TMP0; WRITE_RM16 TMP0; END`. These operations are not supported yet.
Extend decoder metadata, compiler validation/encoding and the functional
executor while keeping the existing microsequencer's stall/completion/END
contract. Verify displacement widths, all 16-bit EA forms and BP/SS defaults
with Intel evidence, directed tests and the relevant full SingleStep families.
