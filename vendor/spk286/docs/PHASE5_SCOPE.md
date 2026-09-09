# Phase 5 scope and evidence

Baseline: `caffc0beeff15b35370c03c834f884cbf9407e26`, reproduced with
`SPK286_BUILD_DIR=build/phase5-baseline make phase4-check` in a fresh directory.
The gate completed with `PHASE4_VALIDATION_PASS` before implementation began.

## Admitted instruction forms

Unprefixed 16-bit Real Mode only: PUSH/POP r16 (50..5F), PUSH imm16/imm8s
(68/6A), PUSH r/m16 (FF/6), POP r/m16 (8F/0), near CALL rel16 and r/m16
(E8, FF/2), near JMP rel16/rel8/r/m16 (E9, EB, FF/4), near RET with and
without stack release (C2/C3), all sixteen Jcc (70..7F), and
LOOPNE/LOOPE/LOOP/JCXZ (E0..E3).

REALMODE_MVP assigns LOOP to the stack/control-flow milestone. Per D007,
incremental implementation phases do not claim completion of every instruction
in the broader RM milestone. Segment-register transfers, PUSHF/POPF,
PUSHA/POPA, ENTER/LEAVE, far transfers, exception delivery, interrupts,
prefixes, byte operations and later phases remain outside this increment.

## Architectural evidence and implementation boundary

Intel 80286 Programmer's Reference Manual, Appendix B, PUSH/POP, CALL/RET,
JMP/Jcc and LOOP entries are authoritative. The cached manual SHA256 is
`ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.
PUSH SP stores its original value; POP SP's loaded destination replaces the
incremented SP. CALL pushes the next consumed architectural IP. Relative
targets wrap at sixteen bits. RET imm16 releases its unsigned immediate in
addition to the popped word. FLAGS and CS are preserved by these forms.

Stack addressing uses SS and the existing whole-word operand limit check.
Invalid words must block without a partial data cycle, SP/destination update
or retirement. POP memory validates its destination before popping. Exception
delivery and the documented shutdown behavior are deferred, not emulated as
successful execution.

The existing operand service owns logical transfers; the BIU continues to own
READY, arbitration and odd-word splitting. A shared stack operation owns SP
arithmetic. Taken redirects atomically update IP and flush/restart prefetch;
they do not cancel the retiring microprogram. External redirects retain their
existing cancellation semantics. The sequential microsequencer remains generic.
Functional operations introduce no compatibility timing delays.

## Hardware corpus boundary

SingleStepTests/80286 remains pinned at
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. The 47 new files above contain
235,000 discovered vectors before explicit revocation/prefix/exception
exclusions. All admitted vectors must execute in the release gate alongside
the inherited 213,980. Published final IP includes the harness's trailing HLT;
the CPU adapter stops at the target instruction retirement and removes that
one byte. For control transfers, the HLT is injected at the destination by
the physical test harness; a sequential-IP assumption is therefore invalid.
No register, flag, memory or branch target expectations may be relaxed.

## Required release evidence

Independent Python stack/target/condition/count models, exhaustive condition
truth tables, directed dual-simulator stack/control-flow and lifecycle tests,
compiler and independent ROM contract checks, meaningful RTL mutations,
complete new and inherited hardware families, lint, synthesis and regression.
`make phase5-check` must preserve the complete Phase 4 gate. A clean final
build and deterministic regeneration precede verified commits and handoff.
