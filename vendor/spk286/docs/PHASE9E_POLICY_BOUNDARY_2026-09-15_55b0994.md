# Phase 9E policy boundary — 2026-09-15

This document records the first implementation increment after the 9E
observation-only baseline. The implementation snapshot is
`55b099442683e608a25d7ec8895b48597788659b` on
`codex/phase9-timing-tstates`.

## Contract

`spk286_timing_policy` defines the policy-selection boundary:

- `timing_policy_request` is sampled only while reset is asserted;
- the active policy is exposed as `debug_timing_policy` and is locked once
  execution leaves reset;
- policy `0`, `normalized-functional-baseline`, is the only implemented and
  accepted policy;
- unsupported reset-time requests are reported by
  `debug_timing_policy_error` and the active policy remains `0`; and
- requests that change after reset are ignored until the next reset boundary.

The timing trace now receives the latched active policy rather than publishing
an independent constant. This is an interface/boundary change only: policy 0
still inserts no compatibility delay and does not alter the functional CPU,
bus ownership, READY dependencies, queue behavior, protected-mode checks or
architectural results.

Accurate, Fast and Max are not implemented or claimed. In particular, no
historical delay or arbitrary idle state was added.

## Verification

The dedicated `spk286_timing_policy` bank passes six checks in both simulators:

- baseline policy accepted during reset;
- policy becomes locked after reset;
- post-reset requests cannot change the active policy;
- unsupported reset-time policy is reported;
- the error remains visible until a new reset; and
- a later baseline reset clears the error.

The affected timing and integration banks also pass in both simulators:

| Bank | Result per simulator |
| --- | --- |
| `spk286_timing_trace` | 12 checks, 13 cycles |
| `spk286_timing_policy_contract` | 63 checks, 7 cycles |
| `spk286_core` | 7 checks |
| `spk286_timing_capture` | 221 records, 221 cycles, 9 transfers, 4 waits |
| `spk286_timing_calibration` | 6 records, 59 samples, 58 cycles |
| `spk286_timing_policy` | 6 checks |

Additional checks:

```text
bash scripts/lint.sh
  MICROCODE CHECK PASS: 120 entries, 717 words, 10-bit addresses, 8-bit control
  LINT PASS

SPK286_BUILD_DIR=build/phase9e-policy-boundary-synth make synth-check
  SYNTH_CHECK PASS: build/phase9e-policy-boundary-synth/reports/yosys_synth_check.log
```

The Yosys run includes `rtl/spk286_timing_policy.sv` in the integrated `spk286`
hierarchy. Existing Icarus constant-select informational messages remain
unchanged and all affected processes exit successfully.

## Scope and remaining work

This increment establishes the reset/quiescent selection boundary required
before adding profile-specific timing behavior. It does not validate a
historical Accurate schedule, and it does not implement Fast or Max. The next
9E work must add only a separately specified profile and its functional
equivalence evidence; it must not silently reinterpret policy 0.

V1 (`call-stack-precheck`), the complete Phase 9 regression and historical
timing validation remain pending. PCAT and machine integration are outside
this increment.
