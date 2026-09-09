# Phase 6 independent evidence-closure review

Review date: 2026-09-08. Reviewer: a separate agent context from the
implementation agent. This review made no production edits, changed no
expectations or evidence status, and made no commits or pushes. Downloads,
derived page images, focused-test outputs, and review notes were confined to
the ignored `build/phase6-closure-review` directory. Test execution disabled
Python bytecode writes and used that directory for temporary build outputs.

**Disposition: the reviewed capture preparation is acceptable within the
documented limits; architectural approval remains withheld.** No new concrete
preparation defect remains from this review. There have been zero physical
captures, and none of the three unresolved architectural decisions is closed.
The preparation is not a validated fixture adapter or a complete hardware
experiment. In particular, experiment B still needs demonstrated input timing
before a negative result can distinguish the isolated old-IF=1 policies.

## Exact reviewed candidate

The frozen candidate is
`build/phase6-evidence-closure/review-snapshot`. Its `snapshot.json` SHA-256 is
`c9082a4e9ffc3c3965cd01044f8274f8e9a99b5f3c235826f809de02dc143d10`.
The reviewer independently recomputed the hashes of all **192 listed files**:
all matched. The recorded base is
`03c32df5c2d5edcb4606564d1dba215d26640116`. The entry staged tree was
`94fcf66a13ca6a1d618feeff37a48c886d37aa86`.

The reviewer also independently compared the old 147-entry
`build/phase6-final-3/inputs.json` with the 155-entry
`build/phase6-evidence-closure/inputs-final.json`. Exactly 145 original entries
are unchanged, none are missing, and the two changes are the explicit NASM
environment additions in `.github/workflows/ci.yml` and
`scripts/bootstrap.sh`. Eight new entries describe the probe package and its
tests. Every final input hash also matches the frozen snapshot manifest. This
is byte continuity, not a substitute for regression results.

Selected identities, all SHA-256:

| Reviewed file | Hash |
|---|---|
| `rtl/spk286_events.sv` | `2def7f4cdf41818c42c683090f64afcd8f7056be4fb3013217ffc2848cb5c72a` |
| `tools/event_reference.py` | `84e3ccdeeea07e6bbab5a41d5d3d1f33a81bdb1e72f1819ffd82ab7fb911c34f` |
| `docs/phase6_evidence.json` | `ea1d9aa6b866498449698bcc3db00a9ce7e3e30059d492a69fa2e9922dc4ce6e` |
| `research/phase6_probes/probes.asm` | `4ffa4a5063ac8f03e54f21d6f29fc46e7cac0a94b8e925b356bed6aeafaec0be` |
| `research/phase6_probes/mechanics.py` | `253b64fe770ed8a7896da7022894471f91f5c9d3d54104868e843dce11f9d801` |
| `research/phase6_probes/results.py` | `391afd2276001e998304f670cab9ef679863770e15beea7d808f124f14133e46` |
| `docs/PHASE6_CAPTURE_PROTOCOL.md` | `9af66db51dc53de4c7a4533ec19ffd84845e197f2d06f5a58aae3baa19eb53f8` |
| `docs/PHASE6_EVIDENCE_CLOSURE.md` | `be440079be87487a60211a9a7072efd79393c1784a3e71581b5878f4b102ceae` |

## Review scope

The reviewer read the phase scope, handoff, previous architectural review,
interrupt/exception documentation, evidence manifest, source notes, unchanged
evidence gate, event reference model and tests, and the relevant event RTL.
The closure review examined the probe assembly, builder, bounded mechanics
interpreter, capture parser/schema, focused tests, capture protocol, closure
dossier, and declared build-environment additions. Final executable checks
ran from the frozen snapshot, not a moving working tree.

The limited production-code inspection confirms that the existing provisional
policies remain identifiable and that the unresolved-evidence gate remains
closed. It does not constitute a new whole-core architectural review. The
reviewer did not rerun the historical 463-lifecycle gate, a full RTL regression,
the physical corpus, synthesis, or CI. Earlier review scope must not be
silently extended from its historical lifecycle count to the later candidate.
The implementation agent's new ordinary regression, final handoff/log
appendices, recovery package, and any later commit identity are outside this
frozen review's attestation and require their own recorded results.

## Primary evidence independently inspected

The reviewer personally downloaded or rehashed the original PDFs, read the
relevant text, and inspected rendered original page images. The new research
is the 1983 manual and C-2 information package; the other sources are existing
material rechecked for exact scope. The following PDF page numbers are
one-based and separate from printed page numbers.

| Original artifact | Personally inspected decisive pages | SHA-256 |
|---|---|---|
| [Intel iAPX 286 Programmer's Reference, 1983](https://bitsavers.trailing-edge.com/components/intel/80286/210498-001_iAPX_286_Programmers_Reference_1983.pdf), archive identifier 210498-001 | Title/legal matter; B-102 / PDF 297; D-3 / PDF 364 | `367e1834e2f46397047084dffe1de88f65a1c115795b65ba26d1609995983c8f` |
| [Intel Doc. 1634c, 80286(C-2) Information Package, 21 November 1984](https://docs.pcjs.org/manuals/intel/80286/80286_C2_Errata-1984-11-21.pdf) | All six pages read; cover and correction on PDF 4 visually inspected | `9f609723e4c754a58608ab0da5ead3bb6b515be0208ba522f395d52c14997bde` |
| [Intel Doc. 5079B, B-2/B-3 Information Sheet, 21 November 1984](https://docs.pcjs.org/manuals/intel/80286/80286_B2_B3_Errata-1984-11-21.pdf) | INT n correction on PDF 5 | `1384cbf6a0cb23451495611c311879e407cf6789ef7b958764a812de0f5836c6` |
| [Intel 210498-003, 1985](https://bitsavers.trailing-edge.com/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf) | STI B-102 / PDF 302 | `9c6067e777ae694d5f71d8ade23014558be4e9d156041c778aed84c1246d8538` |
| [Intel 210498-005, 1987](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf) | Section 9.7.1, 9-14 / PDF 176; appendix C-2 / PDF 328; STI B-106 / PDF 314 text | `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460` |
| [Intel 210760-002 hardware reference, 1987](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf) | NMI pulse qualification 3-12 / PDF 62; NMI/INTR recognition 3-13 / PDF 63; clock definition 3-15 / PDF 65 | `d3ece037a200b17ef32d78a055d0d96c3e47474d755d94569b9576a9a68c6915` |

Detailed source provenance, narrowly capped excerpts, rendered-page filenames,
and bounded unsuccessful searches are preserved in
`build/phase6-closure-review/RESEARCH_REVIEW.md`, SHA-256
`6e8553f40fca7648a4bc86af032858ac6abd347d37e8a20f12b418db332e26cb`.
This is evidence about the inspected material, not a claim that no
discriminating source exists elsewhere.

| Decision | Independent finding and remaining alternative |
|---|---|
| `failed-iret-nmi` | Generic IRET-execution wording does not distinguish a failed attempt from successful completion. Both release on attempt and continued inhibition remain possible. No new physical trace settles the distinction. |
| `sti-old-if` | Neither the newly inspected 1983 STI page nor the rechecked later pages explicitly addresses old IF=1 or repeated-STI renewal. Transition-only, unconditional renewing, and unconditional nonrenewing policies remain unadjudicated. |
| `fault-tf` | The conflicting appendix statement already appears in 1983. Both the B-2/B-3 and new C-2 corrections explicitly concern INT n; extending that correction to #GP would be an unsupported inference. The relative priority of eligible events does not establish that the fault itself creates a step event. |

The newly extracted hardware timing detail materially limits experiment B:
the documented INTR lead time is two **processor** clock cycles before
instruction completion, while external CLK runs at twice the processor-clock
rate. An input first raised after a nominal two-cycle STI begins has no
automatically guaranteed recognition window at that STI's end. A sweep whose
interrupts all follow the marker can therefore reflect late sampling. It
cannot alone prove unconditional shadowing. The final protocol states this
limitation, requires measured qualification, and preserves inconclusive
results. Repeated STI supplies a separate renewal experiment; it does not
automatically resolve the isolated old-IF=1 distinction.

The hardware NMI wording also uses **system-clock periods** for its low/high
qualification. The protocol correctly defers electrical limits to the exact
part, distinguishes external CLK periods from processor cycles, and describes
any eight-period margin as complete external periods rather than ambiguous
edge counts. No universal nanosecond value is asserted.

## Probe and capture preparation findings

The final preparation incorporates the concrete review corrections:

- Boot initializes all general registers and segments to explicit values.
  Target encodings and fixed offsets are checked against actual NASM bytes.
- Terminal register recording follows the discriminating handler marker and
  uses nine stack words below the event frames. It performs no diagnostic
  IRET or NMI. Saved general registers, FLAGS, and pre-dump SP are distinguished
  from reconstructed control/segment state. Incomplete recording can remain
  inconclusive instead of becoming invented state.
- Experiment A retains the original event frames and distinguishes successful
  IRET controls from failed attempts. Its illustrative partial-pop model is
  not imposed as a physical acceptance criterion: differing SP or bus-read
  ordering must be retained and examined.
- Experiment C without NMI distinguishes the illustrated immediate, handler,
  and absent trap paths and includes explicit TF-restoration controls. The
  optional NMI variant stops at initial event nesting; it cannot claim later
  handler stepping when NMI prevents that handler from executing. Instruction
  fetches alone do not establish execution alignment.
- The mechanics interpreter runs actual generated bytes but assigns
  hypothetical policies. Its 18 combinations are useful preparation cases,
  not an exhaustive set of possible physical behaviors. In particular, an
  event delayed into the handler need not imply the precise live/saved-TF
  behavior of the illustrative handler-step policy. Raw FLAGS must survive
  classification.
- The capture parser rejects the exercised wrong-provenance, missing-artifact,
  corrupted-hash, unsafe-path, duplicate-field, nonfinite-number, inappropriate
  diagnostic-NMI, and mismatched-control cases. The initial-memory digest is
  tied to the actual artifact. Structural acceptance proves neither capture
  authenticity nor architectural correctness and never opens a release gate.
- NASM/NDISASM are explicit dependencies of the mandatory tests, CI, and
  bootstrap path; missing tools are not silently converted into skipped
  verification. The corrected historical manual digest is metadata only.

The reviewer separately downloaded all six pinned fixture-source artifacts
listed by the preparation and verified each recorded hash. The ArduinoX86
revision is `2ccae6470ef2cc12e247b74e3ad2d226b7f74936`; the referenced 80286
corpus revision is `37c73caf53dcd22d3dd369ff09305d13d117a4fe`.
Inspection confirmed the cited pin control/cycling interfaces and the relevant
Harris 80C286 support. This was source inspection, not firmware qualification
or operation of a fixture. The normal HALT/NMI state-dump mechanism would
contaminate the failed-IRET experiment, and the protocol does not adopt it.

## Independently executed checks

From the frozen snapshot, with scratch outputs confined as described above:

```text
python3 -B -m unittest tests.test_phase6_probes tests.test_event_reference tests.test_phase6_release -v
```

Result: **23 tests passed**, Linux subprocess exit **0**, 10.996 seconds.
The probe checks build all 21 configurations twice and include **378 synthetic
executions** across the illustrative policy combinations. These are mechanics
checks and provenance-negative tests, not physical evidence.

Log: `build/phase6-closure-review/focused-tests.log`; SHA-256
`67e4fdc5ec444652e21b1a6630c6272f23064f62b7a11c66c144bbd5400434c4`.

```text
python3 -B -m tools.phase6_evidence
```

Result: Linux subprocess exit **1**, as required, with:

```text
PHASE6_EVIDENCE_BLOCKED: unresolved 286 evidence: failed-iret-nmi, sti-old-if, fault-tf
```

Log: `build/phase6-closure-review/evidence-checker.log`; SHA-256
`88cb131c8d24f2f3ad1da478a4b01303ab7196b58f66eb2a3af12c0918abdb49`.
Command/cwd/exit/hash records are in `build/phase6-closure-review/checks.json`.

These checks support the integrity and honest limits of the reviewed
preparation. They do not supply the missing independent 286 evidence.
**Architectural approval and Phase 6 release remain withheld.**

## Development disposition — 2026-09-08

D-026 permits incremental Phase 7 development on a freshly executable-validated
provisional Phase 6 baseline. This supersedes the earlier prohibition on Phase 7
development, not this report's historical findings or withheld architectural
approval. `failed-iret-nmi`, `sti-old-if` and `fault-tf` remain unresolved under
their unchanged candidate policies. See PHASE7_SCOPE.md and the current
development handoff for later validation and Git identities.
