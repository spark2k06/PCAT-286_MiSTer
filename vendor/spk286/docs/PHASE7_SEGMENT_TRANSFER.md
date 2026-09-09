# Phase 7 segment transfer and SS inhibition

This increment implements PUSH ES/CS/SS/DS (06/0E/16/1E), POP ES/SS/DS
(07/17/1F), and MOV to/from segment registers (8C/8E). Its nine pinned files
pass all 45,000 physical cases, including 1,481 #UD and 131 #GP outcomes.
LDS/LES were inventoried separately and are not part of this increment.
Integrated delivery and full Phase 7 status belong to PHASE7_HANDOFF.md.

## Architectural source and scope

Intel 210498-005 Appendix B MOV B-73 lists the four readable segment registers
and permits loading ES, SS and DS. MOV CS and indices 4..7 are invalid on 286;
the physical 8C/8E files confirm these #UD outcomes. No 386 segment alias is
introduced. Word source or destination offset FFFF uses the existing 286
word-limit fault behavior. A failed POP source preserves the original SP and
selector before the exception frame is pushed.

MOV B-73 states that loading SS inhibits all interrupts until after the next
instruction. POP B-83 explicitly includes NMI and explains that this permits
a following POP SP. This implementation also defers the sampled single-step
trap after the SS load itself, then resumes ordinary sampling after the
following instruction. A synchronous fault remains deliverable. Successful
repeated SS loads renew the documented protection of their next instruction.

All 45,000 physical cases begin with TF and IF clear. Those captures verify
data, flags, source faults and invalid encodings; they do not independently
establish SS interrupt inhibition. The latter policy is based on the Intel
text and is exercised by directed event tests. It is not a new exception to the
three retained Phase 6 evidence questions. An independent integer/address
model matches all 43,388 non-fault cases before RTL comparison.

## Ownership and ordering

The existing control decoder supplies a segment index from captured opcode
or ModR/M metadata. The executor receives the selected architectural selector
and uses only generic READ_SEG16 and WRITE_SEG16 operations. The source selector
port is independent of effective-address segment lookup. The existing segment
state module remains the sole selector/cache owner.

Source acquisition completes before cache write. POP SS reads through the old
SS, completes its SP increment, then loads the new SS selector and cache. A
following stack access consults the new base. A normal reload retains the
established Real Mode policy: selector shifted left four, FFFF limit and 93
normalized access attributes. Existing coordinated CS/IP event/debug reloads
retain their priority and atomic redirect contract.

The event arbiter owns one SS-shadow bit. A completed semantic SS write arms
it. Prefixes of the following instruction retain it; opcode dispatch begins
that protected instruction and clears the bit. Active-instruction ownership
then prevents an asynchronous event until the instruction's boundary. The
SS load itself cannot leave an owed single-step trap. Reset, debug cancellation
and accepted events clear inhibition. A failed SS load never acquires it.
No historical timing delay is encoded in these operations.

Format 12 adds controls 76 and 77 and four entries totaling fourteen words,
preserving all prior 342 words and symbols. The image has 71 entries/356 words,
nine address bits and seven control bits. Frozen format-11 sources and a literal
format-12 appendix independently check the generated image. Source-only
remnants of a format-12 segment load are rejected rather than silently
falling back to the older generic datapath validator after a lost cache write;
earlier format contracts remain unchanged.

## Verification

The CPU bench passes 4,800 cases and 354,661 checks per simulator, covering every
ModR/M register field and address mode, distinct source segments, all segment
overrides, invalid forms, selector boundaries, odd/even stack words and hidden
cache contents. The 42-case lifecycle bench passes 3,589 checks per simulator.
It covers MOV SS plus MOV SP, POP SS plus POP SP through the new stack base,
pending NMI/INTR/TF, repeated SS loads, a faulting load, a fault in the following
instruction, source/cache/END pause/cancel/reset, and later data through new DS.
Full physical runs preserve every original byte and compare complete fault RAM.

The initial compiler run exposed a stale accepted-version range. The next run
exposed incomplete segment programs falling through the legacy validator and
two stale event-mutation anchors. The compiler rejects the incomplete shapes;
the anchors preserve their original STI and IRET defects alongside the new
segment path. No physical expected results were changed.

The first segment mutation audit deliberately failed when removing only a
redundant trap-arbitration guard did not alter observable behavior: the
retirement path still prevented an owed trap. That surviving experiment is
retained as failed audit evidence. The replacement injects a concrete defect
that fails to arm SS protection when TF is set, exposing a premature #DB.
Final mutation, synthesis and complete integrated regression outcomes are
recorded in the validation record, not inferred from this document.

The prospective bounded total is 1,173,998 disjoint physical cases across 262
files, leaving 45 required Phase 7 files. Complete Phase 7, independent review
and any historical cycle-accuracy claim remain pending.

## Completed integrated gate — 2026-09-09

Both increments passed the same fresh 1,198,997-case integrated gate, including
46 benches in each simulator, all 124 intended mutants and synthesis. See
[phase7_stack_frame_validation.json](phase7_stack_frame_validation.json) for the
exact input hashes, actual execution result and verified archive. This closes
user milestones 3 and 4; complete Phase 7 and independent review remain pending.
