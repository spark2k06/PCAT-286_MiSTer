# PM5 independent-review findings resolution — 2026-09-13

This document records the implementation response to
`PROTECTED_MODE_PM5_INDEPENDENT_REVIEW_20260913.md`. The original review is
kept unchanged as the independent-review record; this document records the
follow-up correction state.

## Resolved findings

### Late task-switch effects and IRET save

The task-switch path no longer prefetches and transactionally validates the
incoming TSS image before changing architectural state. The TSS service now
performs the 80286 save/load and BUSY sequencing first. Incoming LDTR and
segment validation runs in the loaded task context, so late faults preserve the
observable partial state expected from the processor. Nested `IRET` uses the
same save path before freeing the returning task.

The micro-executor publishes general registers, FLAGS, TR and LDTR when the
TSS image is loaded, and delays hidden segment-cache publication until the late
segment checks complete.

Covered by:

- `spk286_protected_task_state_fault`: 204 checks, 36 CALL/JMP cases;
- `spk286_protected_task_iret`: 10 checks;
- `spk286_protected_task`: 21 checks.

### Fault vectors, precedence and error metadata

The task-state fault contract now distinguishes:

- short or invalid TSS and invalid/present-state task descriptors as `#TS`;
- a non-present incoming LDT as `#TS`;
- a non-present SS as `#SS`;
- non-present CS/ES/DS as `#NP`;
- an incoming IP beyond CS.limit as `#GP(0)` after the task load.

Segment-fault selection is explicit and ordered SS, CS, ES, DS. Selector error
codes are preserved, with the external-source bit added for event-delivered
faults.

Covered by:

- `spk286_protected_task_fault`: 64 checks, 16 CALL/JMP cases;
- `spk286_protected_task_gate_fault`: 49 checks, 13 cases;
- `spk286_task_segment_service`: 13 checks;
- `spk286_task_switch_service`: 42 checks.

### Error code through an IDT task gate

The task-gate event tail now retains `PUSH_EVENT_ERROR` after the incoming task
commit while suppressing only the stale ordinary interrupt-frame operations.
The new adversarial test raises `#GP(0030)` in one task, dispatches through an
IDT task gate, and checks that `0030` is written to the new task's stack.

Covered by:

- `spk286_protected_task_gate_error`: 7 checks, Icarus + Verilator;
- `spk286_protected_task_gate_event_privilege_outer`: 448 checks, 144 cases,
  Icarus + Verilator.

### JMP NT semantics and BUSY locking

JMP task loads now clear NT regardless of the stored incoming TSS FLAGS value.
The TSS BUSY update exposes a task-service lock request to the BIU, and the
top-level lock request includes it. The HOLD/HLDA test permits the locked task
descriptor update to complete before HLDA is observed.

Covered by:

- `spk286_protected_task_state_fault`: JMP cases and NT checks;
- `spk286_protected_task`: HOLD/HLDA plus task BUSY/LOCK checks;
- `spk286_tss_service`: 38 checks.

## Validation status

Completed successfully:

- Verilator lint and microcode consistency check;
- all focused PM5 service and protected-task tests in Icarus and Verilator;
- `git diff --check`.

The aggregate `make regression` attempt was started twice, but the generated
Verilator C++ build for `spk286_protected_expand_down_tb` exhausted the WSL
environment and was cancelled; the subsequent WSL restart removed its
temporary log. Yosys could not be started afterward because the WSL user
session failed to initialize. These are validation-environment limitations,
not architectural passes, and the aggregate regression and synthesis checks
remain to be rerun in a healthy environment.

This correction does not itself perform a new independent review. PM5 should
remain pending that user-requested review before architectural closure.
