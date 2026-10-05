# Phase 9A follow-up resolution

This document records the focused response to
`PHASE9_TIMING_AUDIT_FOLLOWUP_2026-09-15_a1976ac.md`. The follow-up remains an
immutable review of commit `a1976ac`; this document records the subsequent H4
validator correction.

## H4 residual — resolved within the current observer contract

`tools/capture_timing_trace.py` now validates the semantic relationships that
are directly defined by `rtl/spk286_timing_trace.sv`:

- active `status` values map to the published owner (`INTA=3`, code fetch
  `0xD=1`, other active transfers `=2`);
- odd addresses publish the high-byte lane mask;
- idle samples publish zero address, data, lane and write metadata;
- counters and `trace_cycle` fit their published 64-bit widths;
- cumulative counters do not exceed elapsed CPU cycles;
- event/wait counters advance by at most one per sampled edge;
- policy `0` never publishes compatibility-delay cycles; and
- the transaction identity remains stable while a bus request is waiting for
  READY or reaches its completion sample.

The validator retains the pre-edge sampling convention. It does not impose
relationships between intentionally overlapping metrics, and it does not
reinterpret `queue_empty_cycles` as a starvation-demand metric.

## Tests added

The capture validator suite now contains independent negative cases for:

- incomplete headers;
- negative and non-contiguous counters;
- incoherent BIU deltas;
- status/owner mismatch;
- an invalid odd-address lane;
- non-zero idle data;
- an impossible event-counter jump;
- a non-zero baseline compatibility delay;
- counters wider than 64 bits; and
- transaction identity changes during a READY wait.

There is also a `main()` test proving that a rejected trace does not publish a
new manifest. The valid repository capture continues to pass unchanged.

## Validation status

The focused Python suite passes with 13 tests, and the existing capture passes
the strengthened validator with 221 records. This change is limited to the
capture validator, its tests and documentation; it does not alter RTL,
functional timing, the capture workload or the historical timing claim.

V1 remains open independently because the far mutation audit still stops at
the inherited `call-stack-precheck` mutant. The full Phase 9 regression also
remains deferred until the end of the phase, as agreed in the audit.

## Recheck of commit `1036850`

The subsequent recheck found three remaining H4 omissions without reopening
H1–H3: active even addresses accepted lane mask `2`, a READY-wait request could
disappear directly into idle, and write data was not required to remain stable
while the request waited or completed. Those omissions are corrected in the
follow-up commit after this document's original 13-test snapshot.

The validator now accepts only masks `1` and `3` for even active addresses and
only mask `2` for odd active addresses. A phase-1 sample must be followed by
another active sample in the same non-reset epoch; then address, status,
lanes, direction and owner remain stable. Write data is stable under that
condition, while read data may change until READY. A trace may still end on a
phase-1 sample, and a completed transaction may be followed by a new identity.

The updated focused suite has 21 tests, including the full eight-entry
parity/lane table, the two write-data transitions, the wait-to-idle rejection,
positive read-data and post-completion identity controls, and `main()`
no-publication checks for each remaining H4 invalid trace.
