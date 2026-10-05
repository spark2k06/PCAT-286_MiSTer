# PM4b.5: Protected `RETF` SS Selector Rejection

PM4b.5 extends the bounded negative inter-level return matrix with saved-stack
selector validation. A failed outer `SS` validation must not commit the
restored privilege context or stack pointer.

## Implemented scope

- Exercise a null saved `SS` selector after the outer frame has been read.
- Exercise a present writable stack selector with a DPL/RPL mismatch against
  the returned code privilege level.
- Verify that both failures preserve the target `CS:SS:SP` context.
- Keep the PM4b.3 positive return and PM4b.4 frame-range rejection contracts
  unchanged.

## Acceptance cases

The focused bank re-enters ring 0 through the PM4b.2 two-parameter gate for
each case, then changes only the saved `SS` word at `9FFE` before executing
`RETF 4`:

- `SS=0000`: null-selector rejection;
- `SS=0018`: present writable ring-0 stack rejected for the returned ring-1
  `CS=0061`.

Both cases verify that `CS=0038` and `SS=0018` remain in force when the
unhandled protected fault reaches the testbench shutdown point. The working
`SP` is `9FFC`: the two architectural `RETF` pops and the saved outer `SP:SS`
reads have completed before the late saved-`SS` validation fails, while no
restored outer `SP` candidate is committed.

## Verification

- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — 9 checks,
  including PM4b.3, PM4b.4, null-SS, and privilege-mismatch cases.
- The PM4b.2 protected-system, far-transfer, event, and stack-control suites
  remain the affected regression set.
- Verilator lint, Yosys synthesis, and a second simulator remain unavailable
  in the current Windows environment; Icarus is the executable validation used
  here.

## Remaining scope

Additional invalid types, non-present selectors, table-indicator cases,
expand-down stacks, and task-return policy remain outside this increment;
PM4b.6 covers the first non-present, wrong-type, and `TI=1` cases.
