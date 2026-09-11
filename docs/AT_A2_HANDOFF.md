# AT A2 handoff

## Delivered

- `rtl/spk286_integration/spk286_at_memory_decode.sv` — complete 24-bit
  profile-range classification and ROM-write policy.
- `rtl/spk286_integration/spk286_at_arbiter.sv` — CPU/DMA/refresh/loader
  ownership with HOLD/HLDA gating and protected-interval exclusion.
- `sim/spk286_integration/spk286_at_memory_decode_tb.sv` — boundary and
  cycle-class decode checks.
- `sim/spk286_integration/spk286_at_arbiter_tb.sv` — grant, retention,
  priority, LOCK/HOLD exclusion and reset-loader checks.
- `scripts/test_a2_memory_arbiter.sh` — Icarus and Verilator runner.

## Acceptance

Run from the repository root:

```sh
bash scripts/test_a2_memory_arbiter.sh
```

The passing run reports `A2_MEMORY_DECODE_PASS`, `A2_ARBITER_PASS` and
`A2_MEMORY_ARBITER_TEST_PASS` in both simulators.

## Boundary

These are standalone A2 contract units. They are registered in the Quartus
integration QIP but are not yet wired into the active XT-derived top level.
No physical RAM, PIC, DMA channel state, refresh cadence, A20 gate or AT BIOS
behaviour is claimed. A3 must connect real device-side transaction ownership
and dual-PIC interrupt acknowledgement to this boundary.
