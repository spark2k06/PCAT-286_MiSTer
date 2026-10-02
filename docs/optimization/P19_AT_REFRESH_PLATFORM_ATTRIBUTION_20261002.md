# P19: remaining MiSTer versus reduced 86Box platform cost

Date: 2026-10-02. Status: **PIT channel 1 cadence correction adopted after
directed checks; old-cadence and combined CHECKNUM attribution controls complete;
combined P18/P19 RBF generated; full regression and hardware validation pending**.

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
The original attribution did not alter production. The following correction
is adopted separately; full regression and hardware acceptance remain pending.

## PIT-driven AT refresh correction

The [IBM AT technical reference, September 1985](https://www.minuszerodegrees.net/manuals/IBM_5170_Technical_Reference_6280070_SEP85.pdf)
describes channel 1 OUT as the refresh request source, normally every 15 us.
The old requester waits 32 system clocks after completion: its minimum interval
is 0.64 us at 50 MHz plus service. It is a functional arbitration stimulus,
not the BIOS-programmed AT cadence. Native 86Box's `pit_refresh_timer_at` also
reacts to rising OUT1 by toggling port 61h bit 4; it adds no explicit CPU HOLD
service, so the reduced model still cannot establish exact historical timings.

The new requester samples actual `pit_counter_out[1]`, retaining one pending
event across lock/arbitration delays. Repeated events coalesce while ownership
is occupied. Accepted operations drain even if refresh is disabled. Completion
increments the row exactly once. The machine's port 61h implementation, arbiter,
DMA priorities, CPU HOLD/HLDA, caches and physical KFSDRAM AUTO REFRESH remain
unchanged. No new user configuration switch is introduced.

Directed validation uses the real KF8253, fractional 1,193,182 Hz PIT clock and
BIOS-style channel 1 mode 2 divisor 18. Icarus and Verilator each pass 27 checks:
13 rising edges equal 13 completions, nine measured periods are 752-756 system
clocks (about 15.1 us). Tests include stable high OUT, no unprogrammed periodic
events, deferred grant, pending-event coalescing, disable/drain and global reset.
The requester passes strict Verilator lint. The existing A4 DMA/PIT test passes
both simulators with its original single refresh, DMA data and IRQ checks.

The real CPU machine diagnostic programs channel 1 before its original channel
0 IRQ test. Common and divided CPU clocks both pass A20 aliasing, ROM sinks,
IRQ/IRET, original POST sequence and 14 retained / 14 physically drained writes;
both observe two real PIT refresh transfers. No success assertion is removed.

Two initial test-fixture failures are retained: a missing combinational settle
caused duplicate PIT register acceptance, and a repeating accelerated A4 pulse
violated that fixture's single-refresh premise. The corrected fixtures settle
acceptance before sampling and emit one delayed A4 event. The RTL is unchanged
by these repairs. The user requests an RBF containing this correction and P18,
with 50 MHz timing closure still deferred.

The distributed event diagnostic ROM also initializes channel 1, mode 2,
divisor 18, so future machine-boundary runs test a programmed AT refresh source.
Its ROM/HEX/case/metadata are regenerated and reproducibly checked. Both common
and divided-clock machine fixtures pass with the distributed ROM (12 posts /
12 drains) and the A20/ROM-sink entry variant (14 / 14), preserving all original
POST/IRQ/memory expectations. This is a diagnostic-fixture update, not another
hardware RTL change. The frozen RBF inputs retain their original unused test ROM.

Evidence: [P18 follow-up inventory](../evidence/perf01-posted-write-20261002/README.md),
particularly the immutable `refresh/` group. This extends the missing-ownership
observations already documented in [P12](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).

## First real integer confirmation

The two matched old-policy controls publish stable formatted CHECKNUM integer
values: **6138 without AT requests, 5666 with production's 32-clock requester**.
This is a 7.69% loss and exactly reproduces the user's P17 MiSTer Dhrystone
observation. A read-only two-sample RAM capture identifies the formatter,
owned PID, binary and initial disk; both controls use the same binary,
initial CMOS, disk, configuration and CPU objects. Only AT-refresh enable varies.
Their math tests continue, so this is partial integer evidence, not final
DOS acceptance or a measured gain for the corrected PIT policy.

The exact integer reproduction supplies strong evidence that omitted AT
HOLD/refresh service accounts for the residual P17 integer hardware gap.
It does not establish every peripheral or electrical difference as solved.
The combined P18/PIT candidate is measured separately with actual 86Box PIT
OUT1 driving the corrected RTL; that adapter keeps native SDRAM refresh and
records HOLD/HLDA. Its guest values and peripherals still belong to 86Box.

## Completed old-policy CHECKNUM confirmation

Both matched controls completed CHECKNUM with guest RC0 and `ALL_DONE`.
The strict comparison verifies the same binary, CPU objects/options, initial
disk, CHECKNUM, configuration, initial CMOS and profiler header. AT-request
enable alone differs; native SDRAM refresh remains active in both.

| Same-binary control | Dhrystones/s | K Whetstones/s |
| --- | ---: | ---: |
| AT ownership requests disabled | 6,138 | 113.6 |
| Original 32-clock AT requester enabled | 5,666 | 106.7 |
| User's P17 MiSTer observation | 5,666 | 106.7 |

The old requester reduces rates by 7.69% and 6.07%. Both real benchmark
numbers now reproduce the user's hardware observation exactly. This strengthens
the platform-cost attribution for this workload; it does not establish a
cycle-accurate AT model or solve every peripheral/electrical difference.
Host exit timeouts followed by SIGTERM are explicitly classified separately
from completed guest success. Immutable evidence: `refresh-checknum-complete/` under the
P18/P19 evidence directory; earlier partial receipts remain unchanged.

## Completed combined posted/PIT result

The combined adapter finished with **6906 Dhrystones/s / 121.6K Whetstones/s**,
guest RC0 and `ALL_DONE`. This is +21.89% / +13.96% versus the old requester
with P17 memory, and matches the completed posting-only model's rates. The
PIT cadence's much smaller ownership cost does not change CHECKNUM's rounded
output here. CPU objects/options, initial disk, CHECKNUM, CMOS/configuration
and cache capacities match. Posting and the PIT-driven requester are the
explicit platform changes; profiler-header differences are retained and are
not described as an identical-binary control.

The combined model reaches 89.58% / 91.22% of immediate-memory SPK286 at
7709 / 133.3K. Its physical counterpart still needs MiSTer acceptance, and
50 MHz setup closure remains user-deferred. See the [combined RBF receipt](P18_P19_COMBINED_RBF_20261002.md)
and immutable `combined-checknum-complete/` evidence.
