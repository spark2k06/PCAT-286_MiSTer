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

## Next stages

- M2b: logical Ts/Tc scheduling, physical response capture and delayed
  publication, including cancellation and MAX bypass.
- M2c: qualified first instruction-form metadata and dependency-aware
  duration control in a bounded fixture.
- Full CPU wiring, architectural issue milestones, IU lookahead (P06-IU01),
  event coverage, physical-board calibration and complete FPGA cost/STA
  remain separate gates in the [contract](P06_TIMING_CONTRACT_20261003.md).
