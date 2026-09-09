# Phase 7 far pointer and control transfers

Status: isolated implementation; the integrated executable gate and delivery
remain pending. This is not complete Phase 7 or independent review approval.

## Functional contract

C4/C5 LDS/LES acquire a complete memory pointer before writing the selected
ES/DS cache and destination GPR. The shared segment owner installs the Real
Mode base (selector shifted left four), limit FFFF and access 93. Register
forms are #UD. A pointer starting at FFFE wraps its second word to offset zero;
an odd out-of-range word faults before pointer acquisition or destination writes.

9A/EA and FF /3,/5 use the existing CS:IP context commit and prefetch redirect.
Memory CALL acquires both pointer words before checking or writing the return
frame. CALL checks the entire four-byte stack interval, pushes old CS then the
next IP, and commits the destination. RETF first checks and acquires its complete
four-byte frame. CA then adds the unsigned immediate allocation to SP. These
operations preserve FLAGS and do not release NMI inhibition; IRET owns that
release. Register FF /3,/5 remain #UD. No 386 behavior or machine glue is added.

The executor reuses pointer, auxiliary and allocation temporaries, existing
stack/operand services and the single architectural register/segment owners.
BIU completion, instruction-byte availability and redirects remain real
functional dependencies. Every pause/cancel/reset boundary is exercised.
No microinstruction count is claimed as historical timing.

## Source evidence and physical scope

The Intel 80286 and 80287 Programmer's Reference Manual, order 210498-005
(1987), sections 3.6 and 3.8 and instruction entries CALL/JMP/RET/LDS/LES,
defines the two-word pointers, return frame and register/memory restrictions.
Primary source: https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf

All eight pinned SingleStepTests/80286 files were executed in full at revision
37c73caf53dcd22d3dd369ff09305d13d117a4fe: 40,000 selected and passed, zero
failures, local skips or revocations. The independent parser audit checked all
275 active files and retained 67 normal plus 1,858 event negative comparisons.
All physical expected register, memory and frame values remain unchanged.

The pointer families each contain 33 offset-FFFF #GP cases. Valid FFFE wrap
appears four times in C4, three in C5, and four each in FF /3 and /5. The 26
#GP cases in each CA/CB file start with SP=FFFF. Direct 9A/EA each have eleven
instruction-length #GP captures. Register-invalid examples retain producer
identity and first-prefix frame addresses. The preserved raw observations and
actual run hashes are recorded in phase7_far_observations.json and the evidence
archive produced only after a completed integrated gate.

## Verification

An independent transaction oracle supplies 6,760 CPU cases covering all pointer
ModR/M forms, register aliases, selector changes, stack/address boundaries,
source/stack overlap, READY lanes and exact ordered memory writes. Both
simulators passed 639,234 checks and 1,296 deliberately stalled accesses.
A separate lifecycle bench passed 247 cases and 15,629 checks in each simulator,
including each microcode boundary, cancellation, reset, prefix faults and full
unmasked NMI/INTR/TF frames. Twelve injected RTL defects were rejected; both
pristine far benches passed. Eight retained data and twelve stack/control
mutants also passed. The retained event audit rejected all 22 intended defects. The expanded event
lifecycle passed 468 scenarios / 46,520 checks in both simulators, and Yosys
synthesis passed with 14,069 mapped / 1,195 sequential cells.

The older event lifecycle bench expected legal memory FF /3 to remain
unsupported. Its original failure is preserved. The current test instead checks
the exact target, link, SP and unchanged FLAGS, and adds a CALL/RETF round trip
inside an NMI handler. This updates an obsolete admission contract; it does not
alter physical captures or hide a failing implemented instruction.

The strict disjoint prototype summary contains 1,238,997 identities. That
summary combines retained runs and is not a claim that one integrated RTL
snapshot has passed the whole regression. `make phase7-far-check` performs that
fresh gate, retains the nested stack/frame and Phase 6 executable checks, and
uses a distinct bounded-increment success marker. Complete Phase 7 remains
strictly failing while the remaining 32 opcode files are unimplemented.

## Generated source contract

Format 14 has 83 entries and 492 words, nine-bit addresses and seven-bit controls.
Controls 113-115 are CHECK_PUSH2, CHECK_POP2 and ADD_ALLOCATION_SP. The 433 prior
words, entry addresses and loop destinations are preserved. Human-readable
zzzzzzzzzz_far_pointer.mc is authoritative. Frozen format-13 sources and the
independent literal phase7_far fixture check strict operand lifetimes, every
protocol step and generated consistency. No generated output is hand edited.

The separate arithmetic prototype also used tentative format-14 controls. It
must be rebased from its human-readable source after this increment is delivered;
its generated image cannot be merged with this one. Its four unresolved IDIV
physical captures are not waived or included in this passing far cohort.

The first expanded event bench passed its functional checks but failed its final
scenario-count assertion: the added case runs at five READY delays, not three.
The corrected total is 468. The nonzero run and exact hashes remain recorded.

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
