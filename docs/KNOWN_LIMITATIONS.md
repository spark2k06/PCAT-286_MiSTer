# Known limitations and pending evidence

## Initial machine profile

- This is an XT-derived `XT_COMPAT` machine profile with SPK286. It is not a
  complete IBM PC/AT implementation: dual PIC/DMA organization, 8042, AT
  RTC/CMOS semantics, 16-bit ISA and extended AT memory remain deferred.
- Historical 80286 timing is not certified. The OSD control schedules the
  legacy XT bus and is named **XT Bus Pace**; no Accurate/Fast/Max CPU timing
  claim is made.
- CPU pause is unavailable in the initial profile. F12 uses MiSTer's normal OSD
  behavior; SPK286 `execute_enable` stays asserted because it is not a global
  quiesce and may not discard an outstanding response.
- The inherited PCXT peripheral feature set is retained. Its extensions do not
  turn the machine into an AT.

## BIOS boundary

Production BIOS adaptation is expressly outside I0-I6. No B0, B1 or B2 work is
included, and no BIOS source or binary was modified. The current PCXT/Micro8088
firmware contains 8088/V20/FPU probing assumptions and may fail on this profile.
That compatibility result is a later task and is not a diagnostic-ROM gate.

## Simulator, FPGA and hardware boundary

- I4 validates the CPU/adapter/event/peripheral integration with portable
  subsystem benches; vendor HPS/PLL/SDRAM primitives are outside those models.
- The full production-KF8259 event path passes in Verilator. Icarus `vvp` is too
  slow for that combination, so its full program run uses a documented narrow
  PIC boundary and separately tests the real KF8259 in a short dual-simulator
  case.
- FPGA synthesis, fit, constrained timing, resources and RBF belong to I5 and
  are reported separately from simulation.
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
