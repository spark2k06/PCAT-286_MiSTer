# PM4b.1: Inter-Level Call Gate (Zero Parameters)

PM4b.1 adds the protected-mode inter-level `CALL FAR` path for a call gate
with zero parameters. It covers the transition from an outer privilege level
to the gate target's more privileged code segment.

## Implemented scope

- Validate the call-gate descriptor and target code segment, including an
  outer-level target whose privilege is more privileged than the caller.
- Read `SPn` and `SSn` from the current task's 80286 TSS through the BIU.
- Validate the new stack selector as a present, writable data segment with the
  required privilege relationship.
- Precheck the four-word frame before changing architectural `CS`, `SS`, `IP`,
  or `SP`.
- Switch to the TSS-provided stack and push, in architectural order, the old
  `SS`, old `SP`, old `CS`, and old `IP`.
- Commit the new `CS`/`SS` context and stack pointer only after all required
  writes complete.
- Preserve Real Mode far-call behavior and its existing stack-range policy.
- Report the protected-mode `#TS`, `#SS`, `#NP`, and `#GP` classes used by the
  validation path.

## Explicit deferrals at PM4b.1 closure

- PM4b.1 itself covered only a zero-parameter gate. PM4b.2 now extends the
  same path with bounded parameter-word copying; see
  [PROTECTED_MODE_PM4B2.md](PROTECTED_MODE_PM4B2.md).
- Inter-level `RETF`/return-frame validation is not part of PM4b.1 or PM4b.2.
- Expand-down stack handling remains deferred until its descriptor and limit
  policy are specified and covered by independent tests.

## Verification

The implementation was checked with the deterministic microcode unit/audit
suite and Icarus directed simulations. The protected-system test covers the
outer-level call-gate transition, descriptor accessed bits, exact frame bytes,
target execution, and stack restoration. Existing far-call, far-lifecycle,
event, event-lifecycle, and stack-control suites were also rerun.
