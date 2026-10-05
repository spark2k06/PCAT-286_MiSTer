# Phase 9C normalized BIU contract evidence — 2026-09-15

This record covers the first 9C focal increment from commit
`eb6f2d0`. It is a normalized CPU-boundary observation, not a physical
80286 pin trace or a historical T-state certification.

## Checks and captures

| Check | Result |
| --- | --- |
| `spk286_timing_capture` / Verilator | PASS; 221 records, 9 accepted transfers, 4 READY waits |
| `spk286_timing_capture` / Icarus | PASS; 221 records, 9 accepted transfers, 4 READY waits |
| Existing CSV validator | PASS for both captures |
| `make timing-trace` | PASS; Verilator manifest written |
| Python focused suites | PASS; 35 tests |
| Verilator trace SHA-256 | `34b49a77ec3f2cda19d3fce60136cd484bea21cee21316669384452a73d392bd` |
| Icarus trace SHA-256 | `dea36c53ff59bcd4a73feecbe2dab9dbdfb34d9dd4d910f1b8a86d4510a8b7aa` |

The real CPU capture checks idle metadata, active status/owner mapping, the
complete even/odd lane rule, READY/phase consistency, continuity of a pending
transaction and stable write data during a wait and its completion. Read data
is intentionally not required to remain stable before READY. The workload
also reaches HLT, exercises READY waits and observes the implicit XCHG LOCK.

The 9B calibration was regenerated from the current HEAD with both simulators:
12 records, equal Verilator/Icarus calibration outputs, and combined CSV
SHA-256 `04d1ceee15296dd628b4de1c897c71bc902c5f0258f1dfad11172e1d7ec50c6a`.

## Simulator observation boundary

The two 9C trace CSVs have the same number of rows and the same external bus
and architectural observations, but their internal `operand_wait_cycles`
counter differs after the data operation: the Verilator capture reports the
shorter normalized count while Icarus reports the longer one. This is recorded
as an observation/tool scheduling discrepancy, not silently normalized and not
treated as evidence of a CPU functional failure. The 9C workstream therefore
remains open for a simulator-independent definition or physical reference for
that counter.

## Scope boundary

H4 remains closed and the 9B suite retains exactly twelve classes. Native
`T1/T2/T3/Tw/T4`, physical bus traces, historical frequency profiles and the
remaining 9C matrix (I/O, INTA, HOLD/HLDA, reset/cancellation and native
wrapper) remain pending.
