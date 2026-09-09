# Verification Workflow

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

## 2026-09-09 closure review status

The [Phase 7 closure dossier](PHASE7_CLOSURE_20260909.md) records the separate
independent review, exact corrected inputs, new commands/results and retained
historical evidence. The isolated combined candidate adds temporal REP INS
stimulus and its intended stale-input mutant; production source remains at the
delivered arithmetic increment. Complete Phase 7 admission is still blocked by
REP initial-zero-count event ordering and one incomplete E7 capture. Diagnostic
partial E7 success is not whole-file acceptance. The strict evidence gates and
all three inherited D-026 architectural questions remain explicit.

## Phase 0 executable proof

The same logical reset test is available through two independent simulators:

```bash
make lint
make test
make regression
```

`make test` runs Verilator lint, a compiled C++ Verilator harness, the Icarus
testbench, and Python unit tests for the SingleStep data reader. `make
regression` adds a Yosys synthesis sanity check. A test failure propagates a
non-zero exit status.

`make verify-failure` runs both simulators with an intentionally incorrect
expected fetch address and succeeds only when both commands reject it with a
non-zero status. The incorrect expectation is never part of the normal test.

The smoke test proves reset state, hidden CS base, the first physical fetch,
80286 `CODE` bus status, upper-byte selection, and READY completion. It does
not prove instruction execution.

## Phase 1 directed RTL tests

`make unit` runs shared SystemVerilog testbenches through Verilator's compiled
timing engine and independently through Icarus. The original C++ Verilator
reset harness remains in the regression. The generated package locally permits
unused public constants in isolated consumers (D-012); all other relevant
warnings remain fatal. `make lint` uses `--Wall` for every implemented module.

Run one focused test with, for example:

```bash
bash scripts/test_units.sh both spk286_registers
bash scripts/test_units.sh both spk286_segments
bash scripts/test_units.sh both spk286_fetch
bash scripts/test_units.sh both spk286_core
```

The first argument may also be `verilator` or `iverilog`. Tests cover register
state, every ordinary real-mode paragraph value for all four segments, cached
address formation, fetch waits/lanes/backpressure/restarts and integrated state
commits. These are datapath tests, not instruction execution results. Yosys
checks every independent module and the integrated hierarchy with `check -assert`.

## Phase 2 prefetch and execution tests

The directed unit set includes `spk286_prefetch_queue_tb`, which checks
empty/full behavior, ordered byte insertion and consumption, pointer wrap,
simultaneous refill/consume, flush and reset. It runs through both Verilator and
Icarus.

`spk286_execution_tb` is an end-to-end synthetic-memory test. It executes one
single `MOV r16, imm16`, redirects while prefetched bytes are present, executes
the remaining seven register destinations, and then presents an unsupported
opcode. The bus model inserts deterministic READY stalls on every transaction.
The test compares final GPRs, IP, FLAGS, unsupported-opcode indication and
queue bounds in both simulators.

The supported Phase 2 instruction is:

```text
B8 + rw    MOV reg16, imm16
```

The opcode's low three bits select AX/CX/DX/BX/SP/BP/SI/DI. The immediate is
consumed as low byte then high byte; the frontend writes `{high, low}` and does
not write FLAGS.

## Phase 2.75 compiler and control tests

`make microcode-test` runs Python compiler/ROM tests independently of simulation.
Every build entry point first checks the committed artifacts against generated
bytes. `make regression` runs ten directed RTL benches in both simulators,
reset smoke, Python/vector tests, available-corpus SingleStep smoke, independent
Yosys component checks and full generic synthesis of the integrated core.

The additional directed benches are:

- `spk286_microsequencer_tb`: nonzero entry load, sequential progression,
  dependency/pause hold and resume, END, exactly-once retirement, next decode,
  reset/cancel and invalid-entry/ROM/fallthrough protection.
- `spk286_microcode_rom_tb`: semantic MOV sequence relative to its generated
  entry symbol and invalid unused addresses.
- `spk286_decoder_tb`: all 256 opcodes and the eight destination encodings
  sharing one entry.
- `spk286_microcode_execution_tb`: 48 directed MOV combinations (eight
  destinations, 0000/FFFF/12A5 immediates, even/odd starts), exact state at each
  retirement in an eight-MOV stream, full FLAGS/segment/GPR preservation,
  queue underfill, READY delays, pauses, malformed controls, reset and redirect
  cancellation at all micro-operation boundaries, restart and unsupported bytes.

Run focused benches with `bash scripts/test_units.sh both <name>`.
The inherited execution/queue/fetch tests remain unchanged and run through the
new production microcode path. `make singlestep-mov` remains the separate full
40,000-case migration gate. This is architectural evidence, not cycle accuracy.

The pre-Phase 3 audit adds adversarial Python checks for malformed corpus input,
unsupported state/prefixes, duplicate identities, revocation/selection accounting,
and inconsistent simulator summaries/status. `make singlestep-audit` independently
cross-checks the complete external corpus against its upstream parser and proves
17 deliberately faulty batches fail in the real RTL executable. It is opt-in,
requires the external corpus/parser, and preserves the ordinary regression path.

## Phase 3 operand and bus tests

The directed suite now contains 17 shared benches, each executed by Verilator
and Icarus. Phase 3 and its independent architectural review cover the reusable
components and complete MOV path:

| Bench | Directed coverage per simulator |
| --- | --- |
| `spk286_modrm` | All 256 encoded bytes |
| `spk286_effective_address` | 25,056 independent EA/default-segment checks |
| `spk286_operand_decode` | 1,280 contexts plus partial cancellation; 12,099 checks |
| `spk286_biu` | 110 word/reset/cancel cases plus arbitration; 2,419 checks |
| `spk286_mov_operands` | 128 register pairs, 480 memory/boundary cases, four- and eight-instruction streams; 47,468 checks |
| `spk286_operand_lifecycle` | 46 lifecycle cases including coincident READY/redirect and register writeback/END; 2,440 checks |
| `spk286_operand_service` | Direct logical API, independent REG/RM direction, repeated context, response backpressure and whole-word limits; 206 checks |

Run any row with `bash scripts/test_units.sh both <bench>`. Tests distinguish
DS/SS bases, every addressing/displacement mode, signed disp8, disp16 extremes,
16-bit wrap, physical carry into A20, code/data alignment, unchanged state,
word limits, READY on both odd subcycles, held responses and no duplicate writes.
The MOV integration bench observes 908 data wait cycles and 1,559 cycles with
data traffic and queued instruction bytes; a continuous four-instruction stream
checks order, IP, single retirement and absence of ordinary data-access flush.
Lifecycle tests cover partially consumed bytes, first/second data cycles and
held completions under pause, malformed controls, redirect and reset.

The review adds an eight-instruction stream that changes BX, SI and BP before
using wrapped DS and signed BP+SI SS addresses, loads into an address register,
then returns to direct DS addressing. Each retirement has an independent state
and transaction-count check. The operand-service bench drives the existing API
without a decoder, MOV controller, executor temporary or new instruction.

`make phase3-boundary-audit` runs two pristine Icarus benches and compiles four
isolated RTL mutants in the ignored build directory. It requires the intended
assertion to reject lost code ownership, cancel/READY response leakage, duplicate
operand requests and truncated word-limit arithmetic. A compilation failure
cannot count as a rejected functional mutant. Production source bytes are
checked before and after; generated artifacts and corpus expectations are never
modified. This audit is also part of `make phase3-check`.

Compiler tests add format/encoding 2, context/TMP0 lifetime and independent
active ROM contract checks while preserving the original format 1 fixture.
Python runner tests exercise all 512 opcode/ModR/M length combinations and
explicit disjoint scope accounting. SingleStep audit adds real executable
memory-read/write fault injection; all ten corpus files are parser-cross-checked.

For final validation, use a clean source tree and a previously unused build
directory. Preserve earlier logs; concurrent jobs must not share a build path.

```bash
make singlestep-fetch
make mcl86-fetch  # If the pinned audit references are not already cached.
SPK286_BUILD_DIR="$PWD/build/phase3-final" make phase3-check
```

The script requires the pinned clean corpus and runs deterministic regeneration,
consistency, compiler/audit and all Python tests, inherited MCL86 comparison,
lint, all dual-simulator benches, waveform/state smoke, complete supported 89/8B
and B8..BF families, synthesis, regression, adversarial audits and traced memory
replays. All failures propagate. Full per-opcode reports are preserved before
later smoke/replay. CI also fetches and executes the full supported hardware
families and adversarial audit; new instruction forms must extend this gate.

## Waveforms

Waveforms are opt-in:

```bash
make waveform
gtkwave build/traces/reset_verilator.vcd
```

The Verilator harness writes VCD only when `--trace` is requested. Large future
regressions should retain traces only for reproducible failures.

## SingleStep data path

`tools/singlestep.py` reads JSON, JSONL, and MOO 1.0/1.1 common chunks into a
normalized `SingleStepCase`. It preserves test indexes, instruction bytes,
initial/final state, cycle fields, exception metadata, hashes, and revocation
lists. `tools/run_tests.py` currently validates and selects data only; the RTL
instruction-execution adapter is `tools/run_singlestep.py`, described in
[SINGLESTEP_INTEGRATION.md](SINGLESTEP_INTEGRATION.md). Bus/cycle comparison
remains deferred. `make state-smoke` maps the existing fixture and three
directed state vectors into normal RTL commit ports, then compares all GPRs,
IP/FLAGS, visible segments, hidden caches and the first fetch. It follows the
ordinary CS-reload entry convention and never deposits hidden state directly.

This small adapter runs through the existing C++ Verilator executable; the
same RTL mechanisms are tested independently in Icarus directed tests. It
reports `instructions_executed=0` and does not compare the instruction's final
state. Cases must supply canonical storage FLAGS, an empty queue, ordinary
real-mode state and the first fetched bytes. Expected/actual snapshots and
driver stderr are retained under `build/state-vectors/<source-stem>/`.

The external corpus is configured with `SPK286_SINGLESTEP_PATH` or an explicit
`--source` path. It is not vendored into this repository.

## Evidence policy

Functional, bus, and cycle results must be reported separately. A BIOS or
MiSTer success cannot override a failing architectural test. If simulators
disagree, reduce the case and inspect language semantics, initialization,
assignment ordering, and traces before changing RTL or expectations.

## Gate completo de Phase 2.80

```bash
make mcl86-fetch
make singlestep-fetch  # Sólo si no existe ya el corpus fijado.
SPK286_BUILD_DIR="$PWD/build/phase2.80" make phase2.80-check
```

Para una validación desde cero, utilizar un checkout limpio y un directorio
de build todavía inexistente. No es necesario borrar resultados anteriores.
El script exige el corpus limpio en el commit contractual y los ocho ficheros
B8..BF; no admite el skip opcional de la regresión cotidiana.

Se ejecutan tests MCL86 offline, reconstrucción pública, generación/consistencia
y auditoría de ROM SPK286, todos los tests Python, lint, diez bancos RTL en
ambos simuladores, reset/waveform, cuatro vectores de estado, SingleStep smoke,
sample de 100 por opcode, familia completa, nueve ámbitos Yosys y síntesis
genérica, regresión completa, pruebas negativas, data-loader y replay B8 con VCD.
Los fallos cortan el script mediante `set -euo pipefail`.

`make regression` incluye los tests sintéticos MCL86 y la auditoría de SPK286
sin añadir una dependencia de red. La comparación contra las referencias
públicas es otro gate obligatorio en CI (`make mcl86-fetch mcl86-check`) y en
`phase2.80-check`. Una caché ausente/corrupta falla; nunca se normaliza el
original antes de validar su SHA-256.

## Phase 4 release validation

`make phase4-check` requires all 50 admitted opcode/form files at the pinned
clean corpus commit. It runs the entire reviewed phase3-check, then the 400-case
ALU smoke, all admitted ALU cases, isolated ALU mutations and final generated
consistency/Git checks. Use a previously absent SPK286_BUILD_DIR for release.
All 17 inherited directed benches remain; three new shared benches bring the
suite to 20 benches per simulator:

- spk286_alu: 29,912 deterministic vectors from an independent mathematical
  oracle, including 14 edge values, carry/borrow, every low-byte parity,
  exhaustive nibble combinations and 20,000 seeded random cases.
- spk286_alu_instructions: 10,240 cases across eight families/five forms,
  register pairs, every EA form, distinct DS/SS, disp8/disp16, signed immediates,
  odd/aligned words, READY, segment-boundary blocking, exact GPR/FLAGS/IP/RAM,
  neighbors, transaction counts, no CMP writes and immediate starvation.
- spk286_alu_lifecycle: pause, malformed controls, redirect with/without READY,
  reset at operand/result/FLAGS/END and partial-immediate boundaries, plus eight
  consecutive dependent instructions mixing arithmetic, logic, CMP and MOV.

`make alu-audit` compiles copied inputs and rejects eight intended mutants:
CF inversion, word parity, missing OF/AF, reversed subtraction, missing carry-in,
CMP writeback and all-FLAGS updates. Two pristine benches must pass first;
compile failures cannot count as mutation rejection. Source SHA-256 values
are checked after execution. The four reviewed Phase 3 mutants, two pristine
benches and 20 comparator-fault probes remain mandatory.

The compiler retains frozen format-1/format-2 contracts and adds an independent
format-3 contract plus negative temporary/context/result/FLAGS-order tests.
The 80286 parser audit now covers all 250,000 discovered records, including
masks, prefixes and exceptions, while preserving all inherited probes.
Masks remain upstream values. Logical CF/OF are checked by the independent
oracle/directed tests because the upstream F7EE mask omits them alongside AF.

The pinned upstream moo2json converter does not emit RMSK. The audit compares
its complete represented state and cycles, then independently decodes each
binary RMSK using the MOO 1.1 field layout and verifies every production mask.
A missing/changed/extra mask or other state field fails; no mask or expected
architectural value is weakened. This also covers all excluded records.

## Phase 5 stack/control gate

Run `make phase5-check` with a fresh `SPK286_BUILD_DIR` for release. It preserves
the complete `phase4-check`, including double deterministic generation,
compiler/ROM and MCL86 audits, Python tests, lint, all benches in both
simulators, full inherited hardware families, mapped synthesis, regression,
failure propagation, parser/comparator mutations and operand/ALU mutations.
It then requires all 47 new hardware files, complete stack/control execution,
twelve isolated stack/control RTL mutants, and generated-artifact consistency.
No missing corpus or selected case is a successful skip.

`tools/stack_control_reference.py` is independent of production decode,
compiler and adapter logic. It models PUSH/POP ordering and boundaries, next-IP
relative arithmetic, CALL/RET, all conditions and LOOP/JCXZ. Directed CPU
vectors cover 9,128 cases, all 512 condition/FLAGS combinations, all GPR/EA
forms, distinct DS/SS, overlapping operands/stack, SP wrap and invalid words,
odd/even bus lanes and READY waits 0..4. The bench checks exact whole GPR/FLAGS,
CS/segment preservation, sparse memory plus neighbors, ordered physical
transactions, IP, taken/not-taken flush counts and single retirement.

The stack lifecycle bench covers 180 pause/malformed-control/cancel/reset
scenarios at opcode, partial immediate, request, each odd subcycle, held
response, target/redirect and END boundaries. It additionally covers twelve
unsupported group forms with cancellation recovery, full six-byte queues,
outstanding stale code fetches, repeated same-address redirects and twenty
uninterrupted nested CALL/RET/PUSH/POP/LOOP/Jcc instructions with poisoned
wrong-path register writes. Accepted canceled words must drain exactly once;
reset follows the existing physical-abort contract.

The twelve RTL mutants change SP arithmetic, pushed source, POP SP order, SS
selection, CALL return-IP source, relative target, signed condition, LOOP,
JCXZ, early SP commit, prefetch flush and duplicate retirement.
Each must compile and fail the intended semantic assertion, with pristine
positive controls and unchanged production source hashes. Parser/comparator
audit now includes 67 rejected copied-batch faults and 51 pristine executions.
This is architectural and directed bus validation, not historical timing or
captured physical-cycle equivalence.

## Phase 6 event release gate

`make phase6-check` runs the complete inherited gate followed by full exception-
aware hardware execution, event mutation testing and another broad regression.
It requires a fresh output directory, pinned clean corpus, all 106 source files,
deterministic double generation, frozen formats 1–4 and active format 5 contracts,
full parser/RMSK/EXCP agreement, preserved 24/67 inherited negative probes,
new event probes, both simulators, MCL86, failure propagation, structural/mapped
Yosys checks and invariant validation-input hashes.

`event_reference.py` models ordered frame/return effects and an independent
instruction-level interruptibility table. `event_vectors.py` covers every vector,
SP 0–7, limits, both word alignments and frame/IVT aliasing. `event_streams.py`
generates 96 reproducible dependent histories with nested handlers, saved IP/FLAGS
modification and INTR/NMI/TF competition. Lifecycle tests perturb entry and IRET
at micro-operation, physical-half and held-response boundaries. Bounded READY is
a liveness assumption; an indefinitely low READY is an allowed wait.
The 463 lifecycle scenarios also sweep all 256 INTA vectors with READY-low data
noise and verify LOCK release and partial frame effects after failed INTR entry.

The full cohort must remain 440,574 inherited normal + 1,423 inherited faults +
32,052 new-family cases. Reports retain all 43,951 prefix exclusions individually;
selected failures, skips, revocations and exception exclusions must be zero.
`tools.phase6_reports` rejects missing, duplicate, malformed or inconsistent
accounting. Full reports are copied before regression smoke overwrites work files.

Executable checks cannot settle ambiguous 286 behavior. `phase6_evidence.json`
therefore blocks `PHASE6_VALIDATION_PASS` until each required primary/physical
decision is resolved. See [review](PHASE6_ARCHITECTURAL_REVIEW.md) and
[run evidence](PHASE6_HANDOFF.md). No cycle-accurate timing claim follows from
functional corpus results or independently parsed captured bus records.

## Phase 6 evidence-closure preparation

`python3 -m unittest tests.test_phase6_probes -v` checks NASM encodings, two
reproducible payload builds, 378 executions of generated bytes under 18
illustrative hypothetical policies, and provenance/parser rejection paths.
NASM/NDISASM are mandatory for these tests and declared by CI/bootstrap. Missing
physical captures are not skips or passes: `research.phase6_probes.results
--require-physical` rejects simulation and NOT-RUN records. Structural validity
still requires independent inspection of actual physical traces and timing.

See [protocol](PHASE6_CAPTURE_PROTOCOL.md), [closure dossier](PHASE6_EVIDENCE_CLOSURE.md)
and the latest [handoff](PHASE6_HANDOFF.md) for executed checks, source hashes,
native trigger limitations and preserved original evidence. The three decisions
remain unresolved, so no Phase 6 release-pass marker is claimed. New probe runs
are synthetic and never added to the 474,049-case physical cohort.

## Provisional development gate (D-026, 2026-09-08)

`make phase6-exec-check` runs the same complete executable implementation as
`make phase6-check` in a previously absent build directory. Both retain input
fingerprints, every inherited check, all 474,049 physical cases, mutations,
trace checks and final regression. `tools.phase6_cohort` freezes the 106-family
report contract independently of later decoder/adapter expansion.

The development check also requires a well-formed evidence file with exactly
the three named policies and references. It prints the actual pending set and
`PHASE6_EXECUTABLE_VALIDATION_PASS` only after executable validation succeeds.
The strict entry then runs the unchanged `tools.phase6_evidence`; only strict
success may print `PHASE6_VALIDATION_PASS`. Tests execute both shell compositions
and prove inherited, report, mutation, trace, regression, consistency and evidence
errors propagate. Missing families, malformed JSON, duplicate/new decisions or
changed candidate policies are not the authorized pending status.

CI runs executable validation and a separate exact classification of the strict
evidence result. `PHASE6_ARCHITECTURAL_EVIDENCE_PENDING` is an explicit pending
architectural result, not an architectural approval or a suppressed test failure.

## Phase 7 byte/prefix increment

`make phase7-byte-prefix-check` is a bounded development gate, separate from
the unfinished full Phase 7 gate. It requires an absent build directory, captures
all executable inputs and the complete form inventory, runs the full inherited
executable gate, then runs all 150 implemented physical opcode files with prefixes
and exceptions enabled. `tools.phase7_reports` verifies source Git blobs, unique
index/hash identities, identity-file hashes and disjoint totals: 474,049 legacy,
43,951 readmitted legacy prefixes and 219,998 new-form cases. The two upstream
revocations remain separate. No selection/prefix/exception skip or selected
failure is accepted. Historical unprefixed reports remain frozen and separate.

New directed tests exercise all byte ALU input pairs/carry combinations, encoded
byte aliases and preserved halves, byte/word boundary and physical lane behavior,
byte CPU forms, prefix lifetime, instruction length, first-prefix event restart
and LOCK/HOLD ownership. Both simulators run the same benches. Seven new copied
RTL mutants must fail their intended assertions, with pristine controls passing;
all inherited mutants and parser/comparator negatives remain mandatory.

The word-limit mutation anchor was updated for the width-dependent expression
after the first fresh integrated run stopped at that audit. The mutation still
truncates the widened limit sum to 16 bits, and the unchanged word-boundary
assertion rejects it. That interrupted gate is retained as a failure; a new
complete run is required for the repaired input set.

Scalar I/O prototype evidence is separately identified in
[PHASE7_IO_CAPTURE_REVIEW](PHASE7_IO_CAPTURE_REVIEW.md). Directed I/O and seven
full-family successes do not constitute all eight families or full regression.
No hardware cycle-accuracy claim follows from these functional/transaction
checks. [PHASE7_HANDOFF](PHASE7_HANDOFF.md) records final commands, exit codes,
hashes, resource deltas and missing work.

The directed F2/F3 scalar probes exercise accumulated context, length and event
lifetime; they do not provide physical REP iteration evidence. Repeated-string
forms remain outside the implemented registry. The current normalized LOCK
contract is functional ownership, not a historical native-pin waveform claim.

The second fresh run stopped at the stack-segment mutation anchor, whose
non-stack branch now includes the segment override. Its replacement preserves
that branch and still forces stack accesses through DS instead of SS; the
original ordered-address assertion remains unchanged.
`tests.test_mutation_anchors` now checks every one of the 53 active mutation
anchors and bench paths early, before expensive simulator builds. Intended
functional rejection is still required from every actual copied-RTL audit.

The third fresh gate passed the complete 737,998-case corpus but failed the
prefix comparator audit: selecting a MOV memory probe by byte[1] misread a
prefixed register-only instruction. Probe selection now requires captured
MEMR/MEMW traffic and no exception, so IVT/frame traffic cannot stand in for a
real operand. All physical cases are still checked; only the representative
negative-probe selection changed. The full prefix parser/comparator audit passes
with this correction, and a unit test covers prefixed registers, real operands
and exception traffic.

A separate clean-acquisition check found that the downloader still enumerated
only the 106 old files. It now derives requests from the active supported set,
with an explicit cross-module test. A new checkout from the original public
remote contains exactly 150 matching pinned blobs and a clean Git status. The
next complete gate uses that fresh corpus rather than the previously expanded
working cache. Host C++ compilation may use SPK286_BUILD_JOBS; simulation
semantics and all required checks are unchanged.

## Scalar increment gate

`SPK286_BUILD_DIR="$PWD/build/a-new-scalar-run" make phase7-scalar-check` runs
the complete byte/prefix gate (including inherited executable validation), all
31 added scalar files, strict cross-cohort identity accounting, seven new scalar
mutants and final input consistency. The byte and scalar cohorts contain
737,998 and 63,000 disjoint cases respectively. The marker is deliberately
PHASE7_SCALAR_VALIDATION_PASS; it cannot assert complete Phase 7 readiness.

The current ordinary suite contains parser/report/gate negatives; compiler
fixtures preserve formats 1–6 and independently specify format 7. Two added
benches exercise TEST write suppression/width/EA/faults and scalar register/flag
preservation under READY, prefixes and pause at retirement. Direct-scalar FLAGS
cases include IF/TF set; they inspect the scalar retirement boundary and do not
adjudicate the inherited event-policy questions. Source-fingerprinted mutation
audits require pristine success and the intended semantic assertion failure;
compiler errors and timeouts are never mutation kills.

## Phase 7 shift/rotate increment

`SPK286_BUILD_DIR="$PWD/build/a-new-shift-run" make phase7-shift-check` invokes
the complete scalar gate, all 42 additional physical files, strict disjoint
identity accounting and nine new isolated-copy RTL mutations. All 34 benches
run in both simulators. The fresh candidate gate requires 189 ordinary Python
tests, 67 compiler tests, lint, inherited parser/comparator/event checks, smoke,
synthesis and regression. Its marker cannot grant complete Phase 7 approval.

The new arithmetic bench checks 154,112 independent closed-form vectors, count
boundaries, captured inputs, pauses during calculation, response backpressure,
reset and cancellation. The CPU bench checks 12,222 cases, CL/CX aliases, all
ModR/M modes, byte/word memory limits, READY, immediate starvation and zero-count
reads without writes. Physical reports require all 210,000 records with original
bytes/masks, no exclusions/failures and no identities shared with the 800,998
prior cases. See PHASE7_HANDOFF.md for actual integrated-gate status.

## Phase 7 data-transfer increment

`SPK286_BUILD_DIR="$PWD/build/a-new-data-run" make phase7-data-check` runs the
complete shift gate, all sixteen added physical files, strict cross-cohort
identity accounting and eight isolated-copy RTL mutations. The combined
requirement is 1,058,998 distinct records with no selected skips or failures.
All 36 benches run in both simulators; compiler, lint, parser/comparator,
event/stream, smoke, synthesis and regression checks remain mandatory.

The 5,690-case CPU bench covers aliases, all EA forms, direct-offset byte
acquisition, LEA faults, unsigned XLAT/wrap and implicit LOCK/HOLD. The 55-case
lifecycle bench covers pause/cancel/reset, both odd exchange write halves,
separate memory/register commits and a dependent mixed stream. Eight defects
must fail precise semantic assertions after pristine controls pass. Complete
Phase 7 approval is not provided by the bounded data marker.

## Phase 7 unary and decoded dispatch increment

`SPK286_BUILD_DIR="$PWD/build/a-new-unary-run" make phase7-unary-check` runs the
complete data gate, eight full new files, strict disjoint identity accounting,
ten new isolated-copy RTL mutants and final input consistency. The complete
bounded requirement is 1,098,998 records with no selected skips/failures, all
38 benches in both simulators, compiler/lint, smoke, inherited event/stream and
comparator checks, synthesis and regression. Its marker is not complete Phase 7.

The independent CPU suite has 10,832 cases; the 70-case lifecycle suite covers
fifteen dispatch/operand/commit boundaries, invalid FE forms and a dependent
mixed stream. Existing generic sequencer and operand-decoder units now test
branch validity/range, retained entry, cached EA reuse, pauses and cancellation.
Four pristine benches precede ten intended semantic mutation failures. Changes
to three audit reasons reflect earlier actual FLAGS/memory assertions; no CPU
expectation was weakened.

The fresh unary retry passed all requirements on 228 unchanged executable
inputs. The retained first gate exposed an obsolete invalid-FF test selection;
the supported INC/DEC encodings are now tested by their dedicated suites, while
FF /3, /5 and /7 retain the exact negative assertions. The failed gate and both
reproduction/fix runs remain in the validation archive. Exact hashes and
measured results are in phase7_unary_validation.json and PHASE7_HANDOFF.md.

## Phase 7 decimal/radix adjustment increment

`SPK286_BUILD_DIR="$PWD/build/a-new-adjust-run" make phase7-adjust-check` runs
all inherited unary checks, six full new physical files, strict disjoint
accounting and twelve new RTL mutation checks. The fresh integrated gate passed
1,128,998 physical records, 41 benches in both simulators, 207 ordinary tests,
76 compiler tests and 99 intended mutants. Lint, smoke, full parser/comparator
checks, synthesis, regression and all 242 unchanged input fingerprints passed.

The pure arithmetic bench has 352,256 independent vectors and 4,740,163 checks;
the CPU bench covers 8,184 normal cases and 2,044 immediate stalls. The 157-case
lifecycle bench checks 9,075 invariants including full odd/even #DE frames,
length faults, cancellation and pending-event competition. Exact actual
integrated-gate results are recorded in phase7_adjust_validation.json and PHASE7_HANDOFF.md.

## Phase 7 segment-transfer increment

`SPK286_BUILD_DIR="$PWD/build/a-new-segment-run" make phase7-segment-check`
requires every inherited adjustment check, all nine full physical files,
disjoint accounting, ten new semantic mutants and unchanged input fingerprints.
The prospective total is 1,173,998 physical records, 43 dual-simulator benches,
212 ordinary and 78 compiler tests, and 109 intended RTL mutants. The 4,800-case
CPU bench checks exact selectors/caches and 354,661 invariants; the 42-case
lifecycle bench checks 3,589 invariants around SS inhibition and data through
new segment caches. Actual integrated results belong to PHASE7_HANDOFF.md.

## Phase 7 combined segment and stack/frame gate

`SPK286_BUILD_DIR="$PWD/build/a-new-frame-run" make phase7-stack-frame-check`
requires every inherited segment/adjustment check, the five full new physical
files, exact upstream-revocation accounting, fifteen new intended RTL faults and
unchanged input fingerprints. The candidate includes 46 benches in both
simulators, 220 ordinary and 80 compiler tests, and 124 intended RTL faults.
The fresh combined gate passed all 1,198,997 disjoint physical cases and all
267 input checks. The interrupted segment-only run does not supply a success
result. Actual counts, log hash and archive are recorded in
[phase7_stack_frame_validation.json](phase7_stack_frame_validation.json).

## Phase 7 far pointer/control candidate gate

`SPK286_BUILD_DIR="$PWD/build/a-new-far-run" make phase7-far-check` requires the
complete inherited stack/frame gate, all eight physical files, strict disjoint
identity accounting, twelve new intended RTL defects and unchanged inputs.
The candidate contains 48 dual-simulator benches, 226 ordinary tests, 82 compiler
tests and 136 total intended mutants. The prospective physical total is
1,238,997. Prototype physical, directed, lifecycle, retained-event and synthesis
checks passed; the fresh integrated gate is pending and must not be inferred
from the separate prototype summary.

## Completed far-control executable gate — 2026-09-09

All 1,238,997 disjoint physical cases, 48 benches in both simulators, 136 RTL
mutants and synthesis passed on the unchanged integrated candidate. See
[phase7_far_validation.json](phase7_far_validation.json) for exact source hashes,
actual execution and the verified archive. Earlier pending-gate notes above
record the preparation state. Independent architectural review and full Phase 7
remain pending; a self-review does not close that requirement.

## Completed arithmetic executable gate - 2026-09-09

All 1,288,997 disjoint physical records, 51 benches in both simulators, 153
intended RTL faults, strict adapter negatives, lint and synthesis passed on
the unchanged integrated candidate. See phase7_arithmetic_validation.json for
the exact 295 inputs, real command results and verified archive. The previous
byte-IDIV failures are resolved under D-036. Complete Phase 7 and independent
architectural review remain pending; this is an implementation self-review.
