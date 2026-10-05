# Phase 9 — Historical 80286 timing and bus fidelity

Status: the normalized functional validation gate and global regression passed
at snapshot `5769bd2`. Phase 9 remains open for historical timing evidence,
the remaining policy work and downstream 9F validation. No historical timing
certification or complete Phase 9 release approval is implied. The phase is
deliberately separate from the completed functional milestones, Phase 8 CPU
fixes, and downstream PCAT-286 performance candidates. See the current
[status receipt](PHASE9_CURRENT_STATUS_2026-09-16.md).

## 1. Motivation and current boundary

SPK286 has a functionally validated 80286-oriented CPU architecture with a
six-byte prefetch queue, READY-aware transactions, segmentation/protection,
exceptions where supported, and a normalized BIU interface. The current bus
contract explicitly states that it is not a cycle-accurate implementation of
the physical 80286 pins. The timing model also states that historical timing is
not a requirement of the current functional phase.

The remaining gap is therefore known and intentional:

- instruction timing is not yet calibrated against a selected physical 80286;
- native bus states and their `T1/T2/T3/Tw/T4` relationships are not yet
  reproduced as a validated model;
- prefetch timing and its interaction with execution, data transfers and bus
  ownership are not yet cycle-certified;
- current `Fast`/`Max` behavior removes or avoids implementation delays, but is
  not a claim of a historical 80286 running at a named frequency;
- passing architectural SingleStep cases does not by itself certify timing.

This is a documented limitation, not a request to add arbitrary idle states to
the functional CPU.

## 2. Objectives

Phase 9 shall establish, for explicitly selected profiles and evidence:

1. instruction-level timing classes or budgets where the available evidence
   supports them;
2. BIU bus-cycle sequencing, including request ownership and READY-derived
   wait states;
3. prefetch start, refill, consumption, redirect and starvation behavior;
4. interaction between prefetch, EU data transfers, `LOCK`, `HOLD/HLDA`, INTA,
   reset and cancellation;
5. a clean separation between `Accurate`, `Fast` and `Max` timing policy;
6. reproducible validation artifacts tied to source, tool, profile, ROM/test
   payload and trace hashes.

Phase 9 is not a promise that every undocumented transistor-level detail can be
reconstructed. Each claim must identify its fidelity level and evidence.

## 3. Fidelity levels

| Level | Meaning | Phase 9 requirement |
| --- | --- | --- |
| Architectural | Registers, FLAGS, IP, memory, exceptions and effects | Existing functional baseline; preserve it |
| Instruction timing | Validated instruction latency/classes for a named profile | Add only where measured or documented |
| Bus-cycle timing | Ordered external transactions and READY/ownership timing | Required for the BIU workstream |
| Pin/cycle exact | Clock-by-clock pin trace equality | Only claim for covered hardware traces |

An Accurate profile must not be called complete merely because its divider is
named 6, 8, 10, 12, 16, 20 or 25 MHz. A Fast or Max profile may be useful and
compatible while intentionally not matching historical cycle counts.

## 4. Work packages

### 9A — Timing observation and trace schema

Add counters and trace fields for emulated CPU clocks, BIU busy time, accepted
transfers, READY waits, prefetch requests/responses, queue occupancy,
redirect/cancel events, operand waits and compatibility delays. Distinguish
functional dependency waits from optional historical padding.

The schema shall record source revision, selected timing policy, reset context,
address/status/data/lanes, owner, `LOCK`, `HOLD/HLDA`, READY and relevant T-state
markers. It must support bounded traces and comparison of event relationships,
not only total elapsed cycles.

The first implementation is `rtl/spk286_timing_trace.sv`, connected to the
debug-only `debug_timing_*` outputs of `spk286`. It records 64-bit counters for
CPU clocks, BIU busy cycles, accepted transfers, READY waits, prefetch request
and response activity, queue consumption/emptiness, redirects, cancellation,
operand waits and event requests/completions. The live trace fields expose
address, status, data, byte lanes, owner, `LOCK`, `HOLD/HLDA`, READY, queue
occupancy and a normalized bus phase.

The current policy identifier is `0`, meaning the normalized functional
baseline. The compatibility-delay counter therefore remains zero. The
normalized phase values are `0=idle`, `1=active/READY-wait` and
`2=active/READY-complete`; they are observation markers and are not claims that
the present interface already implements physical `T1/T2/T3/Tw/T4` states.
The capture is reproducible with `make timing-trace`. It runs the deterministic
MOV/XCHG/HLT workload with controlled READY waits and writes a versioned CSV
plus a JSON manifest under `build/timing/`. The manifest records the source
revision, simulator version, timing-policy metadata, reset context, source
hashes for every compiled RTL/generated/support input, trace hash and final
counter summary. Captures require a clean Git tree and verify that those
inputs do not change during compilation. The CSV validator checks all columns,
types, ranges, contiguous pre-edge samples, bus phase fields and counter
relationships before the manifest is written. An external `--build-dir` is
supported; the trace path in the manifest is relative to the manifest itself.
This makes the current 9A observation baseline persistent and comparable
without implying physical T-state accuracy.

The validator also derives the current status/owner mapping and odd-byte lane
rule from the observer, enforces the complete even/odd lane table, rejects
non-zero idle data, bounds counters to their
published 64-bit width and elapsed epoch, limits event/wait increments to one
per sample, preserves READY-wait transaction identity and write data,
requires a pending transaction to remain active until completion, and
enforces zero compatibility delay for policy `0`. Read data may vary before
READY, a bounded trace may end during a wait, and a completed transaction may
be followed by a new identity. These are observer-contract checks, not claims
about undocumented physical bus behavior.

Each CSV row is a sample immediately before a rising edge. Its counters
include edges already executed, while the fields describe the bus inputs for
the edge about to execute. The current schema publishes only valid, non-reset
rows and therefore requires contiguous cycles; an intermediate reset epoch
needs an explicit future schema rule rather than being silently concatenated.
`queue_empty_cycles` measures `execute_enable && queue_count == 0`, i.e.
occupancy, and is not by itself a starvation-demand counter. READY waits,
queue occupancy and operand waits may overlap and are not a partition of total
CPU time.

The focused contract test is `spk286_timing_trace_tb`, run through
`scripts/test_units.sh` in both Icarus and Verilator. It covers reset, idle,
READY waits/completion, code ownership, lane decoding, prefetch/queue events,
redirect/cancel edges and event counters. The persistent capture is a separate
`spk286_timing_capture_tb` workload so the contract test remains small and
tool-friendly. The observer test also covers data writes, odd lanes, INTA
reads, HOLD/HLDA metadata and queue-empty observation. The operand service
exposes `timing_wait` from its effective memory-service state: register forms,
limit checks, cancellation and the response-acceptance cycle are excluded.

The focused validation passed `spk286_core` and `spk286_xchg_hold_lock` in both
simulators, `scripts/lint.sh` and `scripts/synth_check.sh`. The later global
run also passed `scripts/test.sh` and synthesis at snapshot `5769bd2`; its
scope and the expand-down runner policy are recorded in the [current status
receipt](PHASE9_CURRENT_STATUS_2026-09-16.md).

### 9B — Instruction timing calibration

The bounded calibration suite is implemented in
[`PHASE9B_TIMING_CALIBRATION.md`](PHASE9B_TIMING_CALIBRATION.md). It captures
twelve isolated Real-Mode instruction/event classes under the normalized
functional baseline, with immediate READY and deterministic memory, and
records retirement/event-completion intervals plus dependency counters. Its
evidence level is functional observation only: no physical 80286 trace or
historical cycle claim is attached. Native T-state calibration and reference
comparison stay open.

Select a documented 80286 target and a physical reference where possible. Build
small, isolated programs covering register operations, memory operations, odd
words, branches, calls/returns, strings, interrupts and faults. Separate the
EU's intrinsic work from waiting for prefetch, operands, READY and bus ownership.

The output is a set of measured timing classes or budgets, not an opcode list of
unexplained delay constants. Architectural results must remain identical across
timing policies.

### 9C — BIU and native bus-cycle calibration

Model and validate the observable bus sequence for code, data, I/O, INTA,
READY-low waits, odd-word transfers, `LOCK`, `HOLD/HLDA`, reset and cancellation.
Use the normalized boundary only as an intermediate contract; do not claim it
is the physical 80286 pin protocol until the native wrapper and evidence exist.

The first 9C focal increment now checks the real `spk286` capture workload at
the CPU boundary. It validates the complete idle/active metadata relation,
owner/status mapping, the even/odd lane table, READY/phase consistency and
continuity of a pending transaction through completion. Write data is held
stable while waiting; read data is not constrained by this check. The bank
also requires an observed READY-wait completion. This is a normalized BIU
contract check, not a native `T1/T2/T3/Tw/T4` or historical-cycle claim.

The one-outstanding-request implementation may remain an implementation choice
if it reproduces all required observable relationships. It must not be assumed
cycle-exact merely because it has the correct address/data effects.

### 9D — Prefetch and instruction-unit fidelity

Validate the six-byte queue's refill threshold, word/byte fetch selection,
odd-address and control-transfer cases, queue flush, redirect drain and
interaction with EU data requests. Preserve the current rule that a prefetch
does not bypass higher-priority data, locked or ownership operations.

The normalized functional matrix was first recorded at snapshot `8bf7a19` in
[`PHASE9D_PREFETCH_MATRIX_2026-09-15_8bf7a19.md`](PHASE9D_PREFETCH_MATRIX_2026-09-15_8bf7a19.md).
The D1/D2 corrections and HLT resumption are resolved at snapshot `873fed8`
in [`PHASE9D_9E_RESOLUTION_2026-09-15_873fed8.md`](PHASE9D_9E_RESOLUTION_2026-09-15_873fed8.md).
The independent P2 review finding on temporal HLT-resume validation is closed
at snapshot `3b0bb7e` in
[`PHASE9D_P2_RESOLUTION_2026-09-15_3b0bb7e.md`](PHASE9D_P2_RESOLUTION_2026-09-15_3b0bb7e.md).
The regenerated `spk286_prefetch_fidelity` capture derives an independent byte
stream from accepted code-bus transfers and checks linear refill,
empty/partial/full occupancy, starvation, data traffic, odd-address
redirect-under-READY-wait, stale-response invalidation and HLT/NMI resumption
in both Verilator and Icarus. The normalized captures match cycle by cycle for
1,190 rows. These remain functional/dependency checks, not historical
refill-cycle measurements; physical timing evidence remains separate.

`spk286_fetch` covers word/odd-byte fetches, response backpressure, redirect
and cancellation during a wait, restart races and segment limits;
`spk286_prefetch_queue` covers six-byte capacity, ordering, simultaneous
consume/refill, pointer wrap, flush and reset; and `spk286_core` covers the
integrated fetch/queue path, architectural redirects and reset recovery.

If the selected hardware evidence requires a deeper internal instruction queue,
look-ahead or a particular refill timing, specify it separately from the
architectural six-byte storage. Do not add speculative behavior that changes
CS:IP, segment-limit checks, byte order or stale-response handling.

### 9E — Accurate/Fast/Max policy

Implement timing policy as a reusable layer over the functional CPU:

- `Accurate`: only validated historical timing and dependencies;
- `Fast`: remove selected compatibility delays while retaining real BIU and
  READY dependencies;
- `Max`: remove all removable delays allowed by the documented contract and
  FPGA implementation, without claiming a historical clock.

The policy must not alter architectural results, external side effects, bus
ownership or protected-mode checks. Runtime changes require a defined reset or
quiescent-boundary contract.

The first 9E entry increment is recorded in
[`PHASE9E_POLICY_BASELINE_2026-09-15_43eefa1.md`](PHASE9E_POLICY_BASELINE_2026-09-15_43eefa1.md).
The reset-boundary selector is now implemented at snapshot `55b0994` and
documented in
[`PHASE9E_POLICY_BOUNDARY_2026-09-15_55b0994.md`](PHASE9E_POLICY_BOUNDARY_2026-09-15_55b0994.md).
The `spk286_timing_policy_contract` bank verifies in both simulators that the
baseline remains policy `0`, `normalized-functional-baseline`, with no
compatibility delay and unchanged bus/ownership metadata across representative
code, data, INTA, LOCK, HOLD, restart and event observations. The subsequent
9E Max increment accepts policy `2`, `dependency-driven-max`, at the same reset
boundary and proves that its normalized counters and bus/ownership observations
match policy `0` across the focused observation matrix. This is a functional
equivalence result, not a historical cycle-accuracy claim; no removable delay
has yet been identified or inserted in the current implementation.
The capture manifests explicitly set `historical_cycle_accuracy_claim` to
false. The Max functional-equivalence evidence is now recorded separately, but
no Accurate historical profile or historical cycle claim is made. Fast remains
unsupported until it has its own explicit contract and evidence.
The independent P3 adapter-initialization omission is closed at snapshot
`a3c493a` in
[`PHASE9E_P3_RESOLUTION_2026-09-15_a3c493a.md`](PHASE9E_P3_RESOLUTION_2026-09-15_a3c493a.md):
the reset-smoke, state-vector and SingleStep C++ adapters explicitly request
baseline policy `0` before reset. This preserves the selector contract under
randomized Verilator initialization without changing RTL or architectural
behavior.

### 9F — Downstream integration validation

Transfer only the portable CPU changes to PCAT-286 or other consumers. Validate
BIOS, SDRAM, ISA, video, XT-IDE and peripheral behavior separately. A consumer
benchmark may measure useful performance, but it cannot close Phase 9 by itself.

PCAT P01/P02/P03 remain downstream optimizations. P02 may be retained as a
plausible Fast/Max prefetch-chain optimization, but it must not be described as
historical 80286 timing until 9C/9D evidence supports that claim.

## 5. Evidence hierarchy

Use, in order:

1. Intel 80286 hardware and programmer reference documentation;
2. hardware-derived 80286 traces such as SingleStepTests/80286;
3. captured physical 80286 bus/pin traces for questions not covered above;
4. emulator source and established HDL implementations as implementation
   references, never as sole proof of historical timing.

Every timing claim shall state whether it is documented, measured on hardware,
derived from a trace, or an implementation hypothesis.

## 6. Required validation matrix

| Area | Minimum cases |
| --- | --- |
| Prefetch | Linear refill, queue thresholds, odd entry, limit, redirect, HLT |
| EU/BIU overlap | Fast EU, queue starvation, data transfer during refill |
| Memory | Byte/word, odd word, READY waits, ROM/protection, A20 policy |
| Ownership | Data priority, `LOCK`, `HOLD/HLDA`, DMA boundary, cancellation |
| Events | INTR/NMI/INTA, faults, reset, stale-response drain |
| Modes | Real Mode and supported Protected Mode transitions |
| Profiles | Accurate/Fast/Max at each explicitly validated frequency |
| Consumers | BIOS boot and representative PC/AT software on identified RBF |

Run the matrix with a reference configuration and a candidate configuration.
Compare architectural effects first, then transaction order, then timing. A
different timing trace is not automatically a failure in Fast/Max, but it must
be explained and must not violate a real dependency.

## 7. Acceptance criteria

Phase 9 may close only for a named profile and scope when:

- the selected evidence and fidelity level are recorded;
- instruction and BIU timing claims are reproducible from versioned traces;
- READY, ownership, `LOCK`, `HOLD/HLDA`, redirects, reset and cancellation are
  correct under the measured timing policy;
- the six-byte prefetch behavior and its interaction with data transfers are
  validated for the admitted cases;
- Accurate/Fast/Max differences are policy differences, not hidden functional
  divergences;
- no arbitrary idle state, false path or multicycle constraint is used to hide
  a missing timing contract;
- downstream RBF tests identify the exact CPU revision, consumer revision,
  configuration and image hashes;
- uncovered timing behavior remains explicitly marked as unknown rather than
  being promoted to a general 80286 compatibility claim.

## 8. Relationship to current work

Phase 8 functional fixes and downstream P02 can proceed without waiting for
Phase 9. They must preserve the contracts that Phase 9 will measure. P03's
SDRAM buffering and any later video optimization must likewise preserve CPU
transaction order and must not be used to infer historical CPU timing.

The initial Phase 9 dependency inventory is recorded in
[PHASE9_SYSTEM_TIMING_DEPENDENCIES.md](PHASE9_SYSTEM_TIMING_DEPENDENCIES.md).
It is the point-4 handoff for separating mandatory CPU/system dependencies from
optional historical timing before trace instrumentation begins.

The current implementation is therefore suitable for functional development and
Fast/Max performance experiments, but the historical timing question remains an
explicit future phase of SPK286.
