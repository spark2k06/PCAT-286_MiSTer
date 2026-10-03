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

## Next stages

- M2c: qualified first instruction-form metadata and dependency-aware
  duration control in a bounded fixture.
- Full CPU wiring, architectural issue milestones, IU lookahead (P06-IU01),
  event coverage, physical-board calibration and complete FPGA cost/STA
  remain separate gates in the [contract](P06_TIMING_CONTRACT_20261003.md).
