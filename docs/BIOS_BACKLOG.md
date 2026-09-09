# Production BIOS backlog

Production BIOS adaptation is outside the I0-I6 core delivery. No BIOS source
or binary was changed, and B0-B2 were not started.

## Current result

The project-owned diagnostic ROM passes deterministic machine simulations.
Production PCXT/Micro8088 BIOS execution was not evaluated on physical hardware
in this task, so there is no honest POST, DOS or CheckIt result to report. The
unchanged firmware contains 8088/V20/FPU assumptions and may fail even though
normal 286 identification techniques see SPK286's Real-Mode FLAGS behavior.

## Later work

- **B0 — inventory and reproduce:** select exact BIOS binaries and hashes,
  reproduce their behavior on a physically validated I6 build, and capture
  POST/port traces without changing firmware.
- **B1 — explicit adaptation:** make the smallest reviewable firmware changes
  required for the XT-derived SPK286 profile, without claiming an AT chipset.
- **B2 — compatibility validation:** test POST, option ROMs, DOS, CheckIt and
  selected software against pinned firmware and RBF artifacts.

These tasks must remain independent of the core diagnostic acceptance result.
