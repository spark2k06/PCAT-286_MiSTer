# PM4b.7: Protected `RETF` Restored-SP Limit Rejection

**Historical record, superseded 2026-09-29:** the additional restored-SP
limit check described below was incorrect. Intel's RET algorithm permits
restoring an empty or otherwise out-of-range stack pointer because it does
not access the new stack. OS/2 exposed the error with SP=0800 and limit=07FF.
See [the correction and executable reproducer](OS2_OUTER_RETURN_DIAGNOSIS_20260929.md).
The original implementation and verification record below is retained for
provenance, not as the current architectural contract.

PM4b.7 validates the final outer stack pointer produced by `RETF imm16` after
the saved outer `SS` descriptor has been accepted and before the context
commit. This closes the remaining ordinary expand-up stack-limit hole in the
bounded inter-level return path.

## Acceptance case

The focused bank enters ring 1 with `SS=0069` and limit `FF03`. The two source
parameter words at `FF00` and `FF02` remain readable by the call gate, and the
gate reaches ring 0 with the normal frame. The target then executes `RETF 8`:

- saved outer `SP=FF00` and `imm16=8` produce restored `SP=FF08`;
- the validated outer `SS` limit is `FF03`;
- the return raises #SS before committing the outer `CS:SS:SP` context.

The bank verifies that the current target context remains `CS=0038`,
`SS=0018`, `SP=9FFC` after the already-consumed return frame words.

## Implementation

- Add a late restored-`SP` check against the latched outer `SS` limit.
- Suppress `CONTEXT_COMMIT` when that check fails.
- Classify the failure as #SS and report the saved `SS` selector as the fault
  error word.

## Verification

- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — 19 checks,
  covering PM4b.3 through PM4b.8.
- The PM4b.2 protected-system, far-transfer, event, and stack-control suites
  remain the affected regression set.
- Verilator lint, Yosys synthesis, and a second simulator remain unavailable
  in the current Windows environment; Icarus is the executable validation used
  here.

## Remaining scope

Expand-down stack policy, additional multi-word boundary combinations, and
task-return policy remain outside this bounded increment; PM4b.8 covers the
exact ordinary-stack boundary.
