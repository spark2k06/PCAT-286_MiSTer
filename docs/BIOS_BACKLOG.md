# Production BIOS backlog

Production BIOS adaptation is outside the I0-I6 core delivery. No BIOS source
or binary was changed, and B0-B2 were not started.

## Current result

The project-owned diagnostic ROM passes deterministic machine simulations.
On 2026-09-10 the user reported a first physical-board attempt with the I5 RBF:
after the splash, neither the supplied XT Sergey-derived BIOS nor the Supersoft
diagnostic produced visible boot output. A preliminary overlay rendered reset-
vector-looking values but did not prove that its snapshot was advancing. With
the splash disabled from core start the same build produced a black machine
raster and no overlay. These observations motivated a live `SNAP` heartbeat
and a blank-raster fallback; they are not evidence that SPK286 itself remained
in reset. The exact board/configuration and loaded RBF hash were not captured,
so this remains a reported observation rather than a completed I6 result.

The supplied 64 KiB images are retained outside Git under `SW/ROMs/test/`:

| Image | SHA-256 |
| --- | --- |
| `xtsergey_mod.rom` | `df25bbc8aba4e35eb56ca585b2c7054da1d7435278b2bfe0f0c7ffae2f85f443` |
| `supersoft_diag.rom` | `9de4e13b37e05a924db1842510b411e1042268da18b982ce2226c2c66f1ba806` |

A reduced simulation using each exact image, the production SPK286 wrapper,
XT bridge, KF8288 and READY logic completes the native reset-vector fetch and
far transfer without a CPU or bridge fault. XT Sergey reaches POST writes
`01h, 02h, 03h, 04h`; Supersoft enters its low-memory clear loop. This narrows
but does not reproduce the physical failure because SDRAM, the complete
peripheral set and video are modeled only at their boundary.

The unchanged firmware contains 8088/V20/FPU assumptions and may still fail
later even though normal 286 identification techniques see SPK286's Real-Mode
FLAGS behavior. The next board discriminator is the project-owned
`pcat286_event_diag.rom`, followed by the passive SPK286 CPU/register/bus/trace
overlay defined in the I6 checklist. It is not replaced by the Supersoft BIOS
diagnostic.

## Later work

- **B0 — inventory and reproduce:** select exact BIOS binaries and hashes,
  reproduce their behavior on a physically validated I6 build, and capture
  POST/port traces without changing firmware.
- **B1 — explicit adaptation:** make the smallest reviewable firmware changes
  required for the XT-derived SPK286 profile, without claiming an AT chipset.
- **B2 — compatibility validation:** test POST, option ROMs, DOS, CheckIt and
  selected software against pinned firmware and RBF artifacts.

These tasks must remain independent of the core diagnostic acceptance result.
