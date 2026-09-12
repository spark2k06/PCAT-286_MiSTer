# Known limitations and pending evidence

## Initial machine profile

- The default `XT_COMPAT` machine remains XT-derived. The optional
  `AT_PROFILE` adds the AT CPU/bus/device composition and real EGA path, but
  it is not yet a complete IBM PC/AT implementation: real media, physical
  PS/2 handling, 16-bit ISA timing and full DOS/hardware acceptance remain
  pending.
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
- I5 produces a successful Quartus compile, fit and RBF. In the current
  `AT_PROFILE` build, reset recovery is positive in all analyzed corners
  (worst case +3.750 ns), while inherited video/HPS/SDIO paths still report
  global setup violations (worst case -21.009 ns). Whole-project timing
  sign-off is therefore explicitly not claimed; see `I5_FPGA_BUILD.md`.
- No physical MiSTer board is authorized or available in this task. I6 is
  prepared through ROM loading, port signatures and LED observation, but stays
  pending until an actual board/configuration is supplied and execution is
  explicitly authorized.

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
