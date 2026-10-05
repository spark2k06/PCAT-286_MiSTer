# SPK286 Timing Model

## Status

Draft architectural specification for the SPK286 timing subsystem.

This document defines how SPK286 must separate **functional CPU semantics** from
**historical timing compatibility** so that the same RTL implementation can
support both accurate 80286 timing profiles and unrestricted high-performance
execution.

This document does **not** make cycle accuracy a requirement for the current
Real Mode MVP. Functional correctness remains the primary milestone.

---

## 1. Purpose

SPK286 is intended to support two complementary goals:

1. Reproduce the externally observable timing behaviour of historical 80286
   systems closely enough for software and system-level compatibility.
2. Allow the same CPU implementation to run without artificial historical
   delays, producing a hypothetical high-performance "super 286" while
   preserving 80286 architectural semantics.

These goals must not require two separate CPU implementations.

The timing model must therefore be designed as an independent policy layer
around a single functional execution engine.

---

## 2. Fundamental Architectural Rule

The most important rule in this document is:

> **Functional semantics and timing policy must remain separable.**

SPK286 must not encode historical timing by scattering arbitrary idle states,
NOP states or fixed delay states throughout instruction-specific RTL in ways
that are inseparable from execution semantics.

The implementation should distinguish between:

- work that is functionally required;
- waits caused by real dependencies;
- waits required only to reproduce historical timing.

Conceptually:

```text
                SPK286 Functional Core
                         |
                         v
                  Required operation
                         |
             +-----------+-----------+
             |                       |
             v                       v
      Real dependency?       Compatibility delay?
             |                       |
             v                       v
        Always wait            Timing-policy controlled
```

A real dependency must be respected in every mode.

A compatibility delay may be removed in accelerated modes.

---

## 3. Timing Modes

SPK286 should support the following conceptual timing modes.

The exact user-facing names may change later.

### 3.1 Accurate Mode

Accurate mode attempts to reproduce the timing behaviour of the selected
historical 80286 profile.

It should eventually model, where relevant:

- instruction execution latency;
- BIU sequencing;
- code prefetch behaviour;
- data bus cycles;
- READY-derived wait states;
- aligned and unaligned accesses;
- interrupt acknowledge timing;
- bus ownership transitions;
- instruction/bus interaction.

Accurate mode is the mode intended for historical compatibility.

Functional execution remains identical to other modes.

Only timing policy changes.

---

### 3.2 Fast Mode

Fast mode removes artificial instruction-level compatibility delays while
retaining a historically constrained or compatibility-oriented BIU.

Conceptually:

```text
Execution Unit:
    run as soon as dependencies permit

BIU:
    preserve selected historical bus behaviour
```

This mode is useful for distinguishing:

- limitations caused by the 80286 execution engine;
- limitations caused by the historical external bus.

Fast mode may ultimately be hidden from the normal user interface if Max mode
is sufficient, but the architecture should not prevent it.

---

### 3.3 Max Mode

Max mode removes artificial historical delays from both the functional
execution path and the BIU whenever doing so does not alter architectural
semantics.

Execution proceeds as soon as all real dependencies are satisfied.

Examples of dependencies that must still be honoured:

- required instruction byte not yet available;
- operand data not yet returned;
- BIU busy with an earlier transaction;
- READY not asserted;
- required memory write not completed;
- interrupt acknowledge sequence not completed;
- serialization required by architectural state;
- segment state not yet updated;
- queue flush or redirect still pending.

Max mode must **not** bypass these dependencies.

Conceptually:

```text
Historical CPU:
    semantic work
    + implementation latency
    + historical timing padding

SPK286 Max:
    semantic work
    + unavoidable implementation/dependency latency
```

Max mode therefore represents a hypothetical 80286 with the same ISA and
architectural behaviour but without unnecessary historical delay.

---

## 4. One CPU, Multiple Timing Policies

SPK286 must use one functional architecture.

Do not maintain separate execution implementations such as:

```text
spk286_accurate.sv
spk286_fast.sv
```

for the same instruction semantics.

Preferred conceptual structure:

```text
                         SPK286
                           |
              +------------+------------+
              |                         |
              v                         v
       Functional Engine          Timing Policy
              |                         |
              +------------+------------+
                           |
                           v
                         BIU
```

A timing policy may influence when a completed functional stage is allowed to
advance, but should not redefine what the stage does.

---

## 5. Historical Speed Profiles

Accurate mode should support selectable historical CPU speed profiles.

Initial candidate profiles include:

```text
80286:
    6 MHz
    8 MHz
    10 MHz
    12 MHz / 12.5 MHz

High-speed CMOS 286-class profiles:
    16 MHz
    20 MHz
    25 MHz
```

These values are targets for future validation rather than assumptions that all
versions share identical internal timing.

Before declaring a profile historically accurate, SPK286 should verify:

- CPU clock definition;
- instruction timing;
- bus timing;
- READY behaviour;
- vendor-specific differences;
- any documented differences between NMOS/HMOS and CMOS implementations.

A profile should not be called cycle-accurate solely because the clock divider
matches a historical frequency.

---

## 6. FPGA Master Clock and Emulated CPU Clock

The physical FPGA clock should be independent from the emulated CPU frequency.

For example:

```text
FPGA master clock: 80 MHz
        |
        +--> Accurate 6 MHz profile
        |
        +--> Accurate 10 MHz profile
        |
        +--> Accurate 25 MHz profile
        |
        +--> Max mode
```

Historical modes should normally use clock-enable or equivalent scheduling
logic rather than requiring the entire design to be physically clocked at the
historical frequency.

This permits:

- one synthesis target;
- runtime speed selection;
- stable peripheral clocks;
- clean clock-domain design;
- high internal timing margin.

The exact master frequency is implementation-dependent.

---

## 7. Functional Cycles vs Timing Cycles

SPK286 must distinguish between:

### 7.1 Functional progress

A state transition required to perform architectural work.

Examples:

- consume opcode;
- consume ModR/M;
- calculate effective address;
- request operand read;
- update register;
- update FLAGS;
- retire instruction.

### 7.2 Dependency wait

A wait caused by something not yet being available.

Examples:

- prefetch queue empty;
- BIU busy;
- memory response pending;
- READY low.

These waits exist in all timing modes.

### 7.3 Compatibility wait

A wait inserted only to reproduce historical timing.

Examples may eventually include:

- instruction execution padding;
- historically required idle clocks;
- timing gaps between internal phases.

Compatibility waits are honoured by Accurate mode and may be removed by Fast
or Max mode.

---

## 8. Timing Metadata

The instruction-control architecture should allow timing information to exist
without embedding it directly into functional semantics.

A future microinstruction or instruction descriptor may contain timing-related
metadata such as:

```text
functional action
sequencing control
optional timing class
optional minimum-cycle requirement
```

The exact representation is intentionally unspecified at this stage.

Possible implementations include:

- a cycle budget;
- a timing-class identifier;
- timing-table lookup;
- per-micro-operation minimum latency;
- explicit synchronization points.

The design must not prematurely commit to a bit encoding until the real control
path is sufficiently mature.

---

## 9. Accurate-Mode Timing Scheduler

A future timing scheduler may conceptually operate as follows:

```text
functional operation completes
          |
          v
historical minimum satisfied?
      /           \
    yes            no
     |              |
     v              v
 advance        timing wait
```

Max mode would bypass the historical-minimum check while still respecting real
dependencies.

The scheduler should preferably be reusable across multiple instructions
instead of duplicating counters in individual opcode implementations.

---

## 10. Relationship to Microcode

SPK286 is expected to use a hybrid architecture containing both hardwired RTL
and microcoded sequencing.

Likely hardwired blocks include:

- register file;
- FLAGS storage and generation primitives;
- ModR/M decoding;
- effective-address generation;
- segmentation machinery;
- BIU;
- prefetch queue;
- bus-cycle engine;
- microsequencer.

Likely microcoded responsibilities include:

- instruction sequencing;
- operand-transfer sequencing;
- ALU-operation selection;
- complex instructions;
- string instruction control;
- interrupt/exception entry;
- protected-mode operations;
- descriptor and task-related flows.

Timing metadata should be associated with microcode or control sequencing only
where useful, but the number of microinstructions must not automatically define
the historical number of CPU cycles.

This is essential for Max mode.

---

## 11. BIU Timing

The BIU must be treated separately from instruction execution timing.

The BIU is responsible for externally visible transactions such as:

- code fetch;
- memory read;
- memory write;
- I/O read;
- I/O write;
- interrupt acknowledge;
- READY handling;
- byte-lane selection;
- aligned/unaligned word transfers;
- bus ownership.

Accurate mode should eventually reproduce historically meaningful BIU timing.

Fast mode may preserve BIU timing while accelerating internal execution.

Max mode may use the fastest safe BIU sequencing permitted by the FPGA/system
memory interface.

---

## 12. READY and Wait States

READY is a real dependency and must never be treated as optional timing
padding.

In every mode:

```text
bus transaction starts
        |
        v
READY asserted?
   /         \
 yes          no
  |            |
  v            v
complete      wait
```

Max mode must still wait for READY.

A memory subsystem may emulate historical wait states in Accurate mode while a
faster memory configuration may assert READY sooner in Max mode.

---

## 13. Prefetch Behaviour

SPK286 has a six-byte prefetch queue.

Timing modes must not change the architectural correctness rules of the queue.

All modes must preserve:

- byte ordering;
- correct architectural IP;
- correct fetch pointer;
- queue flush on redirect;
- stale-read rejection;
- instruction-stream correctness;
- no byte duplication;
- no byte loss.

Timing modes may affect:

- refill opportunities;
- bus arbitration;
- how quickly the queue is replenished;
- when prefetch may resume after operand access.

In Max mode, a fast EU may drain the queue faster than the BIU can refill it.

This is expected behaviour and creates a natural performance limit.

---

## 14. Natural Max-Mode Bottlenecks

Max mode must not attempt to hide genuine architectural bottlenecks.

Potential limits include:

- prefetch bandwidth;
- bus width;
- memory latency;
- unaligned word accesses;
- BIU arbitration;
- serial instruction dependencies;
- microsequencer throughput;
- FPGA Fmax;
- external SDRAM interface latency.

A useful property of Max mode is that it allows SPK286 to reveal which parts of
the 80286 architecture are intrinsically limiting once historical silicon
timing constraints are removed.

---

## 15. PC/AT Peripheral Timing Independence

Accelerating SPK286 must not automatically accelerate the entire PC/AT system.

Future SPK286_AT integration should maintain independent timing for peripherals
whose real-time behaviour matters.

Conceptually:

```text
                   FPGA master clock
                          |
        +-----------------+-----------------+
        |                 |                 |
        v                 v                 v
      SPK286           AT chipset       peripherals
   variable timing    controlled bus    fixed/derived timing
                                             |
                                             +-- PIT
                                             +-- RTC
                                             +-- keyboard
                                             +-- ISA devices
```

For example, Max CPU mode should not make the PIT run several times faster.

Peripheral timing must remain compatible unless a specific accelerated-machine
profile intentionally changes it.

---

## 16. MiSTer Runtime Selection

A future MiSTer integration may expose a CPU-speed option such as:

```text
CPU Speed
    286 6 MHz
    286 8 MHz
    286 10 MHz
    286 12.5 MHz
    286 16 MHz
    286 20 MHz
    286 25 MHz
    Fast
    Max
```

The final exposed list must depend on profiles that have actually been
validated.

User-visible labels should distinguish between:

- historically modelled timing;
- accelerated/non-historical modes.

Max mode must not be presented as an authentic historical 286 frequency.

---

## 17. Meaning of "Cycle Accurate"

SPK286 should distinguish several levels of timing fidelity.

### 17.1 Instruction-cycle accurate

Instruction completion latency matches the target processor for defined
conditions.

### 17.2 Bus-cycle accurate

The sequence and timing of external bus operations match the target processor
closely enough to reproduce relevant system behaviour.

### 17.3 Pin/cycle exact

Externally visible signal transitions match the physical processor essentially
clock by clock.

The intended long-term target for SPK286 is primarily:

```text
instruction-cycle accuracy
+
bus-cycle accuracy
```

Pin/cycle exact replication should only become a requirement if evidence shows
that it is necessary for compatibility.

---

## 18. SingleStepTests Timing Validation

SPK286 already uses SingleStepTests/80286 as a source of hardware-derived
architectural validation.

The available corpus also contains bus/cycle information that may later be used
to calibrate timing.

The validation strategy should evolve in stages.

### Current stage

Compare architectural results:

- registers;
- FLAGS;
- IP;
- memory;
- exceptions where supported.

### Future timing stage

Compare relevant trace properties such as:

- bus operation type;
- address;
- data direction;
- code fetches;
- memory accesses;
- sequence of bus events;
- timing-state relationships.

Exact trace equality should not be required until SPK286 has a mature timing
model.

SingleStep cycle traces are evidence, not a reason to prematurely encode
timing into the functional RTL.

---

## 19. Additional Timing References

SingleStepTests alone may not be sufficient for every timing question.

Future timing work should use multiple sources where possible:

- Intel 80286 documentation;
- hardware-derived SingleStep traces;
- published timing tables;
- MCL86 architecture as a design reference;
- other independently developed x86 cores;
- oscilloscope/logic-analyser captures from real hardware where available;
- BIOS and software behaviour;
- benchmark comparisons.

Reference cores should be treated as implementation examples rather than
authoritative behavioural specifications.

---

## 20. MCL86 Design Lesson

MCL86 demonstrates a useful architectural concept: functional instruction
sequencing can be separated from a cycle-compatibility mechanism.

SPK286 may adopt the same general principle without copying MCL86's exact
implementation.

The useful lesson is:

```text
functional sequencing
        |
        +--> historical cycle budget when accuracy is enabled
        |
        +--> immediate dependency-driven progress when accuracy is disabled
```

SPK286 should generalize this concept for the more complex 80286 architecture,
including:

- 16-bit external data bus;
- six-byte prefetch queue;
- 24-bit physical addressing;
- hidden segment caches;
- protected mode;
- descriptor handling;
- exceptions;
- privilege mechanisms;
- task switching.

---

## 21. Max Mode Is Not a Higher Historical Clock

Max mode must not be described internally as simply:

```text
286 @ 80 MHz
```

unless the CPU is genuinely executing the same historical cycle schedule at an
80 MHz emulated CPU clock.

A dependency-driven accelerated core may complete some instructions in fewer
internal cycles than a real 80286.

Therefore Max mode should be treated as:

> An accelerated 80286-compatible execution mode.

Performance may be expressed using benchmark-derived equivalent performance,
but not as a literal historical clock frequency.

---

## 22. Benchmark-Based Equivalent Performance

A future informational metric may compare Max mode against a known historical
286.

Example:

```text
Reference:
    286 25 MHz benchmark = 10.0 s

SPK286 Max:
    same benchmark = 2.5 s

Relative performance:
    4.0x

Approximate "25 MHz 286 equivalent":
    100 MHz equivalent performance
```

This value is only a benchmark comparison.

It is not a claim that SPK286 is internally a cycle-identical 100 MHz 80286.

---

## 23. Testing Requirements for Timing Infrastructure

When timing-policy logic is introduced, tests should verify that functional
state is invariant across modes.

For the same program and initial state:

```text
Accurate result == Fast result == Max result
```

except for timing-observation fields.

Required test categories should eventually include:

- register state identical across modes;
- FLAGS identical across modes;
- memory state identical across modes;
- exception behaviour identical across modes;
- interrupt semantics preserved;
- queue correctness preserved;
- READY stalls honoured in all modes;
- redirects produce identical architectural results;
- only execution timing differs.

---

## 24. Performance Counters for Simulation

Simulation infrastructure should eventually expose useful timing statistics
without making them architectural CPU state.

Potential counters include:

- master FPGA-equivalent cycles;
- emulated CPU cycles;
- retired instructions;
- BIU busy cycles;
- READY wait cycles;
- prefetch-starvation cycles;
- compatibility-delay cycles;
- operand-memory wait cycles.

These counters can help answer questions such as:

```text
Why is Max mode not faster here?

    10% execution
    65% prefetch starvation
    20% data-memory waits
     5% other
```

They should normally remain verification/debug instrumentation rather than
architectural registers visible to x86 software.

---

## 25. Timing Configuration Interface

The RTL should eventually have a clean timing configuration interface.

Conceptually:

```text
timing_mode
timing_profile
```

Possible abstract values:

```text
timing_mode:
    ACCURATE
    FAST
    MAX

timing_profile:
    PROFILE_6MHZ
    PROFILE_8MHZ
    PROFILE_10MHZ
    PROFILE_12_5MHZ
    PROFILE_16MHZ
    PROFILE_20MHZ
    PROFILE_25MHZ
```

This is conceptual only.

Do not freeze encoding widths or register interfaces until system integration
requires them.

---

## 26. Reset and Runtime Mode Changes

The safest initial implementation should require timing-mode/profile changes to
take effect on reset.

This avoids introducing difficult questions about changing timing policy in the
middle of:

- a bus transaction;
- a partially executed instruction;
- interrupt entry;
- prefetch activity.

Runtime switching without reset may be added later if it can be proven safe.

MiSTer OSD integration should initially prefer:

```text
select CPU speed
        |
        v
reset CPU/system
        |
        v
new timing policy active
```

---

## 27. Protected Mode

Timing-policy separation must continue to apply after Protected Mode is added.

Protected-mode functionality may introduce complex multi-step operations such
as:

- descriptor fetches;
- descriptor validation;
- privilege checks;
- gate processing;
- stack switching;
- TSS operations;
- task switching;
- exception delivery.

These operations are particularly suitable for separating:

```text
required semantic sequence
```

from:

```text
historical minimum timing
```

Max mode must preserve every required semantic step even if compatibility
delays are removed.

---

## 28. Exceptions and Interrupts

Timing acceleration must not alter interrupt/exception ordering.

All modes must preserve:

- instruction-boundary rules;
- restart behaviour;
- priority ordering;
- trap/fault semantics;
- saved state;
- interrupt inhibition rules;
- NMI handling;
- INTR acknowledge semantics.

Timing policy may change how quickly the CPU reaches a legal recognition point,
but must not invent a recognition point that violates 80286 architecture.

---

## 29. DMA / HOLD / Bus Ownership

Future AT integration will require interaction with external bus masters.

Max mode must still respect:

- HOLD;
- HLDA or equivalent system integration contract;
- DMA ownership;
- incomplete bus cycles;
- locked cycles when supported.

A fast CPU cannot continue using memory while another bus master legitimately
owns the bus.

Therefore bus ownership is a real dependency, not compatibility timing.

---

## 30. Synthesis Considerations

Timing-policy logic should be efficient enough that Accurate-mode support does
not significantly reduce achievable FPGA Fmax.

Avoid structures where:

- large timing tables become critical combinational paths;
- timing selection expands every execution-state decoder;
- multiple full CPU datapaths are synthesized for different modes.

Preferred architecture:

```text
single datapath
single control architecture
small timing-policy layer
```

---

## 31. Development Strategy

Timing accuracy should be introduced incrementally.

Recommended order:

```text
1. Complete functional Real Mode CPU
2. Validate ISA extensively with SingleStep
3. Integrate PC/AT system
4. Identify software/system timing dependencies
5. Add timing-observation infrastructure
6. Calibrate instruction timing
7. Calibrate BIU timing
8. Validate historical profiles
9. Expose Accurate/Fast/Max modes
10. Continue timing refinement during Protected Mode work
```

This order intentionally avoids turning cycle accuracy into a blocker for
functional CPU development.

The work represented by items 4–10 is now tracked as the planned
[Phase 9 timing-fidelity workstream](docs/PHASE9_TIMING_FIDELITY.md). Until that
phase is completed, no SPK286 or downstream PC/AT profile may be called
historically cycle-accurate solely because it boots, passes SingleStep
architectural checks, or achieves a particular MHz/benchmark result.

---

## 32. Current Phase Policy

Until the timing subsystem is explicitly implemented:

- functional correctness has priority;
- existing READY behaviour must remain correct;
- bus sequencing must remain architecturally sane;
- new RTL must not make future Max mode impossible;
- new RTL must not encode historical delays as mandatory semantic states;
- agents should document any temporary timing assumptions.

A current phase is not incomplete merely because exact historical timing is not
yet implemented.

---

## 33. Rules for Future Contributors and Agents

When adding CPU functionality:

1. Do not add idle states solely to match an assumed instruction cycle count
   unless the timing subsystem explicitly requires them.
2. Do not make functional completion depend on an arbitrary historical delay.
3. Identify real dependencies separately from compatibility delays.
4. Preserve READY and bus dependency semantics in all modes.
5. Preserve the ability to execute dependency-driven in Max mode.
6. Prefer reusable timing metadata or timing classes over opcode-specific delay
   hacks.
7. Validate timing claims against evidence.
8. Do not call a profile cycle-accurate until it has been tested as such.
9. Do not modify architectural expected results to accommodate timing bugs.
10. Keep functional regressions independent from deep timing regressions.

---

## 34. Definition of Done for the Future Timing Subsystem

The timing subsystem will be considered mature when:

- one functional CPU implementation supports all timing modes;
- Accurate mode reproduces validated historical instruction timing;
- Accurate mode reproduces required BIU timing;
- READY/wait-state behaviour is correct;
- supported historical profiles are independently validated;
- Fast mode removes instruction-level artificial delays;
- Max mode removes all removable compatibility delays;
- architectural results remain identical across timing modes;
- peripheral clocks remain independent;
- SingleStep timing traces are used where applicable;
- PC/AT software remains stable under accurate profiles;
- Max mode remains functionally compatible;
- timing mode can be selected cleanly by system integration;
- no major opcode-specific timing hacks are required.

---

## 35. Long-Term Goal

The desired end state is:

```text
                        SPK286
                           |
                 one functional core
                           |
                   timing policy
          +----------------+----------------+
          |                |                |
          v                v                v
     Accurate 8 MHz   Accurate 25 MHz      Max
          |                |                |
          +----------------+----------------+
                           |
                           v
                        SPK286_AT
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
     historical PC/AT                 accelerated 286
      compatibility                    experiment
```

This allows SPK286 to serve both as:

- a historically oriented 80286 implementation;
- a platform for exploring how far the 286 architecture can be accelerated
  when freed from original silicon timing constraints.

---

## 36. Architectural Decision Summary

SPK286 adopts the following timing-model principles:

1. **One functional CPU implementation.**
2. **Functional semantics are independent from timing policy.**
3. **Real dependencies are mandatory in every mode.**
4. **Historical compatibility delays may be removed in accelerated modes.**
5. **Accurate mode targets validated 80286 timing profiles.**
6. **Fast mode may accelerate execution while retaining a constrained BIU.**
7. **Max mode executes as quickly as real dependencies and FPGA resources allow.**
8. **Peripheral timing remains independent from CPU acceleration.**
9. **SingleStep hardware traces will be used as timing evidence when the core is
   mature enough for cycle-level validation.**
10. **Functional Real Mode development must not be blocked by unfinished cycle
    accuracy.**

These rules should guide future SPK286 RTL, microcode and system integration.
