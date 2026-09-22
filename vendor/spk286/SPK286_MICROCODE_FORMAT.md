# SPK286 — Microcode Format and Tooling Specification

**Document:** `SPK286_MICROCODE_FORMAT.md`  
**Project:** SPK286  
**Status:** Updated microcode architecture specification  
**Primary microcode source format:** SPK286 Microcode DSL  
**Microcode compiler:** Python 3  
**Generated target:** Synthesizable SystemVerilog microcode ROM/package  
**Companion documents:**
- `SPK286_SPEC.md`
- `SPK286_REALMODE_MVP.md`
- `SPK286_ENVIRONMENT.md`
- `SPK286_TIMING_MODEL.md`

---

# 1. Purpose

This document defines the source format, compilation flow, generated representation, validation rules, and implementation boundaries for SPK286 microcode.

The goal is to make the SPK286 execution engine:

- readable;
- maintainable;
- synthesizable;
- testable;
- deterministic;
- suitable for automated development agents;
- extensible from real-mode execution toward later protected-mode support;
- independent from opaque hand-written hexadecimal ROM contents;
- compatible with a timing architecture in which functional semantics are
  separable from historical timing policy.

SPK286 shall use project-owned microcode.

The microcode system shall follow the timing architecture defined in
`SPK286_TIMING_MODEL.md`.

In particular:

> Functional semantics and timing policy must remain separable.

The number of microinstructions used to implement an architectural operation
must not, by itself, define the historical number of 80286 clock cycles for
that operation.

Real dependencies such as BIU completion, READY, operand availability,
prefetch availability, queue flush completion, and required serialization must
be respected in every timing mode.

Historical compatibility delays may be represented through explicit timing
metadata or a separate timing-policy mechanism and may be bypassed in
accelerated modes where architecturally safe.

The project must not claim to reproduce Intel's original 80286 internal microcode unless authentic source material becomes available and its legal and technical use is explicitly justified.

---

# 2. Design Decision

SPK286 shall use:

```text
SPK286 Microcode DSL
        |
        v
Python microcode compiler
        |
        +--> generated SystemVerilog definitions
        |
        +--> generated microcode ROM
        |
        +--> human-readable listing
        |
        +--> symbol/debug map
        |
        +--> validation report
        |
        +--> optional timing metadata / timing-class definitions
        |
        v
SPK286 microsequencer
```

The authoritative microcode source shall be the DSL source.

Generated SystemVerilog shall not be manually edited.

---

# 3. What Is a DSL?

DSL means **Domain-Specific Language**.

A DSL is a small language designed for one specific technical domain rather than for general-purpose programming.

Examples of well-known DSLs include SQL for database queries and regular-expression syntax for pattern matching.

In SPK286, the DSL exists specifically to describe CPU micro-operations in a form that is easy for humans, development agents, and debugging tools to understand.

The DSL is **not executed by the FPGA**.

The development flow is:

```text
human / agent
      |
      v
SPK286 .mc source
      |
      v
Python microcode compiler
      |
      v
generated microinstruction ROM
      |
      v
SystemVerilog / FPGA
```

For example, a developer may write:

```text
instruction ADD_R16_RM16:
    READ16 EA -> TMP0
    DST + TMP0 -> DST FLAGS_ARITH
    END
```

The Python compiler translates those symbolic statements into the packed control fields required by the SPK286 microsequencer and datapath.

The synthesized FPGA therefore contains the generated microcode representation, not a parser or interpreter for the DSL.

This separation allows the human-readable microcode language to remain stable even if the internal packed microinstruction format changes later.

---

# 5. Why a Dedicated DSL

The microcode source shall use a small domain-specific language instead of directly encoding microinstructions as:

- hexadecimal constants;
- binary constants;
- raw packed SystemVerilog structures;
- YAML records for every individual microinstruction;
- large hand-written `case` statements.

The DSL exists to express CPU micro-operations in terminology close to the SPK286 architecture.

Example:

```text
instruction MOV_R16_IMM16:
    FETCH_IMM16 -> TMP0
    TMP0 -> DST
    END
```

This is intentionally more readable than a raw encoded microinstruction such as:

```text
0x41A802130005
```

or a large packed SystemVerilog initializer.

The compiler is responsible for translating symbolic operations into the actual microinstruction encoding.

---

# 5. Scope

The first version of the microcode system shall support the needs of the Real-Mode MVP.

Initial use includes:

- register transfers;
- ALU operations;
- FLAGS updates;
- effective-address sequencing;
- memory reads;
- memory writes;
- I/O reads;
- I/O writes;
- stack operations;
- instruction sequencing;
- branches inside microcode;
- instruction completion;
- prefetch interaction;
- exceptions relevant to real mode.

The first version does not need to implement historical cycle accuracy, but it
must not encode instruction semantics in a form that prevents later
Accurate/Fast/Max timing policies.

The design must reserve clean extension points for later:

- descriptor reads;
- privilege checks;
- protected-mode exception entry;
- gate handling;
- task switching;
- system instructions;
- LOADALL-related internal state if later implemented;
- timing classes or other explicit timing metadata;
- timing-policy synchronization points where later evidence proves they are
  required.

Protected-mode mechanisms and the final timing-metadata syntax do not need to
be implemented in the first DSL/compiler version, but the format must not make
them impractical to add.

---

# 6. Source Tree

Recommended layout:

```text
microcode/
├── README.md
├── source/
│   ├── core.mc
│   ├── data_move.mc
│   ├── alu.mc
│   ├── stack.mc
│   ├── control.mc
│   ├── strings.mc
│   ├── io.mc
│   ├── exceptions.mc
│   └── system.mc
├── generated/
│   ├── spk286_microcode_pkg.sv
│   ├── spk286_microcode_rom.sv
│   ├── spk286_microcode.lst
│   ├── spk286_microcode_symbols.json
│   └── spk286_microcode_validation.json
└── tools/
    └── compile_microcode.py
```

The exact file split may evolve.

The logical separation by instruction family is preferred over one monolithic source file.

---

# 7. File Extension

SPK286 microcode source files shall use:

```text
.mc
```

Example:

```text
microcode/source/data_move.mc
```

The `.mc` extension means SPK286 microcode source and does not imply compatibility with any external microcode language.

---

# 8. Language Philosophy

The DSL shall remain intentionally small.

It is not a general-purpose programming language.

It shall not contain:

- arbitrary loops;
- dynamic memory allocation;
- user-defined runtime functions;
- recursion;
- arbitrary arithmetic expressions;
- hidden side effects;
- implicit control flow.

Every DSL statement must compile into a deterministic and inspectable micro-operation or microsequencer action.

The source should make execution ordering explicit.

Historical timing delay must not be hidden inside otherwise functional
statements. If timing annotations are introduced, they must be explicit,
inspectable, deterministic, and semantically separate from the architectural
operation itself.

---

# 9. Basic Syntax

Initial syntax concept:

```text
instruction <NAME>:
    <statement>
    <statement>
    ...
```

Example:

```text
instruction MOV_R16_IMM16:
    FETCH_IMM16 -> TMP0
    TMP0 -> DST
    END
```

Labels may be used inside instruction bodies:

```text
instruction LOOP:
start:
    CX - 1 -> CX FLAGS_NONE
    IF_NOT_ZERO CX, branch
    END

branch:
    APPLY_REL8
    FLUSH_PREFETCH
    END
```

Exact syntax may evolve only through an intentional format-version change.

---

# 10. Comments

Comments shall use:

```text
# comment
```

Example:

```text
instruction PUSH_R16:
    # SP is decremented before the write.
    SP - 2 -> SP FLAGS_NONE
    WRITE16 SS:SP, SRC
    END
```

All comments and identifiers in microcode source shall be written in English.

---

# 11. Identifiers

Identifiers shall use uppercase snake case for architectural and micro-operation names.

Examples:

```text
MOV_R16_IMM16
FETCH_IMM16
READ16
WRITE16
TMP0
TMP1
ALU_RESULT
EXCEPTION_VECTOR
```

Local labels should use lowercase snake case where practical:

```text
repeat_loop:
fault_exit:
done:
```

---

# 12. Architectural Operands

The initial DSL shall recognize symbolic operands for:

## General registers

```text
AX BX CX DX
SP BP SI DI
```

## Byte register halves

```text
AH AL
BH BL
CH CL
DH DL
```

## Segment registers

```text
CS DS SS ES
```

## Instruction state

```text
IP
FLAGS
```

## Internal temporaries

At minimum:

```text
TMP0
TMP1
TMP2
TMP3
```

The exact number of internal temporaries is an RTL implementation decision.

The DSL compiler must reject references to undefined architectural or temporary operands.

---

# 13. Decoder-Resolved Operands

The decoder/microsequencer interface should allow generic symbolic operands such as:

```text
SRC
DST
RM
REG
EA
SEG
IMM8
IMM16
DISP8
DISP16
```

These refer to instruction-decoder results rather than fixed registers.

Example:

```text
instruction MOV_RM16_R16:
    REG -> TMP0
    WRITE16 EA, TMP0
    END
```

The compiler does not decide ModR/M meaning.

The decoder and effective-address subsystem provide the resolved operand metadata.

---

# 14. Micro-Operation Classes

The DSL shall organize operations into a small set of classes.

## 13.1 Data transfer

Examples:

```text
SRC -> DST
```

```text
IMM16 -> TMP0
```

```text
TMP0 -> AX
```

## 13.2 ALU

Examples:

```text
AX + TMP0 -> AX FLAGS_ARITH
AX - TMP0 -> TMP1 FLAGS_ARITH
TMP0 AND TMP1 -> TMP2 FLAGS_LOGIC
TMP0 XOR TMP1 -> TMP2 FLAGS_LOGIC
```

## 13.3 Shifts and rotates

Examples:

```text
SHL TMP0, 1 -> TMP0 FLAGS_SHIFT
ROR TMP0, CL -> TMP0 FLAGS_ROTATE
```

Exact supported shift/rotate forms shall follow the implemented 80286 execution datapath.

## 13.4 Memory operations

Examples:

```text
READ8 EA -> TMP0
READ16 EA -> TMP0
WRITE8 EA, TMP0
WRITE16 EA, TMP0
```

Segment-qualified operations may be represented as:

```text
READ16 SS:SP -> TMP0
WRITE16 SS:SP, TMP0
```

## 13.5 I/O operations

Examples:

```text
IO_READ8 DX -> TMP0
IO_READ16 DX -> TMP0
IO_WRITE8 DX, TMP0
IO_WRITE16 DX, TMP0
```

## 13.6 Instruction-stream operations

Examples:

```text
FETCH_IMM8 -> TMP0
FETCH_IMM16 -> TMP0
FETCH_DISP8 -> TMP0
FETCH_DISP16 -> TMP0
```

## 13.7 Prefetch operations

Examples:

```text
FLUSH_PREFETCH
REQUEST_PREFETCH
```

The microcode shall not directly implement the entire prefetch state machine.

The Bus Interface Unit / Instruction Unit owns the physical prefetch mechanism.

Microcode only requests architecturally meaningful actions.

## 13.8 Stack operations

Stack actions may initially expand into ordinary ALU and bus operations.

Example:

```text
SP - 2 -> SP FLAGS_NONE
WRITE16 SS:SP, TMP0
```

Helper micro-operations such as:

```text
PUSH16 TMP0
POP16 -> TMP0
```

may later be added if they compile into explicit deterministic sequences.

## 13.9 Exception and interrupt operations

Initial symbolic operations may include:

```text
RAISE_EXCEPTION <vector>
ENTER_INTERRUPT <vector>
```

The centralized exception unit remains responsible for architectural semantics.

Microcode must not duplicate exception policy across instruction families.

## 13.10 Instruction completion

Every normal instruction path must terminate explicitly with:

```text
END
```

Exception paths must terminate through a defined exception transfer mechanism.

Falling off the end of an instruction block is a compiler error.

---

# 15. FLAGS Control

FLAGS updates must always be explicit.

Initial modes should include:

```text
FLAGS_NONE
FLAGS_ARITH
FLAGS_LOGIC
FLAGS_INC
FLAGS_DEC
FLAGS_SHIFT
FLAGS_ROTATE
FLAGS_MUL
FLAGS_DIV
```

The exact list is implementation-defined and may grow.

Example:

```text
TMP0 + TMP1 -> TMP2 FLAGS_ARITH
```

An ALU operation without a declared FLAGS policy shall be rejected unless the operation has a compiler-defined fixed policy.

This is intended to prevent accidental flag updates.

Undefined or reserved 80286 FLAGS behavior must be implemented from documented/tested evidence rather than inherited from later x86 processors.

---

# 16. Microcode Control Flow

The DSL shall support explicit local branches.

Initial forms:

```text
GOTO <label>
```

```text
IF_ZERO <operand>, <label>
IF_NOT_ZERO <operand>, <label>
IF_FLAG <flag>, <label>
IF_NOT_FLAG <flag>, <label>
```

Example:

```text
instruction REP_MOVSB:
repeat_loop:
    IF_ZERO CX, done
    MOVSB_STEP
    CX - 1 -> CX FLAGS_NONE
    GOTO repeat_loop

done:
    END
```

The exact string-operation decomposition may differ.

No implicit looping shall be generated by the compiler unless explicitly documented.

---

# 17. Calls and Shared Microcode

The first implementation should prefer explicit local sequences.

If significant duplication appears, the DSL may support:

```text
CALL_MICRO <routine>
RETURN_MICRO
```

Shared microcode routines must have:

- well-defined inputs;
- well-defined outputs;
- documented temporary-register usage;
- deterministic return behavior.

A hardware micro-return stack shall not be introduced unless its resource and timing cost is justified.

Compiler inlining may be preferred for small shared routines.

---

# 18. Instruction Entry Points

Each decoded instruction form shall map to one symbolic microcode entry point.

Example concept:

```text
opcode/form                  microcode entry
------------------------------------------------
MOV r16, imm16               MOV_R16_IMM16
MOV r/m16, r16               MOV_RM16_R16
ADD r16, r/m16               ADD_R16_RM16
PUSH r16                     PUSH_R16
```

The mapping may be generated as part of the decoder tables.

The compiler shall emit a symbol map containing every entry-point address.

---

# 19. Microinstruction Representation

The exact packed RTL width shall be determined after the initial datapath and microsequencer skeleton exist.

The logical microinstruction shall contain fields equivalent to:

```text
source_a
source_b
destination
alu_operation
flags_mode
bus_operation
bus_width
address_source
prefetch_action
ip_action
sequencer_action
condition
next_address
special_operation
optional_timing_class
optional_minimum_timing
```

The timing-related fields above are conceptual extension points. They do not
need to exist physically in the first implementation, and their exact encoding
must remain deferred until timing work begins.

Not every field must physically exist if a more compact encoding is justified.

The DSL must remain independent from the packed bit positions.

This separation allows the microinstruction encoding to evolve without rewriting instruction source.

---

# 20. Suggested SystemVerilog Type

Generated RTL may use a structure conceptually similar to:

```systemverilog
typedef struct packed {
    src_sel_t        src_a;
    src_sel_t        src_b;
    dst_sel_t        dst;
    alu_op_t         alu_op;
    flags_mode_t     flags_mode;
    bus_op_t         bus_op;
    bus_width_t      bus_width;
    prefetch_op_t    prefetch_op;
    seq_op_t         seq_op;
    cond_t           condition;
    micro_addr_t     next_addr;
    timing_class_t   timing_class; // Optional future field.
} microinstruction_t;
```

The `timing_class` field is illustrative only. The first implementation may
omit it entirely.

The final structure shall be based on measured implementation needs and must
preserve the separation between functional control and historical timing
policy.

The DSL compiler owns the mapping from source statements to this representation.

---

# 21. ROM Implementation

The generated microcode shall be synthesizable as FPGA ROM.

Preferred result:

```systemverilog
localparam microinstruction_t MICROCODE_ROM [0:MICROCODE_DEPTH-1] = '{
    ...
};
```

or an equivalent inferred-ROM implementation.

Vendor-specific RAM primitives must not be required by the architectural CPU source.

If Quartus inference quality requires a wrapper or alternate initialization form, that mechanism shall remain isolated from the authoritative DSL.

---

# 22. Microcode Compiler

The compiler shall be written in Python 3.

Recommended path:

```text
tools/microcode/compile_microcode.py
```

or:

```text
microcode/tools/compile_microcode.py
```

The exact path may follow the final repository organization.

The compiler should rely on the Python standard library where practical.

---

# 23. Compiler Stages

The compiler shall conceptually perform:

```text
source files
    |
    v
lexer / parser
    |
    v
intermediate representation
    |
    v
symbol resolution
    |
    v
semantic validation
    |
    v
micro-op expansion
    |
    v
microinstruction encoding
    |
    +--> SystemVerilog
    +--> listing
    +--> symbols
    +--> validation metadata
```

A complex compiler framework is not required.

A small hand-written parser is acceptable if the grammar remains simple and well tested.

---

# 24. Intermediate Representation

The Python compiler should create an explicit internal representation before generating RTL.

Example conceptual Python structures:

```python
class MicroInstruction:
    pass

class MicroBlock:
    pass

class MicroProgram:
    pass
```

The actual implementation may use dataclasses.

The IR must preserve:

- source file;
- source line;
- instruction entry point;
- local label;
- generated micro-address;
- symbolic operands;
- expanded operations.

This information is important for debugging and failure reports.

---

# 25. Required Compiler Validation

Compilation must fail on at least:

- duplicate instruction entry names;
- duplicate labels within a scope;
- unresolved labels;
- invalid operands;
- invalid micro-operation names;
- invalid FLAGS mode;
- illegal bus width;
- impossible source/destination combinations known to the compiler;
- branch target outside valid scope;
- instruction path without `END` or exception transfer;
- microcode ROM overflow;
- generated address width overflow;
- invalid or undefined timing class, if timing metadata is enabled;
- timing annotations that violate the active microcode-format version.

Warnings should be produced for:

- unreachable labels;
- unreachable microinstructions;
- unused shared routines;
- suspicious temporary-register overwrite where detectable.

---

# 26. Determinism

Given identical:

- microcode source;
- compiler version;
- compiler options;

the generated output must be byte-for-byte deterministic where practical.

The compiler must not depend on:

- unordered filesystem traversal;
- random symbol assignment;
- timestamps embedded in generated RTL;
- host-specific absolute paths.

A build timestamp may be emitted only in a separate non-authoritative report if desired.

---

# 27. Generated Files

Minimum generated artifacts:

## SystemVerilog package

```text
microcode/generated/spk286_microcode_pkg.sv
```

Contains:

- microinstruction types or generated constants where appropriate;
- microcode entry-point constants;
- ROM size constants;
- generated enum/table information if required.

## ROM

```text
microcode/generated/spk286_microcode_rom.sv
```

Contains the synthesized microcode contents or ROM module.

## Listing

```text
microcode/generated/spk286_microcode.lst
```

Human-readable example:

```text
0000  MOV_R16_IMM16
0000    FETCH_IMM16 -> TMP0
0001    TMP0 -> DST
0002    END

0003  ADD_R16_RM16
0003    READ16 EA -> TMP0
0004    DST + TMP0 -> DST FLAGS_ARITH
0005    END
```

## Symbol map

```text
microcode/generated/spk286_microcode_symbols.json
```

Contains mappings such as:

```json
{
  "MOV_R16_IMM16": 0,
  "ADD_R16_RM16": 3
}
```

Additional local-label mappings may be included.

## Validation report

```text
microcode/generated/spk286_microcode_validation.json
```

Contains:

- compiler format version;
- source file hashes;
- ROM depth;
- used entries;
- unused entries;
- warnings;
- instruction entry count;
- timing metadata/version information when timing annotations are enabled;
- validation status.

---

# 28. Source Mapping

The compiler shall preserve source mapping from generated micro-addresses back to DSL source.

Example:

```text
micro_pc 0x0123
    -> data_move.mc
    -> instruction MOV_RM16_R16
    -> line 42
    -> WRITE16 EA, TMP0
```

This mapping is required for useful debugging.

SingleStep regression failures should be able to report the current:

```text
micro_pc
microcode entry
source file
source line
source statement
```

where practical.

---

# 29. Debug Integration

Simulation builds should expose at least:

```text
micro_pc
micro_entry
micro_instruction
micro_source_symbol
timing_mode
timing_wait_active
timing_class
```

The timing-related signals are required only once the timing-policy subsystem
exists. Until then, simulation tooling may omit them.

The symbol text itself does not need to exist in synthesized hardware.

Simulation tooling may map numeric values to symbols using the generated JSON/listing files.

The FPGA implementation should keep only hardware-relevant numeric state.

---

# 30. Build Integration

A standard generation command shall be provided.

Example:

```bash
python3 tools/microcode/compile_microcode.py
```

or:

```bash
make microcode
```

Normal RTL build should ensure generated files are up to date.

A stale generated microcode artifact must be detectable.

---

# 31. Generated-File Consistency Check

CI and local validation should support:

```text
compile microcode from source
        |
        v
compare against committed/generated expected output
        |
        +--> identical: PASS
        |
        +--> different: FAIL
```

Whether generated RTL is committed to Git or recreated during every build is a repository policy decision.

In either case, generated output must be reproducible.

---

# 32. Unit Testing the Compiler

The microcode compiler requires its own tests.

Test at least:

- valid minimal instruction;
- labels;
- conditional branch;
- undefined label rejection;
- duplicate label rejection;
- invalid operand rejection;
- missing `END`;
- ROM overflow;
- deterministic output;
- source mapping.

Compiler tests shall run independently from RTL simulation.

---

# 33. Unit Testing Microcode Behavior

Microcode must be verified at several levels.

## Level 1 — Compiler validation

Prove that the source is structurally valid.

## Level 2 — Microsequencer unit tests

Verify:

- sequential next;
- branch;
- condition evaluation;
- instruction completion;
- ROM addressing.

## Level 3 — Directed CPU tests

Verify short instruction examples.

## Level 4 — SingleStep functional tests

Verify architectural result.

## Level 5 — SingleStep bus tests

Verify externally visible transactions.

## Level 6 — Timing-policy invariance

When multiple timing modes exist, verify that architectural results remain
identical across Accurate, Fast, and Max modes for the same initial state and
program, except for timing-observation fields.

## Level 7 — Cycle comparison

Refine instruction and bus timing where required.

The microcode language is not considered correct merely because it compiles.

---

# 34. Relationship to SingleStepTests

SingleStepTests/80286 remains the primary empirical reference for real-mode behavior.

The microcode must never contain special cases for:

- known SingleStep test addresses;
- test indexes;
- specific corpus byte sequences solely to pass tests.

The correct flow is:

```text
SingleStep failure
        |
        v
inspect architectural behavior
        |
        v
inspect bus/cycle divergence
        |
        v
identify RTL or microcode cause
        |
        v
fix general CPU behavior
```

---

# 35. Relationship to Decoder

The decoder identifies the architectural instruction form.

The microcode implements the execution sequence.

The boundary should conceptually be:

```text
instruction bytes
      |
      v
decoder
      |
      +--> instruction form
      +--> operand metadata
      +--> prefixes
      +--> ModR/M metadata
      |
      v
microcode entry point
```

The microcode compiler shall not become a second x86 decoder.

---

# 36. Relationship to Effective Address Unit

Effective-address calculation should remain a reusable CPU subsystem.

Microcode may request:

```text
CALC_EA
```

or consume decoder-prepared `EA` state.

The exact split shall be determined by the RTL architecture.

The microcode must not duplicate 16-bit ModR/M addressing tables across instruction bodies.

---

# 37. Relationship to Bus Interface Unit

The Bus Interface Unit owns physical bus-cycle sequencing.

Microcode requests logical bus operations such as:

```text
READ16 EA -> TMP0
WRITE16 EA, TMP0
IO_READ8 DX -> TMP0
```

The BIU is responsible for:

- physical address presentation;
- BHE;
- byte lanes;
- Ts/Tc/Ti sequencing;
- READY;
- HOLD/HLDA interaction;
- bus status;
- actual completion timing.

Microcode shall stall until a requested bus operation reports completion.

BIU completion and READY are real dependencies. They must be honoured in every
timing mode, including Max mode.

Historical bus-cycle compatibility belongs to the BIU/timing-policy layer, not
to opcode-specific delay sequences embedded in microcode.

This separation is essential for later bus/cycle convergence and for supporting
both historically accurate and accelerated execution with one functional CPU.

---

# 38. Relationship to Prefetch Unit

The prefetch queue and refill mechanism belong to the Instruction Unit / BIU.

Microcode may request:

```text
FLUSH_PREFETCH
```

or other explicitly defined control actions.

Microcode shall not directly manipulate queue storage indices unless a later architecture review proves that necessary.

All timing modes must preserve identical architectural instruction-stream
semantics. Accelerated modes may refill the queue sooner, but may not bypass
queue correctness, stale-read rejection, redirects, or required byte
availability.

This preserves separation between execution semantics and physical fetch behavior.

---

# 39. Relationship to Exception Unit

Exception sequencing must remain centralized.

Microcode may indicate:

```text
RAISE_EXCEPTION INVALID_OPCODE
```

but the architectural exception unit is responsible for:

- vector selection;
- saved state;
- priority;
- stack operations where centralized;
- restart/fault semantics;
- mode-dependent behavior.

This is especially important for future protected mode.

---

# 40. Future Protected-Mode Extension

The microcode architecture must reserve the ability to add operations such as:

```text
LOAD_DESCRIPTOR
CHECK_SEGMENT_LIMIT
CHECK_PRIVILEGE
LOAD_TASK_STATE
SAVE_TASK_STATE
ENTER_GATE
```

These names are illustrative.

They are not required to exist in the Real-Mode MVP.

The important requirement is that the microsequencer, compiler, and packed format can grow without replacing the entire real-mode microcode architecture.

Protected-mode sequencing must follow the same timing rule as Real Mode:
descriptor fetches, privilege checks, gate processing, task operations and
exception sequencing are functional dependencies; historical delays associated
with them must remain separable from those semantics.

---

# 41. Microcode Versioning

The DSL shall have an explicit format version.

Example:

```text
microcode_format 1
```

A source-format change that breaks compatibility shall increment this version.

Compiler output metadata shall record the accepted format version.

---

# 42. No Silent Semantics

The compiler shall not silently infer behavior that affects architectural correctness.

Examples of behavior that must remain explicit:

- FLAGS updates;
- memory access width;
- instruction completion;
- queue flush;
- exception transfer;
- microcode branch;
- timing-policy synchronization or compatibility delay, if present.

Convenience syntax is allowed only when its expansion is deterministic and documented.

A compiler convenience form must not silently introduce historical delay into a
functional operation.

---

# 43. Example — MOV Immediate

Illustrative source:

```text
instruction MOV_R16_IMM16:
    FETCH_IMM16 -> TMP0
    TMP0 -> DST
    END
```

Possible expanded listing:

```text
MOV_R16_IMM16:
    FETCH_WORD TMP0
    MOVE TMP0 DST
    END
```

The exact encoded microinstructions are an implementation detail.

---

# 44. Example — ADD Register/Memory

Illustrative source:

```text
instruction ADD_R16_RM16:
    READ16 EA -> TMP0
    DST + TMP0 -> DST FLAGS_ARITH
    END
```

For a register-form ModR/M instruction, the decoder/execution interface may allow the same entry to avoid a physical memory bus request.

Alternatively, register and memory forms may use separate microcode entries.

This decision must be based on RTL clarity and timing behavior.

---

# 45. Example — PUSH

Illustrative source:

```text
instruction PUSH_R16:
    SRC -> TMP0
    SP - 2 -> SP FLAGS_NONE
    WRITE16 SS:SP, TMP0
    END
```

The final ordering must match verified 80286 behavior.

This example defines DSL style, not authoritative instruction timing.

If later timing evidence requires PUSH to consume additional historical cycles,
those cycles should be represented through the timing-policy mechanism rather
than by adding semantically meaningless micro-operations to this sequence.

---

# 46. Example — Conditional Branch

Illustrative source:

```text
instruction JZ_REL8:
    IF_NOT_FLAG ZF, not_taken
    APPLY_REL8
    FLUSH_PREFETCH
    END

not_taken:
    SKIP_REL8
    END
```

The actual decoder/fetch architecture may consume the displacement before microcode begins.

The final implementation shall follow the chosen SPK286 instruction-unit contract.

---

# 47. Example — REP Structure

Illustrative only:

```text
instruction REP_MOVSB:
repeat_loop:
    IF_ZERO CX, done
    MOVSB_STEP
    CX - 1 -> CX FLAGS_NONE
    GOTO repeat_loop

done:
    END
```

A production implementation may require additional checks for:

- REP/REPE/REPNE semantics;
- interrupts between iterations;
- segment overrides;
- direction flag;
- prefetch interaction;
- exact 80286 restart behavior.

The DSL must be capable of expressing such sequencing explicitly.

---

# 48. Style Rules

Microcode source shall prioritize:

1. architectural clarity;
2. explicit side effects;
3. testability;
4. traceability;
5. compactness.

Avoid clever compressed forms that obscure bus or FLAGS behavior.

One instruction family should follow a consistent style.

---

# 49. Agent Rules

An implementation agent modifying microcode must:

1. inspect relevant 80286 documentation;
2. inspect applicable SingleStep cases;
3. understand current decoder/BIU contracts;
4. modify one coherent instruction family at a time;
5. regenerate microcode;
6. run compiler tests;
7. run relevant RTL unit tests;
8. run relevant SingleStep functional tests;
9. inspect bus mismatches separately;
10. record regressions and known timing debt;
11. preserve separation between functional semantics and timing policy;
12. never add idle/NOP micro-operations solely to force a historical cycle count
    when an explicit timing-policy mechanism should represent that delay;
13. distinguish real dependency stalls from removable compatibility waits.

The agent must not change the compiler encoding and instruction behavior simultaneously unless necessary and clearly documented.

An agent must not claim cycle accuracy merely because an instruction has been
padded to match a published cycle count. Timing claims require evidence and
must follow `SPK286_TIMING_MODEL.md`.

---

# 50. Initial Implementation Order

Recommended microcode-tooling sequence:

```text
DSL grammar
    |
    v
minimal Python parser
    |
    v
IR
    |
    v
symbol resolution
    |
    v
SystemVerilog generator
    |
    v
listing + symbol map
    |
    v
microsequencer skeleton
    |
    v
first microcoded operation
    |
    v
MOV
    |
    v
ALU
    |
    v
stack
    |
    v
control flow
    |
    v
remaining Real-Mode MVP
    |
    v
timing-policy integration
```

Do not design the entire final protected-mode microinstruction vocabulary before real-mode execution exists.

Likewise, do not block functional Real-Mode completion on exact historical
timing. The microcode architecture must merely preserve a clean path to later
timing integration.

---

# 51. First Compiler Milestone

The first useful compiler milestone shall:

- parse at least one `.mc` file;
- support instruction entry points;
- support sequential statements;
- support labels;
- support `END`;
- resolve symbolic micro-addresses;
- generate synthesizable SystemVerilog;
- generate a readable listing;
- generate a symbol map;
- reject invalid input;
- produce deterministic output;
- have unit tests.

It does not need to support the full final DSL.

It also does not need to implement timing annotations. If timing metadata is
not yet supported, the compiler and IR should avoid assumptions that would make
such metadata difficult to add later.

---

# 52. First CPU Milestone Using Microcode

The first CPU behavior using generated microcode should be deliberately small.

Recommended progression:

```text
RESET
  |
  v
fetch
  |
  v
decoder
  |
  v
microcode entry
  |
  v
MOV register, immediate
  |
  v
END
```

This proves the complete toolchain before large instruction families are implemented.

---

# 53. Definition of Done for the Initial Microcode System

The initial microcode subsystem is considered ready for normal SPK286 development when:

- `.mc` source is authoritative;
- Python compilation is deterministic;
- generated SystemVerilog synthesizes;
- Verilator accepts the generated ROM;
- Icarus accepts the generated ROM;
- labels and entry points resolve correctly;
- compiler errors are useful;
- source mapping exists;
- micro-PC is observable in simulation;
- at least one real instruction executes through generated microcode;
- regeneration is integrated into the documented build flow;
- functional sequencing does not depend on arbitrary historical delay states;
- the implementation remains compatible with the timing architecture defined in
  `SPK286_TIMING_MODEL.md`.

---

# 54. Deferred Decisions

The following details should not be frozen until the initial datapath exists:

- exact microinstruction width;
- exact ROM depth;
- exact number of temporary registers;
- exact bit allocation;
- whether shared routines use call/return or compiler inlining;
- whether the ROM is committed or generated at build time;
- whether some simple instructions bypass microcode;
- exact opcode-to-entry encoding;
- exact handling of register-vs-memory ModR/M forms;
- exact timing-annotation syntax in the DSL;
- exact timing metadata width or encoding;
- whether timing is represented by cycle budgets, timing classes, scheduler
  tables, per-micro-operation minima, or another evidence-driven mechanism;
- exact ownership boundary between microsequencer timing metadata and the
  external timing scheduler.

These decisions must be driven by implementation evidence rather than guessed prematurely.

---

# 55. Final Constraint

The microcode system exists to make SPK286 easier to understand and verify.

It must not become an opaque abstraction layer that hides CPU behavior.

It must also not become the place where historical timing is encoded through
unexplained idle operations. Functional sequencing must remain understandable
independently from compatibility timing.

The guiding rule is:

> A developer inspecting a failing instruction should be able to move from the SingleStep failure to the current micro-PC, from the micro-PC to a symbolic microcode statement, and from that statement to the RTL subsystem responsible for the observable behavior.

For timing failures, the same developer should additionally be able to
distinguish:

```text
functional dependency
    vs.
historical compatibility delay
```

and identify whether the observed wait belongs to the microsequencer, BIU,
READY/memory dependency, prefetch subsystem, or timing-policy layer.

The intended result is:

```text
Readable SPK286 microcode
        +
deterministic Python tooling
        +
synthesizable SystemVerilog
        +
hardware-derived regression
        +
separable timing policy
        =
maintainable and timing-extensible 80286 execution engine
```

## Phase 5 implemented format 4 extension

The implemented compiler accepts formats 1 through 4. Format 4 adds these
functional operations without altering formats 1..3 or the generic sequential
microsequencer. Encoding 4 retains a five-bit control word. The active image
uses 97 words, seven address bits and twenty entries; the first 45 words and
eight inherited entries are unchanged. The emitted package exposes
`MC_FORMAT_VERSION`, independently checked by the ROM auditor.

| Control | Encoding | Completion and effect |
|---|---:|---|
| `CHECK_RM16` | 19 | Validate decoded whole-word destination without data/GPR access |
| `FETCH_IMM8S -> TMP0` | 20 | Consume and sign-extend one instruction byte |
| `PUSH16 DECODED TMP0` | 21 | Conditionally push captured source/decoded next IP through SS; commit SP on completion |
| `POP16 -> TMP0` | 22 | Read SS:SP, capture word and commit SP+2 on completion |
| `READ_IP16 -> TMP0` | 23 | Capture current architectural next IP |
| `TARGET_REL16 TMP1` | 24 | Capture (architectural next IP + TMP1) modulo 65536 |
| `TARGET_ABS16 TMP0` | 25 | Capture absolute near target |
| `REDIRECT DECODED` | 26 | If taken, accept IP/prefetch restart; otherwise complete without flush |
| `ADJUST_SP16 TMP1` | 27 | Commit unsigned SP adjustment after stack pop |
| `COUNT DECODED` | 28 | Decrement CX for LOOP family; preserve it for JCXZ |

Target and temporary lifetime validation rejects undefined sources, duplicate
stack/count operations, target overwrite, missing target/redirect, work after
redirect, and POP memory writes without a prior destination precheck. Pending
ALU FLAGS must still be disposed and committed according to format 3 rules.
A target is local to one instruction and clears on start/reset/external cancel.
Formatting whitespace is non-semantic. Labels remain debug source mappings,
not executable microbranches. No timing mode is inferred from ROM length.

## Phase 6 implemented candidate format 5

Format 5 widens controls from five to six bits; the address remains seven bits.
The 128-word active image contains 28 entries. Numeric controls 0–28 retain their
meanings; 29–45 add FETCH_IMM8, READ_FLAGS, RESTORE_FLAGS, SET_IF, HALT,
REQUEST_EVENT, EVENT_ACK, EVENT_FLAGS, EVENT_CS, EVENT_IP, CLEAR_IF_TF,
VECTOR_IP, VECTOR_CS, CONTEXT_COMMIT, POP16_TMP1, POP16_TMP2 and IRET_COMMIT.

The common EVENT_ENTRY protocol is ACK, acquire/push saved FLAGS, acquire/push
saved CS, acquire/push saved IP, clear live IF/TF, read vector IP/CS, install
context, END. INTERRUPT_RETURN pops TMP0/TMP1/TMP2, installs IP/CS/FLAGS together,
then END. INTA and stack operations wait for their real service completions.

Compiler validation recognizes bounded functional protocols rather than decoding
x86 opcodes. Saved fields and candidate lifetimes must precede consumers; malformed
ordering, unavailable temporaries and incomplete event terminals fail compilation.
Frozen formats 1–4 remain source-derived tests. The only removal in inherited
active stack sequencing is POP_RM16's destination precheck, corrected from pinned
physical fault evidence. Generated source maps preserve symbolic micro-PC lookup.
This functional sequencing defines no historical clock count or timing profile.

## Format 6 byte extension (verified prior image)

Format 6 retains format 1–5 parsing and frozen fixtures. Controls 46–57 are
READ_REG8, READ_RM8, WRITE_REG8, WRITE_RM8, FETCH_IMM8_TMP1, READ_REG8_TMP1,
READ_RM8_TMP1, READ_DST8, MOVE8, WRITE_RESULT_REG8, WRITE_RESULT_RM8 and
WRITE_RESULT_DST8. Byte DSL operands spell REG8/RM8/DST8 explicitly; TMP0/TMP1
reads are zero extended. Byte lifetimes, ModR/M availability and result/FLAGS
disposition reuse the existing datapath validation, with mixed word/event
controls rejected in byte programs.

The active image has 37 entries, 174 words, eight-bit addresses and six-bit
controls. All inherited entry addresses remain stable. The immediate fetch and
RM read in ALU_RM16_IMM16 and ALU_RM16_IMM8S are reordered to acquire all required
instruction bytes before a data access. Historical format fixtures are not
rewritten. `microcode_phase7_byte.json` independently specifies the active words,
entries and labels, including that ordering change.

This sequential extension has no executable microcode branches or REP loops.
The separate, uncommitted I/O prototype grows to 41 entries/190 words and is not
the production format contract.

## Verified prior format 7 scalar extension

Format 7 retains all prior formats and adds four six-bit controls:
58 FLAGS_DECODED; 59 SIGN_EXTEND8; 60 SIGN_FILL16; 61 CONST_ONE_TMP1.
`FLAGS DECODED` commits only a decoded candidate/mask through the existing FLAGS
owner. `SIGN_EXTEND8 TMP0` sign-extends the low byte; `SIGN_FILL16 TMP0` replaces
the temporary with its word sign replicated sixteen times. `CONST_ONE -> TMP1`
provides the mathematical constant for INC/DEC. Each operation performs required
functional work; none models historical compatibility delay.

The exact permitted scalar protocols are direct flag update/END; READ_FLAGS to
TMP0, TMP0 to DST8, END; READ_DST16 to TMP0, sign operation, TMP0 to DST, END;
and READ_DST16, constant one, shared ALU, conditional result disposition, FLAGS
commit, END. Decode captures independent source and destination register indexes.
Thus CWD obtains AX while committing DX without adding architectural storage.

The active independent fixture is `microcode_phase7_scalar.json`: 42 entries,
193 words, eight-bit addresses, six-bit controls. All 174 prior control words,
entries and source maps remain a stable prefix. The format-6 source snapshot is
`microcode_phase7_byte_sources.json`; prior expected results are not rewritten.
The isolated I/O prototype's 58–62 control assignments conflict with this newer
source contract and require a deliberate source rebase and regeneration.

## Verified prior format 8 shift/rotate extension

Format 8 adds SHIFT (62) and COUNT_LOW_TMP1 (63), retaining eight-bit addresses
and six-bit controls. The active image contains 48 entries/235 words. All 193
prior words and entry addresses remain unchanged; format-7 sources are frozen
in `microcode_phase7_scalar_sources.json`. The independent active fixture is
`microcode_phase7_shift.json`. Generated artifacts remain source-derived.

`COUNT_LOW -> TMP1` snapshots the architectural count register's low byte.
`SHIFT DECODED TMP0 TMP1 -> TMP2 FLAGS_DECODED` requests an arithmetic result,
flag candidate/mask and write disposition. Valid protocols require ModR/M, then
constant/CL/immediate count, operand acquisition of matching width, SHIFT,
conditional result disposal, COMMIT_FLAGS and END. Incomplete or mismatched
protocols fail compilation. The executor waits for the arithmetic service;
it contains no x86 opcode decoder or timing delay sequence.

A zero count reads/checks its operand but suppresses data and FLAGS writes.
Nonzero shift computation proceeds in genuine elementary steps and honors
pause, response backpressure and cancellation. Undefined flags have the
explicit policy documented in `docs/PHASE7_SHIFT_FLAGS.md`. This is not an
Accurate timing profile. The isolated older I/O prototype must be rebased from
its human-readable sources before it can use the current control encoding.

## Verified prior format 9 data-transfer extension

Format 9 adds READ_EA (64), WRITE_REG8_TMP1 (65), WRITE_REG16_TMP1 (66),
READ_TARGET16_TMP1 (67), MOVE_SOURCE16_TMP1 (68), SET_ADDRESS_TMP1 (69) and
ADD_BASE_TMP0_TMP1 (70). The image now has 57 entries/282 words with nine-bit
addresses and seven-bit controls. The prior 235 words/entry addresses are
unchanged. Frozen format-8 sources and an independent literal format-9 fixture
check both old and new encodings.

Nine complete typed protocols provide LEA, byte/word RM exchange, AX/register
exchange, four direct-offset MOV forms and XLAT. Address setup precedes memory
access; both exchanged values are acquired before disposal. The compiler
rejects missing source/address acquisition and incomplete final writeback.
The executor consumes typed operations and decoded selectors without decoding
x86 opcodes. Source maps remain available; this defines no historical delay.

## Verified prior format 10 unary and decoded dispatch extension

Controls 71 DISPATCH_DECODED, 72 CONST_ZERO_TMP1 and 73 CONST_ONES_TMP1 extend
the image to 65 entries/328 words with nine-bit addresses and seven-bit controls.
All prior 282 words/entry addresses are unchanged. Frozen format-9 sources and
a new independent literal appendix specify historical and current encodings.
The parser handles multi-digit versions; canonical reconstruction recognizes
terminal dispatch and standalone memory INC/DEC using older controls.

DISPATCH DECODED requires exactly one preceding DECODE_MODRM and terminates its
entry. The generic sequencer follows a decoded symbolic target without macro
retirement or state reset. Target entries reuse an explicitly rearmed cached
operand context without another byte acquisition. Six typed unary protocols
require RM read, constant, ALU result, matching-width disposition, FLAGS commit
and END. Malformed or incomplete protocols fail compilation. No operation or
branch is a historical timing delay.

## Active format 11 decimal and radix adjustments

ADJUST (74) requests the captured arithmetic service; CHECK_ARITHMETIC (75)
serializes a pending #DE before normal END. The direct and immediate-radix
programs each require complete acquisition, computation, result disposition,
FLAGS commit and fault check. AAM radix zero suppresses AX and commits the
physical fault FLAGS policy before the existing event owner captures the frame.
The image has 67 entries/342 words with nine address and seven control bits;
all prior 328 words and entry addresses remain unchanged. Frozen format-10
sources and the independent format-11 literal fixture check both contracts.
No microinstruction represents an idle delay or duplicates opcode decoding.
See docs/PHASE7_DECIMAL_ADJUST.md for arithmetic, exception and lifetime rules.

## Active format 12 segment transfers

READ_SEG16_TMP0 (76) and WRITE_SEG16_TMP0 (77) transfer a decoded architectural
selector through the existing temporary and sole segment/cache owner. The
source index comes from captured opcode/ModR/M metadata, independently of EA
segment selection. The four programs are MOV_RM16_SEG, MOV_SEG_RM16, PUSH_SEG
and POP_SEG. Source completion precedes cache write; POP commits old-stack
SP before loading the new selector. The generated image has 71 entries and
356 words; all 342 previous words are preserved. The compiler rejects incomplete
segment transfer protocols. SS inhibition belongs to the event owner, not to
microcode delays. See PHASE7_SEGMENT_TRANSFER.md and D-033.

## Active format 13 stack/frame and bounds programs

Five explicit programs express PUSHA, POPA, ENTER, LEAVE and BOUND. Generic
register transfers, auxiliary/allocation temporaries and a five-bit counter
support the frame loop; generated instruction-local branch targets carry an
explicit valid bit. The existing microsequencer owns and validates branches.
The image has 76 entries/433 words, nine address bits and seven control bits;
all 356 prior words and entry addresses are preserved. ENTER uses a transient
stack cursor and per-transfer checks: a fault preserves original architectural
SP/BP while retaining accepted memory writes. BOUND checks both modular word
starts and permits the physically observed FFFE-to-0000 even wrap. See D-034
and PHASE7_STACK_FRAME.md for sources and independent literal contracts.

## Active format 14 far pointer and context transfers

CHECK_PUSH2 (113) and CHECK_POP2 (114) validate the full four-byte return frame;
ADD_ALLOCATION_SP (115) applies RETF's unsigned immediate allocation. Seven
complete source protocols express LDS/LES, direct/memory far CALL and JMP, and
RETF with or without allocation. Both words precede pointer installation, and
CALL acquires a memory pointer before creating its return link. Context commit
uses the existing CS:IP owner and flush path. FLAGS and NMI blocking are unchanged.
The image has 83 entries/492 words, nine-bit addresses and seven-bit controls.
All 433 prior words, entries and frame-loop destinations remain stable. Frozen
format-13 sources and the independent literal format-14 fixture prevent silent
encoding or protocol drift. The separate arithmetic prototype must rebase its
human-readable source before integration because its tentative controls conflict.
See PHASE7_FAR_TRANSFERS.md for physical evidence and precise fault/lifecycle rules.

## Active format 15 integer arithmetic programs

Controls 116..120 describe byte/word implicit multiplication/division, immediate
signed multiplication and low/high result disposal. Four complete protocols
append 29 words to the delivered 492-word far image. The current image has
87 entries, 521 words, ten-bit addresses and seven-bit controls. Every previous
entry, control value and loop destination remains unchanged. Frozen format-14
sources and an independent literal format-15 fixture protect that boundary.
The arithmetic service captures operands, honors pause/cancel and produces one
response; microcode disposes results and FLAGS before publishing a divide
exception. The BIU owns operand access. No historical timing claim is made.
See docs/PHASE7_IDIV_COMPATIBILITY.md for the negative byte-overflow rule.

## String integration after arithmetic - format 16

The arithmetic format-15 image remains a frozen 521-word contract. Five string
protocols append 43 words and controls 121..130. The new active image has 92
entries / 564 words / ten-bit addresses / eight-bit controls. Its human source
is zzzzzzzzzzzz_strings.mc; generated artifacts must be regenerated normally.

## Current ordered integration candidate - 2026-09-09

This isolated candidate contains all 307 required opcode files but has not been
validated as a complete Phase 7 delivery. It preserves the arithmetic format-15
source and independent literal, followed by the string format-16 source and
literal. I/O is appended in format 17: 100 entries, 612 words, ten address and
eight control bits. Arithmetic controls remain 116..120, strings 121..130 and
I/O occupies 131..135. All generated artifacts come from human-readable source.

The functional RTL matches the separately tested complete candidate, whose
full regression passed and whose strict physical run failed preparation of E7.
Those older results do not establish this newly ordered image's execution.
The new image passed 254 ordinary tests, 88 compiler tests, independent active
and frozen literal/round-trip audits, lint and both-simulator decoder checks.
Fresh affected instruction tests, physical coverage, mutation audits and complete
regression are recorded separately as they actually finish.

The required E7 record c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e is still not revoked
upstream. Its missing captured write strobe/data are not reconstructed from AX.
No original expected values, captures or revocation policy have been changed.
The original Phase 6 D-026 evidence questions remain open. New REP event evidence
and independent review remain pending; no new waiver or Phase 8 work is claimed.

See PHASE7_REP_EVENT_EVIDENCE.md and PHASE7_IO_CAPTURE_REVIEW.md for evidence
limitations. Complete Phase 7 remains incomplete; this directory is not a
verified Git delivery.

## PCAT register execution extension — format 22 (2026-09-22)

Controls 173..180 add the byte/word and both-direction variants of
`DECODE_ALU_*` and `DECODE_MOV_*`. Register-direct ModR/M captures both
operands together, then executes and retires with an atomic architectural
commit. Memory operands continue through the original microcode body. The
compiler requires that body to match the optimized direction and width.

This downstream image preserves `CARRY_FILL8=171` and `LOADALL=172`; their
upstream numbering differs. Always regenerate package and ROM together with
this compiler. Exactly eight existing ROM words change; all 122 entries,
labels, branch targets and the 723-word layout remain fixed. The independent
contract is `tests/fixtures/microcode_register_execution.json`.

The sequencer accepts `operation_retire` only alongside `operation_done`.
Capture and execution are useful work, not historical timing states. The
two-clock execution interval excludes opcode dispatch, retirement boundaries
and instruction-byte starvation. See the downstream integration receipt in
`docs/optimization/REGISTER_EXECUTION_50MHZ.md` at the PCAT repository root.

## Immediate execution extension — format 23

Controls 181..189 add `FETCH_ALU_DST16_IMM16`, `FETCH_ALU_DST8_IMM8`,
`FETCH_ALU_RM16_IMM16`, `FETCH_ALU_RM16_IMM8S`, `FETCH_ALU_RM8_IMM8`,
`FETCH_MOV_DST16_IMM16`, `FETCH_MOV_DST8_IMM8`, `FETCH_MOV_RM16_IMM16`
and `FETCH_MOV_RM8_IMM8`. They acquire one or two immediate bytes under the
existing queue handshake. `IMM8S` sign-extends its byte to a word.

For a register destination, the last accepted immediate byte captures the
source constant and original destination; the following enabled clock commits
and retires through the shared format-22 execution stage. CMP/TEST suppress
the GPR write, ALU operations use the existing decoded FLAGS/undefined masks,
and MOV preserves FLAGS. No following opcode byte is consumed while commit
is pending. Start, cancel and reset clear both partial and completed capture.

RM controls follow a complete `DECODE_MODRM`. Memory destinations acquire the
immediate into the same temporary and fall through at the same edge as before;
they retain the original protection, operand service, result and FLAGS sequence.
The compiler requires the exact complete width/destination/memory protocol.
Accumulator/register-immediate entries retain their historical tail in the
image for stable symbols; their new first control retires before that tail.

Exactly nine words change relative to format 22. All 122 entries, labels,
branch targets and the 723-word layout remain fixed; address/control widths
remain ten/eight bits. The frozen format-22 contract remains independently
executable, and a separate format-23 fixture specifies the literal delta.

See [the immediate execution receipt](../../docs/optimization/IMMEDIATE_EXECUTION_50MHZ.md).
