# Phase 7 memory strings and repetition

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

Status: string/arithmetic integration candidate, 2026-09-09.
The complete integrated gate and the specific REP/TF evidence review remain
pending. This document does not close user milestone 7 or enlarge D-026.

## Functional ownership and sequencing

MOVS, CMPS, STOS, LODS and SCAS execute five project-owned microprograms.
The existing decoder supplies width, comparison and prefix metadata. The
microsequencer follows explicit validated local branch targets; the operand
unit and BIU retain all physical transfer and READY ownership. No loop counter
or RTL state represents a historical timing delay.

Each address is captured from the old SI or DI before that register advances
modulo 65536 by the byte/word width and DF. Source addresses use DS or the last
segment override; destinations always use ES. Source data is captured before
an overlapping destination is written. Byte loads preserve AH. Successful
CMPS/SCAS update all six arithmetic flags from source-minus-destination or
accumulator-minus-destination; other flags remain unchanged.

REP starts no element when CX is zero. Otherwise each successful element
decrements CX once. CMPS/SCAS test the newly calculated ZF against REPE/REPNE
after the first comparison, independently of entry ZF. Whole-instruction
retirement occurs once, after the loop terminates. Explicit LOCK spans that
instruction; HOLD and READY remain actual dependencies.

## Physical fault commit order

The pinned hardware corpus revision is
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`. Every one of the 50,000 unrevoked
memory-string captures passes with unchanged expected registers, flags,
memory, bus transactions and exception frames. Of these, 1,865 contain #GP.
The research pass also inspected the 218 INS/OUTS faults; those observations
are not memory-string RTL coverage or implemented string I/O.

| Instruction | Fault location | Retained attempted-element effects under REP |
|---|---|---|
| MOVS | Source word at FFFF | CX decreases once; SI advances; DI is unchanged |
| MOVS | Destination word at FFFF | SI and DI advance; CX decreases twice |
| CMPS | Destination word at FFFF | DI advances; CX and SI are unchanged |
| CMPS | Source word at FFFF | Both indexes advance; CX decreases once |
| STOS | Destination word at FFFF | DI advances; CX decreases twice |
| LODS | Source word at FFFF | SI advances; CX decreases once; AX is unchanged |
| SCAS | Destination word at FFFF | DI advances; CX decreases once |

These effects follow each form's complete access order, including prior
successful elements and CX underflow. Non-REP forms preserve CX. A rejected
word access issues no physical half-transfer; already accepted earlier writes
are retained. Faulting CMPS/SCAS do not commit new comparison flags. The fault
frame saves the first prefix. This is not an atomic rollback contract:
Intel's iAPX 286 Operating System Writer's Guide, 121960-001, section 7,
printed page 7-7, explicitly cautions against restarting a repeated string
after a segment-limit violation.

## Interrupt and lifetime contract

NMI and enabled INTR can be accepted before a nonempty REP's first element or
after a complete nonfinal element. A partial REP saves its first-prefix CS:IP;
the final boundary saves next IP. IRET refetches the instruction with the
retained CX/SI/DI so completed elements are not duplicated. Each odd word's
physical halves finish before the logical element boundary.

SS-load inhibition extends through the complete following REP and suppresses
NMI, INTR and TF there. STI extends its maskable-interrupt inhibition through
that instruction. Synchronous faults are still recognized. The inherited
STI-old-IF and failed-IRET policies retain their recorded status.

The candidate raises TF after each completed repeated element, with first-prefix
IP on a nonfinal trap and next IP on the last. Directed tests validate that
implementation, including IRET and SS/STI adjacency. IBM's October 1990
Hardware Interface Technical Reference, printed page 9, explicitly describes
per-iteration single stepping on 80286 REP MOVS. Its application to the common
REP mechanism of the other primitives is an inference requiring independent
review. See PHASE7_REP_EVENT_EVIDENCE.md for the exact source and limitations.
The initial CX=0 competing-event ordering remains a separate unresolved
question; no new exception is added to D-026.

Debug cancellation invalidates active addresses, temporary ownership and repeat
context while preserving architectural effects already committed. Reset follows
the native CPU reset path. Pause freezes execution without consuming a response
twice. Cancellation cannot undo accepted writes.

## Executed verification and its limits

- 10,272 independent instruction scenarios passed in both simulators, including
  byte/word operations, all source overrides, both directions, boundary offsets,
  overlap, early comparison termination, range faults and READY waits.
- 500 pause, cancellation, reset, event-frame and IRET scenarios passed in both.
- 148 fault-boundary, HOLD/LOCK, SS/STI, prefix-length and entry-event scenarios
  passed in both.
- All 50,000 physical cases passed without skips or added revocations. The
  independent parser and negative comparator audit also passed on the 285-file
  admitted inventory.
- Existing event, byte-prefix, data and segment mutation audits passed. New
  string mutation and synthesis execution records are retained separately;
  only actual successful results may be reported as passed.

The original scalar watchdog of 512 cycles rejected 1,283 long but progressing
physical REP cases. The test adapter now allows a finite `512 + 64 * initial_CX`
execution budget only for prefixed memory-string opcodes. Scalar and CX=0
budgets stay 512. This is a tooling limit, not a timing model, a RAM/FLAGS mask
change or permission to omit a physical case. Both failed and successful runs
are retained in the observation record.

`make phase7-string-check` requires a fresh directory and recursively reruns
the complete inherited gate on the same candidate before adding all string
captures and mutants. It checks unchanged source inputs and exact disjoint
identity coverage of 1,338,997 cases on the arithmetic baseline. A combination of older prototype reports
can validate accounting only; it cannot establish that integrated CPU result.

## Primary references

- [Intel 210498-005, 80286 and 80287 Programmer's Reference Manual](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf):
  section 3.7.2, chapters 5 and 9, and Appendix B instruction pages.
- Intel iAPX 286 Operating System Writer's Guide, 121960-001, printed pages
  7-3 and 7-7: stepping and string fault restart limitations; locally archived
  source identity is included in the observation record.
- [Hardware-generated 80286 corpus](https://github.com/SingleStepTests/80286/tree/37c73caf53dcd22d3dd369ff09305d13d117a4fe):
  all ten memory-string files and their original bus/EXCP/RMSK fields.

## Arithmetic-baseline integration candidate

The candidate preserves all 521 arithmetic words and appends 43 string words.
Format 16 has 92 entries, 564 words, ten address bits and eight control bits;
new controls are 121..130. Frozen format-15 arithmetic sources and the existing
independent arithmetic literal remain checked. No generated image was edited.
The active registry contains 295 required files; twelve I/O files remain pending.

The earlier observations above describe the separately validated string-only
prototype. The new candidate passed 240 ordinary tests, 86 compiler tests,
independent literal/round-trip audits, lint and the 256-opcode decoder in both
simulators. Seven separate CPU/lifecycle benches also passed in both: string
instructions, string lifecycle, string boundaries, arithmetic instructions,
arithmetic lifecycle, far instructions and far lifecycle. Its physical,
mutation/synthesis and fresh complete integrated gate have separate run records.

New IBM documentation explicitly supports per-iteration single stepping of
80286 REP MOVS. See PHASE7_REP_EVENT_EVIDENCE.md for the exact source, limited
scope and remaining CX=0 event-order question. Independent review remains pending.

## Fresh focused verification on the arithmetic baseline

All 140,000 physical cases across arithmetic (50,000), memory strings (50,000)
and far-control forms (40,000) passed without exclusions. Both simulators passed
the seven separate affected benches. All 18 string and 17 arithmetic RTL
mutants were rejected with passing pristine controls. The independent parser
and event comparator passed on all 295 admitted files, including 1,858 rejected
event probes. Synthesis passed with 17058 mapped / 1398 sequential cells.
Exact command records and retained log hashes are in
phase7_string_arithmetic_observations.json. These are focused prerequisites;
the fresh complete 1,338,997-case integrated gate is still required.
