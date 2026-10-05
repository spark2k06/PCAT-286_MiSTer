# Protected Mode PM3a — IDT Lookup and Same-Level Event Gates

Status: implemented as a bounded PM3a slice. This increment connects protected
event entry to the IDTR and supports same-level 80286 interrupt and trap gates.
It does not claim privilege-level stack switching, inter-level/task call gates,
outer-privilege IRET or complete nested-fault recovery.

## Implemented contract

Protected event entry now:

- checks that `IDTR.base + vector * 8 + 7` is within `IDTR.limit` before any
  gate bytes are consumed;
- reads the complete eight-byte gate through the normal operand/BIU channel;
- accepts only present, reserved-form-valid interrupt (`type 6`) or trap
  (`type 7`) gates;
- applies the gate DPL rule to software `INT` requests without applying that
  software-only check to faults, NMI or INTR;
- validates the gate target selector through the existing protected CS
  descriptor service and keeps target CS/IP/cache commit atomic;
- builds the protected same-level frame in FLAGS, CS, IP order before the
  target context commit;
- clears TF for both gate types, clears IF for interrupt gates and preserves
  IF for trap gates;
- reports IDT/gate/target failures as #GP or #NP according to the candidate
  state, with the existing bounded event-entry failure policy retained for a
  fault raised while an event is active.

Real Mode keeps the existing IVT path through the same microcode entry. The
new gate operations therefore do not change the real-mode event contract.

## Verification

`sim/unit/spk286_protected_system_tb.sv` covers the IDT-backed vector 0D fault
path and software INT 20h/21h using interrupt and trap gates. The latter checks
same-level CS/offset dispatch and the distinct IF/TF results. It also covers a
same-level event targeting conforming code, with normalized CS RPL, unchanged
SS/CPL and a returning `IRET`. The current integrated bench passes 100 checks in
Icarus; the PM3a-specific additions contribute seven checks. The focused
expand-down bench now includes 89 PM3 event checks: the original eight
CPL0/CPL1/CPL3 gate, target-presence and IDTR-limit cases, a 55-case
CPL0/CPL1/CPL3 target/gate matrix, and a 34-case CPL2 target/gate matrix
covering real TSS stack descents and CS-limit preflight. The outer-level cases
exercise the existing PM3e TSS-stack path; they do not claim task-gate closure.

Microcode format 18 adds `VALIDATE_EVENT_GATE`, `EVENT_GATE_IP`,
`EVENT_GATE_CS` and `CLEAR_EVENT_FLAGS`; generated artifacts and the active
Phase 8 contract are regenerated from the authoritative `.mc` source.

## Deferred PM3 work

Task gates, task switching, complete error-code frame policy and
evidence-backed nested-fault/shutdown behavior remain later work. External
NMI/INTR and same-level IRET are documented separately in
`PROTECTED_MODE_PM3B.md`; the bounded outer-level event path is documented in
`PROTECTED_MODE_PM3E.md`.
