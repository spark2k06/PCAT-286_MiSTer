# Phase 7 ordered integration

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
