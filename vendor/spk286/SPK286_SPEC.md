# SPK286 — Intel 80286-Compatible FPGA Soft-Core Specification

**Document:** `SPK286_SPEC.md`  
**Project:** SPK286  
**Status:** Updated engineering specification  
**Primary implementation language:** SystemVerilog  
**Primary initial FPGA target:** Intel Cyclone V / DE10-Nano class hardware  
**Primary verification target:** Verilator + SingleStepTests/80286  
**Long-term integration target:** Reusable standalone 80286 CPU IP; PC/AT and MiSTer system cores are separate downstream projects

---

## 1. Purpose

SPK286 is an open-source, synthesizable SystemVerilog implementation of the Intel 80286 architecture.

The project shall aim for:

1. **Architectural compatibility** with a real Intel-compatible 80286.
2. **Behavioral compatibility** at instruction, register, flag, exception, and memory levels.
3. **Bus-level compatibility** with the observable 80286 local bus.
4. **Cycle-level compatibility** where the available hardware-generated reference traces allow it.
5. A design that is **portable**, **testable**, **modular**, and usable independently of any specific PC/AT implementation.
6. A timing architecture in which **functional semantics are independent from timing policy**, allowing both historically compatible operation and accelerated execution from the same CPU implementation.

SPK286 is a CPU-only project. It must not be coupled internally to MiSTer, IBM PC/AT chipset logic, VGA, audio, storage, BIOS implementation details, or other motherboard/peripheral logic.

The SPK286 repository ends at the CPU boundary: architectural execution, microcode, prefetch, segmentation/protection, exceptions, the Bus Interface Unit, and the native external CPU interface.

Any eventual PC/AT or MiSTer system shall be developed as a separate project that consumes SPK286 as a replaceable CPU component.

---

## 2. Project Definition

SPK286 is **not**:

- an 80386 core artificially restricted to 16-bit operation;
- ao486 configured to look like a 286;
- a 80186 core with extra opcodes;
- an instruction-level emulator implemented in software;
- a high-level x86-compatible CPU that ignores original 80286 timing and bus behavior in compatibility mode;
- a PC/AT core itself.

SPK286 **is**:

> A dedicated FPGA soft-core implementing the Intel 80286 programming model, segmentation architecture, protection model, bus semantics, instruction behavior, exceptions, and—where practical and verifiable—observable timing characteristics.

SPK286 shall use one functional CPU architecture with a separable timing-policy layer.

Compatibility/Accurate modes must reproduce 80286-observable behavior as closely as available evidence permits.

Accelerated modes may remove historical timing delays while preserving architectural semantics and all real dependencies such as READY, BIU availability, operand completion, prefetch availability, bus ownership, and required serialization.

The implementation may use modern FPGA techniques internally, but compatibility modes must follow the 80286 rather than a later x86 processor.

### 2.1 Project boundary and downstream consumption

SPK286 shall remain a standalone CPU-development project comparable in scope to
a reusable processor IP core.

The following belong **inside SPK286**:

- CPU top-level RTL;
- Execution Unit and datapath;
- register file and FLAGS machinery;
- decoder and microsequencer;
- project-owned microcode source;
- deterministic microcode compiler/tooling;
- generated microcode ROM/image;
- prefetch/instruction unit;
- effective-address generation;
- segmentation and protection logic;
- interrupt/exception machinery;
- Bus Interface Unit;
- native 80286-style external bus behaviour;
- READY, HOLD/HLDA, LOCK, INTR/NMI and INTA-related CPU behaviour;
- CPU-only simulation, verification, synthesis-smoke and debug infrastructure;
- SingleStepTests/80286 integration;
- documentation needed to integrate SPK286 as an external CPU component.

The following are explicitly **outside SPK286** and belong to separate system
projects:

- IBM PC/AT motherboard/chipset implementation;
- PIC;
- PIT;
- DMA controller;
- 8042 keyboard controller;
- RTC/CMOS;
- ISA backplane/device integration;
- video, audio and storage subsystems;
- PC/AT BIOS selection or ROM mapping policy;
- MiSTer framework integration;
- MiSTer `emu` top level, OSD and HPS integration;
- MiSTer-specific SDRAM/system arbitration;
- complete machine clock trees unrelated to the CPU itself.

A future project such as `PCAT286_MiSTer` may consume a released SPK286 CPU
package. That package should provide a documented set of synthesizable RTL files
and a deterministic generated microcode image suitable for downstream builds.

Conceptually:

```text
SPK286 repository
    |
    +--> authoritative microcode source
    +--> microcode compiler
    +--> generated spk286 microcode image
    +--> CPU RTL
          |
          +--> EU / datapath
          +--> decoder / microsequencer
          +--> prefetch
          +--> segmentation / protection
          +--> BIU
          +--> native CPU interface
    |
    +--> tests / SingleStep / documentation
    |
    +========== project boundary ==========
                    |
                    v
          separate consumer project
             PCAT286_MiSTer
                    |
          +---------+---------+
          |         |         |
        SPK286   AT chipset   peripherals
```

The downstream project must not be required to contain the SPK286 microcode
source/compiler in order to synthesize a released CPU package, although those
sources remain authoritative and public inside SPK286.

The exact export manifest may evolve, but it shall be documented and
reproducible.

---

## 3. Source Hierarchy and Research References

The implementation agent must use the following source hierarchy when resolving behavior.

### 3.1 Tier 1 — Primary architectural references

Intel 80286 documentation is the primary source for defined architectural behavior.

Recommended documents:

- **80286 Hardware Reference Manual (1987)**
- **80286 and 80287 Programmer's Reference Manual (1987)**
- **iAPX 286 Programmer's Reference Manual**
- **iAPX 286 Operating Systems Writer's Guide**

Archive:

- https://www.bitsavers.org/components/intel/80286/

For conflicts involving documented architectural behavior, Intel documentation takes precedence over modern software emulators or unrelated HDL cores.

### 3.2 Tier 2 — Physical 80286 behavior

SingleStepTests/80286 is the primary empirical reference for real-mode instruction and bus behavior.

Repository:

- https://github.com/SingleStepTests/80286

The currently published real-mode tests were generated using a physical:

- **Harris N80C286-12**

The repository states that the real-mode suite contains:

- 326 instruction forms;
- nearly 1.5 million instruction executions;
- more than 32 million captured cycle states;
- initial and final register state;
- initial and final memory state;
- address bus values;
- data bus values;
- bus controller status;
- pin state;
- processor T-state.

These traces are exceptionally important to SPK286 and must be integrated into the automated verification workflow.

### 3.3 Tier 3 — Architectural implementation references

The following projects are references for engineering ideas, decomposition, testing methods, and microsequenced FPGA design.

They are **not automatically authorized code sources**.

#### MCL86

- https://github.com/MicroCoreLabs/Projects/tree/master/MCL86
- https://microcorelabs.com/2016/03/03/lots-of-interest-in-the-mcl86-core/

Relevant concepts:

- microsequencer-based execution;
- separation of Execution Unit and Bus Interface Unit;
- small microcode-oriented FPGA implementation;
- optional cycle-compatible behavior;
- strong separation between instruction execution and physical bus handling;
- separation between functional instruction sequencing and compatibility timing.

MCL86 is explicitly described by its author as a microsequencer-based, structurally compatible and cycle-compatible 8086/8088 soft IP core.

#### S80186 / s80x86

- https://github.com/jamieiles/80x86

Relevant concepts:

- clean synthesizable SystemVerilog organization;
- verification methodology;
- C++ reference model strategy;
- extensive automated testing;
- Cyclone V synthesis;
- instruction/decode/execution separation;
- build automation and reproducible development environment.

S80186 is **not** an 80286 implementation and is explicitly not cycle-compatible with one.

#### z386

- https://github.com/nand2mario/z386
- https://github.com/nand2mario/z386_MiSTer

Relevant concepts:

- microcode-driven x86 FPGA architecture;
- prefetch subsystem;
- decoder organization;
- bus interface organization;
- segmentation unit decomposition;
- protection unit decomposition;
- separation of architectural mechanisms into small synthesizable modules;
- practical Cyclone V / MiSTer integration.

z386 is a 386-class implementation and must not be used as evidence that a behavior is valid for the 80286.

Only mechanisms that are also verified against 80286 documentation or hardware behavior may be carried into SPK286.

---

## 4. Licensing Rule

Before copying or adapting source code from any reference implementation, the agent **must explicitly inspect and record its license**.

Current known constraints:

- `jamieiles/80x86` is GPL-3.0.
- `SingleStepTests/80286` is published under MIT.
- MCL86 and z386 must be treated as **reference-only** until their applicable source licenses are explicitly confirmed for the files being considered.

Unless the SPK286 repository owner explicitly chooses a compatible license:

> Do not copy RTL, microcode, tables, generated source, or substantial implementation fragments from MCL86, S80186, z386, or another CPU core.

It is acceptable to study architecture, interfaces, testing methodology, module boundaries, and published documentation and then create an independent implementation.

The agent must maintain a file such as:

`docs/SOURCE_NOTES.md`

recording:

- source consulted;
- URL;
- license;
- what concept was learned;
- whether any code was reused;
- justification for license compatibility if code was reused.

---

## 5. Design Philosophy

SPK286 shall favor **correctness before speed**.

Priority order:

1. architectural correctness;
2. deterministic verification;
3. real hardware behavior;
4. bus correctness;
5. cycle correctness;
6. maintainability;
7. FPGA resource efficiency;
8. maximum clock frequency.

Do not optimize away behavior that is visible to software or to the external bus.

Do not introduce 386 behavior merely because it is easier to implement.

Functional semantics and historical timing policy must remain separable.

Do not encode historical timing by scattering semantically meaningless idle/NOP states through instruction-specific RTL or microcode when the delay belongs in the timing-policy mechanism.

When Intel documentation and a physical SingleStep trace disagree, the discrepancy must be investigated and documented rather than silently selecting one.

---

## 6. High-Level Architecture

The preferred architecture is a microsequenced CPU with clear functional separation.

Suggested top-level decomposition:

```text
                         +----------------------+
                         |       SPK286         |
                         |                      |
       instruction ----->| Instruction Unit     |
       stream            | - prefetch           |
                         | - decoder            |
                         +----------+-----------+
                                    |
                                    v
                         +----------+-----------+
                         | Microsequencer       |
                         | Internal microcode   |
                         +-----+----------+-----+
                               |          |
                    +----------+          +-------------+
                    v                                   v
          +---------+---------+              +----------+---------+
          | Execution Unit    |              | Address / Protect  |
          | - registers       |              | Unit               |
          | - ALU             |              | - segmentation     |
          | - flags           |              | - descriptors      |
          | - shifts          |              | - privilege        |
          | - mul/div         |              | - limit checks     |
          +---------+---------+              +----------+---------+
                    |                                   |
                    +----------------+------------------+
                                     |
                                     v
                           +---------+---------+
                           | Bus Interface Unit|
                           | - memory          |
                           | - I/O             |
                           | - code fetch      |
                           | - INTA            |
                           | - bus timing      |
                           | - HOLD/HLDA       |
                           +-------------------+
```

This organization is inspired by the separation seen in original x86 processors and by useful patterns in MCL86 and z386, but SPK286 must define its own implementation.

The timing-policy architecture is specified in `SPK286_TIMING_MODEL.md`.

The number of functional RTL states or microinstructions used to implement an operation must not automatically define its historical 80286 cycle count.

---

## 7. Required RTL Characteristics

The core shall be:

- written primarily in synthesizable SystemVerilog;
- free of vendor-specific primitives in architectural modules;
- lintable;
- Verilator-compatible;
- synthesizable with Intel Quartus for Cyclone V;
- designed so other FPGA targets can be added later.

Vendor-specific PLL, RAM, or timing wrappers must remain outside the portable CPU implementation wherever practical.

All source identifiers and code comments shall be written in English.

---

## 8. Proposed Repository Structure

Recommended initial structure:

```text
SPK286/
├── README.md
├── LICENSE
├── docs/
│   ├── SPK286_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── BUS_INTERFACE.md
│   ├── INSTRUCTION_MATRIX.md
│   ├── PROTECTED_MODE.md
│   ├── SPK286_TIMING_MODEL.md
│   ├── TIMING_NOTES.md
│   ├── SOURCE_NOTES.md
│   └── VERIFICATION.md
├── rtl/
│   ├── spk286.sv
│   ├── spk286_pkg.sv
│   ├── instruction_unit.sv
│   ├── prefetch_queue.sv
│   ├── decoder.sv
│   ├── microsequencer.sv
│   ├── microcode_rom.sv
│   ├── register_file.sv
│   ├── alu.sv
│   ├── shifter.sv
│   ├── muldiv.sv
│   ├── effective_address.sv
│   ├── segmentation_unit.sv
│   ├── descriptor_unit.sv
│   ├── protection_unit.sv
│   ├── exception_unit.sv
│   ├── bus_interface.sv
│   └── debug_state.sv
├── microcode/
│   ├── README.md
│   ├── source/
│   └── generated/
├── sim/
│   ├── verilator/
│   ├── unit/
│   └── system/
├── tests/
│   ├── singlestep/
│   ├── directed/
│   ├── regressions/
│   └── protected_mode/
├── tools/
│   ├── singlestep_runner.py
│   ├── moo_to_spk.py
│   ├── trace_compare.py
│   └── microcode/
├── fpga/
│   └── de10_nano/
└── scripts/
    ├── build.sh
    ├── test.sh
    └── lint.sh
```

This is a recommendation, not an immutable requirement. Module boundaries may change when justified by implementation evidence.

Any `fpga/de10_nano` or similar directory inside SPK286 is limited to CPU-only
synthesis, pin/interface experiments, or smoke-test harnesses. It must not grow
into a MiSTer PC/AT machine implementation.

---

## 9. Programmer-Visible Register Model

SPK286 shall implement the 80286 programmer-visible state.

### 9.1 General registers

16-bit:

- AX
- BX
- CX
- DX
- SP
- BP
- SI
- DI

Byte-accessible halves where architecturally applicable:

- AH / AL
- BH / BL
- CH / CL
- DH / DL

### 9.2 Segment registers

- CS
- DS
- SS
- ES

Each segment register must be represented internally by:

1. the programmer-visible 16-bit value;
2. the hidden descriptor/cache state required by the 80286 architecture.

Do not model segment registers merely as `segment << 4`.

Even in real mode, the hidden base/limit state matters for reset behavior and for transitions involving protected or LOADALL-based states.

### 9.3 Instruction pointer

- IP, 16-bit.

### 9.4 FLAGS

Implement 80286 FLAGS semantics, including:

- CF
- PF
- AF
- ZF
- SF
- TF
- IF
- DF
- OF
- IOPL
- NT

Reserved/fixed flag behavior must match 80286 rules rather than later x86 behavior.

### 9.5 System state

Protected-mode-capable implementation must eventually include:

- MSW / machine status state;
- GDTR;
- IDTR;
- LDTR;
- TR;
- hidden descriptor cache state;
- privilege state;
- task state required by 80286 semantics.

Do not expose 80386-only architectural registers such as EIP, EFLAGS, CR2, CR3, 32-bit general registers, or paging state.

---

## 10. Reset Behavior

Reset behavior is an essential compatibility requirement.

After reset, SPK286 shall reproduce the documented 80286 reset state, including the unusual reset code-segment base behavior.

Critical boot behavior:

- CS visible value: `0xF000`
- IP: `0xFFF0`
- hidden CS base: `0xFF0000`
- initial physical instruction address: `0xFFFFF0`

This behavior is different from a simple real-mode calculation of:

```text
CS << 4 + IP
```

and must be explicitly represented by the hidden segment cache.

The reset state of FLAGS, MSW, descriptor tables, queue state, and other internal architectural state shall be taken from Intel 80286 documentation and verified where possible against known hardware behavior.

A reset unit test must verify the first external code fetch address.

---

## 11. Address Space

### 11.1 Physical address width

The core shall implement:

- **24-bit physical addresses**
- maximum physical space: **16 MiB**

External memory address interface:

```systemverilog
logic [23:0] address;
```

### 11.2 Data bus

Native CPU data width:

- 16 bits

Byte and word transactions must honor address alignment and upper/lower byte selection.

### 11.3 I/O address space

Implement the 80286 I/O addressing model and 16-bit I/O port space as defined by the architecture.

---

## 12. Native Bus Interface

SPK286 shall expose enough information to reproduce a native 80286-style local bus and to compare directly against SingleStepTests cycle traces.

At minimum, the native-facing interface shall represent:

### Inputs

- clock;
- reset;
- READY;
- HOLD;
- INTR;
- NMI;
- external data input;
- coprocessor-related inputs if/when 80287 support is enabled.

### Outputs

- A23:A0;
- D15:D0 output;
- data output-enable / direction;
- BHE;
- bus status corresponding to:
  - S0;
  - S1;
  - M/IO;
  - COD/INTA;
- LOCK;
- HLDA;
- processor extension handshake outputs if enabled.

The internal representation may use active-high normalized signals, but a wrapper must be able to produce original active-low pin semantics.

---

## 13. Bus Cycle Types

The Bus Interface Unit must support and distinguish at least:

- code fetch;
- memory read;
- memory write;
- I/O read;
- I/O write;
- interrupt acknowledge;
- halt/passive state.

SingleStepTests uses decoded bus-state labels including:

- `INTA`
- `IOR`
- `IOW`
- `MEMR`
- `MEMW`
- `HALT`
- `CODE`
- `PASV`

The verification wrapper should generate comparable labels from SPK286 bus signals.

---

## 14. Byte Enable and Alignment

BHE behavior must be implemented accurately.

The core must correctly support:

- even-address word transfers;
- odd-address byte transfers using the upper byte lane;
- even-address byte transfers using the lower byte lane;
- unaligned word accesses requiring the appropriate physical bus sequence.

The inactive half of the data bus must not influence functional verification.

Bus lane handling must be validated against SingleStepTests traces.

---

## 15. READY and Wait States

SPK286 shall architecturally support READY-driven wait states even though the current SingleStep real-mode suite states that its tests do not insert wait states.

Requirements:

- READY must be sampled at the correct part of the bus-cycle state machine;
- wait states must not corrupt bus status;
- the CPU must not commit memory-dependent state before the read transaction has completed;
- READY is a real dependency and must be honored in Accurate, Fast, and Max modes;
- the implementation shall include directed READY/wait-state tests independent of SingleStep.

---

## 16. HOLD / HLDA

The core shall implement external bus arbitration compatible with the 80286 HOLD/HLDA model.

Requirements:

- recognize HOLD;
- complete or suspend transactions according to documented rules;
- grant the bus through HLDA;
- preserve CPU architectural state;
- resume correctly when HOLD is released.

DMA-oriented system integration depends on this behavior.

Exact cycle behavior may be implemented after the instruction core is stable, but the interface must be included in the design from the beginning.

---

## 17. LOCK Behavior

LOCK must be architecturally represented and visible at the external bus.

The implementation must support:

- explicit `LOCK` prefix behavior where legal;
- rejection/exception behavior where LOCK is illegal;
- operations for which the 80286 asserts LOCK automatically.

Do not assume LOCK is only a prefix passthrough signal.

SingleStepTests captures LOCK pin state and can therefore be used for regression verification.

---

## 18. Instruction Prefetch

The 80286 has a more advanced instruction unit than the 8086/8088.

The implementation shall model the 80286 prefetch mechanism rather than reusing an 8086 queue unchanged.

The Intel 80286 hardware documentation describes a **6-byte prefetch queue**.

The Bus Unit requests prefetch when enough queue capacity is available, and instruction fetch behavior interacts with bus availability and control transfers.

Requirements:

- six-byte queue capacity;
- correct queue flush on control transfers;
- correct restart behavior after jumps;
- word-oriented code fetch behavior where appropriate;
- no fictional 8088/8086 queue-status output pins;
- separation between prefetch activity and execution.

Important SingleStep limitation:

The current 80286 SingleStep suite deliberately starts instructions after a jump and does **not** fully exercise arbitrary pre-existing prefetch queue contents because the real 80286 does not expose queue-status pins.

Therefore:

> Passing SingleStep cycle traces is necessary but is not sufficient evidence that the general prefetch implementation is complete.

Additional directed prefetch tests must be created.

---

## 19. Decoder

The decoder shall support the 80286 instruction encoding rules.

Requirements include:

- one-byte opcodes;
- `0x0F` two-byte opcode space introduced for 286 system instructions;
- ModR/M decoding;
- displacement decoding;
- immediate operands;
- segment override prefixes;
- LOCK;
- REP / REPE / REPNE;
- 80286 instruction-length rules;
- legal versus illegal prefix combinations;
- invalid-opcode exception generation.

The 80286 instruction-length limit must be modeled according to Intel documentation and verified using SingleStep tests that cover excessive prefix sequences and exception behavior.

---

## 20. Execution Unit

The Execution Unit shall contain:

- general register file;
- temporary internal registers as required;
- 16-bit ALU;
- 8-bit operation support;
- flags generation;
- barrel/iterative shift functionality as appropriate;
- multiplication/division support;
- string-operation support;
- effective-address generation interaction;
- microsequencer execution datapath.

Correct flag behavior is a first-class verification target.

Undefined flag bits must not be forced to later-x86 behavior without evidence.

---

## 21. Effective Address Generation

Implement the 16-bit x86 addressing forms used by 8086/80186/80286 instructions:

- BX + SI
- BX + DI
- BP + SI
- BP + DI
- SI
- DI
- BP
- BX
- displacement-only
- 8-bit displacement
- 16-bit displacement

Correct default segment selection must be enforced.

Segment override prefixes must alter only the operations for which they are architecturally applicable.

---

## 22. Instruction Compatibility Scope

### Phase 1 required baseline

Implement the full real-mode instruction behavior necessary to cover the published `SingleStepTests/80286/v1_real_mode` suite.

This includes:

- inherited 8086 instructions;
- 80186-class instructions supported by 80286;
- 80286-specific instructions that are valid/testable in real mode;
- 80286 exception behavior applicable in real mode.

### Full SPK286 target

Eventually support all architecturally defined 80286 integer/system instructions, including the protected-mode instruction family.

Examples include, but are not limited to:

- ARPL
- LAR
- LSL
- VERR
- VERW
- SGDT
- SIDT
- SLDT
- SMSW
- STR
- LGDT
- LIDT
- LLDT
- LMSW
- LTR

The exact instruction matrix must be maintained in:

`docs/INSTRUCTION_MATRIX.md`

Each opcode/form shall have status values such as:

- not implemented;
- decodes;
- functional;
- SingleStep state passing;
- SingleStep bus passing;
- timing verified;
- protected-mode verified.

---

## 23. Microsequencer and Internal Microcode

SPK286 should use a microsequencer for complex x86 operations.

Important:

> SPK286 microcode is project-owned implementation logic. It must not claim to reproduce Intel's original 80286 microcode unless authentic original microcode becomes available and its use is legally and technically justified.

Microcode shall be designed to make these behaviors explicit:

- register transfers;
- ALU operations;
- flag updates;
- memory reads/writes;
- I/O reads/writes;
- stack activity;
- instruction sequencing;
- exception entry;
- descriptor reads;
- privilege checks;
- task switching;
- bus locking;
- prefetch interaction.

The microcode format must be documented.

Microcode functional sequencing and historical timing metadata must remain separable.

The number of microinstructions used for an architectural operation must not, by itself, define its historical latency.

Where timing metadata is later required, it shall be explicit and compatible with the timing architecture defined in `SPK286_TIMING_MODEL.md`.

Prefer generated ROM contents from readable source definitions rather than hand-maintained opaque hexadecimal blobs.

For downstream CPU integration, the build/release flow shall also be capable of
emitting a deterministic microcode initialization image, preferably a documented
`.hex` representation (or a deliberately chosen equivalent if synthesis evidence
requires another format). The human-readable SPK286 microcode source remains the
authoritative source; the generated image is a distributable build artifact.

Recommended structure:

```text
microcode/source/*.yaml | *.toml | custom DSL
                 |
                 v
          microcode compiler
                 |
                 +--> generated SystemVerilog package
                 +--> ROM initialization file
                 +--> human-readable listing
                 +--> validation metadata
```

The exact tooling language is flexible; Python is recommended.

---

## 24. Real Mode

Real mode is the first implementation milestone.

Required behavior includes:

- traditional segmented addressing;
- 20-bit-compatible conventional addresses;
- 80286 real-mode behavior above the 8086-compatible area where architecturally possible;
- correct segment cache initialization;
- interrupt vector table behavior;
- real-mode exception behavior;
- reset-vector special segment base;
- 80286-specific opcode behavior;
- 24-bit physical bus output.

The implementation must not assume that real-mode segment hidden state is always reconstructable from the visible 16-bit segment selector.

---

## 25. Interrupts and Exceptions

SPK286 must provide a centralized exception/interrupt mechanism.

Support eventually includes:

### External

- INTR
- NMI

### Software

- INT n
- INT3
- INTO

### Faults/exceptions

At minimum, implement all architecturally relevant 80286 exceptions according to Intel documentation, including conditions such as:

- divide error;
- debug/single-step;
- NMI;
- breakpoint;
- overflow;
- BOUND range exceeded;
- invalid opcode;
- processor extension unavailable;
- invalid TSS;
- segment not present;
- stack fault;
- general protection;
- processor extension error where applicable.

The exact exception vector map must be derived from Intel documentation.

Exception priority, pushed state, error-code behavior, restart semantics, and nested-fault behavior must be explicitly tested.

Do not import 386-specific exception semantics.

---

## 26. Protected Mode

Protected mode is a required final feature, but not the first implementation milestone.

The design must reserve clean architectural boundaries for it from day one.

Required protected-mode mechanisms include:

### Descriptor tables

- GDT
- LDT
- IDT

### System registers/state

- GDTR
- LDTR
- IDTR
- TR
- MSW protected-mode state

### Segment descriptors

Implement 80286 descriptor formats and semantics:

- base;
- limit;
- access rights;
- present state;
- DPL;
- code/data attributes;
- conforming/non-conforming behavior;
- readable/writable rules;
- expand-down data semantics where applicable.

### Privilege

Implement:

- CPL
- DPL
- RPL
- effective privilege checks
- IOPL behavior

### Gates

Implement 80286 gate types required by the architecture, including:

- interrupt gates;
- trap gates;
- call gates;
- task gates.

### Task switching

Implement 80286 task-state behavior:

- TSS;
- task register;
- busy state;
- task link;
- privilege stack switching;
- task-gate and TSS-directed switches;
- nested task behavior.

### Protection checks

Protection checks must occur before architectural side effects that the real processor would suppress on fault.

This should strongly influence execution sequencing.

---

## 27. No Paging

SPK286 must **not implement paging**.

Paging is a 80386-class architectural feature and is outside the 80286 target.

Any design copied conceptually from z386 must separate:

```text
segmentation/protection
```

from:

```text
386 paging
```

The latter must not enter the SPK286 architecture.

---

## 28. Entering and Leaving Protected Mode

Implement the genuine 80286 mode-control semantics.

Particular care is required around the Machine Status Word and PE bit.

Do not silently adopt 80386 mode-switch semantics.

The historical 80286 inability to return from protected mode through the later 386-style mechanism must be represented according to Intel behavior.

Reset-based transitions and software techniques relying on 80286-specific behavior must remain possible.

---

## 29. Descriptor Caches

Segment descriptor hidden state is essential.

Each segment register shall have internal cached descriptor information sufficient to implement:

- base;
- limit;
- access rights;
- privilege-related state;
- real/protected/unreal semantics.

This requirement also supports:

- unusual reset CS base;
- LOADALL behavior;
- protected-to-real interactions;
- hardware-faithful segment behavior.

The internal cache representation need not match Intel transistor-level implementation, but behavior must match the architecture.

---

## 30. LOADALL / Unreal Mode

SingleStepTests explicitly reserves a future `v1_unreal_mode` suite.

SPK286 should therefore design for the undocumented 80286 `LOADALL` behavior even if implementation is deferred.

Requirements:

- do not block future initialization of hidden segment caches;
- reserve internal state for 80286 hidden registers needed by LOADALL;
- document known/unknown behavior;
- implement only from reliable hardware research and test evidence.

LOADALL should be a later milestone after normal real mode is stable unless available SingleStep tests make earlier implementation useful.

---

## 31. 80287 Interface

80287 support is desirable but optional for the first SPK286 release.

The top-level architecture should avoid making later integration difficult.

Potential native signals include:

- PEREQ
- PEACK
- BUSY
- ERROR

Initial implementation may:

- expose the pins;
- provide safe inactive behavior;
- raise the appropriate processor-extension unavailable behavior where required.

Full 80287 execution is outside the initial CPU milestone and may be implemented as a separate coprocessor project.

---

## 32. Cycle Accuracy Strategy

Cycle accuracy shall be developed in layers.

### Level A — Functional

Match:

- final registers;
- final memory;
- exception result.

### Level B — Bus transaction

Match:

- transaction type;
- address;
- data;
- byte lane;
- LOCK behavior;
- transaction ordering.

### Level C — Cycle state

Match the hardware-generated trace as far as the test format exposes:

- address bus;
- data bus;
- bus control state;
- pin state;
- Ts/Tc/Ti sequence.

A test may therefore report:

```text
PASS functional
PASS bus
FAIL cycle
```

rather than a single binary result.

This distinction is mandatory because it allows architecture work to advance without hiding timing debt.

Timing validation shall additionally distinguish:

- real dependency stalls;
- BIU/bus timing;
- historical compatibility delays;
- FPGA implementation latency.

Once multiple timing modes exist, regression shall verify that:

```text
architectural_result(Accurate)
    ==
architectural_result(Fast)
    ==
architectural_result(Max)
```

for the same initial architectural state and program, except for timing-observation fields.

---

## 33. SingleStepTests/80286 Integration

The repository shall include an automated test runner for the external SingleStep suite.

Do not vendor the entire test corpus into SPK286 unless licensing, repository size, and maintenance implications are deliberately accepted.

Preferred workflow:

```text
SingleStepTests/80286
         |
         v
MOO files or JSON conversion
         |
         v
SPK286 test adapter
         |
         v
Verilator simulation
         |
         +--> architectural comparison
         +--> memory comparison
         +--> bus comparison
         +--> cycle comparison
         |
         v
machine-readable regression report
```

The runner shall support:

- selecting an opcode;
- selecting a single test index;
- running a random sample;
- running all tests for an instruction form;
- full regression;
- stopping at first failure;
- retaining failure traces;
- deterministic reproduction.

---

## 34. SingleStep Test Semantics

The implementation agent must understand the methodology of the test suite before attempting to match it.

Important facts from the published test documentation:

1. Tests initialize CPU registers and memory.
2. Execution begins as if control has jumped to the specified CS:IP.
3. A terminating HALT is used to identify instruction completion.
4. The final state contains changed registers/memory.
5. Cycle traces may be compared optionally.
6. Current real-mode tests assume 16 MiB RAM mapped and writable.
7. Current tests contain no wait states.
8. Interrupt and trap flags are not exercised in the current real-mode dataset.
9. Prefetch is intentionally constrained by starting after a jump.
10. Invalid or revoked test hashes must be handled according to the repository's revocation mechanism.

The test adapter must account for these conventions rather than forcing the core into an artificial state that could mask real bugs.

---

## 35. Test Failure Output

For every failed SingleStep case, produce a concise but complete artifact.

Example:

```text
Test: add [bx+0Eh], bl
Index: 42
Bytes: ...
Failure class: BUS_DATA_MISMATCH

Expected final:
  AX=...
  FLAGS=...

Actual final:
  AX=...
  FLAGS=...

First bus divergence:
  cycle: 17
  expected:
    state=MEMW
    address=0x123456
    data=0x00A4
    bhe=...
    tstate=Ts
  actual:
    ...

Microstate:
  micro_pc=...
  instruction_state=...
  prefetch_count=...
```

A failing regression must be debuggable without manually adding waveform probes for common cases.

---

## 36. Debug Observability

Simulation builds shall expose internal debug state without affecting synthesis behavior.

Useful debug signals:

- current opcode;
- ModR/M;
- micro-PC;
- current microinstruction;
- AX/BX/CX/DX;
- SP/BP/SI/DI;
- CS/DS/SS/ES visible values;
- hidden segment bases/limits;
- IP;
- FLAGS;
- prefetch queue contents/count;
- current effective address;
- current physical address;
- bus FSM state;
- timing mode/profile when implemented;
- timing wait active;
- timing class/budget when implemented;
- compatibility-delay cycles;
- READY/dependency-wait cycles;
- exception pending/vector;
- protected-mode state;
- CPL;
- descriptor currently being evaluated.

These may be grouped into a simulation-only debug structure.

---

## 37. Waveform Support

The Verilator test environment shall optionally emit FST/VCD traces.

Waveform generation must be:

- disabled by default in large regressions;
- activatable for a single failing case;
- reproducible using the printed test ID.

---

## 38. Unit Tests Independent of SingleStep

SingleStep must not become the only test source.

Create directed unit tests for internal units including:

- ALU;
- flags;
- effective-address generation;
- decoder;
- prefix handling;
- prefetch queue;
- bus state machine;
- byte-lane selection;
- READY wait states;
- HOLD/HLDA;
- reset;
- segment cache;
- descriptor parser;
- privilege comparison;
- exception priority.

This is especially important for features not currently covered by the published 80286 real-mode SingleStep suite.

---

## 39. Reference Software Tests

After instruction-level verification reaches useful coverage, add software-level tests such as:

- small bare-metal assembly diagnostics;
- Intel-compatible CPU detection programs;
- DOS CPU diagnostic utilities where redistribution is legal;
- custom real-mode instruction suites;
- protected-mode exercisers;
- optional PC/AT BIOS POST execution in a separate downstream integration project.

These are integration tests, not substitutes for SingleStep verification.

PC/AT BIOS execution is not a required SPK286 repository deliverable. It may be
used externally to validate the CPU integration contract without moving
motherboard logic into SPK286.

---

## 40. FPGA Target

Initial synthesis target:

- Intel Cyclone V;
- DE10-Nano / MiSTer-class FPGA.

This target is selected because:

- MiSTer uses Cyclone V;
- S80186 demonstrates a SystemVerilog x86-class soft-core on Cyclone V;
- z386 demonstrates a substantially more complex x86 CPU on DE10-Nano.

SPK286 should therefore fit comfortably enough that a separate consumer project can still allocate significant FPGA resources to a PC/AT chipset and video/audio/peripheral logic.

Resource budgeting for the complete PC/AT machine is a downstream-project concern; SPK286 records only CPU resource use.

No strict ALM target is specified initially.

Correctness takes priority over size.

Resource usage must be recorded after each major milestone.

---

## 41. Clocking

The CPU implementation shall use a clean internal clock-enable / timing-policy strategy rather than embedding assumptions about one physical 80286 MHz rating throughout the design.

The physical FPGA master clock and the emulated 80286 timing profile shall be conceptually independent.

Desired capabilities:

- run at an FPGA-friendly internal frequency;
- produce 80286-compatible instruction and bus timing through explicit timing policy;
- support historical effective CPU rates without requiring separate CPU RTL implementations;
- expose a clean CPU timing/configuration contract so a separate PC/AT project can preserve independent peripheral/system timing;
- support accelerated execution without altering architectural semantics.

A historical frequency profile is not considered accurate merely because a divider produces the nominal clock rate. Instruction timing, BIU timing, READY behavior, and any implementation-specific historical differences must also be validated.

Initial candidate historical profiles include:

```text
6 MHz
8 MHz
10 MHz
12 MHz / 12.5 MHz
16 MHz
20 MHz
25 MHz
```

The exact validated list shall be evidence-driven.

An accelerated mode must never silently replace compatible timing.

Conceptual configuration:

```systemverilog
typedef enum logic [1:0] {
    TIMING_ACCURATE,
    TIMING_FAST,
    TIMING_MAX
} timing_mode_t;
```

The exact RTL encoding and configuration interface are deferred.

---

## 42. Performance Modes

SPK286 shall be designed so one functional CPU implementation can support multiple timing policies.

The detailed architecture is defined in `SPK286_TIMING_MODEL.md`.

### Accurate mode

Prioritize validated historical 80286 instruction and bus timing for the selected profile.

Accurate mode may use timing metadata, timing classes, counters, or another explicit scheduler mechanism, but must not alter functional semantics.

### Fast mode

Remove artificial instruction-level compatibility delays while keeping a compatibility-oriented BIU timing policy.

This mode is useful for separating execution-engine limits from external-bus limits.

### Max mode

Remove removable historical timing delays from both execution and BIU operation while preserving every real dependency.

Max mode must still wait for:

- READY;
- BIU transaction completion;
- required instruction bytes;
- required operand data;
- required memory writes;
- bus ownership;
- queue flush/redirect completion;
- architecturally required serialization.

Max mode is not a literal historical clock profile such as "286 @ 80 MHz".

It is an accelerated 80286-compatible mode whose performance may exceed that of any historical 286 because some operations may complete in fewer internal cycles than the original silicon.

This concept is inspired by MCL86's separation between compatible and accelerated operation, but SPK286 shall define and validate its own timing architecture.

However:

> Accurate timing convergence and accelerated modes are explicitly post-functional-MVP work.

Do not use Fast/Max modes to avoid implementing correct 80286 semantics or to hide timing debt.

---

## 43. Development Milestones

### Milestone 0 — Repository and verification skeleton

Deliver:

- repository structure;
- build scripts;
- Verilator smoke test;
- Quartus synthesis smoke test;
- SingleStep loader/parser;
- one dummy test successfully passed through the infrastructure;
- source/license notes.

Acceptance:

- `scripts/build.sh` succeeds;
- `scripts/test.sh` runs;
- CI-capable non-interactive execution.

---

### Milestone 1 — Reset, registers, bus skeleton

Deliver:

- register file;
- FLAGS basic storage;
- segment visible/hidden state;
- reset state;
- native bus output;
- basic code fetch;
- 6-byte prefetch queue skeleton;
- microsequencer skeleton.

Acceptance:

- first reset fetch is `0xFFFFF0`;
- bus signals are traceable;
- FPGA synthesis succeeds.

---

### Milestone 2 — Core real-mode integer execution

Implement a useful subset:

- MOV;
- XCHG;
- ADD/ADC;
- SUB/SBB;
- CMP;
- AND/OR/XOR/TEST;
- INC/DEC;
- PUSH/POP;
- basic branches;
- CALL/RET;
- basic ModR/M addressing.

Acceptance:

- corresponding SingleStep tests pass functionally;
- bus failures are measured separately.

---

### Milestone 3 — Full published real-mode instruction coverage

Implement all instruction forms required by current `v1_real_mode`.

Acceptance target:

- 100% non-revoked tests parse;
- 100% intended opcodes execute;
- no unexplained functional mismatches;
- all known remaining failures categorized.

The implementation agent must not claim milestone completion while skipping difficult instruction families.

---

### Milestone 4 — Real-mode bus and cycle convergence

Tune:

- bus ordering;
- BHE;
- LOCK;
- Ts/Tc/Ti behavior;
- instruction fetch sequencing;
- prefetch interactions visible in tests;
- exception bus traffic;
- timing metadata / timing-class model where required;
- separation of real dependency stalls from historical compatibility delays.

Acceptance:

- near-complete bus trace agreement;
- cycle mismatches documented by instruction family;
- zero functional regressions;
- timing-policy changes do not alter architectural results;
- at least one validated Accurate timing profile can be selected cleanly.

Exact numerical pass threshold shall be set after baseline results exist.

---

### Milestone 5 — System/protection infrastructure

Implement:

- MSW;
- GDTR/IDTR;
- LDTR/TR;
- descriptor parsing;
- hidden descriptor cache;
- protected-mode decoder support;
- privilege machinery;
- system instruction family.

Acceptance:

- directed descriptor/protection unit tests pass;
- real-mode regression remains clean.

---

### Milestone 6 — Protected mode

Implement:

- GDT/LDT/IDT lookup;
- selectors;
- privilege checks;
- gates;
- protected-mode interrupts/exceptions;
- stack changes;
- TSS;
- task switching.

Acceptance:

- dedicated protected-mode assembly suite passes;
- future SingleStep protected-mode tests are integrated when published/available;
- no 386-only assumptions.

---

### Milestone 7 — Unreal mode / LOADALL

Implement and validate 80286 LOADALL/unreal-mode behavior from trustworthy evidence.

Acceptance:

- dedicated tests;
- future `v1_unreal_mode` SingleStep integration when available.

---

### Milestone 8 — Standalone CPU release and integration package

This milestone remains entirely inside the CPU project.

Deliver:

- stable native external CPU interface;
- interrupt support;
- HOLD/HLDA;
- LOCK/READY behaviour;
- optional 80287 handshake;
- documented synthesizable RTL manifest;
- deterministic generated microcode image for downstream use;
- documented reset/clock/timing configuration contract;
- CPU-only synthesis example or smoke harness;
- versioned integration documentation.

Acceptance:

- SPK286 can be consumed as a standalone synthesizable CPU without importing any
  PC/AT or MiSTer machine logic into this repository;
- a separate consumer project can instantiate the documented SPK286 release
  artifacts;
- generated microcode and RTL inputs are reproducible from the authoritative
  SPK286 sources;
- the CPU project remains independently testable with its synthetic/native
  testbench.

At this point a separate project such as `PCAT286_MiSTer` can integrate SPK286.
That system project is not a later directory or milestone implementation inside
SPK286.

---

### Milestone 9 — Timing profiles and accelerated execution

After functional correctness and bus/cycle convergence are sufficiently mature:

Implement and validate:

- selectable Accurate timing profiles;
- timing-policy observability;
- functional-result invariance across timing modes;
- Fast mode;
- Max mode;
- separation between CPU acceleration and peripheral timing;
- performance characterization of execution, BIU, prefetch, and READY bottlenecks.

Acceptance:

- validated Accurate profiles are clearly identified;
- Fast/Max preserve architectural state and memory results;
- READY and bus ownership remain mandatory dependencies;
- no opcode-specific timing hacks are required to switch modes;
- Max-mode performance is measured without mislabeling it as a historical MHz rating.

---

## 44. Definition of Done for Real-Mode MVP

The first major public SPK286 milestone can be called **Real-Mode MVP** when:

- synthesizable on Cyclone V;
- reset vector correct;
- architectural register model correct;
- 24-bit address bus works;
- 16-bit data bus/BHE works;
- complete target real-mode instruction matrix implemented;
- exceptions applicable to the suite work;
- current SingleStep real-mode corpus runs automatically;
- functional results are effectively complete except explicitly documented hardware-test anomalies;
- bus comparison infrastructure is operational;
- failures are reproducible;
- no known failure is hidden by test exclusions without justification.

Booting DOS is **not** sufficient to meet this definition.

---

## 45. Definition of Done for SPK286 1.0

SPK286 1.0 should require:

- real mode;
- protected mode;
- 80286 system instructions;
- descriptors;
- privilege enforcement;
- task switching;
- architectural exception behavior;
- robust external bus interface;
- HOLD/HLDA;
- LOCK;
- READY;
- complete automated regression;
- Cyclone V synthesis;
- integration documentation;
- no intentional 386 architectural extensions in compatibility mode;
- timing architecture remains separable from functional semantics;
- at least one validated compatibility/Accurate timing profile;
- accelerated timing mode does not alter architectural results;
- deterministic downstream microcode image generation;
- documented standalone CPU RTL/export manifest;
- native integration contract sufficient for an external system project;
- no PC/AT chipset or MiSTer machine implementation inside the SPK286 repository.

SPK286 1.0 does not require a MiSTer PC/AT core to exist or boot. Machine-level
integration is a separate project and may proceed independently once the CPU
interface is stable.

LOADALL and 80287 support may be separately versioned if necessary, but their status must be explicit.

---

## 46. What to Learn from Each Reference Project

### 46.1 MCL86

Study:

- microsequencer philosophy;
- EU/BIU split;
- cycle-compatible versus accelerated operation;
- separation of functional sequencing from compatibility timing;
- minimal datapath controlled by microcode;
- test-oriented implementation.

Do not:

- assume 8086 timing applies to 286;
- reuse the 8086 queue design;
- treat 8086 segmentation as sufficient;
- copy code before license verification.

### 46.2 S80186

Study:

- SystemVerilog project organization;
- decoder/testing architecture;
- model-versus-RTL verification;
- Docker/build reproducibility;
- Cyclone V integration;
- clean engineering documentation.

Do not:

- inherit its performance-oriented timing;
- assume 1 MiB addressing;
- assume its 80186 ISA is the complete 286 ISA;
- copy GPL code into a project whose license is not deliberately GPL-compatible.

### 46.3 z386

Study:

- module decomposition;
- prefetch architecture;
- microsequencer structure;
- segmentation module;
- protection module;
- separation of major CPU mechanisms;
- MiSTer/DE10-Nano practical lessons relevant to packaging and FPGA integration boundaries.

Do not:

- implement 32-bit registers;
- implement paging;
- implement 386 descriptor semantics without verifying 286 differences;
- import 386 exception semantics;
- use 386 timing as a 286 reference;
- copy source until license compatibility is confirmed.

### 46.4 SingleStepTests/80286

Use as:

- hardware behavioral oracle;
- regression corpus;
- bus/cycle comparison source;
- source of edge cases;
- basis for instruction completion tracking.

Do not:

- infer that uncovered behavior is irrelevant;
- assume current real-mode traces cover arbitrary prefetch state;
- assume wait states are tested;
- assume protected mode is already covered.

---

## 47. Research Questions the Agent Must Resolve

The implementation process must maintain a living list of unresolved questions.

Initial questions include:

1. Exact reset values for every visible and hidden register.
2. Exact FLAGS reserved-bit behavior by instruction.
3. Exact prefetch refill sequencing outside the constrained SingleStep setup.
4. Exact bus timing around unaligned word accesses.
5. Automatic LOCK assertion cases.
6. HOLD recognition boundaries.
7. READY sampling behavior.
8. Interrupt acknowledge cycle details.
9. Exception priority under simultaneous conditions.
10. Segment-cache behavior across every mode transition.
11. Exact 80286 descriptor edge cases.
12. Fault-versus-trap restart semantics.
13. Double-fault/shutdown behavior.
14. Task switch corner cases.
15. LOADALL hidden-state format and behavior.
16. 80287 exception/handshake behavior.
17. Exact instruction timing by instruction form and operand class.
18. Exact BIU timing differences across historical 80286/80C286 speed grades/vendors.
19. Which observed delays are architecturally required dependencies versus historical implementation latency.
20. Whether selected high-speed CMOS 286 variants exhibit timing differences beyond simple clock scaling.

For every resolved question, cite:

- Intel document/page where possible;
- physical test evidence where available;
- any secondary reference used.

---

## 48. Accuracy Policy

When uncertain, the agent must **not guess silently**.

Use this process:

```text
Unknown behavior
      |
      v
Intel 80286 documentation
      |
      +--> clear? --> implement + test
      |
      v
SingleStep / physical evidence
      |
      +--> clear? --> implement + document
      |
      v
independent historical references/emulators
      |
      v
record unresolved issue
```

Do not choose behavior simply because:

- ao486 does it;
- z386 does it;
- QEMU does it;
- Bochs does it;
- PCem/86Box does it;
- an 80386 manual says so.

Those may provide leads but are not authoritative for an 80286 clone.

---

## 49. Strict CPU-Only Project Boundary

SPK286 is complete as a CPU project when the processor itself meets its
architectural, bus, timing, verification, synthesis and integration-contract
requirements.

A complete IBM PC/AT machine is not a SPK286 deliverable.

During SPK286 development:

- do not make IBM PC/AT BIOS success the primary correctness criterion;
- do not add motherboard devices to make software boot;
- do not add MiSTer framework logic to this repository;
- do not couple CPU internals to a particular chipset implementation;
- keep the native CPU testbench capable of executing instructions with a
  synthetic memory/I/O environment.

The Bus Interface Unit remains part of SPK286 because it is part of the CPU
boundary. The motherboard-side responder, memory controller, chipset and
peripherals are external consumers of the BIU interface.

The intended relationship is:

```text
SPK286
    |
    +--> generated microcode image
    +--> required CPU SystemVerilog RTL
    +--> BIU / native CPU interface
    +--> integration documentation
    |
    +========== repository boundary ==========
                    |
                    v
             PCAT286_MiSTer
                    |
        +-----------+-----------+
        |           |           |
      SPK286     AT chipset   RAM/ROM
                                |
                         video / I/O / storage
```

A downstream MiSTer project may vendor, submodule, package, or otherwise consume
the documented SPK286 release artifacts according to the repository's eventual
integration policy.

SPK286 itself shall not contain:

- PIC/PIT/DMA/8042/RTC implementations;
- ISA machine integration;
- VGA/EGA integration;
- storage controllers;
- MiSTer OSD or HPS interface logic;
- PC/AT BIOS packaging;
- complete PC/AT memory-map glue.

Optional external integration tests may boot a BIOS or operating system, but
those tests must not redefine the CPU-project boundary.


---

## 50. AI-Agent Implementation Rules

The implementation agent must follow these rules.

### Rule 1 — Inspect before implementing

Before modifying RTL for an instruction family:

- inspect Intel behavior;
- inspect relevant SingleStep cases;
- identify bus/cycle requirements;
- identify flag edge cases.

### Rule 2 — Small validated increments

Implement one coherent instruction/mechanism group at a time.

After each group:

- run unit tests;
- run relevant SingleStep tests;
- run regression subset;
- record pass/fail delta.

### Rule 3 — Never “fix” a test by hard-coding test data

Forbidden:

- recognizing test addresses;
- recognizing SingleStep instruction bytes and special-casing them;
- bypassing normal architectural logic for known corpus cases.

### Rule 4 — Do not weaken tests to make the core pass

If expected behavior appears wrong:

- preserve the failing case;
- investigate;
- check revocation list;
- document evidence;
- only then adjust the harness or expectations.

### Rule 5 — Preserve functional correctness while tuning timing

Cycle work must not break architectural state.

Run functional regression before and after timing changes.

Functional semantics and timing policy must remain separable.

Do not add semantically meaningless idle/NOP states solely to force a published cycle count if the delay belongs in the timing-policy mechanism.

Distinguish real dependency waits from removable compatibility waits.

When multiple timing modes exist, verify architectural-result invariance across them.

### Rule 6 — No unverified 386 leakage

Any logic adapted conceptually from a 386 implementation must be checked against 286 documentation.

### Rule 7 — Keep SPK286 CPU-only

CPU correctness changes must not be mixed with motherboard, MiSTer, or PC/AT
system implementation.

Do not add chipset/peripheral logic to SPK286 merely to make an integration test
boot.

FPGA-board files inside SPK286 are limited to CPU synthesis/smoke/integration
examples.

### Rule 8 — Document every intentional incompatibility

Temporary deviations must be listed in a known-issues document.

---

## 51. Required Development Reports

At each milestone, produce a short Markdown report containing:

- implemented scope;
- instructions added;
- SingleStep functional pass count;
- bus pass count;
- cycle pass count;
- known failures;
- FPGA synthesis utilization;
- maximum achieved FPGA clock;
- validated timing profile(s), if any;
- timing-mode invariance status, if applicable;
- Fast/Max performance measurements when implemented;
- newly resolved research questions;
- unresolved blockers;
- downstream CPU-package/export status when relevant.

Suggested location:

```text
docs/progress/
```

---

## 52. CI Expectations

A future CI workflow should include:

1. formatting/lint;
2. RTL compile;
3. unit tests;
4. fast SingleStep sample;
5. full or partitioned regression where practical;
6. microcode generation consistency check;
7. optional Quartus synthesis check.

Large SingleStep suites may be partitioned by opcode or test shard.

---

## 53. Reproducibility

The project shall support a clean-machine development workflow.

Preferred:

- containerized toolchain or documented package versions;
- pinned Verilator version where necessary;
- deterministic Python dependencies;
- deterministic generated microcode;
- deterministic regression selection using explicit seeds.

A command similar to:

```bash
./scripts/test.sh --opcode ADD --seed 286
```

should reproduce a reported failure.

---

## 54. Documentation Standard

Every major subsystem requires a short technical description.

At minimum:

- architecture;
- native bus;
- microcode format;
- decoder;
- prefetch;
- segmentation;
- protection;
- exceptions;
- timing model;
- verification;
- standalone CPU integration/export contract.

Documentation must describe **why** behavior exists, not only signal names.

---

## 55. Initial Agent Task

The first implementation agent should **not begin by writing the entire CPU**.

Its first assignment should be:

> Establish the SPK286 repository, verification architecture, authoritative source notes, SingleStepTests/80286 ingestion pipeline, and a synthesizable CPU skeleton capable of reproducing the 80286 reset vector and issuing the first observable code-fetch bus transaction at physical address `0xFFFFF0`.

Required first-task deliverables:

1. repository structure;
2. `ARCHITECTURE.md`;
3. `SOURCE_NOTES.md`;
4. SingleStep MOO/JSON reader;
5. Verilator testbench;
6. SPK286 top-level skeleton;
7. visible and hidden CS reset state;
8. IP reset state;
9. minimal Bus Interface Unit;
10. reset-vector test;
11. Quartus Cyclone V synthesis smoke test;
12. instructions for running all of the above.

No broad opcode implementation should begin until this foundation is working.

---

## 56. Suggested First Implementation Sequence

After Milestone 0/1:

```text
RESET
  |
  v
code fetch
  |
  v
prefetch queue
  |
  v
decoder
  |
  v
MOV register/immediate
  |
  v
MOV ModR/M
  |
  v
ALU + flags
  |
  v
stack
  |
  v
control flow
  |
  v
string operations
  |
  v
mul/div
  |
  v
exceptions
  |
  v
remaining real-mode ISA
  |
  v
bus/cycle convergence
  |
  v
timing-policy calibration
  |
  v
protected mode
```

This order gives the test infrastructure useful CPU behavior early while keeping the architecture extensible.

---

## 57. Success Criterion

The guiding criterion for every design decision is:

> If the same documented instruction sequence is executed from the same architectural state on SPK286 and on a real 80286, software should observe the same result; and in Accurate mode, where bus traces are available, external hardware should observe the same bus transaction behavior and, ultimately, the same cycle sequence.

Fast and Max modes are allowed to differ in timing, but not in architectural results or required dependency ordering.

SPK286 should become a genuine 80286 FPGA implementation, not merely a CPU capable of running 286-era software.

Success is judged at the CPU boundary. A separate PC/AT or MiSTer project may
provide valuable integration evidence, but booting such a machine is not part of
the SPK286 repository's Definition of Done.

---

## 58. Reference Links

### Intel 80286 documentation

- https://www.bitsavers.org/components/intel/80286/

### MCL86

- https://github.com/MicroCoreLabs/Projects/tree/master/MCL86
- https://microcorelabs.com/2016/03/03/lots-of-interest-in-the-mcl86-core/

### S80186 / s80x86

- https://github.com/jamieiles/80x86

### z386

- https://github.com/nand2mario/z386
- https://github.com/nand2mario/z386_MiSTer

### SingleStepTests/80286

- https://github.com/SingleStepTests/80286

---

## 59. Final Constraint

Do not trade authenticity for an easier shortcut without explicitly changing the project goal.

If a later decision chooses:

- reduced cycle fidelity;
- omitted protected-mode feature;
- non-native bus interface;
- 386-derived compatibility behavior;

that decision must be written as a deliberate project-level specification change.

Timing acceleration is not considered a reduction in compatibility provided that:

- Accurate mode remains available and validated;
- accelerated modes are explicitly labeled non-historical;
- architectural semantics remain identical;
- real dependencies such as READY and bus ownership are preserved.

The project boundary is equally non-negotiable: SPK286 is the CPU. PC/AT
motherboard logic and MiSTer machine integration belong to separate consumer
projects. The BIU and native CPU-facing interface remain part of SPK286.

Until then, the target remains:

**SPK286: a dedicated, standalone, synthesizable, hardware-validated Intel 80286-compatible FPGA soft-core with separable historical and accelerated timing policies.**
