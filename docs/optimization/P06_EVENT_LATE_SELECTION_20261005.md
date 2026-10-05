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
