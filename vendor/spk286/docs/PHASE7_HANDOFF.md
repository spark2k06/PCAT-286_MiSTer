# Phase 7 implementation handoff — 2026-09-08

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

Latest continuation (2026-09-09): the independent review and corrected-boundary
review are complete. R1/R2/R3 are closed in a recoverable isolated candidate;
no additional instruction increment is integrated. REP CX=0 and E7 admission
remain blocking. [The closure dossier](PHASE7_CLOSURE_20260909.md) provides final
identities, actual new/reused validation, recovery and Git/CI delivery status.
[Phase 8 preparation](PHASE8_PREPARATION.md) is complete as a design note only.
The new full regression passed (256 ordinary / 88 compiler tests, 57 benches in
each simulator, mapped synthesis 17,300 / 1,398 cells). The closure archive's
1,663 payloads and restored 412-file / 328-executable-input identities were
verified, followed by passing restored completion tests and microcode checking.
Use the [recovery guide](PHASE7_CLOSURE_RECOVERY.md) and current candidate JSON;
actual documentation commit/push/CI observations are in the post-package local
delivery receipt referenced by the dossier and final task response.
Historical implementation/review-status paragraphs below retain their dates.

Status: **user milestones 1-6 delivered; complete Phase 7 remains incomplete**.
The latest arithmetic gate passed on 295 unchanged executable inputs, with
1,288,997 disjoint physical cases. The delivered arithmetic section at the end
records the latest verified state. Earlier sections preserve historical work
and must not be read as the current missing-form inventory.

## Preserved baseline and Git identity

- Original HEAD: `03c32df5c2d5edcb4606564d1dba215d26640116`.
- Original staged tree: `94fcf66a13ca6a1d618feeff37a48c886d37aa86`.
- Original combined recovery tree: `5938abf0c2f68cb26f71da294bc2c4606c1d26b7`.
- Both original recovery archives/manifests verified; no archive overlaid the
  user's combined staged/unstaged/untracked candidate.
- Verified provisional Phase 6 commit: `52e73cb8ece39621e89cbaf77f59d88581788e54`.
- Baseline branch: `codex/phase6-interrupts-exceptions`; pushed and remote SHA
  verified as the exact commit above. Its GitHub Actions run is
  [34230975610](https://github.com/spark2k06/SPK286/actions/runs/34230975610)
  completed successfully, verified 2026-09-08; architectural evidence is pending.
- Current work branch: `codex/phase7-realmode-completion`.
- No main/master push or merge, history rewrite, branch deletion, independent
  review approval or Phase 8 work occurred.

Phase 6's three architectural questions remain unresolved: `failed-iret-nmi`,
`sti-old-if`, `fault-tf`. D-026 authorizes provisional development; the strict
architectural gate remains failing. Their status is not the reason this phase
remains incomplete.

## Implemented increment

Byte/word operand and lane machinery; B0–B7; 88/8A; C6/C7 /0; byte ADD, OR, ADC,
SBB, AND, SUB, XOR, CMP in register/RM/accumulator/immediate forms; owned invalid
C6/C7 groups; segment/LOCK/F2/F3 accumulation for currently supported non-string
instructions; ten-byte #GP and restart IP including prefixes; LOCK/HOLD ownership.

One architectural register owner, one physical BIU owner and generic
microsequencing remain. Format 6 has 37 entries/174 words, eight-bit addresses,
six-bit controls and deterministic source maps. Frozen format 1–5 fixtures are
preserved. Immediate ALU forms acquire instruction bytes before data access.
See D-027 and the updated microcode, bus and state interface documents.
F2/F3 accumulation is exercised by directed scalar context tests; no physical
REP/string execution pass is claimed. The readmitted scalar corpus exercises
segment/LOCK prefixes, not completed repeated-string semantics.

## Evidence already obtained

The final integrated 150-file run passed 737,998 distinct records:

| Category | Count |
|---|---:|
| Preserved Phase 6 cohort | 474,049 |
| Readmitted prefixes from old families | 43,951 |
| New byte/immediate-MOV forms | 219,998 |
| Total executed/passed | 737,998 |
| Upstream revocations, separate from execution | 2 |
| Discovered | 738,000 |

All full-run selection/prefix/exception skips and selected failures were zero.
This is a subset of the pinned 326-file inventory (307 required, 19 explicitly
excluded files). The complete physical inventory has 1,478,000 records and three
revocations. Counts in phase7_forms.json are inventory, not implicit passes.

Final directed results, rerun in both simulators: 589,824 exhaustive byte ALU cases; 6,256
full-CPU byte/scalar vectors; 130 operand-byte cases; 140 width/I/O BIU cases;
51 prefix/length/event/LOCK scenarios. The final gate ran all 30 benches in both simulators, 175 ordinary Python tests
and 62 compiler tests. It passed all seven new and 46 inherited intended RTL
mutation failures with pristine controls, 67 + 1,844 comparator negatives,
physical/parser audits, traces, smoke, synthesis and the complete regression.

## Isolated I/O work and concrete new blocker

IN/OUT has an isolated prototype: 41 entries/190 words, all eight opcode forms,
byte/word immediate/DX ports, zero-extension and physical carry on odd word I/O,
strict captured port transaction comparison and an independent FF responder.
It passed 35,000 cases in seven complete families, 452 directed cases in both
simulators, compiler/lint checks and six intended comparator negatives.

E7's full run fails on the non-revoked incomplete IOW capture at index 1100,
hash `c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e`. The upstream parser confirms the
same missing strobe/data. No local revocation, expected-data fabrication or
silent exclusion was applied. See [PHASE7_IO_CAPTURE_REVIEW.md](PHASE7_IO_CAPTURE_REVIEW.md)
for the reduced evidence and smallest remaining external action. This prototype
is not part of the production increment or its pass counts.

## Unmet Phase 7 requirements

60 required opcode files remain absent from the current integration registry. Remaining
work includes segment operations and far transfers; LES/LDS;
remaining multiply/divide/#DE groups;
PUSHA/POPA/ENTER/LEAVE/BOUND/#BR; strings and
restartable REP; scalar and string I/O integration. Full event/SS-load/repetition
semantics, complete lifecycle/stream/mutation coverage, full-scope gate and focused
independent review are pending. The revised restart contract also records eleven
physical string-fault examples, independently parsed within all 29,000 records
in seven word-string files. These expose partial SI/DI/CX effects, different
MOVS/CMPS access order, and an irreversible INS read before a destination fault;
they are research observations and are not included in RTL pass totals. Phase 8 was not started and is not ready on this
incomplete phase.

`make phase7-check` deliberately fails this incomplete scope. The separate
`make phase7-byte-prefix-check` verifies only the named increment; it cannot emit
`PHASE7_DEVELOPMENT_VALIDATION_PASS`. Its gate invokes the full inherited
executable gate and separately audits all readmitted/new cases and identities.

## Reproduction and artifacts

Use WSL Ubuntu 24.04 with Python 3.12.3, Verilator 5.020, Icarus 12.0, Yosys 0.33
and NASM 2.16.01. The physical corpus revision is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. No corpus file was changed.

- Baseline: `SPK286_BUILD_DIR="$PWD/build/a-fresh-name" make phase6-exec-check`.
- Increment: `SPK286_BUILD_DIR="$PWD/build/another-fresh-name" make phase7-byte-prefix-check`.
- Complete phase status: `make phase7-check` (currently fails missing scope).
- Strict architectural status: `python3 -m tools.phase6_evidence` (currently fails).
- Local preparation logs/results: `build/phase7-preparation/`.
- First increment gate: `build/phase7-byte-prefix-final/` (failed audit anchor).
- Second gate: `build/phase7-byte-prefix-final-2/` (failed stack mutation anchor).
- Third gate: `build/phase7-byte-prefix-final-3/` (failed prefix probe selection).
- Final fresh gate: `build/phase7-byte-prefix-final-4/` (PASS from a clean corpus).

The complete reproducible record is [phase7_byte_prefix_validation.json](phase7_byte_prefix_validation.json).
The actual Linux make status was 0; elapsed time was 1,719.056 seconds.

- Input manifest SHA256: `4184a88864f28577221081513d53319e572b5a44b8d5f34b10e7d5083c035981`.
- Final log SHA256: `ddedc56e977a89f2633c6ef829ac91810d87ccdfc44b71477d12a59753d7120c`.
- Verified 392-entry evidence archive: `.cache/phase7-byte-prefix-validation-20260908.zip`.
- Archive SHA256: `f97736c3874a5f74fe6cfd2d9440ca5073c49adbd3c4359718d103bfda462cb6`.
- Yosys mapped/sequential cells: 9,882/960, versus baseline 9,308/945; delta +574/+15.
- All source fingerprints and corpus-form hashes matched after the run. There is no historical-cycle-accuracy claim.

The run used `SPK286_SINGLESTEP_ROOT="$PWD/.cache/phase7-clean-corpus-150"`
and `SPK286_BUILD_JOBS=4`; build parallelism affects host compilation only.
The original complete pinned corpus remains untouched. Implementation commit `6caa746784c06a17a18b459b1f228a5843894465` was pushed to
`codex/phase7-realmode-completion`; its exact remote tip was verified. GitHub
Actions run [34244293932](https://github.com/spark2k06/SPK286/actions/runs/34244293932)
completed successfully at 2026-09-08 16:02:12 UTC; the exact run and commit were verified.

### Failed first integrated run and recovery integrity

The first integrated gate returned Linux make status 2 at the inherited
`word-limit-wrap` mutation anchor. Its old expression no longer existed after
the byte-width extension. Log SHA256:
`ce55a70d57ddb22a8a539a26e08fa99e4cfaf43c6655b30c4c46b7d8853bf159`.
The same truncating mutation was adapted to the width-dependent sum; both
pristine benches and all four intended assertion failures pass. The corrected audit passed in the final complete run. This failed attempt
remains a failed historical record.

I/O recovery is `.cache/phase7-io-recovery-20260908/`; its 223-file archive,
manifest, individual file hashes, safe extraction, compiler consistency and
18-file patch applicability were verified. The capture review records hashes
and every known missing validation. No unverified I/O source is staged.

The second fresh increment run also stopped with make status 2, this time at
the obsolete `stack-segment` mutation anchor after the complete Phase 5 corpus
passed. Its log SHA256 is
`39d4342a27671371584664a7a71640ff5b549284aaeb0366ac5a98b1226dd971`.
The repair keeps the non-stack segment-override expression intact and still
forces stack operations through DS, with the same ordered-address assertion.
All 53 mutation anchors now pass a new early unit check; actual semantic
mutation rejection remains required. Neither failed gate is relabeled as passed.

The third complete attempt passed the 737,998-case physical cohort and strict
identity accounting, then failed a comparator sample selection with make status
2. Log SHA256:
`b539f036d04e20e076740df4a6e81b2255f400118f6b1a69adfcfe4d55d90fcb`.
The auditor had treated the opcode after a prefix as a ModR/M byte and selected
a register-only MOV as a memory probe. Selection now uses actual captured
operand traffic and excludes exception-handler traffic. All 67+1,844 comparator
negatives and pristine controls pass with prefixes enabled after that fix.

The downloader also omitted 44 newly active source files. Its active-registry
request list and regression test now cover all 150. A fresh public-remote
checkout in `.cache/phase7-clean-corpus-150` matches every pinned form blob and
has clean Git status. The fourth gate uses this clean source and four host C++
compiler jobs (`SPK286_BUILD_JOBS=4`). A focused dual-simulator prefix build
verified the parallel-build option; RTL simulation itself remains unchanged.
The I/O recovery archive predates this downloader fix; its reproduction guide
uses the original complete pinned corpus, not a fresh download by that prototype.

## Verified scalar increment

This increment adds TEST's six forms; INC/DEC register encodings 40–4F;
CBW/CWD; CLC/STC/CMC, CLD/STD and SAHF/LAHF. Its 31 complete physical files
passed 63,000 prototype records with zero revocations/skips/failures, disjoint
from the verified byte cohort. Directed runs passed 2,236 TEST and 1,968
direct-scalar cases in both simulators; compiler/lint and seven new intended
mutants passed. Format 7 contains 42 entries/193 words and preserves prior words.
The active registry has 181 required files; 126 remain absent.

Fresh integrated `make phase7-scalar-check` passed in
`build/phase7-scalar-final`, using the verified clean 181-file checkout
`.cache/phase7-clean-corpus-181` and four host build jobs. Actual Linux make
status was 0; elapsed time was 1,930.827 seconds. All 800,998 disjoint cases
passed (737,998 prior + 63,000 new), with no required selection/exception/prefix
skips or failures. The gate passed 182 ordinary tests, 65 compiler tests, all
32 benches in both simulators, 60 intended RTL mutants with pristine controls,
inherited event/stream/comparator checks, lint, smoke, synthesis and regression.
All 191 source fingerprints and the form manifest matched after execution.

- Complete record: [phase7_scalar_validation.json](phase7_scalar_validation.json).
- Log SHA256: `250b050dd1136e7bb4dd53f329dd4ec3221d5030920ea672e088d2fb704465ab`.
- Verified 455-entry archive: `.cache/phase7-scalar-validation-20260908.zip`.
- Archive SHA256: `9acd91dd96c15d6170f75050f8d7749eb3a4226ac1515475ab97d18a532b56ea`.
- Yosys mapped/sequential cells: 10,213/963; delta +331/+3 from the byte increment.
- Reproduce: `SPK286_BUILD_DIR="$PWD/build/a-fresh-scalar-run" make phase7-scalar-check`.

These results belong to this increment and do not alter the earlier byte/prefix
commit's historical validation record. Complete Phase 7 implementation and
independent review remain pending. Shift/rotate results belong to the following
separate increment and are excluded from the scalar snapshot counts.

The verified scalar increment was committed as
`ba61ffd85a067ce03d046ef88d00b46ce82ffcf9` and pushed to
`codex/phase7-realmode-completion`; the remote SHA matched exactly. Its CI
run [34249382779](https://github.com/spark2k06/SPK286/actions/runs/34249382779)
completed successfully, verified against the exact scalar commit on 2026-09-08.

## Verified shift/rotate increment

All 42 documented shift/rotate files passed 210,000 physical prototype cases.
The arithmetic bench passed 154,112 independent vectors (3,468,497 checks) and
the complete CPU bench passed 12,222 cases (1,499,227 checks; 5,152 immediate
stalls), each in both simulators. The prototype audit passed 189 ordinary tests,
67 compiler tests, lint, nine new intended mutants and the inherited ALU audit.
Its disjoint identity summary is 800,998 prior + 210,000 new = 1,010,998.
These checks were rerun in the complete integrated gate described below.

The first physical run failed 13,166 multi-count OF comparisons; the reduced
trace and independent mask evidence explain the corrected policy in
[PHASE7_SHIFT_FLAGS.md](PHASE7_SHIFT_FLAGS.md). An intermediate command failed
before execution because its corpus path variable was wrong. The first mutation
audit rejected the CL-source defect on the earlier zero-count-write assertion,
but expected the later GPR assertion; the audit now requires the precise earlier
semantic failure. Neither failed attempt is relabeled as a pass.

Fresh integrated `make phase7-shift-check` passed in `build/phase7-shift-final`,
using the new clean 223-file pinned checkout `.cache/phase7-clean-corpus-223`
and four host compiler jobs. Actual Linux make status was 0; elapsed time was
2,416.800 seconds. All 1,010,998 disjoint physical cases passed with no required
selection/prefix/exception skips or failures. The gate passed 189 ordinary tests,
67 compiler tests, all 34 benches in both simulators, 69 intended RTL mutants
with pristine controls, inherited event/stream/comparator audits, lint, smoke,
synthesis and complete regression. All 206 input fingerprints and the form
manifest matched at the end. The three Phase 6 architectural questions remain
pending, and no strict architectural PASS was emitted.

- Complete record: [phase7_shift_validation.json](phase7_shift_validation.json).
- Log SHA256: `3c94d13dfa349fd6bc3750206f3174bbaf444041696881e23f8a7f3d828b0900`.
- Verified 569-entry archive: `.cache/phase7-shift-validation-20260908.zip`.
- Archive SHA256: `e5833e4d9029b741faf1811cdce4655961001bdb4e6180246ff0e4c3f8131296`.
- Yosys mapped/sequential cells: 10,681/1,018; delta +468/+55 from the scalar increment.
- Reproduce: `SPK286_BUILD_DIR="$PWD/build/a-fresh-shift-run" make phase7-shift-check`.

Format 8 contains 48 entries/235 words with stable source maps and prior words.
At that snapshot, 84 required files remained absent and independent review was pending.
Data-transfer results do not add to the shift commit's physical pass count.

The verified shift increment was committed as
`f2b861f2aaf394927cc32d3b3a8f2e4c64c1f757` and pushed to the work branch;
the remote SHA matched exactly. CI run
[34255473034](https://github.com/spark2k06/SPK286/actions/runs/34255473034)
completed successfully, verified against the exact shift commit on 2026-09-08.

## Verified data-transfer increment

The sixteen-file prototype passed all 48,000 physical cases with zero selected
skips/failures/revocations. Directed CPU and lifecycle benches passed 5,690 and
55 cases in both simulators, including 1,932 instruction-byte stalls and partial
exchange commits. Prototype checks passed 194 ordinary tests, 69 compiler tests,
lint, eight new intended RTL mutants, all seven affected legacy benches in both
simulators, synthesis and the full parser/comparator audit. Prototype Yosys
mapped/sequential cells were 11,345/1,037; the integrated gate must recompute them.

The first compiler attempt failed an outdated version-9 rejection test and an
incomplete exchange protocol that incorrectly reached the older validator.
Format 9 is now valid, and the compiler now recognizes and rejects that missing
writeback. The failed log/result remain in build/phase7-preparation.

Only forty checked changed/new source paths were integrated from the isolated
prototype after the verified shift commit was pushed. No old prototype handoff
or validation record replaced current documentation. Format 9 contains 57
entries/282 words; the current registry contains 239 required files with 68
absent. See PHASE7_DATA_TRANSFER.md and D-030 for the functional contract.

A new clean pinned 239-file checkout is .cache/phase7-clean-corpus-239; every
requested blob and clean Git status were verified. The fresh integrated gate
passed as recorded below. Independent review, remaining Phase 7 implementation
and complete-phase delivery remain pending.

The first integrated data gate failed before RTL execution because the audit CLI
still selected the prior shift fixture by default. The default now selects the
independent data fixture. A CLI test checks default success and explicit stale-
contract rejection; no expected word is changed. The failed gate is preserved as
build/phase7-data-final (actual make status 2). The retry uses a new directory;
its ordinary/compiler requirements increase to 195/70 after this regression test.

The new CLI regression also exposed stale format_version=8 in the new data
fixture, despite its encoding_version=9 and correct 282 literal words. The
metadata now consistently states the designed format 9; the test explicitly
checks all version/width fields. No RTL result, expected word or physical
expectation was changed by this tooling correction.

The fresh retry `make phase7-data-check` passed in `build/phase7-data-final-2`,
using the clean 239-file pinned checkout and four host build jobs. Actual Linux
make status was 0; elapsed time was 2,617.383 seconds. All 1,058,998 disjoint
physical cases passed with no required selection/prefix/exception skips or
failures. The gate passed 195 ordinary tests, 70 compiler tests, all 36 benches
in both simulators, 77 intended RTL mutants with pristine controls, inherited
event/stream/parser/comparator checks, lint, smoke, synthesis and regression.
All 217 input fingerprints and the form manifest matched after execution.
The three Phase 6 architectural questions remain pending; no strict
architectural PASS or complete Phase 7 approval was emitted.

- Complete record: [phase7_data_validation.json](phase7_data_validation.json).
- Log SHA256: `e7789650ae62fbc413e21232cd7557761f1135969870dd09ea2b8ecb45a1c41e`.
- Verified 622-entry archive: `.cache/phase7-data-validation-20260908.zip`.
- Archive SHA256: `9bd0bc2872411ae44ecacc675eb01e661ee93a978b0d875ea0d29c1aeea74f39`.
- Yosys mapped/sequential cells: 11,345/1,037; delta +664/+19 from the shift increment.
- Reproduce: `SPK286_BUILD_DIR="$PWD/build/a-fresh-data-run" make phase7-data-check`.

The unary/dispatch prototype is separately verified and not part of this data
snapshot. Its results are excluded from this increment's physical pass total.

The verified data increment was committed as
`d6cf76d373566db52abc675a1bf66caf3a11a459` and pushed to the work branch;
the remote SHA matched exactly. CI run 34260676954 completed successfully for
that exact data commit.

## Verified unary/dispatch increment

The isolated prototype passed all 40,000 new physical cases and 25,000 affected
prior TEST/near-control cases; the latter are not added twice. The strict
combined summary contains 1,098,998 distinct identities. It passed 202 ordinary
tests, 74 compiler tests, lint, 10,832 CPU cases/810,712 checks and 70 lifecycle
cases/3,170 checks in both simulators. Expanded sequencer/operand units passed
59 and 12,111 checks respectively, and affected TEST/stack-control units passed
in both simulators. Ten new intended RTL mutants and the inherited scalar audit
passed. Prototype mapped/sequential cells were 11,631/1,038; integrated synthesis
must recompute the result. The full parser/comparator audit passed from the
new clean pinned 247-file checkout .cache/phase7-clean-corpus-247.

The first three mutation audits expected later register assertions; actual
injected defects were rejected earlier by FLAGS, memory and FLAGS assertions.
The audit reasons now name those exact failures. Failed logs/results remain
failed and CPU expectations are unchanged. See PHASE7_UNARY_DISPATCH.md.

After the verified data commit was pushed with a clean tree, 39 checked paths
were integrated; all baseline and prototype hashes matched. Format 10 has
65 entries/328 words; no prior word/entry moved. The fresh complete retry of
`make phase7-unary-check` passed as recorded below. The registry contains 247 required files
with 60 absent; complete Phase 7 implementation and independent review remain
pending. The separate adjust prototype contributes no passes to this snapshot.

The first integrated unary gate failed because an inherited negative stack test
still selected FF /0 and /1 as unsupported. Intel's documented INC/DEC encodings
and the new full physical families establish that these now execute normally.
Only that test's selection was narrowed to the still-invalid FF /3, /5 and /7;
all fault assertions remain unchanged. The failure, direct reproducer, and
successful 180-case/11,288-check rerun in both simulators are retained. This
additional verified test change followed the original 39-path integration.

The fresh retry passed in `build/phase7-unary-final-2` using the clean pinned
247-file checkout and four build jobs. Actual Linux make status was 0; elapsed
time was 2,857.252 seconds. All 1,098,998 distinct physical records passed
with no selected skips or failures. All 202 ordinary tests, 74 compiler tests,
38 benches in both simulators, 87 intended RTL mutants and inherited parser,
comparator, event/stream, lint, smoke, synthesis and regression checks passed.
The 228 executable input fingerprints and form manifest matched after the run.
The three inherited Phase 6 architectural questions remain pending.

- Complete record: [phase7_unary_validation.json](phase7_unary_validation.json).
- Log SHA256: `5bec6edf8cb71ba4eda1bc51bd27b575957766170e08f609771ec8002ba79111`.
- Verified 661-entry archive: `.cache/phase7-unary-validation-20260908.zip`.
- Archive SHA256: `f2b4152a6f8d426eb0f2f1ed6ff31546974ed648651786cb1ac5776e2490b012`.
- Yosys mapped/sequential cells: 11,631/1,038; delta +286/+1 from data transfers.
- Reproduce: `SPK286_BUILD_DIR="$PWD/build/a-fresh-unary-run" make phase7-unary-check`.

The decimal-adjust and segment prototypes remain isolated and are excluded from
this increment's pass total. Complete Phase 7 and independent review remain pending.

The verified unary increment was committed as
`09f29929aca9ff7dfa1bde0f2b2c0926e9d8ed56` and pushed to the work branch;
the remote SHA matched exactly and the working tree was clean. CI run
34268932346 completed successfully for that exact commit.

## Verified decimal/radix adjustment increment

After unary delivery, 38 paths were integrated from the isolated adjustment
prototype, with every baseline/prototype byte hash checked before copying.
The six added files passed all 30,000 physical records, including eleven
zero-radix AAM #DE frames. Independent arithmetic, 8,184 CPU cases and 157
lifecycle scenarios passed in both simulators; twelve intended mutations and
inherited ALU mutations were rejected. Prototype synthesis measured 12,445
mapped/1,120 sequential cells (+814/+82 from unary). This result must be
recomputed by the fresh integrated gate.

The prototype passed 207 ordinary tests, 76 compiler tests, lint and generation
consistency. A clean pinned 253-file checkout passed every blob hash and the
full independent parser/comparator audit, including 67 normal and 1,851 event
negative comparisons. Its disjoint summary is 1,128,998 records. The first
summary invocation used a nonexistent data-report path and failed; the corrected
path passed, with both original results retained. Earlier service/testbench
observation and coverage failures remain recorded in PHASE7_DECIMAL_ADJUST.md.

Format 11 has 67 entries/342 words; all prior words/entries are preserved.
The active registry has 253 required files and 54 remain absent. The fresh full
`make phase7-adjust-check` passed in `build/phase7-adjust-final`:

- Linux make exit 0; elapsed 3,091.085 seconds; all 242 executable inputs unchanged.
- 1,128,998 disjoint physical records passed; 30,000 new adjustments, zero failures/skips.
- 207 ordinary and 76 compiler tests; all 41 benches in both simulators.
- All 99 intended RTL mutants rejected with pristine controls; lint, smoke,
  parser/comparator audits, synthesis and the complete regression passed.
- Yosys measured 12,445 mapped / 1,120 sequential cells, +814 / +82 from unary.
- Log SHA256: `da50885b0ab23d693e17e0c9f51c63dcc33406a25e8e94bb7ac6299bf014d6ad`.
- Verified 809-entry archive: `.cache/phase7-adjust-validation-20260908.zip`.
- Archive SHA256: `656cce3739e0f2cf3177ac72f5e89d9d64812e5621c0d8e29be1f5b9fc788669`.
- Complete record: [phase7_adjust_validation.json](phase7_adjust_validation.json).

The first integrated focused invocation supplied three bench names to a script
that accepts one. It ran the arithmetic bench only; a separate recorded run
then passed the CPU and lifecycle benches individually in both simulators.
The full gate subsequently ran every registered bench. No omitted run was
counted as executed. The segment prototype remains isolated and contributes
no cases to this total. Independent review and complete Phase 7 remain pending.

## Integrated segment-transfer candidate

After adjustment delivery at `5d16c3b4fb444a54a26bf0146c4aa9d1b1450a3e`,
35 paths were copied after checking every original and prototype byte hash.
The isolated prototype passed 45,000 full physical cases, 4,800 CPU cases and
42 lifecycle scenarios in both simulators, 212 ordinary tests, 78 compiler
tests, lint, generation consistency and ten new plus 22 existing event mutants.
A clean pinned 262-file checkout passed all blob checks and the independent
parser audit, including 67 normal and 1,851 event negative comparisons.
The strict disjoint summary is 1,173,998 cases. Prototype synthesis measured
12,624 mapped / 1,121 sequential cells; integrated synthesis must recompute it.

Format 12 has 71 entries/356 words and preserves all 342 prior words. The
registry contains 262 required files; 45 remain absent. Fresh integrated
`phase7-segment-check` is pending. Stack/frame work remains isolated and adds
no cases to this candidate. Complete Phase 7 and independent review are pending.

## Combined segment and stack/frame candidate — 2026-09-09

The initial `build/phase7-segment-final` run was interrupted: its log ends in
Hangup and no full-gate completion result exists. It is not a PASS. Before
further integration, all 253 captured executable inputs were verified unchanged;
the interruption record preserves its log hash. To validate the interactions
in one exact candidate, 36 stack/frame paths were then copied after all baseline
and prototype hashes matched. Both increments remain uncommitted until the
fresh combined gate passes; no standalone segment-only gate PASS is implied.

The isolated stack/frame prototype passed all 24,999 physical cases (one
pre-existing upstream C8 revocation), 10,256 CPU cases, 339 lifecycle cases,
65,536 independent modular stack checks and all fifteen new intended RTL faults.
The affected eight data and twelve stack/control mutation checks also passed.
The independent 267-file parser audit passed 67 normal and 1,858 event negatives;
the strict disjoint summary passed 1,198,997 cases. Prototype synthesis measured
13,766 mapped / 1,195 sequential cells (+1,142 / +74 from the segment prototype).

An initial audit survived an unobservable level-three branch-target change.
Zero/one-level event paths now reject that concrete fault; the old failed audit
and intermediate assertion-reason mismatch remain recorded. A later orchestration
command used nonexistent `make synth`; that run remains nonzero and a separate
actual `make synth-check` run passed. The source, RTL and expected physical values
were not changed to bypass those failures.

Format 13 has 76 entries/433 words; the registry contains 267 required files and
40 remain absent. The fresh combined `phase7-stack-frame-check` must pass before
milestones 3 and 4 are delivered. Multiplication/division remains isolated.
Complete Phase 7 and independent architectural review remain pending.

## Delivered combined segment and stack/frame increment — 2026-09-09

The fresh `make phase7-stack-frame-check` completed successfully in
`build/phase7-stack-frame-final`, on the exact combined RTL candidate. It closes
user milestones 3 and 4 together; the interrupted segment-only run remains
INTERRUPTED and is not counted as a PASS.

- 1,198,997 disjoint physical cases passed, including 45,000 segment and 24,999
  stack/frame cases. The single C8 omission is the pinned upstream revocation.
- 220 ordinary tests, 80 compiler tests, and 46 benches in both simulators passed.
- All 124 intended RTL mutants were rejected with passing pristine controls.
- Lint, generated consistency, dual smoke, independent parser/comparator audits,
  synthesis and complete inherited regression passed; all 267 inputs were unchanged.
- Yosys: 13,766 mapped / 1,195 sequential cells, +1,321 / +75 from adjustment delivery.
- Microcode format 13: 76 entries, 433 words, nine-bit addresses, seven-bit controls.
- Complete log SHA256: `15d86b17fcedcd5a944b2259cc628413e622f18b2f2c20c9124102d61237dbc5`.
- Verified archive: `.cache/phase7-stack-frame-validation-20260909.zip` (3345 entries).
- Archive SHA256: `e2f8d363305602402c75985505f82afabbd5510f27b76ea19e48e7017c3eff31`.
- Reproducible result: [phase7_stack_frame_validation.json](phase7_stack_frame_validation.json).

267 of 307 required opcode files are implemented; 40 remain pending. The next
work comprises integer multiply/divide, far pointers/control transfers, memory
strings/REP, scalar/string I/O, and the complete phase gate and independent review.
The arithmetic and far prototypes are separate and do not contribute to this
integrated count. The three inherited Phase 6 evidence questions remain open
under D-026; this is executable development validation, not architectural release
approval or complete Phase 7. No historical cycle-accuracy claim is made.

## Integrated far pointer/control candidate — 2026-09-09

After combined milestone 3/4 delivery at a3a03f51e61b010255ba7056aed6ec943aa0d8c7,
37 prototype paths were integrated after checking every source baseline hash.
Two format documents were rebased onto the delivered format-13 documentation
before appending format 14; every executable RTL/compiler/test baseline matched.

The prototype passed 40,000 full physical records without skips/revocations,
6,760 CPU cases, 247 far lifecycle scenarios, twelve new mutants, eight retained
data and twelve stack/control mutants. The older event bench had a stale
expectation that legal memory FF /3 was unsupported; that assertion was replaced
by exact target, link, SP and FLAGS checks. A CALL/RETF pair inside an NMI handler
adds five READY scenarios proving RETF does not release pending NMI. Both
simulators passed all 468 event cases and 46,520 checks, and the 22 retained event
mutants passed. An initial final-count assertion used three added cases instead
of five; the nonzero original run remains preserved. Synthesis passed at
14,069 mapped / 1,195 sequential cells (+303 / +0 from stack/frame).

A clean pinned 275-file corpus and full independent parser/comparator audit
passed, including 67 normal and 1,858 event negatives. The strict prototype
summary is 1,238,997 disjoint identities. It combines earlier validated cohorts
and is not itself a full integrated run. The fresh `make phase7-far-check` remains
pending. Format 14 has 83 entries/492 words; 275 required files are implemented
and 32 remain pending. Integer arithmetic stays isolated with four unresolved
IDIV captures, and complete Phase 7/independent review remain pending.

## Delivered far pointer and control increment — 2026-09-09

The fresh `make phase7-far-check` completed on the exact integrated candidate
in `build/phase7-far-final`. This closes user milestone 6.

- 1,238,997 disjoint physical cases passed, including all 40,000 far transfers.
- 226 ordinary tests, 82 compiler tests and 48 benches in both simulators passed.
- All 136 intended RTL mutants were rejected with passing pristine controls.
- Lint, generated consistency, dual smoke, independent parser/comparator audits,
  synthesis and complete inherited regression passed; all 278 inputs were unchanged.
- Yosys: 14,069 mapped / 1,195 sequential cells, +303 / +0 from frame delivery.
- Microcode format 14: 83 entries, 492 words, nine address and seven control bits.
- Complete log SHA256: `702714fb2aaae226daee1cbe4d5e5d917c0509a1d334e3440a1b08eb6f0615b1`.
- Verified archive: `.cache/phase7-far-validation-20260909.zip` (3337 entries).
- Archive SHA256: `6f880690d2f3eb73792c8ab04139861e715112014503775af29c1b80aff67d4e`.
- Reproducible record: [phase7_far_validation.json](phase7_far_validation.json).

275 of 307 required opcode files are implemented; 32 remain pending. Integer
multiply/divide, memory strings/REP, scalar/string I/O, final independent review
and complete phase validation remain unfinished. Separate arithmetic and string
prototypes do not contribute to this integrated count. The three inherited
Phase 6 evidence questions retain D-026 status. This is executable development
validation, not architectural release approval or a historical timing claim.

## Integrated arithmetic candidate — 2026-09-09

The next candidate adds the ten arithmetic files on the delivered far baseline.
Focused CPU, lifecycle, physical, mutation, adapter and synthesis checks passed.
The strict fresh `make phase7-arithmetic-check` remains required before delivery.
The general negative byte-IDIV disposition (D-036) passes all original records;
no new corpus exclusions, RMSK bits or D-026 exceptions were introduced.
See PHASE7_ARITHMETIC.md and phase7_arithmetic_observations.json.
Memory strings, I/O and independent full-phase review remain pending.

## Delivered integer arithmetic increment - 2026-09-09

The fresh `make phase7-arithmetic-check` completed on the unchanged integrated
candidate in `build/phase7-arithmetic-final-2`. This closes user milestone 5.

- 1,288,997 disjoint physical cases passed, including all 50,000 arithmetic cases.
- 235 ordinary tests, 84 compiler tests and 51 benches in both simulators passed.
- All 153 intended RTL mutants were rejected with passing pristine controls.
- The new frame comparator passed four pristine cases and 24 permitted
  undefined-bit variants and rejected all 176 frame/address mutations.
- Lint, generated consistency, smoke, independent parser/comparator audits,
  synthesis and inherited regression passed; all 295 executable inputs matched.
- Yosys: 16,484 mapped / 1,395 sequential cells, +2,415 / +200 from far delivery.
- Microcode format 15: 87 entries, 521 words, ten address and seven control bits.
- Complete log SHA256: `504680150547d1c0cb1df34ec08135fb6c51f0c4c54538e425494e9177dca7c2`.
- Verified archive: `.cache/phase7-arithmetic-validation-20260909.zip` (3685 entries).
- Archive SHA256: `d040be66522b920ac0452bc27c58535a0fb4305c597cc271b7d209d8a2c487f8`.
- Reproduction and exact inputs: [phase7_arithmetic_validation.json](phase7_arithmetic_validation.json).

The ten admitted files are 69, 6B and F6/F7 groups /4, /5, /6 and /7. D-036
resolves the four prior byte-IDIV execution failures with a general finite
arithmetic condition. Every original F6.7 record passed; no original record,
expected value or revocation was changed. The 16,777,216-pair exhaustive research
was a separate mathematical experiment, not an exhaustive RTL simulation.

285 of 307 required opcode files are implemented in this delivery; 22 remain.
Memory strings/REP, scalar/string I/O, their final integration and independent
review remain unfinished. The separate full candidate's partial physical run
does not establish a complete phase pass. The original D-026 evidence questions
remain open, and no Phase 8 or historical cycle-accuracy claim is made.

## Preserved remaining candidates - 2026-09-09

The current pending inventory and completed local verification are recorded in
[PHASE7_REMAINING_WORK.md](PHASE7_REMAINING_WORK.md). This supersedes historical
"unimplemented" labels for isolated candidates; only milestones 1-6 are delivered.
The complete phase and focused independent review remain incomplete.
