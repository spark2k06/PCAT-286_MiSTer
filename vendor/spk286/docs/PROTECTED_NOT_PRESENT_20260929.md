# Windows 3.1 absent-segment exception correction — 2026-09-29

## Captured failure after the direct CALL fix

The next integration run passed the previous `0307:B595` failure. Its first
new fault was:

```text
043F:9525  9A 7E 0B 47 04   CALL FAR 0447:0B7E
CPL=3, FLAGS=0216, SS:SP=027F:0FE4
CS base=01B3F0 limit=B6CF access=FB
GDTR=110800:011F LDTR=0038:114C50:5FFF
LDT[0447] at 115090 = 2F 04 90 82 1F 7B 10 00
Observed exception: #GP, error=0447, micro-PC=1DC (VALIDATE_CALL_GATE)
```

The raw descriptor from the saved guest RAM is nonconforming DPL3 readable
code with P=0. Its upper word is `0010`. The access is privilege-valid and
should request `#NP(0444)`, allowing software to load the segment and retry.
Checking the offset against its `042F` limit must occur after presence.
The later `0053:1E4D` error-reporting loop is secondary.

## Architectural evidence

- Intel 80286/80287 Programmer's Reference Manual 210498-005, Appendix B
  CALL checks, requires code type/privilege checks, then presence, then the
  stack and offset checks. Sections 9.6.5 and 11.1 describe absent-segment
  handling and instruction restart. Section 9.6.5 gives the selector error
  format: low bits identify EXT/IDT; they are not the selector RPL.
- Its section 7.4 note requires zero in descriptor bytes 6-7 for **80386
  compatibility**, rather than specifying a 286 fault for nonzero values.
- The Intel 80386 Programmer's Reference Manual, section 13.3.2, explicitly
  discusses 286 programs placing values in that last word:
  <https://pdos.csail.mit.edu/6.S081/2017/readings/i386/s13_03.htm>.
- Local 86Box `src/cpu/x86seg.c::loadcscall()` checks direct code privilege
  before presence and reports `x86np(..., seg & 0xfffc)` without rejecting
  that word.

The 286 manual is retained under `build/references/intel-286-programmer.pdf`;
the public Intel scan is
<https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf>.

## Changes

- The descriptor parser ignores the final word for code/data segments.
  Base remains 24 bits and limit remains 16 bits; no 386 attributes are added.
  This change does not audit the separate system/gate reserved-form rules.
- The executor distinguishes CS type/privilege validity from presence,
  preserving #GP precedence for illegal direct targets and delivering #NP
  for otherwise valid absent targets. A selector pre-check failure remains
  #GP, independent of stale descriptor data.
- Descriptor-generated selector errors clear RPL and carry EXT separately.
  CS offset violations report zero.

Two old tests had encoded the unsupported assumption that nonzero bytes 6-7
must fault. Their expectations now follow the Intel evidence above: the
foundation test checks decoded base/limit and type, and the incoming-task
test requires successful data-cache loading through both CALL and JMP.

## Bounded validation

The initial expanded direct-call reproducer failed 66 checks across 138
cases before the fix. That matrix passes after it. Six further cases exercise
a real #NP handler: verify the saved error and restart IP, publish the code
segment, IRET, retry CALL, execute the target and return to the caller.

- Final direct-call bank: 300 checks / 144 cases pass in Verilator and Icarus.
- Descriptor foundation: 65,573 checks pass in both simulators.
- Incoming task-state bank: 202 checks / 36 cases pass in both simulators.
- Existing protected-system bank: 538 checks pass in both simulators.
- RTL lint and generated microcode consistency pass.
- The PCAT vendor copy used by 86Box passes the same 144-case direct-call
  and retry bank in both simulators, RTL lint and microcode consistency.

Logs are `build/descriptor-np-*.log`. The initial reproducer result is in
`descriptor-np-before.log`; the final handler/retry matrix is in
`descriptor-np-retry.log`. Full regression and synthesis were not run,
following the user's request for bounded checks. Real Windows startup after
this change remains subject to the next integration run.
