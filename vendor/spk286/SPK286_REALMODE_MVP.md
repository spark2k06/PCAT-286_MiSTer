# SPK286 — Real-Mode MVP Goal

> Scope clarification (pre-Phase 3 audit): the machine-level goals below describe
> downstream validation using SPK286. The current CPU-only boundary in
> `SPK286_SPEC.md` and `AGENTS.md` takes precedence over this
> document's older integration milestones. PC/AT hardware, BIOS packaging, and
> MiSTer machine integration belong in a separate consumer project; they are not
> SPK286 implementation requirements. CPU-owned BIU behavior remains in SPK286.

**Document:** `SPK286_REALMODE_MVP.md`  
**Project:** SPK286  
**Target milestone:** SPK286 v0.1 — Real-Mode MVP  
**Primary platform target:** Intel Cyclone V / DE10-Nano / MiSTer  
**Primary simulator:** Verilator  
**Secondary simulator:** Icarus Verilog  
**Primary hardware validation:** MiSTer  
**Companion documents:**
- `SPK286_SPEC.md`
- `SPK286_ENVIRONMENT.md`
- `SPK286_FIRST_PROMPT.md`

---

# 1. Purpose

This document narrows the full SPK286 vision into a practical first major objective.

The long-term SPK286 specification remains valid, but **full 80286 completeness is not required for the first usable release**.

The first major objective is:

> Build a synthesizable, hardware-validated 80286-compatible real-mode CPU core that can boot an AT-class BIOS and run DOS on MiSTer.

This is the target for **SPK286 v0.1 — Real-Mode MVP**.

The project should not attempt to solve the complete 80286 protected-mode architecture before this milestone is reached.

---

# 2. MVP Success Statement

SPK286 Real-Mode MVP is successful when:

1. SPK286 executes real-mode 80286-compatible code reliably.
2. The implementation is synthesized for Cyclone V.
3. The CPU is integrated into a minimal AT-class MiSTer system.
4. An AT-compatible BIOS executes its POST far enough to initialize the system.
5. The system boots DOS.
6. Representative DOS programs execute correctly.
7. The CPU has substantial automated functional validation against `SingleStepTests/80286`.
8. Known timing differences are documented rather than hidden.

The milestone does **not** require:

- complete 80286 protected mode;
- task switching;
- call gates;
- task gates;
- full TSS behavior;
- LOADALL;
- 80287;
- perfect cycle accuracy for every instruction;
- compatibility with every historical 80286 silicon revision.

---

# 3. Why This Scope Exists

A complete 80286 implementation contains several relatively independent complexity layers:

```text
                 SPK286
                    |
       +------------+-------------+
       |                          |
       v                          v
   Real Mode                 Protected Mode
       |                          |
       |                     descriptors
       |                     privileges
       |                     gates
       |                     TSS
       |                     task switching
       |                     complex faults
       |
       v
     DOS
```

The first layer alone is already useful.

A strong real-mode SPK286 can provide:

- authentic 16-bit x86 execution;
- 24-bit physical addressing;
- native 80286-style bus behavior;
- AT BIOS compatibility;
- DOS compatibility;
- a foundation for later protected mode.

Therefore protected mode is deliberately postponed until the CPU has already become useful.

---

# 4. MVP Design Principle

The first release shall follow:

> **Functional correctness first, bus correctness second, exact cycle fidelity third.**

The priority order for v0.1 is:

1. correct instruction results;
2. correct register state;
3. correct FLAGS behavior;
4. correct memory behavior;
5. correct exception behavior relevant to real mode;
6. correct bus transaction type/order;
7. sufficient bus timing for the AT system;
8. exact cycle matching where practical.

The implementation must never intentionally produce incorrect architectural behavior merely to boot DOS.

However, a documented cycle-count difference is acceptable for v0.1 if software-visible behavior remains correct.

---

# 5. Explicitly In Scope

SPK286 v0.1 includes:

## CPU architecture

- 16-bit general-purpose registers;
- byte register halves;
- segment registers;
- hidden segment state;
- IP;
- 80286 FLAGS semantics relevant to real mode;
- deterministic 80286 reset state;
- 24-bit physical address generation;
- 16-bit native data bus;
- BHE / byte-lane behavior;
- real-mode segmentation;
- effective-address generation;
- 80286 real-mode instruction execution;
- instruction prefixes;
- exceptions relevant to real mode;
- external interrupts;
- NMI;
- HOLD / HLDA;
- READY / wait-state capability;
- LOCK behavior required by supported software;
- instruction prefetch architecture.

## Verification

- Verilator;
- Icarus Verilog;
- directed unit tests;
- SingleStepTests/80286 real-mode integration;
- reproducible failing cases;
- functional comparison;
- memory comparison;
- bus comparison infrastructure;
- optional cycle comparison.

## FPGA

- Cyclone V synthesis;
- MiSTer-compatible integration boundary;
- real hardware execution.

## System-level goal

- minimal AT-class system sufficient for BIOS and DOS;
- BIOS ROM;
- RAM;
- interrupt system;
- timer;
- DMA as required;
- keyboard controller behavior as required;
- CMOS/RTC as required;
- storage path sufficient to boot DOS;
- video path sufficient to observe boot and DOS operation.

---

# 6. Explicitly Out of Scope for v0.1

Do not allow these items to block the MVP:

## Protected mode

Deferred:

- full PE-mode execution;
- GDT;
- LDT;
- IDT protected-mode gate semantics;
- privilege enforcement;
- CPL / DPL / RPL;
- call gates;
- task gates;
- 80286 TSS;
- hardware task switching;
- nested tasks;
- protected-mode stack switching;
- protected-mode fault edge cases.

## Undocumented features

Deferred unless directly required:

- LOADALL;
- unreal-mode behavior;
- undocumented internal state.

## Coprocessor

Deferred:

- full 80287 implementation.

The core may reserve future interface signals.

## Perfect timing

Deferred:

- exact cycle match for every opcode;
- every prefetch corner case;
- every wait-state combination;
- every silicon revision timing difference.

Cycle work is still encouraged where SingleStep provides clear evidence, but exact completeness is not a release blocker.

---

# 7. Long-Term Compatibility Preservation

Although protected mode is deferred, the real-mode architecture must not make it impossible later.

Therefore:

- segment registers must include hidden state;
- the decoder must reserve the `0x0F` system opcode space;
- exception handling must be centralized;
- address generation must support future descriptor-based bases;
- the register/state architecture must allow system registers later;
- the microsequencer must allow complex system instructions later.

Do not implement a "fast shortcut" architecture that would need to be discarded to add protected mode.

The MVP is a reduced feature target, not a disposable prototype.

---

# 8. CPU Identity

SPK286 must remain a dedicated 80286-compatible implementation.

The MVP must not become:

- an 80186 pretending to be a 286;
- a 386 with disabled features;
- ao486 in compatibility mode;
- a software emulator embedded in FPGA logic.

The real-mode subset must still reflect genuine 80286 behavior where observable and documented.

---

# 9. Reset Requirement

Reset is the first mandatory hardware behavior.

Required visible state:

```text
CS = 0xF000
IP = 0xFFF0
```

Required hidden CS base:

```text
0xFF0000
```

Required first physical fetch:

```text
0xFFFFF0
```

This behavior must pass:

- Verilator test;
- Icarus test;
- Cyclone V hardware observation when hardware validation begins.

---

# 10. Real-Mode Instruction Goal

The MVP should support the full instruction set needed by realistic AT BIOS and DOS software.

The intended endpoint is broader than "only enough instructions to boot one BIOS."

Instruction support should converge toward the full published `SingleStepTests/80286/v1_real_mode` corpus.

The implementation must include inherited and 286-supported instruction families such as:

- data movement;
- arithmetic;
- logic;
- shifts and rotates;
- multiplication;
- division;
- stack operations;
- CALL / RET;
- JMP;
- conditional branches;
- LOOP family;
- string operations;
- REP family;
- flag-control operations;
- IN / OUT;
- interrupt instructions;
- BOUND;
- ENTER / LEAVE;
- PUSHA / POPA;
- IMUL forms;
- shifts with immediate counts;
- 80286 instructions usable in real mode.

The exact matrix must live in:

`docs/INSTRUCTION_MATRIX.md`

---

# 11. Instruction Implementation Strategy

Do not implement instructions in random opcode order.

Use dependency-oriented groups.

Recommended progression:

```text
RESET / fetch
     |
     v
MOV / addressing
     |
     v
ALU / FLAGS
     |
     v
stack
     |
     v
control flow
     |
     v
interrupts
     |
     v
string operations
     |
     v
mul/div
     |
     v
I/O
     |
     v
remaining real-mode ISA
```

Each instruction family should be tested before moving to the next major family.

---

# 12. Real-Mode Segmentation

The MVP must support real-mode addressing correctly.

Normal real-mode addressing concept:

```text
physical = segment_base + offset
```

with conventional segment bases typically derived from:

```text
segment << 4
```

However, SPK286 must maintain hidden segment state because:

- reset CS has special base state;
- future protected mode needs it;
- future LOADALL/unreal-mode support may need it.

Do not design segment registers as simple 16-bit values only.

---

# 13. 24-Bit Physical Address Bus

SPK286 must expose a 24-bit physical address interface.

Even though conventional DOS normally operates below 1 MiB, the 80286 physical bus supports 16 MiB.

The architecture must not artificially truncate addresses to 20 bits.

A future AT memory controller may choose how much RAM to populate.

---

# 14. A20 Behavior

A20 gating is primarily a system/chipset concern.

SPK286 should generate its architectural physical address.

The surrounding AT system may implement A20 gating according to PC/AT behavior.

Do not put PC/AT-specific A20 keyboard-controller behavior inside the CPU.

This separation is important:

```text
SPK286 physical address
          |
          v
AT system A20 logic
          |
          v
RAM
```

---

# 15. Bus Accuracy Goal

For the MVP, the bus should accurately represent:

- code fetch;
- memory read;
- memory write;
- I/O read;
- I/O write;
- interrupt acknowledge;
- BHE;
- address;
- data;
- LOCK;
- READY;
- HOLD / HLDA.

The bus must be usable by a future/parallel AT chipset implementation.

Exact T-state matching is desirable but not mandatory for every instruction in v0.1.

---

# 16. Prefetch Goal

The real-mode MVP needs a working 80286-appropriate instruction prefetch mechanism.

Target:

- six-byte queue architecture;
- refill behavior;
- control-transfer flush;
- interaction with bus availability;
- deterministic operation.

SingleStep's current testing methodology does not fully validate arbitrary queue history.

Therefore prefetch requires both:

- SingleStep-visible validation;
- custom directed tests.

Perfect reconstruction of every internal timing edge is not required before DOS boot.

---

# 17. FLAGS Accuracy

FLAGS errors frequently break real software while appearing harmless in simple tests.

The MVP must prioritize correct behavior for:

- CF;
- PF;
- AF;
- ZF;
- SF;
- TF;
- IF;
- DF;
- OF;
- relevant 80286 system flag state.

Undefined/reserved bits must not be forced to 386 behavior without evidence.

SingleStep comparisons should validate FLAGS aggressively.

---

# 18. Exceptions Required for MVP

The real-mode CPU must correctly support exceptions encountered by BIOS and DOS diagnostics.

At minimum investigate and implement:

- divide error;
- single-step/debug behavior when needed;
- NMI;
- breakpoint;
- overflow;
- BOUND range exceeded;
- invalid opcode;
- processor extension unavailable;
- other real-mode-visible 80286 exceptions required by documentation/tests.

Exception ordering and saved state matter.

Do not simply redirect all exceptional conditions to generic software interrupts.

---

# 19. External Interrupts

INTR and NMI are required for the eventual AT system.

The MVP must eventually support:

- INTR sampling;
- interrupt acknowledge bus cycles;
- vector acquisition;
- FLAGS/CS/IP stack frame behavior;
- IF semantics;
- NMI handling.

Integration with dual 8259 PICs belongs to the AT system, not the CPU.

---

# 20. READY / Wait States

READY support is required for hardware integration.

The initial SingleStep corpus may not insert wait states, but the CPU architecture must allow them.

Directed tests should verify:

- read wait states;
- write wait states;
- code-fetch wait states;
- state retention while waiting.

Exact historical timing tuning may continue after DOS first boots.

---

# 21. HOLD / HLDA

The CPU must eventually support HOLD/HLDA sufficiently for AT DMA.

This may be implemented after initial instruction execution works, but before declaring the AT/DOS hardware milestone complete.

Do not remove this capability from the bus interface because early CPU-only tests do not need it.

---

# 22. LOCK

LOCK must exist in the architectural bus interface.

Implement enough behavior to support legal real-mode locked operations and BIOS/DOS software.

Precise rare edge cases may be refined after the main MVP if they are not required by current tests/software.

All known deviations must be documented.

---

# 23. Verification Philosophy

The MVP uses multiple verification levels.

## Level 1 — Unit

Test isolated modules:

- ALU;
- FLAGS;
- effective address generation;
- decoder;
- prefetch;
- register file;
- bus FSM.

## Level 2 — Directed instruction tests

Run small handcrafted instruction programs.

## Level 3 — SingleStep functional validation

Compare:

- initial state;
- final registers;
- final FLAGS;
- memory changes.

## Level 4 — SingleStep bus validation

Compare:

- transaction type;
- address;
- data;
- BHE;
- ordering;
- LOCK.

## Level 5 — Cycle validation

Compare detailed cycle states where useful.

## Level 6 — Software integration

Run:

- BIOS POST;
- DOS;
- CPU diagnostics;
- representative DOS programs.

No single level replaces the others.

---

# 24. SingleStep MVP Requirement

The Real-Mode MVP should aim for very high functional coverage of the currently published real-mode dataset.

The project should report separate metrics:

```text
Tests parsed
Tests executed
Functional pass
Memory pass
Bus pass
Cycle pass
Known revoked/skipped
Known core bugs
Known harness bugs
```

Do not report a single misleading percentage that mixes unsupported and untested cases.

---

# 25. SingleStep Acceptance Philosophy

For v0.1:

### Required

- no unexplained broad functional failures;
- no systematic register corruption;
- no systematic FLAGS corruption;
- no systematic addressing errors;
- no hidden test exclusions used to create artificial success.

### Strongly desired

- near-complete functional pass rate;
- high bus transaction agreement.

### Not mandatory for release

- 100% exact cycle trace agreement.

Any remaining cycle mismatches must be categorized and documented.

---

# 26. Verilator Role

Verilator is the main regression engine.

The test infrastructure should eventually support:

```bash
python3 tools/run_tests.py --smoke
python3 tools/run_tests.py --opcode MOV
python3 tools/run_tests.py --test-id <id>
python3 tools/run_tests.py --all --jobs <n>
```

The full suite must be reproducible and parallelizable.

---

# 27. Icarus Role

Icarus remains a secondary correctness/portability check.

Required coverage:

- RTL compile;
- reset;
- major unit tests;
- selected instruction tests;
- selected regressions.

The entire SingleStep suite does not need to run through Icarus.

---

# 28. Cyclone V Synthesis

SPK286 Real-Mode MVP must synthesize for Cyclone V.

Resource usage should be measured but not aggressively optimized before correctness.

Track:

- ALMs;
- registers;
- block RAM;
- DSPs;
- Fmax.

The CPU should leave enough room for the surrounding PC/AT system.

No hard resource ceiling is imposed initially.

---

# 29. MiSTer Relationship

SPK286 remains a standalone CPU.

MiSTer integration belongs above it.

Expected layering:

```text
MiSTer framework
       |
       v
PCAT_MiSTer
       |
       v
SPK286
```

The CPU repository may include a small Cyclone V/MiSTer validation wrapper, but MiSTer framework logic must not infect the CPU architecture.

---

# 30. PCXT_MiSTer as Reference

PCXT_MiSTer should be used as an important reference for the future AT system.

Study/reuse where legally appropriate:

- MiSTer top-level organization;
- `emu` conventions;
- HPS integration;
- OSD;
- ROM loading;
- SDRAM plumbing;
- video/audio infrastructure;
- Quartus project organization;
- timing constraints;
- build/release structure.

Do not reuse XT architectural assumptions merely because the infrastructure is convenient.

---

# 31. PCAT_MiSTer MVP

The CPU milestone and system milestone can overlap, but they remain conceptually separate.

A minimal `PCAT_MiSTer` target for the first DOS boot should contain only what is necessary.

Likely major blocks:

```text
                     SPK286
                        |
                        v
                  AT bus/chipset
                        |
       +----------------+----------------+
       |                |                |
       v                v                v
      RAM              ROM              ISA
                                         |
                     +-------------------+------------------+
                     |                   |                  |
                     v                   v                  v
                    PIC                 PIT                DMA
                     |
                     +--> keyboard / RTC / storage / video
```

Do not attempt historical perfection of every peripheral before BIOS progress can be measured.

---

# 32. AT System Priority

For the first BIOS/DOS boot, prioritize system components by actual boot dependency.

Likely sequence:

1. CPU + ROM + RAM;
2. chipset memory mapping;
3. interrupt controllers;
4. PIT;
5. keyboard controller/A20 behavior;
6. CMOS/RTC;
7. video;
8. storage boot path;
9. DMA features required by selected storage/peripherals;
10. remaining ISA completeness.

The exact order should be driven by BIOS execution traces.

---

# 33. BIOS Strategy

The first BIOS should be chosen for:

- legal availability;
- compatibility with the implemented AT target;
- debugging practicality;
- known behavior under emulators/real hardware.

Do not hard-code SPK286 around one BIOS implementation.

The goal is eventual compatibility with multiple suitable AT BIOSes.

The initial BIOS is a validation target, not part of the CPU architecture.

---

# 34. DOS Boot Goal

The first major system milestone is:

> Reach a DOS command prompt using SPK286 on MiSTer.

A successful boot should include:

- BIOS POST;
- memory detection;
- interrupt/timer initialization;
- storage boot;
- DOS kernel initialization;
- command interpreter prompt.

Record boot logs and known workarounds.

Do not call a system "DOS compatible" if it only reaches the boot sector and fails immediately afterward.

---

# 35. Post-Boot Software Validation

After reaching DOS, test representative workloads.

Suggested categories:

- CPU detection utility;
- memory utility;
- arithmetic-heavy program;
- string-heavy program;
- file I/O;
- timer-dependent software;
- keyboard input;
- simple graphics/text software;
- compiler/interpreter workload;
- one or more period games or applications.

The exact programs must be legally usable.

---

# 36. BIOS/DOS Is Not the Only CPU Test

Boot success is a powerful integration signal but can hide CPU defects.

Continue SingleStep regression even after DOS boots.

A BIOS may simply never exercise a broken instruction.

The release requires both:

```text
instruction-level evidence
            +
system-level evidence
```

---

# 37. Cycle Accuracy Policy for v0.1

Cycle accuracy is **progressive**.

Classify instruction timing status:

- `functional_only`
- `bus_compatible`
- `cycle_close`
- `cycle_verified`

Do not delay DOS boot because an obscure instruction has one extra internal cycle unless it affects real software or bus compatibility.

However, do not abandon timing research.

The long-term specification still targets high hardware fidelity.

---

# 38. Performance Modes

Do not create an accelerated CPU mode before compatible operation is stable.

For v0.1, one correct implementation mode is enough.

An accelerated mode may be added later.

---

# 39. MVP Milestones

## RM0 — Foundation

Deliver:

- repository;
- docs;
- Verilator;
- Icarus;
- reset;
- first fetch `0xFFFFF0`;
- SingleStep loader foundation;
- Cyclone V synthesis skeleton.

---

## RM1 — Basic execution

Deliver:

- prefetch foundation;
- decoder;
- MOV;
- register addressing;
- memory addressing;
- basic ALU;
- FLAGS.

Target:

- execute small synthetic programs.

---

## RM2 — Core control flow

Deliver:

- stack;
- PUSH/POP;
- JMP;
- CALL/RET;
- conditional branches;
- LOOP;
- segment operations.

Target:

- execute non-trivial real-mode test programs.

---

## RM3 — BIOS-capable instruction set

Deliver:

- remaining arithmetic/logical families;
- shifts/rotates;
- string operations;
- interrupts;
- I/O;
- multiply/divide;
- 80186/286 real-mode instruction additions needed by BIOS.

Target:

- start executing an AT BIOS meaningfully.

---

## RM4 — SingleStep functional convergence

Deliver:

- broad real-mode corpus execution;
- failure classification;
- instruction matrix;
- very high functional correctness.

Target:

- eliminate architecture-level failures before relying on BIOS behavior.

---

## RM5 — AT bus readiness

Deliver:

- READY;
- HOLD/HLDA;
- LOCK;
- interrupt acknowledge;
- robust byte lanes;
- stable bus contract.

Target:

- CPU ready for PCAT_MiSTer integration.

---

## RM6 — Minimal PCAT_MiSTer bring-up

Deliver:

- CPU integration;
- BIOS ROM;
- RAM;
- minimum chipset infrastructure;
- observable POST progress.

Target:

- BIOS starts and executes on real MiSTer hardware.

---

## RM7 — BIOS POST completion

Deliver missing AT components based on actual BIOS requirements.

Target:

- complete or near-complete POST;
- reach boot-device execution.

---

## RM8 — DOS boot

Deliver:

- storage boot path;
- required interrupts/timing;
- stable runtime.

Target:

- DOS command prompt on MiSTer.

This is the **SPK286 v0.1 Real-Mode MVP system goal**.

---

## RM9 — Stabilization

Deliver:

- regression cleanup;
- representative DOS software tests;
- synthesis/resource reports;
- known limitations;
- release documentation.

Target:

- reproducible v0.1 release.

---

# 40. Stop Conditions

If development discovers that one subsystem is significantly harder than expected, do not automatically expand scope.

Examples:

### Protected mode needed unexpectedly

Confirm whether the selected BIOS/software truly requires it.

Prefer a real-mode-compatible validation target before implementing protected mode solely to unblock one program.

### Exact timing blocks boot

Fix the required timing behavior.

Do not generalize immediately into total cycle-perfect implementation unless evidence requires it.

### One peripheral blocks PCAT boot

Implement the minimum accurate peripheral behavior required, then continue.

Avoid unrelated peripheral completeness work.

---

# 41. Deferred Backlog After v0.1

After the Real-Mode MVP is stable, possible v0.2+ work includes:

- protected-mode infrastructure;
- system instructions;
- descriptors;
- privilege checks;
- protected interrupts;
- task switching;
- LOADALL;
- 80287;
- deeper cycle convergence;
- multiple 286 speed grades;
- expanded AT peripheral fidelity;
- alternate BIOS compatibility.

This backlog must not distract the v0.1 implementation agent.

---

# 42. Definition of Done — CPU Real-Mode MVP

The CPU-only portion is considered MVP-ready when:

- reset is correct;
- Cyclone V synthesis succeeds;
- real-mode instruction coverage is broad enough for AT BIOS/DOS;
- SingleStep functional regression is highly successful;
- memory addressing is reliable;
- FLAGS are reliable;
- interrupts work;
- I/O instructions work;
- bus interface is stable;
- READY is supported;
- HOLD/HLDA is supported enough for AT integration;
- LOCK support is sufficient for tested software;
- known deviations are documented.

---

# 43. Definition of Done — System Real-Mode MVP

The overall v0.1 milestone is done when:

- SPK286 runs on MiSTer;
- AT-class BIOS executes successfully;
- DOS reaches a command prompt;
- basic keyboard/timer/storage operation works;
- representative DOS software runs;
- no hidden software emulator substitutes for CPU functionality;
- known limitations are documented;
- build and validation procedures are reproducible.

---

# 44. Non-Goals That Must Not Delay v0.1

Do not hold the release for:

- OS/2 protected mode;
- Windows/286 protected mode;
- Xenix protected mode;
- exact hardware task switching;
- every 80287 feature;
- exact timing of every undocumented corner case;
- LOADALL;
- exotic multi-fault protected-mode behavior.

Those are later achievements.

---

# 45. Agent Decision Rule

When choosing between two implementation tasks, prefer the task that most directly advances one of:

```text
SingleStep functional correctness
             |
             v
real-mode instruction completeness
             |
             v
stable CPU bus
             |
             v
AT BIOS execution
             |
             v
DOS boot on MiSTer
```

If a task does not materially advance that path, question whether it belongs before v0.1.

---

# 46. Progress Reporting

Each milestone report should include:

```text
CPU:
- implemented instruction forms
- SingleStep tests executed
- functional pass rate
- bus pass rate
- cycle pass rate

FPGA:
- ALM usage
- RAM usage
- DSP usage
- Fmax

System:
- BIOS execution milestone
- POST code reached
- boot stage reached

Known issues:
- architectural
- bus
- timing
- MiSTer integration
```

This keeps progress measurable.

---

# 47. Recommended Project Labels

Use clear milestone terminology.

Suggested:

```text
SPK286 v0.0.x  foundational development
SPK286 v0.1    Real-Mode MVP
SPK286 v0.2    timing / compatibility refinement
SPK286 v0.3+   protected-mode development
SPK286 v1.0    complete project-defined 80286 target
```

Versioning may change later, but the distinction between v0.1 real mode and full 80286 completion should remain explicit.

---

# 48. Practical Guiding Question

At every stage before v0.1, ask:

> Does this work make SPK286 more likely to execute real 80286 real-mode software correctly and boot DOS on MiSTer?

If the answer is no, it is probably not a priority for the MVP.

---

# 49. Final MVP Goal

The first great objective of SPK286 is therefore:

> **SPK286 v0.1 shall be a standalone, synthesizable, real-mode 80286-compatible FPGA soft-core, validated extensively against physical 80286 SingleStep test data, integrated into an AT-class MiSTer system, and capable of booting and running DOS.**

Protected mode remains a long-term project goal.

It is not a prerequisite for proving that SPK286 is already a useful and technically meaningful CPU core.
