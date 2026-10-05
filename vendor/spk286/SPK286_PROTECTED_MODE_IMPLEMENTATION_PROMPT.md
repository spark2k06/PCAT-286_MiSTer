# Prompt — SPK286 Protected-Mode Implementation

You are implementing Intel 80286 Protected Mode in the `SPK286` standalone CPU
repository.

Your task is to turn the normative requirements in
`SPK286_PROTECTED_MODE.md` into small, verified, reproducible RTL increments.
Do not treat this prompt as permission to skip evidence, weaken tests or expand
the project boundary.

---

## 1. Mission

Implement 80286 Protected Mode as an extension of the existing SPK286 Real-Mode
CPU. Preserve the current architecture, generated-microcode flow, BIU ownership,
prefetch ownership, event semantics and Real-Mode compatibility.

The final result must be a standalone synthesizable 80286 CPU core. It must not
become a PC/AT machine implementation.

The implementation is complete only when the Protected-Mode specification,
directed tests, simulator regression, synthesis checks and evidence report all
agree. A BIOS boot, a reference emulator result or a single passing program is
not sufficient closure evidence.

---

## 2. Read these files before changing anything

Read the complete contents of these files first:

1. `AGENTS.md`
2. `SPK286_SPEC.md`
3. `SPK286_REALMODE_MVP.md`
4. `SPK286_MICROCODE_FORMAT.md`
5. `SPK286_TIMING_MODEL.md`
6. `SPK286_PROTECTED_MODE.md`
7. `SPK286_ENVIRONMENT.md`
8. `docs/ARCHITECTURE.md`
9. `docs/STATE_INTERFACE.md`
10. `docs/BUS_INTERFACE.md`
11. `docs/INTERRUPTS_EXCEPTIONS.md`
12. `docs/INSTRUCTION_MATRIX.md`
13. `docs/DECISIONS.md`
14. `docs/VERIFICATION.md`
15. the active Phase 8 handoff and preparation documents

Then inspect the current Git status, current branch, recent commits and the
actual RTL/module ownership. Do not assume that the repository state matches a
historical handoff. Preserve unrelated user changes.

Before implementation, identify:

- the current generated microcode format and compiler command;
- the current decoder and dispatch ownership;
- the current visible and hidden segment state;
- the current event/exception owner;
- the current BIU request/response and cancellation contracts;
- the current test commands for Verilator, Icarus, lint and synthesis;
- any known open evidence notes that affect event or segment semantics.

If the repository contradicts the Protected-Mode specification, stop at the
contradiction, record it, and resolve it from Intel 80286 evidence before making
a broad RTL change.

---

## 3. Non-negotiable architectural constraints

### 3.1 80286 only

Implement the 80286, not a generic later x86 CPU. Do not add:

- paging;
- CR0/CR2/CR3/CR4 or other 386 control registers;
- 32-bit operands or addressing;
- 386 descriptor granularity/default-size fields;
- 386 TSS layout;
- 386-style protected-to-real mode exit;
- 386-only system instructions;
- undocumented behaviour invented to simplify implementation.

The target has 16-bit selectors, 16-bit offsets, 24-bit physical addresses and
the 80286 descriptor, gate and task formats.

### 3.2 CPU-only boundary

Keep all of the following outside this repository:

- PC/AT chipset and motherboard logic;
- PIC, PIT, DMA, 8042 and RTC/CMOS;
- RAM/ROM mapping and BIOS packaging;
- VGA/EGA, storage, ISA and MiSTer logic;
- AT bus glue and machine-level diagnostics.

The CPU may issue the required memory, I/O, interrupt acknowledge and bus
ownership transactions through its native interface. The downstream consumer
owns the devices that respond.

### 3.3 Ownership

Maintain one owner for each architectural responsibility:

- decoder: opcode/ModR/M recognition and symbolic dispatch;
- microcode: ordered semantic sequencing;
- register file: visible GPRs, segment selectors, IP and FLAGS;
- segment service: hidden caches, reloads and access checks;
- descriptor service: selector resolution, descriptor fetch/decode and privilege
  predicates;
- event service: exception/interrupt/gate entry, return and priority;
- task service: TSS saves/loads, busy/link state and task returns;
- BIU: all physical bus cycles, READY waits, HOLD/HLDA and response retention;
- prefetch unit: instruction queue storage, refill and flush;
- timing policy: historical delays only, never functional semantics.

Do not create a second decoder, a second architectural register file or an ad-hoc
bus master inside a system-instruction handler.

---

## 4. Evidence and ambiguity policy

Use this source hierarchy:

1. Intel 80286 programmer and hardware manuals;
2. reproducible physical 80286 evidence and pinned captures;
3. pinned `SingleStepTests/80286` cases when Protected-Mode data exists;
4. independent emulators and reference cores as corroboration only;
5. implementation convenience.

For every non-obvious rule, record:

- the source and exact section/page or test identity;
- the rule being implemented;
- the observable architectural consequence;
- whether the rule is confirmed, provisional or unresolved;
- the test that would detect a regression.

Do not silently choose a 386 interpretation when the 286 rule is uncertain. Add
an explicit pending item and stop the affected milestone until the ambiguity is
resolved or consciously accepted by the project owner.

---

## 5. Required implementation order

Do not implement all Protected Mode in one pass. Work through these milestones.

### PM0 — State and descriptor foundation

Implement and test:

- 16-bit MSW with PE and the documented 80286 fields;
- GDTR and IDTR (16-bit limit, 24-bit base);
- LDTR and TR visible selectors plus hidden caches;
- CS/DS/ES/SS hidden-cache representation for protected mode;
- selector decomposition (`index`, `TI`, `RPL`);
- descriptor byte assembly through the existing BIU;
- GDT/LDT table selection and complete 8-byte limit checks;
- typed descriptor classes and reserved-form rejection.

Do not connect this milestone to instruction execution until parser and state
tests pass independently.

### PM1 — System instructions

Implement through the existing project-owned decoder and microcode path:

- `SGDT`, `SIDT`, `LGDT`, `LIDT`;
- `SMSW`, `LMSW`;
- `SLDT`, `LLDT`;
- `STR`, `LTR`;
- `VERR`, `VERW`;
- `LAR`, `LSL`, `ARPL` when their exact 80286 semantics are pinned;
- `CLTS` only after its 80286 availability and semantics are confirmed.

For every instruction, implement legal forms, invalid forms, memory wait states,
faults, FLAGS effects, destination preservation and retirement behaviour.

Do not implement `MOV CRx`, paging, 386 debug/control instructions or hidden
testbench-only PE writes.

### PM2 — Protected segment loads and access checks

Implement:

- protected CS, DS, ES and SS reloads;
- selector null/table-limit/present/type checks;
- CPL/DPL/RPL/effective-privilege rules;
- readable-code and writable-data policy;
- conforming/non-conforming code rules;
- expand-down data checks;
- code/data/stack segment-limit checks;
- protected instruction fetch and queue redirect;
- typed #GP, #NP, #SS and #TS fault production.

Validate the complete protected word before its first physical half where the
80286 requires a pre-check. Do not use cancellation to fake a precise rollback.

### PM3 — Protected events and gates

Implement:

- IDT lookup and complete 8-byte entry-limit validation;
- interrupt gates;
- trap gates;
- software interrupt DPL rules;
- external INTR/NMI entry rules;
- protected exception frames and error codes;
- same-level and outer-level `IRET`;
- nested-fault handling and shutdown policy;
- queue flush and exactly-once event completion.

No handler instruction may execute before target descriptor validation, required
stack changes and frame writes complete.

### PM4 — Call gates and privilege stack changes

Implement:

- same-level call gates;
- inter-level call gates;
- TSS privilege-stack selection;
- parameter-word copying;
- protected far returns;
- fault atomicity for every validation stage.

Test every supported CPL/RPL/DPL relationship, including rejected transfers.

### PM5 — TSS and task switching

Implement the fixed 80286 TSS contract:

- TSS field layout and named offsets;
- `LTR` and busy-state updates;
- direct TSS far call/jump;
- task gates;
- outgoing save and incoming load;
- backlink and nested task state;
- task-switched MSW state;
- `IRET` task return.

Use one task-switch service for all entry paths. Do not use a 386 TSS or assume
that task switching is just a larger call-gate frame.

### PM6 — Closure

Complete:

- full directed Protected-Mode suite;
- dual-simulator regression;
- lint and synthesis sanity;
- SingleStep Protected-Mode integration when available;
- independent review and evidence report;
- timing-policy separation;
- standalone integration/export notes.

---

## 6. Required architectural contracts

### 6.1 Descriptor contract

Document and test:

- exact 80286 8-byte descriptor layout;
- reserved-field policy;
- descriptor classes;
- GDT/LDT selection;
- table-limit arithmetic without wraparound;
- present/accessed/busy state;
- base/limit/access-rights cache contents;
- descriptor memory side effects.

The descriptor service shall return a typed candidate result. It shall not write
architectural state directly when validation fails.

### 6.2 Selector and privilege contract

Create a truth table for every operation involving:

- CPL;
- DPL;
- RPL;
- effective privilege;
- present state;
- segment type;
- table origin;
- null selectors;
- conforming code;
- stack selectors.

The truth table must be executable or directly consumed by directed tests. Do
not leave privilege rules only as prose.

### 6.3 Hidden-cache contract

On successful segment reload, commit visible selector and hidden cache as one
architectural operation. On failure, retain the old architectural cache unless
the authoritative 80286 rule explicitly defines a partial effect.

Effective-address generation, prefetch, stack operations, far transfers and
event entry must consume cache state, not reconstruct a base from the selector.

### 6.4 Event and frame contract

Extend `docs/INTERRUPTS_EXCEPTIONS.md` with protected-mode rows before wiring
RTL. Each event row must define:

- source and eligibility;
- priority;
- vector;
- gate type;
- saved IP semantics;
- FLAGS image and IF/TF effects;
- CS/SS stack changes;
- error-code presence and width;
- retirement/completion pulses;
- nested-fault behaviour;
- queue flush point.

### 6.5 TSS contract

Create a named field-offset table for the 80286 TSS and test every field used by:

- LTR;
- privilege stack switching;
- task save/load;
- task gates;
- nested task return.

The table must explicitly identify fields that are reserved or not implemented.

### 6.6 Bus contract

All descriptor, gate, TSS, stack and IVT/IDT accesses go through the BIU. The
BIU must preserve address, direction, status, byte enables and write data while
waiting for READY. HOLD cannot split a physical transfer or an architectural
sequence declared indivisible by the 80286 contract.

Add transaction labels or trace metadata for descriptor, TSS, gate, frame and
protected instruction-fetch activity. Keep cycle-accurate refinement separate
from functional acceptance.

---

## 7. Test-first requirements

Before each RTL slice, add or update focused tests. At minimum, cover:

### 7.1 Descriptor tests

- null, first and last valid selectors;
- GDT and LDT selection;
- exact table-limit boundary;
- one-byte and one-descriptor overflow;
- all supported descriptor classes;
- present/not-present state;
- reserved encodings;
- base values crossing physical address boundaries;
- odd and stalled descriptor reads;
- reset during a descriptor transaction.

### 7.2 Privilege tests

- all relevant CPL/DPL/RPL combinations;
- data reads and writes;
- readable code as data;
- non-readable code;
- writable and non-writable data;
- conforming and non-conforming code;
- valid and invalid SS loads;
- null selector behaviour;
- expand-up and expand-down limits.

### 7.3 Instruction tests

For each system instruction:

- legal register/memory form;
- ModR/M coverage;
- memory wait and held response;
- invalid encoding;
- table/segment limit fault;
- privilege fault;
- unchanged destination state after failure;
- FLAGS effects;
- exactly-once retirement.

### 7.4 Event/gate tests

- interrupt versus trap gate IF/TF behaviour;
- software interrupt DPL rejection;
- hardware INTR/NMI acceptance;
- IDT limit failure;
- not-present gate/target;
- same-level entry;
- outer-level entry with stack switch;
- error-code frame;
- `IRET` to same level;
- `IRET` to outer level;
- nested fault and shutdown policy;
- event coincident with READY, pause or HOLD.

### 7.5 Task tests

- LTR valid/invalid selector;
- busy state;
- direct TSS transfer;
- task gate;
- outgoing register/segment save;
- incoming cache load;
- backlink and nested return;
- invalid incoming state;
- task switch under READY wait;
- reset during task-switch progress.

### 7.6 Mutation tests

Build deliberate mutants that:

- ignore TI;
- wrap descriptor-table arithmetic;
- accept a non-present descriptor;
- invert an RPL comparison;
- skip a segment-limit check;
- commit CS before target validation;
- lose a TSS busy update;
- duplicate a frame push after a pause;
- release bus ownership early;
- flush the queue at the wrong point.

The verification suite must reject each mutant for the correct reason.

---

## 8. Required workflow for every implementation increment

For each increment:

1. inspect the current source and active handoff;
2. identify the smallest architectural slice;
3. write or update the contract and directed tests;
4. implement the smallest RTL/microcode change;
5. regenerate all generated artifacts through the official tooling;
6. run the focused test;
7. run relevant Verilator lint;
8. run the affected tests in Verilator and Icarus;
9. run relevant SingleStep or hardware-derived tests when available;
10. run Yosys/synthesis sanity where the module hierarchy is affected;
11. run the broader regression;
12. inspect diffs, generated-artifact consistency and test logs;
13. document evidence, limitations and exact commands;
14. commit only the verified logical increment.

Do not proceed past a failing check by changing expected values, excluding a
test, weakening an assertion or silently changing the contract.

Suggested commands, adapted to the repository's actual available targets:

```text
make lint
make unit
make test
make regression
make microcode-test
```

Use the exact commands documented by the current `SPK286_ENVIRONMENT.md` and
Makefile. If a command is unavailable, report the missing dependency and run the
closest documented substitute; do not invent a green result.

---

## 9. Protected-Mode implementation checklist

Maintain a checklist in the implementation report and update it only with
evidence:

- [ ] Intel source identities and relevant pages recorded.
- [ ] Descriptor bit layout and reserved-field policy pinned.
- [ ] Selector/privilege truth table executable.
- [ ] MSW and system-register state implemented.
- [ ] GDT/LDT/IDT table arithmetic tested without wraparound.
- [ ] Hidden segment-cache ownership implemented.
- [ ] System-instruction matrix complete for the current milestone.
- [ ] Protected segment reload matrix complete.
- [ ] Limit/expand-down checks complete.
- [ ] Protected instruction fetch and queue flush tested.
- [ ] Exception/error-code matrix complete.
- [ ] Interrupt/trap/call/task gates tested.
- [ ] IRET same-level and outer-level paths tested.
- [ ] 80286 TSS layout and task-switch paths tested.
- [ ] Bus traces cover descriptor/TSS/frame transactions.
- [ ] READY/pause/HOLD/reset retention tested.
- [ ] Verilator and Icarus agree on affected tests.
- [ ] Lint and synthesis sanity pass.
- [ ] Real-Mode and Phase 8 regressions remain clean.
- [ ] No paging or 386-only semantics entered the RTL.
- [ ] Evidence report and known limitations updated.

---

## 10. Stop conditions

Stop implementation and report the blocker if:

- the Intel 80286 rule cannot be reconciled with current project contracts;
- a proposed change requires 386 behaviour to make a test pass;
- descriptor, event, task or BIU ownership becomes ambiguous;
- a fault's partial effects are unknown and the implementation would guess;
- a test only passes after expected data is modified;
- generated microcode is stale or manually edited;
- Real-Mode behaviour regresses without a documented architectural reason;
- protected-mode work starts requiring PC/AT chipset or BIOS logic;
- the available evidence cannot distinguish competing behaviours.

When stopped, provide:

1. the smallest reproducer;
2. exact command and source/test identity;
3. observed versus expected state/bus activity;
4. the conflicting source rules;
5. the smallest decision needed to continue.

---

## 11. Required final report

At the end of each milestone, report in Spanish or English with these sections:

1. **Scope completed** — exact architectural behaviours implemented.
2. **Files changed** — RTL, microcode, tests and documents.
3. **Evidence** — Intel references, physical captures and test identities.
4. **Verification** — exact commands and pass/fail results.
5. **Bus behaviour** — descriptor, frame, TSS and READY/HOLD observations.
6. **Known limitations** — unresolved or intentionally deferred behaviour.
7. **Real-Mode impact** — regression status and any justified changes.
8. **Next smallest increment** — one bounded follow-up task.

Do not claim “Protected Mode complete” while any required milestone or evidence
class remains missing.

---

## 12. First task for the new session

Your first response must not start by editing RTL. It must:

1. confirm the repository path and current branch;
2. show the current Git status without modifying it;
3. read the required documents listed in section 2;
4. summarize the current segment, event, BIU and microcode ownership;
5. identify whether PM0 can start without resolving an existing contradiction;
6. propose the smallest PM0 implementation slice and its tests.

Only after that review may you implement the first change. Begin with PM0
descriptor/state infrastructure, not with gates, task switching or an operating
system boot experiment.

The goal is a verified 80286 Protected-Mode CPU boundary, not merely a program
that happens to run in a PC emulator.

