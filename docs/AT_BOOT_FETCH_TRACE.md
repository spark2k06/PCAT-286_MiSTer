# AT first-fetch hardware recorder

The AT profile now contains a passive recorder for the first 32 native CPU
code-read transactions after the most recent CPU reset. An aligned CPU word
normally contains two serialized backend byte reads. The entry is committed
only on the actual CPU `bus_valid && ready` edge, with the word accepted by
the CPU on that edge. Backend READY alone does not commit it.

The recorder has no output connected to CPU execution, reset, READY, HOLD,
arbitration, SDRAM or device control. Its 32 x 256-bit array has synchronous
read and one write per completed CPU fetch. Reset invalidates the count and
discards an incomplete entry without clearing the RAM. After 32 completions
the array freezes. Yosys `proc; memory_dff; memory_collect` recognizes one
`$mem_v2` and merges the output register into the memory read port; this is an
inference check, not Quartus placement/timing sign-off.

## OSD controls

In **System & BIOS**, enable **SPK286 Debug** and **Boot Fetch Trace**.
The latter selects the trace page automatically.

| Option | Status bits | Meaning |
| --- | --- | --- |
| SPK286 Debug | 71 | Existing overlay enable, unchanged |
| Debug Page | 73:72 | Existing page selection when Boot Fetch Trace is Off |
| Boot Fetch Index | 78:74 | Entry 0 through 31; menu labels are decimal |
| Boot Fetch Trace | 79 | Select the boot recorder instead of the rolling trace |
| Boot Fetch View | 80 | Address = 0; Data = 1 |

The visible header and all data use hexadecimal: menu index 31 appears as
`IDX:1F`, and 32 completed entries appear as `COUNT:20`. `FULL` means 32
entries have completed. `WAIT` means a CPU code fetch is currently pending.
`VALID` means the selected entry is a completed record or the current
incomplete record.

If the very first read never completes, select index 00: `COUNT:00 WAIT:1
VALID:1` exposes a registered snapshot of the pending transaction. Its
response flag CPU_RDY is zero, so its CPU data word is not an accepted value.
For a later stalled fetch, select index equal to COUNT. Owner flags in this
pending view are live snapshots. Unwritten indices produce `VALID:0` and
zero words. Data/Address selection and entry selection never rearm capture.

Cold/OSD reset, splash hold and an 8042 CPU reset invalidate and rearm this
recorder. Thus a later 8042 reset replaces the earlier boot sequence. This
mode deliberately captures the first reads after the most recent reset.
The memory port uses the same CPU reset to cancel unaccepted CPU records
and drain accepted records without returning stale data; see
[AT_CPU_RESET_MEMORY_BOUNDARY.md](AT_CPU_RESET_MEMORY_BOUNDARY.md).

## Address view (VIEW:0)

Each row is a raw eight-digit hexadecimal word. No bits are converted to
the old XT address/data/status trace representation.

| Row | Bits | Meaning |
| --- | --- | --- |
| T0 | 31:24 | Start flags: `{CPU_VLD, CPU_RDY, RST, HLT, CPU_STATUS[3:0]}` |
| T0 | 23:0 | Native CPU physical byte address |
| T1 | 31:24 | Response flags, described below |
| T1 | 23:0 | KFSDRAM physical word address at first accepted backend command |
| T2 | 31:16, 15:0 | CS and architectural IP when the CPU request became visible |
| T3 | 31:16 | Exact 16-bit word accepted by CPU at CPU READY |
| T3 | 15:0 | Clocks from request observation to CPU READY; saturates at FFFF |

Response flag byte, from bit 7 to bit 0:

| Bit | Meaning |
| --- | --- |
| 7 | CPU READY on completion; zero for a pending snapshot |
| 6 | Backend read-data-valid observed |
| 5 | Backend READY observed |
| 4 | KF read_request observed at backend acceptance |
| 3 | At least one KF read_flag/data sample observed |
| 2 | Backend response word differed from the most recent KF sample |
| 1:0 | Number of KF samples, saturated at 3; normally 2 for an aligned word |

The start RST flag is necessarily zero for a captured request because reset
discards pending capture and prevents arming. During the splash the ordinary
CPU debug page shows actual reset, including the CPU-local 8042 source.

For an aligned first fetch with two ordinary SDRAM samples, the expected
address-side pattern is:

```text
T0:8DFFFFF0
T1:FA07FFF8
T2:F000FFF0
T3:WWWWLLLL
```

`WWWW` must match the little-endian word from ROM offsets FFF0/FFF1, and
`LLLL` is the observed latency rather than a fixed expected value. A BIOS
whose first bytes are EA 12 must produce `WWWW=12EA`. This example does not
claim that all BIOS images begin with those bytes.

## Data view (VIEW:1)

| Row | Bits | Meaning |
| --- | --- | --- |
| T0 | 31:24 | Decoder opcode snapshot when the CPU request became visible |
| T0 | 23:0 | Hidden CS base at the same time |
| T1 | 31:16, 15:0 | First and last KF data_out captured with KF read_flag |
| T2 | 31:8 | First backend physical byte address, before owner ROM alias/word mapping |
| T2 | 7:6, 5:4 | First and last backend byte enables (`01` low, `10` high) |
| T2 | 3:0 | Owner flags at last KF sample; live owner flags for a pending entry |
| T3 | 31:30, 29:28 | DQM at first and last SDRAM READ command |
| T3 | 27:26, 25:24 | DQM at first and last KF read_flag sampling boundary |
| T3 | 23:16 | Decoder opcode snapshot on CPU completion/current pending snapshot |
| T3 | 15:0 | Clocks from CPU request observation to first KF sample |

DQM fields use `{UDQM, LDQM}` and are active high. Normal reads should show
`00` at all four captured boundaries. Owner flags are the actual packed
`{active_q, response_pending_q, owner_refresh_q, kf_idle}` signals, not an
invented CPU bus-state number. The normal first-read base is FF0000 and the
first backend address is FFFFF0; the owner maps that to word 07FFF8.

For aligned code reads, the CPU's accepted low byte should equal the low
byte of the first KF sample and the accepted high byte should equal the
high byte of the last KF sample. Because reads enable both DQ lanes, both
KF samples should normally contain the same SDRAM word. Recording them
separately exposes unstable or incorrect data across the two transactions.
The mismatch flag compares backend data with KF data; it does not itself
validate CPU lane assembly. The integrated first-fetch test checks assembly.

The opcode fields are decoder snapshots contemporaneous with the observed
fetch. Prefetch runs ahead of instruction execution: these fields are not a
promise that the recorded word has already been decoded. The accepted CPU
word is the authoritative stream datum. Instruction decode provenance still
requires CPU queue-consumption/opcode-dispatch signals in simulation or a
SignalTap capture, especially for a byte prefetched before a branch flush.

## Hardware capture procedure

Use a separately named future diagnostic RBF after timing/SDRAM constraints
have been checked. This recorder has been simulated; it is not present in
the previously tested `at_sdram_word_address_AT_FAST` release file.

1. Record the exact system BIOS filename and SHA-256, and its bytes at ROM
   offsets FFF0 through FFFF.
2. Enable the overlay and Boot Fetch Trace. Reset through OSD. During splash
   verify reset on the ordinary CPU page if needed, then return to the boot
   trace. The first fetch is retained automatically even if viewed later.
3. Capture both Address and Data views for index 00. Include the header.
4. Capture both views for indices 01 through at least 0F (menu 00 through 15).
   If COUNT stops earlier with WAIT=1, also capture the index equal to COUNT.
5. Repeat with splash disabled and after a new cold boot. Do not infer an
   opcode from an unqualified changing live data bus.

If Address view already matches FFFFF0 / 07FFF8 / F000:FFF0 but the CPU
word differs from the ROM, compare the first/last KF samples and DQM fields.
If KF samples are correct but CPU data is wrong, inspect backend/bridge lane
assembly. If CPU data is correct, continue to the next recorded fetch and
capture queue consumption, opcode dispatch and exception-vector reads to
locate the first architectural divergence.

Tests: `scripts/test_at_boot_trace.sh` checks pending observability, sample
and CPU-response alignment, data-valid without READY, non-code filtering,
full-buffer freeze and reset discard in Icarus and Verilator. The existing
`scripts/test_debug_overlay.sh` now checks normal XT rendering and AT raw
records/header in both simulators. Neither test substitutes for SDRAM pin
timing or whole-board validation.
