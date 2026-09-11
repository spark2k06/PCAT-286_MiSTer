# AT A5 handoff — devices and routing

**Date:** 2026-09-11
**Status:** Functional boundary complete; system acceptance pending
**Branch:** `codex/spk286-xt-integration`

## Delivered

- `rtl/spk286_integration/spk286_at_8042.sv`
  - ports `60h/64h`, output buffer, keyboard IRQ1, controller status;
  - output-port A20 control and active-low CPU reset request;
  - command-byte, keyboard enable/disable and self-test response subset.
- `rtl/spk286_integration/spk286_at_rtc_cmos.sv`
  - ports `70h/71h`, seven-bit CMOS index and NMI mask;
  - deterministic status/date storage, BCD seconds and periodic IRQ8;
  - Status-C read-to-clear behaviour.
- `rtl/spk286_integration/spk286_at_storage_video.sv`
  - primary ATA register boundary and deterministic IDENTIFY/status response;
  - floppy register boundary, channel-2 DMA request and terminal IRQ6;
  - EGA I/O range and a small A0000h aperture shadow for contract tests.
- `rtl/spk286_integration/spk286_at_device_router.sv`
  - one-owner decode for 8042, RTC, ATA, floppy and video;
  - response-owner retention through READY;
  - deterministic `FFh` response for unmapped I/O;
  - IRQ vector wiring: IRQ1 keyboard, IRQ6 floppy, IRQ8 RTC and IRQ14 ATA.

All modules are listed in `rtl/spk286_integration/spk286_integration.qip`.
The active MiSTer machine remains `XT_COMPAT`; the existing XT peripheral
path and its `KFPS2KB`, `rtc`, FDC, IDE and EGA implementations were not
mutated.

## Functional evidence

```text
bash scripts/test_a5_at_devices.sh
```

The Icarus and Verilator runs report:

```text
A5_AT_DEVICES_PASS keyboard=1 rtc_irq8=1 ata_irq14=1 floppy_dma_beats=2 irq6=1 video=1
A5_AT_DEVICES_TEST_PASS
```

The test covers keyboard FIFO pop and IRQ1, A20 output-port programming,
periodic RTC IRQ8 and BCD seconds, ATA status/data and IRQ14, EGA I/O and
memory routing, unmapped I/O, and a two-beat floppy-like DMA channel-2
transfer completed through the A4 arbiter/DMA boundary.

## Acceptance still pending

This functional boundary is not yet a DOS-boot or hardware acceptance. The
remaining A5 work is to attach the physical PS/2 receiver, provide the real
MiSTer media backend, replace the video shadow with the selected EGA/VGA
memory path, connect the router and IRQ vector to an AT top level, and run
the DOS/representative-device trace ladder. Board evidence remains A7 work.
