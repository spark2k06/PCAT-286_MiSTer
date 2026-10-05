# SPK286 remaining work — 2026-10-05

This is the consolidated CPU-only work register. It reuses the existing story
identifiers and acceptance contracts; it does not reopen completed increments
or create a new phase plan.

## Source and acceptance status

| Item | Audited state |
| --- | --- |
| Repository | `SPK286` |
| Branch | `codex/protected-mode-windows31` |
| Source revision | `b1eed8fec9138af1545bf3901fc267bde3cfdd1c` |
| Working tree before this documentation update | Clean |
| Latest portable CPU increment | Legal ten-byte completion and shared syntax preview; directed checks passed |
| Latest complete regression | **USER_DEFERRED** for the current increments; no new complete-regression PASS is claimed |
| Historical timing and complete protected-mode certification | Open for the explicitly listed scope/evidence |
| External E7 issue publication | **HELD_BY_USER**; no external publication or message is authorized |

The established CPU and the completed functional P06/P12 version in PCAT are
not pending stories. Their acceptance remains limited to its recorded scope:
[portable profiles](PROFILE_TIMING_ACCEPTANCE_20261004.md),
[READY chaining](READY_CHAINING_20261004.md) and
[the latest encoding update](PORTABLE_ENCODING_UPDATE_20261005.md).
The instruction-interval model does not certify historical native pin timing.

Priorities on H-stories retain the existing review's P1/P2 classification.
For evidence, timing and validation follow-ups, P1 means a current release
qualification and P2 means subsequent fidelity/evidence work; these priorities
organize this register and do not authorize a new implementation or test run.

## 1. Remaining functional/protection stories

The current list comes from the marked follow-ups and section 5 of the
[global protected-mode review](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md).
Its later closure statements supersede earlier dated work-package lists.

| Existing story | Priority | Remaining scope | Closure condition/evidence |
| --- | --- | --- | --- |
| **H02 — partial** | P1 | Explicit LOCK privilege and protected zero-count REP precedence. | Establish independent 286-specific expectations for explicit LOCK versus CPL/IOPL, invalid-LOCK precedence and the protected CX=0 INS/OUTS privilege boundary. Cover all CPL/IOPL combinations, permitted/denied effects and competing faults. Keep implicit memory XCHG locking independent of IOPL. |
| **H05** | P1 | Descriptor verification/inspection presence and conforming-code rules. | Separate LAR, LSL, VERR and VERW truth tables for P=0/1, conforming code, privilege combinations, system descriptors and invalid selectors. Failed inspection must preserve the destination and clear ZF. Resolve the LSL conforming-code disagreement with a physical 286 discriminator; do not import a 386 rule or assume emulator agreement settles it. |
| **H17** | P2 | JMP task-switch NT policy adjudication and documentation reconciliation. | Obtain a physical 286 observation of incoming NT=0/1 after direct-TSS and task-gate JMP, preferably by PUSHF rather than a following IRET. Retain CALL/INT and nested IRET controls. The current compatibility policy preserves incoming NT; Intel table 8-2 and native 86Box disagree. Change that policy only after adjudication. |
| **H19 — partial** | P1/P2 | Remaining multiword/boundary/restart matrix. | Audit LES/LDS, BOUND, ENTER/PUSHA/POPA, far memory pointers, REP memory/I/O, call parameter copying and system-table operands. Cover last valid byte/word, limit+1, FFFF crossing, odd addresses, expand-down extremes, null/read-only/execute-only segments, exact descriptor-table end and 24-bit address wrap. Specify permitted partial effects independently per family; do not impose universal rollback. |
| **H20** | P1/P2 | Event ordering and diagnostic completeness. | Extend the independent competing-event matrix across MOV/POP SS shadows, STI with old IF=0/1, faults, TF, NMI, INTR, REP and failed IRET. Preserve the existing provisional policies until primary/physical evidence settles them. Capture the first relevant context completely rather than diagnosing only the final shutdown or trap banner. |

These are CPU stories. Their existence does not establish that currently
working Windows, OS/2 or games fail on these combinations. A source discrepancy
requires a focused failing executable case before an RTL correction, and each
change requires its relevant lint, dual-simulator and source-bound checks.
H19 excludes the already closed [ESC first-word fix](PROTECTED_MODE_H19_ESC_BOUNDARY_20261001.md).

## 2. Physical evidence notes and LOADALL

### D-026/D-037 notes — open, nonblocking for functional development

Priority: **P2**, physical/evidence qualification. Publication stays held.

The five exact notes are defined by
[the Phase 7 policy](PHASE7_FUNCTIONAL_POLICY.md),
[the Phase 6 register](phase6_evidence.json) and
[the Phase 7 register](phase7_evidence_notes.json). H20 overlaps the first four;
they are evidence obligations, not five additional missing instruction families.

| Note | Missing evidence |
| --- | --- |
| `failed-iret-nmi` | Primary 286 clarification or physical trace distinguishing NMI release on successful IRET from a faulting IRET attempt. |
| `sti-old-if` | 286-specific observation for STI entered with IF=1 and consecutive STI instructions. |
| `fault-tf` | Adjudication of the real-mode entry/completion versus instruction-exception single-step text. |
| `rep-zero-count-event-order` | Physical phase sweep with CX=0/1/3 and complete saved frames distinguishing pre-instruction recognition from zero-count completion. |
| `e7-incomplete-physical-capture` | Original acquisition data or corrected capture supplying the actual missing write strobe/payload for the one pinned E7 record. |

The E7 record remains **NOT EVALUABLE**, never a PASS, reconstructed expectation
or general exclusion. Its exact corpus/hash/index restriction remains binding.
Issue publication stays held by user request. `rep-tf-granularity` already has
an accepted documentary disposition with an explicit inference beyond MOVS;
this register does not reopen it as an unresolved note.

### Milestone 7 — LOADALL evidence/corner-case closure

Priority: **P2**. Closure requires the evidence below, not reimplementation of
the delivered functional slice.

The fixed 102-byte image implementation, staging/atomic publication,
hidden-cache accesses and directed READY/reset/HOLD/NMI checks are implemented.
The milestone remains open under [LOADALL evidence](LOADALL_EVIDENCE.md) and
[its milestone contract](MILESTONE_7_LOADALL.md):

1. Select and record the target Intel/Harris/AMD 80286 stepping.
2. Establish direct silicon or hardware-derived unreal-mode evidence for the
   `0F05`/historical `0F04` spelling issue, image fields, cache validity/type
   semantics and corner cases.
3. Complete the specified top-level protected CPL0 success coverage and obtain
   independent silicon confirmation of nonzero-CPL frame behavior.
4. Resolve the documented reserved-FLAGS and protected-image PE-clear
   disagreements with 86Box/PCem using stronger evidence.
5. Record covered lifecycle behavior and exact historical timing separately;
   finish the applicable independent/regression closure when authorized.

The existing DOS [LOADALL probe](../research/loadall_probe/README.md) supplies
the physical handoff; actual silicon observations remain outstanding.

## 3. Phase 9 — historical instruction, bus and prefetch fidelity

Phase 9 remains open. The normalized functional observations and policy-0/Max
equivalence are delivered for their covered scope. The provisional interval
overlay supplies useful instruction minima and estimates; it is not pin- or
cycle-certified. See [the phase plan](PHASE9_TIMING_FIDELITY.md),
[its status receipt](PHASE9_CURRENT_STATUS_2026-09-16.md),
[dependency inventory](PHASE9_SYSTEM_TIMING_DEPENDENCIES.md) and
[portable profile contract](PROFILE_TIMING_CONTRACT.md).

| Existing increment | Priority | Remaining scope and closure condition/evidence |
| --- | --- | --- |
| **9A** | P2 | Extend observation where needed to timestamp external INTR/NMI-to-acknowledge relationships and define intermediate-reset epochs. Bind validated traces to source/profile inputs. Existing normalized counters/traces are not physical T-states. |
| **9B** | P2 | Select named hardware/reference profiles; validate instruction classes against documented/physical evidence and separate intrinsic work from operand/prefetch/READY waits. Record which profile-table entries remain estimates. |
| **9C** | P2 | Define and validate native 80286 signal polarities and Ts/Tc/idle relationships for code, data, I/O, INTA, odd words, READY, LOCK, HOLD/HLDA, reset and cancellation. Distinguish physical 286 phases from the existing normalized internal state names. Complete native trace comparison. |
| **9D** | P2 | Validate historical refill/overlap behavior and queue timing against the selected reference, while preserving the existing six-byte queue, redirect/drain and ownership semantics. |
| **9E** | P2 | Complete explicit Accurate and, if retained under the documented policy model, Fast contracts and evidence. Preserve baseline/Max architectural equivalence and real dependencies. Record an accepted runtime-change boundary for each interface. This does not request an additional OSD mode. |
| **9F** | P2 | Perform named-profile downstream acceptance with exact CPU/consumer revisions, configuration, ROM/payload/RBF hashes and hardware observations. Execution and machine-specific fixes live in the consumer repository. |

The CPU profile host provides virtual clock boundaries and qualifies logical
bus completion; SPK286 does not select MiSTer frequencies or provide an OSD.
Physical 6/12 MHz aggregate observations can anchor provisional calibration,
but neither aggregate benchmark agreement nor extrapolation to other rates
establishes native bus/pin timing. MAX is accelerated dependency-driven
execution, not a historical MHz claim.

Full captured bus-event/cycle comparison remains distinct from the existing
architectural SingleStep comparison; use the
[SingleStep integration contract](SINGLESTEP_INTEGRATION.md) and 9C evidence
to extend it without weakening state comparisons or counted omissions.

## 4. Validation, standalone packaging and release closure


- **Current standalone profile selection refresh: P1.** The generator pins
  predate the accepted instruction-length and encoding-metadata source
  updates and the equivalent null-segment specialization. Preserve the
  historical baseline and READY-chain contracts; publish an explicitly
  verified current selection, regenerate deterministically and rerun its
  focused standalone gates. PCAT uses its own current generator/overlay.
  See [the source-bound CPU change](NULL_SEGMENT_COMMIT_SPECIALIZATION_20261005.md).

- **Current complete regression: P1, AUTHORIZED_AFTER_TIMING_CLOSURE.** After the consumer candidate closes physical timing, run the authorized broader
  checkpoint, run the appropriate current standalone regression with immutable
  inputs, generated microcode/profile consistency, lint, affected banks and
  physical corpus admission. Include MAX versus the accepted original-engine
  behavior for changed profile paths. Preserve the existing Icarus-only long
  expand-down matrix policy and report actual simulator coverage.
- The 2026-10-04 composed gate records five distinct legacy auditors outside
  that composition. Assess the selected release target's required adapter/audit
  coverage before claiming that target's full closure; do not silently rebase
  frozen historical evidence to make a check pass.
- **PM6 release closure: P1**, conditional on the still-open protected-mode scope,
  applicable independent review/evidence, reproducible current validation and
  standalone release/integration documentation. The
  [protected-mode specification](../SPK286_PROTECTED_MODE.md#pm6--protected-mode-closure)
  is the acceptance contract, not a list of still-unimplemented PM0–PM5 blocks.
The [CPU-only repository boundary](../AGENTS.md#cpu-only-project-boundary)
assigns whole-machine features and FPGA timing to the consumer project.
9F records CPU acceptance against those consumer results. Recent PCAT OS
observations leave the specific H05/H17/H20 and LOADALL questions above open.

## Review/update rule

Update the original story/evidence document and this register together when a
scope is closed. Record the exact source, directed test, broader-gate disposition
and independent/physical evidence. Keep **implemented**, **directed PASS**,
**full regression**, **physical evidence** and **historically certified** as
separate statuses. Documentation-only consolidation adds no validation run or
architectural claim.
Keep accepted portable sources and this work register synchronized with the
consumer vendor copy using explicit revision/hash provenance. Regenerate
consumer-owned overlays from their own generator rather than importing them
as portable CPU sources.
