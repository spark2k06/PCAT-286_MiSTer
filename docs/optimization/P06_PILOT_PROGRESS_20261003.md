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

- Map the qualified forms to actual decode/start/issue/commit milestones,
  reuse existing retention and validate fetch/redirect/ownership/events.
- Catalogue the full T286REF timer/setup/return wrapper before running that
  DOS program under a historical policy; component results cannot replace it.
- Full CPU wiring, architectural issue milestones, IU lookahead (P06-IU01),
  event coverage, physical-board calibration and complete FPGA cost/STA
  remain separate gates in the [contract](P06_TIMING_CONTRACT_20261003.md).
