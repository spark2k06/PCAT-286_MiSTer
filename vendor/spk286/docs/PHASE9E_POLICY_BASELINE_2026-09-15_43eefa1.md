# Phase 9E baseline policy contract — 2026-09-15

Snapshot: `43eefa1` on `codex/phase9-timing-tstates`.

This is the first 9E increment after the normalized functional 9D matrix. It
does not implement Accurate, Fast or Max and does not add historical delays.
It protects the current policy boundary while the profiles and their evidence
are still being defined.

## Contract

The current timing policy is `0`, `normalized-functional-baseline`:

- the timing layer is observation-only;
- `compatibility_delay_cycles` remains zero;
- policy metadata remains valid only outside reset;
- queue occupancy, READY, bus identity, owner, LOCK and HOLD/HLDA metadata are
  reported without policy-induced changes; and
- code, data and INTA phases retain their existing owner and READY phase
  classification.

This contract deliberately does not claim historical cycle accuracy. A future
profile selector must be introduced at a defined reset or quiescent boundary,
and each profile must preserve architectural results, external effects, bus
ownership and protected-mode checks.

## Verification

The new `spk286_timing_policy_contract` bank exercises seven sampled cycles
covering reset and idle, code READY wait/completion, data ownership with LOCK
and HOLD/HLDA, INTA, queue-empty execution, restart/cancel, operand wait and
event edges. It performs 63 assertions in each simulator.

```text
SPK286_BUILD_DIR=build/phase9e-policy-verilator \
  bash scripts/test_units.sh verilator spk286_timing_policy_contract
  TIMING POLICY CONTRACT PASS checks=63 cycles=7

SPK286_BUILD_DIR=build/phase9e-policy-iverilog \
  bash scripts/test_units.sh iverilog spk286_timing_policy_contract
  TIMING POLICY CONTRACT PASS checks=63 cycles=7
```

The existing `spk286_timing_trace` and `spk286_timing_capture` banks remain
unchanged and continue to verify the schema and independent operand-wait
counter model. No RTL functional path or timing delay was modified by this
increment; only the contract bank and test registration were added.

## Remaining 9E work

Still pending are the explicit policy-selection interface, the functional
equivalence matrix across any selected profiles, and historical evidence for
any Accurate claim. V1 (`call-stack-precheck`) and the final Phase 9 global
regression remain independent closure requirements.
