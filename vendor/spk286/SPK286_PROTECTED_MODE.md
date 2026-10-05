# SPK286 — Intel 80286 Protected-Mode Specification

**Document:** `SPK286_PROTECTED_MODE.md`
**Version:** 1.0 planning baseline
**Status:** Normative implementation specification for the future Protected-Mode milestones
**Owner:** SPK286 CPU project
**Target:** Intel 80286-compatible protected mode without paging

This document defines the architectural, microarchitectural, verification and
integration requirements for adding 80286 Protected Mode to SPK286. It is an
implementation contract, not evidence that Protected Mode is already present in
the RTL.

The document deliberately describes the 80286 rather than a generic x86
protected mode. In particular, it must not introduce 80386 control registers,
page translation, 32-bit descriptors, 32-bit operands, 32-bit addressing or
386-style mode-exit semantics.

---

## 1. Purpose and completion rule

Protected Mode is a required long-term SPK286 capability. It shall be added as
an extension of the existing Real-Mode CPU, not as a second execution engine.

The implementation is complete only when all of the following are true:

- the visible architectural state and hidden segment state are defined for both
  modes;
- descriptor-table instructions, selector loads, privilege checks, gates,
  protected-mode interrupts and task switching have a single documented owner;
- faults are raised before side effects that the real 80286 suppresses;
- real-mode behaviour remains unchanged by the addition;
- no paging or other 80386-only behaviour is present;
- directed protected-mode tests pass in both supported simulators;
- the complete protected-mode test suite is reproducible from a clean checkout;
- all deliberate limitations and unresolved hardware questions are recorded;
- the native CPU boundary remains consumable by a downstream PC/AT project.

Booting a protected-mode operating system is useful integration evidence but is
not, by itself, a definition of correctness.

---

## 2. Authority and source hierarchy

When sources disagree, apply the repository-wide hierarchy in
`SPK286_SPEC.md`:

1. Intel 80286 programmer and hardware reference manuals;
2. reproducible physical 80286 evidence, including the documented stepping;
3. pinned executable 80286 test corpora;
4. independent reference implementations used only as corroboration;
5. project policy and implementation convenience.

The following references are the initial authority set:

- Intel **iAPX 286 Programmer's Reference Manual**, 210498-003 (1985),
  especially the protected-mode, system-instruction and exception chapters;
- Intel **80286 Hardware Reference Manual**, 210760-002 (1987), especially
  interrupt priority, bus ownership, reset and shutdown behaviour;
- the pinned `SingleStepTests/80286` corpus, when protected-mode cases become
  available;
- `SPK286_SPEC.md`, `SPK286_REALMODE_MVP.md`, `SPK286_TIMING_MODEL.md` and
  `SPK286_MICROCODE_FORMAT.md`;
- `docs/STATE_INTERFACE.md`, `docs/BUS_INTERFACE.md`,
  `docs/INTERRUPTS_EXCEPTIONS.md` and `docs/VERIFICATION.md`.

Reference cores such as 86Box, Bochs, ao486 or z486 can expose useful hypotheses
and test stimuli. They do not override Intel documentation or physical evidence.
No source code from a reference core is to be copied into SPK286 without an
independent licensing and design decision.

---

## 3. Scope boundary

### 3.1 Included in SPK286

SPK286 owns all CPU-visible Protected-Mode behaviour:

- the Machine Status Word protected-mode state;
- GDTR, IDTR, LDTR and TR visible and hidden state;
- descriptor fetch, decode and validation;
- hidden descriptor caches for CS, DS, ES and SS;
- selector and privilege calculations;
- protected-mode segment reloads and effective-address checks;
- system instructions and their faults;
- interrupt, trap, call and task gates;
- protected-mode exception entry and return;
- privilege-level stack changes;
- 80286 task-state switching;
- protected-mode bus requests made by the CPU;
- READY, HOLD/HLDA, LOCK, INTR, NMI and INTA interactions required by those
  operations;
- timing-policy metadata, while keeping historical timing separate from
  functional semantics;
- CPU-only tests, traces and synthesis checks.

### 3.2 Excluded from SPK286

The following remain downstream machine responsibilities:

- GDT/IDT contents supplied by firmware or an operating system;
- RAM and ROM devices;
- PIC, PIT, DMA, 8042, RTC/CMOS and ISA devices;
- PC/AT memory-map and chipset glue;
- VGA/EGA, audio, storage and BIOS packaging;
- MiSTer framework and HPS/OSD integration;
- paging, virtual memory and 80386 control registers.

The protected-mode CPU shall issue ordinary memory and I/O transactions through
the existing native CPU bus boundary. The downstream system decides what device
responds to those transactions.

---

## 4. Architectural state

### 4.1 Machine Status Word

SPK286 shall model the 16-bit 80286 Machine Status Word (MSW) as architectural
state. At minimum it contains:

| Bit | Name | Required behaviour |
|---:|---|---|
| 0 | PE | Protected-Mode enable. `0` selects Real Mode; `1` selects Protected Mode. |
| 1 | MP | Preserve and expose according to the 80286 definition. |
| 2 | EM | Preserve and expose according to the 80286 definition. |
| 3 | TS | Task-switched state; set by task switching and cleared only by the 80286-supported instruction. |
| 4–15 | reserved/implementation-defined | Preserve only where the authoritative 80286 source requires it; do not import 386 CR0 semantics. |

`SMSW` reads the architecturally visible MSW. `LMSW` writes only the fields
permitted by the 80286. In particular, the implementation must not silently
provide `MOV CR0` or a 386-style PE-clear path.

The exact reserved-bit read/write policy shall be captured in a directed test
before the system-instruction family is declared complete.

### 4.2 Descriptor-table registers

SPK286 shall hold the following visible registers:

| Register | Width | Meaning |
|---|---:|---|
| GDTR | 16-bit limit + 24-bit base | Global Descriptor Table location. |
| IDTR | 16-bit limit + 24-bit base | Interrupt Descriptor Table location. |
| LDTR | 16-bit selector + hidden descriptor cache | Local Descriptor Table selector and resolved descriptor. |
| TR | 16-bit selector + hidden TSS cache | Current task selector and resolved task-state segment. |

The internal representation may use wider fields for arithmetic and validity
metadata, but externally observable values must be masked to the 80286 widths.
There is no paging root, page-directory base or 32-bit control register.

### 4.3 Segment registers and hidden caches

CS, DS, ES and SS each have:

- a visible 16-bit selector;
- a hidden descriptor cache containing at least base, limit, type/access rights,
  privilege metadata, present state, table origin and validity;
- mode information identifying Real-Mode or Protected-Mode interpretation;
- enough state to distinguish a valid loaded cache from a selector value that
  has not yet been successfully loaded.

The visible selector and the hidden cache are committed together on a successful
reload. A failed reload must not install a new selector, cache or privilege
state, except for side effects explicitly required by the 80286 fault model.

The hidden cache is the source used by effective-address formation. The selector
alone must never be used as a substitute for a protected-mode base, limit or
access-rights check.

### 4.4 Existing state ownership

Protected Mode extends, but does not replace, the ownership rules in
`docs/STATE_INTERFACE.md`:

- the architectural register file owns visible GPRs, segment selectors, IP and
  FLAGS;
- the segment service owns hidden segment caches and reload candidates;
- the descriptor service owns transient descriptor bytes and validation results;
- the event service owns entry/return candidates and interruptibility state;
- the BIU owns physical bus-cycle sequencing and response retention;
- microcode requests these services and does not become a second architectural
  storage block.

---

## 5. Descriptor model

### 5.1 Descriptor size and address formation

80286 descriptors are 8 bytes. A descriptor-table linear/physical address is
formed as:

```text
descriptor_address = table_base + (selector.index * 8)
```

The addition is performed on the 24-bit physical address path used by SPK286.
The table limit is checked before the descriptor bytes are requested:

```text
selector.index * 8 + 7 <= table_limit
```

The check shall use at least 20 bits internally so that overflow cannot wrap
and turn an invalid descriptor into a valid low-address access.

Every descriptor fetch is an ordinary CPU memory read through the BIU. The
descriptor service may issue one or more physical cycles depending on alignment
and bus width; it must retain ownership and response data until the complete
descriptor has been assembled.

### 5.2 Descriptor classes

The implementation shall distinguish these descriptor classes:

- code segment;
- data segment;
- expand-down data segment;
- available 80286 TSS;
- busy 80286 TSS;
- 80286 call gate;
- 80286 task gate;
- 80286 interrupt gate;
- 80286 trap gate;
- LDT descriptor;
- invalid or reserved descriptor forms.

The descriptor decoder shall expose a typed result rather than making later
microcode infer type from raw access bits. Reserved encodings must remain
explicitly invalid; an implementation must not reinterpret them as 386 system
descriptors.

### 5.3 Segment descriptors

For a loaded code or data segment, the cache shall retain:

- 24-bit base;
- 16-bit limit;
- segment type;
- readable/writable permission;
- accessed state policy;
- conforming or non-conforming code state;
- expand-down state;
- descriptor privilege level (DPL);
- present state;
- descriptor-table origin;
- selector and RPL used to load it.

The 80286 descriptor layout and reserved fields shall be implemented exactly as
specified by the Intel 80286 manual. The implementation must not use the 386
granularity, default-size or long-mode bits. Any field that is physically
reserved on the 286 is validated and preserved only according to documented
286 behaviour.

### 5.4 System descriptors and gates

System descriptors use the same 8-byte table slot but have class-specific
interpretation. The descriptor service shall decode and validate the class
before fetching any second-level object such as a TSS or gate target.

Gate descriptors shall retain:

- target selector;
- target offset;
- gate type;
- gate DPL and present state;
- parameter-word count for a call gate where applicable;
- reserved-field validity.

Gate target selectors are validated against the selected GDT/LDT at the time of
transfer. A gate target is not a flat physical address and must not bypass
segment checks.

---

## 6. Selectors and privilege

### 6.1 Selector fields

A selector is a 16-bit value:

```text
15                         3 2  1 0
+---------------------------+----+--+
|           index           | TI |RPL|
+---------------------------+----+--+
```

- `index` selects an 8-byte descriptor;
- `TI=0` selects the GDT;
- `TI=1` selects the current LDT;
- `RPL` is the requestor privilege level.

The null selector (`index=0`, with either table indicator and RPL) is not a
loadable code or data segment. Loading it into DS or ES produces the documented
286 result; loading it into CS or SS faults.

### 6.2 Privilege values

The implementation shall carry these values independently:

- CPL: current privilege level, derived from the active CS;
- DPL: descriptor privilege level;
- RPL: selector requestor privilege level;
- effective privilege, `max(CPL, RPL)`, where the operation requires it.

Privilege checks shall be performed on captured candidates before committing a
new selector, hidden cache, IP, SP, FLAGS or task state.

### 6.3 Data-segment loads and access

For ordinary data-segment loads, the effective privilege must satisfy the
80286 rule for the descriptor class. The implementation shall test:

- descriptor present state;
- data/code readability rules;
- writability for SS and write operations;
- `max(CPL,RPL)` against DPL;
- null-selector restrictions;
- expand-down lower/upper bounds;
- selector table-limit validity.

A readable code segment may be used as a data source only when its 80286 access
rights permit it. A code segment is never implicitly writable.

### 6.4 CS loads and control transfers

CS can be loaded only by the architecturally permitted far control-transfer,
interrupt, gate, task-switch or return operations. A direct data-segment reload
must not install CS.

For a non-conforming code segment, the target privilege and gate rules shall be
checked before installing CS. For a conforming code segment, CPL does not change
as a result of the transfer, but the target descriptor's conforming rules still
apply.

The far-transfer service shall produce one typed result:

```text
SUCCESS(new_cs_cache, new_ip, new_cpl)
FAULT(vector, error_code, fault_context)
```

It must not expose partially installed CS/cache state to the next instruction.

### 6.5 SS loads and stack privilege

SS loads are more restrictive than DS/ES loads. A successful protected-mode SS
load shall require the descriptor and selector relationships specified by the
80286, including:

- writable data-segment type;
- present state;
- DPL equal to the incoming CPL;
- selector RPL equal to the incoming CPL;
- valid limit and base for the current stack operation.

An SS fault is distinct from a general protection fault and must use the 80286
stack-fault context. The visible SS, hidden SS cache and SP must remain coherent
when the load succeeds and unchanged when it fails.

---

## 7. Segment limits and effective addresses

### 7.1 Offset checks

Every protected-mode memory reference shall be checked against the active
segment cache before its first physical bus cycle. The check depends on:

- segment type;
- read or write direction;
- operand width;
- starting offset;
- expand-down state;
- 16-bit offset wrap rules.

For an ordinary expand-up segment, a byte at offset `O` is valid when `O <= L`.
A word access requires that the complete word satisfies the 80286 limit rule;
it must not issue the first physical half and discover the fault afterward.

For an expand-down segment, the lower boundary and maximum offset are selected
according to the 80286 descriptor definition. The implementation must not use
the 386 D/B bit to select a 32-bit maximum; SPK286 has 16-bit offsets.

### 7.2 Code fetch limits

Instruction prefetch uses the active CS cache. A fetch that would cross the
code-segment limit is not silently wrapped. The prefetch unit reports a typed
segment-limit fault to the event owner when a required byte cannot be fetched.

Speculative bytes that are not required by the current architectural boundary
must not create a guest-visible fault prematurely.

### 7.3 Stack limits

Stack reads, writes, pushes, pops, frame construction and privilege-level stack
changes use the SS cache and the stack-specific limit rules. A multi-byte stack
operation must validate the complete architectural word before issuing its first
physical half. If the 80286 permits a partial physical effect for a particular
faulting operation, that behaviour must be called out in a source-backed test;
the generic cancellation path must not invent a rollback.

### 7.4 I/O privilege

The 80286 I/O privilege rules shall be applied at the CPU boundary defined by
the target architecture. Do not import the 80386 I/O-permission bitmap. If the
80286 rule cannot be resolved from the authoritative source set, the operation
must remain an explicit pending item rather than being treated as unrestricted
I/O by accident.

---

## 8. Protected-mode system instructions

The decoder shall recognize the 80286 protected-mode instruction families and
dispatch them through the existing project-owned microcode path. It shall not
add a parallel ad-hoc system-instruction executor.

The initial required family is:

| Family | Architectural purpose |
|---|---|
| `SGDT` / `SIDT` | Store GDTR/IDTR limit and base to memory. |
| `LGDT` / `LIDT` | Load GDTR/IDTR from memory. |
| `SMSW` / `LMSW` | Read/write the 80286 Machine Status Word. |
| `SLDT` / `LLDT` | Read/load the current LDT selector and cache. |
| `STR` / `LTR` | Read/load the current task selector and cache. |
| `VERR` / `VERW` | Validate readability or writability of a selector and update FLAGS as specified. |
| `LAR` / `LSL` | Read access rights or limit of a valid selector where permitted. |
| `ARPL` | Adjust selector RPL and report the comparison through FLAGS. |
| `CLTS` | Clear the task-switched state if confirmed by the 80286 authority set. |

The exact opcode, ModR/M, privilege and flag semantics for each family shall be
listed in the instruction matrix before RTL implementation. Unsupported 386-only
forms such as `MOV CRx`, `MOV DRx`, `INVLPG` and paging controls shall decode as
the correct 80286 invalid/undefined instruction behaviour, not as harmless NOPs.

### 8.1 Descriptor-table loads

`LGDT` and `LIDT` shall:

1. decode a 16-bit limit and 24-bit base operand;
2. perform the complete memory read through the BIU;
3. commit the table register only after the read completes;
4. preserve the previous register if the operand access faults;
5. invalidate no segment cache unless the 80286 architecture explicitly
   requires it.

`SGDT` and `SIDT` shall snapshot the visible table-register fields and write the
architectural memory image through the normal data-write path.

### 8.2 LDT and task-register loads

`LLDT` and `LTR` shall validate the selector and descriptor before committing
the visible selector and hidden cache. `LTR` shall perform the 80286 busy-state
transition required for the loaded TSS descriptor. `LLDT` shall require an LDT
descriptor and shall make subsequent `TI=1` selector resolution use the new LDT.

The update of a descriptor's accessed/busy state is an architectural memory
write. It must be represented in the bus trace and must obey READY, HOLD and
LOCK ownership rules.

### 8.3 Selector validation and inspection

`VERR`, `VERW`, `LAR` and `LSL` shall:

- inspect a selector without loading its cache;
- apply the correct CPL/RPL/DPL/type/present checks;
- leave destination registers unchanged when the operation fails, unless the
  80286 explicitly defines another result;
- update only the documented FLAGS bits;
- distinguish a null selector from an out-of-limit or wrong-type selector.

### 8.4 LMSW and mode entry

`LMSW` is the architectural entry point from Real Mode to Protected Mode. The
implementation shall model the 80286 PE transition and its serialization rules.
It shall not provide a 386 `MOV CR0` substitute or allow software to clear PE
through a later 386 mechanism.

The required software sequence is represented by the architectural contract,
not hard-coded into the CPU:

```text
load GDT/IDT
load any required LDT/TSS state
set PE with LMSW
perform a far control transfer to load protected CS and flush prefetch
continue in Protected Mode
```

The exact visibility of PE relative to the next instruction and queue flush
must be verified with Intel documentation and a directed transition test.

---

## 9. Interrupt and exception architecture

### 9.1 Event ownership

Protected-mode events extend `docs/INTERRUPTS_EXCEPTIONS.md`. The event owner
shall arbitrate among:

- instruction faults;
- debug/single-step events;
- NMI;
- maskable INTR;
- software `INT`, `INT3` and `INTO`;
- protected-mode gate and task-switch faults;
- nested faults during exception entry.

Priority and eligibility are architectural state, not an incidental consequence
of microcode layout. A pause, READY wait or held bus response must not duplicate
an event or lose a pending event.

### 9.2 IDT lookup

For vector `V`, the IDT entry address is:

```text
idt_entry = IDTR.base + (V * 8)
```

Before the entry is read, the implementation shall verify that the complete
8-byte entry is within `IDTR.limit`. A failed bounds check raises the
80286-protected-mode fault required for an invalid IDT reference; it must not
wrap into another table entry.

The entry is then decoded as an interrupt gate, trap gate or task gate. Reserved
or not-present forms fault before installing target state.

### 9.3 Interrupt and trap gates

For an interrupt or trap gate, the CPU shall:

1. capture the event's architectural return context;
2. validate the gate, target selector and target code descriptor;
3. determine whether a privilege-level stack change is required;
4. validate and load the new SS:SP when required;
5. push the required FLAGS, CS and IP values on the new stack;
6. clear or preserve IF/TF according to the gate type and 80286 rules;
7. install target CS/cache and IP coherently;
8. flush the prefetch queue;
9. retire/complete the event exactly once.

No target instruction may execute before all validation and required frame writes
complete. If entry faults, the original architectural context remains governed
by the 80286 nested-fault rules, not by a generic redirect/cancel operation.

### 9.4 Software and external event privilege

Software interrupts must apply the IDT-entry DPL rule before entry. Hardware
INTR/NMI acceptance uses the external-event rules and must not incorrectly reuse
the software `INT` DPL check. The event source, vector and error-code policy are
retained in the event context for debugging and verification.

### 9.5 Exception frames and error codes

Protected-mode faults that push an error code shall use the 80286-defined error
code width and contents. The implementation shall classify each vector as:

- no error code;
- selector/error-code word;
- nested-entry or shutdown-sensitive fault.

The matrix must specify saved IP semantics (faulting or following instruction),
FLAGS image, CS/SS state and whether the faulting instruction retires. No 386
error-code convention may be imported without explicit 80286 evidence.

### 9.6 IRET in Protected Mode

`IRET` shall validate and restore the saved IP, CS and FLAGS. For a return to a
less privileged level it shall additionally validate and restore SS:SP and the
required data-segment visibility. Candidate state is held until every required
word and descriptor check succeeds.

The operation is not a collection of independent visible writes. A successful
return commits the new context coherently and flushes the queue. A failing
return follows the 80286 fault path and leaves no stale protected-mode cache
installed.

---

## 10. Gates and far control transfer

### 10.1 Call gates

An inter-level call gate may change CPL and stack. The implementation shall:

- validate the gate DPL against the caller's CPL and selector RPL;
- validate the target code descriptor;
- locate the new privilege stack in the current TSS;
- validate the new SS:SP;
- copy the gate-specified parameter words in the 80286-defined order;
- push the old SS:SP and return CS:IP;
- install the target context only after all required reads and checks succeed.

Same-level call gates shall not perform a privilege stack switch. A direct far
call and a call-gate transfer are distinct paths even when they reach the same
code descriptor.

### 10.2 Return from a call gate

The protected-mode far return path shall use the saved privilege context and
perform the 80286 parameter-word discard rules. It must validate the restored
CS and, when returning outward, SS:SP before committing visible state.

### 10.3 Task gates

A task gate names a TSS descriptor rather than a code descriptor. The event or
far-control path validates the task gate and then enters the task-switch service.
The gate's DPL controls software access; hardware event entry follows its own
privilege rules.

### 10.4 Far jumps and returns

Far jumps may target a code segment, conforming code segment, call gate or task
gate according to the 80286 descriptor rules. A far jump never performs a
return-stack cleanup. `RETF` and `IRET` are separate operations with separate
validation and frame semantics.

---

## 11. Task State Segment and task switching

### 11.1 TSS contract

SPK286 shall model the 80286 TSS as a fixed-format memory object. The TSS service
shall provide named fields for at least:

- backlink;
- privilege-level stack pointers and selectors;
- task IP and FLAGS;
- general registers;
- segment selectors;
- LDT selector;
- reserved or implementation-defined fields required by the 80286 layout.

Field offsets and total size shall be recorded in an implementation table tied
to the Intel manual. The service must not use a 386 TSS layout or 32-bit fields.

### 11.2 Hardware task switch

A task switch may be requested by:

- a task gate;
- a far call to a TSS descriptor;
- a far jump to a TSS descriptor;
- an interrupt path using a task gate.

The task-switch service shall:

1. validate the new selector and TSS descriptor;
2. validate table limits and present/busy state;
3. save the outgoing task state in the current TSS;
4. update busy/link state as required;
5. load the incoming task state;
6. load and validate the incoming segment selectors/caches;
7. set the task-switched MSW state;
8. commit the new task context coherently;
9. flush the prefetch queue;
10. complete the transfer or raise the specified fault.

The implementation shall preserve the distinction between completed external
memory writes and uncommitted candidate architectural state. A fault during a
task switch must follow the documented 80286 partial-effect rules; it must not
be converted into a generic rollback.

### 11.3 Busy state and nested tasks

The TSS descriptor busy bit, backlink and nested-task state are architectural.
`IRET` from a nested task shall follow the 80286 task-return rules, including
busy-state updates and restoration of the previous task. A task gate must not
be treated as a call gate with a larger frame.

### 11.4 Task-switch locking and bus ownership

Descriptor busy-bit updates, TSS saves and TSS loads are ordered memory effects.
The BIU shall keep each accepted physical transaction stable until READY. HOLD
shall not split an indivisible architectural sequence identified by the 80286
bus contract. The functional implementation may initially use a serialized
task-switch service; historical cycle refinement belongs to the timing policy.

---

## 12. Mode transitions and reset

### 12.1 Real Mode to Protected Mode

The transition is initiated by setting PE through the 80286 MSW mechanism. The
implementation shall preserve the currently loaded real-mode segment caches
until each segment is explicitly reloaded under Protected Mode.

A far control transfer is required to load a protected CS and establish the
protected instruction stream. The prefetch queue must be flushed at the point
defined by the 80286 transition semantics.

### 12.2 Protected Mode operation

Once PE is set, all segment loads, memory references, instruction fetches,
interrupt entries and returns use protected-mode validation. A selector value
that happens to equal a real-mode paragraph value has no real-mode meaning.

### 12.3 Leaving Protected Mode

The 80286 does not provide the 80386 `MOV CR0` PE-clear path. SPK286 shall not
implement one. Any supported protected-to-real transition must follow the
documented 80286 reset or processor-specific mechanism and must be explicitly
evidenced before implementation.

The design shall reserve no hidden “magic” debug write that clears PE in normal
operation. Testbench setup may initialize architectural state only through the
documented reset/setup contract.

### 12.4 Reset

Reset shall restore the 80286 reset mode and reset descriptor-table/system state
as specified by the existing SPK286 reset contract. It shall clear transient
descriptor fetches, gate candidates, task-switch progress, pending protected
events, queue contents and bus ownership. The first post-reset fetch remains the
existing 80286 reset-vector transaction.

---

## 13. Fault atomicity and partial effects

Protected Mode makes operation ordering observable. Every multi-step operation
shall classify effects as one of:

| Class | Meaning |
|---|---|
| Candidate | Internal value that is not architecturally visible and may be discarded on fault. |
| Accepted bus effect | A completed external read/write that cannot be undone by a debug cancel. |
| Architectural commit | Visible register/cache/MSW/task state that becomes guest state. |
| Fault entry effect | Frame words or descriptor updates required by the 80286 exception path. |

The following rules are mandatory:

- descriptor and gate checks precede target CS/SS/cache installation;
- a segment-limit fault precedes the first physical byte of a protected word
  access;
- selector loads commit visible selector and hidden cache coherently;
- a completed descriptor busy/accessed-bit write is never silently rolled back;
- a queue flush occurs only after the new code context is committed;
- a faulting instruction does not retire;
- an event entry does not generate a second retirement pulse;
- pause and READY waits freeze candidate state without duplicating commits;
- redirect/cancel drains accepted physical transactions but does not fabricate
  rollback of external writes.

These rules extend the commit matrix in `docs/INTERRUPTS_EXCEPTIONS.md` and
shall be represented by explicit state-machine assertions where practical.

---

## 14. Microarchitecture and service decomposition

### 14.1 Decoder

The decoder recognizes the 80286 opcode and ModR/M form, resolves operand
metadata and dispatches a symbolic microprogram. It does not fetch descriptors,
perform privilege checks or own visible architectural state.

### 14.2 Descriptor service

The descriptor service owns:

- selector decomposition;
- GDT/LDT table choice;
- table-limit checks;
- descriptor byte acquisition;
- descriptor type and access-rights decode;
- privilege predicates;
- candidate hidden-cache construction.

It exposes typed results to microcode and the event owner. Raw descriptor bytes
must not be decoded independently by several instruction handlers.

### 14.3 Segment service

The segment service owns successful cache installation, mode-dependent limit
checks and effective-address classification. It provides separate APIs for:

- code fetch;
- data read;
- data write;
- stack read/write;
- far target validation;
- selector reload.

The operation type is part of the request so that a readable code segment cannot
be accidentally accepted for a stack write.

### 14.4 Event service

The event service owns protected-mode entry, exception selection, gate dispatch,
frame construction, IRET candidates and nested-fault policy. It reuses the
existing physical stack/BIU services rather than issuing untracked bus writes.

### 14.5 Task service

The task service owns TSS field mapping, outgoing saves, incoming loads, busy/link
state and task-return progress. It must be invoked by both gate and far-control
paths; there must not be a separate task-switch implementation for each opcode.

### 14.6 BIU and prefetch

The BIU remains the only owner of physical bus transactions. The prefetch unit
remains the only owner of instruction-stream queue storage and refill. Protected
mode may invalidate or redirect the queue, but it must not write queue entries
directly from descriptor or event microcode.

### 14.7 Timing separation

Functional descriptor sequencing is independent of the number of historical
cycles. Accurate/Fast/Max timing policy may annotate descriptor fetches, gate
entry and task-switch phases, but it may not remove READY, bus ownership,
required serialization or descriptor memory dependencies.

---

## 15. Native bus and observable transactions

The normalized contract in `docs/BUS_INTERFACE.md` remains the functional
baseline. Protected Mode adds transaction classes, not a second bus.

At minimum, the following activity must be observable in traces:

- GDT/LDT/IDT descriptor reads;
- TSS reads and writes;
- descriptor accessed/busy-bit writes where required;
- protected-mode stack frame writes and reads;
- interrupt-acknowledge cycles for external INTR;
- instruction fetches after a protected far transfer or event entry;
- queue flush and redirect markers in debug state.

Address, direction, byte enables, status and driven data remain stable while a
request waits for READY. HOLD/HLDA cannot steal ownership in the middle of an
accepted physical cycle. A higher-level architectural sequence may span multiple
cycles; its transient state must remain valid across pause and wait states.

LOCK policy shall be derived from the 80286 bus contract and the existing BIU
ownership rules. It must cover any descriptor/TSS read-modify-write sequence
that the hardware makes indivisible, without turning every protected-mode read
into an unconditional locked cycle.

---

## 16. Debug and observability requirements

The following debug information shall be available in simulation, either as
existing ports or trace-only state:

- PE and MSW fields;
- GDTR/IDTR base and limit;
- visible LDTR/TR selectors;
- decoded descriptor class, base, limit, DPL and present/type bits;
- current CPL, candidate RPL and effective privilege;
- descriptor-table source and index;
- protected-mode operation kind;
- pending exception vector and error code;
- gate type and target selector/offset;
- task-switch phase and current TSS selector;
- candidate versus committed CS/SS/DS/ES cache state;
- protected-mode queue flush/redirect reason;
- physical transaction identifier for descriptor, TSS and frame accesses.

Debug state must describe CPU operation, not become an alternate setup path for
hidden descriptors. Setup interfaces may initialize documented architectural
state for a test, but a protected-mode test must be able to exercise the normal
descriptor-loading path.

---

## 17. Verification plan

### 17.1 Required test layers

Protected Mode shall be developed through these layers:

1. pure selector and descriptor parser tests;
2. descriptor-table boundary and byte-assembly tests;
3. hidden-cache and segment-reload tests;
4. effective-address and segment-limit tests;
5. system-instruction tests;
6. privilege and gate predicate tests;
7. protected-mode exception/frame tests;
8. TSS and task-switch tests;
9. end-to-end transition tests;
10. dual-simulator CPU regression;
11. synthesis/lint checks;
12. external software and hardware integration evidence.

Every layer shall run without requiring PC/AT chipset logic.

### 17.2 Descriptor and selector corpus

The directed corpus shall cover:

- null, first and last valid descriptors;
- GDT/LDT selection;
- table-limit exact boundary and one-byte/one-descriptor overflow;
- every supported code/data/system descriptor class;
- present and not-present descriptors;
- all CPL/RPL/DPL relationships relevant to each operation;
- conforming and non-conforming code;
- readable code and writable data;
- expand-up and expand-down limits;
- invalid/reserved access encodings;
- descriptor base carries across the 64 KiB and 1 MiB boundaries;
- descriptor fetches stalled by READY and interrupted by reset.

### 17.3 Instruction tests

Each system instruction shall have tests for:

- legal register and memory operands;
- misaligned and odd physical addresses;
- READY wait and held response;
- table-limit and segment-limit faults;
- privilege violations;
- not-present descriptors;
- reserved encodings;
- unchanged destination state on failure;
- FLAGS effects;
- queue and retirement behaviour.

### 17.4 Protected-mode transition tests

The transition suite shall include at least:

- Real Mode setup of GDT/IDT followed by `LMSW` and a far jump;
- protected code and data reloads;
- a protected data read/write at a nonzero descriptor base;
- a code-limit and data-limit fault;
- a privilege-level call gate and return;
- interrupt and trap gates with distinct IF/TF behaviour;
- a privilege-level stack switch;
- a task-gate and direct TSS switch;
- nested task return through `IRET`;
- a protected-mode exception whose handler returns with `IRET`;
- a reset from Protected Mode and verification of reset state;
- an attempted unsupported 386 mode-exit sequence, which must not silently
  clear PE.

### 17.5 Fault-injection and mutation tests

The verification suite shall deliberately mutate:

- selector index bits;
- table limits;
- descriptor present/type bits;
- DPL/RPL/CPL relationships;
- gate target selectors;
- TSS busy/link state;
- operand bytes after acceptance;
- READY timing and response backpressure;
- event requests coincident with descriptor completion;
- HOLD requests during descriptor and frame transactions.

Each mutant must be rejected by a focused assertion or directed test. A test
that passes because the protected-mode path is accidentally bypassed is invalid.

### 17.6 External references

When protected-mode SingleStepTests become available, the ingestion and selection
rules in `SPK286_ENVIRONMENT.md` and `docs/SINGLESTEP_INTEGRATION.md` apply. Until
then, use Intel-derived directed tests and clearly labelled hardware/reference
evidence. Do not claim full corpus coverage from Real-Mode tests.

---

## 18. Implementation milestones

### PM0 — State and descriptor foundation

Deliver:

- MSW PE state;
- GDTR/IDTR/LDTR/TR storage;
- hidden cache representation;
- selector decomposition;
- descriptor parser and table-limit checks;
- unit tests independent of instruction execution.

Acceptance:

- all descriptor fields and reserved bits have an authority note;
- no 386-only fields exist in the architectural state;
- Real-Mode regression remains unchanged.

### PM1 — System instructions

Deliver:

- SGDT/SIDT/LGDT/LIDT;
- SMSW/LMSW;
- SLDT/LLDT;
- STR/LTR;
- VERR/VERW;
- LAR/LSL and ARPL where the authority set confirms the exact 80286 form;
- CLTS only after its 80286 semantics are pinned.

Acceptance:

- directed instruction tests pass with READY stalls and fault cases;
- table-register and cache commits are atomic;
- system writes are visible through the native bus.

### PM2 — Protected segment reloads and access checks

Deliver:

- protected CS/DS/ES/SS loads;
- code/data type checks;
- limit and expand-down checks;
- effective privilege calculation;
- protected instruction fetch;
- typed #GP/#NP/#SS/#TS faults.

Acceptance:

- all selector and privilege matrix tests pass;
- no invalid memory operation issues a physical cycle;
- Real-Mode segment behaviour remains clean.

### PM3 — Exceptions, gates and returns

Deliver:

- IDT lookup;
- interrupt/trap gates;
- software and external event privilege rules;
- protected exception frames;
- IRET to same and outer privilege levels;
- nested-fault/shutdown policy.

Acceptance:

- event priority and frame tests pass under pause and READY backpressure;
- target state is never installed before validation completes;
- queue redirects are exactly once.

### PM4 — Call gates and privilege stack switching

Deliver:

- same-level and inter-level call gates;
- TSS privilege-stack lookup;
- parameter-word copying;
- protected far returns.

Acceptance:

- gate and return matrix passes for all supported privilege relationships;
- partial physical effects are documented and tested.

### PM5 — Task state and task gates

Deliver:

- 80286 TSS field service;
- LTR and busy-state updates;
- direct TSS call/jump;
- task gates;
- nested tasks and IRET task return.

Acceptance:

- task-switch tests pass under memory wait, HOLD and reset scenarios;
- TSS layout is independently checked against the Intel source;
- no 386 TSS fields or paging state are used.

### PM6 — Protected-mode closure

Deliver:

- complete directed protected-mode suite;
- SingleStep protected-mode integration when available;
- independent review and evidence dossier;
- timing annotations separated from semantics;
- standalone release notes and downstream integration contract.

Acceptance:

- protected-mode failures are zero or explicitly classified with evidence;
- Real-Mode and Phase 8 regressions remain green;
- synthesis and both simulators agree;
- no unsupported 386 behaviour has entered the RTL.

---

## 19. Definition of Done

Protected Mode is ready for an SPK286 release candidate when:

- PE/MSW and all required descriptor-table state are implemented;
- descriptor parsing and hidden cache loading are complete;
- GDT/LDT/IDT selection and bounds checks are correct;
- CS/DS/ES/SS privilege and limit checks are complete;
- protected-mode system instructions are complete;
- interrupt/trap/call/task gates are implemented;
- protected-mode exceptions and error-code frames are correct;
- call-gate stack changes and TSS switching are correct;
- IRET and nested-task return are correct;
- no paging or 386-only mode control is present;
- all affected tests pass in Verilator and Icarus;
- lint, synthesis sanity and regression pass;
- bus traces show descriptor/TSS/frame transactions and stable READY waits;
- timing policy does not alter architectural results;
- documentation, sources, test identities and generated artifacts are
  reproducible;
- a standalone downstream consumer can instantiate the CPU without importing
  PC/AT machine logic into SPK286.

---

## 20. Deferred and explicitly unresolved items

The following are not silently solved by this document:

- undocumented LOADALL/Unreal Mode behaviour;
- stepping-specific protected-mode errata not supported by evidence;
- exact historical cycle counts for every descriptor and task-switch phase;
- 80287 protocol and numeric execution;
- 80386 extensions, paging and 32-bit execution;
- PC/AT chipset, BIOS and MiSTer integration;
- any physical behaviour contradicted by later authoritative 80286 evidence.

Each unresolved item must have a named issue, source status and impact on the
current milestone. “Works in an emulator” is not sufficient closure evidence.

---

## 21. Agent implementation rules

Agents implementing this specification shall:

1. inspect the active phase, handoff and current ownership documents first;
2. implement one milestone slice at a time;
3. add tests before or together with RTL;
4. keep descriptor, segment, event and task ownership explicit;
5. never hard-code a test selector, vector, address or expected state;
6. never weaken a test to accommodate incorrect RTL;
7. preserve Real-Mode behaviour and existing generated-microcode contracts;
8. keep physical bus sequencing in the BIU;
9. distinguish accepted bus effects from architectural commits;
10. document any ambiguity before choosing a compatibility policy;
11. run focused tests, lint, affected regression, dual-simulator checks and
    synthesis sanity before committing;
12. report exact commands, source identities and remaining evidence gaps.

Protected Mode is an architectural extension, not a reason to move chipset or
BIOS logic into this repository.

---

## 22. Initial implementation checklist

Before the first Protected-Mode RTL commit, the implementation task shall have:

- [ ] a pinned Intel source set and local source notes;
- [ ] a descriptor bit-layout table with reserved-field policy;
- [ ] a selector/privilege truth table;
- [ ] an exception/error-code matrix;
- [ ] a TSS field-offset table;
- [ ] a system-instruction opcode matrix;
- [ ] a state-ownership review for descriptor, segment, event and task services;
- [ ] a directed test plan for every PM milestone;
- [ ] a no-386-leakage review;
- [ ] a reproducible test command and clean-build location.

No broad Protected-Mode implementation should begin while these inputs are
missing or contradictory.

---

## 23. Final architectural rule

SPK286 Protected Mode shall make the same documented instruction sequence,
started from the same architectural state and memory image, observe the same
80286-visible results as a real Intel 80286. In Accurate mode, where evidence
exists, the CPU shall also expose the same dependency ordering and bus
transaction behaviour. Fast and Max modes may remove historical compatibility
delays, but may not change descriptor validation, privilege, fault, task, READY,
HOLD, LOCK or architectural commit semantics.
