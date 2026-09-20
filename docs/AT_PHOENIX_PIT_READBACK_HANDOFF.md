# Phoenix floppy detection and AT PIT read-back — 2026-09-20

## Hardware evidence

The user's state-probe v4 reports CMOS10=44, CMOS0E=20 and matching
calculated/stored checksums 0395/0395. Both configured drives are 1.44 MB;
this configuration is valid. Phoenix nevertheless leaves BDA48F=11 and
BDA490=93. After INT13 reset, the directory read returns AX=0200/CF=1 and
FDC result bytes 44 05 00 00 01 02 02. Changing the number of configured
drives is not the remedy.

The earlier RTC retention fix successfully preserves HPS/SETUP CMOS data,
but it did not fix this runtime drive misclassification. A20, DMA addressing,
the option-ROM map, the disk images and the production Phoenix ROM are not
changed by this investigation.

## Confirmed PIT defect

Phoenix F000:9447, shared by the floppy waits, sends E2h to port 43h and reads
port 40h to inspect counter 0's programmed mode. E2h is an **8254 status-only
read-back command**, not a count latch. The previous AT adapter explicitly
used an 8253 backend without read-back support. The command was ignored and
the subsequent IN consumed a count byte instead of status, advancing the
LSB/MSB pointer. Later count pairs could consequently be byte-swapped and
the BIOS wait arithmetic could expire prematurely.

The focused regression loads counter 0 with 1234h in mode 0, then reads
status. The old implementation returns 34h (count LSB) instead of 30h
(OUT=0, null=0, LSB/MSB, mode 0, binary). The regression fails before the fix.

Reference: Intel 8254 datasheet, Read-Back Command, figures 10–12, pages 8–9:
https://www.cs.cmu.edu/~410/doc/8254.pdf
Local comparison: `D:/GitHub/86box_dev/src/pit.c`, `pit_write`,
`ctr_latch_status` and the independent count/status read state.

## Implementation

- Add opt-in `ENABLE_8254` to KF8253 and its internal modules. Only the AT
  adapter enables it; default XT instances retain their 8253 interface.
- Decode read-back counter selects and independent count/status latches.
- Return latched status before count, without consuming a count byte.
- Preserve the first unread snapshots on repeated latch commands.
- Report OUT, null-count, RW, mode bits as programmed, and BCD.
- Track null count on complete CR writes and CR-to-CE reloads.
- In 8254 mode a new mode control word releases old latches and resets byte
  phases even if the RW format is unchanged.

This is not a claim of complete cycle-accurate 8254 emulation. The inherited
counter engine and FDC mechanical timing have not been generally reworked.

## Validation and limits

- `scripts/test_at_pit_ports.sh`: Icarus + Verilator, including RTC/reset,
  PIT clock, all three channels, status-only/count-only/combined read-back,
  repeated snapshots, interleaved LSB/status/MSB, null-count reload, OUT,
  reprogramming, and the previous gate/refresh/parity tests.
- `scripts/test_at_pit_irq0.sh`: mode 3/divisor 65536 IRQ0 transitions.
- `scripts/test_a4_dma_refresh_pit.sh`: Icarus + Verilator integration.
- `scripts/test_at_bios_first_fetch.sh`: production CPU/loader/SDRAM fetch
  checks for the existing BIOS set and the private Phoenix test fixture.
- Focused Verilator lint: no errors; existing backend width/combinational
  assignment warnings remain.
- An investigative old/new default-KF8253 comparison passes 10,000 identical
  bus transactions with exact data/OUT comparison (Icarus). Source snapshots
  and log are under `build/phoenix-boot-probe/`.

`scripts/test_at_phoenix_fdc_post.sh` executes original Phoenix F000:A16C
with the production SPK286 CPU, PIC, PIT, RTC, FDC, bridge and SDRAM path.
The private fixture installs RAM/stack/interrupt vectors and initializes the
PIC and PIT. Phoenix IRQ0/IRQ6 handlers remain original. INT10 is a no-op
and INT15 declines external wait services. Both drives are mounted 80x2x18
and CMOS10=44. All original bytes from 0200h through FFEFh are preserved;
the source ROM on disk is never changed or redistributed in the fixture.

For practical runtime, the default test accelerates **both** PIT and FDC
timebases by ten. This is functional integration evidence, not production
timing certification or a complete POST/DOS boot. `AT_PHOENIX_REAL_TIME=1`
disables acceleration; allow a substantially longer timeout in that mode.

The baseline with the old AT PIT adapter reproduces **BDA48F=11** and writes
CMOS0E=20, after premature waits and FDC resets. With read-back enabled the
isolated detection reaches **BDA48F=44**. The trace still contains a timeout
on the long seek to cylinder 50; the later 8-to-0 drive-detection sequence
completes correctly. Do not describe this as all FDC timing passing.

## Hardware result and remaining boot issue

The synthesized core now confirms the correction with both drives configured
as 1.44 MB. State probe v4 reports `CMOS10=44`, `CMOS0E=00`, matching checksum
`0311/0311` and `BDA48F=44`. INT13 reset, directory and IO.SYS-sector reads all
return successfully (`R AX=0000`, `D AX=0001`, `1 AX=0001`), with the FDC kept
at 500 kbit/s for the 1.44 MB medium.

The original MS-DOS 6.22 floppy now reaches `Iniciando MS-DOS...`, proving that
the boot sector and initial system-file reads have progressed beyond the old
FDC failure. It still stops at that point. The HDD reaches the equivalent
`Starting MS-DOS...` point and stops too. The remaining problem is therefore a
separate common DOS initialization issue, not the Phoenix drive-type mismatch.
It is not resolved by this change and must be investigated independently.
