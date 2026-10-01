# CheckIt numeric benchmark reference — 2026-10-01

## Accepted frontend milestone

`SW/CHECKNUM` builds `build/checknum/CHECKNUM.EXE`, a standalone DOS program
that prints Dhrystones/s followed by **thousands of Whetstones/s**. It uses
the supplied CheckIt 3.03C routines and original software floating-point
library, with no benchmark-menu interaction. No CPU or PCAT RTL is changed.

The user ran it on MiSTer on 2026-10-01 and confirmed that it works. The
[hardware screenshot](evidence/checknum-20261001/mister-checknum.png) shows:

```text
A:\>checknum
3584
72.2
```

Executable: 318,272 bytes; SHA256
`38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6`.
See [the build instructions](../SW/CHECKNUM/README.md) and
[extraction/patch manifest](evidence/checknum-20261001/CHECKNUM.manifest.json).
The generated executable is not stored in Git; it is reproducible from the
two hash-pinned files in the user's supplied CheckIt installation.

## Measurements

| Machine and program | Dhrystones/s | K Whetstones/s | Evidence |
| --- | ---: | ---: | --- |
| MiSTer PCAT, original CheckIt, user reports maximum CPU speed | 3584 | 71.9 | [User screenshot](evidence/checknum-20261001/mister-checkit.png) |
| Original native 86Box 5.3 build 8200, 286 at 25 MHz, original CheckIt | 4143 | 70.9 | [User screenshot](evidence/checknum-20261001/user-native-checkit.png) |
| Original native CPU backend in local 86Box 6.0, 286 at 25 MHz, original CheckIt | 4143 | 70.9 | [Unmodified CheckIt control](evidence/checknum-20261001/native-original-checkit.png) |
| Same native 86Box 6.0 machine, CHECKNUM | 4143 | 70.9 | [Redirected DOS output](evidence/checknum-20261001/native-checknum.txt) |
| Same native machine with a 287 configured, CHECKNUM forces software FP | 4143 | 70.9 | [Redirected DOS output](evidence/checknum-20261001/native-287-checknum.txt) |
| MiSTer PCAT, CHECKNUM | 3584 | 72.2 | [User acceptance](evidence/checknum-20261001/mister-checknum.png) |
| MiSTer PCAT after the coherent 1 KiB RAM-read buffer, original CheckIt | 4042 | 78.7 | [User screenshot](evidence/perf01-ram-buffer-20261001/mister-checkit.png) |
| MiSTer PCAT after the coherent 1 KiB RAM-read buffer, CHECKNUM | 4143 | 78.1 | [User screenshot](evidence/perf01-ram-buffer-20261001/mister-checknum.png) |

The native controls use independent copies of
`D:\ISOs\MiSTer\286_win3.1.vhd`, MR BIOS `mr286`, EGA, 2048 KiB RAM,
`cpu_speed = 25000000`, `cpu_use_dynarec = 0`, and the same private BIOS
settings. HIMEM's startup memory test is disabled. The original CheckIt
control is unmodified and runs interactively; CHECKNUM runs with DOS stdout
redirection. Both use 86Box fast-forward with the guest clock/PIT advancing
through CPU execution. Host elapsed time is not the benchmark's timer.

Native reference binary SHA256:
`762553e131ee9f9525ed85a313a6ab3e3b1bc6532575386e9b0474b924ec846e`.
The full disposable run folders are under
`build/perf01-checkit-20261001`; only relevant acceptance artifacts are tracked.

The supplied native screenshot is **the original 86Box CPU**, not SPK286 in
86Box. Hardware RBF hash, actual selected frequency, RAM/BIOS settings and
memory-manager configuration are not attested by these screenshots. The
current PCAT configuration targets 50 MHz; CheckIt's displayed 35.02 MHz is
a software estimate and is not evidence of the physical clock frequency.

## Fidelity and bounded checks

- Input EXE/OVL hashes are checked before creating output. Originals remain
  untouched. The EXE is flattened into a DOS MZ image with rebuilt relocations.
- The complete benchmark overlay (15,760 bytes) and its BIOS-tick reader
  remain byte-identical at their original relative segment addresses.
- The original Microsoft CRT and math library initialize/clean up the program.
  The measured loops, calibration, data constants and score formulas remain.
- Changes are confined to a numeric main frontend, numeric format strings,
  untimed GUI progress/abort operations, and forcing the software-FP choice
  during runtime initialization. No timed benchmark instructions are patched.
- Focused verification passed: two deterministic rebuilds; modified-input
  rejection before writing output; MZ extent/relocation checks; relocation at
  two DOS load segments; four frontend call relocations; benchmark/timer byte
  identity; DOS execution and errorlevel 0; exact native CheckIt screen/output
  agreement; software-mode output with native 287 hardware configured; user
  acceptance on MiSTer.

This does not claim bit-identical scores on every run. BIOS-tick quantization
and display rounding remain those of CheckIt. The observed hardware Whetstone
values 71.9/72.2 differ by about 0.4%; repeat-run sampling is still needed to
measure a variation range. The integer result matches exactly in these runs.
No full SPK286 regression or synthesis is part of this frontend milestone.

## PERF01 interpretation and next measurement

### Bounded SPK286-in-86Box control

A private SPK286 25 MHz run reached CHECKNUM after the slow BIOS/DOS boot and
completed the integer measurement. A coherent guest-RAM snapshot contains
`3854\r\n` in both the frontend's formatted-output stack buffer and the DOS
output buffer. The earlier floating result was 3854.269884686137, consistent
with the integer formatting. That numeric line is absent from the original
source disk. See [the partial capture](evidence/checknum-20261001/spk25-partial.json).

The two-score run did **not** complete within the 1,200-second host-time limit.
The redirected DOS file remains size zero in its on-disk directory while open;
there is no `ALL_DONE` marker, final Whetstone output or accepted normal exit.
BIOS ticks and floating-point working state advanced during the measurement.
The owned emulator instance was closed after saving the snapshot. This is a
partial integer observation, not a completed benchmark pair or regression pass.

Settings: SPK286 binary SHA256
`07392d78cc648e4005d1d3c9802ddf28028a12a99f47dd4e948ec48329e4e7e7`,
25 MHz, P02/P05, normalized timing request 0, MR BIOS, EGA, 2048 KiB RAM.
The 86Box wrapper steps one CPU clock per guest cycle and keeps external READY
asserted. PCAT also requests timing policy 0; P01/P06 concern its machine-side
memory bridge, not additional standalone CPU macros.

The captured integer score is 93.02% of the native 25 MHz result. It suggests
that comparing the native CPU alone with MiSTer alone cannot isolate the cause.
Complete the paired SPK286 run and record matching hardware frequency/options
before attributing the hardware difference to a particular CPU or bridge path.

### Initial hardware comparison

Against the native 25 MHz reference, the observed hardware integer score is
86.51% (13.49% lower). The numeric hardware Whetstone score is 101.83%
(1.83% higher). These results establish a workload-dependent gap; they do not
identify its cause or establish a general equivalent CPU frequency.

SPK286 clock cycles implement the core's actual execution and bus dependencies.
Their count per instruction need not equal a physical 80286's instruction
timings. A nominally higher clock therefore does not guarantee a higher
Dhrystone score. CPU sequencing, instruction fetch, memory service, bridge
waits and refresh remain hypotheses to measure under PERF01.

The next control is CHECKNUM with **SPK286 in 86Box**, at explicit frequencies
and matching CPU options, followed by a hardware run with recorded RBF hash
and settings. Record guest cycles per measured region and bus/fetch waits.
This separates the standalone CPU contribution from the PCAT memory/bridge
contribution before selecting a performance optimization. H15/H16 descriptor
state changes are not established causes of this benchmark gap.

### Hardware update after the RAM-read buffer

The user subsequently built and tested PCAT implementation `add2392`, which
adds a coherent 1 KiB RAM data-read buffer without changing SPK286. CHECKNUM
increased from 3584 / 72.2 to **4143 / 78.1**, gains of **15.60% / 8.17%**.
The integer result equals the native 25 MHz reference; software math is 10.16%
higher. Original CheckIt separately increased from 3584 / 71.9 to 4042 / 78.7.
These are separate observed runs; they do not establish a variation range or
general cycle equivalence. The exact reason for the new CheckIt/CHECKNUM
integer difference has not been isolated.

See the [PERF01 hardware record](HARDWARE_FOLLOWUPS_20260930.md) and
[artifact receipt](evidence/perf01-ram-buffer-20261001/hardware-observation.json)
for the screenshots, local RBF/report hashes and remaining timing/acceptance
scope. Complete SPK286-in-86Box and matched repeated hardware controls remain
useful for attributing the remaining cost.
