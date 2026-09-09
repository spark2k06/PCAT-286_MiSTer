# Phase 7 stack frames and bounds

This increment implements PUSHA (60), POPA (61), BOUND (62), ENTER (C8), and
LEAVE (C9). The isolated RTL passes all 24,999 non-revoked physical cases in
five complete opcode files. The single omitted ENTER record is already in the
pinned upstream revocation list; no local revocation or expected-data edit was
made. Integrated delivery status belongs to PHASE7_HANDOFF.md.

## Source and architectural behavior

Intel 210498-005 Appendix B BOUND B-22, ENTER B-40/B-41, LEAVE B-64,
POPA B-85 and PUSHA B-88 define the instruction protocols. Arithmetic and
addresses are 16-bit Real Mode operations; no 386 stack/address size exists.
Every instruction preserves FLAGS except for the existing exception entry.

PUSHA captures the original SP separately and pushes AX,CX,DX,BX,original SP,
BP,SI,DI. POPA reads DI,SI,BP,discards the stored SP word, then BX,DX,CX,AX.
Their preflight enumerates all eight modular word starts: even transfers may
wrap between words, while a word starting at FFFF faults before the operation.
The independent range unit checks every possible initial SP. PUSHA with SP
1,3,5 reaches shutdown through the existing failing exception-stack mechanism;
it is not implemented with a special instruction-index or corpus-byte case.
LEAVE checks the BP-based word before changing SP, then completes POP BP.

ENTER captures allocation and nesting level before data access, masks the level
to five bits, pushes the old BP, follows parent words in SS and pushes the new
frame pointer when the level is nonzero. A transient stack cursor feeds the
existing stack/operand service while architectural SP and BP retain their
original values. Each actual parent read or push checks its word offset.
After success, BP receives the frame pointer and SP the cursor minus allocation.
A fault discards transient state but preserves already accepted memory writes.
The exception frame uses the original architectural SP and first prefix IP.

An initial complete-transfer preflight incorrectly prevented earlier ENTER
parent writes in thirteen physical fault cases. The raw bus and final RAM
show those writes survive; the existing CPU register-restart rule does not
make memory atomic. Replacing that preflight with the transient cursor and
per-transfer checks passed all thirteen failures and the full 4,999-case file.
No expected physical memory was changed. Preserved raw examples 23,95,577 and
source hashes are in phase7_stack_frame_observations.json. Preliminary case
904 was independently found to be already revoked upstream and was never used
to introduce special RTL or a new exclusion.

BOUND rejects register addressing at the ModR/M byte with #UD, checks both
modular word starts before a data request, reads lower then upper words and
compares the signed index with inclusive limits. It raises #BR vector 5 when
outside either bound, and #GP vector 13 for an illegal word start. Both words
are read even when the lower comparison will fail.

The printed BOUND Real Mode rule says FFFD and above fault. Four independent
physical records instead read an even lower word at FFFE and the upper word
at 0000: one retires normally and three deliver #BR. Raw bus and both parsers
agree. The implemented physical 286 policy therefore permits that even wrap;
FFFD/FFFF still fault before reading either word. This evidence-based refinement
is explicit and is not a claim that the printed manual says the same thing.
The first blanket FFFC range-check run and its four failures are retained.

All 1,221 invalid-register BOUND captures retain unused generator tail bytes.
Their adapter admission requires original #UD evidence and bounded original
instruction bytes. The CPU faults at the invalid ModR/M; it does not decode or
execute the tail. The original capture bytes and memory remain unchanged.

## Microcode and ownership

Format 13 preserves all 356 previous words and adds five symbolic programs;
the image has 76 entries/433 words, nine address bits and seven control bits.
Generic fixed-register transfers, auxiliary/allocation storage, a five-bit
counter and symbolic conditional branches express the ENTER loop. Branch
metadata resolves instruction-local labels and has an explicit valid bit;
the existing sequencer validates range/target and owns every branch. The
executor has typed arithmetic/transfer operations, not a second x86 decoder.
Generated outputs are never edited manually. Independent literal word and
branch contracts, source mapping and canonical reconstruction are required.

PUSHA/POPA are explicit eight-word programs. The BIU retains physical ownership,
the operand service owns READY completion, and the existing register/segment
state modules remain the only architectural owners. Pauses freeze all loop,
frame and cursor state. Cancel/reset remove transient request/branch ownership
without rolling back already committed architectural or physical operations.
No historical instruction timing is encoded through meaningless idle states.

## Verification and preserved failures

The CPU bench passes 10,256 independent cases, 5,188,360 checks and 15,828
instruction-byte stalls in each simulator. It checks exact GPR/FLAGS/memory,
ordered bus accesses, all nesting levels, all address forms and precise faults.
The lifecycle bench passes 339 cases and 39,513 checks per simulator, including
NMI/INTR/TF competition, full exception frames, pause/cancel/reset at all program
boundaries, partial ENTER fault writes, PUSHA shutdown and mixed dependent code.
The stack-range bench independently enumerates all 65,536 initial SP values.

Fifteen intended RTL faults are rejected after two pristine benches. The
original target-XOR-one mutant survived the lifecycle bench's level-three
path; adding explicit zero/one-level event cases exposed the lost frame restore.
The failed original audit and the subsequent reason-mismatch run remain failed
evidence. No implementation or prior expectation was weakened. Earlier stale
compiler-version and LEA-audit anchors, the invalid-tail adapter failure, the
BOUND and ENTER implementation failures, and a report helper that incorrectly
assumed zero upstream revocations remain recorded in preparation logs.

The registry has 267 required files and 40 remain absent. The prospective
bounded total is 1,198,997 disjoint physical cases. Full combined regression,
synthesis, independent review and integrated delivery require actual recorded
results; prototype counts do not imply complete Phase 7 or historical timing.

## Completed integrated gate — 2026-09-09

Both increments passed the same fresh 1,198,997-case integrated gate, including
46 benches in each simulator, all 124 intended mutants and synthesis. See
[phase7_stack_frame_validation.json](phase7_stack_frame_validation.json) for the
exact input hashes, actual execution result and verified archive. This closes
user milestones 3 and 4; complete Phase 7 and independent review remain pending.
