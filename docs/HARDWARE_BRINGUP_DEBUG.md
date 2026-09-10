# SPK286 hardware bring-up overlay

The **System & BIOS → SPK286 Debug** option enables a passive four-page
display. **Debug Page** selects CPU, Registers, Bus or Trace. The selection
changes only during vertical blank, following the method used by PCXT's
`test/crtc-debug` branch, so enabling the display does not tear the video
output.

The reproducible bring-up configuration uses **Boot Splash Screen = No** from
core start. If the machine video path remains completely blank, a watchdog
aligns a diagnostic-only active window to the existing HS/VS timing so the
overlay remains visible. `RASTER:N` means normal machine blanking is in use;
`RASTER:F` means this fallback is active. It changes only the final debug video
selection and has no path into the emulated machine.

The overlay has no path back to SPK286, the bridge, READY, HOLD, the chipset or
memory. Source-domain counters and trace registers only sample completed
transactions. A toggle/acknowledge handshake captures one coherent
source-domain snapshot per video frame and holds its wide data stable while it
crosses into the display domain. The source observer has a hard-reset input
separate from the CPU reset, so it continues to report `cpu_reset=1` instead
of freezing the last pre-reset state. This cannot alter machine execution.

Every page includes `SNAP:xx`. This 8-bit wrapping sequence increments for
each acknowledged snapshot. Two captures with different `SNAP` values prove
that the displayed machine fields are current even if all CPU/bus counters
remain unchanged.

## Pages

### CPU

This page shows `CS:IP`, the hidden CS base, current opcode, microcode PC,
SPK286 BIU state, FLAGS, last event vector/kind, reset/halt/shutdown/event
flags, five fault indicators, completed CPU and XT transfer counters, latest
port-80 value, READY and CPU bus-valid.

The error abbreviations are `C` control error, `U` unsupported opcode, `M`
microcode fault, `O` operand blocked and `B` bridge protocol error. A counter
is a wrapping 16-bit observation, not a performance counter.

### Registers

This page shows all eight general registers in SPK286's documented x86 order
(`AX,CX,DX,BX,SP,BP,SI,DI`), all four segment selectors
(`ES,CS,SS,DS`), `IP`, FLAGS and the hidden CS base.

### Bus

This page shows the live 24-bit SPK286 address, data out/in, raw BIU status and
control flags, followed by the projected 20-bit XT address, byte data out/in,
8288 status and bridge control flags. `HI` is the selected high byte of a
serialized word and `MAP` records projection of a physical address into the
retained 1 MiB XT map.

### Trace

Rows 0–3 are the four most recently accepted XT transactions, newest first.
Each row is captured only when the chipset asserts READY and contains:

```text
R/W A:AAAAA D:DD S:S
```

`R/W` is direction, `A` the 20-bit projected address, `D` the byte transferred
and `S` the 8288 status. Status values are `0` INTA, `1` I/O read, `2` I/O
write, `3` halt, `4` code read, `5` memory read, `6` memory write and `7`
passive. No arbitrary RAM read is performed: “memory observation” means this
accepted-transfer history, which is safe for hardware bring-up.

## Interpreting a failed boot

- `SNAP` changes while counters stay at zero and reset remains asserted:
  confirm both required ROM slots and reset/loader ownership.
- `SNAP` does not change: treat every other field as stale and inspect the
  debug capture path before diagnosing the CPU.
- CPU counter changes but XT remains zero: inspect BIU state, CPU status and
  bridge error.
- XT changes and trace contains reset code reads near `FFFF0`, but `CS:IP`
  never leaves the reset window: inspect returned ROM bytes and READY.
- `CS:IP` reaches `F000:E...` and port-80 advances: CPU/ROM execution is alive;
  use the last trace rows to identify the peripheral or memory access where it
  stops.
- Any error bit at one: record all four pages before resetting.

The overlay is diagnostic evidence, not proof of cycle accuracy or physical
validation. I6 still requires the exact RBF/ROM hashes, board details, repeated
resets and the project diagnostic result.

The raster, page, register/trace extraction, clock-domain handshake and
font/RGB latency are reproducibly tested with:

```sh
bash scripts/test_debug_overlay.sh
```

The command runs the same test under both Icarus and Verilator and includes a
fully blank upstream-raster case matching splash-off board bring-up.
