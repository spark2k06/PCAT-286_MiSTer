# PM4b.3: Inter-Level `RETF` with Parameter Discard

PM4b.3 completes the positive bounded return half of the PM4b call-gate slice.
An inter-level `RETF imm16` now reuses the validated outer-frame service used by
protected `IRET`, while applying the 80286 parameter-discard amount to the
restored outer stack pointer. PM4b.4 adds the first negative frame-range case
and closes a bus-safety gap in that path.

## Implemented scope

- Validate the returned `CS` with the protected outer-return rules.
- Read the saved outer `SP` and `SS` from the current stack after the two
  architectural `RETF` pops and the immediate parameter allocation.
- Validate the saved `SS` as the destination privilege-level writable data
  stack, including a single bounded `SP + N + 3` frame-range check for the
  remaining saved `SP:SS` words.
- Perform that outer-frame range check once, before the first saved outer word
  is read, so a valid exact-limit frame is not re-evaluated after `SP` advances
  between bus reads.
- Commit `IP`, `CS`, `SS` and `SP` atomically only after both descriptor checks
  complete.
- Restore `SP = saved_SP + imm16`, so `RETF 4` discards the two parameter words
  copied by PM4b.2.
- Capture a valid SS candidate even when the descriptor accessed bit was
  already set by an earlier protected transition.

## Acceptance frame

The focused Icarus bank enters ring 0 through the PM4b.2 two-parameter call
gate, then executes `RETF 4` at `0038:0100`:

```text
9FF4  old IP = 0245
9FF6  old CS = 0061
9FF8  parameter 1 = 1357
9FFA  parameter 2 = 2468
9FFC  old SP = FF00
9FFE  old SS = 0069
```

The committed result is `0061:0245`, `SS=0069`, `SP=FF04`.

## Verification

- 88 microcode compiler/contract tests pass.
- The generated contract and independent audit pass at 120 entries and 711
  words.
- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` passes 62
  checks, including the PM4b.4 through PM4b.9 limit and selector cases and
  the one/thirty-one-parameter RETF boundaries.
- The existing protected-system PM4b.2 bank remains green at 100 checks.
- Existing far-transfer, event, and stack-control suites are rerun as affected
  regression checks.

## Known limitations

- Expand-down stacks remain outside this bounded slice.
- Broader negative RETF limit coverage, expand-down policy, and task-return
  policy remain later PM4 work.
- Verilator lint, Yosys synthesis and a second simulator are unavailable in
  the current Windows environment; Icarus is the executable validation used
  here.
