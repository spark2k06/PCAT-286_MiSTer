# Protected Mode PM4a — Same-Level Call Gates

Status: implemented as a bounded PM4a slice. This increment adds protected
same-level call-gate dispatch to the existing far-call instruction paths.

## Implemented contract

For `CALL FAR` immediate and memory forms in Protected Mode, the CPU now:

1. resolves the supplied selector as either a direct code descriptor or a
   call-gate descriptor through the existing GDT/LDT descriptor service;
2. checks call-gate reserved form, presence and `DPL >= max(CPL, gate RPL)`;
3. obtains the gate target offset and code selector;
4. validates a present target code descriptor: a non-conforming target uses the
   gate transition privilege rules, while a conforming target requires
   `DPL <= CPL`, ignores the target selector RPL and remains intra-level;
5. pushes the return CS followed by the return IP through the normal stack and
   BIU services; and
6. commits the validated target CS/cache and target IP with the existing queue
   redirect.

The candidate target context is not installed before gate, target-code and
stack validation complete. Direct far calls retain their existing path when
the supplied selector names a code descriptor. No SS change occurs in this
same-level slice.

The integrated gate-fault matrix also covers a reserved-form call gate, a
non-present call gate, a call gate whose target selector names a data
descriptor, and DPL0 gates addressed with RPL1 and RPL3 selectors. These
failures deliver #GP/#NP with the selector error code and do not push a partial
call return frame before the fault frame. A directed CPL1 attempt against the
DPL0 gate also validates the outer fault frame, caller-stack preservation and
return through `IRET`.

Inter-level call gates, TSS privilege-stack selection, parameter copying and
protected far returns across privilege levels are covered by the bounded PM4b
path and its separate cross-phase matrix. The protected expand-down fixture
adds a real CPL2 same-level matrix with 28 cases covering gate DPL/RPL,
presence, the GDT limit and normal, non-readable, conforming, data and
not-present targets. Task gates, task switching and complete target-stack/type/
limit combinations remain deferred. The conforming target case is limited to
the same-level frame path; it does not perform a TSS stack switch.

## Verification

`sim/unit/spk286_protected_system_tb.sv` covers ordinary same-level gate
dispatch plus a conforming target with a deliberately different selector RPL,
including retained CPL/stack and same-level `RETF` restoration. The protected
expand-down bench adds the 28-case CPL2 matrix; its complete directed run
passes 2183 checks in Icarus.

The inherited FAR instruction matrix passes 6,760 cases with 643,216 checks,
and the FAR lifecycle matrix passes 247 cases with 15,982 checks in Icarus.

Microcode format 18 adds `VALIDATE_CALL_GATE` and `VALIDATE_CALL_CS`; the
authoritative source and generated ROM are consistent at 117 entries and 670
words.
