# Provisional CPU timing profiles

This CPU-only overlay contains one generated functional CPU variant, its event
controller, a combinational Intel/native instruction table and a small interval
scheduler. It preserves the current SPK286 functional baseline. Select either
`spk286` or `spk286_profiled` in a design; no duplicate execution engine is needed.

## Host interface

The original functional interface remains available. Three new inputs are added:

- `historical_enable`: 0 selects the original MAX behavior; 1 enables the schedule.
- `cpu_boundary`: one fabric-edge pulse for each virtual historical CPU clock.
- `timing_read_wait_event`: a qualified extra external READ wait at that boundary.
  Do not use this input for implementation stalls, WRITE waits or CODE prefetch.

The host retains the fixed fabric clock and supplies virtual clocks without a
new PLL. It must capture physical READY on every fabric edge, retain payload and
ownership, and qualify logical bus completion at the appropriate Ts/Tc boundary.
This package contains no board bus controller, frequency selector or OSD. With an
unqualified fabric-speed bus it validates instruction minima but does not model
the complete historical bus. Stable RAM, I/O, INTA, odd beats and reset/cancel
draining remain responsibilities of the host's existing functional bus contract.

## Implemented temporal contract

Functional microsequencing and protected/event services run on the fabric clock.
Metadata supplies instruction-family budgets; micro-operation counts are never
used as execution clocks. Actual data dependencies must complete before retirement.
The schedule retains the original functional retirement until its deadline and a
virtual CPU boundary, and admits no following opcode/prefix during that interval.
The following head can enter on a fabric edge in the completed boundary's retained
admission window, preserving a two-clock RR interval without an extra tick.

Idle asynchronous event selection remains at fabric speed, including an edge that
coincides with acceptance of an older pending NMI. Original instruction/context
boundary guards still exclude an interior body. Active instruction/REP boundaries,
event budgets and logical bus publication remain qualified by virtual clocks. This
does not claim native pin accuracy or an exact IRQ/NMI recognition phase.

Original software-event, fault, HOLD/LOCK, IRET and shadow semantics remain binding.
An accepted software event preserves its instruction budget through entry;
asynchronous/fault entry starts its own explicit provisional budget. REP checks
use the original functional continuation predicate, setup once and per-iteration
budgets; the final false continuation still retires normally. Count/outcome/ModR/M
metadata is retained from the current instruction rather than inferred from FSM
states. Untaken/taken INTO uses the original OF condition, not a REDIRECT pulse.

Each accepted odd word reference adds two clocks before the BIU splits it. RMW
therefore adds four for odd READ+WRITE. Productive-clock counting freezes on an
extra qualified READ wait, avoiding overflow from arbitrarily long wait debt.
Real backend latency stretches actual dependencies and is not classified as an
external board wait. Internal register/FLAGS/service work may finish before the
visible instruction boundary; this is an interval model, not an exact internal EU
commit-phase model or cycle-accurate pins implementation.

LOCK has no additional execution-clock charge; 0F is an escape. REP setup includes
one REP prefix, and any remaining counted override/repeated prefix uses an estimated
two-clock native fallback. The extra prefix count is retained without a new queue.

Intel instruction timings are the base. Entries requiring missing target length,
protected gate/task classification, prefix fallback or native-only behavior are
explicitly estimated; physical 6/12 MHz measurements anchor later class-sensitive
calibration. Other frequencies remain estimated pending validation. MAX is separate.

## Reproduction and source synchronization

`tools/profile_cpu_baseline.json` pins the complete package-first functional RTL
closure, including the generated microcode. It has no dependency on a PCAT private
receipt. The portable builder uses that baseline and produces exactly the published
profiled TOP/events bytes from PCAT; its generation manifest has standalone paths.
The metadata and scheduler source bytes are also unchanged. The host's interface
adapter, timings, resources and system behavior require their own acceptance.

Run:

```
python3 scripts/build_p06_profile_cpu.py
python3 scripts/check_p06_profile_cpu.py --output build/profile-cpu-focused
```

The focused check verifies deterministic byte identity, strict full-CPU elaboration,
the independent schedule oracle and passive full-TOP LOCK/REP/override aggregation
with Icarus and Verilator. It also checks the unchanged reset/fetch assertions in
both mode settings with Icarus, and the full independent combinational metadata
oracle in two simulators with directed negative/cost checks. It is not an external
SingleStep corpus run or a substitute for board integration/OS acceptance. Keep
the baseline microcode source/generated-contract checks and the full functional CPU
regression, and compare MAX against the original engine before publishing a host.
Do not change historical expected values or flush prefetch to hide fixture timing:
self-modifying fixtures must initialize code before the stream can prefetch it.
