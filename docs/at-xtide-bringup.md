# AT IDE storage-port regression

The AT profile retains its IDE/VHD storage interface, which uses the standard
primary channel at `1F0h–1F7h` and alternate-status/device-control port `3F6h`.
The XTIDE option-ROM slot and loader path described in the original bring-up
were retired when `C8000h–DFFFFh` became fixed UMB RAM. The `300h` XT2IDE window
remains unmapped.

This regression records the IDE I/O decode and storage bridge behavior; it
does not imply that the AT OSD still accepts an XTIDE ROM.

## Cause and fix

`spk286_at_machine.is_a5_io_port()` did not include the IDE primary channel.
Consequently the machine's unmapped-I/O sink completed reads with `FFh` and
discarded writes before they reached `spk286_at_device_router`. The IDE engine
could still be configured through the independent HPS management interface.

The AT-only path forwards `1F0h–1F7h` and `3F6h` to the existing IDE engine;
the old XT2IDE `300h–30Fh` window is intentionally unmapped. The `1F0h` data
register is accepted as one native 16-bit I/O beat.
The broad `3F0h–3F7h` FDC range is explicitly gated so `3F6h` cannot be
accepted by the floppy endpoint. It applies to `PCAT-286_AT_FAST.qsf` and the
other AT profile through the existing integration QIP; no CPU pacing change is
needed.

## Reproduction and coverage

Run `bash scripts/test_at_xtide_machine.sh`. Set `AT_XTIDE_VERILATOR=1` to also
run Verilator. The test uses the production AT bridge, machine decoder, router,
IDE engine and `hps_ext`. Only the CPU instruction engine is replaced with a
bus driver; the Quartus RAM primitive uses the simulation model.

Against `94fd21d`, after configuring a present master and a ready status through
`hps_ext`, the CPU-side check failed:

```text
CPU port 0307: expected 40, got ff (sink_reads=1)
```

With the decoder fix the regression checks:

- IDE reset requests and register access through the HPS extension transport.
- Status and detection-register access from the CPU bus, including odd byte lanes.
- Software reset, delayed host responses and IRQ clearing by normal/alternate status.
- A full 256-word standard AT transfer using native x16 reads from `1F0h` and
  alternate status reads from `3F6h`.
- The old `300h` XT2IDE window remains unmapped and reaches the I/O sink.
- No duplicate commands and no decoding of neighboring ports.

The AT bus clock is 50 MHz. Each simulation runs with zero extra CPU idle
cycles and with 32 extra cycles between accesses. Both cases pass in Icarus
and Verilator with the decoder fix. Host FIFO words are spaced
to allow the registered management read pipeline to settle; this is not a test
of physical ARM/GPIO timing. Synthetic host payloads stand in for image contents.

The earlier `test_a5_at_devices.sh` instantiated the device router directly,
so it could not detect a missing entry in the machine's upstream decoder. It
now also checks the real IDE engine's native word path and the `3F6h` FDC/IDE
ownership boundary. These tests do not execute the BIOS or prove booting from
physical MiSTer hardware; the rebuilt AT_FAST RBF still needs that final
hardware check.

## Banner hang: missing BIOS INT 40h (2026-09-16)

The IDE decode and AT PIC changes did not resolve the reported hang after
the AT XUB banner. The `FFh`/`7Fh` absent-device change also did not fix it.
The banner alone does not establish that the CPU is polling IDE status.

A directed test now executes the actual SPK286, AT chipset, Sergey IVT
initialization and INT 13h handler, and the r631 AT option ROM instructions.
The original Sergey POST installs only IVT entries 00h–1Fh. INT 40h remains
0000:0000. In `ide_at.bin`, code at C800:0525 tests whether INT 13h already
supports hard disks by calling AH=08h through INT 13h and INT 40h. Sergey's
INT 13h succeeds, so C800:0534 executes `INT 40h` and jumps to 0000:0000
before drive detection at C800:0807.

The old `ide_xtl.rom` uses a different check at C800:0C32: it checks the
segment of INT 40h and copies the old INT 13h vector when INT 40h is absent.
It therefore handles this XT BIOS omission, explaining why the old image
could continue while the AT image fails before printing drive information.

`scripts/patch_xtsergey_at_int40.ps1` creates the separate BIOS
`SW/ROMs/test/xtsergey_mod_at_atpic_int40.rom` from the AT-PIC variant.
It redirects the five-byte DS setup at F000:E1AB to an unused ROM area at
F000:E370, copies INT 13h into INT 40h, and completes the original DS setup.
Only that call site, the 22-byte routine and the final checksum byte change.
Size is 65536, sum8 is 00h, and the reset vector is preserved. No INT 15h
service or CPU/PIC/IDE RTL change is needed for this specific correction.

Reproduce with PowerShell `./scripts/patch_xtsergey_at_int40.ps1` followed by
`bash scripts/test_at_xub_probe.sh`. The test first observes the bad jump with
the prior BIOS, then runs the actual patched POST call site and observes
successful arrival at drive detection with INT 40h = F000:EC59. Video and
keyboard services and the external memory are simulation fixtures. This
proves the specific failure and fix in that execution path, not a complete
physical disk boot. The subsequent hardware report confirmed that this BIOS
gets past the banner, displays the hotkey bar, identifies both primary disks
and reports both secondary-channel positions as absent.

## Post-detection hang: missing CPU SALC (2026-09-16)

The requested rollback restores `rtl/common/ide.v` to its original absent-bus
value, `FFFFFFFFh`. The shared engine no longer has the speculative `7Fh`
change. Primary AT ports/native word data and the removal of `300h` remain.

With the actual r631 AT ROM and the INT40-patched Sergey BIOS, the expanded
CPU/chipset probe reproduces a second failure **after** both primary IDENTIFY
transfers and both secondary timeouts. It reaches C800:094F (construct the
fixed-disk parameter tables), calls C800:069E and stops at C800:06A1:

```text
C800:069E  F6 05 20  test byte [di],20h
C800:06A1  D6        salc
C800:06A2  75 02     jnz 06A6h
```

`SALC` sets AL to FFh when CF=1 and 00h when CF=0, preserving AH and FLAGS.
In particular, the following conditional jump needs TEST's ZF to survive.
SPK286 had explicitly excluded this undocumented instruction. Its decoder
classified D6 as unsupported, **not** as an architectural #UD: the development
`unsupported_opcode` diagnostic stopped progress at that instruction. This is
a CPU compatibility omission, not an IDE-port collision or another missing
Sergey BIOS service. A responsive hotkey bar does not prove the main boot path
is progressing.

The integrated CPU copy now admits D6 and uses the ordinary byte-register
write owner. Microcode format 21 appends the four controls READ_FLAGS,
CARRY_FILL8, MOVE8, END. CARRY_FILL8 is control 171, transforming a captured
temporary without writing FLAGS. All previous 717 ROM words, entry addresses
and branch targets remain unchanged; the image is now 721 words. The source
compiler regenerated the package, ROM and metadata. No BIOS or XUB binary
was changed for this fix, and no upstream SPK286 repository was edited.

Validation:

- `bash scripts/test_at_xub_probe.sh`: missing-INT40 reproduction and fixed
  detection checks still pass. With two synthetic disks, the actual CPU now
  completes initialization, expires the boot delay, resets/configures IDE,
  issues READ MULTIPLE for one boot sector and transfers control to 0000:7C00:
  `AT_XUB_BOOT_PASS identify=2 reads=1 cycles=3329802`.
- The extended fixture accelerates the PIT divisor to 1024. It still uses
  the production PIT/PIC and real Sergey timer/INT13/INT15 handlers. Video,
  keyboard, POST setup, external RAM and host disk contents remain fixtures;
  this is not a physical VHD/SDRAM/OS boot claim. The host model follows the
  management protocol, including repeated reset requests and SEEK/ABRT.
- SingleStepTests/80286 D6: all 1,000 physical cases pass, none excluded or
  revoked. Source blob `bda19075232193a5dd8d146feb332ffe2a8c814e` from the
  local `SPK286/.cache/singlestep-80286/v1_real_mode/D6.MOO.gz` corpus. The
  7,000 physical CBW/CWD/LAHF cases also pass.
- Direct scalar RTL: 2,272 cases / 138,653 checks in **each** of Icarus and
  Verilator, covering both carries, all AH byte values, FLAGS preservation,
  prefixes and READY stalls. The decoder passes both simulators; CPU lint
  and the two new microcode lifecycle/round-trip tests pass. The Yosys CPU
  synthesis sanity check also passes (not a Quartus board fit).
- `bash scripts/test_at_xtide_machine.sh`: both pacing configurations pass
  with 256 native data words and `legacy_300=0`.

The broad `make regression` is **not green**: it stops at eight pre-existing
microcode-test failures (stale format/Phase-8 contracts and far TASK_SWITCH
validation expectations). They were reproduced before the SALC edit (88 tests)
and remain the same eight failures afterwards (90 tests). They were not waived
or changed to accept this patch. Logs are in `build/at-xub-probe/`.

For the next hardware test, rebuild the AT core and retain
`xtsergey_mod_at_atpic_int40.rom` plus `ide_at.bin`. The user has not yet tested
the SALC-capable RBF on hardware; successful real-disk boot remains unconfirmed.
