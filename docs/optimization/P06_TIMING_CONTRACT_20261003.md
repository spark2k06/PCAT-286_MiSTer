# P06/P12: fixed-50 MHz timing contract and 6 MHz pilot

Date: 2026-10-03. Status: **design contract and directed acceptance plan**.
Historical CPU integration is `NOT_IMPLEMENTED`; physical 6/12 MHz is
`NOT_MEASURED`. References and their limitations are in the
[Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md).
This advances the reference/design portion of
[P06-M1](P06_TIMING_REFERENCE_PLAN_20261003.md); it does not close physical M1.
Unwired component implementation and its directed evidence are tracked in
[the pilot progress](P06_PILOT_PROGRESS_20261003.md).

## 1. Product and pilot boundary

Use one functional SPK286 engine with a separate historical timing policy.
Retain the existing accelerated MAX path and the common physical **50 MHz**
for CPU, bridge and SDRAM. The first development candidate is a **6 MHz Real
Mode pilot**, qualified by instruction form and event coverage. It must not
be presented as a complete historically timed CPU.

The future Intel-family speed list remains 6, 8, 10, 12.5, 16, 20, 25 MHz,
plus MAX. What a selected nominal speed means with historical timing disabled
is still an OSD/product decision before implementation. This document does
not silently choose a new user-facing switch or policy encoding.

Current internal policy 0 and policy 2 have the same dependency-driven
schedule; policy selection is reset locked. `execute_enable` also selects
native execution versus external verifier control. Reusing it as a global
clock divider would not pause the BIU, fetch responses or all state changes.

## 2. Time units and rational clock proposal

| Quantity | Meaning | Pilot value |
| --- | --- | --- |
| `fabric_cycle` | Existing physical clock edge; hardware capture/service | 20 ns / 50 MHz |
| `cpu_clock` | Intel table unit and duration of one Ts/Tc state | 1/6 MHz = 166.666... ns |
| `cpu_phase` | One of the two CLK periods per processor clock | 1/12 MHz = 83.333... ns |
| `board_ready_at` | Board's qualified response/extra-wait availability | Independent of intrinsic opcode clocks |
| `physical_capture_at` | Actual retained backend result, fabric timestamp | Measured, not inferred from virtual frequency |

Proposed 6 MHz generator: on each fabric edge add 6 to a phase accumulator
modulo 25. On carry, emit one phase event; emit one processor-clock boundary
on every second phase event. Reset accumulator and phase parity together.
For an initial phase of zero, phase boundaries occur at fabric edge
`ceil(25*n/6)` and CPU boundaries at `ceil(25*n/3)`.

Thus every 25 fabric cycles emits six phase events and three CPU boundaries;
processor intervals repeat **9, 8, 8** physical cycles. Their mean is exactly
6 MHz relative to the assumed 50 MHz fabric clock. A boundary is less than
one fabric cycle late relative to its ideal rational deadline, with no
accumulated drift. This is 20 ns quantization, not matching the electrical
edges of an independent oscillator. Oscillator tolerance remains separate.

The accumulator needs only five bits for this pilot, with a suitably widened
sum and one phase-parity bit. This is an algorithmic size observation, not a
whole-design FPGA cost estimate. Generalize only after the pilot. Historical
profiles up to 25 MHz require at most one 2x-CLK phase event per fabric edge;
MAX bypasses imposed historical timing and is not a claim of a 50 MHz Intel
processor using a 100 MHz external CLK.

No new clock domain or PLL is proposed. These events are synchronous enables.
PIT/RTC, video/audio, SDRAM refresh and board arbitration keep their actual
time bases while CPU progress is limited.

## 3. Capture and publication are separate events

The following event names describe the proposed contract, **not existing
ports**. Their implementation must reuse existing retained records where
possible and be reviewed against the source hashes in the manifest.

| Milestone | Rule |
| --- | --- |
| `logical_request` | CPU timing policy permits the operation; retain type, owner, address, lanes, data and cancellation context |
| `physical_accept` | Backend accepts one command on a fabric edge; never repeat it while waiting for a CPU milestone |
| `physical_capture` | Capture valid completion/read data on any fabric edge; draining cannot depend on a CPU enable |
| `logical_bus_complete` | At a permitted Tc boundary, board timing allows completion and the retained physical result exists |
| `queue_publish` | Publish retained fetch bytes to the six-byte CPU queue at their logical completion, with space and matching stream |
| `operand_publish` | Make retained read data available to its requesting instruction once the logical cycle completes |
| `write_slot_accept` | Retain one historical CPU write when its qualified instruction milestone permits it |
| `architectural_commit` | Publish GPR/FLAGS/IP and other architectural updates only at qualified milestones with dependencies satisfied |
| `event_boundary` | Recognize events at the allowed architectural boundary; preserve existing shadows, locks and restart semantics |

An early physical result is retained until its logical publication. READY may
be a one-fabric-cycle pulse and must not be lost between virtual ticks. A late
result blocks publication; it can never be replaced by stale data or a
fabricated ready indication. Capture and consume on the same edge require an
explicit bypass rule or next-boundary publication, with directed evidence.

The existing fetch and BIU already contain retained response slots. The
bridge's current direct-memory completion consumes READY immediately; its
STATE_COMPLETE path also advances on physical edges. Neither is a persistent
virtual-response protocol. The former /2 debug `COMPLETE_ON_CPU_SAMPLE` path
aligns a related clock and is not this new rational scheduler.

Prefer a single retention point per outstanding logical beat and gate its
publication; do not add a second speculative response queue by default.
Where capture advances the physical service state, retain the logical
owner/record independently until publication. Otherwise a next request could
steal the old response or HOLD could observe the bus as free too soon.

## 4. Logical bus, board waits and implementation misses

For a qualified ordinary transfer, use one Ts followed by one or more Tc
states. Sample completion at the end of Tc. Each reference-permitted extra
wait repeats Tc; zero-wait back-to-back transfers may start the next Ts
immediately. These are processor clocks, not 50 MHz cycles.

The native READY pin is **low to complete / high to wait**. Existing normalized
`ready=1` denotes acceptance/completion. The adapter must explicitly translate
the concepts, not invert the current handshake globally. Historical bus state
records are separate from current normalized trace phases 0/1/2.

Two tests decide whether a Tc boundary can complete:

1. The identified board policy permits completion at that boundary.
2. The implementation has a valid retained result for that operation.

If (1) is false, record an external/reference wait. If (1) is true but (2) is
false, record `deadline_miss` and an implementation extension. Both conditions
can overlap; count mutually exclusive intervals plus their union, not their
sum. Extending a bus cycle safely is preferable to corrupting data, but any
implementation extension fails the claimed historical timing for that case.
Never relabel SDRAM/cache service latency as a physical-board wait to obtain
a passing score.

The zero/one/two-extra-wait fixture used in directed simulation is an explicit
**abstract board fixture**, not the collaborator's unknown board. Native
86Box uses 2/3/4 service costs at the corresponding selections; those integer
charges do not reproduce a READY waveform. Record both models separately.

Preserve address/lane/type stability for an accepted beat. The next address
may be previewed in the preceding phase as Intel specifies, but command
acceptance and current response association remain distinct. Proving this
address pipelining requires a phase trace, not a lower aggregate elapsed time.
Do not increase backend outstanding capacity simply to implement preview.

An odd word consists of two ordered byte transfers; grant no intervening HOLD
between its halves. LOCK also prevents a grant. Historical Th requires the
documented Ti transition and physical/posted-write drain before ownership is
transferred. The current functional BIU grant is not already proof of those
historical transitions. DMA, refresh and loader continue independently, with
their real arbitration recorded as board activity.

## 5. EU/BIU overlap and prefetch limits

The Intel instruction clocks constrain the instruction schedule under the
stated operand conditions. They are not a generic delay added after executing
the complete instruction, nor a separate EU budget plus every bus clock.
Required data, queue bytes and architectural dependencies remain mandatory.
Scheduling memory/queue work in parallel is necessary to model overlap.

The metadata key must include opcode form, addressing/alignment, mode,
prefixes and taken outcome where applicable. For the first kernel set:

- Distinguish register/register 2 from register/immediate 3 clocks.
- Distinguish A1 read 5, A3 write 3, and arithmetic-memory 7 clocks.
- Distinguish LOOP 8/4, JNE not-taken 3, and JE/JMP 7 with the applicable
  target-length note. Record target instruction length before applying it.
- Model read waits on the actual read references; do not add every write or
  fetch wait to the EU budget when that work can overlap.

Intel's aggregate table does not specify every internal read/write issue
phase. **No invented intermediate phase is certified here.** A metadata row
must identify which milestones are sourced, inferred or unvalidated. Directed
CPU/bus traces and physical elapsed measurements constrain those inferences.
Until then, a row may validate minimum duration and functional ordering but
cannot claim exact intra-instruction bus timing.

Keep the six-byte logical prefetch queue. A completed physical cache-line fill
is backend capacity, not extra bytes available to the CPU. Reserve capacity
for every outstanding logical fetch; queue occupancy plus reserved bytes
must not exceed six. Prefetch fills are normally words; the first odd-target
fetch is a byte. Redirect/HALT inhibits the old stream. A redirect invalidates
its queued and retained bytes, while an accepted physical transaction drains
exactly once and its result is discarded. Use existing cancellation state if
it suffices; an epoch in a trace does not require a wide hardware epoch counter.

This six-byte limit excludes instructions already consumed by the decoder.
Intel separately specifies three decoded-instruction entries (hardware 3-3 /
PDF 53). Current SPK286 has a single active instruction context and dispatch
waits for an inactive microsequencer; it does not implement that lookahead.
Record this as **P06-IU01: decoded-instruction pipeline coverage**. A six-byte
queue plus an instruction-duration counter is therefore insufficient by
itself to claim a complete physical prefetch/decoder model. The initial
fixture must expose that limitation and distinguish decoder backpressure
from memory waits. Evaluate a simulation-only model before proposing any
storage or pipeline change; current pilot resource constraints remain intact.

Data wins over a new prefetch, without preempting a started fetch. The Intel
two-clock prefetch inhibition needs a qualified EU demand point; adding
priority when a late functional request appears is insufficient. Scheduling
that demand point is an explicit acceptance item.

Intel permits one pending CPU write. The existing PCAT posted slot is below
coherent caches and can finish physically before or after the CPU's logical
write milestone. Capacity, visibility, ordering, LOCK, cancellation and drain
must be accounted for without accidentally granting two historical write
slots. A second write or a dependent read must wait/forward only as the
declared model permits. Do not equate a downstream early acknowledgment with
historical EU completion or permit an I/O side effect before its bus command.

## 6. Directed acceptance matrix, prepared for the pilot

These are required whole-pilot checks. Component portions executed so far are
identified in [the progress and evidence](P06_PILOT_PROGRESS_20261003.md),
**not whole-CPU pilot results**. Retain a fabric
timestamp and phase/state timeline, plus architectural and byte scoreboards.
Use simulation observers for wide counters; synthesizable timing control
should not inherit a bank of 64-bit trace registers.

| ID | Directed case | Required observation |
| --- | --- | --- |
| C01 | Generator reset, at least 250,000 fabric edges | Exact phase/CPU counts; 9/8/8 CPU intervals; rational boundary error <20 ns; deterministic reset phase |
| C02 | Result arrives at every fabric offset before/during/after Tc sample | Exactly one physical capture and one logical completion; no early publish; correct sample-edge rule |
| C03 | One-edge READY pulse, prolonged consume backpressure, identical successive commands | Retained data survives all gaps; no stale response or command replay |
| C04 | Explicit board waits 0/1/2; independent early/late backend response | Ts/Tc counts, external waits and implementation misses separately classified |
| C05 | Prefetch occupancy 0 through 6, word/byte fills, consume and separate decoded lookahead | Reservations fit within six prefetch bytes; decoded entries accounted separately; expose P06-IU01 decoder stalls; data outranks only unstarted fetch |
| C06 | JE/JMP target instruction lengths 1/2/3/6, even/odd target, LOOP exit | Intel form costs and target-length rule qualified without counting the same refill twice |
| C07 | Register immediate versus register/register; direct disp16 versus base+index+disp; even/odd operands | Correct metadata selection and additional actual byte transfers; unchanged results/defined FLAGS |
| C08 | Read, write and memory RMW with variable waits | Read/write reference counts and EU/BIU overlap; no blanket fetch+EU+memory summation |
| C09 | First posted write, second write, same-address read, code invalidation, locked write | One historical write capacity; visibility and drain order; no early architectural/I/O effect |
| C10 | Redirect/reset/cancel before accept, during wait and at capture/publication | No old-stream publication; accepted writes retain the existing CPU-reset drain contract; no replay |
| C11 | HOLD during Ts/Tc, odd-word second half and LOCK; simultaneous DMA/refresh | Correct owner/priority, Ti/Th sequence and draining; no pause of independent masters |
| C12 | IRQ/NMI at completion boundaries; STI/SS shadow, HLT, INTA | Existing functional semantics and safe acknowledgment retained; historical event timings only where qualified |
| C13 | Frozen R0/B0/M0 plus full timer/setup/return metadata | All 42 samples/six summaries and existing signatures; gross/baseline preserved; timer qualification unchanged |
| C14 | CPU throttled while PIT/RTC/video/audio/refresh run | Identified device cadence unchanged; CPU throughput reduction cannot freeze peripherals |
| C15 | MAX with policy bypass, same deterministic input | Existing architectural/traffic behavior; no unconditional timing stage or MAX latency penalty |
| C16 | Complete fit with baseline constraints and selected seed | Resource delta and all four STA corners, physical 20 ns paths, CDC/SDRAM scope preserved |

For C02, a concrete starting example is a bus request allowed at CPU boundary
t0, followed by Ts and Tc. If board wait=0 and a response was captured during
Ts, publication waits until the end of Tc, t0+2 CPU clocks. Board wait=1 moves
the first permitted completion to t0+3. If the backend misses that permitted
boundary, increment `deadline_miss` and extend Tc. A capture on the permitted
edge must follow the selected same-edge rule; never silently treat it as an
extra external board wait.

C12 preserves functional event behavior while checking integration. It does
not extend the pilot's historical coverage to complete IRQ/NMI/PM/REP timing.
Before booting the full DOS program under the pilot, catalogue every opcode
in the measured wrapper as well as the kernel. Unsupported temporal metadata
must be reported explicitly, not silently use native 86Box or zero-clock
defaults. A stand-alone kernel fixture may qualify a family earlier.

## 7. FPGA baseline and acceptance gates

Baseline source milestone: **b14e54b**, selected fixed50 admission/retained-FDC
seed 1 fit. The
[selection receipt](../evidence/fixed50-timing-20261003/admission-retained-fdc-selection.json)
binds its inputs and RBF; [P21](P21_FIXED50_TIMING_20261003.md) explains scope.

| Metric | Baseline |
| --- | ---: |
| Placed ALMs | 35,698 / 41,910 (85.18%) |
| Equivalent ALMs | 29,993 |
| Registers | 38,119 |
| M10K | 416 / 553 |
| RAM bits | 3,301,019 |
| DSP / PLL | 39 / 3 |
| Worst global setup / minimum global hold | -0.022 ns / +0.073 ns |

The baseline is **not globally timing closed**. CPU/HDMI margins are positive
in all four models; the remaining cold setup failure is the ROM-loaded to
instruction-buffer-valid path. A slow virtual profile does not repair this
physical timing violation or authorize a multicycle exception.

Measure a complete candidate with identical tools, device, seed, CDC/SDC
selection, source scope and coverage. Report placed and equivalent ALMs, FF,
M10K/RAM, DSP/PLL and each corner's setup/hold, including MAX. Inspect mapping
and fitter replication separately. No numerical ALM cost is promised before
synthesis. Design constraints are one shared scheduler, no extra CPU/PLL,
unchanged cache/queue capacities and simulation-only detailed observers.
Any new storage must be explained and measured. A measured cost and MAX
impact require acceptance before adopting production RTL.

## 8. Work order and remaining gates

1. **Complete now:** source/byte extraction, Intel/native differences, this
   capture/publication contract, directed cases and current resource baseline.
2. **Next bounded proposal:** implement a simulation-only 6 MHz scheduling
   fixture, qualify milestone assumptions and wrapper opcode coverage; perform
   C01-C15 incrementally before any production OSD or profile release.
3. **Physical/reference acceptance:** ingest unchanged T286REF results from
   the collaborator at actual nominal 6 and 12 MHz, identify board/CPU/BIOS and
   timer/wait assumptions, investigate disagreements with discriminating cases.
   The ordinary native 12.5 MHz control remains a distinct frequency.
4. **Production pilot adoption:** measured FPGA cost, MAX equivalence, P21
   timing acceptance and the declared physical/reference scope. Only then
   consider other speeds and broader instruction/event coverage.

The collaborator's results are not required to finish this contract or to
build a clearly provisional simulation fixture. They are required before
claiming the physical accuracy promised by M1. No scalar benchmark fitting
can substitute for the missing board/bus evidence.
