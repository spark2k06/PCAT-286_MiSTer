# Hardware follow-ups retained after the OS/2 EGA fix

Date: 2026-09-30. Baseline: PCAT `e80b52a`, 86Box `2a94fd669`.

The user accepted OS/2 startup on MiSTer after the EGA corrections. See
[the EGA integration and acceptance record](PCAT_EGA_86BOX_INTEGRATION_20260930.md).
This document preserves useful observations from the earlier investigation
and separates open findings from that resolved boot failure.

## PERF01 — MiSTer CPU and machine benchmark throughput

2026-10-02 update: [real CHECKNUM memory-control attribution](optimization/P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md)
now records 4804 / 88.6K with production PCAT READY timing in 86Box, against
7709 / 133.3K with immediate READY on the same CPU. Actual code-buffer hit rates
are approximately 79.41% / 84.18%, much lower than the synthetic kernel. The
[4 KiB synchronous-tag instruction candidate](optimization/P13_CODE_BUFFER_4K_20261002.md),
commit `0399806`, has passed directed coherence/cancellation checks and was
measured separately with the 1 KiB data buffer retained. FPGA timing and hardware
acceptance remain separate from this attribution and implementation evidence.

The user subsequently reports 4911 / 94.4K in CHECKNUM on the 4 KiB candidate:
+12.612% / +12.784% against P10. The completed fit grows to 32,609 equivalent
ALMs, 38,741 physically placed ALMs and 44,251 registers. Its code-buffer tags
map to registers, making RAM-inference cost reduction the next requested step.
The screenshots, fitted comparison and provenance limits are retained in P13.

[P14](optimization/P14_CODE_BUFFER_RAM_MAPPING_20261002.md) now maps the tags
to M10K while preserving 4 KiB capacity and directed cycle-visible responses.
Full-project synthesis registers fall from 42,403 to 35,680; estimated ALMs
needed fall from 34,101 to 31,317. These are map counts, not placed occupancy.
The subsequent user fit reduces placed ALMs from 38,741 (92%) to 36,043 (86%),
equivalent ALMs from 32,609 (78%) to 30,552 (73%) and registers from 44,251 to
37,733, with one additional M10K. Hardware retains 4911 Dhrystones. CheckIT
remains 95.1K Whetstones; CHECKNUM reports 99.1K versus 94.4K before, without
an established cause for the math variation. CPU/system 50 MHz setup/hold is
positive in all four models. HDMI setup -0.104 ns at Slow -40 C still prevents
whole-design closure. The user retains P14 and explicitly defers HDMI while
prioritizing PERF01 throughput.

The frozen P13 private CHECKNUM repeat has now completed at 5390 / 101.4K
with PCAT memory-control timing, up 12.20% / 14.45% over the old-capacity
4804 / 88.6K control. [P15](optimization/P15_DATA_BUFFER_ASSOCIATIVITY_PLAN_20261002.md)
records the completed guest/host-teardown qualification and the rationale for a
same-capacity 1 KiB two-way data buffer. On the accepted candidate traffic,
its shadow reduces data-read misses from 378,345 to 420 in Dhrystone and from
1,931,287 to 190,075 in Whetstone. Those shadow estimates alone do not establish
a measured implementation gain.

The user has subsequently authorized P15. Its 1 KiB two-way data buffer is
implemented and has passed directed coherence/replacement/hit-latency checks,
both memory-port/code/data pipeline capacities and isolated M10K inference.
The pre-build frozen full fit has finished: +35 net equivalent ALMs, +85
placement ALMs, +289 registers, no additional M10Ks (416/553 total). Its data
entity adds 342.8 equivalent ALMs; other fitted logic compensates most of this
in whole-design totals. CPU 50 MHz has -0.194 ns setup in slow 100 C, with
positive hold; deferred HDMI has -0.188 ns setup in slow -40 C. CPU timing
closure remains a follow-up; P15 must not be described as fully closed.

The user tested the exact candidate RBF at maximum CPU speed. CheckIT reports
5023 / 95.6K and CHECKNUM 5023 / 96.4K: both improve integer by 2.28% over 4911.
Math is inconclusive across the separate observations; no repeated sample set
or full compatibility regression is established. The private unchanged
CHECKNUM has completed RC0/ALL_DONE/final profile at **5525 / 102.4K**, versus
5390 / 101.4K (+2.50% / +0.99%). Its retained identities include matched CPU
objects; actual data miss counts match the two-way shadow exactly in both
function phases. Host teardown required the classified SIGTERM after guest
completion. See P15 and its retained evidence for exact identities/limitations.

The user next authorized a write-path experiment measured in 86Box before
synthesis. A private owner prototype overlaps ordinary write admission/launch,
retaining physical completion and unchanged KFSDRAM commands/recovery. Directed
physical byte/address scoreboards pass in Icarus and Verilator (22 writes/20
reads in each variant), and private-adapter smoke reduces writes from 7 to 6
wait clocks while preserving two-clock hits. [P16](optimization/P16_WRITE_ADMISSION_PROTOTYPE_20261002.md)
has now completed unchanged CHECKNUM RC0/ALL_DONE/final profile at
**5666 / 102.9K (+2.55% / +0.49%)** versus P15's 5525 / 102.4K. Identical CPU
objects/configuration/image/CMOS were verified; host monitor teardown required
the classified SIGTERM after guest completion. The user requested an RBF after
the early integer result. Commit `95f5b21` promotes the write-admission owner,
with bounded physical burst/byte/refresh and composed cancellation checks PASS.
Its 50 MHz observer-free full fit completed from 1205 unchanged frozen inputs:
**+465 net equivalent ALMs, +314 placed ALMs, +149 registers, no extra M10Ks**.
The owner including KFSDRAM itself adds 11.2 ALMs; much of the net change comes
from physical synthesis of unchanged logic. CPU setup is -0.450 ns / -0.029 ns
in the slow models, with positive hold in all four; this fit has positive HDMI
setup/hold. The RBF is available under `build/perf01-write-admission-fit-20261002/`.
The user subsequently reports **5139 / 97.1K in both CheckIT and CHECKNUM**:
integer +2.31% over P15, math +1.57% / +0.73% respectively. The report follows
delivery of the P16 RBF; loaded hash/OSD setting were not separately captured.
Screenshots and provenance are retained in P16. Repeated hardware measurements,
broad compatibility and CPU closure remain pending; no full regression.

The requested deeper throughput review is retained in
[P17](optimization/P17_MEMORY_PATH_THROUGHPUT_REVIEW_20261002.md). P16's real
integer phase already has code/data hit rates above 99.98%; the next private
prototype overlaps bridge/port capture with backend command acceptance,
reducing common hits from two wait clocks to one at unchanged cache capacity.
Four fixed-work physical-data kernels gain **9.46–11.40%** with unchanged
GPR/FLAGS/memory/retired/write signatures. Strict bridge/port lint and bounded
ownership/cancellation checks pass. Complete real CHECKNUM now gives
**6138 / 113.6K (+8.33% / +10.40% versus P16 5666 / 102.9K)**, with guest
RC0/ALL_DONE and final profile. Entry overlap is integrated after directed
common/divided-clock, machine A20/ROM-sink and external-writer checks. Further
ideal-write controls show 13.31–15.74% extra scope on
those kernels after entry overlap, requiring an explicit posting/coherence/
drain specification rather than assuming that ideal service is implementable.
Open-row SDRAM is another unmeasured possibility; bounded write-address
locality is not controller row-hit evidence. CPU RTL/options, cache capacity
and SDRAM timings/refresh are unchanged. The subsequent user build and MiSTer
screenshots give **5666 / 106.7K**, agreeing between CheckIT and CHECKNUM:
**+10.25% / +9.89%** over the hardware P16 observation. Fitted total is 30,832
equivalent ALMs (74%), 36,191 placed ALMs (86.35%), 38,198 registers and 416
M10Ks. Bridge/port local cost is +13.8 equivalent ALMs with no additional RAM;
global logic/placement counts fall by 220/251, partly through changed packing.
CPU setup remains negative at **-0.979 / -0.958 ns** in the slow corners
(reported minimum Fmax **47.67 MHz**), with positive hold in all four models.
The worst setup path is unchanged CPU prefetch -> event error-code decode,
with 20 logic levels; cache reset/admission controls also have setup violations.
Video hold reaches -0.074 ns and HDMI PLL source setup -0.034 ns. The hardware
gain supports retaining P17, but does not establish 50 MHz closure or broad
compatibility. User reports, screenshot provenance and a private fitted-path
extraction are preserved in P17; no new synthesis or full regression was run
for this analysis.

The user retained P17 and deferred timing closure. The next authorized step is
[P18 one-entry posted writes](optimization/P18_ONE_ENTRY_POSTED_WRITES_20261002.md).
Its private physical-data kernels gain 13.18–15.45% over the P17 control with
matching architectural signatures and exact physical write counts. The module
passes strict lint, 495 physical/bridge/arbiter checks and 145 composed-cache
checks. Isolated mapping estimates the entire enabled new block at 51 ALMs,
59 registers and no RAM; no fitted whole-design delta is claimed. Matched real
CHECKNUM integer formatter outputs are **6138 -> 6906 (+12.51%)**; complete DOS
math/exit receipts remain pending. Bounded real-CPU machine checks pass at
common/divided clocks, as do bridge dual-simulator checks and Quartus frontend
elaboration (0 errors). Production adoption and MiSTer throughput remain pending.
The separate [P19 platform attribution](optimization/P19_AT_REFRESH_PLATFORM_ATTRIBUTION_20261002.md)
identifies missing AT refresh/HOLD/arbitration: production's 32-clock requester
costs 7.18-9.88% in P17 physical-data kernels with unchanged signatures. That is
comparable to the residual 7.69% / 6.07% hardware gap; real matched CHECKNUM
controls are running. No refresh-policy change or full regression is claimed.

Added 2026-10-01. Status: numeric reference accepted; directed memory-path
attribution and a coherent 1 KiB RAM-read buffer implemented and checked;
hardware CheckIt/CHECKNUM improvement observed; repeated matched measurements
and further throughput attribution remain open. The subsequent
[all-corner 50 MHz closure](optimization/P08_50MHZ_TIMING_CLOSURE_20261002.md)
has positive setup and hold. The user confirmed the selected RBF at maximum
speed, reported normal Windows 3.1/OS/2/game operation, and supplied matching
CheckIT/CHECKNUM results of 3946 Dhrystones / 76.7K Whetstones. See the
[hardware observation record](optimization/P08_HARDWARE_CHECKIT_20261002.md).
The small decrease from the best earlier observations is recorded without
an established cause. The earlier
[50 MHz audit](optimization/P05_50MHZ_AUDIT_20261001.md) describes physical
limits addressed by the later closure. The initial CheckIt 3.03C report was 3584
Dhrystones / 71.9K Whetstones on MiSTer,
versus 4143 / 70.9K for the **original native 86Box 286 at 25 MHz**. The supplied
native screenshot is not SPK286-in-86Box. The new standalone CHECKNUM frontend
reproduces 4143 / 70.9 on that native reference; the user accepted it on MiSTer
with 3584 / 72.2. See [the acceptance record](CHECKNUM_REFERENCE_20261001.md).
The subsequent hardware results and local RBF/report hashes are recorded below;
the 2026-10-02 selected-RBF identity and maximum-speed setting are user-attested.
Other runtime settings and repeat-run variation remain to be matched.
This is a whole-machine performance story; no CPU functional cause is established.

Acceptance plan for later work:

1. Record the benchmark executable/hash, disk, BIOS, memory size, video,
   CPU frequency, timing policy, active CPU options and RBF/build hash for both
   machines. Distinguish original native 86Box from SPK286-in-86Box explicitly.
2. Repeat the same workload after the current protected-mode work is accepted,
   retaining complete scores and repeat-run variation.
3. Compare emulated CPU cycles per workload, accepted memory/I/O transactions,
   READY waits, prefetch starvation, bridge/SDRAM service time, refresh/DMA and
   video accesses. Host wall time and 86Box's speed percentage are separate data.
4. Attribute any gap using directed measurements before changing RTL. Preserve
   architectural results and real bus dependencies in every timing policy.

H15 concerns descriptor-cache publication during task switches. Those caches
hold segment translation/protection state; a benchmark improvement from H15 is
not claimed. Start with the existing [memory throughput](AT_MEMORY_THROUGHPUT.md)
and [bus latency](optimization/BUS_LATENCY_50MHZ.md) evidence when profiling
PCAT. The directed measurements and first optimization below are complete;
further hardware attribution and acceptance remain open. The numeric DOS reference is ready.

### Current-source memory-path investigation — 2026-10-01

Base: PCAT `3e16222`, SPK286 `2073e96`, 86Box `cfb9f52cd`. The
[measurement receipt](evidence/perf01-pcat-20261001/summary.json) records exact
source hashes, options, final architectural signatures and comparison results.
These are four **synthetic firmware kernels**, not execution of the commercial
CheckIt benchmark. The existing fixture named `whetstone` uses fixed-point
operations; it does not reproduce CheckIt's software floating-point library.
No production RTL, CPU option, clock, disk image or RBF was changed during this
baseline investigation. The implementation below is a subsequent milestone.

#### Source findings

- Production CPU, AT bridge, memory port, read buffer and KFSDRAM all run at
  `CLK_50M`. `SPK286_AT_CDC` does not insert a mailbox in this CPU/RAM path;
  its other clock-domain boundaries cannot be charged as CPU memory waits.
  The optional 25 MHz CPU divider is disabled, and execution enable is 1.
- P01/P02/P05/P06 are enabled in both the current project configuration and
  the latest local synthesis flow report. The old missing-P01/P02 configuration
  discrepancy has already been corrected. Aligned RAM words already use x16.
- The production P03 read buffer has 64 aligned eight-byte lines (512 bytes).
  `cache_candidate` requires `in_code_fetch`: ordinary data reads, including
  stack and record accesses, pass through to SDRAM. Writes also go to SDRAM.
  A write invalidates the matching cached physical line, not every code line.
- A data access uses one KFSDRAM word transaction. The controller activates
  the row and precharges after each transaction; it does not keep a row open
  for a subsequent independent CPU data access. Code fills amortize this over
  four words, but wait for all four before returning the requested word.
- The bridge retains capture, command acceptance, response and CPU completion
  boundaries. Its code-buffer hits still traverse registered stages. Returning
  to IDLE also separates requests; single-access latency is not the sustained
  transfer interval. P01/P06 have removed earlier bookkeeping states already.

#### Comparison with 86Box

`src/cpu/spk286_backend.cpp:spk286_model_tick()` keeps `top.ready=1` and supplies
read data before the active CPU edge. `src/cpu/spk286_host.c:exec_spk286()` steps
one model clock and increments guest time once per cycle. It does not call the
native instruction/prefetch timing model to insert RAM READY waits.

Normal 286 RAM accesses use the mapping callbacks in `src/mem/mmu_2386.c`.
`cpu_use_exec` remains zero for a 286 in `src/cpu/cpu.c`, so the RAM callbacks'
conditional read/write lookup penalties are not active on this path. Aligned
word transfers avoid the misalignment charge; odd CPU beats use byte callbacks.
Device callbacks can have their own timing effects. This describes ordinary RAM,
not a claim that every I/O or video operation has zero cost in 86Box.

The **native** 86Box 286 at 25 MHz has nominal read/write/prefetch costs of four
CPU cycles (160 ns) in `cpu_table.c`, unless overridden by wait-state settings.
`cpu_update_waitstates()` selects those costs; `prefetch_run()` models instruction
byte availability and overlap with instruction execution. These four cycles
are not applied to the SPK286 wrapper. Nor are their definitions identical to
the request-to-READY measurement below. Native 86Box and SPK286 at the same
nominal MHz are therefore different timing models.

#### Measured access costs at 50 MHz

The existing directed runner was rebuilt from current sources and obtained
P01/P02/P05/P06 from `config.tcl`. P03 was enabled for the production comparison.
Physical SDRAM refresh was enabled; AT refresh requests, IRQ, DMA, loader and
video contention were absent from this reduced harness.

| Access | Minimum wait clocks | Mean across the four kernels | Mean time |
| --- | ---: | ---: | ---: |
| Code-buffer hit | 3 | 3.00 | 60 ns |
| Code miss/four-word fill | 11 | 11.19–11.55 | 224–231 ns |
| Data read | 8 | 8.13–8.31 | 163–166 ns |
| Data write | 7 | 7.10–7.47 | 142–149 ns |

Clocks are counted from the first edge observing the CPU request to the edge
observing CPU READY; the terminal READY edge is excluded from the wait count.
Typical decomposition is 1 admission + 6 owner service + 1 return for a data
read, 1+5+1 for a write, and 1+1+1 for a code hit. Owner availability/refresh
extends admission for some physical accesses. Busy counters overlap and are
not added together as separate costs.

In the integer mix, demanded operand service occupies 59.35% of elapsed clocks
and demanded instruction-byte starvation 3.57%; in the Dhrystone-shaped fixture,
these are 42.47% and 11.71%. Operand service includes admission and response
dependencies, not just external stalls. Code hit rates are 99.91% and 98.48%
respectively. Merely enlarging the code buffer is not the strongest measured
candidate for these kernels.

#### Controlled isolation of the integration cost

[The diagnostic probe](../scripts/profile_at_ideal_bus.py) generates a private
copy of the existing harness under `build/`. Its always-READY variant supplies
the same backing RAM directly to the CPU, preserving byte lanes and the BIOS
alias. The CPU and its options are unchanged. It is an approximation of the
86Box CPU/RAM boundary for these no-device workloads, not a physical SDRAM
proposal or a timing-compatible replacement for the complete machine.

| Kernel | Physical PCAT path, clocks | Always-READY CPU bus, clocks | Physical / ideal |
| --- | ---: | ---: | ---: |
| Integer mix | 1,018,179 | 501,701 | 2.029x |
| Fixed-point mix | 778,897 | 432,999 | 1.799x |
| Working set | 1,014,656 | 509,984 | 1.990x |
| Dhrystone-shaped fixture | 1,003,290 | 561,536 | 1.787x |

Every pair agrees on complete GPR/FLAGS state, the hash over the full backing
memory, instruction retirement count and CPU write count. All four physical
runs in the generated probe also reproduce the original harness's result
counters and signature exactly. The ideal variants report zero external READY
waits and pass the original firmware memory-pattern checks.

Separate existing counterfactuals keep the bridge and P03 while making only
selected physical-owner accesses ideal. In the integer mix, ideal data reads
give +23.8% throughput, ideal reads+writes +39.3%, and a simulated 1 KiB data-read
cache with physical writes +23.3%. Ideal code fills alone give no improvement
(-0.2%, due to changed scheduling/refresh phase). In the Dhrystone-shaped fixture,
the corresponding results are +12.0%, +24.3%, +11.8% and +0.9%. These gains are
not additive and are not predictions of hardware CheckIt scores. The cache
experiment has no DMA/HPS writers and is not a coherence-validated design.

This establishes a substantial integration cost independently of CPU
architectural changes. It does **not** establish that CPU sequencing contributes
nothing: the existing partial SPK286-in-86Box integer score, 3854 at 25 MHz,
still differs from native 86Box's 4143. Nor does a synthetic 1.8–2.0x ratio prove
the exact loss in commercial CheckIt. The loaded hardware RBF remains unattested;
the receipt records the local RBF hash and matching flow options only. No timing
closure or historical cycle accuracy is inferred from these simulations.

### Coherent RAM-read buffer implementation — 2026-10-01

Base: PCAT `5d619db`; SPK286 and 86Box sources are unchanged. The production
configuration enables `SPK286_AT_RAM_READ_BUFFER`, retaining the normal 50 MHz
CPU and `SPK286_AT_NO_DEBUG`. Commenting out this assignment selects the physical
bypass for comparison. No OSD choice or CPU timing-policy change is introduced.

The pipeline is shared memory port → P03 code buffer → new RAM-read buffer →
SDRAM owner. The new buffer holds 512 direct-mapped words (1 KiB of data), indexed
and tagged with the canonical 25-bit backend address. A synchronous lookup
returns a hit one clock after acceptance; a miss reads the complete aligned RAM
word. Odd-byte requests still use their original CPU byte lane. Tags and data
share a 512×31-bit M10K RAM; only validity and transaction control are reset.

Only ordinary CPU RAM reads of cycle class 5 are eligible. Low RAM below A0000
and canonical extended/shifted/EMS RAM from 100000 through 11DFFFF can be cached;
the machine's existing mapper remains responsible for installed-memory bounds,
A20 and aliases. Canonical backend FF0000 is RAM, not a second BIOS alias. Video,
option ROM, UMB, BIOS, I/O, instruction fills, refresh and DMA/loader reads bypass
the buffer. The P03 code buffer remains independent.

CPU, DMA and loader writes all reach physical SDRAM before completion. Matching
cached words are updated with their accepted byte enables; writes neither
allocate a missing line nor evict an unrelated tag. The common owner serializes
these operations, so no writer can race a pending cache fill. P03 still
invalidates matching instruction lines. CPU cancellation flushes validity even
while idle or under another owner; accepted physical transfers drain, preserving
DMA/loader writes and suppressing cancelled fills. Four-word instruction bursts
forward every beat and complete only on the final READY.

#### Directed acceptance and performance

The [measurement receipt](evidence/perf01-ram-buffer-20261001/summary.json) and
[A/B comparison](evidence/perf01-ram-buffer-20261001/ram-buffer-comparison.json)
retain source hashes and final architectural signatures. With the same CPU,
options, 512-byte code buffer, SDRAM pin model and physical refresh:

| Synthetic kernel | Buffer off, clocks | Buffer on, clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Integer mix | 1,018,179 | 826,081 | +23.25% |
| Fixed-point mix | 778,897 | 682,866 | +14.06% |
| Working set | 1,014,656 | 913,639 | +11.06% |
| Dhrystone-shaped fixture | 1,003,290 | 897,746 | +11.76% |

All four pairs agree on complete GPR/FLAGS, the full backing-RAM hash,
instruction retirement and CPU write counts. Every baseline reproduces the
earlier pre-buffer elapsed clock count. These kernels are not commercial CheckIt
and do not predict its software floating-point score. DMA/HPS/IRQ contention is
absent from the performance runs and covered separately where indicated below.

Directed checks passed:

- Isolated unit in Icarus and Verilator: word and odd-byte hits; CPU/DMA/loader
  byte/full writes; no write allocation; tag collisions and high physical tags;
  excluded regions/classes; refresh/code/DMA bypass; disable/re-enable; idle and
  active cancellation; stalled CPU and loader writes; cancelled read fills;
  complete normal/cancelled four-word bursts; identical back-to-back requests.
- Memory port + P03 + new buffer in Verilator: data updates and code-line
  invalidation under CPU/DMA/loader writes, refresh and DMA-read bypass, and a
  stalled loader write across CPU cancellation. Strict standalone RTL lint and
  simulation assertions pass. The sole lint waiver is the intentional split
  between asynchronous control reset and synchronous RAM enables.
- Quartus 17.0.2 isolated Analysis & Synthesis: 0 errors, 0 warnings; a
  512×31-bit simple-dual-port M10K RAM inferred (15,872 block-memory bits).
  This is module mapping, not full-board fitting or timing closure.
- Quartus production Analysis & Elaboration passes with 0 errors and 155
  warnings, using the real project with the cache macro enabled. Full fitting,
  STA and new RBF generation remain for the
  user's hardware build.

The isolated unit passes in both simulators. Icarus stalls in a zero-time delta
scheduling loop when the existing memory-port/P03 combinational handshake chain
is cascaded with the new stage; that pipeline is checked with Verilator, the
same simulator used for the physical CPU workloads. No pipeline Icarus pass is
claimed. No full SPK286 regression was run for this milestone.

Reproduction in Ubuntu WSL:

```sh
PCAT_BUILD_DIR="$PWD/build/ram-buffer-unit" bash scripts/test_at_ram_read_buffer.sh
PCAT_BUILD_DIR="$PWD/build/ram-buffer-perf" bash scripts/test_at_ram_read_buffer_perf.sh
PCAT_BUILD_DIR="$PWD/build/ram-buffer-map" bash scripts/check_at_ram_read_buffer_quartus.sh
AT_CDC_CHECK_OUTPUT="$PWD/build/ram-buffer-frontend" bash scripts/check_at_cdc_quartus.sh
```

The implementation milestone did not generate or overwrite the existing RBF.
The user subsequently built and tested the new variant, as recorded below.

#### User hardware performance observation — 2026-10-01

After building the RAM-read-buffer variant, the user supplied
[original CheckIt](evidence/perf01-ram-buffer-20261001/mister-checkit.png) and
[CHECKNUM](evidence/perf01-ram-buffer-20261001/mister-checknum.png) screenshots:

| Program | Earlier MiSTer result | New MiSTer result | Observed gain |
| --- | --- | --- | --- |
| Original CheckIt, Dhrystones/s | 3584 | 4042 | +12.78% |
| Original CheckIt, K Whetstones/s | 71.9 | 78.7 | +9.46% |
| CHECKNUM, Dhrystones/s | 3584 | 4143 | +15.60% |
| CHECKNUM, K Whetstones/s | 72.2 | 78.1 | +8.17% |

Use each program's own earlier measurement; mixing 71.9 from CheckIt with
72.2 from CHECKNUM would change the reported gain. The two new screenshots
differ by 2.50% in integer score and about 0.76% in math score. Their same
benchmark routines have the original BIOS-tick calibration/quantization, while
frontend and run conditions can differ. These screenshots alone do not isolate
that variation; repeat-run sampling is still pending.

The new CHECKNUM integer score equals the original native 86Box 286 at 25 MHz
reference (4143). Its 78.1K software-math score is 10.16% above that reference's
70.9K. This is agreement for a particular benchmark, not general CPU cycle
equivalence. CheckIt's CPU estimate remains approximately unchanged: 35.02 MHz
before and 35.01 MHz now, despite higher benchmark scores.

The [hardware receipt](evidence/perf01-ram-buffer-20261001/hardware-observation.json)
records the screenshot hashes and local full-build artifacts. The current local
RBF is 4,115,792 bytes, dated 2026-10-01 16:06:41 Europe/Madrid, SHA256
`f3f79bf56a2b7a09f2df020a3215668b4c21f657483fd0ae72d7bf1341aac9b7`.
The successful flow report includes P01/P02/P05/P06, the RAM-read-buffer macro
and NO_DEBUG; it targets 50 MHz. This local-file correspondence does not
independently attest the exact hash of the RBF loaded on MiSTer or all runtime
settings. No new synthesis or regression was run when recording the result.

The full-build reports still show negative setup slack: `FPGA_CLK2_50` reaches
-4.479 ns in the slow -40 C corner, with reported Fmax 40.85 MHz; SDRAM and
video also have negative setup entries. The observed benchmark improvement
does not establish timing closure. Detailed path attribution, repeat-run
scores and normal boot/DMA coverage remain open under PERF01.

#### Next bounded performance work

The [2026-10-02 physical-read response experiment](optimization/P09_SDRAM_RESPONSE_EVALUATION_20261002.md)
has now measured one of these candidates in isolation. Forwarding KFSDRAM's
already registered read response removes one owner cycle, while preserving
the registered request entry. All eight directed workload pairs preserve
architectural state and write counts. With production buffers enabled, the
cycle reduction is only 0.027–0.112% in the two CheckIT-shaped kernels and
Dhrystone 2.1, versus 2.010% in the working-set kernel. The prototype remains
an experiment: no timing fit or hardware validation was performed and the
production owner is unchanged. The separate
[bridge response candidate](optimization/P10_BRIDGE_RESPONSE_20261002.md)
removes one return cycle for native RAM/ROM hits, misses and writes. Its four
production-buffer kernels show 9.294–10.255% higher throughput with matching
architectural state and write counts. Directed protocol, cancellation and
corrected real-CPU warm-reset/IRQ tests pass. The user subsequently reported
4361 Dhrystones (+10.517% versus 3946), CheckIT 84.1K Whetstones (+9.648%)
and CHECKNUM 83.7K (+9.126%) on MiSTer; the previous result was 76.7K.
The [screenshots and attribution limits](evidence/perf01-bridge-hardware-20261002/README.md)
are retained. These hardware measurements are separate from the synthetic
kernels. The generated candidate has worst setup -0.557 ns at 50 MHz, with
hold positive in all four corners. Preserve the measured benefit while
recovering timing closure; keep the previous timing-closed RBF as fallback.

The [completed same-clock comparison](optimization/P11_86BOX_50MHZ_COMPARISON_20261002.md)
now records **7709 / 133.3K for SPK286 in 86Box at 50 MHz**, with CPU sources
and P02/P05/P07 matching the hardware candidate. Native 86Box at 50 MHz gives
8287 / 144.9K, repeated identically; its 25 MHz control remains 4143 / 70.9K.
Both 50 MHz CPU arms complete CHECKNUM with DOS RC0. The primary PERF01 target
is the **PCAT versus standalone SPK286 integration gap**: hardware's 4361 / 83.7K
is 56.57% / 62.79% of the same CPU with immediate memory service. Matching
that reference would require +76.77% / +59.26% hardware throughput. The smaller
native-CPU difference is an additional control. The report links ready-to-use
50 MHz profiles, complete receipts and the scope of these comparisons.

1. Capture request/wait counts and actual code/data-buffer behavior for CHECKNUM
   in PCAT, with the loaded RBF recorded. Profile writes, hit turnaround,
   capacity/conflict misses, prefetch and SDRAM service in the same benchmark
   region. The 512-byte code buffer's high synthetic hit rate does not establish
   the DOS application's hit rate. Use the completed standalone result as the
   primary reference before attributing the gap to a physical SDRAM limit.
2. Extend the observed RAM-read-buffer hardware improvement with repeat-run
   CHECKNUM results, timing/path review and normal boot/DMA coverage. Retain
   the off/on configuration for matched comparisons.
3. Independently evaluate reducing registered hit/response turnaround and
   retaining SDRAM rows between safe accesses. Preserve acceptance, cancellation,
   LOCK, byte enables, ordering and refresh; check FPGA timing for each candidate.

The earlier attribution tools remain available in the Ubuntu WSL checkout:

```sh
PCAT_BUILD_DIR="$PWD/build/perf01-pcat" PCAT_PROFILE=1 bash scripts/test_checkit_profile.sh
python3 scripts/profile_at_ideal_bus.py build/perf01-pcat
```

The first command covers four directed kernels with physical/P03 and owner
controls; the second checks the always-READY boundary against those baselines.
They use the current production options, now including the RAM-read buffer;
the historical attribution tables above predate it. Use the dedicated A/B
runner above to compare the new buffer against its physical bypass.
This is performance attribution, not a full SPK286 regression. Full local logs
and generated harnesses for this run are in `build/perf01-pcat-20261001/`.

## 1. PIC special mask mode: pending functional review

Status: concrete source discrepancy; no focused reproduction or correction
yet. This is a chipset follow-up, with no CPU H-story assigned.

In `rtl/KFPC-XT/HDL/KF8259/HDL/KF8259_Control_Logic.sv`:

- OCW1 updates `interrupt_mask` only while the stored
  `enable_special_mask_mode` is clear.
- Every OCW3 stores both ESMM and SMM, including SMM when ESMM is clear.
- A separate `interrupt_special_mask` is updated by later OCW1 writes while
  ESMM is stored as set. It is not derived directly from the current IMR and
  the persistent special-mode state.

The [Intel 8259A datasheet, printed pages 15-16](https://www.pcjs.org/documents/datasheets/intel/INTEL_8259A_PIC.pdf)
describes ESMM as permission for that OCW3 command to change SMM. When ESMM
is zero, SMM remains unchanged. OCW1 continues to program IMR. In special
mask mode, a masked in-service level no longer blocks lower-priority unmasked
requests; requests on the masked level remain masked.

The local 86Box reference, `src/pic.c`, agrees: `pic_write()` always updates
`dev->imr` for OCW1, and updates `special_mask_mode` only when OCW3 bit 6 is
set. Priority selection combines the current IMR, ISR and SMM state.

### Bounded acceptance cases for a future change

1. Enter SMM with OCW3 `68h` after programming IMR. The existing mask must
   immediately govern which in-service levels inhibit other priorities.
2. Write OCW1 while SMM is active. IMR readback and interrupt masking must
   change, including masking the selected level's own requests.
3. Select IRR/ISR reads with OCW3 `0Ah`/`0Bh`. These ESMM=0 commands must
   preserve SMM.
4. Leave SMM with OCW3 `48h`. Ordinary in-service priority blocking must
   resume using the current IMR, without a stale separate special mask.
5. Cover both controllers and cascade delivery, plus normal-mode behavior.

These cases are specifications for later work, not tests executed here.
The retained OBS02 capture saw neither PIC receive an ESMM command, while
RTC interrupt delivery continued. It does not implicate this discrepancy in
the resolved OS/2 black screen.

## 2. Historical OS/2 observations and reusable diagnostic lessons

The [retained evidence manifest](evidence/hardware-followup-20260930/manifest.json)
contains source-video provenance, the local RBF hash and a selected set of
OBS02 frames. The video does not attest the hash of the loaded RBF.
[The original transcription](evidence/hardware-followup-20260930/observations.json)
records the pre-fix state; its unresolved-pointer limitation describes that
capture, not the current acceptance status of OS/2.

- Execution at `01F8:3326..3331` and `2CC6..2CF2` is a kernel work wait. The
  same wait occurred transiently in a successful 86Box run. It does not by
  itself locate the earlier failure or prove that the CPU has stopped.
- OBS02 retained `#GP(0)` at `0377:05F7`, with ES=0000, BX=0000,
  opcode/ModR/M `8B/47`, decoded offset `0008`, and matching instruction
  context. Matched PMWIN code identifies an access to `[ES:BX+8]` after LES.
  Rejecting that null-segment access is consistent with 286 protection.
- Static analysis found PMWIN cleanup callers, but the capture contains no
  executed caller, preceding LES bus data, or stack bytes. The origin of the
  null pointer was never traced. Do not turn this record into an established
  LES defect or reopen H08/H19 on that basis.
- Vector-70 completions and RTC status-C reads continued. Exception counts
  remained stable (`NP=003D`, `GP=0009`, `SS=DF=0000`). This was not an
  observed exception storm or stopped RTC interrupt stream.
- EGA bus-write shadows differed from the successful graphics snapshot.
  Such shadows report delivered writes, not internal video-domain register
  state or VRAM contents. Later EGA isolation in 86Box and the accepted
  hardware correction provide the stronger evidence for this boot failure.

For future observers:

- Capture instruction context before event microcode overwrites it, and
  retain an explicit CS:IP match flag for the fault-entry record.
- Keep normal demand-loading #NP history separate from other exceptions.
- Distinguish CPU reset from peripheral reset. Device shadows must survive
  CPU-only reset if the corresponding devices retain their state; record
  whether a shadow has actually seen a transaction.
- Count events in their source clock domain and transfer a coherent snapshot.
  Counters with different reset origins cannot be compared as absolute totals.
- Identify module code and limits before reusing selectors or addresses from
  another OS/2 run; allocations differ.
- Use the existing 86Box EGA backend to separate CPU and video behavior.
  Its functional success does not establish FPGA timing or SDRAM integration.

## 3. NSSI 0.60 report: closed as MRBIOS-associated behavior

[The supplied screenshot](evidence/hardware-followup-20260930/nssi-060-invalid-opcode-20260927.jpg)
shows NSSI 0.60 reporting `Invalid Opcode` during `Determining bus type...`,
then returning to the DOS prompt. The displayed dump begins `B564 F000`.
The forum post shown in the image is dated 2026-09-27.

Closed on 2026-10-02 at the user's request. The user confirms the failure was
associated with MRBIOS and also occurred in 86Box with the same BIOS.
This supplies the cross-environment comparison missing from the original
triage record. No SPK286 implementation story remains open for this report.
No CPU, EGA or BIOS correction was applied for this closure. The original
screenshot remains historical evidence; exact reproduction settings and the
underlying MRBIOS/NSSI interaction were not independently captured in this run.

## Cleanup boundary

The temporary OBS01/OBS02 RTL and workload-specific markers were removed
from the working sources by restoring the committed compact observer. The
normal configuration remains 50 MHz with `SPK286_AT_NO_DEBUG` enabled and
`SPK286_AT_DEBUG_CPU_DIV2` disabled. The accepted EGA correction is unchanged.

Superseded reports, redundant frames, extracted guest binaries and old timing
reports were removed from the pending tree. A local, ignored recovery copy
and the temporary observer patch are in `build/cleanup-20260930/`; they are
not required to use this document or the retained evidence. No guest boot,
regression or synthesis was run for this documentation cleanup.
