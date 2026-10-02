# P16: measure overlapping write admission and launch

Date: 2026-10-02. PERF01 write-admission candidate, authorized by the user.
Status: directed checks, unchanged 86Box CHECKNUM RC0 and frozen full fit complete.
After the early integer result, the user authorized an RBF while math continued.
The write-admission candidate is in production RTL and the user has supplied
MiSTer benchmark improvement. CPU timing closure, repeated measurements and
broad hardware compatibility remain open. No full regression.

## Control and motivation

[P15](P15_DATA_BUFFER_ASSOCIATIVITY_PLAN_20261002.md) has completed at
5525 / 102.4K in the private PCAT model and 5023 / 96.4K in the user-confirmed
MiSTer CHECKNUM observation. P15 mean data-read waits are 2.00059 / 2.10415 clocks,
while physical write waits are 7.24954 / 7.26504. Writes number 2,765,295 /
8,852,056 in its Dhrystone/Whetstone phases. Counts overlap internal execution;
one saved service clock is not a promised score increase.

The normal SDRAM owner accepts/captures a transaction, then launches KFSDRAM
on a later edge. This private prototype launches an ordinary write on its
accepting edge. It keeps one serialized retained transaction, the complete
physical write/recovery/precharge sequence and completion after KFSDRAM becomes
idle. Reads, code bursts and abstract refresh retain their original launch.
The controller, CAS/row timings, byte mapping, refresh parameters, CPU options,
4 KiB code and 1 KiB two-way data buffers remain unchanged.

The first write ACTIVE command must use the incoming accepted address;
subsequent column/data commands use the retained transaction. The prototype
therefore muxes the incoming canonical address only on write admission and
marks that physical command issued on the accepting edge. It does not report
completion before physical recovery. The new acceptance-to-ACT address path
has not been fitted or checked for FPGA/board timing.

## Completed directed evidence

[Evidence and reproduction patch](../evidence/perf01-write-admission-20261002/README.md)
retain the two private roots and their 15-file identity manifest. Only
`spk286_at_mister_sdram_owner.sv` differs between these roots; production
sources remain unchanged. Creation used commit `9d46e34`; subsequent P15
documentation/comparison-tool commits do not alter these input sources.

| Check | Control | Write-admission prototype |
| --- | ---: | ---: |
| Icarus physical byte/address scoreboard | PASS, 22 writes / 20 reads | PASS, same counts/values |
| Verilator physical byte/address scoreboard | PASS | PASS |
| Icarus bench finish time | 3,436,000 ps | 3,216,000 ps |
| Private adapter ordinary byte write | 7 wait clocks | 6 |
| Private adapter nonallocating write | 7 | 6 |
| Cached code/data hit | 2 / 2 | 2 / 2 |
| Code miss / data miss | 12 / 13 | 12 / 13 |
| Alias/update/invalidate/nonallocation/cancel smoke | PASS | PASS |

The bench uses a 10 ns clock: its 220,000 ps reduction is 22 clocks, one per
physical write. Physical reads, values and masks remain the acceptance checks;
the timing/control adapter itself leaves guest memory values in 86Box.
All private sources stayed unchanged through checking/building. Compiled CPU
objects exactly match the completed P15 control. The original 86Box/release
CPU objects and binaries were reused without modification.

## Current real-guest measurement and decision

Candidate binary: `build/perf01-write-admission-20261002/probe/86Box-memory-probe`.
Arm: `build/perf01-write-admission-20261002/pcat-write-admission/spk50`.
CPU 50 MHz, ISA 8 MHz, same initial disk/CHECKNUM/configuration/CMOS as P15.
CHECKNUM began at 2026-10-02 14:02:39 Europe/Madrid. After the integer formatting
phase, two read-only guest-RAM reads found the stable formatted output
`5666\r\n` at physical byte address `0x4CB38`. This was provisionally **+2.55%**
versus P15's 5525. Reading did not stop the emulator or write to guest/host
process memory. The completed RC0 output below confirms that early integer value.

The user then explicitly requested creating an RBF before math completion.
The production owner has the private prototype's behavior, with its launch
comment corrected and the combinational signal written as `logic` plus `assign`.
No other production RTL/configuration or controller timing parameter changes.

Additional bounded checks before freezing the RBF candidate:

- Physical BL1/CL2 pin model: PASS, 71 accepted/completed writes, 70 reads,
  41 periodic refresh commands over 1224 clocks. Includes a four-word read
  followed by byte writes, alternating banks/rows, poisoning upstream payload
  after acceptance, physical completion before acknowledgement, and a bounded
  refresh-starvation assertion. The faster refresh parameters are test stimuli;
  production retains 100/400 clocks.
- Same new pin/traffic test against the frozen P15 owner: PASS, the same 71
  writes and 70 reads, 44 refresh commands and 1313 clocks. The candidate's
  shorter run issues three fewer scheduled refresh commands; both satisfy the
  same starvation bound and data checks. These cycle totals are the directed
  mixed workload, not an additional CHECKNUM speedup or a vendor timing sign-off.
- Existing finite SDRAM read-window and both DQM wiring checks: PASS, including
  their intentional clock-skew failure controls.
- Composed bridge/buffer cancellation and coherence check: PASS.

## Completed unchanged CHECKNUM comparison

[Receipts, final profiles and trace fingerprints](../evidence/perf01-write-admission-20261002/README.md)
retain matched initial disk, CHECKNUM, configuration, CMOS, CPU backend, compiled
CPU objects, profiler and CPU macros. CPU 50 MHz and 86Box ISA 8 MHz are verified
in coherent process samples. Code/data capacities and controller timings match.

| Private PCAT memory-control model | Dhrystones/s | K Whetstones/s | Application BIOS ticks |
| --- | ---: | ---: | ---: |
| P15 control | 5525 | 102.4 | 256 |
| P16 write admission | 5666 | 102.9 | 251 |
| Displayed rate gain | +2.55% | +0.49% | Adaptive work, not a fixed-work comparison |

The guest finished with `RC TICKRUN 0` and `ALL_DONE`, published a final profile,
and the runner completed at 15:10:00 Europe/Madrid. Host elapsed time was
4041.267 s; it includes boot, sampling and host teardown and is not the guest
benchmark's time. Monitor exit timed out after guest completion; the owned
emulator exited after SIGTERM (return -15), explicitly classified as
`exit_timeout_then_sigterm`, like the completed P15 control. No clean host exit
is claimed. The strict comparison explicitly accepts that classified teardown.

| Mean memory wait clocks | P15 Dhrystone | P16 Dhrystone | P15 Whetstone | P16 Whetstone |
| --- | ---: | ---: | ---: | ---: |
| Code fetch | 2.00110 | 2.00112 | 2.11925 | 2.11882 |
| Data read | 2.00059 | 2.00061 | 2.10415 | 2.10527 |
| Data write | 7.24954 | 6.16845 | 7.26504 | 6.22776 |

P16 accepted 2,732,949 / 8,888,367 physical writes in the two function phases.
Actual data misses (418 / 189,982) match the unchanged two-way shadow exactly.
One fixed launch clock is removed per write; mean differences also include
changed adaptive work, interrupt placement and refresh interference. Bus waits
overlap CPU execution and cannot be added to internal instruction clocks.

Each function trace retains 250,000 accepted operations including calibration
and interrupts. Those bounded footprints are not full working sets. There is
one completed guest run per build; the small math gain is not a repeated result.
86Box owns values/peripherals; DMA/loader/abstract AT refresh and electrical
board behavior remain outside the adapter. Hardware is a separate observation below.

## Completed frozen FPGA fit and available RBF

[Fitted evidence](../evidence/perf01-write-admission-20261002/fitted/fit-observation.json)
compares the P15 and P16 pre-build manifests and verifies both sets of final
artifacts. Only the SDRAM owner differs in the 1203 common inputs; P16 adds
the directed bench and its launcher for 1205 inputs. No frozen source changed
during compilation, no QSF assignments were appended, and BUILD_DATE is 261002.

Full Quartus flow: **32:11, 0 errors, 854 warnings**, 2026-10-02 14:40:25 to
15:12:42 Europe/Madrid including launcher overhead. Quartus 17.0.2 in the same
recorded Docker image targets Cyclone V 5CSEBA6U23I7. CPU remains 50 MHz,
all established CPU options active, `SPK286_AT_NO_DEBUG` enabled and DIV2 disabled.

| Final whole-design resources | P15 | P16 | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs needed | 30,587 (73%) | 31,052 (74%) | +465 |
| Physically placed ALMs | 36,128 (86%) | 36,442 (87%) | +314 |
| Registers | 38,022 | 38,171 | +149 |
| M10Ks | 416/553 (75%) | 416/553 (75%) | 0 |
| Payload/tag memory bits | 3,301,019 | 3,301,019 | 0 |
| Allocated block memory bits | 4,259,840 | 4,259,840 | 0 |
| DSPs / PLLs | 39 / 3 | 39 / 3 | 0 / 0 |

The +465 is the actual net full fit cost (+1.11 percentage points of equivalent
ALM capacity), not 465 ALMs of new owner logic. Owner including KFSDRAM rises
from 122.6 to 133.8 equivalent ALMs (+11.2) and 178 to 182 registers (+4).
The unchanged code-buffer entity rises from 1701.5 to 1977.9 ALMs (+276.4)
and 831 to 891 registers through physical synthesis/packing changes; the data
entity changes from 948.8 to 954.2 ALMs. Do not sum the owner and its nested
KFSDRAM entity, or infer architectural resource changes from those fit variations.

| CPU/system FPGA_CLK2_50 model | Setup ns | Hold ns |
| --- | ---: | ---: |
| Slow 100 C | -0.450 | +0.250 |
| Slow -40 C | -0.029 | +0.237 |
| Fast 100 C | +2.569 | +0.134 |
| Fast -40 C | +2.734 | +0.119 |

P16 **does not close all CPU/system 50 MHz setup corners**. P15's worst setup
was -0.194 ns; P16's worst is -0.450 ns, with TNS -6.195 ns (slow 100 C).
Slow -40 C TNS is -0.080 ns. Hold stays positive. These are the only negative
rows in the final STA summary. In this fit, HDMI setup/hold are positive in
all models (minimum +0.855 / +0.157 ns), with unchanged video/HDMI sources.
No new full constraint/electrical audit or vendor SDRAM timing sign-off is claimed.

Candidate: `D:/GitHub/PCAT-286_MiSTer/build/perf01-write-admission-fit-20261002/work/output_files/PCAT-286.rbf`
(4,147,800 bytes; SHA256
`fc5b0694b00e529ac49ad2e5461086c8c176bfc84c2a854d8be2cded0e981cf2`).
This is the candidate delivered for comparison against the user's P15
CHECKNUM 5023 / 96.4K observation.

## User MiSTer benchmark observation

[Both original screenshots and provenance](../evidence/perf01-write-admission-20261002/hardware/hardware-observation.json)
retain the subsequent user report: CheckIT and CHECKNUM both show **5139 / 97.1K**.
The immediate handoff context associates this report with the delivered P16 RBF;
the screenshots do not attest the loaded hash or explicitly reconfirm the maximum
OSD setting. The candidate's frozen configuration is 50 MHz with CPU options active.
CheckIT's 35.02 MHz is its application estimate.

| User MiSTer observation | P15 | P16 | Change |
| --- | ---: | ---: | ---: |
| Integer, both programs | 5023 | 5139 | +2.31% |
| CheckIT K Whetstones/s | 95.6 | 97.1 | +1.57% |
| CHECKNUM K Whetstones/s | 96.4 | 97.1 | +0.73% |

The observed integer gain agrees in direction and scale with the private
PCAT-model +2.55%. Math also improves in these observations, with one sample per
program; there is no repeat distribution. This hardware benchmark does not
establish full compatibility or repair the negative setup corners. No new
synthesis or regression was run to record these screenshots.

Implementation: `95f5b21`. Complete guest comparison: `b4e73bf`.

1. Completed: guest RC0/ALL_DONE/final profile and classified host teardown retained.
2. Completed: rates and per-transfer waits compared against P15 with identities enforced.
3. Completed: user-authorized frozen full fit, resources/timing and RBF retained.
4. User MiSTer benchmark improvement observed. Repeated hardware measurements,
   CPU closure and any resource reduction are subsequent work. A full regression
   remains a separate task.

Open-row SDRAM policy, refresh-cadence evaluation and a faster common-hit path
are later investigations. No such controller-policy change is in this prototype.
