# P06/P12 first public speed-selector candidate

## Objective and release contract

Prepare a newly synthesized PCAT-286 RBF with one OSD choice:
`MAX / 6 / 8 / 10 / 12.5 / 16 / 20 / 25 MHz`.
The first implementation applies the choice through **Reset & apply settings**.
New status bits `77:75` preserve MAX for older configurations. No public
T-state switch, extra CPU PLL or second synthesized CPU is introduced.

All logic keeps the common 50 MHz physical clock. Rational clock enables
describe virtual processor boundaries; peripherals keep their original
PIT, RTC, DMA/refresh, video and audio clocks. Lower nominal CPU speeds do
not relax any 20 ns physical timing requirement.

Historical scheduling is provisional. Intel instruction minima, original
functional dependencies and retained logical bus timing are separate.
Complex forms explicitly marked estimated, target-instruction length,
internal EU milestones and board-specific calibration still need further
qualification. This release must not be described as cycle accurate or as
a completed calibration to every physical 286 motherboard.

The [physical 6/12 MHz anchors](P06_PHYSICAL_REFERENCE_RESULTS_20261004.md)
and native visible-zero/automatic/wait controls remain the basis for
comparison. A global benchmark multiplier is not used. The physical
machine's board identity and actual clocks remain unverified; 86Box's
nominal 12 profile is 12.5 MHz.

## Resource fallback

The first fit starts with the existing feature configuration. If resource
pressure prevents a fit, first set `ENABLE_OPL2=0` in `config.tcl`. Keep the
Adlib/OPL2 implementation and all other configuration choices available.
Measure complete fitted resources against the selected fixed-50 MHz build,
not isolated generic synthesis cell counts.

## M1: selector and retained bus components

The reset-applied generator uses ten register bits: three selector bits,
a six-bit phase accumulator and one parity bit. Its increments are
12/16/20/25/32/40/50 modulo 50. Every second phase is a processor boundary;
MAX supplies a boundary on every fabric edge. This generator alone is not
an instruction timing implementation.

The bridge reuses its existing request, lane and response payload storage.
Historical requests start Ts at a processor boundary, begin Tc on the
following boundary and can finish at the next boundary. Physical READY/data
is captured on the fabric clock, even between virtual boundaries. The
bridge remains occupied, with LOCK retained, until logical publication.
Odd-word halves and the two INTA requests therefore retain their original
functional ownership and sequencing. Actual backend lateness is an
implementation deadline miss, not an inferred motherboard READY wait.

Directed acceptance:

- Generator: 1,512 cases and 2,583,001 checks in each simulator, identical
  dual traces and summaries; 64 reset-applied transitions, randomized
  frequency windows, eight four-state cases and four rejected mutants.
- Bridge: 1,512 transfers, 8,745 checks, 2,016 accepted/captured physical
  beats and 1,512 logical publications in each simulator. CODE, READ, WRITE,
  split targets, odd lanes, INTA, LOCK and backend latencies 0 through 20
  are exercised for every profile, including MAX.
- Existing bridge response tests pass in both simulators.
- Yosys proves every original bridge output and matching original state
  equivalent to the immutable selected build in MAX for both completion
  modes. A changed READY negative control fails. No protocol assumptions
  or output masks are used.

Generator-only synthesis reports 114 generic cells / 10 register bits.
These are not FPGA ALMs and exclude the CPU schedule and complete project.

M1 qualifies components only. Production OSD/CPU integration, broader
functional validation and a new fit/RBF are subsequent milestones of this
same objective.
