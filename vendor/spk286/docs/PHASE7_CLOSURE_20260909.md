# Phase 7 closure review — 2026-09-09

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

**Phase 7 development remains blocked.** Milestones 1–6 remain delivered;
milestones 7–9 are incomplete. Independent review and its concrete corrections
are complete, but REP initial-CX=0 event ordering and one required E7 capture
remain unresolved. Strings/I/O stay in reconstructable isolated candidates.
No additional evidence waiver, production RTL integration or timing profile is
delivered by this closure.

**Phase 6 architectural evidence remains open:** `failed-iret-nmi`, `sti-old-if`
and `fault-tf`, under the existing D-026 policies. Those three questions alone
do not block development. Strict `phase6-check` and provisional
`phase6-exec-check` remain distinct; successful ordinary CI is not Phase 7
approval.

## Exact reviewed inputs and findings

The separate read-only reviewer was `/root/independent_phase7_review` (Mencius).
Its [original report](PHASE7_INDEPENDENT_REVIEW_20260909.md) covers all seven
requested architectural/verification boundaries. Its
[changed-boundary addendum](PHASE7_REVIEW_CORRECTIONS_20260909.md) closes the
three findings below. Report transport changed relative artifact links only;
original reports and their checksums remain in the recovery package.

| Snapshot | Files | Source-manifest SHA256 |
| --- | ---: | --- |
| Preserved ordered format-17 candidate | 409 | `04ccc181a8951a66b49fc282ba9baf6471ef40ef6f1807a3b2a6bdb027030b98` |
| Corrected executable-test candidate | 409 | `235b0b15d1eaaacf37eae1bb708d9c44e076e5b4b5f736b9dae5f5f2ba39d185` |
| Final evidence/review disposition snapshot | 412 | `b4f8a5af3139c8d804438928a9a741c25fdf6a0cde85b1a1f2305312980274d1` |

The last two snapshots share **328 byte-identical executable inputs**, manifest
SHA256 `f5da66b8427b83d44aa2da2b61e70105d072564653b17793dbf2359dcf76adba`.
The final snapshot adds the reviewed evidence/report records and IBM primary
PDF, with an explicit pending zero-count question and full approval withheld.
The independent reviewer checked all 412 hashes and this executable equivalence
in `DELIVERY_SNAPSHOT_REVIEW.md` (preserved under the review artifact directory).
Neither original nor corrected frozen inputs were overwritten.

| Finding | Disposition | Verification |
| --- | --- | --- |
| R1, P2: missing `phase7-arithmetic-check` target broke incremental validation | Restore the target using the existing arithmetic script in the new candidate | Independent original failure; arithmetic/strings/I/O/full-gate dry runs now resolve their entrypoints. Nested expensive gates were not executed by those dry runs. The full gate already used a separate path. |
| R2, P2: constant port stimulus let stale repeated INS data survive | Keep the existing 376 lifecycle cases; add 24 byte/word, parity, DF and READY cases with independently varying accepted samples; add the intended stale-input mutant | 400 lifecycle cases / 35,477 checks in each simulator; 19 I/O mutants detected with three passing pristine controls |
| R3, P3: completion tests did not isolate reviewer-validation branches | Add a clearly synthetic valid fixture and reason-specific negative checks | Three focused tests pass, including the previously existing method; no gate or evidence requirement is relaxed |

Only four executable-test/build files changed: `Makefile`,
`sim/unit/spk286_string_io_lifecycle_tb.sv`, `tools/audit_io.py` and
`tests/test_phase7_completion.py`. **RTL, authoritative/generated microcode,
physical corpus, admission policy and expected results are unchanged.** No
functional CPU defect was demonstrated. The first lifecycle compilation exposed
four width warnings in the added test; explicit Boolean comparisons fixed them.
The failed attempt remains preserved and was not counted as successful coverage.

Review was performed and corrected boundaries are satisfactory. **Full candidate
approval remains withheld**, and the final machine-readable completion record
does not say `approved`. Agreement on provisional behavior does not supply
missing hardware evidence.

## Executable validation and physical accounting

All new commands, tool versions, timestamps, durations, exit codes and log hashes
are recorded in `build/phase7-closure-20260909-main/*-result.json`. New heavy jobs
were serialized. The prior pristine-audit timeout and unchanged successful retry
remain historical records; no timeout or comparator was relaxed.

Final regression result: **PASS**, 1633.6 seconds. 88 compiler tests, 256 ordinary Python tests, 57 RTL benches in each
simulator, both whole-core smoke simulators, repeated physical-family smoke
samples and Yosys structural/mapped checks passed. Mapped synthesis reports
17,300 cells / 1,398 sequential cells. The regression ran against
the corrected 409-file snapshot; the final 412-file disposition snapshot has
the independently verified identical 328 executable inputs. Receipt:
`build/phase7-closure-20260909-main/regression-final-result.json`; log SHA256
`3b1f2ff7522f218e687edf41d84abdb6b19d8c477edccadf2fb5f900e7c25b21`.

New focused validation passed: compiler tests (88), deterministic generation and
literal audit, lint, both smoke simulators, three completion tests, both extended
INS lifecycle benches, and all 19 intended I/O mutants with pristine controls.
The final strict completion check exited 1 with exactly
`PHASE7_COMPLETION_PENDING: rep-zero-count-event-order: primary/physical evidence pending`.
The E7 reproduction independently retains its strict preparation failure.
The complete expensive `phase7-check` was not rerun through unchanged known
evidence failures. Its wiring was checked; a successful complete gate remains
required before integration/delivery of the pending increments.

| Run and scope | Required cases | Prepared cases | Executed | Passed | Execution failures | Required unexecuted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical combined full corpus, 307 required files / 306 prepared | 1,386,997 | 1,381,997 | 1,381,997 | 1,381,997 | 0 | 5,000 E7 |
| New diagnostic partial E7, one required file, incomplete admission | 5,000 | 4,999 | 4,999 | 4,999 | 0 | 1 |

Both rows have **zero new admission exclusions**. The diagnostic overlaps the
first row's required cohort and must not be added as a new required population.
Strict full physical acceptance remains **FAIL**. The original full-run report
continues to record 5,000 unexecuted cases; the diagnostic is separate evidence.
An internal prepared-file summary's `discovered=1,382,000` excludes E7 preparation
and is not the total required corpus. Samples, two simulators, parser checks and
synthetic tests are not additional physical cases.

Historical full evidence is reused because the reviewed RTL, microcode and
physical adapter are unchanged: 254 ordinary Python tests, 88 compiler tests,
57 benches per simulator, 17,300 mapped / 1,398 sequential cells and 189 intended
mutants. The latter is **136 retained + 17 arithmetic + 18 I/O + 18 strings**;
136 is not a separate addition to 189. The new I/O audit reruns the prior 18 and
adds one, giving a retained inventory of 190; only 19 were rerun in this session.
The review's original stale-input mutant surviving old tests is a demonstrated
coverage gap, not a successful mutation detection.

The inherited 474,049 unique-case cohort remains disjoint internally:
440,574 + 1,423 + 32,052. Its separate 43,951 prefix-readmission cases and all
later overlapping family samples retain their original accounting. The earlier
memory-strings-only 1,338,997-case pass is historical, not a new session run.

## Evidence dispositions and smallest next actions

- **REP per-element TF:** IBM's explicit repeated-MOVS/80286 statement was
  reinspected in context. Extension to other repeat primitives and restart-frame
  behavior is identified as an inference, independently reviewed. The final
  candidate records this narrow question resolved. This does not resolve TF on
  faulting elements (`fault-tf`).
- **REP initial CX=0:** Intel 210498-003 and -005 prose/flowchart order remains
  inconclusive; no applicable discriminating erratum or raw hardware capture was
  obtained. The candidate has no element side effects. Its next-IP event policy
  remains provisional. The [evidence note](PHASE7_REP_EVENT_EVIDENCE.md) contains a
  reviewed CX=0/1/3 capture protocol, event eligibility controls and a phase sweep
  separating arrival, latching and acceptance. Next action: obtain a physical
  capture with a justified window after acceptance of the target instruction and
  before its zero-count completion, or primary
  clarification that discriminates the alternatives.
- **E7:** the required hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e` at index 1100
  still has an IOW address phase without captured write strobe/data. Current
  upstream checks found no correction, revocation or public E7 issue. The new
  4,999-case diagnostic passes but cannot repair that evidence. Next action:
  obtain the acquisition trace, corrected capture/export or independently
  evidence-backed admission disposition. Details are in the
  [capture review](PHASE7_IO_CAPTURE_REVIEW.md).

The updated local `build/phase7-closure-20260909-main/E7_ISSUE_BODY.md` is ready
for review. **Publication remains PENDING BY USER REQUEST.** No third party was
contacted, and no admission exclusion or new waiver was enacted.

## Delivery, recovery and next-phase boundary

Production remains the delivered arithmetic base, 285 supported opcode files.
The isolated combined candidate covers 307 required files but is not integrated.
Production `phase7_forms.json` intentionally retains 22 pending files. Source
order is arithmetic format 15, strings 16, I/O 17; the candidate retains 100
entries / 612 words, ten address bits and eight control bits. Human microcode and
generation ownership are unchanged.

The original two archives were rehashed and every one of their 2,007 / 4,129
payload checksums verified. The new [recovery guide](PHASE7_CLOSURE_RECOVERY.md)
describes the full candidate, exact correction patch, manifests, review reports
and new evidence. Restoration must target an absent isolated directory.
`phase7_pending_candidate_validation.json` records the final archive identity,
restoration receipt and current results without rewriting the historical rows.

The new 88,572,726-byte package has SHA256
`83b339bc38437255091b2e486a9d481c21d3d36091c40e265cb3797b7e705c8c`.
Actual restoration into `build/phase7-closure-20260909-restore-check` passed all
1,663 payload checksums, all 412 final source hashes and all 328 indexed
executable hashes. The recovered three completion tests and microcode check
passed. A separate native-POSIX control verified safe executable permissions and
direct script execution; unsafe/existing destinations were rejected.

Git delivery status is recorded separately from executable acceptance. The
starting branch/remote were clean and synchronized at
`74c0b53ffe0fc212e0c8b70c3a780901b69def29` on
`codex/phase7-realmode-completion`. The
[arithmetic CI run](https://github.com/spark2k06/SPK286/actions/runs/34333445407)
for exact commit `6dcc0e1c046e83b9393bb29fe774b3c18fefa2d2` was freshly confirmed
**completed successfully**, including the provisional Phase 6 executable gate.
It does not validate the unintegrated format-17 candidate or resolve architectural
evidence. Closure documentation delivery is recorded in the final handoff and
local delivery receipt after commit/push; no main/master ref is changed.

Delivery receipt location:
`build/phase7-closure-20260909-main/git-delivery.json`; exact closure-commit CI
snapshot: `build/phase7-closure-20260909-main/closure-commit-ci.json`. These are
post-package delivery observations and are not claimed to be inside the archive.

[Phase 8 preparation](PHASE8_PREPARATION.md) is complete as a design note only.
It records CPU-only programs, observable completion conditions, transaction/CDC
contracts and the Micro8088 CPU/FPU prerequisites from read-only inspection of
the named consumer at `7bbdbbbe5ba1c2737da88943bbc668f5520faa31`. No Phase 8 RTL,
new harness or consumer modification was implemented; no boot, fit or historical
cycle-accuracy result is claimed.

The live continuation record is [PHASE7_HANDOFF.md](PHASE7_HANDOFF.md), with
actionable pending work in [PHASE7_REMAINING_WORK.md](PHASE7_REMAINING_WORK.md).
