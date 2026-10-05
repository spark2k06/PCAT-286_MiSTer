# Instruction Matrix

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

## Milestone 7 current slice - 2026-09-16

The active generated image is format 21 (121 entries, 719 words, ten address
bits and eight control bits). The LOADALL state owner and evidence boundary are
described in [MILESTONE_7_LOADALL.md](MILESTONE_7_LOADALL.md) and
[LOADALL_EVIDENCE.md](LOADALL_EVIDENCE.md).

| Encoding | Status | Verification |
| --- | --- | --- |
| `0F 05` | Functional fixed-image LOADALL slice; real-mode hidden-cache translation verified | `spk286_decoder`, `spk286_loadall_service`, `spk286_loadall_integration`, both simulators |
| `0F 04`, `0F 07`, other 286 `0F` holes | Invalid-opcode classification retained | Decoder checks and existing event/exception boundary |
| `64h`-`67h` | Invalid first bytes on the 80286; no 386 prefix behavior | Decoder classification contract |
| LOADALL protected-mode privilege/PE checks | Functional local checks; protected event frame path covered, historical closure pending | `spk286_loadall_service`, `spk286_loadall_protected` |

## Current delivered inventory - 2026-09-09

285 of 307 required files are implemented and passed the fresh 1,288,997-case
arithmetic gate. Exact per-file identities and dispositions are in
phase7_forms.json and phase7_arithmetic_validation.json.

| Boundary | Current delivery | Evidence |
| --- | --- | --- |
| Byte/word scalar data, ALU, TEST, unary, shifts, adjustments and FLAGS | Implemented | Full admitted physical families and directed lifecycle tests |
| Segment MOV/PUSH/POP and SS inhibition | Implemented | Full physical families; directed event tests under recorded evidence policies |
| PUSHA/POPA/ENTER/LEAVE and BOUND | Implemented | Full physical families and exact partial-write/fault checks |
| LDS/LES and far CALL/JMP/RET | Implemented | Full physical families and CS/cache/redirect lifecycle checks |
| MUL/IMUL/DIV/IDIV and immediate IMUL | Implemented | All 50,000 arithmetic records; D-036 byte-IDIV disposition; exact #DE frame checks |
| Memory strings and REP | Separate candidate; not delivered | Full prototype gate passed; competing-event evidence and integration pending |
| Scalar and string I/O | Separate candidate; not delivered | Directed tests pass; full E7 preparation fails on an incomplete physical capture |
| Inherited interrupts/exceptions | Provisional executable baseline | The three D-026 architectural evidence questions remain open |
| Complete Phase 7 / Phase 8 | Incomplete / preparation only | Corrected boundaries independently reviewed; REP CX=0, E7 and complete delivery/gate remain pending |

## Historical phase and increment snapshots

The following tables retain the status and counts at their original delivery.
Use the current inventory above for implementation status.


Phase 5 executes word MOV, binary ALU, stack and near control-flow forms through generated microcode.
This file is the single source of instruction status; entries are updated only when a
test and the relevant evidence support the status.

| Family | Forms covered | Status | Verification |
| --- | --- | --- | --- |
| Reset / code fetch | architectural reset, state, real-mode caches, fetch/restart | Phase 1 foundation verified | Verilator + Icarus directed/smoke, Yosys |
| MOV / data movement | `MOV r16, imm16` (`B8..BF`) | SingleStep state passing; generated microcode | 40,000/40,000 hardware vectors; Verilator + Icarus directed execution |
| MOV / ModR/M store | Unprefixed `MOV r/m16, r16` (`89 /r`), register and memory | SingleStep state passing; generated microcode | 3,955/3,955 supported vectors; all register pairs and EA modes in both simulators |
| MOV / ModR/M load | Unprefixed `MOV r16, r/m16` (`8B /r`), register and memory | SingleStep state passing; generated microcode | 3,940/3,940 supported vectors; all register pairs and EA modes in both simulators |
| ADD | `01/03/05`, `81 /0`, `83 /0`; unprefixed word forms | SingleStep state passing; generated microcode | 20,754/20,754 hardware vectors; independent ALU and dual-simulator CPU tests |
| OR | `09/0B/0D`, `81 /1`, `83 /1`; unprefixed word forms | SingleStep state passing; generated microcode | 20,755/20,755 hardware vectors; independent ALU and dual-simulator CPU tests |
| ADC | `11/13/15`, `81 /2`, `83 /2`; unprefixed word forms | SingleStep state passing; generated microcode | 20,766/20,766 hardware vectors; independent ALU and dual-simulator CPU tests |
| SBB | `19/1B/1D`, `81 /3`, `83 /3`; unprefixed word forms | SingleStep state passing; generated microcode | 20,774/20,774 hardware vectors; independent ALU and dual-simulator CPU tests |
| AND | `21/23/25`, `81 /4`, `83 /4`; unprefixed word forms | SingleStep state passing; generated microcode | 20,761/20,761 hardware vectors; independent ALU and dual-simulator CPU tests |
| SUB | `29/2B/2D`, `81 /5`, `83 /5`; unprefixed word forms | SingleStep state passing; generated microcode | 20,757/20,757 hardware vectors; independent ALU and dual-simulator CPU tests |
| XOR | `31/33/35`, `81 /6`, `83 /6`; unprefixed word forms | SingleStep state passing; generated microcode | 20,757/20,757 hardware vectors; independent ALU and dual-simulator CPU tests |
| CMP | `39/3B/3D`, `81 /7`, `83 /7`; unprefixed word forms | SingleStep state passing; generated microcode | 20,761/20,761 hardware vectors; independent ALU and dual-simulator CPU tests |
| PUSH | `50..57`, `68`, `6A`, `FF /6` | SingleStep state passing; generated microcode | 52,508/52,508; original PUSH SP, SS/limit/READY/odd-word tests |
| POP | `58..5F`, `8F /0` | SingleStep state passing; generated microcode | 43,516/43,516; destination precheck and POP SP ordering |
| Near CALL | `E8`, `FF /2` | SingleStep state passing; generated microcode | 8,785/8,785; architectural return IP and nested streams |
| Near RET | `C3`, `C2` | SingleStep state passing; generated microcode | 9,646/9,646; optional unsigned stack release |
| Near JMP | `E9`, `EB`, `FF /4` | SingleStep state passing; generated microcode | 12,749/12,749; six-byte queue flush and stale response discard |
| Jcc | all `70..7F` | SingleStep state passing; generated microcode | 80,000/80,000; all 512 predicate/FLAGS combinations |
| LOOP / JCXZ | `E0..E3` | SingleStep state passing; generated microcode | 19,390/19,390; count boundaries and taken/not-taken paths |
| Strings / REP | none yet | Not implemented | — |
| Multiply / divide | none yet | Not implemented | — |
| I/O | none yet | Not implemented | — |
| Interrupts / exceptions | protected same-level and bounded outer-level IDT interrupt/trap gates, external NMI/INTR, same-level and bounded outer-level IRET, error-code/nested-entry policy | Real-mode baseline plus PM3a/PM3b/PM3c/PM3d/PM3e functional slices | `spk286_protected_system`, `spk286_protected_event_outer`, event matrices |
| 80286 real-mode additions | none yet | Not implemented | — |
| Protected-mode system instructions | `SGDT/SIDT/LGDT/LIDT/SMSW/LMSW/SLDT/STR/LLDT/LTR/VERR/VERW/LAR/LSL/ARPL/CLTS`; CPL0 success and CPL1/CPL3 privilege rejection | PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g functional slice | `spk286_protected_system` (488 checks, including 388 PM1 selector-matrix checks), `spk286_arpl`, `spk286_clts`, `spk286_clts_privilege` (13 checks) |

## Protected-Mode PM0/PM2 preparation — 2026-09-11

The PM0 descriptor/state foundation is independently tested. PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g connect
a bounded system-instruction slice through the normal decoder, microcode and
BIU owners. PM2a adds protected DS/ES/SS reloads, hidden-cache commits and
pre-BIU data limit checks. PM2b adds protected CS validation and direct far
transfer cache/redirect commit. PM3a adds IDT lookup and same-level interrupt
and trap-gate entry; PM3b adds external NMI/INTR entry and validated same-level
IRET. PM3c adds bounded selector/error-code frames and nested event-entry
shutdown. PM3d adds a bounded outer-level IRET return with restored SS:SP.
PM3e adds a bounded outer-level interrupt/trap-gate entry using TSS-selected
SPn/SSn and a prechecked destination frame. PM4a adds same-level call gates.
PM2e now extends data, event-stack, call-gate and outer-return range handling
to expand-down descriptors. PM2 also covers the normal expand-up CS demand
boundary: an instruction crossing CS:01FF faults before the out-of-limit code
cycle and preserves the incomplete destination. PM3d also accepts a
conforming-code `IRET` without changing CPL or SS. Direct protected TSS
switching now has a bounded PM5ae slice covering direct TSS transfers, IDT
task gates, nested-task `IRET` and non-null incoming LDTR resolution. The full PM1 form list remains
recorded in
[PROTECTED_MODE_PM0.md](PROTECTED_MODE_PM0.md).

| Family | Forms | Status | Verification |
| --- | --- | --- | --- |
| Descriptor-table registers | GDTR/IDTR base+limit; LDTR/TR selector+hidden cache | PM0 state foundation | `spk286_protected_foundation`: 24 checks, Icarus + Verilator |
| Selector/descriptor parser | 8-byte 286 segment/system descriptors; GDT/LDT decomposition | PM0 independent service | `spk286_protected_foundation`: boundary, reserved-form and typed-candidate checks |
| Protected-mode system instructions | `SGDT/SIDT/LGDT/LIDT/SMSW/LMSW/SLDT/STR/LLDT/LTR/VERR/VERW/LAR/LSL/ARPL/CLTS`; CPL0 success and CPL1/CPL2/CPL3 privilege rejection | PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g functional slice | `spk286_protected_system` (538 checks: 388 selector-inspection + 49 LLDT/LTR matrix checks), `spk286_protected_expand_down` (1152 CPL1/CPL2/CPL3 selector-matrix checks), `spk286_arpl`, `spk286_clts`, `spk286_clts_privilege` (13 checks) |
| Protected segment reloads / cache translation | `MOV DS/ES/SS,r/m16`; GDT/LDT resolution; accessed bit; null `DS`/`ES` acceptance and null `SS` rejection; normal and expand-down word limit gates; CPL0/CPL1/CPL2/CPL3 DPL/RPL/type/presence matrices | PM2a + PM2e functional slices | `spk286_protected_system`, `spk286_protected_expand_down` (2183 combined PM1–PM4 checks; CPL2 PM1/PM2/PM4a slices complete) |
| Protected CS / direct far transfers / instruction fetch | `CALL/JMP FAR` validation path; conforming and non-conforming CS rules; `RETF` validation path; CS cache, IP and prefetch redirect commit; normal CS-limit demand fault | PM2b + protected fetch-boundary functional slices | `spk286_protected_expand_down` adds 188 CPL0/CPL1/CPL2/CPL3 CS matrix checks; `spk286_protected_system`: 100 checks including CS:01FF demand boundary; far matrices: 6,760 + 247 cases, Icarus + Verilator |
| Protected event gates | IDT bounds; interrupt/trap gates; software DPL; same-level and bounded outer-level target CS/IP; target DPL/RPL/type/presence; conforming target and frame entry | PM3a/PM3e + PM2e functional slices | `spk286_protected_system`: 7 additional checks; `spk286_protected_expand_down`: 89 CPL0/CPL1/CPL2/CPL3 gate, target, type and limit checks; see [PROTECTED_MODE_PM3A.md](PROTECTED_MODE_PM3A.md) |
| Protected external events / return | NMI/INTR IDT entry; INTA vector; same-level `IRET` CS validation and commit | PM3b bounded functional slice | `spk286_protected_system`: 3 additional checks, Icarus + Verilator; see [PROTECTED_MODE_PM3B.md](PROTECTED_MODE_PM3B.md) |
| Protected exception frames / nested entry | selector/error-code word after saved IP; handler consumption; invalid nested target enters shutdown | PM3c bounded functional slice | `spk286_protected_system`: 2 additional checks in Icarus; see [PROTECTED_MODE_PM3C.md](PROTECTED_MODE_PM3C.md) |
| Protected outer-level return | saved `IP/CS/FLAGS/SP/SS`; CS/SS descriptor validation; conforming-code same-level `IRET`; coherent cache/context commit | PM3d bounded functional slice | `spk286_protected_system`: 5 additional checks in Icarus; see [PROTECTED_MODE_PM3D.md](PROTECTED_MODE_PM3D.md) |
| Protected outer-level event entry | TSS `SPn/SSn` selection; target CS/SS validation; complete old-context/error frame; atomic CS/SS/SP/IP/FLAGS commit | PM3e bounded functional slice | `spk286_protected_event_outer`: 6 checks in Icarus; see [PROTECTED_MODE_PM3E.md](PROTECTED_MODE_PM3E.md) |
| Protected same-level call gates | call-gate lookup/DPL/RPL/TI; conforming and non-conforming target CS/IP validation; return CS:IP frame and queue redirect | PM4a bounded functional slice | `spk286_protected_system`: GDT/LDT ordinary, conforming, RPL1/RPL3 and CPL1/DPL0 rejection checks; `spk286_protected_expand_down`: 28-case CPL2 DPL/RPL/presence/target/limit matrix in Icarus; see [PROTECTED_MODE_PM4A.md](PROTECTED_MODE_PM4A.md) |
| Protected inter-level call/return | TSS `SPn/SSn`; zero/one/two/thirty-one-parameter call gates; copied parameters; outer `RETF`; ordinary and expand-down stack bounds; CPL/RPL/DPL/presence/GDT-limit privilege matrix | PM4b + PM2e functional slices | `spk286_protected_system` (100 checks), `spk286_protected_retf` (62 checks), `spk286_protected_expand_down` (96 PM4 gate-matrix checks across CPL0/CPL1/CPL2/CPL3); see [PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md) |
| Direct protected task switching | fixed 80286 TSS image; outgoing save/incoming load; backlink/busy; task-segment cache validation; incoming IP/CS-limit validation; atomic TR/MSW/LDTR/FLAGS/IP/register/cache commit; nested-task `IRET` return; non-null incoming LDTR and LDT-qualified segment selectors; far `CALL/JMP` through task gates; typed task-gate rejection and reset cancellation; direct-TSS `DPL >= max(CPL,RPL)` authority; IDT task-gate DPL/RPL authority and terminal task-switch commit; direct-TSS target descriptor fault matrix; event target descriptor fault matrix; HOLD/HLDA retention; incoming LDTR selector/class/presence/limit matrix; explicit MSW.TS checks on direct, gate and IRET paths; independent fixed-TSS word/offset table checks; `LTR` busy-state and fixed-limit matrix; protected transaction trace metadata | PM5a–PM5af bounded functional slice | `spk286_task_switch_service` (42 checks), `spk286_protected_task` (20 checks), `spk286_tss_service` (38 checks), `spk286_protected_ltr` (23 checks), `spk286_protected_task_fault` (64 checks, 16 CALL/JMP cases), `spk286_protected_task_state_fault` (156 checks, 36 CALL/JMP cases), `spk286_protected_task_gate` (9 checks), `spk286_protected_task_gate_far` (14 checks), `spk286_protected_task_gate_fault` (49 checks, 13 CALL/JMP + reset cases), `spk286_protected_task_privilege` (116 checks, 32 CALL/JMP cases), `spk286_protected_task_privilege_outer` (328 checks, 96 CALL/JMP cases), `spk286_protected_task_gate_privilege` (116 checks, 32 CALL/JMP cases), `spk286_protected_task_gate_privilege_outer` (232 checks), `spk286_protected_task_gate_event_privilege_outer` (448 checks, 144 CPL0–CPL3 cases), `spk286_protected_task_iret` (10 checks) and `spk286_protected_task_ldt` (8 checks, Icarus + Verilator); direct TSS `CALL/JMP`, IDT/far task-gate entry, backlink return, incoming-LDT cache load, CPL0–CPL3 DPL/RPL matrices for direct TSS and far task gates, incoming task CS/SS CPL0–CPL3 matrix, CPL0–CPL3 software-INT task-gate authority and target-fault matrix, direct-target and incoming-state fault atomicity, HOLD/HLDA retention, `LTR` validation and protected transaction trace metadata; see [PROTECTED_MODE_PM5E.md](PROTECTED_MODE_PM5E.md) |

Suggested status progression is: `Not implemented`, `Decodes`, `Functional`,
`SingleStep state passing`, `SingleStep bus passing`, `Timing verified`, and
`Protected-mode verified`.

Each selected opcode file has 5,000 discovered vectors. Inherited exclusions are 1,016
prefix and 29 exception cases for 89, and 1,031 prefix and 29 exception cases
for 8B; none is counted as passed. Whole-word segment overflow fails closed
before data side effects, but exception delivery and prefixes remain unsupported.
Directed bus/READY/byte-lane checks do not imply captured bus-cycle equivalence.

Phase 4 new totals: 200,000 discovered, zero revoked, 32,904 prefix exclusions,
1,011 exception exclusions, 166,085 selected/executed/passed and zero failures.
There are no full-run sampling skips. The inherited 47,895 cases remain required.
TEST and byte/unary ALU forms are not admitted. See PHASE4_SCOPE.md for exact
forms, masks and the defined/preserved/undefined FLAGS distinction.

Phase 5 adds 235,000 discovered vectors, 8,052 prefix and 354 exception
exclusions, and 226,594 selected/executed/passed with zero failures or full-run
sampling skips. The combined inherited/new requirement is 440,574. See
[PHASE5_HANDOFF.md](PHASE5_HANDOFF.md) for the complete per-opcode accounting.

## Phase 6 candidate form/source matrix

| Form/source | Candidate behavior | Evidence boundary |
|---|---|---|
| CD ib / CC / CE | vectors imm8 / 3 / OF-dependent 4, shared frame | complete admitted physical families; both INTO paths |
| CF | ordered IP/CS/FLAGS pops and coherent return | complete family; failed-IRET NMI relationship unresolved |
| 9C / 9D | shared FLAGS push/pop and Real Mode masks | complete families and boundary model cases |
| FA / FB | IF clear/set | complete families; STI old-IF qualifier unresolved |
| F4 | one retirement and architectural halt | complete family plus directed wake/idle tests |
| INTR / NMI / TF | shared entry, INTA, edge retention and priority | directed full-CPU/model evidence, no physical concurrency captures |
| #GP | supported word/stack/code-demand limits | all 1,234 inherited nonprefixed physical #GP cases admitted |
| #UD | invalid 8F groups and invalid owned FF forms | 189 inherited physical #UD cases plus directed forms |
| Entry failure | partial visible frame and shutdown | primary-informed directed boundaries, corpus safeguards exclude low SP |

Total admitted cohort: 474,049. Prefixes and all later-phase instruction families
remain deferred. Legal unsupported forms are not converted into invented #UD.
This is implemented candidate scope, **not release approval**; see
[PHASE6_ARCHITECTURAL_REVIEW](PHASE6_ARCHITECTURAL_REVIEW.md).

## Verified Phase 7 byte/prefix increment — 2026-09-08

Earlier phase tables above are historical admission snapshots. The current
candidate additionally implements B0–B7, 88/8A, C6/C7 /0, the byte forms +0/+2/+4
of the eight binary ALU groups and 80 /0–7. Invalid owned C6/C7 extensions produce
real #UD. Segment overrides, explicit LOCK ownership, duplicate prefixes and the
ten-byte #GP limit apply to these and the inherited 106 families. F2/F3 on these
non-string forms do not perform iteration.

Prototype physical validation passed all 737,998 admitted cases from 150 files:
474,049 original identities, 43,951 readmitted old prefixes, 219,998 new-form
identities; two upstream revocations are separate. Integrated executable gate
status is recorded in PHASE7_HANDOFF.md; no complete Phase 7 pass follows from
this subset. No captured bus equivalence is claimed for these 150 families.

At the byte/prefix snapshot, 157 required opcode files remained absent from the
production decoder/admission registry. IN/OUT has an isolated prototype and an unresolved malformed captured
transaction. All other missing forms in phase7_forms.json remain implementation
obligations, including segments/far transfers, unary/TEST, shifts, multiply/
divide, adjust, added stack/FLAGS, memory strings and string I/O.

## Verified Phase 7 scalar increment

The scalar increment adds TEST 84/85, A8/A9 and F6/F7 /0; register INC/DEC 40–4F;
CBW/CWD 98/99; SAHF/LAHF 9E/9F; CMC/CLC/STC F5/F8/F9; CLD/STD FC/FD. The 31
complete physical files passed 63,000 prototype cases with prefixes/exceptions
admitted and no skips or failures. Directed tests independently cover 2,236 TEST
and 1,968 direct-scalar cases in both simulators. The complete integrated gate
passed all 800,998 distinct physical cases, 32 benches per simulator and the
required compiler/lint/mutation/synthesis/regression checks. Memory INC/DEC, other F6/F7 extensions,
remaining MOV/segment/far/shift/multiply/stack/string/I/O forms remain required.
The active registry has 181 of 307 required opcode files; 126 remain unimplemented.

## Verified Phase 7 shift/rotate increment

C0/C1/D0/D1/D2/D3 now implement /0 ROL, /1 ROR, /2 RCL, /3 RCR, /4 SHL,
/5 SHR and /7 SAR for byte/word register and memory operands, with immediate,
one or CL counts. The isolated full physical run passed 210,000 cases from all
42 required files. Undocumented /6 remains excluded. At the shift snapshot, the production registry
contained 223 of 307 required files; 84 remained absent. The complete integrated
gate passed 1,010,998 distinct physical cases, 34 benches in both simulators,
lint, mutation audits, synthesis and regression. PHASE7_HANDOFF.md records the
exact inputs and delivery status.

## Verified Phase 7 data-transfer increment

86/87 implement byte/word XCHG; 90–97 exchange AX/register (including NOP);
8D computes LEA and faults on a register source; D7 implements unsigned XLAT;
A0–A3 implement accumulator/direct-offset MOV. All sixteen full prototype files
passed 48,000 cases with faults/prefixes included and zero skips/failures.
At the data snapshot, the registry contained 239 of 307 required files; 68 remained missing.
The fresh integrated gate passed 1,058,998 distinct physical cases, all 36 benches
in both simulators and required compiler/lint/mutation/synthesis/regression
checks. Exact delivery status is recorded in PHASE7_HANDOFF.md.

## Verified Phase 7 unary increment

F6/F7 /2 NOT, /3 NEG and FE/FF /0 INC,/1 DEC add eight required files. All
40,000 prototype physical cases passed with prefixes/exceptions included and
zero skips/failures. The active registry contains 247 of 307 required files;
60 remain absent. The fresh integrated unary gate passed 1,098,998 distinct
physical cases, all 38 benches in both simulators and the required compiler,
lint, mutation, synthesis and regression checks. Independent review and the
complete phase remain pending; see phase7_unary_validation.json and the handoff.

## Verified decimal/radix adjustment increment

27,2F,37,3F,D4,D5 implement the six ordinary adjust forms. All 30,000 isolated
physical cases passed, including eleven AAM radix-zero exceptions with complete
saved frames. The active registry has 253 of 307 required files; 54 remain
absent. The fresh integrated gate passed all 1,128,998 disjoint records, 41
benches in both simulators, compiler/lint/mutation checks, synthesis and
regression. See phase7_adjust_validation.json; independent review and complete
Phase 7 delivery remain pending.

## Integrated segment-transfer candidate

06/07/0E/16/17/1E/1F/8C/8E add ordinary segment MOV/PUSH/POP, invalid segment
encodings and successful SS-load inhibition. The prototype passed all 45,000
physical cases; IF/TF inhibition uses Intel documentation and directed tests.
The registry has 262 required files and 45 remain absent. The full integrated
gate and complete phase remain pending. See PHASE7_SEGMENT_TRANSFER.md.

## Integrated stack/frame and BOUND candidate

60/61/62/C8/C9 add PUSHA, POPA, signed BOUND, ENTER and LEAVE. Their isolated
RTL passed all 24,999 non-revoked physical records with unchanged capture data.
The registry contains 267 required files and 40 remain absent. The fresh combined
segment/frame gate remains pending. See PHASE7_STACK_FRAME.md for the ENTER
partial-write and BOUND even-wrap evidence.

## Current combined segment and stack/frame delivery — 2026-09-09

The latest executable inventory is 267 implemented required opcode files, with
40 pending. Segment MOV/PUSH/POP, SS event inhibition, PUSHA/POPA/ENTER/LEAVE and
BOUND passed the combined 1,198,997-case gate. The older phase-specific tables
above describe their historical increments. See phase7_stack_frame_validation.json
for current executable evidence; complete Phase 7 remains incomplete.

## Integrated far pointer/control candidate — 2026-09-09

LDS/LES (C4/C5), direct far CALL/JMP (9A/EA), RETF (CA/CB) and memory far CALL/JMP
(FF /3,/5) are implemented candidates. All eight physical files passed in the
prototype. The registry contains 275 required files, with 32 pending; the fresh
integrated 1,238,997-case gate and delivery are pending.

## Current far pointer and control delivery — 2026-09-09

The integrated executable inventory is 275 required opcode files, with 32
pending. LDS/LES and far CALL/JMP/RET passed the fresh 1,238,997-case gate.
Historical tables above describe earlier increments; phase7_far_validation.json
contains the latest exact executable evidence. Complete Phase 7 is incomplete.
