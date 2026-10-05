# PM4b.8: Protected `RETF` Restored-SP Limit Boundary

PM4b.8 closes the ordinary expand-up limit boundary for the restored outer
stack pointer. The check must reject a value above the limit while accepting a
value exactly equal to it.

## Acceptance case

The focused bank enters ring 1 with `SS=0069` and limit `FF04`, calls the
existing two-parameter gate, and executes `RETF 4`. The saved `SP=FF00` plus
the immediate allocation produces `SP=FF04`, exactly equal to the limit.

The return is accepted and commits `CS=0061`, `SS=0069`, `IP=0245`, and
`SP=FF04`. This complements PM4b.7, where `RETF 8` produces `FF08` against a
`FF03` limit and is rejected.

## Verification

- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — 19 checks,
  covering PM4b.3 through PM4b.8.
- The PM4b.2 protected-system, far-transfer, event, and stack-control suites
  remain green after the preceding RTL increment.
- Verilator lint, Yosys synthesis, and a second simulator remain unavailable
  in the current Windows environment; Icarus is the executable validation used
  here.

## Remaining scope

Expand-down stack policy, additional multi-boundary combinations, and
task-return policy remain outside this bounded increment.
