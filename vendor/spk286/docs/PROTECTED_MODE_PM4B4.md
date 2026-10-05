# PM4b.4: Protected `RETF` Frame-Range Rejection

PM4b.4 closes the first negative inter-level `RETF` case and prevents a
protected return from reading the saved outer `SP:SS` frame after its bounded
range check has already failed.

## Implemented scope

- Keep the ordinary writable-stack frame precheck ahead of saved outer-frame
  reads.
- Suppress all stack bus requests while the range-fault path is active.
- Preserve the current target `CS:SS:SP` context when the outer frame is
  rejected; no restored `SP:SS` candidate is committed.
- Record the rejection at the existing focused protected-mode bank without
  changing the PM4b.3 positive return contract.

## Acceptance case

The focused bank enters ring 0 through the PM4b.2 two-parameter call gate and
then executes `RETF 4`. The target first reloads `SS` with selector `0050`, a
present writable ring-0 stack descriptor whose limit is `9FFB`. After the
architectural pops, the saved outer `SP:SS` words occupy `9FFC..9FFF`; the
return must therefore fault before reading either word.

The bank verifies that:

- the call gate reaches `0038:0100` with `SP=9FF4`;
- no physical read is issued for the rejected saved `SP:SS` words;
- `CS=0038`, `SS=0050`, and `SP=9FF8` remain uncommitted after the fault;
- the old frame bytes at `9FFC..9FFF` remain unchanged.

The focused testbench deliberately leaves the resulting fault unhandled so
that shutdown provides a deterministic observation point; this is a test
harness boundary, not a claim about final exception-delivery policy.

## Verification

- `bash ./scripts/test_units.sh iverilog spk286_protected_retf` — 62 checks,
  6311 READY stalls, including the PM4b.4 rejection case.
- The PM4b.2 protected-system, far-transfer, event, and stack-control suites
  remain the affected regression set.
- Verilator lint, Yosys synthesis, and a second simulator remain unavailable
  in the current Windows environment; Icarus is the executable validation used
  here.

## Remaining scope

Additional selector/type/RPL and limit-negative cases, expand-down stacks, and
task-return policy remain outside this bounded increment; PM4b.5 and PM4b.6
cover the first saved-SS selector and descriptor-class cases.
