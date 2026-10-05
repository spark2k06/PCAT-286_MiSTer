# Phase 9B/9C audit resolution — 2026-09-15

This document records the implementation response to
`PHASE9B_9C_AUDIT_2026-09-15_3018a9c.md`. The audit remains historical; this
file records the verified work after commits `34be41f` and `14259ef`.

## B3 and evidence preservation

The calibration validator now checks the per-interval identity:

```text
biu_busy_cycles == accepted_transfers + ready_wait_cycles
```

It does not combine this partition with operand, prefetch or queue counters,
which may overlap. The CSV reader now checks the original row length before
normalizing fields, so both empty and non-empty overflow fields are rejected.
The real `main()` flow captures both simulator outputs before parsing them;
identical invalid simulator files therefore fail before any success manifest
can be published.

Raw evidence is always written below a simulator-specific `phase9b-*`
directory, including single-simulator runs. The manifest identifies each
baseline/extra file relative to itself, records its repository-relative path
when available, computes its own SHA-256 and reports six records. The combined
CSV remains a separate twelve-record product.

## Verification performed

The focused Python suites passed:

```text
python3 -m unittest tests.test_timing_calibration tests.test_capture_timing_trace -v
42 tests: PASS
```

The following also passed on the WSL `Ubuntu-24.04` environment:

```text
bash scripts/lint.sh
LINT PASS
```

The final 9B calibration capture was generated with commit `14259ef` and both
simulators:

- combined CSV: `build/phase9-final-calibration/timing/spk286_timing_calibration.csv`, 12 records, SHA-256
  `04d1ceee15296dd628b4de1c897c71bc902c5f0258f1dfad11172e1d7ec50c6a`;
- each Verilator/Icarus baseline bank: 6 records, SHA-256
  `164a8623a41322377ff5cbec8d24ab871743f098bf214270bceed67f342bc864`;
- each Verilator/Icarus extra bank: 6 records, SHA-256
  `cb2c175f7378bbd08800244ce0a1fdf4a7ecb9226635d562fe9d8c9746a243b6`.

## `operand_wait_cycles` investigation

The historical comparison at commit `eb6f2d0` first differed at trace row and
cycle 20. Only `operand_wait_cycles` differed; the external bus fields and all
other published counters were equal. That capture reported final values 2 for
Verilator and 4 for Icarus.

The same RTL/support input hashes were rebuilt in the correct WSL distribution,
with separate build directories and fresh binaries. The clean manifests now
record:

- Verilator 5.020 (Debian 5.020-1);
- Icarus Verilog 12.0 stable;
- 221 records for each simulator;
- identical complete CSVs and SHA-256
  `34b49a77ec3f2cda19d3fce60136cd484bea21cee21316669384452a73d392bd`;
- final `operand_wait_cycles=2` in both captures.

The older manifest identified its Icarus executable as a different `12.0
devel` build (`s20150603-1539-g2693dd32b`). Its VVP artifact also references
the Linux Icarus VPI path and cannot be executed by the Windows runtime. The
discrepancy is therefore classified as a non-reproducible tool/build artifact,
not as a demonstrated RTL or bank-sampling defect. No simulator-specific
normalization or functional RTL workaround was added.

The capture bank now contains an independent per-edge model. It derives an
effective memory wait from the admission handshake or an outstanding response
handshake, explicitly rejects unknown classifications, and compares the model
counter with the RTL counter after each sequential update. It passes in both
simulators.

## Scope remaining open

H4, B1, B2, B3 and the twelve 9B classes remain closed at their documented
scope. V1 (`call-stack-precheck`) remains independently open for global Phase 9
closure. The full regression remains deferred by decision until the end of
Phase 9. Historical native `T1/T2/T3/Tw/T4` timing, named frequency profiles,
the remaining Phase 9D prefetch matrix and downstream integration evidence are
not closed by this work.

The next focused increment is the planned prefetch/instruction-unit fidelity
matrix: linear refill, queue thresholds, redirects/flushes, starvation and
odd-entry behavior, using the existing queue/fetch/core banks before any
historical timing claim is made.
