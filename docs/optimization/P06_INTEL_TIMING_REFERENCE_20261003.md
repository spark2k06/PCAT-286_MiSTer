# P06/P12: Intel timing extraction for T286REF

Date: 2026-10-03. Status: reference extraction and source review complete for
the R0/B0/M0 kernel bodies. Historical CPU integration and physical 6/12 MHz
measurements remain pending; provisional components are tracked in
[the implementation progress](P06_PILOT_PROGRESS_20261003.md). This is a companion to the
[pilot contract](P06_TIMING_CONTRACT_20261003.md) and
[native wait-state measurements](P06_NATIVE_WAITSTATES_RESULTS_20261003.md).

## 1. Source identity and interpretation

The primary sources are Intel's 1987
[programmer reference 210498-005](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf)
and [hardware reference 210760-002](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf).
Their SHA-256, local paths, inspected pages,
native source hashes and unchanged DOS bytes are frozen in the
[manifest](../evidence/p06-intel-contract-20261003/manifest.json).
PDF page numbers below are **one based**. The relevant tables and footnotes
were checked against rendered scans; OCR alone misreads several opcodes,
including EB/8B/89.

| Intel source | Printed pages | PDF pages | Facts used |
| --- | --- | --- | --- |
| 210498-005 | B-6 | 214 | Clock unit, addressing/alignment/read-wait corrections, fetch limits |
| 210498-005 | B-19, B-33, B-116 | 227, 241, 324 | ADD, CMP, XOR operand forms |
| 210498-005 | B-54, B-56, B-70 | 262, 264, 278 | Jcond, JMP, LOOP and branch notes |
| 210498-005 | B-73 | 281 | MOV, including A1/A3 direct-offset forms |
| 210760-002 | 3-3 | 53 | Separate three-entry decoded-instruction queue and parallel units |
| 210760-002 | 3-15 through 3-19 | 65 through 69 | Processor clocks, phases, Ts/Tc/Ti/Th, address pipelining |
| 210760-002 | 3-24/3-25, 3-32 | 74/75, 82 | Six-byte prefetch, priorities, one buffered write, READY polarity |

One published instruction clock is **one processor clock**, not one clock
period at the chip's CLK pin. A 6 MHz processor uses a 12 MHz CLK input.
The instruction table gives an execution-rate reference under its stated
conditions; its memory forms are **not EU-only costs** to which all bus cycles
should then be added again.

B-6 requires an additional clock for base + index + displacement addressing,
two clocks per odd-address word operand reference, and one clock for each
extra wait on a memory read. Fetch/write waits may overlap execution. Its
5-10% aggregate fetch-overhead estimate is descriptive, not a correction
factor to apply to every kernel. Required instruction bytes, bus contention
and dependent reads must be modeled explicitly.

## 2. Frozen workload and timing forms

The unchanged T286REF2 COM is 2,840 bytes, SHA-256
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.
Offsets are file offsets; DOS IP is file offset + 0100h. Each gross sample
executes 256 iterations. Every LOOP executes 255 taken paths and one exit.
The manifest records actual final COM bytes, including ORG relocation, rather
than copying NASM's symbolic listing addresses.

The native column records **handler base charges** in the inspected original
286 backend. Memory/prefetch charges can increase elapsed execution further.
It is not a prediction of the whole DOS sample.

| Case / file offset | Actual bytes | Form / work per iteration | Intel processor clocks | Native 86Box base charge |
| --- | --- | --- | --- | --- |
| R0 / 038B | `01 D8` | ADD AX,BX | 2 | 2 |
| R0 / 038D | `31 FA` | XOR DX,DI | 2 | 2 |
| R0 / 038F | `83 C3 01` | ADD BX, sign-extended imm8 | 3 | 2 |
| R0 / 0392 | `81 F7 AA 55` | XOR DI,imm16 | 3 | 2 |
| R0 / 0396 | `E2 F3` | LOOP, target IP 048Bh | 8 taken / 4 exit | 11 / 11 |
| B0 / 0399 | `39 C0` | CMP AX,AX | 2 | 2 |
| B0 / 039B | `75 02` | JNE, always not taken | 3 | 3 |
| B0 / 039D | `74 01` | JE, always taken; next executed instruction is two-byte JMP | 7 + 2 target bytes | 7, then generic refill |
| B0 / 03A0 | `EB 01` | JMP short; next executed instruction is two-byte LOOP | 7 + 2 target bytes | 7, then generic refill |
| B0 / 03A3 | `E2 F4` | LOOP, target IP 0499h | 8 taken / 4 exit | 11 / 11 |
| M0 / 03A6 | `A1 10 0B` | MOV AX,[0B10h], aligned moffs16 read | 5 | 4 |
| M0 / 03A9 | `03 06 12 0B` | ADD AX,[0B12h], aligned direct disp16 read | 7 | 7 |
| M0 / 03AD | `A3 14 0B` | MOV [0B14h],AX, aligned moffs16 write | 3 | 2 |
| M0 / 03B0 | `81 36 16 0B 5A 5A` | XOR [0B16h],imm16, aligned read/modify/write | 7 | 7 |
| M0 / 03B6 | `E2 EE` | LOOP, target IP 04A6h | 8 taken / 4 exit | 11 / 11 |

Baseline file 0388h contains `E2 FE`: LOOP to itself at IP 0488h. It has the
same 255/1 branch split. Each kernel/baseline ends with C3 RET. B0's INC AX
at 039Fh and NOP at 03A2h are never executed and must not be charged.
M0 performs **three data reads and two data writes per iteration**; the XOR
accounts for one of each. Instruction fetch is additional traffic. Direct
disp16 and moffs16 use no base/index combination; every M0 word is physically
even because segment bases are multiples of 16.

Jcond B-54 and JMP B-56 explicitly qualify their taken cost by the length of
the next executed instruction. LOOP B-70 publishes 8/4 without that footnote.
Do not extend the Jcond/JMP footnote to LOOP without separate evidence.
Likewise, do not add that branch note twice by charging both a target-byte
allowance and the same fetch work in a timeline. How the note maps to the
prefetch/decoder timeline is a pilot acceptance item.

The table covers the kernel bodies, not all instructions between PIT latches.
CALL/RET, register setup, timer port I/O and signature stores contribute to
gross elapsed time. Their future timing metadata must be qualified before
claiming a complete T286REF historical run. The binary and instrumentation
remain unchanged; subtracting the baseline does not isolate EU time.

## 3. Why native 86Box is a contrast, not a cycle oracle

The accepted executable uses `exec386_2386`. In `386.c:197-222`, OP_TABLE maps
to `ops_2386_*`; `386_ops.h:2319-2340` selects the actual 16-bit 286 handlers.
This establishes that the shared handlers inspected here are used by these
native controls. With no FPU activity, their CLOCK_CYCLES charges apply
directly. Relevant points:

| Native source location | Observation |
| --- | --- |
| `cpu.c:904-914` | rr=2, rm=7, mr=7; conditional not-taken=3 plus taken increment=4 |
| `x86_ops_arith.h:58-86, 215-233, 381-398` | Register arithmetic/CMP and register-from-memory ADD |
| `x86_ops_arith.h:760-889, 956-998` | Group 81/83 immediates reuse rr/mr rather than Intel's separate register-immediate 3-clock forms |
| `x86_ops_jump.h:18-34, 161-176, 233-246` | Conditional branches, LOOP=11 for non-486, short JMP=7; taken transfers flush prefetch |
| `x86_ops_mov.h:344-357, 427-437` | A1 memory read=4; A3 memory write=2 for non-486 |
| `386_common.c:503-577` | Simplified prefetch: subtract encoded instruction/EA bytes; account for operand-memory occupancy and refills; cap at 16 bytes |
| `cpu.c:4483-4522`; `qt_settingsmachine.cpp:91-101` | 16-bit refill width=2; visible wait N becomes config N+1 and service cost N+2 |

The physical **prefetch** queue has six bytes. Intel also specifies a separate
**three-entry decoded-instruction queue** in 3-3 / PDF 53. Those are different
capacities, and instructions already decoded do not occupy prefetch bytes.
The native model's single 16-byte ceiling and whole-instruction accounting
do not directly reproduce these two queues. The ceiling alone does not prove
that all of its gain is fictitious: the physical CPU also has decoder lookahead.
A generic refill after a flush is not proof that the explicit
Intel target-instruction-length note is implemented exactly. Conversely,
differing handler constants alone do not determine the elapsed difference:
prefetch, actual memory service and instrumentation also contribute.

Existing results remain valid **raw fixed-work emulator measurements**. They
are not invalidated by this review, and their expected values are not changed.
Physical results may land outside the native envelope. Do not tune SPK286's
historical policy to reproduce these constants when Intel specifies another
form or the collaborator's identified hardware supplies contrary evidence.

## 4. CPU/board facts that the pilot must preserve

The hardware reference establishes these constraints:

- Each Ts, Tc, Ti or Th state is one processor clock. An ordinary zero-wait
  transfer uses Ts followed by Tc; every extra wait repeats Tc. Back-to-back
  transfers need no compulsory idle clock.
- The chip's **READY pin is active low**. PCAT/SPK286's normalized `ready` is
  active high. They are different interfaces; one must not copy the pin's
  polarity into the present handshake.
- Address presentation can precede the next Ts while the current transfer
  finishes. This is address pipelining, not permission to duplicate a command
  or release the current owner before its accepted transfer completes.
- Instruction prefetch normally transfers words when at least two slots of
  the six-byte queue are free. A transfer to an odd code target starts with a
  byte. Data outranks a new prefetch but cannot interrupt one already started.
- The instruction unit can queue three fully decoded instructions separately
  from prefetch. Current SPK286 dispatch starts a new instruction only while
  its microsequencer is inactive (`spk286.sv:836-864`,
  `spk286_microsequencer.sv:31`); it has no equivalent three-entry decoded queue.
  This is an identified architectural-model gap, not a measured throughput
  attribution or an authorization to add hardware storage.
- The EU inhibits prefetch two processor clocks before a data transfer. A
  historical candidate needs a qualified data-demand milestone; present
  priority-on-request behavior alone does not establish that lookahead.
- One CPU write may be buffered, allowing EU progress; a second pending
  write stalls it. PCAT's existing downstream posted-write slot is useful
  infrastructure, but its early acknowledgment and the CPU's historical
  write-buffer milestone require separate accounting.
- LOCK and the second part of an odd word precede HOLD in local-bus priority.
  A grant after Tc passes through Ti before Th. An accepted bus transfer must
  finish before another owner uses the bus.

These are CPU constraints. An ISA clock, memory wait policy or oscillator
tolerance belongs to an identified board. Native 6 MHz uses ISA 6 MHz; native
12.5 MHz uses ISA 8 MHz. Neither selection establishes the collaborator's
board cadence or automatically changes PCAT's device clocks.

## 5. Remaining evidence

This extraction is enough to specify a limited pilot and discriminating
checks. It does not identify internal EU micro-operation phases for every
opcode. Full latch-to-latch instruction coverage, branch-footnote timeline
placement, instruction-unit lookahead including the decoded queue,
selected-board memory/ISA policy and
physical 6/12 MHz measurements remain acceptance work. Protected-mode, REP,
variable-latency operations and complete event timing are later expansions.

The physical DOS program can reveal elapsed-work disagreements and signature
failures, but cannot reconstruct READY waveforms or internal prefetch phases.
Keep those limits when adjusting the model after the collaborator replies.
