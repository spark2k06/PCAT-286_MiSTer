# Phase 9E Max functional-equivalence increment — 2026-09-15

This increment establishes policy `2` as the explicit dependency-driven Max
profile at the reset boundary. It does not claim historical timing accuracy and
does not add artificial waits, idle states or functional shortcuts.

## Contract

- Policy `0` remains `normalized-functional-baseline`.
- Policy `2` is `dependency-driven-max`.
- Both policies preserve the same functional schedule in the current RTL:
  there are no validated removable compatibility delays to eliminate.
- The request is sampled only during reset and remains locked after reset.
- Unsupported policy requests remain rejected and select the safe baseline.
- The policy metadata identifies the selected profile, while counters,
  transaction observations, ownership, READY classification, queue metadata,
  redirects, cancellation and event counters remain equivalent.
- This result is limited to the normalized functional observation layer and the
  integrated core smoke. It is not evidence for historical 80286 timing.

## Evidence

The focused `spk286_timing_policy_equivalence` bank drives identical reset,
code/data bus, READY, prefetch, queue-starvation, redirect/cancel, operand-wait,
event and HOLD/HLDA observations into policies 0 and 2. It compares every
normalized counter and trace field except the intentional policy identifier.

The parameterized `spk286_core_tb` is also run with policy 0 and policy 2. The
same architectural reset, state-commit, prefetch, redirect, cancellation and
repeat-reset checks must pass for both selections.

The captures retain `historical_cycle_accuracy_claim=false`; a later increment
must add independent evidence before describing any policy as historically
accurate.

## Remaining 9E work

Fast remains unsupported. A future Fast increment needs an explicit dependency
contract and its own equivalence evidence. Accurate remains pending historical
80286 references and reproducible traces. The final Phase 9 regression and the
historical timing work for 9B–9D remain separate gates.
