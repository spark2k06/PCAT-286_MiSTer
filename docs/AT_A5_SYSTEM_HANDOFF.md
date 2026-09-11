# AT A5 handoff — composed system boundary

**Date:** 2026-09-11
**Status:** Intermediate boundary evidence complete; acceptance pending
**Branch:** `codex/spk286-xt-integration`

## Delivered

`rtl/spk286_integration/spk286_at_machine.sv` composes the AT profile behind
one explicit machine boundary:

- `spk286_machine_cpu` and the normalized AT bus bridge;
- 24-bit memory decode, ROM protection and CPU/DMA/refresh arbitration;
- AT PIC, DMA, refresh and PIT services;
- 8042, RTC/CMOS, storage/video router and IRQ/NMI wiring.

The wrapper exposes separate CPU-memory, DMA-memory and refresh-memory
handshakes. This is the point at which the future MiSTer SDRAM, media and
video owners can attach without changing the CPU transaction contract.
The active MiSTer top level remains `XT_COMPAT`; it was not switched to this
profile by this milestone.

The AT bridge was also corrected so the first INTA beat can complete on READY
without fabricated read data, while ordinary reads still require an explicit
data-valid response.

The next attachment boundaries are now implemented in
`rtl/spk286_integration/spk286_at_mister_memory_port.sv`. It serializes the
CPU, refresh and DMA endpoints into one MiSTer-facing 16-bit backend port,
latches request metadata across backend stalls, preserves byte lanes, and
reports accidental multi-owner requests. The composed event-ROM test now
drives the machine through this port and the new
`rtl/spk286_integration/spk286_at_mister_sdram_owner.sv`, which exercises the
existing KFSDRAM controller and physical byte masks in simulation. The active
`CHIPSET_SPK286` still owns the legacy XT memory/peripheral path internally,
so the final top-level profile selection remains a separate step.

## Composed evidence

Run:

```text
bash -lc "AT_SYSTEM_MAX_CYCLES=200000 bash scripts/test_at_machine_boundary.sh"
```

The run performs production Icarus elaboration and production Verilator lint,
then executes the CPU through the composed boundary with the project-owned
event diagnostic ROM. The passing runtime marker was:

```text
AT_SYSTEM_BOUNDARY_PASS memory_beats=211 io_writes=12 irq0=1 refresh=60 port80=4
AT_MACHINE_BOUNDARY_TEST_PASS
```

The diagnostic observed the native reset fetch at `FFFFF0`, fetches from the
`F0000h` ROM window, PIC/PIT programming, one IRQ0 service through both INTA
beats with vector `20h`, the handler EOI and `IRET`, and the POST sequence
`70h -> 72h -> 71h -> 86h`.

For deterministic whole-CPU runtime, the testbench uses the small portable
master-only `spk286_at_machine_pic_model` under `AT_MACHINE_PIC_MODEL`. The production
`spk286_at_pic` plus imported KF8259 pair are still elaborated and linted here,
and the production PIC behaviour remains covered by the A3 focused tests.
This evidence therefore proves composition and transaction ownership, not
yet the final production-PIC/DOS/hardware path.

## Acceptance still pending

This milestone is not a DOS-boot or board acceptance. Remaining work is to
select the AT SDRAM owner in the real MiSTer top level, attach HPS/media and
video owners, exercise physical keyboard/storage/video paths, run the DOS and
representative-device trace ladder, and then produce a board-loadable RBF for
user testing. No AT compatibility claim is made until those steps pass.
