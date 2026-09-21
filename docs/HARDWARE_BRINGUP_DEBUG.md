# SPK286 hardware debug overlay

The core has one compact, passive hardware observer. It is intended for
occasional diagnosis on MiSTer when a BIOS stops with no useful screen.

## Building it

The checked-in release configuration in `config.tcl` contains:

```tcl
set_global_assignment -name VERILOG_MACRO "SPK286_AT_NO_DEBUG"
```

Comment that line to include the compact observer. No other macro is needed.
The **System & BIOS → SPK286 Debug** switch will then appear in the OSD.

The observer samples about 176 state bits, displays one page and has no path
back to the CPU, bridge, READY, HOLD, chipset or memory. A toggle/acknowledge
handshake captures one coherent source-clock snapshot per video frame and
holds it stable while it crosses into the display clock domain. `SYSTEM.sdc`
constrains that payload as an asynchronous mailbox.

## Display fields

`RASTER:N` uses the machine video blanking. `RASTER:F` means that the input
remained blank long enough for the diagnostic fallback raster to be used.
The fallback changes only the final debug video output.

`CS:IP`, `OP`, `UPC`, `BS` and `FLAGS` identify the current CPU execution
point, opcode, microcode address, BIU state and flags. `FB` indicates a blocked
instruction fetch. `RST`, `HLT` and `SHD` report reset, halt and shutdown.

The five error flags are:

- `C`: CPU control error
- `U`: unsupported opcode
- `M`: microcode fault
- `O`: operand blocked
- `B`: bridge protocol or keyboard event overflow

`POST` is the latest port-80 value. The first `RDY` and `VLD` are the CPU
READY and bus-valid inputs.

The `AT` rows show the current 20-bit address, 8288 status, valid, direction,
I/O selection, READY, bridge-idle, HOLD request, data out/in and detailed BIU
state. Status values are `0` INTA, `1` I/O read, `2` I/O write, `3` halt, `4`
code read, `5` memory read, `6` memory write and `7` passive.

`LAST` is the most recently completed AT transfer:

```text
LAST R A:AAAAA D:DD S:S
```

The direction changes to `W` for a write. `SNAP` is an 8-bit wrapping
sequence. Two photographs with different `SNAP` values prove that the values
are current even if the CPU fields themselves have stopped.

## Reading a stopped warm reset

- If `SNAP` changes, the observer and video clock are alive.
- If `RST` remains one, inspect reset ownership before CPU execution.
- If `SHD` or any error flag is one, record the complete page before reset.
- If `CS:IP` and `UPC` remain fixed, use `OP`, `BS`, `FB`, READY and the
  current/last AT transactions to distinguish a CPU wait from a bus wait.
- If `CS:IP` changes while `RASTER:F` is shown, CPU execution continues and
  the failure is likely in BIOS video reinitialisation or the EGA path.
- If `CS:IP` is fixed but `SNAP` advances, the displayed state is a genuine
  stopped point rather than a stale frame.

The observer supplies evidence for diagnosis; it does not prove cycle
accuracy or alter the result of a machine transaction.
