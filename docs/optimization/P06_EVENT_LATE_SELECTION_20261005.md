# P06 execution event budget selection

## Change and reason

The prior critical CPU path starts at operand blocking or BIOS availability,
then crosses event dispatch, instruction timing classification, prefix/budget
arithmetic, deadline comparison and register-write selection. Dispatch is a
live functional permission; feeding it into the timing decoder creates a long
combinational path.

Compute retained instruction metadata and delivery metadata in parallel, then
select their completed qualification, READ-wait policy and clock budget.
Both lanes use the unchanged authoritative instruction table. Delivery entries
are constant event entry names selected by protected mode, so synthesis can
fold this lane. No instruction/event minima are duplicated or retuned. No
state, fabric stage or virtual-clock interval is added. Admission and retained
source budgets remain unchanged.

## Directed validation

| Gate | Result |
| --- | --- |
| Actual metadata expressions, all symbolic inputs | Admission/execution lanes equal during every body |
| Scheduler state and all public outputs | Induction PASS against frozen `d30d476` |
| Wrong execution opcode negative control | Counterexample; rejected |
| Strict generated full CPU lint | PASS |
| Scheduler and full TOP prefix oracles, both simulators | PASS |
| Full CPU handoff, all eight profiles, both simulators | PASS |
| Exact comparison to `3cd8501` qualification | Entire result list identical, including cycles, events, faults, cancellation, HOLD and complete MAX public stream |

The scheduler proof retains its explicit reset/initial-state scope and the
separately discharged metadata-lane equality contract. No stimulus or expected
instruction clock value was changed. Full regression remains **USER_DEFERRED**;
hardware testing is **NOT_RUN**.

In isolated Yosys generic execution-metadata mapping, cell count changes from
1,226 to 1,179, with zero registers in both versions. Dispatch-to-budget generic
depth changes from 30 to 2 gates; dispatch-to-qualification and READ-wait policy
change from 16 to 2. These figures describe the isolated mapped cone. They are
not Cyclone V ALM costs, fitted path delays or a timing closure claim.

The [sealed directed packet](../evidence/p06-event-late-20261005/manifest.json)
includes the unchanged policy table, original builder, current inputs,
generated CPU, proof and negative-control logs, exact baseline comparison,
dual simulator results and generic cost scripts/netlists. Every archived member
was verified byte for byte before deleting owned simulator temporaries.

## Physical acceptance

Fit all enabled features at the existing physical 50 MHz with OPL2 retained.
Measure four-corner global/CPU setup and hold, SDRAM margins, actual physical
ALMs, registers and memory. Retain the existing stricter 0.700 ns palette
minimum-route requirement and confirm its fitted endpoints. Validate palette
hold additionally against the preceding SDC on the same fitted netlist where
possible. No clock, profile divisor or new timing exception is introduced by
this CPU change. A completed fit, rather than generic logic depth, decides its
physical benefit.

## Completed physical result

All-features seed-1 compile at frozen `c38898c` completed in 32:32; detailed
four-corner STA took 4:08. All 1,376 frozen source inputs, the compiled M10K
image, functional receipts and constraint identities are bound in the
[sealed fit packet](../evidence/p06-event-late-fit-20261005/manifest.json).

| Measurement | Deadline CSA | Event selection |
| --- | ---: | ---: |
| Global setup minimum | -10.412 ns | -6.989 ns |
| CPU setup minimum | -10.359 ns | -6.989 ns |
| Global hold under original SDC | +0.041 ns | +0.009 ns |
| CPU hold minimum | +0.121 ns | +0.118 ns |
| Equivalent ALMs | 31,234 | 31,563 |
| Physical placed ALMs | 36,638 | 36,757 |
| Registers | 38,203 | 38,218 |
| M10K / DSP / PLL | 416 / 39 / 3 | 416 / 39 / 3 |

Physical placement occupies 87.70% of the FPGA. No new RTL state was added;
fitted register counts include physical optimization. Recovery/removal minima
are +2.033/+0.327 ns. SDRAM input setup/hold are +5.185/+5.000 ns and output
setup/hold are +2.785/+0.300 ns.

The voluntary 0.700 ns palette routing guard reports -0.099 ns hold. Independent
STA with the exact preceding SDC on the same fitted netlist gives positive
global hold in all four corners, minimum +0.009 ns. All recorded fitted files
and both bitstreams remain byte-identical across that check. Setup remains
open; the critical path now starts at retained instruction entry, crosses the
budget/deadline and the global REP permission into stack/operand/register
selection. The next changes address that combinational dependency.

The archive was read back byte for byte before removing 318,014,818 logical
bytes of owned compiler temporaries. RBF/SOF and reports remain available.
Full regression is **USER_DEFERRED**; hardware testing is **NOT_RUN**.

RBF: `build/p06-event-late-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`
