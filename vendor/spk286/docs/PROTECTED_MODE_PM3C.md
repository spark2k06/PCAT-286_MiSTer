# Protected Mode PM3c — Error-Code Frames and Nested Entry Failure

Status: implemented as a bounded PM3c slice. This increment extends the
same-level PM3 event path with 16-bit protected-exception error-code frames
and verifies the existing shutdown policy when a second fault occurs during
event entry.

## Implemented contract

For protected faults in the current `#TS/#NP/#SS/#GP` family, event arbitration
captures whether an error word is present and preserves its 16-bit value. The
implemented selector-fault sources use the faulting selector; other protected
fault sources in this slice use zero until their individual architectural
classification is added.

The event frame is written in this order:

1. saved FLAGS;
2. saved CS;
3. saved IP;
4. the optional 16-bit error word.

The error word is therefore at the top of the frame for a handler to consume
before a same-level `IRET`. It is conditional: ordinary software, NMI, INTR,
trap and protected events without an error-code classification do not gain an
extra stack word. Stack writes remain normal BIU-owned 16-bit transfers and
honour READY, pause and stack-limit dependencies.

If gate or target validation faults while an event is already active, the
bounded policy enters shutdown and does not commit an invalid handler CS.
Double-fault escalation and a complete 80286 #DF physical policy remain
deferred.

## Verification

`sim/unit/spk286_protected_system_tb.sv` adds directed coverage for a
non-present selector (`0040`): the #NP gate receives one 16-bit error word,
the handler consumes it, and the frame bytes remain observable. It then makes
the same gate target a data descriptor and checks nested event-entry failure
and shutdown without a bad CS commit. The protected bench passes 59 checks in
Icarus, including the inherited PM3d outer-level `IRET` checks; the inherited
PM3a/PM3b Verilator coverage remains unchanged.

Microcode format 18 adds the explicit `PUSH_EVENT_ERROR` operation. The
authoritative source and generated ROM are consistent at 117 entries and 668
words.

Privilege-level stack switching during event entry, call gates, task gates and
full selector/error-code classification remain later milestones. The bounded
outer-level `IRET` return is documented in `PROTECTED_MODE_PM3D.md`.
