# P06/P12: initial native 286 DOS reference

Status: native measurement milestone complete, 2026-10-03. Physical 6/12 MHz
measurements are **NOT_MEASURED**. Historical-profile RTL and instruction/bus
cycle validation remain pending. This complements the
[P06 plan](P06_TIMING_REFERENCE_PLAN_20261003.md) and
[P12 reference contract](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).

## Tested program and scope

`T286REF2` executes fixed-work R0 register, B0 branch/prefetch and M0 aligned-RAM
cases. All use 256 iterations and seven baseline plus seven gross repetitions.
Each sample checks its result signature; the host validator recomputes timer
phase/delta and all six summaries. The baseline is recorded separately. These
numbers include measurement, setup, loop and signature-store overhead; they
are not isolated instruction costs and are not baseline-subtracted.

The reproducibly assembled DOS executable is **2,840 bytes**, SHA-256
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.
The ready-to-copy file is
`build/p06-timing-reference-20261003/T286REF.COM`.
[Source/build instructions](../../SW/CPUTIME/README.md), the frozen executable,
NASM listing with exact case bytes, raw CSVs and receipts are retained in the
[evidence bundle](../evidence/p06-timing-reference-20261003/README.md).

## Original 86Box 286 results

Both final controls completed with **guest exit 0, host exit 0**, 42 valid
samples and six valid summaries. Runtime inspection confirmed the native
`exec386_2386` dispatcher, not SPK286, and the actual requested CPU frequency.
The ordinary Intel entry labelled `12` runs at **12,500,000 Hz**.

| Case | 6 MHz median ticks (min–max) | 12.5 MHz median ticks (min–max) |
| --- | ---: | ---: |
| R0 baseline | 728 (728–728) | 382 (381–382) |
| R0 register gross | 1339 (1338–1339) | 1017 (1017–1017) |
| B0 baseline | 728 (727–728) | 382 (381–382) |
| B0 branch gross | 1899 (1898–1899) | 1066 (1066–1066) |
| M0 baseline | 728 (727–728) | 382 (381–382) |
| M0 memory gross | 2153 (2153–2154) | 1384 (1383–1384) |

Units are elapsed **PIT input ticks**, conditional on the recorded standard
BIOS reload assumption. Lower elapsed ticks mean less time for this identical
work. No measured MHz or per-instruction CPU-cycle count is inferred.

| Runtime setting | 6 MHz control | `12` entry / 12.5 MHz control |
| --- | ---: | ---: |
| Actual CPU frequency | 6,000,000 Hz | 12,500,000 Hz |
| `cpu_waitstates` | 0 / automatic table | 0 / automatic table |
| Prefetch/read/write service cycles | 2 / 2 / 2 | 3 / 3 / 3 |
| `timing_rr` | 2 | 2 |
| ISA frequency / `isa_cycles` | 6,000,000 Hz / 1 | 8,000,000 Hz / 2 |
| Observed PIT0 mode | 2, binary LSB/MSB | 2, binary LSB/MSB |
| Program CS / aligned word offset (decimal) | 3858 / 2832 | 3858 / 2832 |

`cpu_waitstates=0` selects automatic memory timing. It does not remove native
instruction `CLOCK_CYCLES` or prefetch costs. The two profiles also differ in
memory service costs and ISA cadence; their elapsed-time ratio need not equal
the CPU-frequency ratio. These service-cycle fields do not count extra READY
waits on a physical board. Cache flags were **not sampled** by this runner;
the recorded effective prefetch/read/write costs are the observed controls.

## Identity, environment and unsuccessful controls

The local 86Box source base is
`fa3343da5b551bc937114c1e3ab3a8e16aed9e79`; source hashes and model limitations
are recorded in P12. The native executable is the previously built native
reference, with SHA-256
`2d87185ff14842a20a2bd0fed1713820dd64eabaa049b08a9827b48948de4dd3`.
It includes the earlier extra 50 MHz table entry, unused by these ordinary
6/12.5 MHz controls. Native execution was verified at runtime.

Each run cloned `D:/ISOs/MiSTer/286_win3.1.vhd` into its own private image,
installed the same program and booted plain DOS with `FILES=20, BUFFERS=10`,
without the image's memory managers or TSRs. The input disk's SHA-256 remained
`cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f`.
The board was `[ISA] MR BIOS 286 clone`; configuration, initial CMOS, guest
commands, CPU-state samples and binary/runner/validator hashes are retained.
Frequency labels and CMOS differ by profile; entire private images are not
claimed byte-identical. ROM/BIOS identity is frozen in the bundle manifest.

Early controls sampled during CPU-dispatch initialization or stopped at the
MRBIOS speed-change acknowledgment; they are not accepted measurements.
The subsequent revision-2 calibration controls produced valid guest CSVs but
host teardown returned **−6**, so they are recorded as **host-failed controls**.
They used periodic screenshots and manual acknowledgment/F10. The cause of
that host failure is not established. Final repeats used their calibrated CMOS
without periodic screenshots and exited cleanly with host and guest code 0.
The original calibration-run receipts are preserved rather than promoted to
full-run PASS. Both final BIOS logs contain the diagnostic
`F000:C3D4 Illegal instruction`; successful program/host completion does not
mean the logs contain no warnings.

## Limits and physical handoff

The program never reprograms PIT/PIC or timer vectors. It records
`NOT_CALIBRATED`, nominal PIT input 1,193,182 Hz and an **assumed** BIOS divisor
65536. Its checks reject incompatible mode/status/windows and verify functional
signatures. They cannot certify the actual reload register/crystal or exclude
whole-period CPU stalls. The final DOS controls exercised mode 2; mode 3 has
source review and exhaustive host arithmetic plus synthetic parser coverage,
but no executed DOS mode-3 control in this milestone.

For the collaborator's actual 6 and 12 MHz settings, run the **same binary** in
plain DOS and retain the complete files:

```dos
T286REF 6 > REF6.CSV
T286REF 12 > REF12.CSV
```

Record CPU marking, board/BIOS, RAM, speed-switch method, DOS/TSRs and any known
memory/ISA/refresh wait configuration using the P12 manifest. Do not require
the collaborator to alter wait states. Intrinsic processor timings are fixed
by the CPU; board READY waits may be configurable on some machines and otherwise
remain a property of that recorded system. A physical 12 MHz measurement is
distinct from the native 12.5 MHz control. No historical profile is certified
by these initial samples; M1's physical and reference-extraction gates stay open.
