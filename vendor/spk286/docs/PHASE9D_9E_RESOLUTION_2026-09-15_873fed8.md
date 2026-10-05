# Phase 9D/9E review resolution — 2026-09-15

This document resolves the D1 and D2 findings from
`PHASE9D_9E_REVIEW_2026-09-15_0c92920.md` and records the completed HLT
resumption coverage. The implementation snapshot is
`873fed80872f63b0e046cbd129ce6eafc0562b25` on
`codex/phase9-timing-tstates`. The historical matrix and prior audits remain
unchanged.

The work is limited to the integrated Phase 9D observation bank, its capture
validator and focused tests. No RTL file was changed. Timing policy remains
`0`, `normalized-functional-baseline`; this evidence does not claim historical
80286 cycle accuracy.

## Findings resolved

| Finding or requirement | Status | Resolution and proof |
| --- | --- | --- |
| D1 — odd-address memory adapter | Verified | `sim/unit/spk286_prefetch_fidelity_tb.sv` now forms every aligned memory word from the two bytes in the same even/odd pair. Scenario 2 redirects to odd IP `0301h` and uses distinct neighboring bytes (`A0 B8 78 56 F4`); the execution path reaches the target result `AX=5678`. Running the former `{memory[A+1],memory[A]}` adapter as a temporary uncommitted mutant terminates with `redirect consumed bytes from the old stream` and exit status 1. |
| D2 — instruction wait classification | Verified | The capture publishes the effective execution/demand signals and defines `byte_demand` only for an executable, non-event, non-operand-blocked, empty-queue state that actually needs a byte. Queue-empty fetch activity is retained as a separate observation. The final captures contain 55 effective byte-demand samples and 4 queue-empty/fetch-activity samples without a demand. |
| HLT re-entry/resumption | Verified | Scenario 4 executes `HLT`, injects NMI through vector 2, executes a handler that writes `AX=5678`, and reaches a second `HLT`. The capture records one transition into the resumed event path and the validator requires it. |
| H4, B1, B2 and B3 | Remain closed | No regression was found. Their existing contracts and evidence were not reopened. |
| 9E policy baseline | Independent | The existing policy-0 baseline remains valid. No Accurate/Fast/Max historical claim was added by this increment. |

## Regenerated evidence

Verilator and Icarus were run independently in separate build directories from
the clean implementation snapshot. Each manifest preserves the simulator
identity, source revision, clean-tree status, compiled-input hashes, trace hash
and record count.

| Item | Verilator | Icarus |
| --- | --- | --- |
| Manifest | `build/phase9d-evidence-verilator/timing/spk286_prefetch_fidelity.json` | `build/phase9d-evidence-iverilog/timing/spk286_prefetch_fidelity.json` |
| Original CSV | `build/phase9d-evidence-verilator/timing/spk286_prefetch_fidelity.csv` | `build/phase9d-evidence-iverilog/timing/spk286_prefetch_fidelity.csv` |
| Simulator | Verilator 5.020 2024-01-01 rev (Debian 5.020-1) | Icarus Verilog 12.0 (stable) |
| Records | 1,190 | 1,190 |
| CSV SHA-256 | `9d56b1d1b6ef47ff9777f2f20aa609b633456b790b12f649eeb97c07f9cc60d1` | `9d56b1d1b6ef47ff9777f20aa609b633456b790b12f649eeb97c07f9cc60d1` |

The two CSVs compare equal row by row after schema validation. Their summaries
are identical:

| Observation | Result |
| --- | ---: |
| Scenarios | 1, 2, 3, 4 |
| Maximum queue occupancy | 6 |
| Effective instruction-byte demand | 55 |
| Queue-empty fetch activity without demand | 4 |
| Operand-wait samples | 17 |
| READY-low data-wait samples | 8 |
| Stale-stream invalidations | 1 |
| HLT-resume observations | 1 |
| HLT reached | yes |

The manifests reference the correct simulator-specific CSV path. The CSVs are
kept separate; no original capture was overwritten by a combined result. The
input-hash map in each manifest includes the RTL, generated microcode,
microcode sources/compiler, testbench, signal include, source list and capture
tools.

## Validator and negative controls

`tools/capture_prefetch_fidelity.py` validates the additional fields before
publishing a manifest. It keeps queue-empty fetch activity distinct from real
EU byte demand and checks that `instruction_wait` is exactly the effective
demand classification. `tests/test_capture_prefetch_fidelity.py` contains
independent positive and negative controls; the negative queue-activity case is
rejected while the effective-demand case is accepted. Existing malformed-byte,
lost/duplicated-byte, stale-invalidation and inconsistent-transition controls
remain active. These synthetic rows are validator controls, not CPU captures.

## Commands and actual results

```text
python -m unittest tests.test_capture_prefetch_fidelity tests.test_timing_calibration tests.test_capture_timing_trace -v
  Ran 51 tests ... OK

bash scripts/lint.sh
  MICROCODE CHECK PASS: 120 entries, 717 words, 10-bit addresses, 8-bit control
  LINT PASS

scripts/test_units.sh verilator spk286_prefetch_fidelity
scripts/test_units.sh iverilog spk286_prefetch_fidelity
  PREFETCH FIDELITY PASS; both produce 1,190 records and hlt_resume=1

scripts/test_units.sh verilator/iverilog spk286_fetch
  FETCH PASS: 26 checks in each simulator

scripts/test_units.sh verilator/iverilog spk286_prefetch_queue
  PREFETCH_QUEUE PASS: 19 checks in each simulator

scripts/test_units.sh verilator/iverilog spk286_core
  CORE_STATE_FETCH PASS: 7 checks in each simulator

python capture comparison and workload validation
  CAPTURE_COMPARE_PASS records=1190 instruction_wait=55
  queue_activity_without_demand=4 hlt_resume=1
```

The temporary D1 mutant was intentionally not committed. It failed the
integrated Icarus bank at scenario 2, proving that the odd-address fixture
detects the original adapter construction rather than merely documenting the
correct one.

## Remaining work

The functional 9D matrix is verified for the covered cases, including HLT
resumption. Historical prefetch timing, native T-state equivalence and the
Accurate/Fast/Max implementation remain separate work. V1
(`call-stack-precheck`) remains pending for the global Phase 9 closure. The
complete regression remains intentionally deferred until the end of Phase 9.
The next independent increment may continue with the planned 9E policy work;
PCAT and machine integration are outside this change.
