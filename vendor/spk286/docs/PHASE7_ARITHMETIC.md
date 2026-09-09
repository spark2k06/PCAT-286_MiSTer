# Integer arithmetic development increment

Status: delivered executable development increment; the fresh integrated
gate passed. Complete Phase 7 and independent architectural review are pending.


MUL/IMUL/DIV/IDIV support byte and word operands through the existing register,
ModR/M and memory machinery. Immediate 286 IMUL supports sign-extended byte
and word immediates with the decoded register destination. A captured iterative
service performs arithmetic; the common microexecutor owns results and FLAGS,
the BIU owns operand bus accesses, and the event owner publishes #DE.

Acquisition precedes calculation. Immediate bytes precede the memory operand,
so instruction-length faults cannot leak an operand access. Implicit results
are disposed to AX and DX as required, followed by FLAGS and the arithmetic
fault check. A fault suppresses both destination writes. Asynchronous events
observe the completed instruction; cancellation preserves effects already
committed and prevents late responses. Pausing freezes owned state and consumes
neither operands nor responses twice. No historical cycle count is inferred.

Legal integer division uses truncation toward zero and the dividend's sign for
the remainder. Word and unsigned quotient limits retain the documented #DE
contract. A physically evidenced negative-byte-overflow rule is described in
PHASE7_IDIV_COMPATIBILITY.md. Its finite candidate is computed during the first
eight steps of the real quotient calculation using otherwise idle product
storage. It introduces no timing-only instruction states. The unchanged full
5000-record F6.7 file, not just the four former discrepancies, passed on the
combined candidate. Fresh execution on this delivery candidate also passed all 5000 F6.7 records.

Multiplication sets CF/OF by signed/unsigned range and uses captured upper-product
SZP behavior. AF remains unchanged. Division preserves the six architecturally
undefined arithmetic flags. The adapter applies only original corpus RMSK bits
to the original EXCP FLAGS stack word on divide error, checking SS:SP and all
original bytes. Defined FLAGS, CS/IP, other RAM bytes and address sets remain
strict. Binary version 3 carries these optional masks; unmasked batches keep
version 2. Four pristine cases, 24 declared undefined-bit variants and 176
rejected frame/address mutants verify the comparison boundary.

Format 15 adds controls 116..120 and four complete microcode protocols: 87
entries / 521 words / ten address bits / seven control bits. All 492 delivered
far-image words, entry addresses and branch destinations are unchanged. Frozen
format-14 sources and an independent literal format-15 contract are required.
The active registry has 285 of 307 required files; the 22 memory-string and I/O
files remain outside this increment. Separate combined prototypes do not
substitute for this candidate's integrated validation.

Focused evidence on this candidate currently includes 284500 service vectors,
19556 CPU scenarios, 780 arithmetic lifecycle cases, 6760 retained far-transfer
cases and 247 retained far lifecycle scenarios, all in both simulators.
The complete `make phase7-arithmetic-check` must additionally repeat all inherited
checks on one unchanged input set and require 1,288,997 disjoint physical cases,
all 153 RTL mutation probes (136 inherited plus 17 arithmetic), parser/comparator
audits and synthesis. It remains fail-closed. Complete Phase 7, independent
architectural review and the three original D-026 evidence questions stay pending.

PHASE7_INTEGER_ARITHMETIC.md and phase7_muldiv_observations.json preserve the old
frame-based prototype and its four historical failures. They do not describe
the corrected delivery candidate. New execution records will be linked here
only after the corresponding commands actually complete.

The candidate's fresh physical run passed all 90000 arithmetic and retained
far-control records without skips or new revocations. This includes every
F6.7 record. The new arithmetic comparison audit also passed: four pristine
cases, 24 permitted undefined-bit differences, 176 rejected frame/address
mutants. See phase7_arithmetic_observations.json for exact logs and exits.

Focused mutation audits passed all 17 new arithmetic and 12 retained far probes
with their unchanged control benches. The independent parser/comparator audit
passed on all 285 admitted files, preserving 67 ordinary and 1858 event negatives.
Synthesis passed at 16484 mapped / 1395 sequential cells (+2415 /
+200 from delivered far control). These checks permit integration for the
fresh full gate; they are not that gate or independent architectural approval.

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
