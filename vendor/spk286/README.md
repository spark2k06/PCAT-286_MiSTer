# SPK286

SPK286 is an open-source, synthesizable SystemVerilog project targeting an
Intel 80286-compatible FPGA soft-core.

SPK286 is a **CPU-only project**. Its scope ends at the processor boundary:
architectural execution, microcode, prefetch, segmentation/protection,
exceptions, the Bus Interface Unit (BIU), timing policy, and the native external
CPU interface.

A future PC/AT or MiSTer machine implementation is a **separate downstream
project** that will consume SPK286 as a reusable CPU component. Motherboard
logic such as PIC, PIT, DMA, 8042, RTC/CMOS, ISA, video, storage, BIOS mapping,
MiSTer OSD/HPS integration, and complete machine glue do not belong in this
repository.

Conceptually:

```text
SPK286
  |
  +-- CPU RTL
  +-- BIU / native 80286-style interface
  +-- microcode source + compiler
  +-- generated microcode image
  +-- timing policy
  +-- verification / SingleStep
  |
  +========== repository boundary ==========
                 |
                 v
          PCAT286_MiSTer
          (separate project)
```

## Current status

The current pending-only work register is [Remaining work](docs/REMAINING_WORK.md).
It consolidates the still-open CPU stories and evidence gates; dated phase
reports below retain their original acceptance scopes.

**Phase 7 milestones 1–9 are delivered and functionally/development ready**
under [D-037](docs/PHASE7_FUNCTIONAL_POLICY.md), with independent functional
approval for the executed sources and policy. Fresh integrated validation covers
all 307 required opcode files: **1,386,996 evaluable passes and one NOT EVALUABLE
E7 capture**, with no executable failures or unexpected omissions.

The five named evidence notes remain open and nonblocking; historical 80286
timing is not certified. Phase 8 can start from this accepted functional baseline;
it was not implemented here. The current Phase 8 scope (D-038) adds two
independent CPU-only workstreams: reproduce/fix the BIU HOLD/HLDA race against
implicit LOCK during memory `XCHG`, and diagnose/fix deterministic no-deadlock
handling of coprocessor ESC opcodes `D8–DF` (including `DB`) through the decoder
and project-owned microcode. The existing PCXT/PCAT BIOS is to be retested
unchanged after the ESC fix; BIOS adaptation is not Phase 8 work unless an
independent firmware defect remains. See the [Phase 8 preparation](docs/PHASE8_PREPARATION.md),
[D-038](docs/DECISIONS.md#d-038--phase-8-biu-race-and-esc-decoder-scope-2026-09-10),
[D-039](docs/DECISIONS.md#d-039--phase-8-downstream-transfer-and-user-hardware-checkpoint-2026-09-10),
the [delivery and validation record](docs/PHASE7_FUNCTIONAL_CLOSURE_20260909.md),
[independent review](docs/PHASE7_FUNCTIONAL_REVIEW_20260909.md) and
[recovery guide](docs/PHASE7_FUNCTIONAL_RECOVERY.md). Historical narratives below
preserve their original evidence and are superseded for current Phase 7 status.

After 8A and 8B pass and are independently reviewed in SPK286, their portable
CPU changes are transferred to `PCAT-286_MiSTer` and committed there. The user
then owns Quartus synthesis and the physical RBF test. An explicit user OK closes
the Phase 8 hardware checkpoint; no BIOS adaptation is required after that OK.

The independent CPU now matches the established PCAT functional baseline,
including fetch chaining, parallel bounds, synchronous microcode and real-mode
IP wrap. See the [CPU synchronization record](docs/PCAT_CPU_BASELINE_SYNC_20261004.md).

A provisional CPU-only instruction interval variant, `spk286_profiled`, is
available with a reproducible builder, explicit instruction metadata and retained
retirement deadlines. Its host supplies virtual CPU boundaries and the bus timing
contract; no AT chipset, MiSTer clocks or OSD are included. See the
[profile timing contract](docs/PROFILE_TIMING_CONTRACT.md) for the interface
and limits, and the [directed acceptance record](docs/PROFILE_TIMING_ACCEPTANCE_20261004.md).

**Phase 9 — historical 80286 timing and bus fidelity** remains incomplete and is
not release-approved. The provisional interval model and established performance
implementation do not close the gap to a validated instruction-, BIU- and
pin/cycle-level timing model. See the [Phase 9 timing fidelity plan](docs/PHASE9_TIMING_FIDELITY.md).

Completed and verified:

- **Phase 0** — repository, simulation and verification infrastructure.
- **Phase 1** — architectural register state, IP/FLAGS, visible/hidden segment
  caches, reset behavior, Real Mode address formation, READY-aware fetch and
  redirect handling.
- **Phase 2** — six-byte 80286 prefetch queue and first executable instruction
  family: `MOV r16, imm16` (`B8..BF`).
- **Phase 2.5** — permanent SingleStepTests/80286 integration.
- **Phase 2.75** — generated microcode and reusable microsequencer; the existing
  `B8..BF` family now executes through one shared `MOV_R16_IMM16` microprogram.
- **Phase 2.80** — validación independiente del toolchain MCL86 y endurecimiento
  de los contratos y round-trip del microcódigo SPK286, sin ampliar la ISA.
  Véase el [handoff y los resultados exactos](docs/PHASE2_80_HANDOFF.md).
- **Phase 3** — complete 16-bit ModR/M/EA, reusable register/memory operands,
  shared READY-aware BIU and microcoded unprefixed word MOV (`89`/`8B`).
  See the [architecture and validation handoff](docs/PHASE3_HANDOFF.md).
- **Phase 4** - reusable word ALU, architectural FLAGS masks, executor
  temporaries and five shared microprograms for ADD/ADC/SUB/SBB/CMP/AND/OR/XOR.
  See the [complete validation and handoff](docs/PHASE4_HANDOFF.md).
- **Phase 5** - reusable SS:SP stack words, near CALL/RET/JMP, all Jcc and
  LOOP/JCXZ, with architectural-IP redirects and six-byte prefetch invalidation.
  See the [architecture, exact corpus results and handoff](docs/PHASE5_HANDOFF.md).

The current SingleStep baseline for `B8..BF` is:

```text
40,000 executed
40,000 passed
0 failed
```

The additional supported SingleStep corpus passes 3,955/3,955 cases for `89`
and 3,940/3,940 for `8B`, with zero failures. The 2,047 prefixed and 58 exception
cases are explicitly excluded, never counted as passes. Directed tests cover
all register pairs, EA forms, distinct DS/SS, READY waits, odd word splits and
prefetch coexistence in both simulators. Exception delivery, prefixes and exact
historical timing remain future work.

Phase 4 now adds reusable word ALU/FLAGS on these operand services. Its 40
unprefixed forms cover ADD/ADC/SUB/SBB/CMP/AND/OR/XOR in both REG/RM directions,
AX immediate, and 81/83 word-immediate forms. The full admitted new corpus
passes 166,085 cases with zero failures; prefixes and exceptions are counted
separately. See [PHASE4_SCOPE](docs/PHASE4_SCOPE.md) for exact scope and FLAGS policy. This is
functional validation, not historical cycle accuracy.

Phase 5 adds 47 unprefixed stack/near-control forms and passes all 226,594
admitted new hardware cases. The full release gate retains the inherited
213,980 cases, for **440,574/440,574** passing cases. PUSH SP/POP SP ordering,
CALL return IP, RET release, target wrap, all conditions, stale prefetch and
nested streams are independently checked in both simulators. Interrupt and
exception entry, far transfers and historical timing remain future work.

## CPU architecture direction

SPK286 is being developed as a microsequenced CPU with reusable hardwired
subsystems.

The intended structure is approximately:

```text
prefetch / instruction unit
          |
          v
       decoder
          |
          v
    microsequencer
          |
          v
   generated microcode
          |
     +----+--------------------+
     |                         |
     v                         v
 execution/datapath       address/protection
     |                         |
     +------------+------------+
                  |
                  v
                 BIU
                  |
                  v
         native CPU interface
```

The human-readable microcode source is authoritative. The deterministic compiler
generates committed SystemVerilog constants/ROM, a listing, source map and
validation metadata. Normal builds reject stale artifacts. A separate `.hex`
export remains deferred until a downstream integration requires it.

## Timing model

Functional CPU semantics and historical timing policy are deliberately
separate.

The long-term timing model supports the following conceptual modes:

- **Accurate** — reproduce validated historical 80286 instruction and BIU timing
  for a selected profile.
- **Fast** — remove artificial instruction-level compatibility delays while
  retaining a compatibility-oriented BIU.
- **Max** — remove removable historical delays from execution and BIU operation
  while preserving all real dependencies.

Real dependencies such as READY, BIU completion, operand availability,
prefetch availability, queue redirects, bus ownership and required
serialization must remain valid in every mode.

Candidate historical profiles include 6, 8, 10, 12/12.5, 16, 20 and 25 MHz,
but a profile is not considered accurate until its timing has been validated.

`Max` is an accelerated 80286-compatible mode, not a claim that SPK286 is a
literal historical "286 at X MHz".

## Verification philosophy

SPK286 uses a layered verification strategy:

1. directed RTL/unit tests;
2. Verilator as the primary simulator;
3. Icarus Verilog as an independent secondary simulator;
4. Python/vector tests;
5. Yosys structural/synthesis sanity checks;
6. SingleStepTests/80286 hardware-derived vectors;
7. later bus/cycle convergence against captured hardware traces.

SingleStepTests is treated as hardware-derived evidence, not as an excuse to
special-case corpus data.

Expected values must never be modified merely to make broken RTL pass.

## Development environment

Use WSL2 Ubuntu as the primary command-line environment. The authoritative
working tree remains the Windows checkout at `/mnt/d/GitHub/SPK286`; do not make
a second clone for normal work.

- Verilator is the primary simulator and lint engine.
- Icarus Verilog is the independent secondary simulator.
- Python 3 standard-library tooling handles test data, microcode tooling and
  reporting where practical.
- Yosys provides an inexpensive synthesis sanity check.
- Quartus Prime is isolated in the existing `raetro/quartus:mister` Docker
  image and is intentionally outside the fast loop.

## Quick start from WSL

```bash
cd /mnt/d/GitHub/SPK286
./scripts/bootstrap.sh
make help
make test
make regression
```

Useful targets currently include:

```text
make env              report the detected toolchain
make microcode        regenerate committed ROM, constants, listing and maps
make microcode-check  compare generated artifacts without modifying them
make microcode-test   run the independent Python compiler/ROM tests
make lint             run Verilator lint with warnings visible
make unit             run directed RTL/unit tests
make verilator        build/run the Verilator smoke path
make test             run the fast dual-simulator and Python tests
make regression       run the complete normal regression including Yosys checks
make waveform         rerun a focused Verilator test and emit a VCD trace

make data-smoke       validate the SingleStep JSON/MOO loader path
make state-smoke      verify RTL state initialization and first fetch
make singlestep-fetch acquire the pinned external 80286 MOO working set
make singlestep-smoke run deterministic hardware-vector smoke cases
make singlestep-mov   run the full non-revoked B8..BF hardware-vector suite
make singlestep-operands run the full supported 89/8B hardware-vector suite
make phase3-check     run the mandatory complete inherited Phase 3 validation
make singlestep-alu   run every admitted Phase 4 hardware-vector form
make alu-audit        reject eight isolated ALU/datapath RTL mutants
make phase4-check     run the complete mandatory Phase 4 release validation
make singlestep-stack-control run all 47 admitted Phase 5 hardware forms
make stack-control-audit reject twelve isolated stack/control RTL mutants
make phase5-check     run all inherited and Phase 5 release validation

make verify-failure   prove simulator failures return non-zero status
make synth-check      run portable RTL through Yosys
make quartus-info     verify the local Quartus Docker image and version
make clean            remove generated build output
```

See [microcode/README.md](microcode/README.md) for the implemented DSL and
micro-PC/source lookup. The portable RTL manifest is `scripts/rtl_sources.sh`:
compile the generated package before the ROM and CPU modules.

Run `make waveform` and open the generated VCD with GTKWave when detailed
cycle/state debugging is needed. Large regressions must opt into traces
explicitly.

## Project boundaries

The BIU is part of SPK286.

The logic on the other side of the BIU is not.

SPK286 therefore owns CPU-facing behavior such as:

- 24-bit address generation;
- 16-bit data transfers;
- BHE / byte-lane behavior;
- code fetch;
- memory and I/O cycles;
- READY;
- HOLD/HLDA;
- LOCK;
- INTR/NMI;
- interrupt acknowledge behavior;
- prefetch interaction;
- timing policy.

A downstream PC/AT project owns:

- RAM/ROM implementation and machine memory map;
- AT chipset;
- PIC/PIT/DMA;
- 8042;
- RTC/CMOS;
- ISA devices;
- video/audio;
- storage;
- BIOS packaging;
- MiSTer framework and OSD/HPS integration.

Booting a PC/AT BIOS can be a useful downstream integration test, but it is not
the Definition of Done for SPK286 itself.

## Key documentation

Read these first:

- `SPK286_SPEC.md` — project-wide architectural specification and CPU-only
  project boundary.
- `SPK286_MICROCODE_FORMAT.md` — microcode DSL, compiler, ROM and
  microsequencer/tooling specification.
- `SPK286_TIMING_MODEL.md` — Accurate/Fast/Max timing architecture and the rule
  separating functional semantics from historical timing.
- `docs/PHASE9_TIMING_FIDELITY.md` — planned work for instruction, BIU,
  prefetch and native 80286 timing validation.
- `SPK286_REALMODE_MVP.md` — functional Real Mode milestone.
- `SPK286_PROTECTED_MODE.md` — 80286 Protected-Mode architecture and
  implementation contract.
- `docs/MILESTONE_7_LOADALL.md` — 80286 LOADALL/unreal-mode milestone, current
  implementation slice, evidence policy, implementation gates, and acceptance
  criteria.
- `docs/LOADALL_EVIDENCE.md` — LOADALL source provenance, image layout,
  implementation contract, validation receipt, and remaining evidence gaps.
- `SPK286_PROTECTED_MODE_IMPLEMENTATION_PROMPT.md` — ready-to-use prompt for a
  new implementation session.
- `SPK286_ENVIRONMENT.md` — development/toolchain environment.
- `docs/DECISIONS.md` — engineering decisions.
- `docs/SINGLESTEP_INTEGRATION.md` — external hardware-vector runner.
- `docs/PHASE2_75_HANDOFF.md` — microcode foundation and validation handoff.
- `docs/PHASE3_HANDOFF.md` — operand architecture, exact results and Phase 4 readiness.
- `AGENTS.md` — rules for autonomous implementation agents.

Earlier handoffs remain useful as historical implementation context.

## Long-term SPK286 deliverable

The intended end product is a standalone reusable 80286 CPU package containing,
at minimum:

```text
authoritative microcode source
        +
deterministic microcode compiler
        +
generated microcode image
        +
required synthesizable CPU SystemVerilog RTL
        +
documented native CPU interface
        +
verification and integration documentation
```

A separate project should be able to instantiate that package as the CPU of a
PC/AT-class FPGA system without importing machine-specific logic into SPK286.

The target remains:

> **SPK286: a dedicated, standalone, synthesizable, hardware-validated Intel
> 80286-compatible FPGA soft-core with separable historical and accelerated
> timing policies.**

Phase 5 scope and delivery: [PHASE5_SCOPE](docs/PHASE5_SCOPE.md) and
[PHASE5_HANDOFF](docs/PHASE5_HANDOFF.md).

## Phase 6 candidate (release blocked)

The working candidate adds shared real-mode INT/IRET, PUSHF/POPF, CLI/STI,
HLT, TF/NMI/INTR arbitration, physical INTA and supported #UD/#GP delivery.
It retains the CPU-only boundary and original state/stack/operand/BIU owners.
The full admitted hardware cohort is 474,049 cases (440,574 inherited, 1,423
formerly excluded faults and 32,052 new-family cases); executed evidence and
limitations are recorded in [PHASE6_HANDOFF](docs/PHASE6_HANDOFF.md).

**Phase 6 is not ready.** Failed-IRET NMI release, the old-IF STI qualifier and
conflicting fault/TF text require 286-specific adjudication. Directed model
agreement cannot replace that evidence. See the
[independent review](docs/PHASE6_ARCHITECTURAL_REVIEW.md).
`SPK286_BUILD_DIR="$PWD/build/phase6-new-run" make phase6-check` requires a
previously absent directory, runs the complete inherited and event checks, and
fails closed while these decisions remain unresolved. D-026 permits incremental
Phase 7 development on this provisional baseline after a fresh
`make phase6-exec-check`. This runs the same executable checks and reports the
actual evidence status without granting architectural approval. The earlier
Phase 3–5 counts above are historical cohorts; the current Phase 6 candidate
also admits their 1,423 unprefixed exceptions.

## Phase 7 development status (2026-09-08)

The provisional Phase 6 baseline is committed as
`52e73cb8ece39621e89cbaf77f59d88581788e54` and has passed fresh executable
validation. Its three architectural evidence questions remain unresolved.

The current Phase 7 increment adds byte register/operand operations, the
remaining immediate-to-RM MOV forms and bounded prefix context for supported
scalar instructions. Its complete bounded gate passed with 737,998 records in
150 physical files, including
all 43,951 previously excluded prefixes in the old cohort. See the
[handoff](docs/PHASE7_HANDOFF.md) for actual final-gate and Git status.

**The complete Phase 7 is not delivered.** Scalar I/O remains an isolated
prototype with a reproducible incomplete E7 bus capture; strings/REP and the
other required forms listed in [PHASE7_SCOPE](docs/PHASE7_SCOPE.md) remain
pending. `make phase7-check` fails incomplete scope.
`make phase7-byte-prefix-check` is explicitly limited to the implemented
increment and cannot grant complete Phase 7 or architectural release approval.

The verified scalar increment adds 31 files (TEST, register
INC/DEC, CBW/CWD and remaining direct flag controls), for 181 required forms.
Its complete `phase7-scalar-check` passed 800,998 distinct physical records,
32 benches in both simulators, compiler/lint, mutation audits, synthesis and
regression. See [the scalar validation record](docs/phase7_scalar_validation.json).
At the scalar snapshot, 126 required opcode files and independent review remained pending. The verified
byte/prefix commit remains `6caa746784c06a17a18b459b1f228a5843894465`.

The verified shift/rotate increment adds all 42 documented files. The complete
`phase7-shift-check` passed 1,010,998 physical cases, 34 benches in both
simulators, compiler/lint, mutation audits, synthesis and regression. At the shift snapshot, the
registry had 223 required files, with 84 still missing; independent review is
pending. See [the shift validation record](docs/phase7_shift_validation.json).

The verified data-transfer increment adds XCHG/NOP, LEA, XLAT and direct-offset
MOV (sixteen files). The fresh complete `phase7-data-check` passed 1,058,998
physical cases, 36 benches in both simulators, 195 ordinary tests, 70 compiler
tests, 77 intended RTL mutants, lint, synthesis and regression. At the data snapshot, the registry
contained 239 required files; 68 remained absent and independent review was pending.
See [the data validation record](docs/phase7_data_validation.json) and handoff.

The verified unary increment adds NOT/NEG and byte/word memory INC/DEC through
a generic decoded branch and cached operand context. Its fresh complete
`phase7-unary-check` passed 1,098,998 distinct physical cases, 38 benches in both
simulators, 202 ordinary tests, 74 compiler tests, 87 intended RTL mutants, lint,
synthesis and regression. The registry has 247 required files with 60 still
absent; complete Phase 7 and independent review remain pending. See the
[validation record](docs/phase7_unary_validation.json),
[dispatch contract](docs/PHASE7_UNARY_DISPATCH.md) and handoff.

The verified decimal-adjust increment adds DAA/DAS, AAA/AAS and AAM/AAD.
The fresh `phase7-adjust-check` passed 1,128,998 distinct physical records,
41 benches in both simulators, 207 ordinary tests, 76 compiler tests, all 99
intended RTL mutants, lint, synthesis and regression. Eleven AAM radix-zero
#DE frames passed without masking their saved FLAGS. The registry contains
253 required files with 54 still absent; complete Phase 7 and independent
review remain pending. See the [validation record](docs/phase7_adjust_validation.json)
and [adjustment contract](docs/PHASE7_DECIMAL_ADJUST.md).

The integrated segment-transfer candidate adds MOV/PUSH/POP of ordinary 286
segments and protection through the instruction following a successful SS load.
Its prototype passed all 45,000 physical cases plus CPU and event suites;
the fresh combined `phase7-segment-check` remains pending. The registry now
contains 262 required files, with 45 still absent. See the
[segment contract](docs/PHASE7_SEGMENT_TRANSFER.md) and implementation handoff.

The integrated stack/frame candidate adds PUSHA/POPA, ENTER/LEAVE and BOUND.
Its prototype passed all 24,999 non-revoked physical cases, directed CPU/event
checks and synthesis. The fresh `phase7-stack-frame-check` validates segments
and frames together after the earlier segment run was interrupted. The registry
contains 267 required files with 40 still absent. Full Phase 7 and independent
review remain pending; see the [frame contract](docs/PHASE7_STACK_FRAME.md).

## Latest Phase 7 increment — 2026-09-09

MUL/IMUL/DIV/IDIV and immediate IMUL are implemented and verified with all
previously delivered scalar, segment, frame and far-control forms. The fresh
gate passed 1,288,997 disjoint physical cases, 51 benches in both simulators,
153 intended RTL faults, lint and synthesis. See
[the exact validation record](docs/phase7_arithmetic_validation.json).
285 of 307 required opcode files are implemented. Memory strings/REP, I/O,
their remaining evidence and final independent review remain pending. Phase 7
is incomplete and `make phase7-check` remains strict.
The [remaining-work record](docs/PHASE7_REMAINING_WORK.md) preserves the verified
local candidates and identifies the required evidence, review and integration.
