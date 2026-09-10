# I6 physical-board checklist

I6 is prepared but pending. Exploratory board runs with an earlier instrumented
candidate showed that a production BIOS did not start and also demonstrated
that splash-time debug values can be misleading. The exact release below has
not yet completed the diagnostic acceptance run, so this document remains a
repeatable procedure rather than a successful hardware result.

## Required files

- `releases/PCAT-286_20260910.rbf`
- `tests/firmware/pcat286_event_diag.rom`
- a legally obtained EGA option ROM accepted by the inherited core

Verify the RBF and diagnostic ROM against the hashes in
`docs/I5_FPGA_BUILD.md` and `docs/I4_TEST_RESULTS.md` before loading them.

## Loading procedure

1. Copy the RBF into the MiSTer `Computer` core directory.
2. Before the first recorded run, set **Boot Splash Screen** to **No**, leave
   it persisted, restart the core, and keep that setting for all captures.
   Start directly in this state: do not begin with the splash enabled and then
   turn it off. This is the reference configuration for the current bring-up
   so no field can be confused with a splash-time snapshot.
3. Open **System & BIOS**.
4. Load `pcat286_event_diag.rom` into **PCAT BIOS** (slot 0).
5. Load the EGA ROM into **EGA BIOS** (slot 3). The machine deliberately
   remains in reset while either required ROM is absent.
6. Leave **XT Bus Pace** at 4.77 MHz for the first run, enable **SPK286
   Debug**, select the **CPU** page, then select **Reset & apply settings**.
   Photograph two CPU-page states with different `SNAP` values.
7. Visit the **Registers**, **Bus** and **Trace** pages without resetting and
   photograph each page. The overlay is observational and does not pause the
   machine.
8. Repeat at 7.16 MHz, 9.54 MHz and Max. These choices pace the XT bus and do
   not select historical SPK286 CPU timing profiles.

## Expected observation

`SNAP` must change between captures; otherwise the remaining values may be a
stale observation. `RASTER:N` means the overlay is using normal video timing,
while `RASTER:F` records that the splash-off fallback active window was needed.
The CPU page must then show changing `CS:IP`, opcode, microcode PC and non-zero
CPU/XT completion counters. The trace page retains the four most recently
accepted XT transactions and the latest port-80 value. The ROM emits `70h,
72h, 71h, 86h` to port `80h`; the passive diagnostic monitor then asserts the
disk LED. Any write to diagnostic port `81h`, or a CPU/bridge protocol fault,
asserts the user LED. Neither the overlay nor the LED monitor supplies READY
or can make a failing transfer pass.

Record for each pace setting:

| Field | Result |
| --- | --- |
| MiSTer board/revision and SDRAM module | Pending |
| MiSTer framework version | Pending |
| RBF SHA-256 | Pending confirmation |
| Diagnostic ROM SHA-256 | Pending confirmation |
| EGA ROM identity/hash | Pending |
| Disk LED reaches PASS | Pending |
| User LED remains clear | Pending |
| SNAP changes; RASTER N/F recorded | Pending |
| CPU page: final CS:IP/opcode/uPC/BIU state | Pending |
| CPU/XT completion counters | Pending |
| Registers page photograph | Pending |
| Bus page photograph | Pending |
| Trace page: four rows and latest POST value | Pending |
| Display/OSD remains usable | Pending |
| Repeated cold and warm resets | Pending |

The field definitions and XT status legend are in
`docs/HARDWARE_BRINGUP_DEBUG.md`. If possible, also capture the port `80h`
sequence with SignalTap or an external logic analyzer. Such a capture is useful
evidence but is not a substitute for recording the exact RBF and ROM hashes.

## Scope boundary

Do not substitute a production BIOS boot, CheckIt, DOS or protected-mode tests
for this diagnostic. Those are later compatibility work. A production BIOS
failure does not invalidate a passing diagnostic, and no PC/AT or
cycle-accurate speed claim follows from I6.
