# Phase 9 — System timing dependency register

Status: Phase 9 point 4 baseline. This document identifies timing dependencies
that software and the downstream PC/AT system can observe or impose. It does
not add historical delay states and does not claim native 80286 pin timing.

## 1. Purpose and boundary

The first timing task is to distinguish dependencies that are required for
correct execution from delays that are only needed for historical compatibility.
The former must remain present in every timing policy. The latter may be
controlled by `Accurate`, `Fast` or `Max` after they have been measured and
specified.

SPK286 owns the CPU-side portion of this register: the execution engine,
prefetch unit, BIU, READY/HOLD/LOCK handling, events and reset/cancellation.
Memory, chipset and peripheral timing remain consumer-owned and are recorded
as integration contracts rather than implemented here.

## 2. CPU-side dependencies already present

| Dependency | Observable condition | Policy | Current evidence | Historical timing still open |
| --- | --- | --- | --- | --- |
| Instruction fetch availability | EU waits for queue data or an accepted fetch response | All modes | `spk286_fetch`, six-byte queue and directed fetch tests | Native T-state placement and refill latency |
| READY-qualified bus completion | Active code/data/INTA transaction holds its identity and waits for `READY` | All modes | BIU lifecycle tests and bus contract | T1/T2/T3/Tw/T4 pin sequence |
| BIU ownership | Data, INTA, locked or held transactions retain ownership until their legal boundary | All modes | arbitration, LOCK/HOLD and event lifecycle tests | Exact ownership transition clocks |
| Odd-word transfer | Word access is split into ordered physical lane transfers | All modes | odd-word and byte-lane tests | Inter-transfer historical timing |
| Data response backpressure | Consumer cannot retire an operation before its response is accepted | All modes | operand/BIU lifecycle tests | Any compatibility delay after response |
| Prefetch starvation | EU cannot consume bytes that are not in the queue | All modes | queue starvation and redirect tests | Hardware refill threshold and overlap timing |
| Redirect and stale response drain | Redirect/reset cancels or drains in-flight work before the new stream is consumed | All modes | redirect/reset lifecycle tests | Exact cancellation and restart clocks |
| `LOCK` and `HOLD/HLDA` | Locked chains and bus ownership cannot be split by HOLD | All modes | event/BIU lifecycle tests | Native pin-level arbitration timing |
| INTA/event sequencing | Interrupt acknowledge and event frame operations wait for their required bus transactions | All modes | event lifecycle and INTA vector sweep | Physical INTA bus states and lead times |
| Reset | Reset aborts transient work and restarts the architectural fetch path | All modes | reset smoke and lifecycle tests | Historical reset release timing |

These dependencies are functional contracts, not optional idle cycles. Removing
one to improve throughput would change the CPU's observable behavior and is not
an admissible `Fast` or `Max` optimization.

## 3. Downstream PC/AT dependencies

The following dependencies belong to the PCAT consumer but can affect CPU
observations through the CPU boundary:

| Consumer dependency | CPU-visible effect | Required Phase 9 observation |
| --- | --- | --- |
| Memory/SDRAM response latency | READY wait duration and prefetch/data overlap | Record READY-low spans by request owner and transaction type |
| ROM/BIOS wait policy | Reset fetch and BIOS instruction throughput | Compare reset/BIOS traces with the identified RBF and ROM hashes |
| PIC/interrupt acknowledge | INTR assertion and INTA response timing | Record assertion-to-acknowledge ordering and vector delivery |
| DMA or other bus master | HOLD/HLDA ownership and CPU stalls | Record ownership hand-off and locked-cycle exclusion |
| ISA/XT-IDE/video access latency | I/O/data READY waits and software-visible throughput | Separate peripheral wait time from CPU compatibility delay |
| Peripheral clocks | PIT/RTC/serial/video event rates | Keep peripheral clocks independent from CPU timing policy |
| Reset and mode selection | Initial timing profile and queue state | Apply timing selection only at reset or a quiescent boundary |

These are integration test inputs, not reasons to move PCAT logic into SPK286.
The eventual consumer tests must identify the exact CPU revision, consumer
revision, configuration and image hashes.

## 4. Candidate software workloads

The workloads below are dependency probes, not timing oracles by themselves:

1. reset and first-fetch smoke;
2. BIOS POST and memory-test path;
3. SuperSoft protected-mode diagnostic;
4. DOS boot and representative disk/I/O access;
5. interrupt-heavy and DMA-active PC/AT activity;
6. HLT, redirect, fault and reset recovery cases.

For each workload, the record must separate architectural result, bus/event
ordering and elapsed timing. A workload passing in 86Box or a PCAT RBF does not
by itself prove historical cycle fidelity.

## 5. Dependency classification for timing policies

| Class | Accurate | Fast | Max |
| --- | --- | --- | --- |
| Architectural/READY/ownership dependency | Preserve | Preserve | Preserve |
| Queue correctness and redirect drain | Preserve | Preserve | Preserve |
| Validated historical instruction latency | Apply for named profile | May remove if classified compatibility-only | Remove if safely removable |
| Historical bus/prefetch padding | Apply only with evidence | Selectively retain | Remove when no real dependency is bypassed |
| Peripheral clock rate | Consumer-defined | Consumer-defined | Consumer-defined |

No profile is considered cycle-accurate merely because its clock divider or
benchmark rate matches a historical frequency.

## 6. Current dependency-to-observation matrix

The following matrix ties the current RTL conditions to concrete observation
fields and directed tests. It is an instrumentation map, not a claim that the
listed behavior has historical T-state placement.

| RTL dependency/condition | Entry/exit observation | Trace field or counter | Directed evidence |
| --- | --- | --- | --- |
| `spk286_biu` active transaction | `bus_valid` asserted until READY-qualified acceptance | `phase`, `owner`, `address`, `status`, `ready`, `biu_busy_cycles`, `accepted_transfers`, `ready_wait_cycles` | `spk286_timing_trace_tb`, `spk286_timing_capture_tb`, BIU lifecycle tests |
| Code fetch (`bus_status == 4'hD`) | fetch ownership and lane identity remain stable during READY wait | `owner=code`, address/status/data/lanes, phase 1/2 | timing trace contract and fetch lifecycle tests |
| Data/INTA ownership | data or acknowledge owner is visible independently of code fetch | `owner=data/ack`, write/data/lane fields | timing trace contract; data and event lifecycle tests |
| Effective operand memory service | wait begins when a valid memory request lacks BIU admission or an accepted request lacks response; ends on acceptance/response | `operand_wait_cycles` from `spk286_operand.timing_wait` | `spk286_operand_service_tb`, `spk286_operand_byte_tb`, timing capture |
| Register operand service | local completion is not classified as memory wait | `operand_wait_cycles` unchanged | operand service local REG cases |
| Queue occupancy | execution enabled while queue count is zero | `queue_count`, `queue_empty_cycles` | timing trace contract and prefetch/queue tests; not a starvation-demand claim |
| Redirect/cancel edge | stream restart and semantic cancellation are edge-counted | `redirects`, `cancels` | timing trace contract and redirect/reset lifecycle tests |
| `LOCK` and HOLD/HLDA | lock/ownership exclusion and hand-off metadata are sampled with bus activity | `lock`, `hold`, `hlda`, owner/phase | timing trace contract and `spk286_xchg_hold_lock` |
| Event request/completion | internal event edges are counted | `event_requests`, `event_completes` | timing trace contract and event lifecycle tests |
| INTR/NMI assertion to acknowledge | external assertion is not currently timestamped at the observation boundary | not yet represented; do not infer from internal event counters | pending Phase 9 event-boundary instrumentation; event lifecycle tests cover function |
| Reset epoch | reset clears counters and suppresses valid rows | `reset`, `trace_valid`, schema policy | observer reset test; intermediate-reset capture contract remains pending |

The counters intentionally overlap: a READY wait can occur while an operand
is waiting, and a queue-empty cycle can overlap either condition. Future
timing profiles must preserve these dependency relationships even if they
remove compatibility-only delay.

## 7. Point 4 completion criteria

Point 4 is complete when:

- every CPU-side wait in the current RTL is classified as a real dependency or
  an explicitly identified compatibility delay;
- every consumer-side timing input has a named CPU-boundary observation;
- the software workload list is tied to reproducible ROM/RBF/configuration
  identities where applicable;
- the open historical questions are listed without inventing delay constants;
- the next Phase 9A trace fields can be derived directly from this register.

The next implementation milestone is Phase 9A: bounded timing/event tracing.
