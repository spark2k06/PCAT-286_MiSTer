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

The ordinary observer configuration keeps SPK286 and the AT chipset at
50 MHz and shows `SPK286 MIN DEBUG`. For the slower timing diagnostic, also
enable this line in `config.tcl`:

```tcl
set_global_assignment -name VERILOG_MACRO "SPK286_AT_DEBUG_CPU_DIV2"
```

That mode runs only SPK286 at 25 MHz while the chipset, memory pipeline and
SDRAM remain at 50 MHz, and shows `SPK286 MIN DEBUG /2`. It gives the CPU
execution datapath a real 40 ns cycle without treating `execute_enable` as a
clock enable. It is intended for diagnosis rather than normal use.

The observer samples about 240 state bits, displays one page and has no path
back to the CPU, bridge, READY, HOLD, chipset or memory. A toggle/acknowledge
handshake captures coherent source-clock snapshots from a display-clock
timer and holds each one stable while it crosses into the display clock
domain. The timer is independent of machine vertical blanking, so BIOS video
reinitialisation cannot leave a stale CPU snapshot on screen. `SYSTEM.sdc`
constrains the payload as an asynchronous mailbox.

## Display fields

`RASTER:N` uses the machine video blanking. `RASTER:F` means that the input
remained blank long enough for the diagnostic fallback raster to be used.
The fallback changes only the final debug video output.

`CS:IP`, `OP`, `UPC`, `BS`, `FLAGS` and `CX` identify the current CPU
execution point, opcode, microcode address, BIU state, flags and loop counter.
`FB` indicates a blocked instruction fetch. `RST`, `HLT` and `SHD` report
reset, halt and shutdown. `RET` is a wrapping count of retired instructions;
if it changes while `CS:IP` repeats, the CPU is executing a live loop.

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
state. The compact `S` field keeps the low three bits of the internal cycle
class: `0` is INTA, `1` I/O read, `2` I/O write, `5` memory or code read and
`6` memory write.

`IRQ8`, `INT` and `HLDA` expose the RTC interrupt input, the combined PIC
interrupt output and the CPU bus acknowledgement. `DMA:r/g` and `REF:r/g`
show request/grant pairs. `BR` is the bridge state (`0` idle, `1` snapshot,
`2` decode, `3` address, `4` command, `5` wait and `6` complete). State `7`
is the CPU-clock alignment stage used only by the optional `/2` mode. `DV` is
the read-data-valid input used together with AT READY to complete a read.

The final two rows expose the MiSTer memory pipeline. `MP` contains the memory
port active/accepted/owner/cancelled fields. `BF` contains the P03 buffer state
(`0` idle, `1` hit, `2` bypass, `3` fill), physical-inflight and cancelled
fields. `SD` contains SDRAM-owner active/write/response-pending. `K` is the
KFSDRAM idle signal and `F` packs its write/read/refresh flags.

`LAST` is the most recently completed AT transfer:

```text
LAST R A:AAAAA D:DD S:S
```

The direction changes to `W` for a write. `SNAP` is an 8-bit wrapping
sequence. Two photographs with different `SNAP` values prove that the values
are current even if the CPU fields themselves have stopped.

## Reading a stopped warm reset

- If `SNAP` changes, the observer's source and display clocks are alive.
- If `RST` remains one, inspect reset ownership before CPU execution.
- If `SHD` or any error flag is one, record the complete page before reset.
- If `CS:IP` and `UPC` remain fixed, use `OP`, `BS`, `FB`, READY and the
  current/last AT transactions to distinguish a CPU wait from a bus wait.
- If `CS:IP` repeats but `CX` or `RET` changes, execution is still progressing.
- If `BR=5` and AT READY is one but `DV` remains zero, the bridge is waiting
  for valid read data rather than for READY.
- If HOLD is one, the DMA/REF request and grant pairs show its source and
  whether the CPU has handed over the bus through `HLDA`.
- If `IRQ8` rises without `INT`, inspect slave-PIC masking/cascade; if both
  rise while `RET` remains fixed, inspect interrupt acknowledgement/entry.
- If `CS:IP` changes while `RASTER:F` is shown, CPU execution continues and
  the failure is likely in BIOS video reinitialisation or the EGA path.
- If `CS:IP` is fixed but `SNAP` advances, the displayed state is a genuine
  stopped point rather than a stale frame.

The observer supplies evidence for diagnosis; it does not prove cycle
accuracy or alter the result of a machine transaction.
