# Phase 7 remaining work - 2026-09-09

Current D-037 policy (2026-09-09): the corrected strings/REP and scalar/string
I/O implementation is integrated in ordinary repository sources. All 307
required files remain in scope. REP initial-zero-count ordering is an open
engineering policy; exactly one incomplete E7 capture is NOT EVALUABLE, with
4,999 evaluable E7 records still required. These and the three inherited D-026
notes are nonblocking for functional/development acceptance. Final executable
validation, independent functional approval and verified delivery remain required.
See [the current policy](PHASE7_FUNCTIONAL_POLICY.md). Historical text below
retains its original dates, counts and conclusions; its incompatible REP/E7
closure prerequisites are superseded by D-037.

Status: **incomplete**. User milestones 1-6 are delivered. Memory strings/REP,
scalar/string I/O and final review/integration/delivery remain open (7, 8, 9).
The delivered arithmetic commit is `6dcc0e1c046e83b9393bb29fe774b3c18fefa2d2`. The following candidates are
preserved local work; their source has not been delivered as an approved increment.

Current closure-session disposition: an actual independent review was performed,
and its three local findings are corrected in an isolated continuation. Review
of the corrected boundaries is satisfactory. REP nonzero TF granularity now has
an explicit primary-document/inference disposition; initial CX=0 event order and
E7 admission remain blocking. The new E7 diagnostic executed 4,999 complete cases
successfully, preserving the one incomplete required observation. See the
[closure dossier](PHASE7_CLOSURE_20260909.md),
[independent report](PHASE7_INDEPENDENT_REVIEW_20260909.md) and
[correction addendum](PHASE7_REVIEW_CORRECTIONS_20260909.md).

The table below is preserved historical validation of the original candidates.
New validation, final identities and recovery/delivery state are recorded in the
closure section of [the candidate record](phase7_pending_candidate_validation.json).

| Candidate | Actual executable evidence | Remaining condition |
| --- | --- | --- |
| Memory strings on delivered arithmetic | 1,338,997 disjoint physical cases; 240 ordinary and 86 compiler tests; 54 benches in both simulators; 171 intended RTL faults detected | REP event adjudication, independent review and integration |
| Complete ordered candidate | 1,381,997 executed physical cases all pass; 254 ordinary and 88 compiler tests; 57 benches in both simulators; 189 intended RTL faults detected | E7 preparation fails; REP evidence, independent review, final gate and delivery pending |

The complete candidate attempted all 307 required opcode files. E7 contains
5,000 required records and failed preparation; none were claimed as executed.
There are zero execution failures among the 306 prepared files and no new
exclusions. The strict full physical result is **FAIL**. Separate successful
regression and audit commands do not establish `make phase7-check` success.

Exact result hashes, source snapshots, microcode sizes, synthesis counts and
verified archive identities are in [the candidate record](phase7_pending_candidate_validation.json).
The archives contain source bytes, actual logs, identities and research records;
large raw artifacts remain ignored. The complete ordered image is format 17,
100 entries / 612 words, with 17,300 mapped and 1,398 sequential cells.

The arithmetic delivery's GitHub Actions status is recorded as an actual dated
snapshot in the candidate record. That workflow checks ordinary regression and
the provisional Phase 6 executable gate; it is not the complete Phase 7 gate.

## E7 capture gap

The pinned corpus remains `37c73caf53dcd22d3dd369ff09305d13d117a4fe`.
E7 index 1100, hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e`, starts an OUT
transaction but has no captured write strobe or payload before HALT. Both the
original parser and independent wire inspection agree. The original July 2025
release has the same incomplete cycles; its FLAGS differ from the pinned record,
so only the explicitly compared fields are claimed identical. The record is not
upstream-revoked. Expected AX must not be fabricated into captured bus data.

The original draft is preserved in `build/phase7-preparation/E7_ISSUE_BODY.md`.
The current local draft, including the new diagnostic and read-only upstream
findings, is `build/phase7-closure-20260909-main/E7_ISSUE_BODY.md` and is included
in the verified closure package. In the earlier session, publication was
attempted after explicit user authorization, but the connector
returned HTTP 403 and the browser was not authenticated. The user then asked to
leave publication pending. No issue was created. A corrected capture/export or
an independently evidence-backed disposition is needed before admitting E7.

## REP event evidence and review

[The evidence note](PHASE7_REP_EVENT_EVIDENCE.md) records IBM's explicit 286
per-iteration single-step statement and its scope. Intel's differing order of
count and pending-interrupt checks leaves the initial CX=0 competing-event case
unadjudicated. No controlled physical event experiment has occurred. The new
independent review supports nonzero stepping with explicit inference, while
retaining the zero-count blocker. Passing directed policy tests does not settle it.

The [focused read-only review request](PHASE7_FOCUSED_REVIEW_REQUEST.md) identifies
the original snapshot and available evidence. Its requested independent review
has now occurred; the dated reports above preserve original and corrected scope.

## Validation retry and continuation

The complete candidate's first new-mutation audit exceeded the existing
60-second wall limit in a pristine arithmetic bench while other regressions ran.
The same source, tests, comparison and limits passed after those runs finished.
This supports scheduling contention as the cause; the failed first result is
preserved and no timeout is counted as a successful mutation detection.

After the new evidence/review questions are resolved, use the preserved ordered
integration plans, verify the exact input identities, and run the complete final
gate on the actual final functional inputs. Fix concrete findings before delivery.

The inherited Phase 6 questions `failed-iret-nmi`, `sti-old-if` and `fault-tf`
remain open under D-026. They alone do not block development. No extra waiver,
architectural release approval or historical cycle-accuracy claim is included.
The authorized [Phase 8 preparation note](PHASE8_PREPARATION.md) is complete;
Phase 8 implementation has not started.
