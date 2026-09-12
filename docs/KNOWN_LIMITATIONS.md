# Known limitations and pending evidence

## Latest AT hardware evidence (2026-09-12)

The user has confirmed BIOS execution and visible Supersoft POST on MiSTer;
commit `6f07770` preserves that hardware checkpoint. The subsequent DMA register
corrections pass the original Landmark DMA2/page routines in simulation and
await the next user-built RBF. Persistent startup B:1 is not yet explained;
a passive First Fault Trace is provided. PIT channels 1/2, full protected-mode
BIOS use, and complete POST remain open. The selected SKIP_PM ROM has separate
EPROM-lane checksum failures introduced by its existing patch.
See `AT_LANDMARK_DMA_HANDOFF.md` for current evidence and hardware steps.
Older I0–I6 statements below describe their original acceptance scope.

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
- The user's latest booting AT_FAST fit has worst setup -21.537 ns and hold
  +0.054 ns. SDRAM_CLK has positive setup/hold; FPGA_CLK2_50 has same-clock
  Fmax 39.36 MHz at the slow 100C corner, below the configured 50 MHz.
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
