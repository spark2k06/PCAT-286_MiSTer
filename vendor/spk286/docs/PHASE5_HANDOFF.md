# Phase 5 handoff - stack and near control flow

Validation status: **PHASE5_VALIDATION_PASS**. Phase 5 is complete and ready
for Phase 6 to build on these primitives. Phase 6 has not been started.

## Repository state

- Branch: `codex/phase5-stack-control-flow`.
- Verified Phase 4 base: `caffc0beeff15b35370c03c834f884cbf9407e26`.
- Phase 4 implementation ancestor: `011c75cc309f5ba0c328770b7add2dbd74415be5`.
- Reviewed Phase 3 base: `e040229ad4e363a833f9dc74b414cdb2217cf664`.
- Verified Phase 5 implementation: `b7a152709d82e614b0c1ff0e25432218360a7504`.
- Delivery commit: the commit containing this handoff; resolve its exact hash
  with `git log -1 --format=%H -- docs/PHASE5_HANDOFF.md`. It adds documentation
  and normalizes the source EOF without changing ROM/constants/listing/maps.
- Baseline reproduction: fresh `build/phase5-baseline`, complete
  `make phase4-check`, `PHASE4_VALIDATION_PASS` before implementation.

## Objective and exact scope

Reusable stack words and near control transfers on the reviewed operand/ALU
foundation. See [PHASE5_SCOPE.md](PHASE5_SCOPE.md) for evidence and roadmap
reconciliation. Implemented forms are unprefixed Real Mode words:

| Family | Encodings |
|---|---|
| PUSH | r16 50..57; imm16 68; sign-extended imm8 6A; r/m16 FF/6 |
| POP | r16 58..5F; r/m16 8F/0 |
| Near CALL | relative E8; register/memory indirect FF/2 |
| Near RET | C3; C2 with unsigned stack release |
| Near JMP | word E9; signed byte EB; register/memory indirect FF/4 |
| Jcc | all sixteen conditions 70..7F |
| Count branches | LOOPNE E0, LOOPE E1, LOOP E2, JCXZ E3 |

No segment-register stack forms, PUSHF/POPF, PUSHA/POPA, ENTER/LEAVE, far
transfers, prefixes, byte ALU, unary/shift/multiply/divide, interrupt/exception
entry, IRET, protection, historical timing modes or machine integration.

## Ownership and architectural behavior

The register file remains the sole SP owner. `spk286_stack` computes the word
offset and next SP; `spk286_operand` performs all logical register/memory
service, existing segmentation translates SS, and the unchanged BIU owns
physical READY/arbitration/odd splitting. There is no stack FSM or second bus.

PUSH captures its source first, requests SS:(SP-2), and commits SP only on
whole-word completion. PUSH SP stores original SP. POP reads SS:SP, captures
its word and commits SP+2 on logical completion, then writes its destination.
POP SP's loaded word therefore replaces the intermediate increment. POP memory
prechecks its full decoded destination before touching the stack. The existing
17-bit offset+1 check rejects overflowing words before a partial physical
access or SP/destination write. Exception delivery and shutdown remain deferred.
The cache currently supplies Real Mode FFFF limits; the standalone operand
bench additionally verifies short limits and validate-only semantics.

CALL pushes architectural next IP, never the speculative fetch cursor.
Indirect CALL captures its RM target before writing the stack, including SP
sources and overlapping source/stack memory. RET takes its target from the
popped word; C2 additionally adds the unsigned immediate to SP after the base
pop. Relative targets use next IP plus the signed byte or word displacement,
modulo 65536. Near transfers preserve all CS/cache state and FLAGS.

`spk286_condition` is a pure sixteen-condition evaluator of CF/PF/ZF/SF/OF.
Captured opcode/group metadata is interpreted in `spk286_control_decode`, not
in the microsequencer. LOOP variants decrement CX before the count/optional-ZF
predicate. JCXZ tests unmodified CX. These instructions preserve FLAGS.

The executor holds one instruction-local target and validity bit. Taken
REDIRECT synchronously writes IP, flushes all six queue bytes and restarts the
existing fetch owner. Outstanding old code responses drain/discard there;
END may retire while this drain is pending, with no wrong-path consumption.
Not-taken transfers leave the queue intact. Repeated/same-address redirects
use the same protocol. Internal redirect does not cancel its owning instruction;
its END retires exactly once. External debug redirects retain cancellation
semantics and latest-target precedence, clearing candidates and temporaries.

Pause and malformed control hold semantic state while accepted physical words
may finish. External cancellation drains an accepted word exactly once without
late SP/target updates. Earlier committed state/external writes are not rolled
back. Reset aborts the physical transaction as in the inherited contract.
This is not yet precise architectural exception delivery.

## Microcode and preserved modules

Compiler 4.0/format 4 adds controls 19..28 for destination validation, TMP0 signed
byte fetch, PUSH/POP, IP capture, relative/absolute targets, conditional redirect,
stack release and decoded count update. The active image has **20 entries,
97 words, seven-bit addresses and five-bit controls**. All first 45 words and
eight Phase 4 entries are preserved. Twelve new entries live in authoritative
`microcode/source/word_stack_control.mc`; generated artifacts were not edited.

The independent Phase 5 ROM fixture, emitted format version, canonical
round-trip and source maps complement frozen formats 1..3. Compiler validation
covers temporary/target lifetimes, prechecked POP destinations, terminal
redirects and existing explicit FLAGS disposition. No timing padding is added.

The microsequencer, BIU, fetch, prefetch queue, registers, segment-cache storage,
ALU, ModR/M/EA calculation and operand decoder RTL are unchanged. Integration,
form decode, executor functional controls and operand validate-only requests
are the production extension. Decisions D-020..D-022 document these boundaries.

## Validation and hardware accounting

The fresh final release run passed 226,594/226,594 new cases.
Every file has zero revocations and zero full-run
selection skips. Prefix and exception exclusions are disjoint and not passes.
The immutable hardware revision is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`.

| Opcode | Discovered | Prefix excluded | Exception excluded | Selected / executed / passed | Failed |
|---|---:|---:|---:|---:|---:|
| `50` | 5,000 | 142 | 0 | 4,858 | 0 |
| `51` | 5,000 | 143 | 0 | 4,857 | 0 |
| `52` | 5,000 | 142 | 0 | 4,858 | 0 |
| `53` | 5,000 | 143 | 0 | 4,857 | 0 |
| `54` | 5,000 | 142 | 0 | 4,858 | 0 |
| `55` | 5,000 | 144 | 0 | 4,856 | 0 |
| `56` | 5,000 | 142 | 0 | 4,858 | 0 |
| `57` | 5,000 | 142 | 0 | 4,858 | 0 |
| `58` | 5,000 | 141 | 0 | 4,859 | 0 |
| `59` | 5,000 | 141 | 0 | 4,859 | 0 |
| `5A` | 5,000 | 139 | 0 | 4,861 | 0 |
| `5B` | 5,000 | 142 | 0 | 4,858 | 0 |
| `5C` | 5,000 | 140 | 0 | 4,860 | 0 |
| `5D` | 5,000 | 140 | 0 | 4,860 | 0 |
| `5E` | 5,000 | 142 | 0 | 4,858 | 0 |
| `5F` | 5,000 | 141 | 0 | 4,859 | 0 |
| `68` | 5,000 | 145 | 0 | 4,855 | 0 |
| `6A` | 5,000 | 145 | 0 | 4,855 | 0 |
| `70` | 5,000 | 0 | 0 | 5,000 | 0 |
| `71` | 5,000 | 0 | 0 | 5,000 | 0 |
| `72` | 5,000 | 0 | 0 | 5,000 | 0 |
| `73` | 5,000 | 0 | 0 | 5,000 | 0 |
| `74` | 5,000 | 0 | 0 | 5,000 | 0 |
| `75` | 5,000 | 0 | 0 | 5,000 | 0 |
| `76` | 5,000 | 0 | 0 | 5,000 | 0 |
| `77` | 5,000 | 0 | 0 | 5,000 | 0 |
| `78` | 5,000 | 0 | 0 | 5,000 | 0 |
| `79` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7A` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7B` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7C` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7D` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7E` | 5,000 | 0 | 0 | 5,000 | 0 |
| `7F` | 5,000 | 0 | 0 | 5,000 | 0 |
| `8F` | 5,000 | 136 | 222 | 4,642 | 0 |
| `C2` | 5,000 | 152 | 24 | 4,824 | 0 |
| `C3` | 5,000 | 154 | 24 | 4,822 | 0 |
| `E0` | 5,000 | 151 | 0 | 4,849 | 0 |
| `E1` | 5,000 | 154 | 0 | 4,846 | 0 |
| `E2` | 5,000 | 152 | 0 | 4,848 | 0 |
| `E3` | 5,000 | 153 | 0 | 4,847 | 0 |
| `E8` | 5,000 | 153 | 0 | 4,847 | 0 |
| `E9` | 5,000 | 153 | 0 | 4,847 | 0 |
| `EB` | 5,000 | 1,036 | 0 | 3,964 | 0 |
| `FF.2` | 5,000 | 1,034 | 28 | 3,938 | 0 |
| `FF.4` | 5,000 | 1,034 | 28 | 3,938 | 0 |
| `FF.6` | 5,000 | 1,034 | 28 | 3,938 | 0 |

New total: 235,000 discovered; 8,052 prefix exclusions; 354 exception exclusions;
226,594 selected/executed/passed; zero failures, revoked or selection-skipped.
The inherited release run passed 213,980/213,980, for a combined
**440,574/440,574** admitted cases. All 97 opcode reports are preserved by the
gate; their 485,000 discovered cases reconcile exactly with 43,003 prefix and
1,423 exception exclusions, zero revoked, zero selected skips and zero failures.

### Final reproduction and checks

On WSL Ubuntu-24.04, from a previously absent `build/phase5-final` directory:

```sh
SPK286_BUILD_DIR="$PWD/build/phase5-final" make phase5-check
```

The process exited zero and emitted all three Phase 3/4/5 validation markers.
A final source-EOF formatting cleanup changes only the source SHA256 sidecar;
the ROM, constants, listing and source map remain byte-identical. The full gate
passed again against that source using the same build directory. The exact
release chain includes:

- Two deterministic regenerations with SHA256 comparison; generated files
  match the staged source-derived artifacts byte for byte. No generated edits.
- 55 compiler/auditor tests, including frozen Phase 4 and active Phase 5
  contracts; 124 total Python tests. The five independent stack/control model
  tests include all 65,536 SP values and exhaustive condition/count relations.
  All 55 compiler tests and artifact consistency also pass on native Windows.
- All 22 directed benches in Verilator and Icarus, dual smoke and state setup.
  New instruction bench: 9,128 cases and 1,928,799 checks in each simulator.
  New lifecycle bench: 180 boundary perturbations, 12 unsupported group cases,
  stale/full queue scenarios, four same-target retirements and 20 nested stream
  instructions; 11,349 checks in each simulator.
- Complete inherited and new physical hardware families, with no sampling.
- Corpus parsing independently agrees for 485,000 unique records and
  8,225,586 captured cycles. All 67 copied-batch fault probes are rejected;
  51 pristine comparator executions pass.
- Four operand/BIU, eight ALU and twelve stack/control RTL mutants rejected
  by their intended assertions; six pristine benches total and unchanged
  production source hashes. Compile errors/timeouts are not accepted as
  functional rejections.
- Pinned MCL86 reconstruction, failure propagation, trace replays,
  Verilator lint, Yosys structural/mapped synthesis and full regression pass.
  The failure-propagation probe deliberately logs a failing reset comparison
  and requires the simulator to return nonzero; it is a passing negative test.

Environment: Linux WSL kernel 6.6.87.2, Python 3.12.3, Verilator 5.020,
Icarus 12.0, Yosys 0.33 (`2584903a060`), Git 2.43.0. Quartus was not needed.

| Generic resource | Phase 4 | Phase 5 | Delta |
|---|---:|---:|---:|
| Mapped cells | 7,326 | 8,260 | +934 |
| Sequential cells | 806 | 825 | +19 |

These are generic mapped cells, not Cyclone V ALMs or Fmax. No historical
cycle-accuracy or FPGA timing result is claimed.

### Evidence fingerprints

The ignored outputs below identify the completed release runs. Log hashes
identify these executions; elapsed times may differ on reproduction.

- `validation.log`: `4bb062f3935e8013c8733b2ae0fcf6e51e63914f627064ec8f0104f3a1bb2a02`.
- `revalidation.log`: `e81092e4cd88b3cfbfaf312e636a23d7f771f4a1b345db9764260abaa959491a`.
- `singlestep/phase5-summary.json`: `b3a58496ec1fded3453cf972dbea6eb2facea9ca2e45222173e8c197b1e4a5f9`.
- `reports/yosys_mapped.log`: `8a9b03b15c6b15c6779a4a4e8a70e2e3d48cedb8bf8f91f513ca1c2fea93ead1`.
- `generated.sha256`: `b3931e5e6ef1b1392d152b10aa72f1823f3210e8745b33904336a31eb30cde69`.


## Bugs, debt and next phase

No inherited Phase 3/4 functional defect required changing the BIU, prefetch,
sequencer or expected hardware results. The implementation explicitly prevents
internal redirect from canceling END, uses original PUSH SP source ordering,
prechecks POP memory before SP effects, and preserves return-IP/cursor separation.

Remaining debt is scoped: exception/shutdown delivery, interrupt frame and
vectoring/INTA/IRET, coordinated architectural CS changes, far transfers,
segment-stack/FLAGS-stack forms, remaining ISA and historical timing validation.
Phase 6 can build serialized entry around stack word completion, existing CS/IP
cache transactions, redirect/drain and retirement boundaries. It must define
its own fault and frame commit ordering; this phase implements no interrupt or
exception engine. CPU-only and separable timing policies remain in force.
