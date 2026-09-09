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
