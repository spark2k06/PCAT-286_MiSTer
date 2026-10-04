# P06: provisional timing implementation progress

Date: 2026-10-03. The components are in `rtl/spk286_timing_pilot`, outside the
production QIP. They are staged CPU-only policy work, not a second execution
engine. Current fixed50 production CPU/bridge/SDRAM sources match the preceding
reference manifest. Historical CPU integration and physical 6/12 MHz validation
remain pending. No new RBF or whole-CPU timing profile is delivered here.

## M2a: 6 MHz clock enables

`p06_clock` implements the specified 6/25 phase accumulator and phase parity.
At 50 MHz it emits 12 MHz phase events and 6 MHz processor boundaries, with
the required 9/8/8 fabric-edge pattern and sub-edge rational quantization.
The nominal frequency is relative to the actual fabric oscillator.

Directed RTL checks cover 250,000 consecutive edges, yielding exactly
60,000 phase events and 30,000 CPU boundaries, then reset/restart at all 25
phase offsets. There are 256,550 checked non-reset edges. Both simulators
use an independent integer-frequency oracle, verify the error bound and check
the statically elaborated MAX form on every edge. MAX advances on each fabric
edge with no historical phase claim. A mutated accumulator step must fail.

Strict Verilator RTL lint passes. Generic Yosys synthesis reports six state
bits and 44 cells for the historical clock component, versus zero state bits
and one reset inverter for its MAX form. These are generic synthesis figures,
**not placed FPGA resources or timing margins**. The component is not in the
production hardware, whose measured P21 baseline therefore remains unchanged.

Frozen receipts/logs are in
[`docs/evidence/p06-pilot-20261003/clock`](../evidence/p06-pilot-20261003/clock).
This covers C01 and the clock-component portion of C15. It does not establish
EU/BIU scheduling, whole-CPU MAX equivalence or the other directed cases.

## M2b: retained one-beat bus fixture

`p06_bus_cycle` accepts a packet at a virtual boundary, retains its address,
lanes, class, write data and LOCK indication, then submits it exactly once.
Physical completion can be captured at any fabric edge. Logical completion
requires an eligible Tc boundary, abstract board permission and the result.
Same-edge capture/publication has an explicit data bypass. A held logical
reply retains its data until consumption. Consecutive packets can share the
old completion/new Ts boundary, including identical commands.

Both simulators pass 759 counted scenarios / 33,404 fabric ticks, plus
published/eligible-boundary cancellation, joint reset/stale completion,
duplicate-completion detection and all 64 MAX control combinations. The sweep
covers all 25 capture offsets, acceptance delays 0..4, response delays 0..24,
board waits 0/1/2 and consume backpressure. A response delayed 80 edges is
classified as nine implementation deadline misses, not nine board waits.
The negative control removing the boundary guard fails for early completion.

Selected fabric-edge traces:

| Scenario | Request | Physical accept | Capture | Logical completion | Board waits | Implementation misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Early, zero waits | 9 | 10 | 10 | 25 | 0 | 0 |
| Early, one wait | 9 | 10 | 10 | 34 | 1 | 0 |
| Early, two waits | 9 | 10 | 10 | 42 | 2 | 0 |
| Capture on eligible edge | 9 | 14 | 25 | 25 | 0 | 0 |
| Late implementation result | 9 | 14 | 94 | 100 | 0 | 9 |

Strict RTL lint passes. Generic synthesis of this **standalone fixture** is
165 cells / 72 register bits; MAX is six cells / zero registers. Of the 72
bits, 48 retain the request, 16 retain the response and eight are control.
This is **not an additional CPU buffer or a production cost estimate**: the
integration must reuse current BIU/fetch/bridge retention wherever possible.
The component is an unwired handshake reference, not a replacement bridge.
Its packet interface needs a qualified admission shim for the existing
level-held CPU request. Global reset assumes a joint backend reset; CPU-only
cancellation drains accepted read/write work and drops its logical response.

Evidence: [`bus`](../evidence/p06-pilot-20261003/bus). This qualifies component
parts of C02/C03/C04/C10/C15, not complete CPU coverage. LOCK is retained but
HOLD/odd-word arbitration, prefetch reservation, decoded lookahead, posted
write visibility and architectural event scheduling remain unimplemented.

## M2c: first form metadata and minimum-duration fixture

`p06_instruction_duration` starts a minimum duration **at instruction start**,
in parallel with functional work. It does not insert a delay after execution.
The existing functional owner would retain results; permission to retire is
conditional on functional completion, dependencies and an eligible boundary.
An actual read-wait event increases the retained budget by one. No blanket
sum of bus clocks, fetch/write waits and instruction clocks is applied.

Already-decoded form IDs (these are not opcode encodings):

| ID | Qualified form | Base processor clocks | Intel programmer PDF page |
| --- | --- | ---: | ---: |
| 0 / 1 / 2 | ADD / XOR / CMP register-register | 2 | 227 / 324 / 241 |
| 3 / 4 | ADD / XOR register-immediate | 3 | 227 / 324 |
| 5 | Jcc | 3 not taken; 7 + next executed instruction bytes when taken | 262 |
| 6 | JMP short | 7 + next executed instruction bytes | 264 |
| 7 | LOOP | 8 taken / 4 exit; no added target-length note | 278 |
| 8 / 9 | A1 moffs16 read / A3 moffs16 write | 5 / 3 | 281 |
| 10 | ADD register from memory | 7 | 227 |
| 11 | XOR memory-immediate RMW | 7 | 324 |

Qualification is restricted to Real Mode, no prefixes and those forms.
Conditional outcomes must be known. A taken Jcc/JMP requires a known next
instruction length of 1..6 bytes in this pilot. Direct A1/A3 reject a complex
EA. Arithmetic memory forms accept an explicitly identified
base+index+displacement correction (+1). Physically odd word operands add +2
per operand reference (+4 for RMW's read and write), under B-6 / PDF 214.
All other form/mode/prefix combinations are explicitly rejected; no zero-cost
fallback is installed. Target metadata and issue/commit milestones still need
an integration contract with the actual decoder/functional engine.

Both simulators check 16,448 metadata combinations/cases and 64 duration cases,
including branch target lengths, LOOP outcomes, register/immediate distinction,
odd/complex-EA corrections, zero/one/two read waits, independent functional/data
dependencies, consumer backpressure, cancellation and consecutive instructions.
Separate cases reject off-boundary or write-class wait events. The 8-bit budget
is a **bounded fixture**: overflow is explicit and blocks retirement. Elapsed
time saturates without wrapping across long dependency stalls. All 64 MAX
control combinations bypass timing. A 3-to-2 register-immediate mutation fails.

The coupled fixture checks 72 aligned memory scenarios using the real new
clock/bus/duration components together. Abstract board waits are 0/1/2, accept
delays 0/4 and physical response delays 0/13/80 fabric edges. Captured data is
poisoned outside the one-edge response. Read/write/RMW traffic and mock-memory
effects are counted; a late result prevents retirement. A mutation ignoring
dependencies fails while the read is still pending.

Selected coupled results, **not CPU benchmark measurements**:

| Form | Board waits per beat | Physical delay | Table minimum + read waits | Observed duration, processor clocks |
| --- | ---: | ---: | ---: | ---: |
| A1 read | 0 | 0 | 5 | 5 |
| A1 read | 2 | 0 | 5 + 2 | 7 |
| ADD register from memory | 0 | 0 | 7 | 7 |
| XOR RMW | 0 | 0 | 7 | 7, two commands / one write |
| XOR RMW | 2 | 0 | 7 + 2 | 9, two commands / one write |
| XOR RMW | 0 | 80 | 7 | 20, waiting for both logical responses |

This caller **mocks functional work as ready**, with response dependencies.
Data issue at instruction start is an unvalidated fixture assumption. The
write/RMW fixture waits for final bus publication conservatively: it does not
model the historical one-entry CPU write buffer or establish its overlap.
There is no prefetch/decoder model, actual odd-word split, GPR/FLAGS engine,
interrupt semantics or full T286REF wrapper here. The initial coupled-test
failure was classified as a test-adapter race: its pre-edge observer altered
the caller count before sampling, temporarily counting one read twice. The
caller now updates its own publication state on clock edges; production CPU
RTL and expected metadata/results were not changed to address it.

Strict lint and generic synthesis pass. The isolated duration component maps
to 19 register bits and about 300 generic cells (the receipts identify exact
source scope and mapping; the coupled stage still synthesizes only this named
component). MAX maps to zero register bits / three cells. These figures are
**not ALMs, full CPU cost or timing margins**. No additional functional engine,
production queue, cache, PLL or timing constraint is added.

Evidence: [`duration`](../evidence/p06-pilot-20261003/duration) and
[`fixture`](../evidence/p06-pilot-20261003/fixture). M2c covers parts of
C06/C07/C08/C15 only. It does not close those whole-CPU cases, C13, historical
CPU integration or physical M1. The final component acceptance reruns clock
and bus too; prior frozen receipts remain unchanged.

## Next stages

The [M3 full CPU register pilot](P06_CORE_REGISTER_PILOT_20261004.md) now
records real dispatch, byte consumption, retained operands, architectural
writes and retirement. M3a observes 208 cases. M3b connects the real CPU's
retained register paths to 6 MHz virtual start/commit in a private source
selection: all 208 cases meet 2/3-clock minima, with late dependencies,
cancellation, scope stops and consecutive instructions tested separately.
MAX per-edge traces remain identical to production. Generic control cost is
22 bits / 284 cells; MAX control disappears. BIU/IU timing and physical
calibration are still open, including the measured dispatch gap in P06-IU01.

The [M4 private CODE/fetch connection](P06_CORE_FETCH_PILOT_20261004.md) now
reuses the real response slot for capture at any fabric edge and publication
at qualified Ts/Tc boundaries. It validates 297 queue/fetch scenarios, 208
warm exact register minima, 208 cold functional cases, lifecycle and explicit
unsupported bus guards. MAX remains equivalent, including a sequential fetch
proof. Isolated fetch cost is +4 FF / +95 generic cells; full FPGA cost is
unmeasured. Data/INTA/HOLD/LOCK and IU/event timing remain open. Complete initial
development against 86Box while physical calibration is pending, as authorized
on 2026-10-04; retain explicit Intel/native differences.

- Map the qualified forms to actual decode/start/issue/commit milestones,
  reuse existing retention and validate fetch/redirect/ownership/events.
- Catalogue the full T286REF timer/setup/return wrapper before running that
  DOS program under a historical policy; component results cannot replace it.
- Full CPU wiring, architectural issue milestones, IU lookahead (P06-IU01),
  event coverage, physical-board calibration and complete FPGA cost/STA
  remain separate gates in the [contract](P06_TIMING_CONTRACT_20261003.md).

## 2026-10-04 pause checkpoint: M5 register handoff

The [private M5 pilot](P06_CORE_IU_HANDOFF_20261004.md) removes M4's additional
virtual dispatch clock for qualified register/immediate streams. All 688
paired first handoffs save one processor clock; 1,448 instructions retain
independent architectural results, with 760 same-edge retire/start events.
Cold/late bytes, 15 lifecycle/event/scope modes, MAX compatibility, strict lint,
microcode consistency and three MAX component equivalence proofs pass.
Three isolated affected components add 47 generic cells and zero register bits;
this excludes top/executor qualification and is not a complete FPGA delta.
M3/M4 frozen evidence remains valid. Full decoded lookahead, bus/event and speed
integration remain open. Work is **paused at the user's request**; no new
development, fit or regression starts until the user resumes.

## 2026-10-04 resumed: M6a isolated real BIU READ

The user resumed work after the M5 pause. The [M6a component milestone](P06_CORE_DATA_READ_PILOT_20261004.md)
now qualifies byte/aligned-word READ timing through the real BIU and operand
service, with CODE disabled. It reuses the existing response storage and
captures READY on every fabric edge while publishing only at qualified Ts/Tc.
The independent 432-case matrix, 33 lifecycle cases and 42 scope guards pass
both simulators; MAX unit/full CPU compatibility and BIU sequential
equivalence pass. A specific early-publication mutant is rejected.

The net isolated restricted BIU delta is +2 register bits / +54 generic cells,
including static pruning of unqualified CODE/ACK/HOLD/LOCK services. It is not
the complete timed BIU or FPGA cost. Shared CODE/DATA logical ownership and
full CPU memory issue/commit remain the next gate; odd words, writes, I/O,
events, decoded IU lookahead and full speed/machine integration are still
open. Production, the selected RBF and the previous frozen evidence are
unchanged. Only directed acceptance was run, not a total regression or fit.

## 2026-10-04 M6b: shared CODE/READ logical ownership

The [M6b component milestone](P06_CORE_SHARED_BUS_PILOT_20261004.md) combines
real fetch/queue, operand and BIU. Existing owner registers retain CODE or DATA
through logical Tc after an early physical READY. All 972 transition cases
require opposite-class issue on the completing Tc; paused result consumers do
not retain the bus. Eligible unaccepted DATA has priority, while held accepted
requests and occupied result slots do not block CODE falsely.

Both simulators pass 1,087 cases: 972 transitions, 8 queue/consumer/metadata
stress cases and 107 cancel/reset/scope cases. Independent mandatory-grant,
physical-presence, cursor, result, queue and owner oracles pass; two distinct
mutants fail their required assertions. Eight affected MAX unit benches and
208 full-CPU MAX cases pass, with original/private edge traces equal. Both
MAX component sequential proofs keep private inputs arbitrary and generic
netlists establish that those controls have no MAX cone.

The isolated timed mappings are BIU 540 cells/78 register bits and fetch
605/102, with original/MAX 504/88 and 508/98. Static pruning of unsupported
services prevents treating these net deltas as full CPU or FPGA overhead.
M3/M4/M5/M6a frozen audits pass. Production, config and selected RBF are
unchanged; no complete regression or Quartus fit was run.

Next is private full-CPU aligned READ issue/result/architectural commit.
Consecutive DATA reuse, odd words, writes/write-buffer overlap, I/O, events,
EU-demand lookahead and full speed/machine integration remain open.

## 2026-10-04 M6c: aligned A1 READ in a real full CPU

The [M6c private CPU milestone](P06_CORE_MEMORY_CPU_PILOT_20261004.md)
connects actual prefix-free Real Mode `MOV AX,[moffs16]` to the shared
CODE/READ bus, retained TMP0, qualified AX commit and retirement. The accepted
instruction uses an aligned word; the minimum is five processor clocks plus
actual extra READ waits, with real fetch/physical dependency extensions.
It does not certify exact Intel issue phasing or a complete historical profile.

Both simulators pass 534 aligned warm/cold and 1,248 directed cases, with
48 byte-identical CPU trace pairs and seven required negative failures.
267 memory and 208 register MAX traces match the original CPU; eleven MAX
unit benches pass. 688 M5 register streams/1,448 instructions preserve their
warm and cold traces exactly. Strict full CPU lint, microcode consistency,
BIU/fetch MAX sequential proofs and all five ancestral evidence audits pass.

The original functional TMP0/MOVE phase supplies pending readiness and
payload; no new result buffer or register bank is introduced. The new
executor pending/retire assignments map to eleven generic cells and zero
register bits. The READ-wait export adds six generic BIU cells over M6b,
without registers. These isolated measurements exclude complete top-level
qualification and are not Quartus ALMs or full FPGA overhead.

Production, config and selected RBF remain unchanged. There is no full
regression, fit or new RBF. Next qualify the remaining memory services and
their actual instruction issue/results: consecutive DATA reuse, odd words,
writes/write-buffer overlap and read/modify/write. Branches, bus/events,
decoded IU lookahead, the DOS wrapper, complete public speeds and physical
collaborator calibration remain open.

## 2026-10-04 M6d: consecutive aligned A1 READ qualification

The [M6d evidence milestone](P06_CORE_READ_STREAM_20261004.md) qualifies the
existing M6c CPU with 240 consecutive-read programs (two, four or eight A1
instructions), 1,120 instructions in each warm/cold matrix, and targeted
pause/cancel/reset/HOLD and full-sequence recovery checks. Original/private
MAX traces remain identical. All 23 dual trace pairs, three independent
negative controls, lint and microcode checks pass; the frozen audit reconstructs
the exact M6c RTL and checks 825 timed programs/3,794 retirements.

This milestone adds zero hardware. The existing serialized DATA handoff is
preserved, not claimed as an Intel-required issue gap. Odd words, writes/RMW,
bus/events, decoded lookahead and complete public profiles remain open.
Production config, RBF and source selection remain unchanged. No total
regression, fit or STA was run.

## 2026-10-04 M6e: private full-CPU odd-word A1

The [M6e private CPU milestone](P06_CORE_ODD_READ_CPU_PILOT_20261004.md) adds
two-beat odd A1 READs using original first-byte/raw-word storage and TMP0.
DATA ownership spans both logical cycles; the first READY cannot publish or
release, and the second physical request starts after first Tc. Alignment
adds two clocks through a separate event, while each READ half contributes
its own actual waits. The minimum is five plus two plus READ waits; real
dependencies still apply. Native Intel pin/issue phase accuracy is not claimed.

Both simulators pass 2,143 timed cases and 43 identical trace pairs. Original
and private MAX each pass 834 caller cases; frozen aligned A1 and consecutive
warm/cold traces are preserved. Eight independent mutations are rejected.
Four affected MAX units, strict CPU lint, microcode consistency, BIU MAX and
aligned equivalence, duration equivalence and control-cone checks pass.

The isolated BIU/duration increment is 30 generic cells/four register bits;
no new payload buffer, queue capacity or PLL is introduced. This excludes
full top/CPU/FPGA cost. Cancel drains accepted halves; reset aborts the original
backend, while invalid HOLD scope remains stopped until reset. These are
distinct acceptance contracts, not a claim of complete historical HOLD service.

Production, config and selected RBF remain unchanged. No total regression,
Quartus fit or STA was run. Next qualify writes/write-buffer overlap and RMW,
then branches/events, decoded lookahead, DOS wrapper and complete public
speeds. Physical collaborator calibration remains pending without blocking
the provisional reference-based development.

## 2026-10-04 M6f: private serialized A3 WRITE

The [M6f private CPU milestone](P06_CORE_WRITE_CPU_PILOT_20261004.md) qualifies
aligned and two-beat odd A3 using the original address/payload and operand
response. END retains functional completion after final Tc; retirement waits
for the qualified boundary and three/five-clock minimum. Odd alignment has
its own eligibility bit. WRITE waits remain real bus dependencies and do not
increment the EU budget as READ waits.

Both simulators pass 2,227 timed cases and 47 identical trace pairs, original
and private MAX each pass 834 WRITE vectors, and the M6e warm/cold READ matrix
remains byte-identical. Eight mutations, four affected MAX units, microcode,
strict lint, bypass proofs and private-input cone checks pass. The isolated
BIU/duration increment is 13 generic cells and one control bit, with no new
payload buffer, queue capacity or PLL; this is not complete FPGA ALM cost.

Cancellation drains accepted writes without reverting their physical effects.
Reset interrupts the original backend and may leave an already written low
byte; the fixture checks this partial word explicitly. Historical single
write-buffer EU overlap, consecutive WRITE/following READ, RMW, events and
complete public speeds remain separate gates. Production config, source
selection and selected RBF remain unchanged; no total regression, fit or STA.

## 2026-10-04 M6g: private bounded XOR word RMW

The [M6g private CPU milestone](P06_CORE_RMW_CPU_PILOT_20261004.md) qualifies
prefix-free Real Mode `81 36 disp16 imm16`, retaining the original effective
address, READ into TMP0, immediate into TMP1, ALU/TMP2, physical WRITE and
COMMIT_FLAGS dependency. FLAGS and retirement share the first qualified
boundary after actual WRITE disposition; no early ALU-result retirement.

The original retained ModR/M identifies the memory form after admission.
Its first CPU boundary adds four once to the existing three-clock RI budget,
without another register. Odd READ and WRITE each add two; only READ waits
charge the EU. Actual serialized dependencies produce earliest eight/twelve
clocks, so the seven/eleven-clock minimum is not binding in those cases.
No claim of exact Intel issue phases or write-buffer EU overlap is made.

Both simulators pass 2,503 timed cases and 67 identical trace pairs. Each
original/private MAX CPU passes 858 RMW cases; the frozen warm/cold A1, A3
and 688-program register-stream references remain byte-identical. Nine
specific mutations, four affected MAX units, strict lint, microcode,
component bypass proofs and private-input cone checks pass. Formal executor
coverage is the extracted real commit fragment, not the whole executor/CPU.

The measured isolated increase is twenty generic cells and zero register
bits, with an unchanged BIU and no new payload, queue capacity or PLL.
Full top/CPU/FPGA resources, fit and STA are outside this milestone.
Cancellation preserves accepted WRITE effects while suppressing FLAGS;
reset can leave a partial word. Historical HOLD, consecutive WRITE/following
READ, write-buffer overlap, branches/events, decoded lookahead, DOS wrapper
and complete public speeds remain separate gates. Production config,
source selection and selected RBF are unchanged. No total regression was run.
