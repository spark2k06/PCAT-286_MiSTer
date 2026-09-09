# SPK286 Phase 0 Handoff

## Status

Phase 0 establishes a reproducible engineering and verification foundation.
The repository contains a deliberately minimal, synthesizable reset/fetch RTL
proof and no meaningful instruction execution. This is ready for the next
functional CPU prompt after the final verification recorded below.

## Selected platform strategy

- Primary HDL environment: WSL2 Ubuntu 24.04.4 on the existing Windows checkout
  at `/mnt/d/GitHub/SPK286`.
- Primary simulator/lint: Verilator 5.020.
- Secondary simulator: Icarus Verilog/VVP 12.0.
- Primary scripting/build: Python 3.12 standard library plus POSIX shell and
  Make 4.3.
- Lightweight synthesis: Yosys 0.33.
- Waveform viewer: GTKWave 3.3.116; VCD is generated explicitly.
- Heavy FPGA tooling: Docker image `raetro/quartus:mister`.
- Future synthesis: introduce a small Cyclone V Quartus project only at a
  milestone boundary; never add it to the normal test loop.

The one authoritative Git working tree remains on `D:`. WSL accesses it via
`/mnt/d`; no duplicate checkout was created. `.gitattributes` makes relevant
source and scripts LF-safe despite the pre-existing Windows Git setting.

## Tools and environment

See [ENVIRONMENT_DETECTED.md](ENVIRONMENT_DETECTED.md) for the full discovery
record. The important results are:

```text
Ubuntu 24.04.4 / WSL2 kernel 6.6.87.2
Python 3.12.3, GCC/G++ 13.3.0, Make 4.3
Verilator 5.020, Icarus/VVP 12.0, Yosys 0.33
CMake 3.28.3, Ninja 1.11.1, GTKWave 3.3.116
Docker 29.1.3; Quartus Prime 17.0.2 in raetro/quartus:mister
```

## Repository structure

```text
rtl/spk286.sv                         Phase 0 reset/fetch skeleton
sim/verilator/reset_smoke.cpp         compiled Verilator harness
sim/iverilog/spk286_reset_tb.sv       shared logical reset test
tools/singlestep.py                   JSON/JSONL/MOO data reader
tools/run_tests.py                    data selection smoke CLI
tests/fixtures/                       checked-in tiny vector
tests/test_singlestep.py               reader unit tests
scripts/                              environment/build/test entry points
docs/                                 architecture, decisions, notes, handoff
microcode/                            reserved for the project-owned DSL
config/environment.example             optional path configuration
```

## Developer commands

Run from WSL at the repository root:

```bash
./scripts/bootstrap.sh
make env
make lint
make test
make regression
make data-smoke
make quartus-info
```

`make test` runs lint, Verilator compilation/execution, Icarus compilation/
execution, and Python unit tests. `make regression` adds Yosys. All commands
are non-interactive and propagate failures with non-zero exit status.

## What the current tests prove

The dual-simulator reset test verifies:

```text
visible CS       = 0xF000
hidden CS base   = 0xFF0000
IP               = 0xFFF0
first fetch      = 0xFFFFF0
CODE status      = 0xD
active-low BHE   = asserted for the first word request
READY            = completes the request and returns to passive output
```

The Python tests prove JSON fixture loading, common MOO 1.1 chunk decoding,
hash preservation, revocation-list recognition, and malformed-input rejection.
The Yosys check proves that the portable RTL elaborates and survives basic
process conversion/structural checking. None of these tests claims instruction
execution.

## Waveform workflow

```bash
make waveform
gtkwave build/traces/reset_verilator.vcd
```

The normal test path does not produce traces. The trace is ignored by Git and
can be deleted with `make clean`.

## SingleStep foundation

The external `SingleStepTests/80286` corpus is not checked out locally. Set
`SPK286_SINGLESTEP_PATH` or use `tools/run_tests.py --source PATH` when it is
available. The reader preserves indexes, bytes, states, cycles, exceptions,
hashes, and revocation information. Phase 1 must add the CPU execution adapter,
then separate functional, memory, bus, and cycle comparison results.

## Docker / Quartus

The existing local `raetro/quartus:mister` image was found and verified with
Quartus Prime Shell 17.0.2 Build 602. The future invocation pattern is:

```bash
docker run --rm \
  -v "$(pwd):/build" \
  -w /build \
  raetro/quartus:mister \
  quartus_sh --flow compile <project>.qsf
```

No full Quartus compile was run in Phase 0. `make quartus-info` is the cheap
availability check. Keep synthesis reports under `build/` and keep Quartus out
of the edit/simulate/test loop.

## References and known risks

Useful references and license decisions are recorded in
[SOURCE_NOTES.md](SOURCE_NOTES.md). The most important risks carried forward
are the exact 80286 hidden segment state, six-byte prefetch behavior, reserved
FLAGS semantics, 24-bit byte-lane/bus timing, and the difference between 286
behavior and tempting 8086/80186/386 reference implementations.

Non-blocking unresolved items are listed in [DECISIONS.md](DECISIONS.md): the
full MOO execution/comparison adapter, final bus wrapper, microcode generation
policy, and first Quartus project assignments.

## Branch and commits

- Branch: `codex/phase0-bootstrap`
- Commits: `a1a24ec` infrastructure baseline; the final verification and
  handoff commit is this commit.
- Push: final branch push is attempted after this commit; the result is
  reported to the user with the final Git status.

## Final verification results

Final clean rebuild results:

- `make env`: PASS; all required WSL commands found and Quartus image detected.
- `make test`: PASS; Verilator lint/build/smoke, Icarus smoke, and 4 Python
  reader tests passed.
- `make regression`: PASS; the same tests plus Yosys elaboration/synthesis
  sanity check, with 0 structural problems.
- `make verify-failure`: PASS; both simulators rejected an incorrect fetch
  expectation with non-zero status.
- `make waveform`: PASS; `build/traces/reset_verilator.vcd` generated.
- `make quartus-info`: PASS; Quartus Prime Shell 17.0.2 Build 602 reported by
  `raetro/quartus:mister`.
- Generated output remains ignored under `build/`; no full Quartus compile was
  run.

## Recommended Phase 1 Starting Point

### Block/component

Implement the first real architectural state block: a resettable register file
and segment-cache boundary integrated with the code-fetch/prefetch entry path.
Keep the visible 16-bit segment values separate from hidden 24-bit base/limit
state, retain the special reset `CS` base, and expose deterministic debug state.

### Why this should be first

It is the smallest coherent block that directly advances RM0/RM1, establishes
the state that every later instruction needs, and prevents a disposable
`segment << 4` shortcut. It also gives the decoder, microsequencer, address
unit, and SingleStep adapter stable contracts before MOV/ALU work begins.

### Architectural responsibilities

- Store AX/BX/CX/DX, SP/BP/SI/DI, IP, FLAGS, and visible CS/DS/SS/ES.
- Store hidden segment base/limit/access state, with reset CS base `0xFF0000`.
- Produce 24-bit physical addresses without truncating to 20 bits.
- Provide deterministic reset and code-fetch request sequencing.
- Keep READY wait-state retention explicit at the bus boundary.
- Provide simulation observability for registers, segment cache, fetch pointer,
  and bus state without changing synthesis behavior.

### Interfaces

- Clock/reset and READY inputs.
- Native 24-bit address, 16-bit data, BHE, bus status, request, write, LOCK,
  and HLDA signals following `docs/BUS_INTERFACE.md`.
- Register/segment state interface for the instruction unit and future
  microsequencer.
- Debug state sufficient to map a failing test to architectural state and the
  current bus/fetch phase.

### Tests to create before or alongside it

- Register reset and independent read/write tests.
- Visible-versus-hidden segment-cache reset tests.
- Physical-address tests for ordinary real-mode segments and reset CS.
- 24-bit boundary and A20-external-to-CPU tests.
- READY wait-state retention tests for a code fetch.
- Dual-simulator reset/fetch regression.
- A first directed vector adapter test using the checked-in schema, followed by
  one real SingleStep `.MOO`/JSON case when the external corpus is configured.

### Relevant reference material

- `SPK286_SPEC.md`, sections 9–18 and 24.
- `SPK286_REALMODE_MVP.md`, sections 8–16 and RM0/RM1.
- `SPK286_ENVIRONMENT.md`, sections 5–16 and 33–42.
- Intel 80286 reset and hardware manuals in the Bitsavers archive.
- SingleStepTests/80286 README/MOO format and its physical Harris 80C286 data.
- `SPK286_MICROCODE_FORMAT.md` for the later project-owned execution boundary.

### Definition of Done

- All architectural state in the block resets deterministically.
- Reset CS/IP and hidden CS base produce the expected first fetch.
- Ordinary real-mode segment bases and 24-bit address arithmetic are tested.
- READY holds and completes requests without state corruption.
- Verilator lint, Verilator tests, Icarus tests, Python tests, and regression
  pass on a clean rebuild.
- The block has no MiSTer/PCAT dependency and no unverified 386 behavior.
- The next block can consume documented interfaces without rewriting reset or
  segment state.
