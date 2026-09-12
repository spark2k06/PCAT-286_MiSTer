# Known limitations and pending evidence

## Latest AT hardware evidence (2026-09-12)

The user confirms BIOS execution and visible Supersoft POST on MiSTer (`6f07770`),
and subsequent DMA2/page-register PASS in hardware (`785231e` preserves that
checkpoint). The startup B:1 fault is traced to the RTC protocol flag lacking
reset; cold/warm simulation and Yosys constant propagation reproduce it.
Hardware now confirms the port 61h/PIT corrections: all three timers, both DMA
controllers/page registers, parity and SYSTEM BIOS pass. Before the DQM fix,
AT failed 16K with both original and patched ROM and repeated POST. XT passed
16K but failed its separate later MEMORY REFRESH; it remains reference-only.
The AT-only RAM observer supplied the data needed to diagnose that difference.
The new RAM Trace identifies the first read at 006E40 returning FF00 instead of
FFFF. The old AT owner reproduces this with actual MiSTer XS/XSDS DQM wiring:
A12/A11 stayed zero on WRITE, so byte writes overwrote the neighboring lane.
The AT-only fix drives the masks on these pins for column commands, preserving
all row bits on ACTIVE. The corrected pin model now includes this wiring;
both it and dedicated DQM are tested. Original-ROM five-pattern RAM cases pass,
including original header and distinct DS/ES, plus injected error controls.
The user now confirms both 16K CRITICAL and MEMORY REFRESH PASS in AT hardware.
The next stop is PROTECTED MODE CPU: SKIP_PM V1 missed the early A3B3 path.
V2 skips both unsupported PM paths with an explicit SKIPPED status and repairs
both interleaved ROM checksums. CPU simulation verifies both continuations and
both original checksum routines; physical V2 confirmation remains pending.
The STA summary archived before the DQM fix had FPGA_CLK2_50 setup -7.563 ns; timing
closure is still pending. The previous -4.338 ns CPU-to-CX path was another fit.
Protected-mode tests are excluded only by the new V2 ROM patch; the old V1
patch did not exclude the early CPU test. V2 checksums are checked independently.
The timer backend is not yet a complete 8254: read-back
status is unsupported. RTC calendar/periodic rates and speaker audio are incomplete.
See `AT_LANDMARK_SKIP_PM_V2.md` for the current ROM and next hardware test.
See `AT_SDRAM_DQM_HANDOFF.md` for the now hardware-confirmed wiring fix.
`AT_CRITICAL_RAM_HANDOFF.md` preserves the earlier instrumentation audit.
See `AT_LANDMARK_PIT_PARITY_HANDOFF.md` for the previous functional fixes.
Older I0–I6 statements below describe their original acceptance scope.

## Initial machine profile

- The default `XT_COMPAT` machine remains XT-derived. The optional
  `AT_PROFILE` adds the AT CPU/bus/device composition and real EGA path, but
  it is not yet a complete IBM PC/AT implementation: real media, physical
  PS/2 handling, 16-bit ISA timing and full DOS/hardware acceptance remain
  pending.
  The CPU-visible 8042 now implements the IBM AT commands and status needed by
  the Landmark U126 and scan-lines diagnostics. The physical HPS path still
  needs complete make/break/extended conversion and keyboard-device command
  exchange; see `AT_8042_KEYBOARD_HANDOFF.md`.
- Historical 80286 timing is not certified. The OSD control schedules the
  legacy XT bus and is named **XT Bus Pace**; no Accurate/Fast/Max CPU timing
  claim is made.
- CPU pause is unavailable in the initial profile. F12 uses MiSTer's normal OSD
  behavior; SPK286 `execute_enable` stays asserted because it is not a global
  quiesce and may not discard an outstanding response.
- The inherited PCXT peripheral feature set is retained. Its extensions do not
  turn the machine into an AT.

## BIOS boundary

Production BIOS adaptation is expressly outside I0-I6. No BIOS source or binary
was modified. The bring-up failure that motivated this profile is currently
attributed to the SPK286 D8–DF coprocessor/ESC decoder blocking; the CPU fix is
tracked in SPK286 Phase 8 workstream 8B. Retest the original BIOS unchanged after
that fix before considering any firmware change. The existing PCXT/Micro8088
firmware contains 8088/V20/FPU probing assumptions, but a BIOS adaptation is
only a contingency for an independently reproduced failure that remains after
the CPU correction. It is not an I0-I6 diagnostic-ROM gate.

## Simulator, FPGA and hardware boundary

- I4 validates the CPU/adapter/event/peripheral integration with portable
  subsystem benches; vendor HPS/PLL/SDRAM primitives are outside those models.
- The full production-KF8259 event path passes in Verilator. Icarus `vvp` is too
  slow for that combination, so its full program run uses a documented narrow
  PIC boundary and separately tests the real KF8259 in a short dual-simulator
  case.
- The user's DMA checkpoint AT_FAST fit has worst setup -22.197 ns and hold
  -0.730 ns. SDRAM_CLK has positive setup/hold; FPGA_CLK2_50 has same-clock
  Fmax 37.28 MHz at the slow 100C corner, below the configured 50 MHz.
  Whole-project timing sign-off is not claimed. See the latest handoff above;
  `I5_FPGA_BUILD.md` retains historical build evidence.
- Hardware testing is performed by the user between turns. The agent has no
  direct board capture; the reported boot and diagnostic screenshots are
  physical observations, while full I6 acceptance remains incomplete.

## SPK286 nonblocking evidence notes

The selected D-026/D-037 CPU policy retains exactly these five nonblocking
questions. They are not physical PASS results and are not prerequisites for
this consumer integration:

1. `failed-iret-nmi`
2. `sti-old-if`
3. `fault-tf`
4. `rep-zero-count-event-order` under the recorded zero-element/next-IP policy
5. `e7-incomplete-physical-capture` for the exact allowlisted record

All evaluable CPU cases remain governed by the imported SPK286 acceptance
records. No Phase 8 completion or publication of the E7 issue is claimed.
