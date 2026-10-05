# Independent review: null-segment commit specialization

**Decision: GO for the exact combinational replacement and a subsequent fit.**

Reviewed the v6 proof helper, raw and timed generated candidates, source bindings,
actual selector service, all proof logs/receipts, and the real seed2 CPU setup path.
The initial source and artifact hash check passed. Each complete candidate reverses
to its production source by undoing only the target assignment.

## Functional argument

- `segment_reload_operation` retains the actual common permission (`allowed` in
  raw, `implementation_allowed` in timed), operation MC77, `temporary_valid_q[0]`,
  and protected mode `protected_msw[0]`.
- MC77 makes the other descriptor operation classes false for every input bit
  pattern. The selector therefore comes from `tmp0_q`, and `descriptor_begin`
  reduces to the retained reload qualifier and `!descriptor_active_q`.
- The null test remains `tmp0_q[15:2] == 0`: TI=0 and index=0; all four RPL values are
  retained. The descriptor offset is zero, so address carry is false for any
  24-bit base. The old limit fault is conditional on a non-null selector and is
  therefore false even for arbitrary table limits.
- `segment_index != 2` still rejects SS. The explicit descriptor-active guard
  prevents a repeated null commit during an active descriptor service.
- No descriptor selector output, other fault predicate, register, state transition,
  clock, or architectural cycle is changed by this single-expression replacement.

The helper extracts the actual continuous-assignment dependency graph and complete
selector instance separately from raw and timed sources. It treats retained state,
operation, bases/limits, and common permission as independent symbolic inputs. The
SAT miter compares the target plus all nine selector outputs, with no assumptions
or reachable-state restriction. Both proofs pass; all four mutants per variant
(missing SS guard, wrong null slice, missing operation qualifier, missing active
guard) produce counterexamples. The reported binary equivalence is sufficient to
substitute this output in its unchanged downstream consumers.

## Relationship to the fitted path

Report: `build/p06-deadline-fold-seed2-allfeatures-20261005-v1/timing/7_slow_1100mv_100c/cpu_setup.rpt`.
Path 1 has setup slack **-0.312 ns**, from duplicated `head_q[2]` to GPR64, with
18 logic levels and data delay 19.576 ns (12.337 ns interconnect, 7.239 ns cells).
Its data cone includes:

`service_start -> descriptor_selector_value[3]/[2] -> selector LessThan0 (three cells) -> descriptor_pre_fault -> segment_state_commit_base -> gpr_data_onehot -> sequential_gpr_write_data -> GPR64`.

The null commit controls `protected_segment_commit_base`, enable and other cache
payload selects; the top-level segment base select consumes those signals. The
replacement removes the redundant general selector/fault chain from this null
case. It is therefore a relevant candidate against the measured path.

## Limits and adoption conditions

- The formal proof covers binary input values. It does not claim four-state X/Z
  simulation equivalence, full-system regression, or board validation.
- Yosys/ABC's 485-to-446 gates and permission-to-target depth 35-to-6 are generic
  mapping results, not Cyclone V ALM, routing, slack or hold predictions.
- The general `descriptor_pre_fault` cone remains used elsewhere; another fitted
  path may become critical. A new all-corner physical fit is required.
- Apply only the exact assignment; regenerate the timed source from its builder,
  then repeat the source-bound proof and directed tests. Preserve all constraints,
  the full feature set, historical timing semantics and unchanged cycle count.
- The full regression remains deferred by the user.
