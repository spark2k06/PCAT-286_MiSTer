# Phase 6: real-mode interrupts and exceptions

Status: implemented candidate; architectural release blocked by the evidence
questions in [PHASE6_ARCHITECTURAL_REVIEW.md](PHASE6_ARCHITECTURAL_REVIEW.md).
Base: `03c32df5c2d5edcb4606564d1dba215d26640116`, following the reviewed
Phase 3/4 ancestry. The inherited Phase 5 gate is run in the fresh, ignored
`build/phase6-baseline` directory before functional edits.

## Admitted instruction forms

Unprefixed, 16-bit real address mode only:

| Bytes | Form | Completion |
|---|---|---|
| CD ib | INT imm8, all 256 vectors | Software event entry, saved next IP |
| CC | INT3 | Software vector 3, saved next IP |
| CE | INTO | OF=0 ordinary retirement; OF=1 software vector 4 |
| CF | IRET | Three stack words, ordinary real CS cache, IP and FLAGS restore |
| FA / FB | CLI / STI | IF clear / set; STI inhibits INTR through the following instruction |
| 9C / 9D | PUSHF / POPF | Word stack service; real-mode FLAGS policy |
| F4 | HLT | One retirement, halt until an eligible event or reset |

Existing Phase 3–5 successful forms remain admitted. Their architectural fault
paths now belong to this phase: word operands at offset FFFF, exhausted demanded
instruction bytes, invalid encodings of decoded 8F/FF groups, and failures of
stack transfers. Legal unimplemented instructions remain explicit unsupported
forms. This phase does not turn all unsupported opcodes into #UD.

NMI, INTR and HOLD are normalized synchronous CPU input pins. NMI uses sampled
rising edges and one pending latch; INTR is a level. A board must synchronize
asynchronous pins. INTR obtains its vector only from the low data lane of the
second physical INTA transaction. No adapter vector sideband is permitted.

The reset real-mode IVT is based at physical zero, with all 256 four-byte entries
addressable. IDTR loading, protected-mode gates, privilege transitions, error
codes, task switches, NPX, REP/string restart, general prefixes, additional
arithmetic families and far CALL/JMP/RET are deferred. No phase-local fake fault
instruction or programmable segment-limit test port is added. Existing reset
special CS base FF0000 and ordinary reload selector*16 behavior are retained.
Variable IDTR is not exposed: the conflicting documented reset limits 03FF/FFFF
cannot affect any admitted vector, whose last byte is 03FF.

## Evidence and limits

The controlling semantic contract and commit matrix are in
[INTERRUPTS_EXCEPTIONS.md](INTERRUPTS_EXCEPTIONS.md). Intel manuals are primary;
the pinned Harris 80286 corpus is physical evidence. MCL86 is a non-controlling
reference. Historical instruction timing and native Ts/Tc/Ti padding remain
separate from functional sequencing, as required by `SPK286_TIMING_MODEL.md`.
READY, owned cycles, word halves, INTA locking and redirect cancellation are
real dependencies and are mandatory in every timing profile.

The physical corpus excludes TF/IF delivery scenarios and boundary SP values;
directed streams must cover those separately. No hardware coverage is claimed
for a scenario absent from the capture set. Unresolved evidence questions must
remain visible in the handoff and cannot be covered by changing golden data.

## Validation and delivery contract

* Preserve and report the inherited 440574 successful cases separately.
* Reassess all 1423 previously excluded non-prefixed exceptions, including the
  354 Phase 5 cases. Physical captures show 1234 #GP and 189 #UD cases.
* Run all admitted cases from 9C, 9D, CC, CD, CE, CF, F4, FA and FB. The pinned
  inventory contains all nine files: 33000 discovered, 948 prefix exclusions,
  32052 admitted before any revocations. Report actual executed counts.
* Pin corpus `37c73caf53dcd22d3dd369ff09305d13d117a4fe`; retain strict sparse
  initial RAM checks, cumulative final RAM comparison, RMSK and EXCP auditing.
  EXCP metadata is an oracle annotation, never a DUT input or an execution recipe.
* Finish compiler checks (frozen formats 1–4 and active format), deterministic
  generation twice, lint, affected dual-simulator benches/smoke, complete corpus,
  independent parser/model audits, inherited and event mutation probes, negative
  gate tests, trace inspection, MCL86 comparison, synthesis sanity and regression.
* `make phase6-check` must fail closed and emit `PHASE6_VALIDATION_PASS` only
  after every mandatory component succeeds. Fresh final output is required.
* Architectural approval remains withheld. D-026 permits incremental Phase 7
  development after fresh `phase6-exec-check` validation while the three named
  evidence questions remain open. Commit only verified development states and
  keep release approval, executable validation and Git delivery distinct.
