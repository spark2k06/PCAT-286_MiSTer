# Protected Mode PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g — System Instructions

Status: implemented as seven instruction slices plus the protected privilege
closure. Protected execution, segment validation and protected event entry are
provided by the subsequent PM2–PM4 slices; the system-instruction privilege
and fault boundaries are explicit here.

## Implemented forms

The live `0F` escape path now admits these `0F 01` group forms:

| REG | Form | Operation |
| ---: | --- | --- |
| 0 | SGDT m16:24 | store GDTR limit and 24-bit base |
| 1 | SIDT m16:24 | store IDTR limit and 24-bit base |
| 2 | LGDT m16:24 | load GDTR limit and 24-bit base |
| 3 | LIDT m16:24 | load IDTR limit and 24-bit base |
| 4 | SMSW r/m16 | store MSW |
| 6 | LMSW r/m16 | load MSW; PE is one-way until reset |

`0F 01 /0..3` require a memory ModR/M form. `SMSW` and `LMSW` accept both
register-direct and memory forms. `/5` and `/7` are rejected as invalid forms
in this slice.

The PM1b selector-store forms are also connected through the same path:

| Opcode | Form | Operation |
| --- | --- | --- |
| `0F 00 /0` | SLDT r/m16 | store the visible LDTR selector |
| `0F 00 /1` | STR r/m16 | store the visible TR selector |

The PM1c descriptor-backed load forms are now connected:

| Opcode | Form | Operation |
| --- | --- | --- |
| `0F 00 /2` | LLDT r/m16 | read a GDT LDT descriptor and commit LDTR |
| `0F 00 /3` | LTR r/m16 | read an available GDT TSS descriptor, mark it busy, and commit TR |

The selector is acquired through the normal `r/m16` operand service. The
descriptor is then read as four ordered words from the GDT through the BIU.
LLDT accepts the null selector and invalidates LDTR. LTR requires an available,
present 80286 TSS descriptor; its access byte is written with the busy bit set
before TR commits. In protected mode LLDT and LTR require CPL0; CPL>0 faults
with #GP before descriptor access, and Real Mode retains the existing #UD
boundary. The privilege matrix now exercises both CPL1 and CPL3 fault paths
with same-level protected exception delivery.

The PM1d selector-verification forms are now connected:

| Opcode | Form | Operation |
| --- | --- | --- |
| `0F 00 /4` | VERR r/m16 | set ZF when the selected segment is readable at the current privilege |
| `0F 00 /5` | VERW r/m16 | set ZF when the selected segment is writable at the current privilege |

The selector is acquired through the normal `r/m16` operand service. A valid
selector is resolved through the GDT or the loaded LDT, with the complete
eight-byte range checked before descriptor reads. VERR accepts readable data
and readable code; VERW accepts writable data only. Data and non-conforming
code use `max(CPL,RPL) <= DPL`, while conforming code uses `DPL <= CPL`.
Null, out-of-range, non-present, wrong-class and privilege-negative results
are non-faulting and clear ZF. Real-mode execution raises #UD.

The PM1e descriptor-inspection forms are now connected:

| Opcode | Form | Operation |
| --- | --- | --- |
| `0F 02 /r` | LAR r16, r/m16 | load access rights into the high result byte |
| `0F 03 /r` | LSL r16, r/m16 | load the visible 16-bit segment/system limit |

Both forms acquire the selector through the normal ModR/M operand path and
read the complete eight-byte descriptor through the GDT or loaded LDT. They
require a valid, reserved-bit-clean, present descriptor with `DPL >=
max(CPL,RPL)`. LAR accepts the recognized 80286 descriptor classes; LSL accepts
non-conforming code/data descriptors plus TSS and LDT descriptors. Success sets
ZF and writes only the destination register. A null, out-of-range,
non-present, invalid-type or privilege-negative selector clears ZF without a
fault and preserves the destination. Real-mode execution raises #UD.

The PM1f and PM1g instruction forms are now connected:

| Opcode | Form | Operation |
| --- | --- | --- |
| `63 /r` | ARPL r/m16, r16 | raise the destination RPL to the source RPL when lower; set ZF only when adjusted |
| `0F 06` | CLTS | clear the MSW/CR0 `TS` bit |

`ARPL` is valid only in protected mode and raises #UD in Real Mode or with
`LOCK`. Its source is always the ModR/M register and its destination uses the
normal `r/m16` operand transaction; an adjusted memory destination is written
only after the source/destination comparison completes. `CLTS` is valid in Real
Mode and at protected CPL0. Protected CPL>0 raises #GP; `LOCK` raises #UD in
either mode. Neither instruction modifies FLAGS except that ARPL writes ZF.

## Ownership and transaction contract

The instruction context owns the `0F` escape lifetime. The decoder continues
to select symbolic entries, while the microsequencer only sees the generated
`SYSTEM_*` operations. The micro-executor requests each logical table word or
byte through the existing operand service and BIU, so `READY` stalls retain
the physical owner and bus data.

Table operations are three ordered transfers at EA, EA+2 and EA+4. Loads hold
their candidate limit/base in executor state and commit to
`spk286_protected_state` only after the third response. Stores expose the
architectural value through the same operand write path. A table operand whose
complete six-byte range exceeds the active segment limit faults before the
first data request. The table base is 24-bit; the high byte is transferred as
one byte.

Descriptor-backed LLDT/LTR operations perform a complete GDT eight-byte
descriptor read at the selector-derived address. The selector must name the
GDT and its full descriptor range must fit within GDTR without 24-bit address
carry. No LDTR/TR state is committed before the final descriptor response;
LTR adds the descriptor access-byte write as the final transaction. Invalid,
non-present, wrong-type and real-mode forms raise the current system fault
path without a partial cache commit.

Descriptor-backed VERR/VERW/LAR/LSL operations use the same ordered BIU reads
but do not modify descriptor state. The final descriptor response is the only
commit point for ZF/result writeback, and negative inspection never produces a
protection fault.

`SMSW` and `LMSW` use one normal operand transaction. `LMSW` suppresses the
operand service's ordinary register writeback and sends only the captured word
to the protected-state owner with mask `000Fh`. The state owner applies the
80286 rule that PE can be set but not cleared until reset. `SMSW` reads the
full MSW and writes it through the normal destination register/memory channel.
In protected mode LGDT, LIDT, LMSW, LLDT and LTR are CPL0-only; a denied load
raises #GP before its table, descriptor or MSW transaction begins.

`ARPL` performs its Real/Protected-mode and `LOCK` precheck before requesting
the operand service. Its ZF update and adjusted destination write are committed
from the same completed comparison. `CLTS` uses a masked protected-state write
of bit 3 only, so PE and all other MSW bits remain unchanged.

## Deliberate non-goals

This slice does not claim task switching or complete protected-mode fault
nesting. Those remain ordered PM5 work and must preserve the same BIU and
commit-owner boundaries. The current PM1 descriptor-class, table-origin and
CPL boundary matrix is complete for the implemented 80286 system-instruction
families; no system-instruction family remains disconnected from its required
CPL boundary.

## Verification

The focused `spk286_protected_system` bench covers the PM1a–PM1e forms through
the integrated core, including table layout, atomic commits, MSW one-way PE,
selector stores, descriptor-backed LLDT/LTR and GDT/LDT VERR/VERW/LAR/LSL
outcomes. `spk286_arpl` adds five integrated ARPL checks, including register and
memory destinations, ZF-only updates, Real-Mode #UD and READY stalls.
`spk286_clts` adds five Real-Mode/CPL0 CLTS checks, and
`spk286_clts_privilege` now passes thirteen checks covering protected CPL1 and
CPL3 #GP paths, `LOCK` #UD, and LGDT/LIDT/LMSW/LLDT/LTR privilege boundaries.
The integrated system bench also covers LLDT null/unload, wrong-type LLDT
rejection, and busy-LTR rejection without hidden-state or descriptor-byte
changes. Its PM1 selector-inspection bank adds 388 CPL0 checks covering
VERR/VERW/LAR/LSL across DPL0..DPL3, RPL0..RPL3, writable/read-only data,
readable/non-readable code, not-present descriptors and the exact GDT-limit
overflow. The LLDT/LTR matrix adds 49 CPL0 checks for valid, not-present,
wrong-type, busy, DPL/RPL, LDT-origin and GDT-limit cases. The bench passes
537 checks in Icarus with deliberate READY stalls.
The protected expand-down bench adds the equivalent CPL1 selector-inspection
matrix: 352 checks across the same DPL/RPL/type/presence and GDT-limit cases,
and the equivalent CPL3 matrix adds another 352 checks through a real
outer-level transition. The CPL2 selector-inspection matrix adds 448 checks
through a real outer-level `IRET`, covering normal/expand-down data, code
types, presence and the GDT-limit boundary. Together with the later CPL2 PM2
segment, PM2b far-CS, PM3 event, PM4a same-level and PM4b call-gate matrices,
it brings the combined bench to 2183 checks in Icarus.
No system-instruction family is disconnected from its required CPL boundary;
the remaining PM1 work is limited to future evidence or architectural
extensions outside the implemented system-instruction families, rather than a
new execution path.
