# Protected mode: global review and implementation specification

Date: 2026-09-29. Status: **review baseline with explicitly marked implementation follow-ups**.

This document records a source review of SPK286 against Intel's 80286 manuals
and the local native 86Box implementation. It defines work to discuss and
implement later. It does not certify protected-mode conformance. The user
requested documentation only, then authorized one integration run using a
disposable copy of the OS/2 disk. No RTL, microcode, test, adapter or production
profile changes are part of this review.
Subsequent authorized implementation and integration observations are marked
within the relevant findings; unaddressed findings remain pending.

## 1. Baseline and evidence rules

| Component | Reviewed baseline |
|---|---|
| SPK286 | `b81d5bff89205d34afd7a458312b39a0bb94e9e4` |
| PCAT-286_MiSTer vendor import | `4d9fcc1` on `beta-05` |
| Local 86Box source | `5630619f5aeddaa5357bb32d25b69dac6b187776` |
| Executed adapter | `build/spk286/86Box-linux`, Release, Verilator backend enabled |
| Adapter RTL source | `D:/GitHub/PCAT-286_MiSTer/vendor/spk286` |
| Executable SHA-256 | `3e1a2aca871abceccd5c390e24f0ac8bc537a287c3966746169ae494ad12358e` |

The primary reference, **[I286]**, is Intel's
[80286 and 80287 Programmer's Reference Manual, 210498-005 (1987)](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
Local cache: `.cache/intel286/programmer.pdf` and `programmer.txt`. PDF SHA-256:
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.
References below use printed section/page identifiers, **B-xx** for instruction
reference pages; OCR sometimes reads the letter B as 8.

Additional primary material available locally is Intel's
[1985 reference manual](https://www.bitsavers.org/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf)
and [Operating Systems Writer's Guide (1983)](https://www.bitsavers.org/components/intel/80286/121960-001_iAPX_286_Operating_Systems_Writers_Guide_1983.pdf).
Use them to resolve wording conflicts, not to multiply independent evidence.

Native 86Box references are paths under `D:/GitHub/86box_dev`, pinned above.
The 286 uses shared `OPS_286_386` / `x86_2386` paths, including `src/cpu/x86seg.c`.
Those files also contain 386 behavior and imperfect checks. Select the 16-bit,
286 path explicitly. Do not import paging, VM86, 32-bit gates/TSS, FS/GS, or an
I/O permission bitmap into this core.

Evidence labels:

- **S — static discrepancy:** the reviewed path contradicts a documented rule.
  A directed executable reproducer is still required before changing RTL.
- **C — candidate:** a suspicious path or disagreement needs further evidence.
- **P — policy:** an intentional compatibility choice or unresolved physical
  behavior, not a newly discovered implementation accident.
- **R — integration observation:** captured on a real software workload. A
  trap alone does not establish that the CPU, rather than the workload, is wrong.

Priorities: **P0** execution context and exception correctness; **P1** instruction
and protection completeness; **P2** boundary and compatibility closure. Priority
is not a claim that the finding caused the current OS/2 failure.

## 2. Why the previous checks did not catch these issues

There was a specification and verification gap. Passing the existing banks was
useful evidence for the cases they encoded, but was interpreted too broadly.

1. **Some tests shared the RTL's wrong assumption.** The old outer-return model
   checked restored SP as if returning accessed the new stack. Its historical
   PM4B7 specification and tests reinforced that model. OS/2 supplied a valid
   empty stack with SP=limit+1 and exposed the mistake.
2. **Instruction names hid different access rules.** Ordinary memory reads,
   descriptor inspection, stack restoration and loading a segment have different
   presence/limit requirements. LSL on an absent descriptor is a concrete example.
3. **Useful unit setup bypassed integration transitions.** Injecting a protected
   context or using LOADALL does not test LMSW followed by an unreloaded real-mode
   CS. Windows exposed that distinction in CPL derivation.
4. **The tested cross-product was incomplete.** CPL/RPL/DPL, conforming code,
   presence, expand-down limits, failed returns and faults during delivery interact.
   One successful case per instruction does not cover these combinations.
5. **Large real-mode coverage was not protected-mode coverage.** The project's
   pinned SingleStep corpus does not establish protected descriptor, gate or task
   semantics. Dual simulators find tool/model issues; they do not provide two
   independent architectural oracles for the same expected result.
6. **Older documents were not always reconciled with later policy.** The PM5
   resolution says JMP clears NT, while the later compatibility decision and
   current RTL preserve incoming NT. See H17.

This review also found disagreements between the Intel instruction appendix,
its explanatory chapters and native 86Box. Replacing one unchecked assumption
with an emulator's behavior would repeat the same problem.

## 3. Corrections already included, not open findings

| Workload/case | Corrected contract | Evidence document |
|---|---|---|
| Windows: initial PE transition | Unreloaded real-mode CS does not imply a nonzero CPL after LMSW | [Entry CPL](PROTECTED_MODE_ENTRY_CPL_20260929.md) |
| Windows: direct protected far CALL | Direct code and gate transfers have separate validation paths | [Direct CALL](PROTECTED_DIRECT_CALL_20260929.md) |
| Windows: demand-loaded target | Valid absent target reports #NP with retryable state | [Not-present targets](PROTECTED_NOT_PRESENT_20260929.md) |
| Windows: failed RETF/IRET | Preserve the source stack cursor until a successful return | [Return restart](PROTECTED_RETURN_RESTART_20260929.md) |
| Windows: LAR/LSL | Descriptor inspection can succeed when P=0 | [Descriptor inspection](DESCRIPTOR_INSPECTION_20260929.md) |
| OS/2: SGDT [BP-6] | Accept valid SS expand-down range; write six bytes | [System-table diagnosis](OS2_SYSTEM_TABLE_DIAGNOSIS_20260929.md) |
| OS/2: RETF to 0067:0800 | Restoring an empty outer stack does not itself access that stack | [Outer-return diagnosis](OS2_OUTER_RETURN_DIAGNOSIS_20260929.md) |

For SGDT/SIDT, the sixth byte's `FF` value is a compatibility choice supported by
native 86Box and the observed OS/2 probe; Intel does not define that byte's value.
Do not describe it as an Intel-mandated constant. The user reported successful
hardware operation of the earlier Windows-related changes. That observation
does not establish complete OS/2 startup or all protected-mode combinations.

## 4. Findings and required behavior

Line numbers below refer to the pinned baseline; signal/function names are the
stable search anchors. Acceptance cases are specifications, not newly executed
tests.

### H01 — System-instruction privilege matrix (S, P1)

`rtl/spk286_micro_executor.sv:334`, `system_privilege_fault`, includes SLDT/STR
stores among privileged operations. Conversely, `descriptor_pre_fault` at 576
does not impose CPL0 on LLDT/LTR. The SLDT/STR store path also lacks the explicit
real-mode rejection used by other descriptor operations.

Required matrix, from [I286] chapter 10 and the individual instructions:

| Operation | Real mode | Protected mode |
|---|---|---|
| SGDT, SIDT, SMSW | Allowed | All CPLs |
| SLDT, STR | #UD | All CPLs |
| LGDT, LIDT, LMSW, CLTS | Allowed subject to instruction rules | CPL0; otherwise #GP(0) |
| LLDT, LTR | #UD | CPL0; otherwise #GP(0) |
| LAR, LSL, VERR, VERW, ARPL | #UD | All CPLs; operand/descriptor checks still apply |

Native evidence: `x86_ops_pmode.h::op0F00_common` (194, 201, 209 onwards) and
its `NOTRM` wrapper. Verify every row at CPL0..3, register/memory forms,
null/non-null selectors and invalid operands. A rejected operation must not
update LDTR/TR, the BUSY bit, destination memory or general registers. Resolve
fault precedence before combining a privilege violation with a bad operand.

**2026-09-30 implementation follow-up: H01 corrected.** SLDT/STR are now
unprivileged in protected mode and reject real mode. Explicit microcode checks
reject forbidden LLDT/LTR before reading their operand; privilege faults carry
zero, not the operand selector, as their error code. VERR/VERW and LAR/LSL also
reject real mode before operand access. The full listed mode/CPL matrix passes
2112 directed cases / 9144 checks in each simulator, including valid/null/TI
selectors and invalid memory operands. Existing system/LTR/CLTS banks and
compiler/ROM/decoder checks pass. See
[targeted milestone evidence](PROTECTED_MODE_TARGETED_FIXES_20260930.md).

### H02 — IOPL, interrupt control, HLT and LOCK (S; LOCK oracle caveat, P1)

The micro-executor's `set_if` and `halt_request` paths are unconditional after
decode; scalar/string I/O do not show a CPL-versus-IOPL gate. [I286] 10.1 and the
I/O instruction definitions require CLI/STI and I/O to reject CPL>IOPL. HLT is
privileged. [I286] 3.29 also restricts explicit LOCK by IOPL on the 286.

Native comparison: `x86_ops_flag.h::opCLI/opSTI`,
`x86_ops_io.h::check_io_perm` call sites and `x86_ops_misc.h::opHLT`.
Native `opLOCK` primarily checks encoding legality; it is not a sufficient
oracle for Intel's 286 IOPL rule. Implicit memory XCHG locking is explicitly
independent of IOPL in [I286] B-114.

Specify all 16 CPL/IOPL combinations, byte/word scalar I/O, REP INS/OUTS,
CLI/STI, HLT, explicit LOCK and implicit XCHG. A denied operation must produce
#GP(0) before any port transaction, IF change or halt/lock side effect. Record
zero-count REP and invalid LOCK precedence separately where evidence is needed.

**2026-09-30 implementation follow-up: HLT corrected; H02 remains open.**
The supplied Phar Lap HELLO program reached a CPL3 HLT service stub and halted
instead of raising #GP(0), even with IOPL=3. The micro-executor now faults before
requesting HALT. Both simulators pass the dedicated 104-case privilege bank;
HELLO and MEM1 finish on the rebuilt 86Box/SPK286 backend. Follow-up comparison
also accepts MEMTEST, TELLME, TELLPROT, SWTEST, XMEMTEST and BIOSDUMP; the original
BIG simulation was stopped by the user before completion; the user subsequently
confirmed BIG working on PCAT/MiSTer hardware on 2026-09-30. These utilities do
not close the privilege matrix. CLI/STI, scalar/string I/O and explicit LOCK
were separate pending work at that checkpoint. See the bounded validation, captured context and
user-reported hardware acceptance in [Phar Lap HLT diagnosis](PHAR_LAP_HLT_20260930.md).

**2026-09-30 second implementation follow-up: CLI/STI and I/O corrected;
H02 remains partial for LOCK and protected REP-zero precedence.** All 16
CPL/IOPL combinations pass the new 2772-case bank in Verilator and Icarus.
Denial produces #GP(0) before IF, STI-shadow, port, memory or string count/index
side effects. Allowed scalar byte/word immediate/DX and INS/OUTS cases include
REP, DF, odd ports, READY stalls and all three timing policies. Existing I/O,
HLT and lifecycle banks pass; 1400 physical real-mode SingleStep samples pass.
No I/O bitmap or other 386 feature is added. Explicit LOCK and the privilege
check for protected zero-count REP remain unresolved and were not changed.
See [targeted milestone evidence](PROTECTED_MODE_TARGETED_FIXES_20260930.md).

### H03 — POPF and non-task IRET flag masks (S, P0)

`spk286_micro_executor.sv:1439`, `sequential_flags_write_mask`, gives nonzero-CPL
POPF mask `4FD5`, always permitting IF changes. Non-task IRET uses `0FD5`, which
never restores NT/IOPL and still permits IF without checking IOPL.

Under [I286] 10.1, NT can be restored, IOPL can change only at CPL0, and IF can
change only when the executing CPL permits it under the old IOPL. Native
`x86_ops_flag.h::opPOPF_286` and `x86seg.c::pmodeiret` implement distinct masks.
The register block's actual `7FD5` filter is not the blocking mask here, despite
an older comment about preserving NT.

Test every CPL/IOPL pair with inverse old/new IF/NT/IOPL, same/outer IRET,
real-mode controls, and a failing return. Use the pre-return privilege when
deciding which FLAGS fields may change; verify exact fault-state preservation.

**2026-10-01 implementation follow-up: H03 corrected.** POPF and ordinary IRET
now share the 286 privilege mask: restore NT, permit IOPL only at CPL0, and
permit IF only when executing CPL <= old IOPL. Outer returns use the source
privilege context. The new 5892-case bank passes in both simulators, also with
PCAT P01/P02/P05 options; failed returns preserve FLAGS/CPL/SP. Existing
ordinary/nested return banks and all 10000 physical real-mode 9D/CF cases
pass. See [block validation](PROTECTED_MODE_BLOCK_20261001.md).

### H04 — NT on interrupt/trap-gate entry (S, P0)

The `clear_event_flags` masks at micro-executor line 1441 clear TF and, for an
interrupt gate, IF. Neither mask clears NT. [I286] 10.1 requires ordinary
interrupt entry to save the old flags and then clear NT; task-gate entry has
different nesting semantics.

Native reference: `x86seg.c::pmodeint` and its flags update. Enter interrupt and
trap gates with NT=1, verify the saved flag word, live NT=0, appropriate IF/TF,
and a normal handler IRET. Otherwise IRET can incorrectly follow the TSS backlink.

**2026-09-30 implementation follow-up: H04 corrected.** The protected ordinary
event mask now clears NT after saving the old FLAGS, for both interrupt and
trap gates. Real-mode and task-gate entry keep their separate rules. The new
158-case bank passes in both simulators, including software INT, #GP delivery,
same/inward transfers, NT=0/1 and all timing policies. It also verifies that
handler IRET takes the ordinary stack-return path. Restoring NT from that frame
is still H03, which this correction does not close. See
[targeted milestone evidence](PROTECTED_MODE_TARGETED_FIXES_20260930.md).

### H05 — VERR/VERW and conforming descriptor inspection (S/C, P1)

`descriptor_verify_success_live` at micro-executor 675 requires P=1, and VERR
requires conforming DPL<=CPL. [I286] 11.3.1/B-111 lists type, visibility and
access checks without a presence requirement, and allows readable conforming
code independently of CPL/RPL/DPL. Native `op0F00_common` VERR/VERW does not test
P and skips the privilege comparison for conforming code.

`descriptor_inspect_success_live` applies DPL>=max(CPL,RPL) to LAR even for
conforming code. This conflicts with [I286] 11.3 and native `opLAR`. However,
the short B-60 summary omits the exemption. Also, B-71 describes LSL in terms of
non-conforming segments, while native `opLSL` accepts conforming code. **Do not
silently generalize 386 LSL behavior or mark its exclusion as a proven 286 bug.**

Specify separate LAR, LSL, VERR and VERW truth tables, including P=0, all
conforming privilege combinations, system descriptor classes and undefined
types. Failed inspection leaves the destination unchanged and clears ZF;
invalid selector values do not themselves raise an exception. Record LSL's
conforming case as an evidence question requiring a physical 286 discriminator.

### H06 — Loading readable conforming code into DS/ES (S, P1)

`descriptor_segment_success_live` at micro-executor 720 imposes DPL<=CPL on
conforming code. `spk286_task_segment_service.sv:169` applies the same comparison
to incoming ES/DS. [I286] B-61, B-74 and task-switch B-13 omit that comparison
for readable conforming segments; execution through CS has a different rule.

Native references: `x86seg.c::loadseg` and task segment loading. Test MOV/POP
DS/ES, LDS/LES and task-loaded ES/DS with readable conforming descriptors at
every DPL/CPL/RPL, plus unreadable controls and absent segments. Do not reuse a
CS-transfer predicate for loading a data-access register.

Observed after the H22 correction: OS/2 snapshot 47 faults at `0228:7A57`,
`36 C5 37` (`LDS SI, SS:[BX]`), #GP(`006C`). CS has CPL0 and the target
descriptor at `1DE4A8` is `12AA 0B80 DF1A 0000`: present, readable conforming
code, DPL2. The erroneous DPL<=CPL comparison rejects this load. This matches
H06's previously recorded rule discrepancy. The subsequent H06 implementation
removes this comparison from both normal DS/ES loads and task-loaded ES/DS.
The focused evidence and isolated retest are in
[H06 diagnosis and validation](OS2_CONFORMING_DATA_LOAD_20260929.md);
the original fault is preserved in the [H22 retest](OS2_CALL_GATE_ACCESSED_20260929.md).

### H07 — Return to conforming code (S, P0)

`descriptor_iret_cs_success_live` (652) has no common RPL>=CPL check for its
conforming arm. `iret_outer_required` (1072) suppresses an outer stack switch
for conforming code. Candidate CS selector/RPL publication (1569 onwards)
retains the old CPL for conforming returns.

[I286] RET B-94/B-95 selects same/outer return using the saved selector's RPL,
then applies the conforming DPL rule. Native `pmoderetf` first rejects RPL<CPL,
and uses RPL>CPL to enter its outer-return path, including conforming targets.
The same shared SPK286 machinery is used by non-task IRET; audit its separate
Intel algorithm rather than assuming all steps are interchangeable.

Test RETF/RETF imm/IRET with conforming targets for RPL<CPL, RPL=CPL and
RPL>CPL, DPL boundaries, present/absent targets and valid/invalid outer SS.
Assert CPL, CS.RPL, SS:SP, frame consumption and fault restart state.

OS/2 1.3 retest after H08/H21 confirmed H07 in an executed path. At
`0228:7B96`, `RETF 000A` attempts to return from CPL0 to CS=`0097` (RPL3),
IP=`0107`. The now-present descriptor at selector index `0094` has access
byte `DF`: conforming readable code, DPL2. Its `DPL <= return RPL` check
passes. The current RTL instead requires `DPL <= current CPL`, rejects the
load, and latches #GP(`0094`); no CS candidate is published. The subsequent
snapshot's combinational `fault error=0000` is not the latched event error.
The source SS=`0038` is expand-down with limit `F4DF`; SP=`F8E8` and the
tentative cursor=`F8EC` are even and in range, so this observation does not
implicate H12 or H14. After correcting the descriptor predicate, retain the
other H07 acceptance checks above: an RPL3 conforming return must also load
the outer SS:SP frame and publish the destination CPL. Local evidence is in
`86box_dev/build/spk286/os2-retf-fault-20260929/` (`spk286-os2.log` and
`retf-fault.txt`).

Implementation retest, 2026-09-29: the H07 return checks now pass for RETF,
RETF immediate and IRET in the directed matrix. OS/2 passed the former
`0228:7B96` #GP(`0094`) failure. It later stopped making progress at
`0257:214C` (`CALL FAR`): after #NP(`007C`), `VALIDATE_CALL_CS` remained at
micro-PC `01DE` for more than 40 million sampled cycles, with no new exception.
This later stall was initially associated with H19's restart matrix. The
follow-up investigation established an independent missing Accessed-bit
write transition, now recorded as H22 below. It also reproduces on a fresh
CALL without any prior fault. H07 is not a claim that OS/2 completes boot.
Evidence: `86box_dev/build/spk286/os2-h07-20260929/`
and the periodic probe in `os2-h07-probe-20260929/spk286-os2-probe.log`.

### H08 — DS/ES invalidation after outer return (S + R, P0)

Successful ordinary outer returns publish CS/SS via the two cache commit ports
(`protected_segment_commit_*` around 942/984). No return-driven invalidation
path for DS/ES appears in `spk286_protected_state.sv` or the micro-executor.

[I286] RET B-95 and the IRET algorithm require clearing data segment registers
that are no longer valid at the destination privilege. Native `pmoderetf` at
1514 and `pmodeiret` at 2140 call `check_seg_valid` for DS/ES.

Load a privileged DS/ES before returning to ring 3; after the return, observe
selector/cache invalidation and #GP(0) on use, with no data access. Include
segments that remain valid, null selectors and readable conforming code. Decide
from 286 evidence whether each check uses cached attributes or rereads the table;
do not inherit extra FS/GS or 386 cache semantics from native 86Box.

The authorized OS/2 trial exposed a matching case: ring-3 startup saves ES=0210
(a DPL0 data selector) and later faults restoring it. The preceding captured
outer-return context had that same privileged ES. The missing invalidation is
directly visible in RTL; the link between that return and the later saved value
is reconstructed from the two captures and startup disassembly, not a continuous
instruction trace. See the [trial report](OS2_FIRST_TRIAL_FINDINGS_20260929.md).

### H09 — JMP through a call gate (S + R, P1; corrected 2026-09-30)

`descriptor_post_fault`'s `cs_validation_operation` arm at 752 accepts ordinary
code and task destinations, but not the call-gate route supported for CALL.
[I286] JMP, "JUMP TO CALL GATE", permits transfers subject to the JMP-specific
privilege rules. Native `x86seg.c::loadcsjmp`, call-gate case at 650, implements it.

Add direct/indirect far JMP cases through GDT/LDT call gates. Check gate
visibility/presence, target type, ignored target RPL and permitted target DPL;
JMP must not perform CALL's parameter copying, push a return address, or use it
to enter a more privileged non-conforming segment.

Integration observation, 2026-09-30: after correcting PCAT's RTC periodic
rate, both MiSTer and SPK286-backed 86Box reach a later OS/2 desktop-startup
wait. Exception snapshot 166 shows `0516:0000`, `JMP FAR 0828:0000`, rejected
as #GP(0828). The descriptor `008E 04B6 E400 0000` is a present DPL3 call gate
accessible from the source CPL2; the core rejects its type before resolving
the target. This is an executed instance of H09. The original 86Box 286 reaches
Desktop Manager with a copy of the same image. The authorized H09 correction
now passes 816 cases / 1,704 checks in each simulator, including selector
prechecks, JMP privileges, Accessed writes and #NP/IRET retry. The final
SPK286-backed 86Box trial reached Desktop Manager with Main/Utilities groups
and the DOS icon. The user accepted this startup progress and requested a
clean exit (return code 0). A later report of a hardware-only black screen
is unclassified and awaits debug register evidence; hardware success is not
claimed. See
[OS/2 desktop diagnosis](OS2_DESKTOP_JMP_CALL_GATE_20260930.md) for the coherent
RAM/state captures, hardware video correspondence and reference-run limitations.

### H10 — Target selector RPL in interrupt/trap gates (S, P1)

`descriptor_cs_access_valid` at 641 adds target-RPL conditions for non-conforming
event targets, including target RPL==target DPL on inward transfer. A gate's
target selector RPL is not the caller's privilege check. [I286] chapter 9 and
the INT algorithm distinguish gate DPL, target code DPL and target selector.

Native reference: `x86seg.c::pmodeint`. Vary only the two target selector RPL
bits in an otherwise valid gate; delivery must have the same architectural
result. Independently test software INT's gate DPL check and hardware interrupt
delivery, same/inward privilege transfers and conforming targets.

**2026-10-01 implementation follow-up: H10 corrected.** Ordinary gate target
validation ignores selector RPL while retaining target DPL <= source CPL and
the independent software gate-DPL check. The new 1476-case bank passes in
both simulators, also with PCAT P01/P02/P05, across software INT, INTR, NMI,
conforming code, inward/same-level delivery and subsequent IRET. Existing
event and task-gate controls pass. See [block validation](PROTECTED_MODE_BLOCK_20261001.md).

### H11 — Fault during exception delivery becomes shutdown (S, P0)

`rtl/spk286_events.sv:43/130`, `entry_failure`, sends any fault during an active
event directly to shutdown. It does not select and deliver #DF. The top-level
`fault_error_valid` list at `spk286.sv:1083` also has no vector-8 error-word path.

[I286] 9.6.2 distinguishes contributory first exceptions (#0/#10/#11/#12/#13),
other first exceptions, double fault and failure while delivering double fault.
The #DF frame includes a zero error word. Native `386.c:325` demonstrates an
intermediate `pmodeint_2386(8,0)` step before reset, but its generic fallback is
not the complete Intel 286 classification table.

Specify the delivery state machine and exception-pair table before coding.
Tests must include #GP followed by #NP, a benign first exception followed by a
protection fault, a working #DF task gate, failing #DF delivery, saved context,
zero error code, and NMI/RESET recovery from shutdown. Check CPU bus shutdown
independently of the board adapter's reset response.

**2026-10-01 implemented:** the controller now delivers the second exception
or #DF according to the 286 first-exception rule. #DF carries zero, retains
saved context/EXT provenance and can enter a dedicated task. A failed #DF
entry shuts down; one recovery NMI is permitted, while failure of that NMI
requires RESET. Its required task-gate test also fixed premature completion
of the shared error push. Stale SS instruction shadows are cleared on shutdown
so a failed task handoff cannot inhibit recovery NMI. Both simulators pass
475 controller cases, 26 CPU cases and the affected event/task banks;
33,000 inherited physical event
captures pass. See [H11 specification and receipt](PROTECTED_MODE_H11_DOUBLE_FAULT_20261001.md).
H11 is closed in this scope. H15's wider task-fault stages and H20's separate
event-ordering evidence remain pending.

### H12 — Stack fault routing and selector error metadata (S/C, P0)

`iret_outer_range_fault` feeds generic `range_fault` (micro-executor 265).
The top-level default classifies that source as #GP rather than the required
#SS(0) for an invalid source stack frame. In addition,
`system_fault_error_code` (906) returns raw `call_gate_selector_q` for both
`call_tss_pre_fault` and `call_stack_range_fault`. These failures refer to a
TSS, a stack descriptor or stack bounds, not uniformly to the gate selector.

[I286] 9.6 error-code formats and CALL/INT/RET algorithms define the source,
index/TI/IDT/EXT bits and zero-code cases. Native `loadcscall`, `pmodeint` and
`pmoderetf` supply comparison points. `task_fault_external` also deserves a
separate provenance audit: an event being non-software is not enough explanation
of which Intel EXT rule was applied.

Build a fault-site ledger before changes: stage, instruction/event origin,
vector, error word, saved CS:IP/SS:SP, and permitted earlier side effects.
Test equal descriptors at selectors with different RPL bits to detect accidental
copying of RPL into the error code. Do not reuse a gate selector for unrelated
TSS/stack failures.

**2026-10-01 implementation follow-up: H12 corrected.** Explicit stack-frame
and SS operand-range faults route to #SS(0). Current-TSS failures name TR,
TSS-derived SS access failures use #TS with the new SS selector, absent valid
SS uses #SS(selector), and capacity/parameter faults have a literal zero code.
Selector RPL bits are cleared and EXT now distinguishes external events from
instruction-generated exceptions. A 996-case first-fault ledger passes in
both simulators, also with PCAT options. H14 negative returns now require #SS.
Mixed-invalid predicate priority remains H13; #DF delivery remains H11. See
[block validation](PROTECTED_MODE_BLOCK_20261001.md).

### H13 — Type/privilege versus presence fault priority (S, P0)

The recent direct-call fix correctly separates access validity from presence.
Several sibling paths still choose #NP/#SS whenever `descriptor_valid && !P`
even if type or privilege is also wrong (`system_fault_vector`, 891 onwards).
In `spk286_task_segment_service.sv:195`, `segment_missing` is selected before
`segment_invalid` for a given segment, including a descriptor with a wrong
type/DPL and P=0.

[I286] B-12/B-13 checks incoming SS/CS type and privilege before presence;
the individual load/call/return algorithms likewise state an order. Preserve
the already implemented SS-before-CS-before-ES/DS selection while correcting
the predicate ordering within each descriptor check where required.

Acceptance must deliberately make two conditions invalid at once: wrong type
plus P=0, wrong DPL plus P=0, short table plus bad access byte, bad CS plus bad
SS. Record expected vector/error/state independently for each instruction family.

**2026-10-01 implementation follow-up: H13 corrected.** Separate type/privilege
access predicates now precede presence classification in segment, gate, return,
system and TSS-derived SS paths. Task validation preserves SS -> CS -> ES/DS
ordering while prioritizing invalid access within each segment; valid absent
CS remains #NP. The 1356-case CPU bank passes in both simulators and with PCAT
options, plus 82 new task-service cases and existing related banks. Hidden-cache
publication remains H15. See [block validation](PROTECTED_MODE_BLOCK_20261001.md).

### H14 — Odd stack pointers rejected in protected frame checks (S, P1)

`iret_outer_range_fault` rejects `return_stack_pointer[0]` and
`call_stack_range_fault` rejects `call_stack_sp_q[0]` regardless of range
(1082/1094). 286 word accesses can be unaligned; the documented frame checks
constrain byte ranges, not general even alignment.

Use ordinary and expand-down stacks with odd SP and sufficient room for an
outer RETF/IRET, call-gate frame or interrupt frame. Distinguish valid unaligned
accesses from an actual FFFF-to-0000 operand overrun. Verify both bus byte
cycles as well as the architectural result; do not erase legitimate wrap checks.

**2026-09-30 implementation follow-up: H14 corrected.** Removed only the two
blanket odd-SP predicates. Directed RETF, RETF-immediate, IRET, inward CALL
with parameter copying and interrupt/trap entry/return pass with odd/even SP
and ordinary/expand-down stacks: 216 cases in each simulator. Actual odd words
use paired byte transfers; invalid limits, wrap and frame underflow still reject
without frame writes or architectural stack publication. The negative return
controls also expose H12's known range-vector routing gap (#GP instead of #SS);
H14 certifies their rejection/restart, not their exception-vector conformance.
See [targeted milestone evidence](PROTECTED_MODE_TARGETED_FIXES_20260930.md).

### H15 — Late task-switch hidden-state publication (C, P0)

PM5 already fixed outgoing saves, BUSY transitions, loaded general-register
publication and several late-fault vectors. Those fixes remain in the baseline.
However, the resolution document explicitly delays hidden segment-cache
publication until all segment checks finish. The current task segment service
validates descriptors as a group and commits at `ST_COMPLETE`.

[I286] task-switch B-12/B-13 first invalidates caches, then loads LDTR, SS, CS
and data caches in sequence. A late CS/ES/DS failure may therefore expose a
different subset of valid incoming caches from the SPK286 grouped publication.
It is not sufficient to compare only final registers on successful task switches.

Specify each observable stage and its exception context. Test a valid incoming
SS followed by invalid CS, then valid SS/CS followed by invalid DS/ES, including
delivery through a task gate. Inspect visible selectors, hidden validity,
TR/LDTR, BUSY/backlink, saved outgoing state and handler context. Reuse previous
PM5 evidence without treating its old transactional model as the oracle.

**2026-10-01 follow-up: closed.** Incoming selectors and cache invalidation
now precede LDTR validation; SS, CS and the data caches publish by successful
stage. Late exceptions use incoming CS:IP and earlier cache/Accessed effects
survive. Eighty executable reset-ROM cases cover CALL/JMP/INT/nested IRET in
both simulators, with private native/SPK 86Box before/after observations.
The native interpreter itself differs from Intel's ordered late context;
that conflict is recorded, not copied into the acceptance expectations.
See [H15 contract and receipt](PROTECTED_MODE_H15_TASK_PUBLICATION_20261001.md).
ES-before-DS remains an implementation policy; physical PM evidence and H16
are separate. This supersedes PM5's grouped cache-publication model.

### H16 — Null incoming LDTR with nonzero RPL (C, P2)

`spk286_task_switch_service.sv:416` recognizes only `0000` as a null incoming
LDTR; `0001..0003` take the invalid-selector route. The common selector decoder
and Intel's null-selector definition use index=0 and TI=0, independent of RPL.
The task initialization prose specifically illustrates `0000`, so establish
the task-load rule explicitly rather than relying only on the general definition.

Compare LLDT and task-loaded LDTR for 0000..0007, assert when no table fetch is
allowed, and include incoming CS/SS that require the LDT. Preserve the
distinction between null GDT selector and LDT entry zero.

**2026-10-01 follow-up: closed in the documented null-field scope.** Task loads
now recognize INDEX=0/TI=0 independently of RPL, and LLDT/SLDT preserve the raw
visible selector. Null LDTs perform no entry-zero descriptor read; CS/SS requiring
the disabled LDT fault, while entry zero of a valid LDT remains usable. The
service's raw selector error now removes RPL, matching the CPU executor's already
normalized error. Both simulators and the vendor pass 80 ROMs in baseline/Max
plus affected banks, with native/SPK before/after observations. The general Intel
field definition and the task example are distinct evidence; no physical PM
capture is claimed. See [H16 contract and receipt](PROTECTED_MODE_H16_NULL_LDTR_20261001.md).

### H17 — JMP task-switch NT policy and stale documentation (P, P2)

`spk286_tss_service.sv:169` intentionally preserves incoming NT on JMP, to run
the original Supersoft sequence. Intel's table 8-2 says to clear it. The common
native task-switch routine and the native task-gate JMP caller must be considered
together; the latter explicitly clears NT.

[NT research](PROTECTED_MODE_NT_JMP_RESEARCH_20260913.md), section 5, records the
current compatibility decision. Its opening summary and the older
[PM5 resolution](PROTECTED_MODE_PM5_FINDINGS_RESOLUTION_20260913.md) still describe
the former clear-NT policy. This review identifies those statements as historical;
they must not be used to infer current RTL behavior.

Before changing this policy, run a physical 286 discriminator with incoming
NT=0/1, direct TSS JMP and task-gate JMP, and observe PUSHF without relying on
a subsequent IRET. Keep CALL/INT and nested IRET controls. Software compatibility
evidence and measured silicon evidence must be recorded separately.

### H18 — Processor-extension traps despite a no-287 profile (S, P1; CPU-side scope corrected)

`microcode/source/zzzzzzzzzzzzzzzz_esc.mc` consumes ESC syntax and retires without
testing MSW.EM/TS. Decoder `supported` has no WAIT (9B) path. A legal unsupported
opcode currently stops as a development diagnostic rather than implementing WAIT.

[I286] 10.2, 11.4 and the numerics initialization section require CPU-side
#NM behavior for emulation/lazy context switching: ESC must respect EM/TS;
WAIT's TS test is controlled by MP. The abbreviated WAIT entry is less precise
than that MP explanation. Implementing these CPU traps does not require
implementing 80287 arithmetic.

Specify the EM/MP/TS truth table, instruction restart address, no unintended
operand/port access, CLTS recovery and retry, with absent-NPX behavior defined.
Keep external 287 BUSY/error/operand transfer support a separately scoped task.

**2026-10-01 scope clarification:** the user explicitly does not want an
80287 implementation. H18 is limited to CPU-side ESC/WAIT and #NM behavior
in the no-coprocessor profile. Arithmetic execution and an external 287
interface are outside this story. Software emulation can handle the CPU traps.

**2026-10-01 implementation follow-up:** ESC now checks EM || TS before
ModR/M/displacement; WAIT checks MP && TS and otherwise completes with BUSY
inactive. The existing event engine delivers restartable #NM with no error word.
Directed tests cover PE/CPL, all controls, prefixes, READY, handlers/IRET,
CLTS retry, emulation skip, pause and cancellation. See
[H18 implementation and evidence](PROTECTED_MODE_H18_NPX_20261001.md).
H18's agreed CPU-side scope is closed; full ESC address-validation conformance
is not claimed. The supplemental physical probe exposed a pre-existing D8
boundary failure now explicitly recorded under H19 below.

### H19 — Remaining boundary and restart matrix (C, P1/P2)

The SGDT and RETF regressions cover important boundaries, but cannot certify all
memory instructions. Review LES/LDS, BOUND, ENTER/PUSHA/POPA, far memory pointers,
REP strings/I/O, parameter copying and system-table operands for multiword
prechecks and partial state. `MC_CHECK_RM32` only has a limited wrap check;
actual operand service/cache checks must be traced before declaring a defect.

Required cases: last valid byte/word, limit+1, FFFF crossing, expand-down zero/full
limits, odd addresses, null DS/ES, execute-only CS override, read-only segments,
GDT/LDT entry ending exactly at the table limit, and 24-bit physical-address
wrap. Record whether the 286 permits earlier reads/writes before a later fault;
do not impose universal rollback where Intel describes partial execution.

**2026-10-01 executable finding:** the supplemental D8 no-NPX physical cohort
has 33 real-mode #GP captures at effective offset FFFF. All 33 fail identically
on pre-H18 `3657489` and the H18 CPU, which retires ESC instead. The other 4,967
D8 captures pass. This is a concrete operand-boundary/precheck defect inside
H19, independent of EM/TS trap handling; retain #NM priority when fixing it.
Native 86Box's no-FPU path is also syntax-only and is insufficient as its oracle.
The [H18 evidence](PROTECTED_MODE_H18_NPX_20261001.md) and receipt retain
every failed identity. No exclusion or failure waiver closes this finding.

**2026-10-01 implemented follow-up:** the ESC microprogram now performs the
existing pure `CHECK_RM16` after #NM/address decoding. All 5,000 D8 physical
captures, including the unchanged 33 former failures, pass. Both simulators
also pass 3,849 boundary/lifecycle cases and the inherited 9,079-case H18
matrix. See [H19 ESC contract and receipt](PROTECTED_MODE_H19_ESC_BOUNDARY_20261001.md).
Only this concrete ESC first-word finding is closed; the other H19 boundary
and partial-execution cases above remain pending.

### H20 — Event ordering policies and diagnostics (P/C, P1/P2)

Existing open evidence policies (`failed-iret-nmi`, `sti-old-if`, `fault-tf`,
`rep-zero-count-event-order`) remain open under their recorded phase decisions.
This review does not resolve them or turn functional approval into silicon
certification. See `docs/phase6_evidence.json` and
[Phase 7 policy](PHASE7_FUNCTIONAL_POLICY.md).

Future cases must combine MOV/POP SS shadows, STI with old IF=0/1, faults in
the following instruction, TF, NMI, INTR, repeated instructions and failed IRET.
The adapter logs only the first 256 fault entries per process and resets the
CPU after shutdown; valid BIOS/OS mode-switch resets and later diagnostic traps
can therefore obscure the first divergence. Capture the complete first relevant
context, not merely the final black screen or trap banner.

### H21 — Faulting POP segment advances architectural SP (S + R, P0)

The OS/2 trial captured #GP(0210) at `13A3:33BC`, `POP ES`. The selector word
is at old SS:07FA, but the logged SP and saved outer stack pointer are 07FC.
`microcode/source/zzzzzzzz_segments.mc::POP_SEG` performs POP16 before segment
validation; `stack_arch_write` at micro-executor 233 updates SP because this
instruction does not use the protected-return staging added for RETF/IRET.

[I286] 11.2's restartable segment loads and POP B-83/B-84 require a retry to
operate on the same selector. Native `x86_ops_stack.h:605`, `POP_SEG_OPS`, saves
ESP and restores it if loading the segment fails; `opPOP_SS_w` does likewise.

Specify POP DS/ES/SS with #GP/#NP/#SS failures, ring transitions into handlers,
handler repair and successful retry. On a failed segment validation, retain
the original SP and destination segment/cache; the saved fault IP must point
to POP. A successful retry advances SP exactly once. SS interrupt shadow must
start only on successful loading. Include register/stack alias boundaries and
verify this change does not impose incorrect POP semantics on unrelated forms.

### H22 — Call-gate target with Accessed=0 never completes (S + R, P0; corrected)

The follow-up OS/2 probe captured `CALL FAR` at `0257:214C`, gate `04F8`,
target `007E:0151`. After #NP(`007C`), OS/2 publishes the target descriptor at
`1DE4B8` as `0326 1620 DA1C 0000`: present non-conforming DPL2 code, A=0.
`VALIDATE_CALL_CS` rereads it indefinitely at micro-PC `01DE`.

The descriptor phase-3 transition omitted `call_gate_cs_validation_operation`
from the operations that enter phase 4 to set Accessed. The completion logic
already waited for that write, so valid A=0 targets could never complete.
This is independent of H19: a fresh valid call reproduces it without a boundary
violation or exception restart. H19 remains pending.

[I286] 7.4, printed page 7-11, requires setting A when loading a segment
descriptor. Native `x86seg.c::loadcscall`, 286 call-gate paths, also sets the
target code descriptor's A bit. The correction adds the missing transition,
conditioned on successful target validation, valid offset and A=0.

Directed coverage includes immediate/indirect CALL, GDT/LDT, A=0/1, same-level,
inner CPL0/CPL2 and conforming targets, copied parameters, RETF, READY stalls,
three timing policies, absent-target repair/retry, wrong type and invalid offset.
See [H22 diagnosis and validation](OS2_CALL_GATE_ACCESSED_20260929.md) for
before/after evidence and the integration result. This correction does not
close the remaining protected-mode findings.

## 5. Coverage map and future work packages

The map below records the original review scope. As of the 2026-10-01
H03/H10/H12/H13 block, scoped H18 and H11 corrections, closed findings are H01,
H03, H04, H06, H07, H08, H09, H10, H11, H12, H13, H14, H15, H16, H18, H21 and H22.
The concrete ESC first-word finding in H19 is also closed. Remaining work is
H02 (partial), H05, H17, H19 (remaining matrix) and H20. The downstream PERF01
benchmark investigation is recorded separately in PCAT's hardware follow-ups.
See the marked follow-ups and
[block validation](PROTECTED_MODE_BLOCK_20261001.md) for closure evidence;
the original work packages do not reopen completed findings.

| Domain | Existing support / reviewed areas | Remaining closure |
|---|---|---|
| Entry/reset/MSW | LMSW, one-way PE, CLTS, LOADALL, CPL entry fix, H18 #NM | Physical LOADALL policies remain separate |
| Descriptor tables | GDTR/IDTR, LDTR/TR, SGDT/SIDT, table limits | H01/H05/H16/H19 |
| Segmentation | Cache reload, type/access/limit, null selectors, expand-down | H06/H08/H13/H19 |
| Privileged operations | Partial system-instruction checks | H01/H02/H03 |
| Code transfers and stack state | Direct CALL/JMP, gates, same/outer returns, POP segments | H07/H09/H10/H12/H14/H21 |
| Events | IDT gates, frames, task gates, interrupts and traps | H04/H11/H12/H13/H20 |
| Task management | TSS save/load, BUSY, backlink, TS, late-fault handling | H13/H15/H16/H17 |
| Floating-point interface | CPU-side ESC/WAIT/#NM; no 287 execution | H19 ESC operand boundaries; external NPX interface separately scoped |
| Machine integration | MR BIOS, DOS/Windows experiments, OS/2 disk | Workload evidence below; not an ISA oracle |
| Timing/bus | READY, HOLD/LOCK, instruction timing policy | Architectural results invariant across policies; cycle certification separate |

Suggested work order, to be agreed before implementation:

1. **Capture and reduce the next OS/2 divergence**, then select its exact
   architectural requirement. Avoid repairing a secondary error-reporting path.
2. **Execution context and fault machinery:** H03/H04/H07/H08/H11/H12/H13/H15/H21.
   Treat exception delivery and late task-state publication as explicit staged
   operations with a fault-site ledger.
3. **Protection and instruction completeness:** H01/H02/H05/H06/H09/H10/H14/H18.
4. **Boundary/physical evidence:** H16/H17/H19/H20 and the LSL conflict in H05.

For each work item, first write a small independent expectation table from the
manual, then a failing minimal executable case, then the smallest correction.
Compare the native 286 path where meaningful and report any reference conflict.
After implementation run affected banks, both simulators, lint and the agreed
broader regression. Keep real OS boots as integration checks and record the
image/profile/binary hashes. Do not count newly added test volume as evidence
that untested semantic combinations are correct.

## 6. OS/2 integration evidence from this review

The user authorized a first trial after the documentation-only restriction.
The original `D:/ISOs/MiSTer/IBM_OS2.vhd` is not attached to this run. The copy,
profile, log, screenshots and samples are under
`D:/GitHub/86box_dev/build/spk286/os2-audit-20260929/`.

Initial original/copy SHA-256:
`cd4dfe0440df06d85410c931114e49d1e88a63318762ed10e99bf5882a260901`.
Configuration: MR BIOS 286, 6 MHz, 2 MB, EGA, IDE channel 0:0, geometry
1020 cylinders / 15 heads / 17 sectors. The copied profile has its own NVR
and global settings. Launch used the existing binary and SDL monitor with
`-P` pointing to the copy, `-O` to its own global configuration and `-L` to
`spk286-os2.log`. No rebuild or core change was made.

The trial finished with TRAP 000D. It passed the earlier SGDT and outer-stack
RETF failure sites and reached `13A3:33BC`. The first relevant new fault and
its later reporting fault are recorded in
[OS2_FIRST_TRIAL_FINDINGS_20260929.md](OS2_FIRST_TRIAL_FINDINGS_20260929.md).
The process was paused, its state captured and then exited normally. The
original and copied VHD hashes still matched their initial value afterward.
No fix or new regression was run. Other static findings above are not claimed
as observed causes of this trial.
