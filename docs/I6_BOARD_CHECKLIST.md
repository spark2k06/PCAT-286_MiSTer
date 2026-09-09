# I6 physical-board checklist

I6 is prepared but pending. No physical MiSTer board was available or
authorized during I0-I5, so this document is a repeatable procedure rather than
a hardware result.

## Required files

- `releases/PCAT-286_20260909.rbf`
- `tests/firmware/pcat286_event_diag.rom`
- a legally obtained EGA option ROM accepted by the inherited core

Verify the RBF and diagnostic ROM against the hashes in
`docs/I5_FPGA_BUILD.md` and `docs/I4_TEST_RESULTS.md` before loading them.

## Loading procedure

1. Copy the RBF into the MiSTer `Computer` core directory.
2. Start PCAT-286 and open **System & BIOS**.
3. Load `pcat286_event_diag.rom` into **PCAT Main/Diagnostic ROM** (slot 0).
4. Load the EGA ROM into **EGA BIOS** (slot 3). The machine deliberately
   remains in reset while either required ROM is absent.
5. Leave **XT Bus Pace** at 4.77 MHz for the first run, select **Reset & apply
   settings**, and observe the LEDs for at least five seconds.
6. Repeat at 7.16 MHz, 9.54 MHz and Max. These choices pace the XT bus and do
   not select historical SPK286 CPU timing profiles.

## Expected observation

The ROM emits `70h, 72h, 71h, 86h` to port `80h`. The passive hardware monitor
then asserts the disk LED. Any write to diagnostic port `81h`, or a CPU/bridge
protocol fault, asserts the user LED. The monitor never supplies READY and
cannot make a failing transfer pass.

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
| Display/OSD remains usable | Pending |
| Repeated cold and warm resets | Pending |

If possible, also capture the port `80h` sequence with SignalTap or an external
logic analyzer. Such a capture is useful evidence but is not a substitute for
recording the exact RBF and ROM hashes.

## Scope boundary

Do not substitute a production BIOS boot, CheckIt, DOS or protected-mode tests
for this diagnostic. Those are later compatibility work. A production BIOS
failure does not invalidate a passing diagnostic, and no PC/AT or
cycle-accurate speed claim follows from I6.
