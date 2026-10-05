# Phase 9D P2 resolution — HLT resume temporal validation

This document closes finding R1/P2 from the independent review of commits
`873fed8` and `999a869`, recorded in
`build/phase9-review-999a869/REVIEW.md`. The implementation snapshot is
`3b0bb7e20ae75b95e707d8132daecc83ae035d51` on
`codex/phase9-timing-tstates`.

The correction is limited to `tools/capture_prefetch_fidelity.py` and its
focused Python tests. No RTL, integrated testbench or capture format was
changed. H4, B1, B2 and B3 remain closed; the full Phase 9 regression, V1 and
historical timing remain pending.

## Temporal contract

For every non-reset row, the validator derives the expected `hlt_resume` value
from the preceding observed row in the same scenario:

```text
previous row: halted=1
current row:  halted=0 and event_active=1
=> current hlt_resume must be 1
```

All other rows must carry `hlt_resume=0`. A reset clears the remembered HLT
state, and a scenario change cannot inherit HLT state from the previous
scenario. Epoch changes without reset do not clear the state, which preserves
the authentic transition at cycle 930. The validator deliberately does not
reject `restart=1`; the real resume row has `restart=1` because entering the
event cancels the old instruction stream.

This exact per-row relation rejects false marks, duplicate marks and missing
marks without encoding a cycle number. It also rejects the review's 845-row
counterexample before the workload summary can be accepted.

The workload validator additionally requires:

- scenario 4 to be present;
- a temporally valid resume marker in scenario 4;
- an active, non-HLT event after the marker; and
- a later HLT in scenario 4, preserving the second-HLT requirement.

The integrated bank still checks the handler's architectural result (`AX=5678h`)
and that execution reaches the second HLT. Those checks remain outside the
CSV summary and were not weakened.

## Focused controls

Added tests cover:

- a valid HLT-to-event transition with `restart=1`;
- a spurious marker without a preceding HLT;
- a missing marker on a real transition;
- a duplicate marker after the transition;
- a marker crossing a scenario boundary; and
- workload rejection when scenario 4 or its second HLT is absent.

The supplied review reproducer now exits nonzero because its old manifests
reference the pre-fix validator hash. Replaying its semantic mutation against
the current authentic capture is also rejected directly:

```text
P2_MUTATION_REJECTED prefetch row 3 HLT resume marker does not match the observed transition
```

The authentic capture remains accepted and reports the real transition at
cycle 930.

## Regenerated evidence

Fresh captures were generated independently after commit `3b0bb7e`:

| Item | Verilator | Icarus |
| --- | --- | --- |
| Manifest | `build/phase9d-p2-verilator/timing/spk286_prefetch_fidelity.json` | `build/phase9d-p2-iverilog/timing/spk286_prefetch_fidelity.json` |
| CSV | `build/phase9d-p2-verilator/timing/spk286_prefetch_fidelity.csv` | `build/phase9d-p2-iverilog/timing/spk286_prefetch_fidelity.csv` |
| Version | Verilator 5.020 2024-01-01 rev (Debian 5.020-1) | Icarus Verilog 12.0 (stable) |
| Source revision | `3b0bb7e20ae75b95e707d8132daecc83ae035d51` | `3b0bb7e20ae75b95e707d8132daecc83ae035d51` |
| Records | 1,190 | 1,190 |
| CSV SHA-256 | `9d56b1d1b6ef47ff9777f2f20aa609b633456b790b12f649eeb97c07f9cc60d1` | `9d56b1d1b6ef47ff9777f2f20aa609b633456b790b12f649eeb97c07f9cc60d1` |
| Input hashes | 63 | 63 |

The validated comparison is cycle-by-cycle identical in both simulators. The
summary remains 55 effective instruction-byte waits, 4 queue-empty fetch
observations without demand, one stale invalidation and one HLT resume at
cycle 930.

## Commands and results

```text
python -m unittest tests.test_capture_prefetch_fidelity -v
  Ran 16 tests ... OK

python -m unittest tests.test_capture_prefetch_fidelity tests.test_timing_calibration tests.test_capture_timing_trace -q
  Ran 58 tests ... OK

bash scripts/lint.sh
  MICROCODE CHECK PASS: 120 entries, 717 words, 10-bit addresses, 8-bit control
  LINT PASS

spk286_fetch: Verilator/Icarus
  FETCH PASS: 26 checks in each simulator

spk286_prefetch_queue: Verilator/Icarus
  PREFETCH_QUEUE PASS: 19 checks in each simulator

spk286_core: Verilator/Icarus
  CORE_STATE_FETCH PASS: 7 checks in each simulator

capture comparison and workload validation
  CAPTURE_COMPARE_PASS records=1190 hlt_resume_cycles=[930]
  demand=55 queue_activity_without_demand=4
```

No global regression was launched. PCAT and machine integration remain outside
this work.
