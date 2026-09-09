# Focused independent Phase 7 review request

Status: request executed on 2026-09-09 by a separate read-only reviewer.

The initial report and changed-boundary disposition are
[PHASE7_INDEPENDENT_REVIEW_20260909.md](PHASE7_INDEPENDENT_REVIEW_20260909.md) and
[PHASE7_REVIEW_CORRECTIONS_20260909.md](PHASE7_REVIEW_CORRECTIONS_20260909.md).
The original request and historical evidence below are preserved. Review
performed and corrected boundaries satisfactory do not imply full approval.

Primary target: `build/phase7-ordered-combined-prototype`, read-only.
Exact 409-file snapshot: `build/phase7-preparation/ordered-combined-full-frozen-source.json`.
Snapshot SHA256: `04ccc181a8951a66b49fc282ba9baf6471ef40ef6f1807a3b2a6bdb027030b98`.
The candidate preserves arithmetic format 15, memory strings format 16 and I/O
format 17 (100 entries / 612 words). Generated output was regenerated and tested.
The earlier 401-file candidate is historical comparison material only.

## Required decision

Independently inspect the new CPU boundaries and their evidence. Identify whether
this is a sound functional development increment on the provisional Phase 6
baseline. Separate demonstrated defects, new evidence gaps and the three existing
D-026 questions: `failed-iret-nmi`, `sti-old-if`, `fault-tf`. Do not invent closure
of those old questions or add a new waiver. Tests and implementation self-review
are not independent approval.

## Actual evidence and limits

- Compiler/literal audits and ten affected benches in both simulators passed.
- The complete ordinary regression passed: 254 ordinary tests, 88 compiler tests,
  57 benches in both simulators, lint and synthesis. All 136 retained RTL mutants
  were detected with passing pristine controls.
- All 307 required physical files were attempted. The 306 prepared files executed
  1,381,997 cases with zero failures. E7 preparation failed on an incomplete capture;
  all 5,000 records in that file remain unexecuted. No new revocations or exclusions.
- Adapter v5 passed six pristine cases, 24 undefined-bit variants and 188 strict
  frame/address/port negatives. Expected port data is not CPU input stimulus.
- The first new-mutation audit exceeded its existing wall limit in a pristine
  bench during concurrent regressions. The unchanged retry has separate actual
  `prototype-ordered-combined-audits-2` log/result files; inspect their real status.
  Never count a generic timeout as a successful mutation detection.
- Exact current records are `prototype-ordered-combined-*-result.json`; the
  preserved archive index is `ordered-candidate-validation.json` when present.

## Boundaries to inspect

1. Register byte aliases, defined/preserved/undefined FLAGS and exact fault frames.
2. Segment/far commits, partial stack effects, pointer aliases and redirect drains.
3. REP element boundaries, partial SI/DI/CX effects, prefix restart and IRET resumption.
4. SS inhibition across a whole REP, STI policy, owed TF and competing events.
5. INS/OUTS irreversible effects, READY, HOLD/LOCK, cancellation and accepted ports.
6. Human microcode authority, frozen/active literal audits and generic sequencing.
7. Required scope/accounting, original masks/revocations and strict gate separation.
8. D-036 general byte-IDIV overflow compatibility; legal arithmetic and unsupported
   positive-overflow predictions must remain distinct from physical observations.

IBM's October 1990 Hardware Interface Technical Reference, printed page 9,
explicitly states that the 80286 single-steps after each repeated MOVS iteration.
See `PHASE7_REP_EVENT_EVIDENCE.md` and its exact PDF hash. Review the inference to
other primitives and the restart frame; no controlled physical TF run is claimed.

For initial CX=0, Intel 210498-005 section 3.7.2 checks pending interrupts before
the count, whereas Appendix B B-93 checks the count first. The candidate performs
no element access, then accepts eligible events at ordinary completion with next
IP. Determine whether the evidence supports that contract or requires a focused
physical adjudication. Do not settle a real inconsistency merely to pass a gate.

Report exact file/line references for actionable findings, severity, reasoning,
the inspected snapshot and limits of validation. No source changes, external
messages, invented expected values, approval fabrication or rewriting of the
original Phase 6 review are authorized by this prepared request. Full Phase 7
remains incomplete while E7 or required new evidence/review is unresolved.
