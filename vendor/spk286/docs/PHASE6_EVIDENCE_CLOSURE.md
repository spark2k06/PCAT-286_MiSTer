# Phase 6 evidence closure — preserved blocked candidate

Status: **BLOCKED**. This task completed additional primary-source research and
a portable capture package. It did not obtain discriminating physical captures
or resolve any of the three required architectural decisions. No Phase 6
implementation commit, push, release or Phase 7 work is authorized by this result.

## Question-by-question disposition

| Required decision | Status | Candidate policy retained | What still excludes closure |
|---|---|---|---|
| `failed-iret-nmi` | Unresolved | Release inhibition at IRET opcode acceptance, even if a later word faults | No examined 286 source distinguishes an unsuccessful attempt from completed return; need A frame/marker captures with edge controls |
| `sti-old-if` | Unresolved | Shadow only on IF 0→1 | No explicit old-IF=1/renewal source; B also needs a proven interrupt-recognition window, otherwise late stimulus mimics a shadow |
| `fault-tf` | Unresolved | No new retirement-based #1 for a faulting target | Intel's broad appendix wording remains in conflict with body text; INT-n correction is narrower than #GP; need C nested-frame captures |

The unresolved evidence file remains byte-for-byte unchanged. Agreement between
the candidate, its directed tests, the new hypothetical interpreter or reviewers
does not decide a missing physical fact. `UnresolvedEvidence` remains in the
independent model for a blocked NMI followed by failed IRET.

## Original state, preservation and final identity

The existing branch is `codex/phase6-interrupts-exceptions`, base/HEAD
`03c32df5c2d5edcb4606564d1dba215d26640116`. Its original prepared tree was
`94fcf66a13ca6a1d618feeff37a48c886d37aa86`, with 78 staged files and no unstaged
changes at entry. The original index is preserved; new research/doc changes are
retained alongside it. An index tree is not an implementation commit.

Before editing, `build/phase6-evidence-closure/verify_original.py` checked the
three original package hashes, all 2,534 retained manifest files, all 147 tested
executable inputs, failure markers, and the evidence checker (exit 1). It copied
the original patch to new ignored storage, extracted the old archive only after
checking member paths, then applied/reconstructed it in an isolated shared clone
of the base. The reconstructed tree exactly matched the prepared tree, and the
147-file byte fingerprint passed. This reconstruction required a byte-level EOL
adjustment only for `.gitattributes`; the old exporter had recorded two
adjustments under its environment. Both are retained as observed, not conflated.

The original `build/phase6-blocked-delivery` archive, patch, manifest and recovery
instructions are preserved. New recovery artifacts are in
`build/phase6-evidence-closure-delivery`. Its `manifest.json` identifies the final
combined candidate tree, unchanged real index, complete file changes, exact byte
snapshots, new executable-input manifest and isolated reconstruction result.
The final tree is recorded externally to avoid a self-referential document hash.
Use its `REPRODUCE.md` and `verify_recovery.py`; do not apply a patch twice or
restore old bytes over later user changes.

## New evidence versus repeated evidence

The independent reviewer inspected original source page images in a separate
read-only context. Its complete research note is retained as
`build/phase6-closure-review/RESEARCH_REVIEW.md`; downloads, text and page images
remain ignored. The following are new source investigations in this task:

**Intel iAPX 286 Programmer's Reference Manual, 1983.** The archive names
210498-001; the inspected title establishes 1983, not a narrower date or silicon
stepping. [Original PDF](https://bitsavers.trailing-edge.com/components/intel/80286/210498-001_iAPX_286_Programmers_Reference_1983.pdf),
SHA-256 `367e1834e2f46397047084dffe1de88f65a1c115795b65ba26d1609995983c8f`.
Printed B-102/PDF297 says "after executing the next instruction"; printed
D-3/PDF364 contains "INT instructions or an instruction exception". Original
title, STI and appendix images were checked. The disputed appendix claim thus
predates the B-2 correction. It still does not exclude either fault-TF behavior,
qualify STI by old IF, or distinguish failed IRET. Scope: Intel 286 description,
Real/Protected context as stated, no demonstrated all-vendor guarantee.

**Intel Doc. 1634c, 80286 (C-2) Information Package, 21 November 1984.**
[Original six-page PDF](https://docs.pcjs.org/manuals/intel/80286/80286_C2_Errata-1984-11-21.pdf),
SHA-256 `9f609723e4c754a58608ab0da5ead3bb6b515be0208ba522f395d52c14997bde`.
The cover identifies C-2 S40172/S54036. Printed/PDF p4 repeats the correction
whose subject is "the \"INT n\" instruction disables the Trap Flag if it".
Its surrounding text specifies Real/Protected Mode from B-2 onward, with original
FLAGS saved before TF clears. All six text pages and original cover/p4 images
were examined. This corroborates the correction's narrow scope; it does not
extend it to synchronous #GP. No old-IF or failed-IRET discriminator was found.

**Additional original timing passages, previously cited hardware manual.**
Intel 210760-002, printed 3-12/PDF62 and 3-15/PDF65, distinguish NMI pulse/low
requirements in system CLK periods from the internal processor clock. Printed
3-13/PDF63 requires INTR lead time before instruction completion. These pages
were independently image-checked; the new finding affects experiment validity,
not CPU policy. The short STI may have no guaranteed window satisfying both
"INTR after STI began" and sufficient lead time to its completion. An all-late
capture sweep cannot resolve old-IF semantics. The exact requirements and
inconclusive classification are in [the protocol](PHASE6_CAPTURE_PROTOCOL.md).

Previously examined sources independently rechecked in this task:

| Original artifact / revision | SHA-256 | Checked printed / one-based PDF pages |
|---|---|---|
| [Intel 210498-003, 1985](https://bitsavers.trailing-edge.com/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf) | `9c6067e777ae694d5f71d8ade23014558be4e9d156041c778aed84c1246d8538` | STI B-102 / 302 |
| [Intel 210498-005, 1987](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf) | `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460` | §9.7.1 9-14 / 176; appendix C-2 / 328 |
| [Intel 210760-002, 1987](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf) | `d3ece037a200b17ef32d78a055d0d96c3e47474d755d94569b9576a9a68c6915` | 3-12..15 / 62..65, as specified above |
| [Intel Doc.5079B B-2/B-3, 21 November 1984](https://docs.pcjs.org/manuals/intel/80286/80286_B2_B3_Errata-1984-11-21.pdf) | `1384cbf6a0cb23451495611c311879e407cf6789ef7b958764a812de0f5836c6` | documentation correction 1, p5 / 5 |

The old source inventory's malformed 210498-005 hash in
`INTERRUPTS_EXCEPTIONS.md` was corrected from the original artifact and the
reviewer's independent hash. This is a metadata correction, not new semantics.

Bounded public searches covered combinations of 80286/286, failed IRET, NMI
blocking, STI with IF already set, consecutive STI, TF/fault handlers, errata,
and physical tests. They produced no raw discriminating capture. The PCjs
exceptions archive proved to be a LOADALL-memo extract, not a separate new
interrupt clarification. Modern x86 and emulator material were leads only.
The earlier OS writer's guide/86BUGS/corpus research remains history; it was
not described as newly discovered evidence. No claim is made that every possible
source has been exhausted.

### User-requested emulator cross-check

A further source inspection followed the user's question about 86Box and
x86emu. The precise 86Box revision is
`62c26bac3050808ca8fec2c93e14fb678ac0a9ad`; `cpu.c` selects the 286 opcode
tables, including the `2386` interpreter table. This is implementation evidence
for the inspected path, not a claim about every build/backend or a physical run.

| Question | Inspected 86Box implementation | Architectural significance |
|---|---|---|
| STI old IF | [opSTI](https://github.com/86Box/86Box/blob/62c26bac3050808ca8fec2c93e14fb678ac0a9ad/src/cpu/x86_ops_flag_2386.h#L64) sets the interrupt-delay counter without testing old IF; a second STI resets it | Concrete unconditional/renewing alternative to SPK286's transition-only policy; the function cites no discriminating physical test |
| Failed IRET/NMI | [opIRET_286](https://github.com/86Box/86Box/blob/62c26bac3050808ca8fec2c93e14fb678ac0a9ad/src/cpu/x86_ops_ret_2386.h#L147) assigns nmi_enable before returning the abort flag on the inspected path | Suggests release despite a recorded abort; does not establish that the exact FFFF/FFFD/FFFB limit probes fault or preserve the same partial effects in this emulator |
| TF/fault | [Interpreter loop](https://github.com/86Box/86Box/blob/62c26bac3050808ca8fec2c93e14fb678ac0a9ad/src/cpu/386.c#L306) samples TF, but abort processing excludes the immediate else-if trap branch on that iteration | Relevant competing-event policy; later handler stepping also depends on fault-entry state and the next sampling boundary, so the branch alone is not a full oracle |

The reviewer additionally followed `x86seg_2386.c` into its included
[x86seg.c](https://github.com/86Box/86Box/blob/62c26bac3050808ca8fec2c93e14fb678ac0a9ad/src/cpu/x86seg.c#L85).
The normal real-mode abort-entry path saves the fault frame and clears live TF;
the next ordinary instruction sampling replaces the sampled TF bit. Together
these support a no-new-step implementation inference for completed entry, with
no claim about unusual entry faults, physical behavior or executed probe results.

For the ambiguous name x86emu, this inspection used
[wfeldt/libx86emu](https://github.com/wfeldt/libx86emu/tree/ce81129c57fdfbf690bebc210a8db97d926cc5e7),
revision `ce81129c57fdfbf690bebc210a8db97d926cc5e7`. Its README explicitly scopes
it to firmware execution rather than complete CPU emulation. Its STI function
sets IF with no local shadow mechanism. This source is not a claim that every
similarly named project lacks a detailed 286 model.

No physical capture or primary 286 discriminator was identified in the inspected
functions. A bounded issue search for STI/286 returned unrelated or insufficient
leads; further IRET/NMI and trap/286 API searches were rate-limited and are marked
unavailable, not negative results. No exhaustive history search or execution of
either emulator is claimed. Finding their original hardware tests or applicable
Intel citations could still close a question; implementation agreement alone
does not exclude the competing hardware behavior.

Exact retrieved source URLs/hashes are retained in ignored
`emulator-sources/sources.json` and copied into the recovery evidence inventory.
The independent reviewer checked this addendum's source findings separately in
`build/phase6-closure-review/EMULATOR_REVIEW.md`; it is included with the delivery
evidence, not silently added to the earlier frozen review. No third-party code
is incorporated into SPK286 or redistributed in the capture package.

## Executable capture preparation and limits

The [capture protocol](PHASE6_CAPTURE_PROTOCOL.md) and
[probe package](../research/phase6_probes/README.md) supply 21 portable NASM
configurations: 12 IRET/NMI trials/controls, 3 STI sequences and 6 TF/fault trials.
They include reset code, a complete IVT, writable memory/stack images, distinct
first-handler markers, post-observation nine-word dumps, disassembly, encoding
checks, image hashes, pin requirements, repeated controls and result templates.
No third-party source was copied into the probes or production CPU.

The byte-executing bounded mechanics interpreter runs 18 illustrative policy
combinations across all configurations. Its 378 synthetic runs demonstrate
payload mechanics and differing observations, not physical 286 semantics. It
uses instruction-start knowledge unavailable to a physical fixture and omits
native timing/prefetch/READY. It assumes ordered per-word IRET partial effects
for its own mechanical assertions; unexpected physical effects must remain raw
data. The NMI companion to C measures initial nesting only, because its terminal
NMI handler does not return to GP. No broader coverage is implied.

The strict standard-library result reader requires explicit physical/primary-
document/simulation/not-run provenance, artifact integrity, CPU/fixture identity,
state/stimulus and repeated-control references. It refuses missing captures,
synthetic substitutes, malformed hashes, unsafe paths, nonfinite numeric data,
NMI dump contamination and different-part controls. Unknown final values are
permitted only with an explicit inconclusive classification. Structural validity
does not prove physical authenticity, sufficient timing or architectural approval.

ArduinoX86 public source was pinned to
`2ccae6470ef2cc12e247b74e3ad2d226b7f74936`; source hashes and exact retrieved
URLs remain in ignored `fixture-sources/sources.json`. The fixture needs a
reviewed adaptation for physical reset/images, pin scheduling, full traces and
passive collection without automatic NMI/HLT injection. No such integration or
physical run occurred here. NOT-RUN templates are not positive test results.

## Changes and validation accounting

Production RTL, authoritative microcode/generated artifacts, event model,
physical corpus admission/comparison/masks, and the evidence gate are unchanged.
The POP-memory SP+2-before-destination-#GP correction and owed-TF-before-next-
opcode-demand-fault priority are preserved. Functional effects, physical bus
ordering and historical timing remain distinct; no clock-accuracy claim,
new mode, nominal-MHz conversion or FPGA ALM/Fmax estimate is made.

New executable work is confined to `research/phase6_probes/{build,mechanics,
results}.py`, its package initializer, NASM source, and `tests/test_phase6_probes.py`.
CI and bootstrap additionally declare NASM/NDISASM so a clean environment can
run those mandatory tests. These two existing environment inputs differ from
the old 147-file manifest; they are not CPU semantic changes. The other 145 old
executable inputs retain their exact tested bytes. The full new set has its own
manifest, so the original 147-file equality is claimed only for the entry audit.
New documentation includes this dossier, the protocol, probe README/schema and
refreshed review. Existing handoff/source notes/verification/decisions get closure
addenda; the exact final changed-file list is in the recovery manifest.

Retained full hardware cohorts are unchanged and counted only once:
**440,574 inherited normal + 1,423 inherited exceptions + 32,052 new-family =
474,049**, from 518,000 discovered with 43,951 prefix exclusions. No selected
failures/skips/revocations or exception exclusions are introduced. New physical
captures = **0**; new synthetic runs are separately counted.

New checks are recorded with exact commands, Linux subprocess statuses and log
SHA-256 in `build/phase6-evidence-closure/checks.json`. They include focused probe/
event-model/release tests, fresh assembly/encoding verification, 378 synthetic
runs, all 21 NOT-RUN records, expected rejection when physical evidence is
required, expected architectural-evidence exit 1, generated consistency and a
fresh ordinary `make regression`. That regression completed with actual Linux
make exit 0 and outer WSL/PowerShell exit 0: 156 Python tests, 59 compiler tests,
25 benches in each simulator, 1,932 event cases, 463 lifecycle scenarios,
96 streams/4,670 completions, dual reset smoke, 970 ordinary SingleStep smoke
cases and Yosys sanity passed. Smoke sampling is not full-corpus readmission.
The retained full physical and mutation counts above remain historical results.
No new full release gate was run. Exact commands, log hashes and result scope
are recorded in the dated [handoff](PHASE6_HANDOFF.md).

The final 155-input manifest SHA-256 is
`caaca2239e354007c63d5cf97754a64d5c9f9402d84a07da0631c8a2632136ef`.
Final integrity checks verify all 155 bytesets, the original archive hashes,
the unchanged real index, every compiled/synthetic artifact hash and the verbatim
review. Separate final-archive reconstruction and portable-package execution
results are retained in the delivery's `package-verification.json` and log.

The old complete release command was
`SPK286_BUILD_DIR="$PWD/build/phase6-final-3" make phase6-check`.
It remains an observed failure at architectural-evidence (checker 1, outer
PowerShell 1; inner make status **unknown**). Its 147 exact inputs and retained
reports were verified here. No full `phase6-check` rerun is warranted while the
same facts are unresolved and production CPU/model execution inputs are unchanged.
`PHASE6_VALIDATION_PASS` is not claimed. The new research source set has its own
fingerprint; its additions were not part of that old release's 147-file set.

After actual closure of all three questions and reviewer findings, require the
full fresh command in an absent directory:

```sh
SPK286_BUILD_DIR="$PWD/build/phase6-evidence-final" make phase6-check
```

Capture its real Linux make exit separately from outer-shell status. Preserve
every inherited cohort/mutant/comparator check, add evidence-backed competing-
behavior tests, obtain same-candidate approval, then commit/push the work branch
and verify its remote SHA. None of those release conditions is waived here.

## Independent review and smallest remaining external input

The historical `PHASE6_ARCHITECTURAL_REVIEW.md` is preserved. It reviewed the
earlier 204-scenario lifecycle stage, not automatically the later 463 scenarios.
The refreshed separate review is recorded in `PHASE6_EVIDENCE_REVIEW.md`, with
the exact source snapshot, primary artifacts personally inspected, probe/schema
findings and disposition. A reviewed capture-preparation package is not approval
of the unresolved Phase 6 architecture.

The reviewer accepted preparation within its stated limitations and retained
architectural disapproval. It independently checked all 192 frozen file hashes,
ran 23 focused tests (including 378 synthetic executions), and observed checker
exit 1. Its report SHA-256 is
`7ca39ed12902c5bf0a394a3f52974c1c919a66a0804246c62854efc83d683e46`.
Final handoff/log appendices, the ordinary regression and recovery export are
outside that frozen review; their separately recorded checks are not silently
attributed to the reviewer. Executable inputs retain the reviewed byte hashes.

For A obtain valid first-NMI, queued-edge and failing-IRET bus/frame/marker
captures across all three failing words and successful/no-edge/held-high controls.
For B obtain a timing-valid old-IF=1/renewal discriminator; if the required short
STI window cannot be demonstrated, provide an independently validated alternative
experiment or explicit Intel 286 clarification. For C obtain TF=1 #GP frame/
marker data with and without pending NMI plus TF=0, successful-target and explicit
restoration controls; keep #UD scope separate. Record actual part identity and
raw bytes. The existing physical corpus omits these behaviors.

No commit or publication of the unverified implementation is made. Remote
credentials and CI are not the blocking issue examined here; no new remote SHA
or CI result is claimed. Work is recoverable from the new snapshot, with the
old package kept intact. Phase 7 has not started.

## Development disposition — 2026-09-08

D-026 permits incremental Phase 7 development on a freshly executable-validated
provisional Phase 6 baseline. This supersedes the earlier prohibition on Phase 7
development, not this report's historical findings or withheld architectural
approval. `failed-iret-nmi`, `sti-old-if` and `fault-tf` remain unresolved under
their unchanged candidate policies. See PHASE7_SCOPE.md and the current
development handoff for later validation and Git identities.
