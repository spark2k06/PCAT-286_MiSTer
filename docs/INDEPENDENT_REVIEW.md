# Independent adapter review

Date: 2026-09-09. Reviewer: independent Codex agent `Lorentz`.

## Scope

The review examined the SPK286-to-XT adapter, bus ownership and reset/ROM
loading contracts, and the I2/I4 tests. It was performed independently from
the implementation work and included reproduction of the import-integrity,
adapter and complete I4 commands.

## Findings and disposition

The first review identified four coverage or integration issues. All four were
resolved before I4 acceptance:

1. Dropping `execute_enable` could lose a prefetched response. Production now
   keeps it asserted and does not advertise the inherited F12 CPU-pause mode.
2. ROM loading had only structural evidence. `pcat_rom_loader` was extracted
   as the production implementation and its test now checks all 65,536 main
   ROM byte writes, EGA presence and composed reset-hold release.
3. The adapter regression omitted wrap boundary cases. It now covers memory
   `FFFFFh -> 00000h` and I/O `FFFFh -> 10000h` word serialization.
4. No composed test joined the bridge to the 8288/PIC command path. The I4
   frontend test now exercises real KF8288 plus real KF8259 under Verilator,
   including two independently READY-delayed INTA cycles and vector `20h`.

The final review reported **no blocking findings**. The reviewer reproduced:

- `scripts/test_i4_machine_events.sh`: pass;
- `scripts/test_i2_bridge.sh`: pass with 20 beats and all seven mutations
  detected;
- `scripts/verify_imports.py verify`: 607 PCXT paths checked with the one
  recorded exception, and all 434 SPK286 paths unchanged.

## Residual observations

- The ownership test uses pin-observer stubs for KF8288 and KF8237. It proves
  the new HOLD/HLDA, drain and LOCK qualification, but it is not a complete
  real-KF8237 DMA transfer regression. Existing chipset regressions cover the
  inherited DMA block separately.
- The dynamic loader test covers the complete main image and the EGA presence
  path. The unchanged, simple XT-IDE `EC000h` branch remains covered by source
  comparison rather than a dynamic loader transaction.
- This review is simulation and source-review evidence. It does not constitute
  Quartus timing closure or observation on physical MiSTer hardware.

These observations are nonblocking for I4 and remain explicit qualification
boundaries rather than being promoted to physical-validation claims.

## I5 bring-up instrumentation review

Date: 2026-09-10. Reviewer: independent Codex agent `Turing`.

This second review was explicitly read-only and ran independently while the
main task owned the build. The reviewer confirmed that it neither modified
files nor started repository-writing processes. It examined the production
SPK286 wrapper and XT adapter again, plus the new external-ROM boundary smoke
and four-page hardware overlay.

No new functional defect was found in the SPK286-to-XT adapter. Status mapping,
byte selection and aligned-word serialization, request retention, READY and
COMPLETE handling, LOCK, HOLD/HLDA ownership, signal widths, GPR order and
segment order were all found consistent.

The review did find instrumentation and test weaknesses. Their disposition is:

1. External-ROM `HLT` and timeout could be accepted after minimal activity.
   They are now fatal; success is the explicit `EXTERNAL_ROM_BOUNDARY_PASS`
   condition after reset-vector execution and 128 accepted transfers.
2. Wide debug vectors crossed clock domains as independently sampled bits.
   They now use a coherent source snapshot with a toggle/acknowledge handshake.
3. The observer was reset with SPK286 and could preserve ambiguous splash-time
   data. It now has a separate hard reset and publishes a visible wrapping
   `SNAP` sequence while SPK286 reset itself remains observable.
4. Page selection could change during a frame. It is now synchronized and
   latched only on vertical blank.
5. Font/RGB latency and blank-input behavior lacked a functional test.
   `scripts/test_debug_overlay.sh` now exercises all pages, architectural and
   trace ordering, coherent refresh, glyph alignment, RGB/HB/VB latency and a
   splash-off fully blank raster under both Icarus and Verilator.
6. Trace legend, SPDX identifier and two synthesis-width warnings were fixed.

The external-ROM test remains intentionally a boundary smoke: it does not
model the complete SDRAM, peripheral and video system and cannot prove a BIOS
boot. Preliminary synthesis attributed roughly 1,046 ALMs, 1,241 registers,
8,192 memory bits and one RAM block to the observer. Final resource and focused
timing evidence must therefore come from the final post-review Quartus build.
