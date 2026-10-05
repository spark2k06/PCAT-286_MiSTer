# PM4b.2: Inter-Level Call-Gate Parameter Copying

PM4b.2 extends PM4b.1 with the 80286 parameter-word copy performed by an
inter-level call gate. The implementation remains a bounded protected-mode
slice: ordinary writable data stacks were the cases covered by the original
increment. Expand-down protected transition stacks are covered by the later
[PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md) slice. Inter-level `RETF` is
now covered by PM4b.3; this document retains the call-gate parameter-copy
contract.

## Implemented scope

- Accept the five-bit parameter count from the validated call-gate descriptor.
- Include the parameter words in the preflight range checks for both the new
  stack and the caller's current SS limit.
- Read the source words through the caller's SS and write them through the
  TSS-selected target SS without changing architectural context early.
- Copy the source words in reverse read order so the committed downward-growing
  target stack contains the original parameter order immediately above the
  return `CS:IP` words.
- Commit the target context only after stack switch, parameter writes, return
  frame writes and all descriptor validation complete.
- Preserve the zero-parameter PM4b.1 path through the same microcode operation.
- Exercise the five-bit count boundaries with one and thirty-one parameters,
  including source-order preservation, complete target-frame placement and
  matching `RETF 2`/`RETF 62` discard amounts.

## Frame contract

For a two-word outer call from `SS:SP = 0069:FF00` to `SS:SP = 0018:A000`,
the final target frame is:

```text
9FF4  old IP = 0245
9FF6  old CS = 0061
9FF8  parameter 1 = 1357
9FFA  parameter 2 = 2468
9FFC  old SP = FF00
9FFE  old SS = 0069
```

The committed target `SP` is `9FF4`. This matches the 80286 downward-growing
stack layout: the last source parameter is read first, then each destination
write moves downward.

## Verification

- `python3 -m unittest discover -s tests -p "test_microcode*.py"` — 88 tests pass.
- `python3 -m tools.microcode.compile_microcode --check` — 120 entries, 711 words.
- `python3 -m tools.microcode.audit_microcode --output build/pm4b2-microcode-audit` — pass.
- `bash ./scripts/test_units.sh iverilog spk286_protected_system` — 100 checks pass; the two-parameter frame, CS-limit demand boundary and PM4 gate-fault matrix are checked under READY stalls.
- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — PM4b.3 through PM4b.9 and the one/thirty-one-parameter boundary bank pass with 62 checks.
- `bash ./scripts/test_units.sh iverilog spk286_far_instructions` — 6760 cases, 648580 checks.
- `bash ./scripts/test_units.sh iverilog spk286_far_lifecycle` — 247 scenarios, 16234 checks.
- `bash ./scripts/test_units.sh iverilog spk286_event_instructions` — 1932 cases, 428443 checks.
- `bash ./scripts/test_units.sh iverilog spk286_event_lifecycle` — 468 scenarios, 48997 checks.
- `bash ./scripts/test_units.sh iverilog spk286_stack_control` — 9128 cases, 1944134 checks.

## Evidence

The parameter count and inter-level stack/frame ordering follow the Intel
80286 Programmer's Reference Manual, section 7 and the call-gate stack-frame
figure. The project records the source provenance in
[`SOURCE_NOTES.md`](SOURCE_NOTES.md).

## Known limitations

- Expand-down protected stacks are not part of the historical PM4b.2 test
  scope; current implementation and cross-phase coverage are documented in
  [PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md).
- PM4b.3 covers bounded inter-level `RETF 4`/parameter-discard plus the
  one-parameter `RETF 2` and thirty-one-parameter `RETF 62` boundary cases,
  PM4b.4 covers ordinary-stack frame-range rejection, PM4b.5 and PM4b.6 cover
  null/mismatched and descriptor-class outer SS selectors, PM4b.7 and PM4b.8
  historically covered restored-SP limit rejection/boundary cases. The
  extra restored-SP rejection was [corrected after the OS/2 capture](OS2_OUTER_RETURN_DIAGNOSIS_20260929.md);
  PM4b.9 covers the
  maximum-count source and target multi-word boundaries. Broader PM4 work and
  additional architectural policies remain later scope.
- Verilator lint, Yosys synthesis, and the second simulator are unavailable
  in the current Windows environment; Icarus is the executable validation
  used here.

## Next smallest increment

Review the remaining PM4 architectural slices and their evidence requirements
without broadening into task switching or machine-level integration.
