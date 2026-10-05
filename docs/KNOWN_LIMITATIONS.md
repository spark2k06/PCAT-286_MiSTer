# Known limitations and pending evidence

Historical record: the dated sections below retain their original test and
delivery scopes. The active pending-only register is
[Remaining work](REMAINING_WORK.md). Subsequent user acceptance includes
Windows 3.1, OS/2, games, floppy writes and the first functional speed-profile
version; earlier unverified/XT statements below are not current open stories.

## HIMEM LOADALL integration (2026-09-22)

The reported HIMEM extended-memory-test stop has `OP=05` and `ERR U=1`:
the vendored CPU recognized `0F 05` (LOADALL) but did not execute it. The
upstream functional LOADALL implementation is now integrated, with directed
AT/SDRAM coverage for repeated LOADALL, extended-memory copying and A20 at
normal and divided CPU clocks. See [AT_HIMEM_LOADALL.md](AT_HIMEM_LOADALL.md)
for the failing baseline, passing fixture and validation limits. Actual
HIMEM completion and Windows 3.1 protected-mode startup remain unverified
on hardware.

## Latest AT hardware evidence (2026-09-20)

The user confirms BIOS execution and visible Supersoft POST on MiSTer (`6f07770`),
and subsequent DMA2/page-register PASS in hardware (`785231e` preserves that
checkpoint). The startup B:1 fault is traced to the RTC protocol flag lacking
reset; cold/warm simulation and Yosys constant propagation reproduce it.
Hardware now confirms the port 61h/PIT corrections: all three timers, both DMA
controllers/page registers, parity and SYSTEM BIOS pass. Before the DQM fix,
AT failed 16K with both original and patched ROM and repeated POST. XT passed
16K but failed its separate later MEMORY REFRESH; it remains reference-only.
The AT memory tests supplied the data needed to diagnose that difference. The
first read at 006E40 returned FF00 instead of FFFF. The old AT owner reproduces
this with actual MiSTer XS/XSDS DQM wiring:
A12/A11 stayed zero on WRITE, so byte writes overwrote the neighboring lane.
The AT-only fix drives the masks on these pins for column commands, preserving
all row bits on ACTIVE. The corrected pin model now includes this wiring;
both it and dedicated DQM are tested. Original-ROM five-pattern RAM cases pass,
including original header and distinct DS/ES.
The user now confirms both 16K CRITICAL and MEMORY REFRESH PASS in AT hardware.
The next Supersoft stop is PROTECTED MODE CPU: SKIP_PM V1 missed the early
A3B3 path. V2 skips both broad, still-uncertified PM diagnostic paths with an
explicit SKIPPED status and repairs both interleaved ROM checksums. CPU
simulation verifies both continuations and both original checksum routines;
physical V2 confirmation remains pending. Separately, the narrower protected
mode path used by Phoenix `INT 15h/AH=87h` is now covered end-to-end, including
the AT warm reset generated from the 80286 SHUTDOWN condition.
The STA summary archived before the DQM fix had FPGA_CLK2_50 setup -7.563 ns; timing
closure is still pending. The previous -4.338 ns CPU-to-CX path was another fit.
Protected-mode tests are excluded only by the new V2 ROM patch; the old V1
patch did not exclude the early CPU test. V2 checksums are checked independently.
The timer backend is not yet a fully validated 8254. AT count/status read-back
is now implemented, simulator-tested and hardware-confirmed: Phoenix detects
both 1.44 MB drives as type 4, clears CMOS0E and completes the diagnostic
R/D/1 reads. See `AT_PHOENIX_PIT_READBACK_HANDOFF.md`. The later DOS stop from
both floppy and HDD was reduced to the missing AT response to 80286 SHUTDOWN;
the correction and passing Phoenix service regression are documented in
`AT_286_SHUTDOWN_WARM_RESET.md`. Physical boot confirmation is pending.
RTC periodic-rate division and speaker audio are incomplete;
calendar/date rollover and MiSTer `F4xx` host-time import are now implemented.
See `AT_LANDMARK_SKIP_PM_V2.md` for the current ROM and next hardware test.
See `AT_SDRAM_DQM_HANDOFF.md` for the now hardware-confirmed wiring fix.
See `AT_LANDMARK_PIT_PARITY_HANDOFF.md` for the previous functional fixes.
Older I0–I6 statements below describe their original acceptance scope.

## Initial machine profile

- The default `XT_COMPAT` machine remains XT-derived. The optional
  `AT_PROFILE` adds the AT CPU/bus/device composition and real EGA path, but
  it is not yet a complete IBM PC/AT implementation: real media, physical
  full AT keyboard-device command handling, 16-bit ISA timing and full
  DOS/hardware acceptance remain pending. The MiSTer mouse now uses the
  imported PS/2-to-COM1 path; physical mouse acceptance is still pending.
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
