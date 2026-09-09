# Phase 7 decimal and radix adjustment

The six forms are DAA 27, DAS 2F, AAA 37, AAS 3F, AAM D4 and AAD D5.
All 30,000 pinned physical captures pass, including eleven zero-radix AAM
divide errors. Integrated-gate and delivery status are recorded in PHASE7_HANDOFF.md;
this prototype evidence does not claim full Phase 7 or an independent review.

## Sources and result policy

Intel 210498-005 Appendix B B-15 through B-18 and B-36/B-37 specify the six
adjust operations and their defined flags. The manual's AAM/AAD descriptions
use decimal radix 0A. The pinned physical D4/D5 files contain every byte radix;
the implementation follows those captured general arithmetic results without
rewriting opcodes, immediates, saved memory or comparison masks.

DAA/DAS compute both corrections from the initial AL, AF and CF. DAS retains
the low-digit subtraction borrow in CF. AAA/AAS adjust the complete AX by
0106 before masking AL to its low nibble; a carry/borrow across the byte
boundary is observable in the physical records. AAM writes quotient to AH
and remainder to AL. AAD writes the low byte of AL + AH * radix and clears AH.

Normal flag masks are 00D5 for DAA/DAS, 0011 for AAA/AAS and 00C4 for AAM/AAD.
Other bits are preserved. These normal undefined-bit choices are kept separate
from the zero-radix fault observation below.

## Zero-radix AAM frame evidence

All eleven pinned D4 radix-zero cases preserve AX and deliver #DE without an
instruction retirement. Their saved FLAGS bytes expose SZP for unsigned initial
AL shifted right by one and clear CF, AF and OF. The fault-only mask is 08D5.
The frame RAM comparison is unmasked even where the final FLAGS register uses
RMSK, so a normal 00C4 mask cannot hide an incorrect saved frame.

The independent full-frame calculations and all eleven identities are retained
in phase7_adjust_zero_radix_observations.json. This is an explicit physical
observation policy, not an Intel guarantee for otherwise undefined flags.
These captures start with TF and IF clear; they do not resolve the inherited
fault-TF question or establish additional interrupt behavior by themselves.

## Functional ownership

The arithmetic service receives a functional kind, AX, radix and carry/auxiliary
inputs, with request/response, enable, cancel and reset. It owns no opcode,
architectural register or bus. Eight restoring-division steps implement AAM;
eight add/shift steps implement AAD. Those steps perform arithmetic dependencies,
not historical timing delays. Accepted inputs are captured and a completed
response remains stable under backpressure or pause.

Format 11 adds ADJUST and CHECK_ARITHMETIC controls and two seven-word programs,
preserving all prior 328 words and symbols. The new image has 67 entries and
342 words with nine address bits and seven control bits. The direct program
acquires AX; the radix program must first acquire its actual immediate byte.
Both compute, dispose of or commit the result, commit FLAGS, check arithmetic
fault status, and then retire only on the non-fault path. Zero-radix AAM
suppresses AX but commits its observed flags before the existing event owner
captures the frame. The fault check is a real serialization dependency.

Reset/start/cancel clear the arithmetic service and pending fault state. Pause
holds semantic execution. Debug cancellation preserves already committed AX
or FLAGS but discards uncommitted results and events. Demanding instruction
byte eleven raises #GP before arithmetic, with unchanged AX/FLAGS and the
first prefix as the restart IP. Existing asynchronous-event ownership remains
in the event arbiter; this increment does not duplicate it.

## Verification

An independent closed-form integer reference covers 352,256 arithmetic inputs,
including the full AL/CF/AF domains with AH edges, all AAM radix/AL pairs and
every AAD radix/AH pair with AL edges. Both simulators pass 4,740,163 checks,
including input snapshots, pause, held response, cancel and reset. A CPU bench
passes 8,184 normal cases, 659,764 checks and 2,044 immediate-byte stalls per
simulator. The dedicated lifecycle bench passes 157 cases and 9,075 checks,
including full even/odd exception frames, pending NMI/INTR competition,
length-fault precedence, fault cancellation and dependent instruction streams.
All twelve injected arithmetic, frame, dispatch and lifetime defects are
rejected by their intended semantic assertions; three pristine benches pass.

Early pure-service runs exposed testbench delta-cycle races at reset/cancel
release; a one-delta settle fixes observation ordering without changing RTL.
An early CPU run matched all 8,184 normal results but failed its immediate
starvation coverage assertion because every radix pair was in one fetch word.
Adding a single prefix for one case class crosses a fetch boundary and exercises
the retained assertion. Width lint was resolved with explicit remainder
truncation, and the service instance was moved after temporary declarations
to avoid Icarus implicit-net warnings. Failed logs remain failed evidence.

The bounded integrated gate requires the inherited regression, lint, both
simulators, all relevant physical files, mutation checks, synthesis and frozen
input consistency. Its prospective disjoint total is 1,128,998 across 253 files;
54 required Phase 7 opcode files still remain. No cycle-accuracy claim is made.
