# Protected Mode PM2a — Segment Reload and Hidden-Cache Enforcement

Status: implemented as a bounded PM2a slice. This increment covers protected
DS, ES and SS reloads plus the first execution-side cache and limit checks. It
does not claim complete protected mode or complete PM2 closure.

## Implemented contract

When PE is set, `MOV DS/ES/SS,r/m16` uses the existing microcoded descriptor
service and BIU ordering:

- the selector chooses GDT or LDT and is checked against the selected table
  limit before any descriptor response is accepted;
- the complete eight-byte descriptor is read before a segment cache candidate
  is considered for commit;
- DS and ES accept null selectors as an unloaded cache, while SS rejects null
  selectors;
- DS/ES apply the 80286 data/code readability and `max(CPL,RPL)` privilege
  rule; SS requires a writable data/expand-down descriptor with `DPL=CPL` and
  `RPL=CPL`;
- a present descriptor with its accessed bit clear performs the descriptor
  writeback before the hidden cache is committed;
- non-present DS/ES and SS candidates report #NP and #SS respectively; other
  invalid candidates report #GP;
- a successful reload commits selector, base, limit, access, class, presence,
  protection, DPL, table indicator and RPL together through
  `spk286_protected_state`.

The cache is the protected-mode source for debug state and logical address
translation. For a protected cache entry, invalid type/presence and complete
word accesses beyond the normal or expand-down limit are rejected before the
data request reaches the BIU. SS faults use vector 12; the other covered data
access faults use vector 13. Real-Mode segment behavior remains owned by
`spk286_segments` and is mirrored into the protected-state storage while PE is
clear.

The committed CS cache also supplies the protected instruction-fetch base and
limit. Speculative prefetch stops at the final legal offset. If an instruction
already admitted at that boundary needs another byte, the demand path raises
#GP before issuing an out-of-limit code cycle, preserves the incomplete
instruction's destination state, and delivers the protected error-code frame.
The handler can consume that word and return with `IRET` without losing the
interrupted stack context.

These rules follow the 80286 protected-segment model in the
[Intel 80286 Programmer's Reference Manual](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
The implementation intentionally keeps historical timing separate from the
functional descriptor and BIU dependencies.

## Verification

`sim/unit/spk286_protected_system_tb.sv` adds the following integrated checks:

- GDT DS, ES and SS reloads commit coherent protected hidden-cache state;
- an LDT-backed DS selector resolves through the loaded LDTR;
- the limited GDT data descriptor writes its accessed bit (`92h` to `93h`)
  before cache commit;
- a valid-form but not-present DS descriptor raises #NP without changing the
  hidden cache or descriptor access byte;
- a valid-form but not-present SS descriptor raises #SS without changing the
  hidden cache or descriptor access byte;
- a word load beyond the protected limit raises #GP without a target data bus
  cycle;
- a two-byte immediate that begins at CS:01FE with a CS limit of 01FF raises
  #GP without a CS:0200 fetch or partial AX write, and its handler restores the
  interrupted context with `POP`/`IRET`;
- the existing PM1 checks and deliberate READY stalls continue to pass.

The bench passes in Icarus with 100 total checks. The
focused core, segments, decoder, execution and protected-foundation tests also
pass after the PM2a wiring change; lint and synthesis are required before
commit.

## Explicitly deferred

The following remain later work and are not implied by this slice:

- protected CS reloads, far CALL/JMP/RET, gates, privilege transitions and
  queue redirect/fetch restart under a new CS;
- full #GP/#NP/#SS/#TS fault-frame delivery and restart semantics;
- complete descriptor privilege/type coverage, including the remaining
  conforming-code, null-selector/system-descriptor combinations and broader
  fault/restart matrices; expand-down data and protected transition-stack
  paths are covered by [PROTECTED_MODE_PM2E.md](PROTECTED_MODE_PM2E.md);
- broader protected instruction-length, restart and fault-classification
  matrices beyond the covered normal expand-up CS boundary, plus the remaining
  PM2/PM3 instruction families.
