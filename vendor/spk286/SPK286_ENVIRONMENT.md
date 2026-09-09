# SPK286 — Development Environment and Verification Workflow

**Document:** `SPK286_ENVIRONMENT.md`  
**Project:** SPK286  
**Status:** Initial environment specification  
**Companion document:** `SPK286_SPEC.md`  
**Primary host environment:** Windows + WSL2 / Ubuntu  
**Primary FPGA target:** Intel Cyclone V / DE10-Nano / MiSTer  
**Primary simulator:** Verilator  
**Secondary simulator:** Icarus Verilog  
**FPGA synthesis tool:** Intel Quartus Prime  
**Automation language:** Python 3

---

## 1. Purpose

This document defines the expected development, simulation, verification, synthesis, and hardware-validation environment for SPK286.

It complements `SPK286_SPEC.md`.

The CPU architecture and compatibility requirements are defined in the specification document. This document defines **how SPK286 shall be developed and tested**.

The implementation agent must read both documents before making architectural or RTL changes.

---

## 2. Environment Philosophy

SPK286 shall not depend on a single simulator or a single FPGA integration environment.

The preferred verification stack is:

```text
                    SPK286 RTL
                        |
            +-----------+-----------+
            |                       |
            v                       v
        Verilator               Icarus Verilog
     primary simulator          secondary check
            |
            v
   SingleStepTests/80286
            |
            v
   functional / bus / cycle
        regression
            |
            v
        Quartus Prime
            |
            v
       Cyclone V build
            |
            v
          MiSTer
            |
            v
    real hardware validation
```

The purpose of using multiple layers is to prevent a successful result in one environment from being mistaken for proof of correctness.

---

## 3. Host Environment

The expected development host is:

- Windows;
- WSL2;
- Ubuntu inside WSL;
- Git;
- command-line development workflow.

The agent must prefer Linux/WSL-compatible scripts.

Avoid requiring GUI interaction for normal:

- compilation;
- simulation;
- regression;
- lint;
- code generation;
- test selection;
- result comparison.

Quartus GUI may be useful for FPGA analysis, but normal synthesis should also be scriptable where practical.

---

## 4. Environment Discovery Rule

The implementation agent must **inspect the actual installed environment before installing or changing tools**.

Do not assume:

- exact Ubuntu version;
- exact Verilator version;
- exact Icarus version;
- exact Quartus version;
- exact Python version;
- exact installation paths;
- exact shell configuration.

Initial environment inspection should include commands equivalent to:

```bash
uname -a
cat /etc/os-release

git --version
python3 --version

verilator --version
iverilog -V
vvp -V

quartus_sh --version
```

If a tool is unavailable, report it before attempting to replace the established workflow.

Do not upgrade, remove, or reinstall an existing tool merely because a newer version exists.

---

## 5. Primary Simulator — Verilator

Verilator is the **reference simulator for SPK286 development and regression**.

Primary uses:

- instruction-level simulation;
- SingleStepTests/80286 execution;
- high-volume regression;
- cycle-by-cycle bus capture;
- C++ testbench integration;
- waveform generation;
- debug builds;
- CI execution.

The project shall treat a successful Verilator build as a basic requirement.

---

## 6. Why Verilator Is Primary

SPK286 verification is expected to involve a very large number of CPU executions.

The published SingleStepTests/80286 real-mode corpus contains approximately:

- 1.5 million instruction executions;
- more than 32 million captured cycle states.

A compiled simulator is therefore highly desirable.

Verilator translates synthesizable SystemVerilog into optimized C++ code, which is well suited to:

- repeated CPU reset/setup;
- rapid instruction execution;
- direct C++ memory models;
- direct test-data ingestion;
- parallel regression;
- machine-readable result generation.

The verification architecture should be designed around this workload rather than around interactive waveform-only simulation.

---

## 7. Verilator Testbench Architecture

The preferred architecture is:

```text
SingleStep test data
        |
        v
 test loader / parser
        |
        v
 C++ Verilator harness
        |
        +--> CPU inputs
        |
        +<-- CPU architectural/debug state
        |
        +<-- native bus state
        |
        v
 comparison engine
        |
        +--> functional result
        +--> memory result
        +--> bus result
        +--> cycle result
```

Python may orchestrate the regression, while C++ drives the per-cycle Verilator simulation.

Recommended division:

### C++

Use for:

- clock driving;
- reset driving;
- memory response;
- I/O response;
- bus sampling;
- per-cycle CPU execution;
- high-speed comparison;
- optional FST/VCD tracing.

### Python

Use for:

- command-line regression orchestration;
- selecting test families;
- converting test formats when needed;
- parallel execution;
- summary generation;
- failure reports;
- statistics;
- microcode generation tools.

---

## 8. Verilator Build Requirements

The project should provide a standard command or script such as:

```bash
./scripts/build_verilator.sh
```

or:

```bash
make verilator
```

The exact build system may evolve, but it must be:

- reproducible;
- non-interactive;
- documented;
- usable from WSL;
- suitable for automated agents.

Recommended warning policy:

- warnings should be visible;
- important width/latch/case warnings should not be ignored;
- warnings must not be globally suppressed without justification.

Do not make the build dependent on implementation-specific Verilator behavior when standard synthesizable SystemVerilog can express the same logic.

---

## 9. Verilator Regression Interface

A target command-line interface should eventually support commands conceptually similar to:

```bash
python3 tools/run_tests.py --smoke

python3 tools/run_tests.py \
    --opcode MOV

python3 tools/run_tests.py \
    --opcode ADD \
    --limit 1000

python3 tools/run_tests.py \
    --test-id 12345

python3 tools/run_tests.py \
    --all \
    --jobs 8

python3 tools/run_tests.py \
    --test-id 12345 \
    --trace
```

Exact option names may differ.

Required properties:

- deterministic test selection;
- deterministic failure reproduction;
- parallel execution where safe;
- useful exit codes;
- concise summary;
- detailed failure artifact.

---

## 10. Waveform Format

For Verilator, prefer:

- **FST** for normal debugging;
- VCD only where compatibility requires it.

Waveform generation shall not be enabled by default during large regressions.

A failing test must be reproducible with tracing enabled using its test identifier.

Example concept:

```bash
python3 tools/run_tests.py \
    --test-id 82491 \
    --trace
```

Generated traces should go to a predictable directory such as:

```text
build/traces/
```

---

## 11. Secondary Simulator — Icarus Verilog

Icarus Verilog is a **required secondary simulator** for SPK286.

It is already part of the expected working environment and must remain useful throughout development.

Its purpose is not to replace Verilator for the full SingleStep regression.

Its purpose is to provide an independent compile/simulation path.

---

## 12. Why Keep Icarus

A second simulator helps detect:

- accidental dependence on Verilator-specific behavior;
- questionable SystemVerilog constructs;
- initialization assumptions;
- race conditions;
- event-ordering mistakes;
- simulator-specific undefined behavior.

A core that only works under one simulator is less trustworthy and less portable.

---

## 13. Icarus Test Scope

Icarus shall be used for:

- RTL compile checks;
- reset test;
- ALU unit tests;
- decoder tests;
- register-file tests;
- effective-address tests;
- simple instruction smoke tests;
- bus FSM tests;
- selected directed regression tests.

Icarus is **not required to execute the complete million-test SingleStep corpus**.

If doing so later becomes practical, that is optional.

---

## 14. Icarus Compatibility Policy

Portable RTL modules should compile with Icarus unless there is a documented technical reason why they cannot.

The agent should avoid unnecessary use of exotic SystemVerilog features when ordinary synthesizable constructs are sufficient.

However:

> Do not reduce RTL clarity or correctness merely to satisfy a limitation of an old Icarus version.

If Icarus lacks support for a valid construct that materially improves the implementation, document the limitation and isolate it where possible.

---

## 15. Icarus Build Target

Provide a command such as:

```bash
./scripts/test_iverilog.sh
```

or:

```bash
make iverilog
```

At minimum, this target should:

1. compile the portable CPU RTL;
2. compile a basic testbench;
3. reset SPK286;
4. verify the reset vector;
5. perform at least one small instruction test;
6. return a non-zero exit code on failure.

---

## 16. Required Initial Dual-Simulator Test

The first meaningful SPK286 RTL milestone shall pass the same reset test under:

- Verilator;
- Icarus Verilog.

The test shall verify:

```text
visible CS = 0xF000
hidden CS base = 0xFF0000
IP = 0xFFF0
first physical code fetch = 0xFFFFF0
```

This test is intentionally simple but architecturally important.

---

## 17. Python Environment

Python 3 is the preferred automation language.

Expected uses:

- SingleStep data ingestion;
- MOO parsing/conversion;
- JSON tooling;
- regression selection;
- reporting;
- microcode generation;
- generated RTL validation;
- build orchestration where appropriate.

The agent must inspect the installed Python version before choosing features requiring a particular release.

---

## 18. Python Dependency Policy

Prefer the Python standard library where reasonable.

If external dependencies are needed:

- document them;
- pin versions where practical;
- use a project-local dependency file;
- avoid modifying the system Python installation globally.

Preferred mechanisms include:

```text
requirements.txt
```

or another clearly documented project-local method.

Do not create a large framework dependency for simple parsing/reporting tasks.

---

## 19. SingleStepTests/80286 Location

SPK286 should treat `SingleStepTests/80286` as an external verification dependency.

Preferred development layouts include:

```text
workspace/
├── SPK286/
└── SingleStepTests/
```

or:

```text
SPK286/
└── external/
    └── SingleStepTests/
```

The exact location should be configurable.

Do not hard-code an absolute user-specific filesystem path into RTL or test source.

---

## 20. SingleStep Path Configuration

The test runner should allow a path through:

- command-line argument;
- environment variable;
- documented default relative path.

For example:

```bash
export SPK286_SINGLESTEP_PATH=/path/to/SingleStepTests/80286
```

or:

```bash
python3 tools/run_tests.py \
    --singlestep-path ../SingleStepTests/80286
```

The actual naming may differ.

---

## 21. Test Data Conversion

If SingleStep `.MOO` data is not convenient for direct high-speed ingestion, it is acceptable to build a conversion pipeline.

Example:

```text
.MOO
  |
  v
Python converter
  |
  +--> compact binary
  |
  +--> JSON metadata
  |
  v
Verilator runner
```

Requirements:

- conversion must be deterministic;
- original test identity must be preserved;
- revocation/hash metadata must not be discarded;
- conversion must not alter expected values;
- converted data should be regenerable rather than manually edited.

---

## 22. Simulation Memory Model

The initial testbench should use a simple synthetic memory model.

The CPU must not depend on MiSTer SDRAM logic to execute instruction verification.

Memory model requirements:

- byte addressable;
- full 24-bit physical address support;
- 16-bit bus servicing;
- correct upper/lower byte behavior;
- configurable READY;
- deterministic initialization;
- support for code and data in the same address space.

For SingleStep real-mode verification, model the memory assumptions required by that test suite.

---

## 23. I/O Model

Provide a simple simulation I/O-port model independent of PC/AT devices.

Requirements:

- 16-bit I/O address;
- byte and word transfers;
- deterministic read responses;
- captured writes;
- bus transaction visibility.

Do not require a simulated 8259, 8254, 8237, or 8042 to test CPU I/O instructions.

---

## 24. Quartus Prime

Intel Quartus Prime is the synthesis tool for the initial FPGA target.

Primary target family:

- Intel Cyclone V.

Primary target board class:

- DE10-Nano;
- MiSTer FPGA platform.

SPK286 must remain synthesizable independently of a complete MiSTer core.

---

## 25. Quartus Environment Discovery

The agent must inspect whether Quartus is available in the WSL/Linux environment or must be invoked through another established mechanism.

Check:

```bash
quartus_sh --version
```

If unavailable from WSL, inspect the existing project/tooling before introducing a new arrangement.

Do not assume a specific Windows Quartus installation path.

---

## 26. Synthesis Smoke Test

The repository should eventually provide:

```bash
./scripts/synth_cyclonev.sh
```

or an equivalent command.

Early synthesis smoke tests do not need to implement the complete MiSTer wrapper.

They only need to prove that:

- SPK286 portable RTL synthesizes;
- there are no accidental unsynthesizable constructs;
- basic timing/resource reports are generated.

---

## 27. FPGA Resource Reporting

At each major milestone, record at least:

- ALMs / logic utilization;
- registers;
- block RAM;
- DSP usage;
- inferred memories;
- achieved Fmax;
- major timing warnings.

Store reports under a predictable location such as:

```text
build/quartus/
```

and summarize relevant numbers in milestone documentation.

Do not prematurely optimize ALM count before functional correctness is established.

---

## 28. MiSTer Hardware Validation

MiSTer is a **real hardware validation target**, not the initial unit-test environment.

The expected path is:

```text
portable SPK286 RTL
        |
        v
Cyclone V synthesis
        |
        v
minimal MiSTer test wrapper
        |
        v
DE10-Nano / MiSTer
        |
        v
hardware observations
```

SPK286 itself must remain independent from MiSTer-specific framework logic.

---

## 29. MiSTer Integration Layers

MiSTer-specific logic must stay outside the CPU.

Recommended hierarchy:

```text
MiSTer framework
      |
      v
PCAT_MiSTer or test wrapper
      |
      v
SPK286
```

SPK286 should not directly instantiate:

- `hps_io`;
- MiSTer OSD;
- SDRAM framework;
- video pipeline;
- audio pipeline;
- MiSTer PLL definitions;
- user I/O framework.

Those belong in integration-level projects.

---

## 30. First MiSTer Test Harness

Before a full PC/AT exists, a minimal MiSTer-oriented hardware harness may be created.

Possible behavior:

- instantiate SPK286;
- provide small ROM/RAM;
- clock/reset core;
- execute a deterministic test program;
- expose status through:
  - LEDs;
  - debug registers;
  - UART;
  - on-screen debug;
  - SignalTap;
  - another simple observable mechanism.

The exact mechanism is secondary.

The purpose is to prove that CPU RTL functioning in simulation also functions when synthesized into Cyclone V hardware.

---

## 31. MiSTer Is Not the Golden Reference

A successful MiSTer execution does not override a failing SingleStep result.

Correctness hierarchy remains:

```text
Intel 80286 architectural documentation
             +
physical 80286 test evidence
             |
             v
          SPK286
```

MiSTer is the implementation platform, not the behavior specification.

---

## 32. SignalTap / Hardware Debug

Intel SignalTap may be used during Cyclone V debugging.

Potential signals to expose:

- physical address;
- data bus;
- bus status;
- BHE;
- LOCK;
- READY;
- current opcode;
- micro-PC;
- IP;
- CS;
- prefetch count;
- exception vector.

Debug instrumentation should be optional and must not alter architectural behavior.

---

## 33. Linting

Verilator lint can be used initially:

```bash
verilator --lint-only ...
```

The project should provide a documented lint command.

Lint policy should prioritize:

- width mismatches;
- unintended latches;
- undriven signals;
- unused architectural state;
- incomplete combinational assignment;
- suspicious case behavior;
- clock/reset mistakes.

Warnings may be locally suppressed only with explanation.

---

## 34. Formatting

The project should adopt one consistent SystemVerilog style.

Formatting automation is desirable but secondary to correctness.

Do not perform huge style-only rewrites mixed with functional changes.

Code conventions:

- English identifiers;
- English comments;
- lowercase snake_case for signals where practical;
- clear `_q` / `_d` or equivalent sequential-state convention if adopted;
- explicit widths;
- explicit signedness where arithmetic depends on it.

---

## 35. Build Directory Policy

Generated files must stay outside source directories where possible.

Recommended:

```text
build/
├── verilator/
├── iverilog/
├── traces/
├── reports/
├── generated/
└── quartus/
```

Do not commit transient simulator binaries or waveform files.

Generated microcode source intended to be reproducible may follow the policy defined in `SPK286_SPEC.md`.

---

## 36. Recommended Scripts

Initial script set:

```text
scripts/
├── env_check.sh
├── lint.sh
├── build_verilator.sh
├── test_verilator.sh
├── test_iverilog.sh
├── test.sh
└── synth_cyclonev.sh
```

Possible responsibilities:

### `env_check.sh`

Report installed versions and missing dependencies.

### `lint.sh`

Run RTL lint.

### `build_verilator.sh`

Build the reference simulator.

### `test_verilator.sh`

Run fast/default Verilator tests.

### `test_iverilog.sh`

Run secondary simulator smoke tests.

### `test.sh`

Run the normal developer validation set.

### `synth_cyclonev.sh`

Run Cyclone V synthesis smoke test.

---

## 37. Standard Fast Validation

A normal small RTL change should eventually be validated with something equivalent to:

```bash
./scripts/lint.sh
./scripts/test_verilator.sh
./scripts/test_iverilog.sh
```

This should remain reasonably quick.

---

## 38. Standard Full Validation

Before completing a major instruction family or milestone:

```text
lint
  |
  v
unit tests
  |
  v
Verilator directed tests
  |
  v
relevant SingleStep subset
  |
  v
Icarus smoke regression
  |
  v
broader SingleStep regression
  |
  v
Quartus synthesis smoke test
```

Full synthesis is not required after every tiny RTL edit.

---

## 39. Long Regression Policy

The complete SingleStep regression may become expensive.

The test framework shall therefore distinguish:

- smoke;
- targeted;
- quick regression;
- full regression.

Example conceptual levels:

### Smoke

Seconds-scale tests.

### Targeted

Only changed instruction/mechanism.

### Quick regression

Representative sample across instruction families.

### Full regression

All applicable non-revoked SingleStep cases.

The exact test count per tier should be determined once baseline performance is measured.

---

## 40. Parallel Regression

The test system should support parallel execution where possible.

Potential model:

```text
Python orchestrator
      |
      +--> worker 1: opcode range
      +--> worker 2: opcode range
      +--> worker 3: opcode range
      +--> worker N: opcode range
```

Requirements:

- deterministic assignment;
- independent temporary files;
- reproducible failures;
- no shared mutable simulator state.

Do not optimize parallelism before a single-worker regression is correct.

---

## 41. Failure Artifacts

Simulation failures should generate artifacts under:

```text
build/failures/
```

Suggested files:

```text
<test_id>/
├── summary.txt
├── expected.json
├── actual.json
├── bus_expected.txt
├── bus_actual.txt
└── trace.fst
```

Waveform generation can be deferred until reproduction if generating it automatically is too expensive.

---

## 42. No Hidden Tool Assumptions

The agent must not rely on an IDE-specific action to validate SPK286.

A fresh shell should be able to run the documented validation flow.

This is important for:

- AI agents;
- CI;
- reproducibility;
- future contributors.

---

## 43. Git Workflow

Development should use Git from the beginning.

Recommended practices:

- small coherent commits;
- no generated build junk committed;
- no unrelated formatting in functional commits;
- commit messages describing architectural behavior changed;
- record baseline before major refactors.

Do not initialize or alter remote repositories unless explicitly requested.

---

## 44. External Reference Repositories

Reference repositories such as:

- MCL86;
- S80186;
- z386;
- SingleStepTests;

should remain external to the SPK286 source tree unless there is a deliberate reason to vendor something.

Preferred:

```text
workspace/
├── SPK286/
├── references/
│   ├── MCL86/
│   ├── s80x86/
│   └── z386/
└── SingleStepTests/
```

or equivalent.

Never mix reference RTL into `rtl/` merely for convenience.

---

## 45. Reference Code License Safety

Before using source from a reference repository:

1. identify its license;
2. identify the license of the specific file if different;
3. determine whether reuse is compatible with the intended SPK286 license;
4. record the decision in `docs/SOURCE_NOTES.md`.

Reading code for architectural understanding is not the same as copying implementation.

The agent must preserve that distinction.

---

## 46. Environment Configuration File

If environment configuration becomes necessary, prefer an example file committed to the repository.

Example:

```text
config/
└── environment.example
```

with values such as:

```bash
SPK286_SINGLESTEP_PATH=../SingleStepTests/80286
SPK286_BUILD_DIR=./build
```

Do not commit machine-specific absolute paths or secrets.

---

## 47. Continuous Integration Readiness

The local build should be designed so future CI can run:

```text
environment check
lint
Verilator build
unit tests
Icarus smoke test
SingleStep sample
```

without manual interaction.

Quartus CI may be optional because of installation/licensing/resource requirements.

---

## 48. Initial Required Toolchain

The first development phase should require only:

- Git;
- Python 3;
- Verilator;
- C++ compiler/toolchain required by Verilator;
- Icarus Verilog;
- Make or equivalent simple build tool.

Quartus becomes required for synthesis milestones.

MiSTer hardware becomes required for hardware-validation milestones.

This keeps the earliest CPU-development loop fast.

---

## 49. Agent Startup Checklist

Before implementing the first SPK286 milestone, the agent shall:

1. read `SPK286_SPEC.md`;
2. read `SPK286_ENVIRONMENT.md`;
3. inspect repository state;
4. inspect available tools and versions;
5. inspect any existing source before creating duplicates;
6. locate or configure SingleStepTests/80286 if already available;
7. create an environment report;
8. identify missing dependencies;
9. avoid changing the host environment unnecessarily;
10. only then implement the repository/test skeleton.

Recommended environment report:

```text
docs/ENVIRONMENT_DETECTED.md
```

This file may include:

- OS;
- kernel;
- Python;
- Verilator;
- Icarus;
- compiler;
- Quartus;
- SingleStep path;
- relevant limitations.

Do not include personal credentials or machine secrets.

---

## 50. First Milestone Tool Requirements

Milestone 0/1 must demonstrate:

### Verilator

- builds SPK286;
- runs reset test;
- validates first fetch at `0xFFFFF0`.

### Icarus

- compiles the same portable RTL;
- runs equivalent reset smoke test;
- validates first fetch at `0xFFFFF0`.

### Python

- can run the test commands;
- begins SingleStep ingestion infrastructure.

### Quartus

If available at this stage:

- synthesizes the minimal core for Cyclone V.

If Quartus is not currently callable from the working environment:

- do not block the simulation milestone;
- document the limitation;
- preserve synthesizable coding discipline;
- add the synthesis step as soon as the established Quartus environment is available.

---

## 51. MiSTer Validation Milestone

Once meaningful instruction execution exists, create a separate hardware validation target.

The first MiSTer hardware milestone should prove:

1. SPK286 synthesizes into Cyclone V;
2. reset behavior is correct;
3. a small ROM program executes;
4. memory transactions behave correctly;
5. results can be observed externally.

A complete IBM PC/AT is explicitly **not required** for this milestone.

---

## 52. Simulator Disagreement Policy

If Verilator and Icarus produce different results:

1. reduce to a minimal reproducible test;
2. inspect for race/order assumptions;
3. inspect initialization;
4. inspect blocking/non-blocking assignments;
5. check SystemVerilog language semantics;
6. only then determine whether one simulator has a limitation/bug.

Do not simply declare Verilator correct because it is the primary simulator.

The RTL should remain deterministic under correctly implemented language semantics.

---

## 53. FPGA/Simulation Disagreement Policy

If simulation passes but Cyclone V hardware fails:

Investigate:

- reset synchronization;
- clock-domain assumptions;
- inferred RAM differences;
- uninitialized state;
- timing violations;
- combinational loops;
- signal width/sign issues;
- synthesis optimization exposing undefined RTL;
- incorrect external interface timing.

Do not patch hardware behavior with arbitrary delays that are absent from the architectural model.

---

## 54. Deterministic Reset Policy

Simulation and FPGA builds must not rely on arbitrary power-up values for architectural state.

Architecturally defined reset state must be explicitly established.

Non-architectural internal state must either:

- reset deterministically;
- or be proven irrelevant before use.

This is particularly important because simulator initialization can hide FPGA bugs.

---

## 55. Synthesis-Safe Debugging

Simulation-only debug logic should use appropriate guards or separate wrappers so it cannot accidentally become required CPU logic.

Example concept:

```systemverilog
`ifdef SPK286_SIMULATION
    // Simulation-only observability
`endif
```

Use such patterns carefully and consistently.

Architectural state must not differ between simulation and synthesis builds.

---

## 56. Compiler and Warning Hygiene

C++ code used for the Verilator harness should compile with useful warnings enabled.

For example:

```text
-Wall
-Wextra
```

or equivalent reasonable settings.

Do not turn every warning into a fatal error until the baseline is clean enough to make that productive.

---

## 57. Expected Development Loop

The preferred daily development loop is:

```text
read failing test
      |
      v
understand Intel behavior
      |
      v
modify small RTL area
      |
      v
Verilator targeted test
      |
      v
Icarus smoke test
      |
      v
SingleStep subset
      |
      v
inspect trace if needed
      |
      v
commit coherent change
```

Quartus and MiSTer validation are added at milestone boundaries or when the problem is hardware-specific.

---

## 58. Performance Measurement

Do not optimize simulation prematurely, but record baseline performance once the SingleStep runner exists.

Useful measurements:

- tests/second;
- CPU cycles/second simulated;
- single-worker speed;
- parallel scaling;
- memory consumption.

This will guide whether:

- MOO conversion;
- binary caching;
- C++ comparison;
- process sharding;

are worth implementing.

---

## 59. Environment Success Criterion

The environment is considered correctly established when a contributor or agent can enter the SPK286 directory and, using documented commands:

1. inspect environment status;
2. lint the RTL;
3. build Verilator;
4. run the reset test;
5. run the equivalent Icarus reset smoke test;
6. run at least one SingleStep ingestion/test path;
7. optionally synthesize the minimal Cyclone V target if Quartus is available;
8. reproduce any reported failure using a stable test identifier.

---

## 60. Final Environment Rule

The canonical SPK286 validation hierarchy is:

```text
              architectural truth
                       |
          +------------+------------+
          |                         |
 Intel 80286 manuals       physical 80286 traces
          |                         |
          +------------+------------+
                       |
                       v
                 SPK286 RTL
                       |
          +------------+------------+
          |                         |
          v                         v
      Verilator                  Icarus
       primary                  secondary
          |
          v
   large regression
          |
          v
       Quartus
          |
          v
      Cyclone V
          |
          v
       MiSTer
```

Verilator is the primary software simulation environment.

Icarus Verilog is the required secondary simulator.

Quartus verifies synthesizability and implementation on Cyclone V.

MiSTer verifies the synthesized design on real FPGA hardware.

None of these replace the Intel 80286 documentation or hardware-generated reference behavior as the definition of correctness.

## Host build parallelism (Phase 7 tooling)

`SPK286_BUILD_JOBS` controls Verilator's C++ compilation jobs through
`--build-jobs`; it defaults to 1. For example,
`SPK286_BUILD_JOBS=4 SPK286_BUILD_DIR="$PWD/build/a-fresh-name" make phase7-byte-prefix-check`.
This changes host compilation concurrency only, not RTL simulation threading,
architectural results, READY dependencies or the CPU timing policy. Record the
chosen value with validation commands. No toolchain upgrade is required.
