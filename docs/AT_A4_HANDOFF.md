# AT A4 handoff — DMA, refresh and PIT

**Date:** 2026-09-11
**Status:** Complete for the functional A4 boundary
**Branch:** `codex/spk286-xt-integration`

## Delivered

- `rtl/spk286_integration/spk286_at_dma.sv`
  - AT-visible DMA1/DMA2 register banks and page registers;
  - eight logical channels, with channel 4 reserved for cascade;
  - address/count flip-flops, masking, software request, mode and terminal
    count state;
  - retained 24-bit address, direction and byte-lane metadata through the
    normalized accept/READY transfer handshake;
  - auto-initialization and increment/decrement support for the first
    functional profile.
- `rtl/spk286_integration/spk286_at_refresh.sv`
  - independent refresh owner request;
  - parameterized functional cadence;
  - accepted refresh beat, row progression and completion count.
- `rtl/spk286_integration/spk286_at_pit.sv`
  - ports `40h–43h`, channel 0 programming and counter output;
  - functional modes 0, 2 and 3;
  - synchronous one-cycle `irq0` pulse on terminal count.
- `rtl/spk286_integration/spk286_integration.qip`
  - includes all three A4 production boundary modules.

The A4 boundary is intentionally separate from the imported XT-oriented
`KF8237`/`KF8253` blocks. The active MiSTer top remains `XT_COMPAT`; no XT
device was changed as part of this milestone.

## Functional profile decisions

- Refresh is a separate arbiter owner and has priority over DMA when both are
  pending.
- DMA1 exposes byte transfers using `{page,address}`. DMA2 exposes an even
  word address and both data lanes in this first profile; full historical
  8237 word-page and device-specific wiring remains an A5/A7 refinement.
- A DMA channel holds its address, direction and lane metadata until its
  transfer endpoint accepts and completes exactly one beat. The programmed
  count is interpreted with 8237 semantics: `0000h` means one transfer
  remaining after the current beat, so a programmed count of `0001h` produces
  two beats.
- `counter_clock` is a sampled PIT tick enable at the boundary. The test uses
  explicit pulses, leaving clock-domain synchronization for later top-level
  wiring.

## Evidence

Run from the repository root:

```text
bash scripts/test_a4_dma_refresh_pit.sh
```

The test passes in Icarus and Verilator and verifies:

- a two-beat DMA1 I/O-to-memory transfer at physical addresses `021234h` and
  `021235h`;
- one terminal-count completion and channel masking;
- refresh winning simultaneous contention against DMA and completing one row;
- PIT channel 0 mode 2 producing `IRQ0`;
- no overlapping DMA/refresh ownership and no protocol errors.

## Remaining boundary work

A5 must connect the AT devices to the authoritative decode, PIC and DMA
requests: keyboard/8042, RTC/CMOS, floppy or ATA storage and the selected
video path. The active top-level machine, AT BIOS behaviour, full DMA device
semantics and board evidence remain outside this A4 handoff.
