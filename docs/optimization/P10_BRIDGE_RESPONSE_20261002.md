# P10: consume native memory responses at the AT bridge boundary

Date: 2026-10-02. PERF01 candidate. Directed functional and performance
validation is recorded below; fitted timing and hardware acceptance are
separate checks.

The [functional evidence bundle](../evidence/perf01-bridge-response-20261002/README.md)
retains the original logs, manifests and guarded comparison. The
[warm-reset fixture receipt](../evidence/perf01-reset-fixture-20261002/README.md)
records the separate test correction and both real-CPU validations.

## Change

For a retained native RAM/ROM transaction in the common CPU/bus clock domain,
the bridge now returns READY and the lane-selected read data during WAIT,
on the same edge that consumes the accepted backend response. It then enters
IDLE. This removes the former extra COMPLETE cycle. It never recaptures the
old CPU request on its completion edge: the CPU presents its next request
after that edge, and only IDLE can capture it.

Eligibility is captured with the request and limited to valid memory classes
5/6/D at a native memory target. Aligned words and individual low/high bytes
qualify. Split transfers, peripheral cycles, INTA and the divided debug CPU
clock retain the registered response path. Reads still require data-valid,
acceptance still precedes completion, LOCK stays asserted through the sampling
edge, and reset masks the direct response. The data mux depends on retained
request eligibility rather than READY, reducing unnecessary timing dependence.

No CPU RTL, clock frequency, buffer size, SDRAM commands, refresh cadence or
request-entry pipeline changes are part of this optimization. No new production
configuration switch is introduced. The separate
[SDRAM response experiment](P09_SDRAM_RESPONSE_EVALUATION_20261002.md) remains
unselected; its gains cannot be added to these measurements.

## Matched workload measurement

Both independently compiled variants use the production CPU options, physical
SDRAM with periodic refresh, a 512-byte code buffer and a 1 KiB data read buffer.
P03-on is the production setting. P03-off comparisons are retained as controls.

| Directed kernel | Baseline clocks | Candidate clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Dhrystone | 845,438 | 766,800 | 10.255% |
| Whetstone-shaped | 701,469 | 637,333 | 10.063% |
| Working set | 956,222 | 874,906 | 9.294% |
| Dhrystone 2.1 | 917,710 | 834,634 | 9.954% |

These are fixed-work 50 MHz cycle counts, not DOS CheckIT/CHECKNUM scores.
The firmware named `whetstone` is a fixed-point synthetic workload, not the
software floating-point routine in CheckIT. DMA/HPS/IRQ contention is absent
from these kernels; other directed tests cover relevant ownership contracts.

All eight A/B pairs preserve complete GPR/FLAGS, backing-memory hash, retired
instructions, CPU write count and SDRAM write count. Speculative code-fetch
counts may change because the bus becomes available earlier. The comparison
records them without requiring false read-count equality. The comparison tool
also checks unchanged CPU, firmware, configuration and harness inputs and
identical assembled workload ROMs.

The measured return interval falls from one clock to zero. In Dhrystone,
code hits consequently wait two bus clocks instead of three. This is a
20 ns reduction per eligible transfer at 50 MHz; total workload time also
depends on instruction overlap, prefetch and refresh phase.

### Aligning a future DOS comparison with 86Box

For the current 50 MHz MiSTer configuration, the corresponding nominal-clock
reference is the same SPK286 revision and options at 50 MHz in 86Box. The local
86Box Intel 286 CPU table stops at 25 MHz; this is the highest listed profile,
not a limit imposed by the SPK286 simulation. Adding a test profile must retain
the intended ISA/peripheral clock configuration rather than doubling every
clock. No 86Box profile is changed by this bridge milestone.

The local `86Box_dev/src/cpu/spk286_host.c` consumes one configured CPU cycle
per `spk286_model_tick()`. Its backend in `spk286_backend.cpp` drives READY high
and supplies 86Box memory data without the PCAT bridge, code/data buffers and
physical SDRAM latency. Equal nominal clocks therefore give an ideal-memory
CPU reference, not an identical machine. A residual score gap includes these
integration costs; matching their bus behavior would require a separate model.
Keep BIOS, RAM, video, guest image and benchmark configuration matched, and
record the actual CPU backend. The original 86Box C 286 is a separate timing
model. CheckIT's estimated MHz must not be substituted for the configured
clock or used to tune the reference until benchmark scores agree.

## Directed validation

- The same synchronous-consumer response bench passes with baseline and
  candidate bridges, in Icarus and Verilator. Each instance checks 159 cases,
  including the common clock and both phases of the divided CPU clock.
- Strict bridge lint passes in both clock configurations without waivers.
- Reference/P01-P02/production bridge profiles, fetch chaining, arbitration
  and DMA/refresh/PIT tests pass.
- Four deliberate mutations are rejected: omitted data-valid, peripheral
  bypass, unmasked reset response and incorrect upper-byte selection.
- The composed bridge/port/code-buffer/data-buffer cancellation bench passes
  with both bridges: 171 checks, 18 CPU acceptances, 10 CPU responses,
  15 physical-backend completions and one write. It covers hit cancellation,
  prephysical cancellation, coincident/late miss responses, a new fetch while
  an old response drains, and exactly-once accepted writes.

The composed cancellation bench uses a synchronous CPU consumer and controlled
backend. Physical SDRAM and real-CPU reset/interrupt checks are recorded
separately; passing it alone does not establish electrical SDRAM timing.

The existing warm-reset firmware was found to contain a 386 near conditional
jump (`0F 85`) despite targeting a 286. Both original and candidate bridges
reached #UD in that fixture. The fixture correction and stronger checks are a
separate validation change, not a CPU correction.
With the corrected 286 firmware, both bridges pass all five reset boundaries:
IDLE, COMMAND, WAIT, registered COMPLETE and a memory READY response. Each
case requires multiple IRQ0 entries, loop iterations, refresh, code hits and
misses while execution stays in the expected ROM. The candidate has four IRQ
entries and 43–49 loop iterations before reset. Both variants reject the old
firmware under the strengthened checks. These tests use the real CPU, PIC,
PIT, refresh and SDRAM pin model; their path has P03 but no data read buffer.
The separate cancellation bench above covers the complete two-buffer path.

## Build and acceptance

Source baseline: frozen `build/perf01-response-baseline-20261002/work` from
PCAT `b5a7c92` plus the recorded verification-only working tree. Candidate
compile: `build/perf01-bridge-response-fit-20261002/work`.
Bridge SHA-256:
`65480d9dab30c7071bc31751fd475caa795e508c766a71bd89dd57c1f6258cc6`.

Configuration remains 50 MHz, NO_DEBUG, P01/P02/P05/P06/P07 and the RAM read
buffer enabled. The SDRAM owner remains the timing-closed reference version.
The known-good fallback is `build/50mhz-closed-20261002/PCAT-286.rbf`.

### Generated RBF and measured timing

The fresh full compile completed in 29:14 with zero errors and 856 warnings;
the additional detailed STA completed in 3:31 with zero errors and 51 warnings.
Delivered artifact: `build/perf01-bridge-candidate-20261002/PCAT-286.rbf`,
4,097,400 bytes, SHA-256:

```text
3cbcbaaba667c48c4ef28c45f484c61563cee660e9fd21e8267a77cd013a3b7e
```

It is byte-identical to the fresh output under the frozen candidate workspace.
The prior timing-closed RBF is retained unchanged. **This candidate does not
close timing at 50 MHz.** Global measured margins are:

| Corner | Setup | Hold |
| --- | ---: | ---: |
| Slow 100 C | -0.557 ns | +0.189 ns |
| Slow -40 C | -0.301 ns | +0.084 ns |
| Fast 100 C | +2.302 ns | +0.133 ns |
| Fast -40 C | +2.612 ns | +0.087 ns |

CPU-domain Fmax is 48.65 MHz at Slow 100 C and 49.26 MHz at Slow -40 C.
The delivered RBF still runs the configured 50 MHz clock; STA does not lower
that clock. All global hold margins are positive. The conditional external
SDRAM budget and inherited platform/HPS scope remain those of the previous
closure audit; no constraints or exceptions were relaxed for this result.

The worst Slow 100 C path runs from `event_gate_candidate_valid_q` through
operand/stack control to `gpr_q[75]`: 17 logic levels, 19.799 ns data delay,
approximately 70% routing. At Slow -40 C the worst path starts in the
microcode ROM and ends at `gpr_q[64]`. These paths do not traverse the new
bridge response. The bridge-to-CPU group retains +5.439/+5.411 ns in the two
slow corners. HDMI scaled/PLL clock groups also have setup violations.
The failing paths are existing CPU/video logic with changed fitted routing;
this observation does not prove that a future placement alone will fix them.

Equivalent logic uses 28,873 ALMs (69%), physically placed ALMs 34,740 (83%),
and registers 37,171. M10K usage remains 414/553 (75%); DSP/PLL usage is
unchanged. The fitted input identities, complete timing reports and audit
are retained in the [fit evidence](../evidence/perf01-bridge-fit-20261002/README.md).

### User-reported hardware performance

After receiving the candidate, the user supplied CheckIT and CHECKNUM
screenshots from MiSTer. Compared with the previous timing-closed RBF:

| Measurement | Previous | Candidate | Gain |
| --- | ---: | ---: | ---: |
| Dhrystones, both programs | 3946 | 4361 | 10.517% |
| CheckIT Whetstones | 76.7K | 84.1K | 9.648% |
| CHECKNUM Whetstones | 76.7K | 83.7K | 9.126% |

CheckIT still estimates approximately 35 MHz (35.04 versus 35.02 previously),
while the configured CPU clock remains 50 MHz. The observed gains support
the practical value of removing the bridge cycle and agree in magnitude
with the directed simulation. The synthetic fixed-point Whetstone-shaped
kernel and CheckIT math test remain different workloads.

The [hardware evidence](../evidence/perf01-bridge-hardware-20261002/README.md)
retains the unmodified screenshots and provenance limits. The association
with the delivered RBF follows the conversation; its loaded hash was not
independently measured. No new full CPU regression or general software
acceptance is claimed. Preserve this performance result while recovering
positive setup margins before selecting a new timing-closed release.
