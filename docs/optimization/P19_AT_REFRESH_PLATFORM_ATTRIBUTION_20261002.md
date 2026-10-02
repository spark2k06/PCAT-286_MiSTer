# P19: remaining MiSTer versus reduced 86Box platform cost

Date: 2026-10-02. Status: **private physical-data attribution passes; matched
real CHECKNUM refresh controls running; production refresh policy unchanged**.

The user requested investigation of modules missing from the PCAT timing
adapter while P18's real math benchmark continues. Compare matching P17
implementations before extrapolating P18's still-unmeasured hardware result.

| P17 observation | Dhrystones | K Whetstones |
| --- | ---: | ---: |
| Reduced PCAT timing path in 86Box | 6138 | 113.6 |
| User's MiSTer CheckIT/CHECKNUM result | 5666 | 106.7 |
| MiSTer relative throughput loss | 7.69% | 6.07% |

These are single observations. The same application, CPU options and capacities
support attribution, but no repeated hardware distribution is available.

## Concrete model omissions

The production top supplies `execute_enable=1` and the ordinary CPU clock is
`CLK_50M`; the debug divide-by-two option is disabled. OSD speed is passed to
gameport selection, not a hidden CPU execution-enable throttle.

The reduced adapter already executes the production bridge, port, code/data
buffers and KFSDRAM owner/controller. It includes the controller's own automatic
refresh. Moving KFSDRAM again cannot reproduce the missing board-side owners.

Production `spk286_at_machine` additionally instantiates `spk286_at_refresh`
and `spk286_at_arbiter`, connects HOLD to the CPU and waits for HLDA, bridge
drain, unlocked ownership and response completion. The default AT request
interval is **32 system clocks** (0.64 us at 50 MHz) plus pending/service time.
This is a request cadence, not a claim of 1.5625 million completed refreshes
per second. The SDRAM owner's AT-refresh record waits for KFSDRAM idle; native
physical refresh remains independently enabled at its existing 100/400-clock
settings. This board HOLD/arbitration cost was absent from the reduced adapter.

Other omitted mechanisms remain hypotheses:

- PCAT PIT/PIC and INTA latency; 86Box currently supplies peripheral behavior
  and immediate host-served completion outside the selected RAM/BIOS path.
- Active DMA, disk/audio drivers and HPS loader ownership. Their activity during
  the benchmark needs measurement; source availability does not prove traffic.
- EGA accesses. EGA has its BRAM frontend; the production RAM controller is not
  indiscriminately shared with raster scanout. CPU video/I/O and interrupt cost
  can still differ, particularly around the application and timer handlers.
- BIOS, PIT programming, load segment and repetition variation. Guest time
  and instruction counts must be compared, not host emulation speed percentages.

The fitted clock's negative setup slack does not lower the configured 50 MHz
frequency. Hardware correctness at that setting remains separate from this
reproducible logical service-cost investigation; closure is user-deferred.

## Bounded physical-data experiment

`probe_at_refresh_cost.py` freezes the already measured P17 and P18 arms and
adds the **production** refresh requester, arbiter and CPU HOLD/HLDA path.
The CPU memory request is qualified by the CPU grant just as in the machine.
The controller's own refresh is enabled in every control. Only AT-request
enable varies. Cache capacity, CPU RTL/options, controller timing and firmware
are identical. There are no interrupts, DMA, loader or video in these kernels.

| Fixed-work kernel | P17 no AT / with AT clocks | P17 loss | P18 no AT / with AT clocks | P18 loss |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone-shaped | 669236 / 742579 | 9.88% | 579701 / 651539 | 11.03% |
| Fixed-point math | 560222 / 607372 | 7.76% | 490802 / 543734 | 9.73% |
| Working set | 658054 / 708934 | 7.18% | 576767 / 641423 | 10.08% |
| Dhrystone 2.1 | 720397 / 792464 | 9.09% | 636510 / 707228 | 10.00% |

All eight pairs match GPRs, FLAGS, backing-memory hashes, retired instructions,
architectural and physical store counts, consumed instruction bytes and
redirects. Real physical SDRAM data is used. These are clock measurements,
not CHECKNUM rates; the fixed-point kernel does not reproduce software floats.

The first probe rejected a one-instruction difference in math retirement counts.
The original HLT/physical-idle stop could precede final HLT retirement in one
arm: stages 1-4 and consumed bytes were equal, but stage 5 differed by one.
The revised stop waits for the actual F4 retirement pulse in **both** controls.
No signature/count equality is waived. Original logs are retained in the build;
the successful frozen fixture and complete comparison are committed as evidence.

The 7-10% P17 directed losses are of the same size as the residual hardware
gap. This identifies a plausible substantial contributor. It does not yet
prove the real CHECKNUM percentage or justify changing the refresh cadence.

## Real application adapter and next attribution

`build_at_refresh_probe.py` builds a separate executable from the validated
P17 physical fixture, unchanged 86Box CPU objects, production AT requester and
arbiter. It exposes HOLD/HLDA counts and refresh completions. The same binary,
profiler, disk and calibrated CMOS run with explicit `--at-refresh 0/1` controls.
CPU values and host peripheral behavior still belong to 86Box; this remains
a partial platform model. The runtime switch exists only in the diagnostic
adapter; no new hardware configuration option is added.

The private build is `build/perf01-at-refresh-86box-20261002`. Its two fresh
arms are `pcat-control` and `pcat-at-refresh`; CPU/disk/profile identities and
the runtime control are recorded. Notify the integer result first. Then compare
complete guest output, phase work and HOLD costs. Port PIT/PIC or another owner
only if a remaining difference or trace supplies evidence for it.

Do not disable native SDRAM refresh or adopt the 32-clock cadence as historical
AT timing on the basis of throughput alone. A cadence correction needs the
board's intended refresh semantics, device-visible behavior and directed tests.
No production change, full regression, synthesis/fitter or hardware acceptance
is claimed for this investigation.

Evidence: [P18 follow-up inventory](../evidence/perf01-posted-write-20261002/README.md),
particularly the immutable `refresh/` group. This extends the missing-ownership
observations already documented in [P12](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).
