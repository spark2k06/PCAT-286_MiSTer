# 80286 SHUTDOWN warm reset on the AT profile

## Failure

The original Phoenix A286 1.01 BIOS completed POST and loaded the DOS boot
sector, but MS-DOS 6.22 stopped after `Starting MS-DOS...`. The same floppy
and hard-disk images booted with this Phoenix ROM in 86Box and with the
modified Sergey ROM in the core.

An instruction trace from the working 86Box configuration reduced the
difference to Phoenix `INT 15h`, function `AH=87h`. Phoenix builds a temporary
GDT, enters 80286 protected mode, copies the requested words, loads an invalid
IDT and executes `INT 0`. The resulting failed exception entry asserts the
80286 `SHUTDOWN` condition. CMOS byte 0Fh contains shutdown code 07h, whose
Phoenix reset-dispatch table selects the continuation at F000:B306.

The CPU core asserted `spk_shutdown`, but the AT machine treated it only as a
sticky diagnostic fault. The processor therefore remained stopped in
protected mode and never fetched the reset vector. This also explains why a
BIOS that does not use this protected-mode service could boot the same media.

## AT behavior and correction

The 80286 leaves SHUTDOWN only through NMI or RESET. The IBM AT motherboard
responds to the shutdown cycle with a CPU-local warm reset. RAM, CMOS and the
AT devices must remain live because the BIOS uses the retained CMOS shutdown
code and low-memory state to resume the interrupted service.

`spk286_at_machine` now includes `spk_shutdown` in `cpu_core_reset` and exports
the same event through `cpu_reset_request`. The latter cancels any serialized
SDRAM request owned by the pre-reset CPU context. It does not reset CMOS,
memory, DMA or the other devices.

This does not change A20 policy. A20 still powers on disabled, CPU accesses
obey the gate, Phoenix opens and closes it through the 8042, and legacy DMA
remains independent of A20.

## Reproduction and validation

`tests/firmware/phoenix_pm87_fixture.asm` calls the untouched Phoenix
`INT 15h/AH=87h` routine with source and destination descriptors. Before the
correction it fails with:

```text
PHOENIX_PM87_SHUTDOWN_NOT_RESET csip=0020:b306 msw=fff1
```

After the correction it observes protected mode, one SHUTDOWN pulse, a second
reset-vector fetch, the copied word, return to real mode and A20 closed:

```text
PHOENIX_PM87_PASS resets=2 destination=a55a PE_reset=1 A20_closed=1
```

The focused Phoenix test, production machine lint/elaboration, machine
boundary, RTC/CMOS retention, serialized-memory cancellation, Phoenix FDC POST,
Landmark PM-skip/checksum cases and AT profile elaboration all pass.

Primary references:

- Intel, *80286 Hardware Reference Manual*, order number 210760-002.
- IBM, *Personal Computer AT Technical Reference*, first edition, March 1984;
  BIOS reset and CMOS shutdown-byte listings.
