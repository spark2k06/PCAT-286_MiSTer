# Protected Mode PM3b — External Events and Same-Level IRET

Status: implemented as a bounded PM3b slice. This increment extends PM3a with
protected NMI/INTR entry coverage and validates the restored CS descriptor
before a same-level `IRET` commits `IP/CS/FLAGS`.

## Implemented contract

Protected same-level `IRET` now:

- acquires the saved `IP`, `CS` and `FLAGS` words in stack order;
- validates the saved CS through the existing protected descriptor service;
- checks the saved IP against the candidate code-segment limit;
- commits the CS hidden cache, restored IP and FLAGS only after validation;
- preserves the Real Mode return protocol when PE is clear.

Protected external events now exercise the PM3a IDT path for:

- NMI vector 02 without software DPL qualification or INTA;
- INTR vector acquisition through the two-cycle INTA protocol;
- same-level interrupt-gate entry followed by a validated same-level IRET.

Inter-level stack changes during event entry and call/task gates remain
deferred. PM3c adds the bounded error-code frame and nested entry-failure
slice documented in `PROTECTED_MODE_PM3C.md`; PM3d adds the bounded outer-level
IRET return documented in `PROTECTED_MODE_PM3D.md`. Double-fault escalation
and the complete physical nested-fault policy remain deferred.

## Verification

`sim/unit/spk286_protected_system_tb.sv` adds three PM3b checks for NMI,
external INTR vector 22 and software INT 22 returning through the protected
same-level IRET path. The bench passes with 55 checks in both Icarus and
Verilator.

The event-instruction matrix remains green with 1,932 cases and 425,011
checks in both simulators. Microcode is regenerated from the authoritative
source and audited as 117 entries and 668 words.

Historical timing remains separate from the functional BIU, READY, frame and
queue dependencies exercised by this slice.
