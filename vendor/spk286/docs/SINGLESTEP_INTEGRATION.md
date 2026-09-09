# SingleStep 80286 Integration

## Purpose

SPK286 uses the external [SingleStepTests/80286](https://github.com/SingleStepTests/80286)
real-mode corpus as hardware-derived architectural evidence for the already
implemented word MOV families (`B8` through `BF`, `89` and `8B`). The corpus
is not part of the SPK286 repository and is never copied into Git history.

The Phase 2.5 runner performs this flow:

```text
MOO test -> normalized state -> RTL initialization -> one target retirement
         -> resulting state -> masked register/RAM comparison
```

## Upstream provenance

- Repository: `https://github.com/SingleStepTests/80286`
- Tested commit: `37c73caf53dcd22d3dd369ff09305d13d117a4fe`
- Published version: `1.1.0`
- Hardware source described upstream: Harris `N80C286-12` real-mode captures
- License: MIT, as declared by the upstream repository
- Acquisition: shallow, blob-filtered sparse checkout through
  `tools/fetch_singlestep.py`

The checkout includes only the upstream README/license, metadata, revocation
list, parser reference, `B8.MOO.gz` through `BF.MOO.gz`, `89.MOO.gz` and
`8B.MOO.gz`. It lives under
`.cache/singlestep-80286/`, which is ignored by Git. A local checkout can be
selected with `SPK286_SINGLESTEP_ROOT` or `--repo`.

## MOO handling

`tools/singlestep.py` reads the MOO 1.1 chunk format directly, including gzip
compression. It follows the upstream `tools/moo2json.py` layout:

- `MOO ` header: version, test count, and CPU identifier;
- `TEST` records with `NAME`, `BYTS`, `INIT`, `FINA`, `CYCL`, `HASH`, and
  optional `EXCP` chunks;
- sparse `REGS`, `RAM `, and `QUEU` state chunks;
- 286 cycle records with the upstream 15-byte packed layout.

Cycle data is parsed and retained for diagnostics, but it is not currently
used as an acceptance criterion. Register masks and the upstream
`revocation_list.txt` are applied before a case reaches the RTL simulator.
Revoked cases are excluded from the valid set and reported separately.

Admission validates the MOO format version/CPU, header count, singleton chunks,
and unique case indexes/hashes. The execution runner accepts only the supported
unprefixed MOV-plus-HALT stream: four bytes for B8..BF, or three to five bytes
for 89/8B according to ModR/M displacement length. Unsupported state,
nonempty queues, unrepresentable initial FLAGS, and disagreement between declared
instruction bytes and initial RAM are errors. B8..BF admission remains strict:
prefixes and exception metadata are errors. For 89/8B only, the runner explicitly
excludes known 286 prefix streams (segment overrides, LOCK and REP combinations)
and exception outcomes before preparation. Neither exclusion is a passing case.
Unknown encodings, malformed supported forms and arbitrary preparation/execution
errors cannot become exclusions. Explicitly selecting an excluded index/hash
fails with its reason.

## State and HALT/IP convention

The current supported corpus cases provide a complete initial 16-bit register
state, sparse RAM, and an empty prefetch queue. The runner loads:

- all eight general-purpose registers;
- `CS`, `SS`, `DS`, and `ES` selectors, using real-mode selector times 16
  hidden bases;
- `IP` and `FLAGS`, with the CS reload and fetch redirect committed together;
- every byte in the initial sparse RAM map.

Each upstream test contains the target instruction followed by `F4` (`HLT`).
The published final `IP` includes that one-byte terminator. SPK286 stops at the
target instruction's retirement boundary, so the runner compares
`published_final_ip - 1` against the target end address and does not execute
the terminator. Upstream obtains state using NMI after HALT and reconstructs
FLAGS/CS/IP from the interrupt frame; SPK286 does not emulate that capture
procedure. This terminator adaptation is independent of the destination opcode;
its current sequential-IP check must be extended explicitly for control flow.
Undefined final register bits are compared through the MOO
register masks. Sparse final RAM entries are merged over the initial map.

For CODE prefetch only, the Verilator adapter returns zero from absent sparse
RAM locations because prefetch may run beyond the declared stream. For MEMR,
every active byte lane must already exist in RAM or the case fails as an
unspecified data read. MEMW commits active lanes only on READY and may create
new locations. The entire resulting sparse map is compared against initial RAM
merged with sparse final RAM; unexpected final bytes or values fail, including
neighboring bytes. This state comparison alone cannot detect repeated or extra
writes that leave existing bytes unchanged, or writes undone before retirement.
Directed RTL monitors separately check accepted transaction counts, addresses
and lanes. Full captured bus-event comparison remains deferred.
No operand value is synthesized from an expected result.

## Commands

Acquire or refresh the pinned external working set:

```text
make singlestep-fetch
```

Run the deterministic smoke set, ten valid cases per opcode:

```text
make singlestep-smoke
```

Run every non-revoked case for `B8` through `BF`:

```text
make singlestep-mov
```

Run every supported unprefixed normal case for both ModR/M directions:

```text
make singlestep-operands
```

Independently compare all decoded cases and cycle records against the pinned
upstream parser, then prove the real simulator rejects deliberate faults:

```text
make singlestep-audit
```

This check requires the external `tools/moo2json.py`. It writes separate
ignored batches/logs and a pristine waveform under `build/singlestep-audit/`
(or `SPK286_BUILD_DIR`). It changes each of the 14 compared registers, a memory
expectation, an actual immediate byte, and an actual opcode: all 17 probes must
fail for the specified reason. Two pristine executions must pass. It never
edits the corpus, production RTL, or ordinary expected-state preparation.
Phase 3 extends the parser comparison to all 50,000 discovered cases and adds
three operand probes: missing read byte, changed actual read byte, and changed
expected written byte. The read/write addresses come from captured bus records.
The complete audit requires 20 rejected faults and four pristine passes.
Two of those pristine runs execute real memory MOV and save traces.
Upstream cycle-parser agreement is not RTL timing validation.

The Python interface also supports one opcode, one index or hash, and a fixed
sample size:

```text
python3 -m tools.run_singlestep --opcode B8 --index 0
python3 -m tools.run_singlestep --opcode B8 --hash <40-hex-test-hash>
python3 -m tools.run_singlestep --opcode B8 --sample 10
```

Failure diagnostics identify the opcode, test index, upstream hash, mnemonic,
initial state, expected state, actual state, and masked differences. To create
a waveform for one reproducible case:

```text
python3 -m tools.run_singlestep --opcode B8 --index 0 \
    --trace build/traces/singlestep-B8-0.vcd
```

The simulator is compiled once and consumes a binary batch per opcode. This
keeps the smoke path suitable for normal regression while allowing the full
corpus to run without launching Verilator once per vector.

The runner requires exactly one result summary, `selected = executed = passed +
failed`, and agreement between failure count and process exit status. Duplicate
opcode selections are rejected. Reported discovery totals obey `discovered =
revoked + prefix_skipped + exception_skipped + selection_skipped + executed`.
Categories are disjoint: revocation takes priority, then prefix, then exception,
then sample selection. Revoked/excluded/unselected cases are not passes.
The pinned full B8..BF set contains 40,000 distinct hashes, no revoked cases,
no prefixes, no exceptions, and no comparison masks. The normal regression runs
80 of these cases only when the external working set is present; otherwise it
prints an explicit skip. It also runs ten supported cases each for 89/8B when
those files are available. Full coverage and audit remain separate commands,
required by `make phase3-check` and CI. The release gate requires all ten files
in the clean pinned corpus; an optional daily-regression skip cannot satisfy it.

| Full family | Discovered | Revoked | Prefix excluded | Exception excluded | Selected / executed / passed | Failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B8..BF | 40,000 | 0 | 0 | 0 | 40,000 | 0 |
| 89 | 5,000 | 0 | 1,016 | 29 | 3,955 | 0 |
| 8B | 5,000 | 0 | 1,031 | 29 | 3,940 | 0 |

Full runs have zero `selection_skipped`. Each run writes per-opcode JSON under
`build/singlestep/reports/`, including index/hash/reason for every scope exclusion.
`phase3-check` copies full reports to `singlestep/full-reports/` before subsequent
smoke or replay commands replace current reports. The 58 unprefixed exception
cases require exception delivery, which Phase 3 does not implement. Directed
tests separately enforce whole-word limit blocking before memory side effects.
The parser audit reports 68 raw exception records: ten also have prefixes and
are already counted in the prefix category. Thus the disjoint exception count
is 58, not 68; total scope exclusions are 2,105.

Phase 2.75 failures also print the actual micro-PC, entry, decoded control word,
active/fault state and queue count. Map a reported numeric PC back to the source:

```text
python3 -m tools.microcode.compile_microcode --pc 0x1
```

The committed JSON source map/listing permits the same lookup without parsing
source inside synthesized hardware. The runner's architectural expected-value,
HALT/IP and memory comparison rules are unchanged by the microcode migration.

## Comparison scope

The current acceptance comparison covers all 14 exposed architectural values:
`AX`, `BX`, `CX`, `DX`, `CS`, `SS`, `DS`, `ES`, `SP`, `BP`, `SI`, `DI`, `IP`,
and `FLAGS`, plus the sparse RAM map. Exact cycle traces, wait-state timing,
prefetch overlap, queue contents, and HALT bus signaling are deliberately not
acceptance criteria yet. The upstream README notes that these captures do not
exercise wait states and do not expose enough queue status to make exact 286
prefetch comparison a Phase 2.5 requirement.

## Maintenance rules

- Keep the upstream corpus in `.cache/`; never commit MOO, generated JSON, or
  generated runner batches.
- Refresh the commit and reported results together when changing provenance.
- Do not alter expected hardware-vector values to make a failing RTL case pass.
- Add a focused parser or state-preparation test before changing the MOO
  interpretation.

## Phase 4 admitted word ALU forms

The exact 40 forms are listed in PHASE4_SCOPE.md. Run all with
`python3 -m tools.run_singlestep --alu --full`, or use `--alu --smoke`.
Individual grouped files are selected as `--opcode 81.0` or `--opcode 83.7`.
The adapter validates both the opcode byte and ModR/M extension, exact
little-endian immediate/displacement length and the unchanged trailing-HLT IP
boundary. Unknown width/form encodings are errors, not exclusions. Revocations,
prefixes, exceptions and sampling retain disjoint accounting.

The 200,000 newly discovered records admit 166,085 executions, with 32,904
prefix and 1,011 exception exclusions, no revocations. All admitted cases pass
in the development full run; final release evidence belongs in PHASE4_HANDOFF.
Full inherited 47,895-case execution remains mandatory. No expected register,
FLAGS or RAM value is rewritten. Arithmetic comparisons have full masks;
logical records supply F7EE for FLAGS, which is passed through unchanged.
The independent directed tests verify defined logical CF/OF that this mask
omits. The implementation preserves stored AF as its undefined policy.

The parser audit independently compares all 50 files (250,000 discovered
records) with upstream. `make phase4-check` requires every file and saves full
new-family reports in singlestep/phase4-full-reports, with inherited full results
retained separately in singlestep/full-reports. Exclusions never count as passes.

The pinned upstream moo2json converter does not emit RMSK. The audit compares
its complete represented state and cycles, then independently decodes each
binary RMSK using the MOO 1.1 field layout and verifies every production mask.
A missing/changed/extra mask or other state field fails; no mask or expected
architectural value is weakened. This also covers all excluded records.

## Phase 5 stack/control adapter

`--stack-control` selects the exact 47 unprefixed word/near forms in
`PHASE5_OPCODES`. The acquisition helper retains the same pinned repository
revision and adds those files to the sparse working set. Admission excludes
only separately counted revocations, recognized prefixes and explicit
exception vectors. Length, file opcode/group, initial RAM bytes, FLAGS storage,
sparse state expansion and all architectural comparisons remain strict.

The upstream physical harness injects a HLT on the first fetch at a transfer
destination. Published final IP includes that HLT, so the unchanged retirement
conversion remains `(published_ip - 1) & 0xffff`. Control forms do not impose
the sequential-IP assertion used for MOV/ALU/stack-only instructions. No target
is recomputed from RTL, patched into expected state, or replaced with a test
address. All published memory and register outcomes retain their masks.

The parser audit covers every new discovered record against upstream, and
adds a pristine execution plus deliberately corrupted expected IP for each of
the 47 new forms. Mutations operate on copied batches. Full release reports
for all inherited and new families are preserved in
`singlestep/phase5-full-reports`, with a strict `phase5-summary.json` aggregate.
The release target refuses absent families and any full-run selection skip.
Primary convention source: the pinned
[SingleStepTests/80286 README](https://github.com/SingleStepTests/80286/blob/37c73caf53dcd22d3dd369ff09305d13d117a4fe/README.md).

## Phase 6 exception-aware adapter

`--events` selects 9C/9D/CC/CD/CE/CF/F4/FA/FB. `--phase6` selects all 106 families
and admits supported old exceptions; `--include-exceptions` allows focused old
family fault runs. The legacy cohorts remain separately measurable. Batch format
2 carries expected completion identity and retirement independently of initial
RAM/register data. EXCP never drives the DUT fault request.

The adapter observes actual `event_completed` or instruction retirement and
compares event identity, retirement, final context and cumulative final RAM.
Faults do not wait for false retirement; handler instructions are not executed.
CF and HLT-under-test use their own capture normalization; ordinary sentinels
retain the pinned capture convention. Sparse reads must exist in input MEMR;
expected final RAM cannot supply read data. Only justified upstream undefined
FLAGS masks apply at the exact recorded frame address.

Invalid 8F group captures can contain arbitrary initialized trailing bytes after
ModR/M. Decode rejects that invalid form immediately; the adapter validates the
whole supplied input image without interpreting those tails as required operands.
The 33 valid 8F destination-limit faults retain POP's SP+2 before #GP entry.

The upstream converter cross-check covers every discovered record, including
prefix exclusions. Independent wire decoders verify RMSK and five-byte EXCP
payloads, identities and bounds. Additional copied-batch probes corrupt event,
retirement, context and each frame byte while retaining the original 67 probes.
See [handoff](PHASE6_HANDOFF.md) for actual counts and timing limitations.
