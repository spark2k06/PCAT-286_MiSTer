# AT A3 handoff

## Delivered

- `rtl/spk286_integration/spk286_at_pic.sv` — AT master/slave KF8259
  wrapper, ports `20h/21h` and `A0h/A1h`, IRQ8-15 cascade through master
  IRQ2, normalized acceptance/READY and two-beat INTA response.
- `rtl/spk286_integration/spk286_at_nmi_gate.sv` — port `70h` bit-7 NMI mask,
  parity/channel-check/external source edge qualification and reset-masked
  output policy.
- `sim/spk286_integration/spk286_at_pic_tb.sv` — programmed master/slave
  PIC, mask reads, masked IRQ, IRQ0 vector, IRQ8 cascade and two-INTA checks.
- `sim/spk286_integration/spk286_at_nmi_gate_tb.sv` — reset mask, enable,
  edge qualification and remask checks.
- `scripts/test_a3_interrupts.sh` — Icarus and Verilator runner.

The production wrapper reuses the imported KF8259 state machines. The master
cascade ID is registered between the two normalized INTA transactions because
the imported block exposes a historical combinational cascade path that can
livelock Icarus; Verilator exercises the real cascaded production wrapper.
Icarus uses the documented portable reference model for the same boundary and
also performs a production-wrapper compile-only check.

## Acceptance

Run from the repository root:

```sh
bash scripts/test_a3_interrupts.sh
```

The passing run reports `A3_AT_PIC_PASS` for the portable and production paths,
`A3_AT_NMI_PASS` in both simulators and `A3_INTERRUPT_TEST_PASS`.

## Boundary

The AT PIC and NMI units are registered in the Quartus integration QIP but are
not wired into the active XT-derived top level. This milestone therefore
proves the device-side contract and hardware-like interrupt trace, not an AT
BIOS boot or a physical-board result. IRQ source routing beyond the explicit
16-bit test boundary and NMI synchronization across a separate clock domain
remain A5/board integration work.
