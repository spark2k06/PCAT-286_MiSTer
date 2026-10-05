# Phase 7 functional/development closure — 2026-09-09

**Phase 7 milestones 1–9 are delivered and functionally/development ready under
D-037.** Strings/REP and scalar/string I/O are integrated in ordinary repository
sources with the delivered arithmetic baseline. Complete executable validation
and independent functional approval cover the exact source and policy below.
The five named evidence notes remain open and nonblocking; historical 80286
timing and complete architectural fidelity are not certified.

The new [independent report](PHASE7_FUNCTIONAL_REVIEW_20260909.md),
[machine-readable validation](phase7_functional_validation.json) and
[completion record](phase7_completion.json) supersede the earlier blocked
candidate status. The [old independent review](PHASE7_INDEPENDENT_REVIEW_20260909.md)
and [old correction report](PHASE7_REVIEW_CORRECTIONS_20260909.md) retain their
actual conclusions under the earlier policy; they have not been changed into
an approval.

## Integrated and reviewed identity

| Input | Identity |
| --- | --- |
| Integration base | `e2bc4a7839cd0aa594b543d8dcaaf253c310a63a` |
| Working branch | `codex/phase7-realmode-completion` |
| Frozen executable inputs | 337; `cbf2f3d7a9cef89ffd268d333d1716d93ae1e4f8d5e77f6308ddd2c057cbc4e5` |
| Frozen acceptance-policy inputs | 10; `7d16bb0a6422bb1d71cf1fe9a665158ca77dc02495e12ae7d1fe7c55974fb9bf` |
| Hardware-derived corpus | SingleStepTests/80286 `37c73caf53dcd22d3dd369ff09305d13d117a4fe` |
| Executed simulator SHA256 | `e5d36905fd4a6e64b471b7948d625c0884fee97e6d3c157a34d27b04e81d808b` |
| Verified execution receipt SHA256 | `e8096fc6b30284aaa5a0716fe860beb79d0819abc85118e6c32a3977e9841a0f` |

The [executable manifest](phase7_functional_executable_inputs.json) and
[policy manifest](phase7_functional_policy_inputs.json) are retained verbatim.
All 47 RTL/microcode files match the recovered corrected candidate. Source `.mc`
files were regenerated normally; no generated artifact was hand-edited.
The active image has 100 entries, 612 words, 10-bit addresses and 8-bit control.

Final review and delivery documentation are outside normative input hashing.
Equality of the 337 executable and 10 policy inputs was checked after that
overlay. The exact full source manifest, file modes, Git tree and implementation/
delivery commit are recorded in the final package and external delivery receipt;
the commit containing this record delivers the integration and acceptance tools.

## Fresh executed results

| Check | Fresh result |
| --- | --- |
| Ordinary Python suite | 261 passed |
| Separate compiler suite | 88 passed |
| Generated microcode / Verilator lint | PASS |
| RTL banks | 59 in each of Verilator and Icarus, PASS |
| Corrected string-I/O lifecycle | 400 cases / 35,477 checks per simulator, PASS |
| Zero-count completion/event cases | 70 memory + 56 I/O, both simulators PASS |
| Complete required hardware-derived cohort | 1,386,996 PASS + one NOT EVALUABLE; all 307 files |
| Intended RTL mutations | 176 detected with pristine controls |
| Arithmetic / combined adapter / scalar-port comparison audits | PASS; 176 / 188 / six intended comparison failures detected |
| Independent synthetic word OUT | Four cases PASS; zero physical captures |
| 86Box original functions / ordinary RTL differential | 28 / 16 cases PASS, separate from physical coverage |
| Mapped synthesis | 17,300 cells / 1,398 sequential, PASS |
| Broad regression | 2 required passes |
| Source/policy consistency and independent functional approval | PASS |

The complete local execution is `build/phase7-functional-full-1`. Its five
completed stages, detailed outputs, binaries and batches are bound by
`execution-receipt.json`. The aggregate log is retained separately as
`build/phase7-functional-full-1.log`. The independent reviewer inspected the
completed results before approving the functional scope. Final
`make phase7-check` verifies that receipt, every retained artifact, exact current
source/policy equality, population accounting and the independent approval.
Reusing that verified receipt for finalization is explicitly recorded; it is
not described as another simulator execution.

The Windows-to-WSL launcher's inline postamble expanded its exit-status variables
prematurely; its outer status capture is invalid and is not used as PASS evidence.
The actual gate scripts kept their checked commands and `set -e`/`pipefail`.
The complete verified five-stage receipt and subsequent direct-argv finalization
with actual status zero establish the result. The separate launcher incident,
reproduction and finalization logs are preserved and assessed by the reviewer.

All 307 required files are represented. The discovered population is 1,387,000;
the three original upstream revocations remain unchanged. The resulting required
population is **1,386,997: 1,386,996 evaluable passes plus exactly one NOT
EVALUABLE record**. There are zero executable failures and zero unexpected
omissions. The 19 original out-of-scope files remain unchanged. Per-file counts,
exact indexes/hashes, raw source Git blobs and category disjointness are checked.
The final evaluable categories are 474,049 legacy, 43,951 legacy-prefix and
868,996 new-form records. These are fresh replays of hardware-derived tests,
not new hardware captures or an addition of historical and current run totals.

The main run detects 190 intended RTL mutations with pristine controls. The
reviewer's three independent zero-count-event mutations are separate evidence,
as are parser/compiler/comparator negative tests. The compiler and ordinary
Python suite counts overlap and must not be added as distinct test populations.

## Evidence and practical reference limits

The five open notes are `failed-iret-nmi`, `sti-old-if`, `fault-tf`,
`rep-zero-count-event-order` and `e7-incomplete-physical-capture`. Their exact
policies, provenance, executable coverage and future evidence needs remain in
the [versioned register](phase7_evidence_notes.json). Its review requirement and
the form inventory's gate requirement are contracts fulfilled by the separate
bound completion record, not unresolved functional review statuses.

The zero-count tests discriminate accepted-opcode completion from normal
pre-instruction event recognition. Their 70 memory-string and 56 string-I/O
cases pass in both simulators. They support the selected engineering policy;
physical confirmation remains open. The separate nonzero REP/TF documentary
disposition and its limited inference are preserved.

E7 index 1100, hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e`, retains its strict
`incomplete captured I/O cycle` diagnostic. Independent original-byte/pinned
parser inspection confirms absent write strobe/payload evidence. It is neither
revoked nor counted as PASS. The other 4,999 E7 records pass. Four separately
specified synthetic word-OUT cases, including the same initial AX/IP and port,
pass ordinary architectural and logical-port comparison; no expected physical
transaction is manufactured from AX.

The [86Box experiment](PHASE7_EMULATOR_REFERENCE.md) executes 28 cases using
original pinned functions and compares 16 ordinary cases with SPK286. The
reviewer independently rebuilt the original-function harness. Event-loop
delivery is inspected statically; its execution is not stubbed into a claimed
priority result. Emulator evidence is not a hardware observation or timing
certificate. Licensed reference code stays isolated from synthesizable RTL.

Earlier failed synthetic-fixture and CLI-preparation attempts are retained
separately. The missing expected instruction RAM in the synthetic fixture and
the split exception-class identity under `python -m` were corrected in tooling;
CPU comparisons and expected architectural semantics were not softened. Prior
review repairs, accepted-value-varying INS stimuli and the nineteenth I/O mutant
remain in the delivered tests. Further review corrections strengthened receipt
artifact coverage, integer schema validation and recovery source inventory.

## Delivery, recovery and next phase

The [recovery guide](PHASE7_FUNCTIONAL_RECOVERY.md) identifies the final archive,
checksum sidecar, canonical source/mode manifests, exact evidence receipt and
isolated native-Linux verification procedure. The external
`build/phase7-functional-delivery.json` records exact base, implementation,
delivery and remote commit identities, CI observations for that revision and
the actual final recovery result. A package-time queued/running CI observation
is not a success claim; completion is recorded in the later external receipt.

`make phase7-evidence-check` remains strict and reports all five open notes.
`phase6-check` retains its original strict architectural contract. Those known
evidence statuses are separate from the successful functional gate and CI.
E7 issue publication remains pending by user request; no issue or external
message was published.

Phase 8 may begin from this accepted functional baseline under the same explicit
notes. [Preparation](PHASE8_PREPARATION.md) remains a design note. No Phase 8,
Protected Mode, LOADALL, coprocessor support, machine integration or historical
timing profile was implemented in this task.
