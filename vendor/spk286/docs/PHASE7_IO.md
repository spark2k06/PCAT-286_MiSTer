# Phase 7 scalar and string I/O candidate

Current functional delivery (2026-09-09, D-037): **Phase 7 milestones 1–9
are integrated, executable-validated and independently approved for functional
development.** All 307 required files are covered: 1,386,996 evaluable records
passed, exactly one E7 capture is NOT EVALUABLE, and there are no unexpected
omissions or executable failures. The three inherited Phase 6 notes and the two
named Phase 7 notes remain open and nonblocking; historical timing is not
certified. Phase 8 may start from this accepted functional baseline; no Phase 8
implementation is included. E7 issue publication remains pending by user request.
See the [functional closure record](PHASE7_FUNCTIONAL_CLOSURE_20260909.md),
[new independent approval](PHASE7_FUNCTIONAL_REVIEW_20260909.md) and
[functional recovery guide](PHASE7_FUNCTIONAL_RECOVERY.md).

## Preserved historical record — superseded for current status

The text below retains its original dates, counts and conclusions. Its earlier
REP/E7 blocking criteria are superseded by D-037 and the functional delivery
above; historical validation and withheld-approval decisions are not rewritten.

Status: isolated implementation with focused executable checks passed; full
required physical validation FAILED. This is not a delivered increment or an
architectural approval. The incomplete E7 capture and the inherited string
REP event evidence requirements remain open. No new D-026 waiver is claimed.

## Functional ownership

Eight project-owned programs add IN/OUT (AL/AX, immediate port or DX) and
INS/OUTS (byte/word, REP/REPNZ). The port is captured once before iteration.
The existing BIU performs all external transactions, including READY waits,
HOLD/HLDA arbitration, LOCK serialization and odd-word lane sequencing. An
odd word at port FFFF carries its second physical address to 010000. No
instruction-level historical timing claim follows from these programs.

INS decrements a repeated count, consumes the port input, advances DI, then
writes ES memory. A destination range fault preserves the already consumed
input and the physically observed extra CX decrement. OUTS advances SI and
CX before reading source memory, then writes the port only after that read
succeeds. Source overrides apply to OUTS; INS always uses ES. All partial
fault results are compared against unchanged physical records. Zero-count
REP causes no port or memory effects. Scalar input preserves AH for AL;
output and string I/O preserve AX and FLAGS.

Accepted transfers survive cancellation until the BIU drains their physical
bus effects; canceled operations cannot commit later architectural results.
Explicit tests cancel after a port cycle is visible and READY-stalled, also
checking odd words, HOLD after acceptance, and LOCK over a repeated sequence.
The same restart boundaries and unresolved TF/zero-count evidence limits as
PHASE7_MEMORY_STRINGS.md apply. An IRET restart test proves the implemented
policy; it is not a new physical capture or hardware adjudication.

## Focused evidence on 2026-09-09

- 237 ordinary Python tests and 86 compiler tests passed.
- Scalar I/O: 452 cases / 24,628 checks in each simulator.
- String I/O: 11,520 cases / 1,494,767 checks / 57,799 READY stalls in each
  simulator, covering directions, segment overrides, repeat forms, counts,
  boundary offsets and even/odd ports including FFFF.
- Lifecycle: 376 cases / 33,622 checks in each simulator, including 24 new
  accepted-transfer cancellation, HOLD and LOCK scenarios.
- Eighteen deliberately broken RTL variants were rejected; three unchanged
  benches passed. The first audit exposed a real accepted-port cancellation
  coverage gap. The stronger test now detects that defect. Failed first-run
  logs are preserved; they are not classified as passing mutation evidence.
- Dual-simulator smoke passed. Synthesis passed: 14,966 mapped cells and
  1,200 sequential cells (+274 / +0 relative to the isolated string image).
- All 8,000 INS/OUTS records, 35,000 records from seven scalar I/O files and
  50,000 memory-string records passed together on this CPU: 93,000 total,
  with no new exclusions or revocations. Six port-comparator negative cases
  and the unchanged comparator passed.

The full E7 file is required. Record 1100, hash
c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e, contains an uncompleted captured
output cycle. Both execution preparation and the later independent parser
comparison stop with `incomplete captured I/O cycle`. Neither full command
passed. No expected port value is fabricated from AX, and no case is skipped.
The raw-byte parser comparison is therefore incomplete for the 297-file set;
it is not a 297-file PASS. Version 4 stores captured port comparisons only;
version 3 remains reserved for the separate arithmetic RAM-mask extension.
A combined adapter must explicitly represent both without reinterpreting an
existing binary version.

`make phase7-io-check` requires every I/O family and all nested prior checks.
Its 1,336,997-case target is a required total, not an achieved result. Full
Phase 7 still needs multiplication/division integration, the outstanding
capture/evidence dispositions, combined regression, independent review and
verified delivery.

See phase7_io_observations.json for exact logs, timestamps and fingerprints.

## Current ordered integration candidate - 2026-09-09

This isolated candidate contains all 307 required opcode files but has not been
validated as a complete Phase 7 delivery. It preserves the arithmetic format-15
source and independent literal, followed by the string format-16 source and
literal. I/O is appended in format 17: 100 entries, 612 words, ten address and
eight control bits. Arithmetic controls remain 116..120, strings 121..130 and
I/O occupies 131..135. All generated artifacts come from human-readable source.

The functional RTL matches the separately tested complete candidate, whose
full regression passed and whose strict physical run failed preparation of E7.
Those older results do not establish this newly ordered image's execution.
The new image passed 254 ordinary tests, 88 compiler tests, independent active
and frozen literal/round-trip audits, lint and both-simulator decoder checks.
Fresh affected instruction tests, physical coverage, mutation audits and complete
regression are recorded separately as they actually finish.

The required E7 record c56d37647cc2dbcce82ca640fdd25ddea1f3ee5e is still not revoked
upstream. Its missing captured write strobe/data are not reconstructed from AX.
No original expected values, captures or revocation policy have been changed.
The original Phase 6 D-026 evidence questions remain open. New REP event evidence
and independent review remain pending; no new waiver or Phase 8 work is claimed.

See PHASE7_REP_EVENT_EVIDENCE.md and PHASE7_IO_CAPTURE_REVIEW.md for evidence
limitations. Complete Phase 7 remains incomplete; this directory is not a
verified Git delivery.
