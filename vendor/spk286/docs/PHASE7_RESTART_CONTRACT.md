# Phase 7 iteration and irreversible-effect contract

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

Current update (2026-09-09): the ordered isolated candidate implements these
boundaries and has received independent review. Nonzero REP TF stepping/restart
is supported with the documented inference beyond MOVS; zero-count competing
events remain unresolved. The preliminary contract and physical observations
below are preserved. See [REP evidence](PHASE7_REP_EVENT_EVIDENCE.md),
[independent review](PHASE7_INDEPENDENT_REVIEW_20260909.md) and
[closure](PHASE7_CLOSURE_20260909.md) for current implementation/delivery status.

Status: pre-implementation contract, 2026-09-08. This document describes required
boundaries and identifies questions to resolve with primary/physical evidence;
it is not a report of implemented or validated behavior.

## Successful string iteration (not a fault-atomic commit rule)

Width is one or two bytes. Direction updates are modulo 65536: +width with
DF=0, -width with DF=1. A segment override affects the source where applicable;
ES:DI remains the string destination. Stack and instruction fetch use their own
segment owners. A normal retirement occurs once for the complete instruction;
an iteration completion is a distinct internal boundary.

| Primitive | Source | Destination | Ordered transfer | Committed iteration state |
|---|---|---|---|---|
| MOVS | override or DS:SI | ES:DI | read source, write destination | SI and DI advance |
| CMPS | override or DS:SI | ES:DI | read destination, read source, subtract source-destination | SI/DI advance; arithmetic FLAGS |
| SCAS | AL/AX | ES:DI | read destination, subtract accumulator-destination | DI advances; arithmetic FLAGS |
| LODS | override or DS:SI | AL/AX | read source, write accumulator | SI advances |
| STOS | AL/AX | ES:DI | write destination | DI advances |
| INS | port DX | ES:DI | read port, write destination; fault evidence below forbids assuming memory prevalidation | DI advances; see fault effects below |
| OUTS | override or DS:SI | port DX | read memory, write port | SI advances; see fault effects below |

On a successful repeated path, CX decreases by one per element; nonrepeated
forms preserve CX. This does not specify the fault commit point: the physical
records below demonstrate a CX decrement even for an element that faults. Initial CX=0 performs no element or port access. MOVS/LODS/
STOS/INS/OUTS repeat until CX=0. CMPS/SCAS additionally stop when their result
ZF disagrees with REPE/REPNE. Entry ZF must not prevent the first comparison.
The final comparison's FLAGS survive ordinary successful completion.

The source value must be captured before an overlapping destination is written.
Physical odd-word halves are one logical element transfer, each independently
READY-gated. A held response is consumed once. Accepted I/O reads and writes
are irreversible external effects; reset or debug cancellation cannot claim to
undo them. Repeating an already accepted I/O request is a correctness defect.

At an interruptible boundary, completed elements remain committed, remaining
CX and next SI/DI identify the unexecuted work. A nonfinal repeated instruction
must save its documented restart CS:IP including required prefix context. The
completed instruction saves next IP. IRET refetch/resumption must not duplicate
an element or use stale queue bytes. Faults before/within an element require a
per-form commit order, including which read/write effects have already occurred.

## Primary evidence and research obligations

Intel 210498-005 section 3.7.2 and Appendix B REP (B-92–93) establish count,
comparison, direction and pending-interrupt checks per repetition. The body
lists interrupt acknowledgement before the count check; Appendix B lists the
zero-count check first. Ordinary CX=0 has no element side effects under either
description, but the exact event boundary must be checked before declaring
competing-event coverage.

General saved fault CS:IP includes all leading prefixes (chapter 9); REP-specific
TF granularity and interrupted restart behavior require an explicit 286 source
or physical capture before claiming those event scenarios. The ordinary
instruction retirement pulse is not itself evidence for REP stepping.

MOV into SS's Appendix B page states all interrupts are inhibited through the
following instruction. POP SS, TF/NMI/INTR distinctions, consecutive shadow
producers and STI/REP adjacency require a source-specific contract. The Phase 6
STI-old-IF interpretation is not reused as an SS-load rule.

Intel 210498-005 LOCK B-68 and 210760-002 section 2 (printed 2-17) describe
automatic XCHG locking and explicit string/rotate usage. Instruction-specific
LOCK duration must be verified; a modern x86 opcode whitelist is not evidence.
The retained B-2 INTA chain remains distinct from ordinary I/O and explicit LOCK.

Open new questions in this working contract are implementation obligations;
they do not enlarge the three-item provisional-development exception.

## Physical fault effects that constrain future implementation

A later preparation-time inspection of the pinned corpus found observable
partial effects that the successful-path table must not obscure. These are
physical input observations, not executed SPK286 string tests or a complete
adjudication of all REP/event ordering. No expected record was changed.

| Exact physical case | Observed result on #GP | Implementation constraint |
|---|---|---|
| 6D index 1, `aebe839133cb336ad219f9947aeb42c1189db647` | INSW at DI=FFFF, DF=1 performs IOR; final DI=FFFD | A port read and index effect cannot be erased by a later destination fault |
| 6F index 24, `1cd84ac8a961224a512d852a6c8ebce27313a6b7` | REP OUTSW at SI=FFFF: CX 63->62, SI=FFFD; no IOW | A faulting attempted element can retain CX/SI effects without a completed output |
| A5 index 41, `939b93037a1081d9512d12c02a6e65028dbfbb0f` | MOVSW with SI=DI=FFFF, DF=0: SI=1, DI unchanged | Source failure occurs before destination-index effects |
| A5 index 42, `4317a9fa5f0b9f4ff19d8d207916102b6a5e93d7` | MOVSW source valid, DI=FFFF, DF=1: both indexes decrease | Destination failure retains both index effects |
| A7 index 57, `e81f1a3d566fdf52aa9c14a63f33251e8698871b` | CMPSW with SI=DI=FFFF, DF=0: DI=1, SI unchanged | Comparison's destination access precedes its source access |
| AD index 60, `b2f1b76649b54a2939067e358fa837997995b670` | LODSW at SI=FFFF, DF=0: SI=1, AX unchanged | Index update is distinct from accumulator commit |

STOSW and SCASW fault samples similarly retain DI movement. EXCP counts from
the complete source files are 109 each for 6D/6F, 525 for A5, 522 for A7, 277
for AB, 265 for AD and 276 for AF; these are inventory counts, not RTL passes.
The reduced working report is
`build/phase7-preparation/string-fault-research.json`.

The upstream parser, independent wire RMSK/EXCP readers and project parser
agree on all 29,000 records in these seven word-string source files. Eleven
selected raw examples and source hashes are retained in
[phase7_string_fault_observations.json](phase7_string_fault_observations.json).
This confirms parsing, not the generality of a proposed micro-operation order.
REP INSW index 126 retains CX 46->44 on its faulting path; REP STOSW index 223
retains CX 7->5, while REPE/REPNE CMPSW index 191 preserves CX=7. These observations
forbid replacing the missing per-form fault contract with one universal
predecrement rule.

Before writing the reusable iteration microprogram, audit all fault outcomes,
including faults after prior successful elements. Preserve old offsets for each memory access while
applying the observed register effects in the correct order. Successful-iteration
completion, attempted-element register effects, irreversible I/O and whole-
instruction retirement need separate signals/controls. Do not use a universal
"commit all SI/DI/CX after memory completion" rule. Exact interruption/IRET and
TF/SS-load behavior still requires its separately identified evidence.
