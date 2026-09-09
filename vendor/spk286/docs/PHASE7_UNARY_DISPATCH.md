# Phase 7 unary arithmetic and decoded dispatch

This isolated increment implements NOT F6/F7 /2, NEG F6/F7 /3 and INC/DEC
FE/FF /0,/1. The eight complete pinned files pass 40,000 RTL cases, including
132 word-limit faults. Five affected prior TEST/near-control files pass 25,000
additional cases; these are already part of earlier cohorts and are not added
twice to the combined count. Full integrated delivery is recorded separately
in PHASE7_HANDOFF.md; complete Phase 7 and independent review remain pending.

## Architectural evidence

Intel 210498-005 Appendix B B-38, B-46, B-77 and B-79 specify DEC, INC, NEG and
NOT. NOT preserves FLAGS. INC/DEC preserve CF. NEG subtracts the operand from
zero, sets CF except for zero input, and defines OF/AF/SF/ZF/PF normally.
An independent integer/address calculation agreed with all 39,868 non-fault
physical records before implementation. The other 132 records contain #GP;
the full RTL run includes them. No expected value, mask or byte was changed.

## Generic branch and operand ownership

F6/F7 and FF first acquire the ModR/M/displacement context, then execute a
terminal DISPATCH DECODED operation. The existing x86 control decoder chooses
a generated symbolic target. F6/F7 /0 retain the existing TEST targets;
FF /2,/4,/6 retain GROUP5_NEAR. FE /2..7 are owned invalid forms and fault at
ModR/M without consuming displacement bytes. Other legal unsupported groups
remain distinct from #UD and internal microcode faults.

The microsequencer receives only branch request, target and target-valid.
It validates range and validity, waits for completion permission, and preserves
the original entry and instruction metadata. The executor does not decode an
opcode. No branch produces guest retirement; only the target's END does.

Existing targets begin with DECODE_MODRM. A generic dispatch explicitly rearms
the already complete operand context. The decoder returns its stored offset and
fields once without consuming a byte or consulting changed GPR inputs. Its
original one-pulse completion behavior remains unchanged for ordinary calls.
Pause holds the pending reuse; start/cancel/reset discard it. This is a real
context-availability handshake, not historical timing padding.

NOT/NEG/INC/DEC use the existing ALU and architectural GPR/FLAGS owner.
Constant temporaries and a decoded operand-direction bit express the arithmetic.
Memory result completion precedes FLAGS commit. Cancellation preserves prior
architectural writes and drains only writes already accepted by the BIU.

## Verification and initial audit findings

The independent CPU bench passes 10,832 cases and 810,712 checks per simulator,
including every byte input/register alias, word boundaries, all EA modes,
READY, prefixes and exact memory writes. The expanded microsequencer bench
passes 59 checks; the operand decoder bench passes 1,280 contexts and 12,111
checks with explicit cached-address pause/cancel/reset coverage. The 70-case
lifecycle bench passes 3,170 checks across fifteen unary boundaries, 24 invalid
FE forms and a dependent unary/TEST/indirect-PUSH/POP stream.

The first three mutation-audit attempts rejected the injected RTL defects, but
their configured failure reasons named later register checks. The first actual
failures were FLAGS for reversed NEG, memory for a truncated complement constant,
and FLAGS for a wrong NEG target. The audit now requires those exact earlier
semantic failures. Original failed logs remain failed; expected CPU results and
assertions are unchanged. The final mutation and synthesis status belongs to
the retained run record, not this descriptive document.

Format 10 contains 65 entries/328 words with all prior 282 words and symbols
preserved. An independent literal appendix and frozen format-9 sources check
the ABI. Complete malformed-protocol and default audit-CLI checks remain required.
The full bounded gate must pass 1,098,998 disjoint physical cases; 60 required
opcode files remain absent. Inherited Phase 6 evidence questions are unchanged.

The first integrated full gate stopped at the legacy stack lifecycle test.
Its unsupported-group selector still included FF /0 and /1, now documented and
implemented INC/DEC. A direct replay reproduced the failure. Only that selector
was updated: all invalid FF register /3,/5,/7 and invalid 8F forms retain their
original no-partial-effect assertions; exhaustive unary and physical tests cover
the newly supported groups. Both simulators then passed the complete stack
lifecycle bench. The failed gate and reproducer remain archived as failures.
