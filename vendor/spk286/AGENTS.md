# SPK286 Agent Guidelines

## Engineering priorities

- Phase 7 development may proceed on an executable-validated provisional Phase
  6 baseline (D-026). `failed-iret-nmi`, `sti-old-if` and `fault-tf` may
  remain open under their recorded policies. This does not waive executable
  failures or grant architectural release approval. `make phase6-check` remains
  strict; `make phase6-exec-check` reports development validation separately.

- D-037 additionally authorizes Phase 7 functional/development closure and
  Phase 8 entry with `rep-zero-count-event-order` and the one exact
  `e7-incomplete-physical-capture` note open. Follow
  `docs/PHASE7_FUNCTIONAL_POLICY.md`; `phase7-check` requires complete executable
  validation and independent functional review. `phase7-evidence-check` reports
  unresolved physical evidence separately. No real failure or unexpected
  omission is waived, and E7 issue publication remains held by user request.

- Correctness takes precedence over implementation speed.
- Tests are part of the specification, not an afterthought.
- Every meaningful RTL change must be verified before it is committed.
- Relevant Verilator lint must pass before committing.
- Affected tests and the existing regression must pass.
- Relevant SingleStepTests/80286 coverage must pass for every newly supported
  instruction family or externally observable behavior where applicable.
- Never modify expected results merely to make broken RTL pass.
- Expected behavior ultimately derives from Intel 80286 documentation and
  physical 80286 evidence; reference implementations are evidence, not
  unquestionable truth.
- Prefer small, logically coherent changes.
- Commit only verified states and preserve reproducibility.
- Document important architectural decisions and avoid unnecessary
  dependencies.
- Avoid premature optimization.
- Never weaken verification merely to obtain green tests.
- Functional semantics and historical timing policy must remain separable.
- Do not encode historical timing by inserting semantically meaningless
  idle/NOP RTL states or micro-operations when the delay belongs in the timing
  policy.
- Real dependencies such as READY, BIU completion, required instruction bytes,
  operand availability, bus ownership, queue flush/redirect completion, and
  required serialization must be honored in every timing mode.

## Required validation

For any meaningful change, run the smallest relevant checks first, then the
broader regression before committing:

```text
focused unit/compiler test
        ->
Verilator lint
        ->
affected RTL tests
        ->
dual-simulator smoke
        ->
relevant SingleStep sample/full opcode family
        ->
Yosys/synthesis sanity check where applicable
        ->
regression
```

Do not bypass a failing check. If a test expectation is questionable, gather
Intel documentation or physical-test evidence before changing it.

When generated microcode exists, regeneration and consistency checks are part
of normal validation. A stale generated artifact is a build failure, not a
reason to hand-edit generated output.

## Debugging policy

When a test fails:

1. reproduce it;
2. reduce it when useful;
3. inspect state, bus activity and traces;
4. form a hypothesis;
5. identify relevant specification/reference evidence;
6. classify the failure as functional, bus, timing, tooling, or test-adapter
   related;
7. change the smallest reasonable implementation area;
8. rerun the failing test;
9. rerun affected tests;
10. run regression before committing.

For SingleStep failures, do not hard-code:

- test addresses;
- test indexes;
- corpus byte sequences;
- expected register/memory values.

Fix the general CPU behavior.

## Microcode policy

SPK286 uses project-owned microcode.

When the generated microcode architecture is present:

- human-readable `.mc` source is authoritative;
- the microcode compiler must be deterministic;
- generated SystemVerilog/ROM images must not be manually edited;
- source mapping from micro-PC back to symbolic microcode should remain
  available for simulation/debugging;
- the microsequencer must not become a second x86 decoder;
- the BIU owns physical bus-cycle sequencing;
- the prefetch unit owns queue storage/refill behavior;
- microcode requests functional operations and waits for real dependencies;
- the number of microinstructions used for an instruction does not, by itself,
  define historical 80286 cycle count.

Timing metadata may be added later, but it must remain explicit and separable
from functional sequencing.

## Timing policy

Follow `SPK286_TIMING_MODEL.md`.

The intended long-term modes are conceptually:

- **Accurate** — validated historical 80286 timing;
- **Fast** — reduced instruction-level compatibility delay with a
  compatibility-oriented BIU;
- **Max** — dependency-driven accelerated execution.

Do not claim a timing profile is cycle-accurate merely because its nominal MHz
or aggregate instruction time matches a published value.

Fast/Max must never change architectural results or bypass real dependencies.

Exact timing implementation is not a blocker for functional Real Mode phases
unless the active phase/handoff explicitly says otherwise.

## CPU-only project boundary

SPK286 is a standalone CPU-development project.

The repository ends at the CPU boundary.

The following belong in SPK286:

- CPU top-level RTL;
- decoder and microsequencer;
- Execution Unit/datapath;
- register and FLAGS machinery;
- project-owned microcode source/compiler/generated image;
- prefetch/instruction unit;
- effective-address logic;
- segmentation and protection;
- interrupts/exceptions;
- BIU and native 80286-style external CPU interface;
- READY, HOLD/HLDA, LOCK, INTR/NMI and INTA-related CPU behavior;
- CPU timing policy;
- CPU-only verification, debug and synthesis infrastructure.

The following do **not** belong in SPK286:

- IBM PC/AT chipset implementation;
- PIC, PIT, DMA, 8042 or RTC/CMOS;
- ISA machine integration;
- video, audio or storage subsystems;
- BIOS packaging or PC/AT memory-map glue;
- MiSTer `emu` top level;
- MiSTer OSD/HPS integration;
- complete machine-level SDRAM/peripheral integration.

The BIU is part of SPK286. The motherboard-side logic connected to the BIU is
not.

A future project such as `PCAT286_MiSTer` may consume SPK286 as a reusable CPU
component. Do not move downstream machine logic into this repository merely to
make a BIOS or operating system boot.

Board-specific files inside SPK286 are limited to CPU-only synthesis,
interface experiments, or smoke-test harnesses.

## Scope and source safety

- Keep Quartus out of the fast simulation loop unless a concrete synthesis or
  ROM-inference question requires it.
- Keep MiSTer and PC/AT machine integration outside the standalone CPU
  repository.
- Treat external CPU cores as reference material unless a compatible license
  and deliberate reuse decision are recorded.
- Do not add 386 architectural behavior to solve a 286 problem.
- Inspect the current phase specification and handoff before implementing.
- Do not expand into later phases merely because the required infrastructure
  makes future work possible.
- Make conservative, reversible choices when a non-critical ambiguity can be
  resolved without blocking progress.
- Do not inspect or modify unrelated personal data, repositories, or projects
  while operating autonomously on SPK286.

## Repository safety

Agents may create working branches, commits, and push their own work branch when
authentication is available.

Do not:

- push directly to `main` or `master`;
- merge into `main` or `master`;
- force-push;
- rewrite published history;
- delete branches or tags;
- perform destructive Git cleanup;
- change repository security/settings without explicit authorization.

Leave the working tree clean at phase completion where practical.

## Communication and repository language

Reason internally in English. Communicate with the user in Spanish. Source
code, identifiers, source comments, scripts, commit messages, microcode
identifiers/comments, and technical identifiers in the repository are written
in English unless an existing project requirement explicitly says otherwise.
