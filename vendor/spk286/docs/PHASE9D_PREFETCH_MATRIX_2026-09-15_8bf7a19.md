# Phase 9D functional prefetch matrix — 2026-09-15

This document records the Phase 9D functional increment at snapshot
`8bf7a19c0a94c5e06a18207f7cbee94975f181b6` on branch
`codex/phase9-timing-tstates`. It extends the earlier focused evidence without
rewriting it. The results use timing policy `0`,
`normalized-functional-baseline`; they do not claim historical 80286 cycle
accuracy.

## Evidence identity

The integrated capture was compiled and run independently with Verilator and
Icarus in separate build directories. Both simulators produced the same
normalized 845-row capture.

| Item | Verilator | Icarus |
| --- | --- | --- |
| Manifest | `build/phase9d-final-verilator/timing/spk286_prefetch_fidelity.json` | `build/phase9d-final-iverilog/timing/spk286_prefetch_fidelity.json` |
| Original trace | `build/phase9d-final-verilator/timing/spk286_prefetch_fidelity.csv` | `build/phase9d-final-iverilog/timing/spk286_prefetch_fidelity.csv` |
| Trace SHA-256 | `d88cbcc8740cd9dc2e6e23d7c57cd083f6e744e2f3857b85f71d8af837fb528c` | `d88cbcc8740cd9dc2e6e23d7c57cd083f6e744e2f3857b85f71d8af837fb528c` |
| Records | 845 | 845 |
| Tool version | Verilator 5.020 2024-01-01 rev (Debian 5.020-1) | Icarus Verilog 12.0 (stable) |

The manifests contain the source revision, clean-tree status, all compiled
and support-input hashes, trace path, trace hash and record count. The input
set includes the generated microcode, RTL, testbench, capture tool, source
lists and microcode compiler. No generated or original capture was overwritten
by the comparison.

Summary of the integrated workload:

| Observation | Result |
| --- | ---: |
| Scenarios | 3 |
| Maximum queue occupancy | 6 |
| Instruction-byte wait samples | 48 |
| Operand/bus wait samples | 6 |
| READY-low data-wait samples | 2 |
| Stale-stream invalidations | 1 |
| Accepted code responses | 36 |
| Consumed instruction bytes | 56 |
| HLT reached | yes |

## Functional matrix

The status in this table is for normalized functional behavior. “Pending” is
not a pass and is retained where the current evidence does not exercise the
requirement. “N/A” is used only where the requirement is historical rather
than functional for this increment.

| Requirement | Status | Test and evidence |
| --- | --- | --- |
| Linear refill | Verified | `spk286_prefetch_fidelity`, scenario 1, plus `spk286_fetch` and `spk286_prefetch_queue`; final traces above. |
| Current RTL refill threshold | Verified | The capture records `fetch_request_internal`; the validator requires queue occupancy `<= 4` whenever the current refill request is asserted. This validates the implemented contract, not a historical timing threshold. |
| Empty, partial and full queue | Verified | Integrated scenarios observe an empty queue and maximum occupancy 6; `spk286_prefetch_queue` verifies partial/full transitions and rejects overfill. |
| Simultaneous consume/refill, pointer wrap and response in flight | Verified | `spk286_prefetch_queue` (19 checks) and the independent reference queue in the integrated capture. |
| No loss, duplication or overflow | Verified | The integrated model is derived from accepted code-bus transfers and response handshakes, then checks every consumed byte; malformed, altered-byte, inconsistent-transition and stale-response controls are rejected by `tests.test_capture_prefetch_fidelity`. |
| Even/odd entry and word/byte selection | Verified | `spk286_fetch` (26 checks) and the integrated response model validate lane selection and byte assembly. |
| Byte order delivered to execution | Verified | Integrated model derives expected bytes from accepted bus data and compares every accepted queue consumption; target program reaches the expected architectural values. |
| Segment-limit boundary and no out-of-limit access | Verified | `spk286_fetch` covers last valid byte, last even byte and rejection beyond the limit. |
| Redirects with different queue occupancy | Verified | `spk286_core` (7 checks) and integrated scenario 2 use a distinct target stream. |
| Redirect while an old request waits for READY | Verified | Integrated scenario 2 holds the old code request with READY low, redirects, drains/cancels the old stream and reaches the target HLT. |
| Queue flush, stale-response drain and new-flow start | Verified | Integrated scenario 2 records one stale-stream invalidation; `spk286_fetch` covers restart/cancellation and response backpressure. |
| Reset and cancellation in relevant states | Verified | `spk286_fetch`, `spk286_core` and all three integrated scenarios reset between epochs; reference state is explicitly cleared per epoch. |
| HLT reached after refill and execution | Verified | All integrated scenarios reach HLT; HLT is represented separately from queue-empty and instruction-byte wait. |
| HLT re-entry/resumption through a supported mechanism | Pending | This capture does not exercise an interrupt or other supported resume path after HLT. No result is inferred from reaching HLT. |
| EU consumption faster than refill | Verified | Integrated scenario 3 records 48 instruction-byte wait samples while the queue is empty and the CPU is not waiting for operands. |
| Real lack of instruction bytes | Verified | `instruction_wait` requires empty queue, non-HLT state and an active/pending fetch condition; the validator rejects a misclassified wait. |
| Operand/bus wait distinguished from instruction-byte wait | Verified | Integrated trace records both `instruction_wait` and `operand_wait`; the validator rejects overlap that would misclassify an empty-queue wait. |
| Data traffic during refill | Verified | Scenario 1 executes `XCHG [0200],AX`; the integrated capture records non-code traffic and READY waits while the code path is active. |
| Recovery after READY starvation | Verified | Scenario 3 holds READY low, then releases it and reaches HLT without consuming bytes outside the independent model. |
| Prefetch does not displace an owned data transaction | Verified | `spk286_biu` (2419 checks) verifies arbitration and ownership; the integrated workload also observes data traffic during refill. |
| LOCK restriction | Verified | `spk286_biu_hold_lock` (13 checks) and `spk286_xchg_hold_lock` (47 checks) pass in both simulators. |
| HOLD/HLDA boundary and resumption | Verified | `spk286_biu_hold_lock` and `spk286_biu_width_io` (2851 checks) pass in both simulators, including retention and release at legal boundaries. |
| Refill continuation after ownership release | Verified | The BIU ownership banks verify resumption after locked/HOLD transactions; no prefetch request is used to steal ownership. |
| Historical refill thresholds, native bus phases and exact cycles | N/A for this increment | No physical trace is present. The capture deliberately uses policy 0 and records functional dependencies, not invented historical delays. |
| Accurate/Fast/Max historical equivalence | N/A for this increment | Phase 9E must define and validate these profiles separately; the current trace policy remains the normalized baseline. |

## Reference model and negative controls

`sim/unit/spk286_prefetch_fidelity_tb.sv` maintains its own byte queue and one
pending response. It derives expected bytes only from accepted code-bus
transfers, lane information and response handshakes. It does not read the DUT
FIFO storage as an oracle. It also records reset epochs, the sampled
pre-edge/post-edge model counts, response metadata, invalidation and the
current refill request.

`tools/capture_prefetch_fidelity.py` reads the CSV with `csv.reader` and
rejects wrong headers, incomplete rows and extra fields before normalization.
The focused Python tests independently reject:

- an altered consumed byte;
- an inconsistent queue transition;
- stale invalidation without a restart;
- an expected byte without a consume event; and
- two captures that differ after parsing.

These synthetic rows are parser/validator controls only; they are not CPU
captures. The manifests are published only after the source tree and all
input hashes are rechecked.

## Commands and results

The following focused checks passed:

```text
python -m unittest tests.test_capture_prefetch_fidelity tests.test_timing_calibration tests.test_capture_timing_trace -q
  Ran 49 tests ... OK

bash scripts/lint.sh
  MICROCODE CHECK PASS
  LINT PASS

SPK286_BUILD_DIR=... bash scripts/test_units.sh verilator spk286_prefetch_fidelity
SPK286_BUILD_DIR=... bash scripts/test_units.sh iverilog spk286_prefetch_fidelity
  PREFETCH FIDELITY PASS; both produce 845 records

python -c "... compare_captures(...); validate_workload(...); ..."
  MATCH 845 rows
```

The existing fetch, queue and core banks passed in both simulators with 26,
19 and 7 checks respectively. The ownership banks passed in both simulators
with the counts recorded in the matrix above. Icarus emitted its existing
constant-select informational messages; every affected process exited zero.

No RTL file was changed by this increment. The changes are limited to the
integrated observation bank, its independent validator, focused negative
tests and the test-unit registration.

## Next Phase 9 increment

The normalized functional 9D base is now evidenced, but 9D is not a claim of
historical timing fidelity. The next independent increment is the Phase 9E
policy contract: retain identical architectural and bus results while
introducing only explicitly specified policy selection. The current RTL
still exposes policy `0` only, so no Accurate/Fast/Max completion is claimed.
V1 (`call-stack-precheck`) and the complete Phase 9 regression remain open
for the global closure gate.
