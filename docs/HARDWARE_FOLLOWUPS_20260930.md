# Hardware follow-ups retained after the OS/2 EGA fix

Date: 2026-09-30. Baseline: PCAT `e80b52a`, 86Box `2a94fd669`.

The user accepted OS/2 startup on MiSTer after the EGA corrections. See
[the EGA integration and acceptance record](PCAT_EGA_86BOX_INTEGRATION_20260930.md).
This document preserves useful observations from the earlier investigation
and separates open findings from that resolved boot failure.

## PERF01 — MiSTer versus SPK286-in-86Box benchmark gap

Added 2026-10-01. Status: pending measurement. The user reports lower benchmark
scores on MiSTer than with the same CPU core integrated in 86Box. Benchmark
names, scores, active RBF and matching configurations have not yet been supplied.
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
PCAT. Measurement and optimization remain a future task.

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
