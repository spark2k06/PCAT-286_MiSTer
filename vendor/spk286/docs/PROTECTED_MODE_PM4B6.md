# PM4b.6: Protected `RETF` Descriptor-Class Rejection

PM4b.6 completes the immediate saved-`SS` descriptor-class cases for the
bounded inter-level `RETF` return path. It keeps rejected descriptor forms
from installing an outer privilege context.

## Acceptance cases

The focused bank re-enters ring 0 through the existing two-parameter gate and
changes only the saved `SS` word before executing `RETF 4`:

- `SS=0020`: valid descriptor form but not present;
- `SS=0028`: present code descriptor, rejected as a stack selector;
- `SS=000D`: `TI=1` selector while no valid/present LDT is loaded.

Each case reaches the protected return target at `0038:0100` with `SP=9FF4`,
then faults after the outer frame reads while preserving `CS=0038`,
`SS=0018`, and the working `SP=9FFC`. No restored outer `SP:SS` candidate is
committed.

## Verification

- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — 15 checks,
  covering PM4b.3 through PM4b.6.
- The PM4b.2 protected-system, far-transfer, event, and stack-control suites
  remain the affected regression set.
- Verilator lint, Yosys synthesis, and a second simulator remain unavailable
  in the current Windows environment; Icarus is the executable validation used
  here.

## Remaining scope

Additional limit-boundary cases, expand-down stacks, and task-return policy
remain outside this bounded increment; PM4b.7 and PM4b.8 cover the rejected
and exact restored-SP ordinary-stack boundaries.
