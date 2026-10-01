# Hardware follow-ups retained after the OS/2 EGA fix

Date: 2026-09-30. Baseline: PCAT `e80b52a`, 86Box `2a94fd669`.

The user accepted OS/2 startup on MiSTer after the EGA corrections. See
[the EGA integration and acceptance record](PCAT_EGA_86BOX_INTEGRATION_20260930.md).
This document preserves useful observations from the earlier investigation
and separates open findings from that resolved boot failure.

## PERF01 — MiSTer CPU and machine benchmark throughput

Added 2026-10-01. Status: numeric reference accepted; current-source directed
memory-path attribution completed; commercial CheckIt/hardware attribution
pending. CheckIt 3.03C reports 3584 Dhrystones / 71.9K Whetstones on MiSTer,
versus 4143 / 70.9K for the **original native 86Box 286 at 25 MHz**. The supplied
native screenshot is not SPK286-in-86Box. The new standalone CHECKNUM frontend
reproduces 4143 / 70.9 on that native reference; the user accepted it on MiSTer
with 3584 / 72.2. See [the acceptance record](CHECKNUM_REFERENCE_20261001.md).
Active hardware RBF provenance and matching settings remain to be recorded.
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
PCAT. The directed measurements below are complete; hardware attribution and
optimization remain open. The numeric DOS reference is ready.

### Current-source memory-path investigation — 2026-10-01

Base: PCAT `3e16222`, SPK286 `2073e96`, 86Box `cfb9f52cd`. The
[measurement receipt](evidence/perf01-pcat-20261001/summary.json) records exact
source hashes, options, final architectural signatures and comparison results.
These are four **synthetic firmware kernels**, not execution of the commercial
CheckIt benchmark. The existing fixture named `whetstone` uses fixed-point
operations; it does not reproduce CheckIt's software floating-point library.
No production RTL, CPU option, clock, disk image or RBF was changed.

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

#### Next bounded performance work

1. Capture completed CHECKNUM scores and request/wait counts in matched SPK286
   and hardware configurations, with the loaded RBF recorded. Use the same
   benchmark region to check how closely these kernel findings transfer.
2. Measure a PCAT RAM-read buffer/cache below the existing ownership boundary,
   with writes still committed to SDRAM and CPU/DMA/loader coherence covered.
   Ordinary RAM is the initial eligible region; devices and EGA retain their
   access semantics. Compare against the unchanged baseline before enabling it.
3. Independently evaluate reducing registered hit/response turnaround and
   retaining SDRAM rows between safe accesses. Preserve acceptance, cancellation,
   LOCK, byte enables, ordering and refresh; check FPGA timing for each candidate.

Reproduction in the Ubuntu WSL checkout:

```sh
PCAT_BUILD_DIR="$PWD/build/perf01-pcat" PCAT_PROFILE=1 bash scripts/test_checkit_profile.sh
python3 scripts/profile_at_ideal_bus.py build/perf01-pcat
```

The first command covers four directed kernels with physical/P03 and owner
controls; the second checks the always-READY boundary against those baselines.
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

## 3. NSSI 0.60 report: retain for triage

[The supplied screenshot](evidence/hardware-followup-20260930/nssi-060-invalid-opcode-20260927.jpg)
shows NSSI 0.60 reporting `Invalid Opcode` during `Determining bus type...`,
then returning to the DOS prompt. The displayed dump begins `B564 F000`.
The forum post shown in the image is dated 2026-09-27.

This attachment was the only pending item in SPK286. It is retained here
because it reports whole-machine behavior with no established CPU cause.
There is no reproduction, precise build/configuration record or confirmed
resolution attached to it. It must not be counted as a newly reproduced CPU
failure, or silently classified as fixed by the EGA change.

Before opening an implementation story, reproduce with a recorded RBF, BIOS,
NSSI executable and configuration; capture the faulting bytes and context;
then compare against native 86Box and SPK286 in 86Box where applicable.

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
