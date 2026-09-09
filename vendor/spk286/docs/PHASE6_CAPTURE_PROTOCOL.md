# Phase 6 physical capture protocol

Status: **prepared, not physically executed**. All three architectural questions
remain open. Payload source: [research/phase6_probes](../research/phase6_probes/README.md).
Research/admissibility: [closure dossier](PHASE6_EVIDENCE_CLOSURE.md).

## Fixture contract and missing integration

Use a physical Intel-compatible 80286 in normal Real Address Mode, with known
vendor/markings/stepping (or explicitly unknown stepping), a valid reset and
ordinary segment caches. A Harris result establishes that part's behavior;
it does not establish every Intel/AMD/Siemens stepping. Record voltage, clock,
temperature if available, markings photo, fixture firmware/host revisions and
all adaptation hashes. Keep INTR and NMI low throughout reset and setup.

Required equipment is a CPU bus responder and capture system with writable
memory at the specified physical addresses, programmable NMI/INTR, two-cycle
INTA response, and complete accepted reads/writes plus pin waveforms. It must
serve code exactly as uploaded, including far/near transfers and handlers,
without injecting a HLT at each branch target. Supply all 24 address bits,
data lanes, BHE, bus status, READY, LOCK, INTR, NMI, CLK and RESET. Distinguish
native status/T-states from SPK286's normalized simulator interface.

The public [ArduinoX86 revision 2ccae647](https://github.com/dbalsom/arduinoX86/tree/2ccae6470ef2cc12e247b74e3ad2d226b7f74936)
is a possible basis. Its README documents Harris 80C286 and pin control;
`CommandServer.h/.cpp` expose pin writes, cycle stepping and cycle-state reads.
`Shield80286.h` describes two external CLK periods per processor cycle. Its
`exec_program` client has NMI/INTR cycle scheduling, but these facilities have
**not** been integrated with this package. The inspected source bytes/URLs are
hashed in `build/phase6-evidence-closure/fixture-sources/sources.json`.

The [pinned SingleStep methodology](https://github.com/SingleStepTests/80286/blob/37c73caf53dcd22d3dd369ff09305d13d117a4fe/README.md)
uses HALT followed by NMI/STOREALL for collection. That path is unsuitable here.
Before a capture, the fixture operator must establish and verify:

1. Physical reset execution from FFFFF0, with the provided memory mapping.
2. No jump-target HLT injection, queue seeding, automatic NMI termination,
   STOREALL, interrupt-based trigger alignment, or debugger single stepping.
3. Accepted-write trigger support for A, and adequately resolved pin scheduling
   for B/C. A software cycle counter does not prove opcode execution.
4. A passive memory/bus capture stop after the terminal dump and HLT. Continue
   the part's required clock after HLT while collecting memory. Stop logging,
   not the dynamic CPU clock, unless the exact part permits static operation.
5. Trace export without commands that execute a finalizer/store routine.

The workspace exposed a serial port named COM3 during read-only enumeration;
its device identity and CPU-fixture role were not established. It was not opened
or sent commands. There is no identified, configured, authorized physical 286
fixture for this task. No hardware was purchased, rewired or flashed, and no
capture request was sent. Integration with suitable equipment is an explicit
remaining step, not an already functioning hardware driver.

## Build, memory and initialization

Run the commands in the probe README using fresh output directories. Each
configuration supplies NASM source-derived binaries, listing, disassembly,
memory mapping/hashes and a NOT-RUN result template. Build uses `cpu 286` and
checks the important opcodes independently. There is no DOS/BIOS dependency.

| Physical address | Size | Initial image / role |
|---|---:|---|
| 000000 | 10000 hex bytes | low.bin: all IVT entries, markers/data initially zero |
| 010000 | 1000 hex bytes | code.bin: CS=1000, reset bootstrap at IP=0100 |
| 030000 | 10000 hex bytes | stack.bin: SS=3000, initialized A5 except return controls |
| FFFFF0 | 10 hex bytes | reset.bin: far JMP 1000:0100, remainder CC |
| Every other physical byte | — | CC default; reads/writes still recorded |

The complete IVT initially points to CS=1000. Offsets: #1=0500, NMI=0600,
#UD=0800, #GP=0400, INTR vector 40h=0700; every other vector goes to 0A00 and
writes the unexpected-event marker. A's first NMI handler changes only vector
2's offset to 0680 **before** its armed marker; CS remains 1000.

After setup, AX=A286, BX=B286, CX=C286, DX=D286, BP=5286, SI=6286, DI=7286,
SP=8000, CS=1000, DS=ES=0000, SS=3000. FLAGS=0002 except the explicit tested
IF/TF changes. The normal real-mode segment reloads establish 64 KiB limits;
hidden-state assumptions derive from reset/reloads, not a fabricated LOADALL
dump. Record unknown hidden cache bits as assumptions. MOV SS is followed by
MOV SP and several setup instructions; all pins remain low during that setup.
General registers unspecified by physical reset are explicitly initialized.

All markers are word writes of DX=D286 to DS=0. Addresses are physical:

| Address | Meaning |
|---|---|
| 2000 / 2002 | Bootstrap completed / experiment armed |
| 2010 | Instruction after tested STI/target has actually written its marker |
| 2020 / 2022 | First #GP handler instruction / explicit TF-restoration control |
| 2030 | First #1 handler instruction |
| 2040 / 2042 | First A NMI setup executing / terminal NMI executing |
| 2050 / 2060 | INTR / #UD handler executing |
| 2070 | Successful IRET return target executing |
| 2080 | Nine-word diagnostic dump completed |
| 20F0 | Unexpected control flow or vector; investigate rather than pass |

A terminal handler starts with its unique marker. After the discrimination
boundary it executes `PUSH SP; PUSHF; PUSH AX; PUSH BX; PUSH CX; PUSH DX; PUSH BP;
PUSH SI; PUSH DI`, writes 2080 and halts. There is no diagnostic IRET or NMI.
At final SP the nine words are DI, SI, BP, DX, CX, BX, AX, FLAGS, pre-dump SP.
PUSH SP stores its pre-decrement value on the 286. The dump uses 18 descending
bytes below any saved frames. It does not overwrite them. Final SP equals
pre-dump SP minus 18; CS:IP is reconstructed from the executed terminal path
and HLT boundary, while stack words/FLAGS/GPR images are measured bus writes.
DS/ES/SS are known from unchanged setup, not an independent register dump.
State this distinction in the result. Unknown/failed dump paths stay inconclusive.

For C, the first GP marker is itself the instruction needed to distinguish a
step after a handler instruction. A #1 there precedes the GP dump. The optional
TF-restoration experiment adds its restoration sequence before that dump.
All diagnostic writes must be tagged separately from the event frames and
the first-handler markers when interpreting the measured interval.

## Native timing, capture and trial acceptance

Intel [210760-002](https://bitsavers.trailing-edge.com/components/intel/80286/210760-002_80286_Hardware_Reference_Manual_1987.pdf),
printed 3-12/PDF62, requires NMI low for four system clock cycles before its
rising transition, then high for at least four additional cycles. Printed
3-15/PDF65 defines system/external CLK as twice the internal processor clock.
Record full periods and edge phase; do not confuse edges, periods and processor
cycles. An optional conservative fixture margin is eight complete external-CLK
periods low and eight high, subject to the actual part's datasheet. This margin
does not prove instruction-start alignment. Keep each second edge well inside
the recorded inhibited interval in A; if timing cannot do that, reject the trial.

The same manual, printed 3-13/PDF63, requires INTR active at least **two
processor cycles before instruction completion** to interrupt before the next
instruction. This is a critical limitation for the short STI experiment.
Do not transfer modern x86 interruptibility or SPK286 internal timing to silicon.

For B/C perform a phase sweep relative to accepted armed write 2002. First find
a coarse bracket including pre-target acceptance, target-associated delivery
and late delivery; retain every trial. Refine each transition across both
external-CLK phases, with resolution sufficient for the part's sample window.
Record exact grid, clock periods, pulse widths, trigger latency/jitter, READY
schedule and repeats. Start with three repeats per point and a fresh reset/image
for each. Extend the bracket if it does not straddle the events; a bounded
timeout or all-late sweep is inconclusive. A fixture providing only coarse
processor-cycle steps may lack sufficient resolution.

Classify trials by actual accepted marker writes, saved frames and pin waveform.
Code fetch means bytes were prefetched; it is never proof of execution. No TF
alignment aid is permitted for B. For C no setup instruction may run with TF=1
between POPF and the target. Do not insert an interrupt-based timing barrier.

A bus-responder keeps INTR high until the acknowledgement protocol permits its
deassertion; for these experiments keep it through accepted second INTA. Return
99h on the first low lane (ignored) and 40h on the second, with stable data and
READY timing on each; record both. INTR stays low for A/C. READY may hold only
according to the fixture contract; it is a real dependency, not an assumed way
to stall a register-only STI after its opcode has entered execution.

Retain complete traces from reset through final HLT, even if analysis focuses
on a shorter interval. Keep timestamps and original instrument units. A missing
marker is not proof of nonexecution if logging was incomplete. Frame words and
their odd-byte lane splits must be decoded in accepted bus order. Do not reject
unexpected CPU data merely because a simulated sequence differs.

## A — failed IRET releases NMI inhibition?

Configurations: A-ffff, A-fffd, A-fffb and A-9000, each with second-edge,
no-second, and held-high controls (12 configurations).

1. Start at physical reset. After 2002 and the first HLT, raise the first NMI
   with the prescribed pulse. It must make a valid frame on SS:8000 and begin
   the first NMI handler. Except the held-high control, deassert it and maintain
   the required low interval before any next edge.
2. The first handler rewrites vector 2 to 1000:0680 and writes 2040. That accepted
   marker proves handler execution and establishes the trigger while inhibited.
3. For second-edge, deliver **exactly one** second low-to-high transition after
   2040, with verified pulse/deassertion timing before IRET. For no-second, stay
   low. For held-high, hold the original first edge high without another rise.
4. The handler installs SP and jumps to 1000:0640, where CF attempts IRET.
   FFFF faults on the first word, FFFD on the second, FFFB on the third. Values
   for valid preceding reads are initialized. Successful control SP=9000 contains
   IP=0900, CS=1000, FLAGS=0002. Valid #GP and NMI vectors are always installed.
5. Capture the #GP frame, possible nested NMI frame, first handler marker and
   subsequent dump/HLT. Never allow a GP handler IRET before observation.

Under ordered partial-pop effects, failing attempts reach SP=FFFF before entry;
#GP writes FLAGS at FFFD, CS at FFFB, IP=0640 at FFF9. A nested NMI then writes
at FFF7/FFF5/FFF3 and saves GP's 1000:0400 before any GP instruction. All these
words and the 18-byte dump fit in SS; the original first NMI frame at 7FFA is
separate. If a physical part has different partial effects, record them; the
experiment has ample descending space even if a fault prechecks earlier words.

| Observation after fault | Interpretation |
|---|---|
| #GP frame, then second NMI frame saving 1000:0400; 2042 before 2020 | Supports release by the failed attempt before GP-handler execution |
| #GP frame, 2020 and GP dump/HLT; no second NMI despite valid queued edge | Supports continued inhibition through this boundary, subject to controls |
| NMI before the attempted IRET/fault, shutdown, missing first entry, late/invalid pulse | Setup/timing failure or unexpected behavior; retain as inconclusive |

Successful IRET plus second-edge must demonstrate that an ordinary return can
release the queued request; no-second and held-high trials must not fabricate a
second edge. A blocked pending NMI is internal: its existence is inferred from
valid stimulus and controls, never asserted as a directly probed silicon latch.

## B — STI entered with IF=1 and consecutive STI

The tested instruction begins at 1000:0200. No TF is set. IF is established by
POPF before the armed marker and near jump; INTR remains low during setup.

| Configuration | Bytes at 0200 | Marker instruction | Saved IP if marker absent / present |
|---|---|---|---|
| B-if0-sti1 | FB 89 16 10 20 | 0201..0204 | 0201 / 0205 |
| B-if1-sti1 | FB 89 16 10 20 | 0201..0204 | 0201 / 0205 |
| B-if0-sti2 | FB FB 89 16 10 20 | 0202..0205 | 0202 / 0206 |

Raise INTR after the first tested STI has begun, sweeping as described above.
Hold through second INTA. Record the INTR frame, accepted 2010 write (if any),
handler marker 2050 and diagnostic dump. Discard pre-STI trials based on saved
IP/context, not on a code-fetch guess. Late arrivals after marker completion
do not discriminate a shadow.

| Hypothesis | IF=0 single | IF=1 single | IF=0 consecutive |
|---|---|---|---|
| Shadow only on IF 0→1 | marker completed | marker absent if request eligible at end | marker absent if request eligible at second STI end |
| Every STI renews a shadow | marker completed | marker completed | marker completed |
| IF-independent, but a shadow is not renewed inside an existing shadow | marker completed | marker completed | marker absent |

This prediction table assumes a request eligible at the relevant boundary.
For the isolated IF=1 experiment, establish both `INTR rise > STI begin` and
the documented pre-completion recognition margin from measured timing. With
STI's short nominal execution, **that window may not exist** on a given part or
fixture. An all-after-MOV result must then remain inconclusive; it cannot confirm
an unconditional shadow. Prefetch, late INTR synchronization and an actual
shadow can produce the same external outcome.

Consecutive STI gives the request additional time before the second boundary
and tests renewal separately, but a nonrenewing result alone cannot distinguish
transition-only from IF-independent nonrenewing behavior. A different proven
experiment or explicit Intel clarification may still be needed for isolated
old-IF=1. Do not shorten the real recognition requirement to manufacture a pass.

## C — sampled TF and a faulting instruction

C-gp-tf1 sets TF with `PUSH word 0102; POPF` at 01FC..01FF and immediately
executes `89 06 FF FF` at 0200: unprefixed `MOV word [FFFF],AX` using DS=0.
TF was zero during the PUSH/POPF setup. No instruction intervenes before the
target. The intended fault is a word crossing the normal 64 KiB limit, so no
destination byte may be written. #GP saves the target start IP=0200.

Run without NMI first. Preserve live/saved FLAGS images, frame nesting and
actual first-handler writes:

| Observation | Discriminated boundary |
|---|---|
| #GP then #1 frame saving 1000:0400, no 2020 before 2030 | #1 before the first GP-handler instruction |
| #GP, 2020 write, then #1 frame saving 1000:0404 | #1 after the first GP-handler instruction |
| #GP and 2020, GP dump then HLT, no #1 | No #1 observed before explicit TF restoration; positive control required |

A delayed pending trap and live TF in the handler may yield similar IP order
but different saved FLAGS. Retain both; the three interpreter policies are
illustrative mechanisms, not an exhaustive list of silicon possibilities.
Never manufacture target retirement to justify #1.

C-gp-tf1-nmi repeats the same target with a single valid NMI pending during its
execution, using the sweep and raw frames to reject early/late alignment. Capture
the initial #GP/#1/NMI nesting. The NMI handler is terminal, with no IRET, so this
companion measures event ordering before the first executed handler; it **does
not** measure later GP stepping after NMI returns. Infer that later behavior
only from a separately designed/validated experiment. A NMI pulse arriving
during GP entry can mimic one during the target; retain alignment uncertainty.

Controls (each with fresh reset and repeated trials):

- C-gp-tf0: FLAGS=0002 and same FFFF fault, isolating ordinary #GP delivery.
- C-success-tf1: FLAGS=0102 and target FFFE; the word succeeds and ordinary #1
  should save 0204 before the following marker. It validates POPF/TF setup.
- C-gp-restore-tf: same fault, then the GP handler marker, explicit
  `PUSH 0102; POPF; MOV [2022],DX`. If no earlier step occurs, this demonstrates
  a #1 after deliberate TF restoration. Earlier #1 paths terminate separately.
- C-ud-tf1: invalid unprefixed `8F C8` (POP /1), #UD vector 6, independent fault
  class. Results apply to that source; do not generalize #GP to every exception.

## Results, provenance and external action

Use [schema 1](../research/phase6_probes/RESULT_SCHEMA.md), with one unique ID per
repeat/sweep point, exact uploaded image hashes, part identity, reset/hidden
assumptions, actual pin stimuli, original bus export, final memory and measured
dump words. Capture clock units and final-state reconstruction separately.
Physical data stays under `provenance: physical`; synthetic mechanics stays
`simulation`; absent captures stay `not-run`. Missing traces are not passes.
The parser rejects synthetic records when physical evidence is required, but
does not authenticate labels or approve an architectural conclusion.

The smallest remaining external action is to give this source/binary package to
an operator of an identified suitable 286 fixture, integrate the five fixture
requirements above, and return repeat/control traces for A and C plus a
demonstrably discriminating B timing experiment. No purchase, firmware flash or
message to a third party is authorized by this preparation alone. An explicit
Intel 286 correction excluding the competing outcome can replace a capture for
its exact question, subject to independent review and vendor/stepping scope.
