# CPU reset and retained AT memory ownership

The CPU/AT bridge use CPU-local reset (splash/OSD/8042), while the physical
SDRAM and HPS loader must remain alive. Previously the serialized MiSTer
memory port had only the global RESET input. A CPU request selected before
its backend command was accepted therefore survived CPU reset.

The failing sequence is:

1. The memory port selects a CPU address, for example 012340, with
   `active_q=1` and `accepted_q=0`.
2. CPU-local reset clears the CPU/AT bridge. Its command-valid signal drops,
   but the memory port retains 012340.
3. The new CPU reset-vector request eventually reaches its command phase.
   The old port record supplies the address while the new bridge supplies
   command-valid. Without cancellation, the old access can be accepted as
   the new CPU request.

The regression with the original implementation fails at 170 ns with
`CPU reset did not discard unaccepted address`. This is a reproducible
reset/protocol defect independent of SDRAM address packing and CAS latency.
It does not establish that this precise window occurred in the user's RBF
capture. The original pre-splash CPU run made such a second CPU reset
possible before the displayed boot, and OSD/8042 resets use the same boundary.

## Interface change

`spk286_at_mister_memory_port.cancel_cpu` is driven by the actual AT CPU reset:
`at_machine_reset | at_cpu_reset_request`. The standalone machine regression
ties it low where only global reset is exercised; the BIOS first-fetch test
uses its CPU boot-reset input.

When `cancel_cpu` is high:

- New CPU candidates, CPU command acceptance and CPU response delivery are
  disabled. Cancelled CPU candidates are excluded from collision detection.
- A selected CPU request that has not been accepted is discarded immediately.
- An accepted CPU request stays retained until the physical backend completes.
  A sticky `cpu_cancelled_q` suppresses its response even if the CPU reset
  pulse ends before completion. Its address/control remain stable while it
  drains; it is never relaunched.
- Loader, DMA and refresh records continue normally. Global memory-port reset
  is not extended with boot reset, because that would prevent BIOS loading
  while `main_rom_loaded` is false.

An accepted physical write cannot be undone by CPU reset. The new interface
preserves that fact while ensuring no stale response is returned to the new
CPU execution context. The physical SDRAM owner, address mapping and
read-data capture timing are unchanged by this correction.

## Validation

`scripts/test_at_mister_memory_port.sh` passes in Icarus and Verilator with:

```text
AT_MISTER_MEMORY_PORT_CPU_RESET_PASS preaccept_cancel accepted_drain loader_preserved
AT_MISTER_MEMORY_PORT_PASS
AT_MISTER_MEMORY_PORT_TEST_PASS
```

The new cases verify unaccepted cancellation followed by a new FFFFF0 read,
accepted draining across a one-clock reset with a distinct stale response,
and an active ROM loader while CPU reset is high and residual CPU-valid is
present. The last case also verifies no false collision or new CPU candidate.
Standalone Verilator lint is clean. The check task rejects X/Z conditions
instead of allowing an indeterminate comparison to count as a pass.

Before/after snapshots and actual Icarus outputs are in
`build/at-splash-control/`: `spk286_at_mister_memory_port.before.sv`,
`memory_old_cancel_adapter.sv`, `memory-reset-before-fix-expected-fail.log`,
and `memory-reset-after-fix.log`. The adapter only adds an unused input so the
same regression can run against the unchanged original behavior.
