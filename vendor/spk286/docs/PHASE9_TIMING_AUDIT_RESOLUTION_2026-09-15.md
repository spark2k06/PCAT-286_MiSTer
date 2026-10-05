# Phase 9A timing audit resolution

This document records the implementation response to
`PHASE9_TIMING_AUDIT_2026-09-15_151b9c7.md`. The audit remains an immutable
historical review of commit `151b9c7`; this document records the subsequent
corrections.

## H1 — effective operand-service wait

`spk286_operand` now exposes `timing_wait`. It is asserted only while an
effective memory operand is blocked waiting for BIU admission or for an
outstanding response. Register operands, prechecks, limit faults,
cancellation and the response-acceptance cycle are excluded. The CPU timing
observer consumes this service-owned signal instead of inferring memory access
from the ModR/M context and global BIU readiness.

The operand service and byte-service tests cover local REG access, admission
backpressure, pending responses, completion, cancellation and invalid limits.

## H2 — external capture directories

The trace path in the JSON manifest is now relative to the manifest directory,
with an additional repository-relative path when the output is inside the
repository. This supports both the default build directory and an external
absolute `--build-dir` without a late `Path.relative_to()` failure.

## H3 — capture provenance

Capture now requires a clean Git tree before compilation. It records SHA-256
hashes for the complete compiled RTL/generated input set and the capture
support inputs, then recomputes them after simulation. A changed tree, HEAD or
input hash aborts manifest publication. The manifest therefore cannot silently
label an uncommitted RTL capture with only the old `HEAD` identity.

## H4 — CSV evidence validation

The validator now requires the complete ordered 32-column schema, parses every
field as an integer, checks Boolean and field ranges, rejects incomplete or
duplicated headers, verifies contiguous pre-edge samples, checks phase/READY
and idle/active bus coherence, enforces monotonic counters and verifies the
BIU busy/accepted/wait relationships. Workload-specific checks remain separate
and require READY waits, transfers, prefetch, queue consumption, implicit
LOCK and HLT.

Negative tests cover incomplete headers, negative/non-contiguous counters and
incoherent bus deltas. Verilator and Icarus captures are retained in separate
directories and are compared byte-for-byte.

## Coverage and documentation

The observer contract test now covers data writes, odd lanes, INTA reads,
HOLD/HLDA fields and queue-empty occupancy. The timing documents define
pre-edge sampling, the current non-reset epoch contract, overlapping metrics
and the dependency-to-observation matrix. INTR/NMI assertion-to-acknowledge
timestamping and intermediate-reset epochs remain explicitly pending rather
than being inferred from internal event counters.

## V1 mutation-anchor status

The three stale anchors identified by the audit were updated to the current
RTL expressions. The shared mutation source ordering was also corrected to
match the package-first order used by the normal RTL build. The mutation-anchor
test passes, and the focused event and data mutation audits pass with their
pristine benches and intended mutant rejections.

At the snapshot documented here, the far mutation audit still stopped at its
pre-existing `call-stack-precheck` mutant because that mutant was not rejected
by the current far-instruction bench. Consequently the far audit, and V1 as a
whole, were not claimed closed by that change. No expected functional result
was weakened.

The subsequent focused closure is recorded in
[`PHASE9_V1_RESOLUTION_2026-09-15.md`](PHASE9_V1_RESOLUTION_2026-09-15.md).
It replaces the stale mutation anchor with the live `call_stack_range_fault`
predicate and adds an independent protected-mode expand-down stack case. The
original RTL passes with zero writes before the stack fault, while the weakened
mutant is rejected after producing an observable premature write. No RTL or
generated microcode change was required.

## Validation status

Focused operand, timing-observer and integrated capture tests pass in Icarus
and Verilator; lint and Yosys synthesis sanity checks pass. The full project
regression remains intentionally deferred to the end of Phase 9 as specified
by the audit decision. Historical cycle accuracy is not claimed.
