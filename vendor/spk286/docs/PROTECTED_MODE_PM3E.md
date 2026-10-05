# Protected Mode PM3e — Outer-Level Event Entry

Status: implemented as a bounded PM3e slice. This increment extends protected
interrupt/trap-gate entry with a privilege transition to a less-privileged
non-conforming code segment using the active 80286 TSS stack fields.

## Implemented contract

For a protected event whose validated gate target is at a numerically lower
privilege level than the current CPL, the CPU now:

1. validates the IDT gate and obtains its target offset and selector;
2. validates the target code descriptor, including target offset and privilege
   rules for non-conforming and conforming code;
3. reads `SP0/SS0`, `SP1/SS1` or `SP2/SS2` from the current 286 TSS according to
   the target CPL;
4. validates the target writable data stack descriptor;
5. prechecks the complete destination frame before its first write;
6. writes old `SS`, old `SP`, `FLAGS`, old `CS`, old `IP` and an optional
   error code to the new stack; and
7. commits the target CS/SS hidden caches, SP, IP and event FLAGS together,
   with the instruction/trap-gate flag policy applied at commit.

The old context is not installed on the source stack. The TSS stack cursor and
the frame writes remain owned by the existing BIU/READY path, so a stalled
response cannot advance the architectural stack state. A failed TSS, SS,
descriptor or frame-boundary validation faults before a partial destination
frame or context commit.

Real Mode retains its independent event-entry service and IVT frame ordering;
the protected entry service is selected only after PE is set. Software event
DPL checks remain distinct from hardware NMI/INTR qualification.

## Deliberate boundaries

This slice was originally closed with ordinary writable data stack descriptors.
Expand-down event-stack handling is now covered by
[PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md). Task gates, task switching,
full #DF escalation and exhaustive fault-classification evidence remain later
work. Historical timing is not inferred from the additional microinstructions;
READY, TSS, descriptor, frame and queue dependencies remain functional
requirements.

## Verification

`sim/unit/spk286_protected_event_outer_tb.sv` enters CPL1 through an IRET frame,
raises a DPL1 interrupt gate targeting CPL0, and checks the TSS-selected stack,
the complete outer frame, IF clearing and handler execution under deliberate
READY stalls. The focused bench passes 6 checks in Icarus.

The existing protected-system, protected-RETF, event-instruction and event-
lifecycle benches continue to pass. The expand-down event-stack boundary is
covered by `spk286_protected_expand_down`. The authoritative microcode source
and generated ROM contain 120 entries and 711 words.
