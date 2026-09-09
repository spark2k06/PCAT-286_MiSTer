# Phase 7 data-transfer increment

This increment adds the sixteen required files 86/87, 90–97, 8D, D7 and A0–A3:
XCHG (including NOP), LEA, XLAT and accumulator MOV with a direct offset.
The isolated full physical run passed 48,000 records with zero revocations,
skips or failures. Integration, regression and exact delivery identity are
recorded separately in PHASE7_HANDOFF.md; this is not complete Phase 7 approval.

## Architectural evidence

Intel 210498-005 Appendix B B-63 specifies that LEA returns the effective offset
without reading data memory and raises #UD for a register source. B-114 specifies
XCHG's exchange and unchanged FLAGS; B-115 specifies unsigned AL indexing for
XLAT. Intel 210760-002 table 3-3 identifies XCHG with memory as an implicit
LOCK owner. The MOV entries specify the A0–A3 accumulator/direct-offset forms.

The sixteen pinned physical files contain 1,280 LEA register-source #UD cases
and 34 XCHG word-limit #GP cases. All were included in execution. No expectation,
mask, byte sequence or source record was changed. Directed cases additionally
cover direct word access at FFFF, byte access at FFFF, XLAT offset wrap, byte
aliases, repeated/segment prefixes, immediate starvation and READY/HOLD.

## Ownership and commit order

The architectural register file and FLAGS owner are unchanged. The executor
gains typed temporary transfers, effective-offset acquisition and a transient
address override. Direct MOV acquires its full offset before a memory operation.
XLAT adds the existing BX base to a zero-extended AL temporary, wrapping the
effective offset at sixteen bits. Normal segment-override selection still applies.
The address override clears at instruction start, cancellation and reset.

LEA obtains the operand decoder's computed offset without requesting the operand
service, so a valid offset FFFF does not become a fabricated word read fault.
Register-source LEA faults as soon as its ModR/M identifies the invalid form.

XCHG obtains both old operands before writing either destination. An RM exchange
finishes the memory/register RM write before committing the old RM value to the
reg field. Memory exchanges request implicit LOCK through the existing BIU;
the CPU never grants HOLD between their read and write. Exact historical LOCK
pin timing is outside this functional increment's claim.

Register-encoded 90–97 use separately decoded source (AX) and target indexes.
The generic executor reads both and writes their captured values through the
single owner, including the AX/AX case. It does not decode x86 opcodes.

Cancellation preserves earlier architectural writes and drains only physical
writes already accepted by the BIU. The dedicated lifecycle bench checks XCHG
before memory write, at both odd-word halves, at the write response, before the
register commit and after that commit but before retirement. It also checks
direct MOV at six byte/data boundaries and a dependent mixed instruction stream.

## Microcode and validation

Format 9 uses seven-bit controls and nine-bit addresses, with 57 entries and
282 words. Seven typed controls extend the existing 235-word image; all earlier
words and entry addresses are preserved. The frozen format-8 source fixture and
independent literal format-9 appendix check historical and current encodings.
Source maps remain available. No idle operation was added for historical timing.

The compiler requires complete address/exchange protocols. A negative test
initially exposed an incomplete exchange that fell through to the older byte
validator after its final TMP1 write was removed. The validator now recognizes
that functional read-secondary/write-RM shape and rejects the missing disposition.
The original failed compiler attempt remains recorded as failed; its expectations
were not weakened. A stale unsupported-version test was advanced from 9 to 10
because format 9 is now implemented.

Older directed tests and the comparator's unsupported-opcode injection used 90
as a synthetic stopping byte. They now use the still-unsupported system escape
0F while keeping the same non-retirement and state-preservation assertions.
Physical source bytes and frozen expected images are unaffected. The seven
affected legacy benches are rerun in both simulators.

The new directed CPU bench passes 5,690 cases with 484,492 checks and 1,932
immediate stalls in each simulator. The lifecycle bench passes 55 cases with
2,953 checks, including partial exchange commits. Eight isolated-copy RTL
mutations cover exchanged values, LEA's source/#UD, AX selection, unsigned XLAT,
the high offset byte, implicit LOCK and address lifetime, with pristine controls.
Strict accounting requires 1,010,998 prior identities plus 48,000 new identities
for 1,058,998 distinct records. Those combined prototype reports do not replace
the fresh integrated gate, synthesis or complete regression.

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
