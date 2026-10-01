# CHECKNUM: numeric CheckIt reference for DOS

Run `CHECKNUM` from any DOS directory. The generated executable is standalone:
it needs no CheckIt EXE, overlay, configuration, help file or menu navigation.
It runs both measurements once, prints two numeric lines and returns to DOS:

```text
4143
70.9
```

Line 1 is Dhrystones per second, rounded to an integer. Line 2 is **thousands
of Whetstones per second**, rounded to one decimal, matching CheckIt's `K`
display. The example is the original 86Box 286 at 25 MHz, not a constant
embedded in the program. Software floating point is forced even when a
coprocessor is configured. DOS output redirection works:

```dos
CHECKNUM > RESULT.TXT
```

Allow both measurements to finish. Run it from ordinary real-mode DOS with
the same memory managers and machine settings used for the comparison.
The program returns errorlevel 0 on success and 1 on a DOS output error.
Timing uses the original BIOS tick counter; small repeat-run differences and
the original rounding/quantization remain possible.

## Build and integrity check

Python 3 and NASM are required **only to build**. The supplied originals must
be CheckIt **3.03C, 04/08/91**, with these SHA256 values:

| Input | SHA256 |
| --- | --- |
| `CHECKIT.EXE` | `41e261db4393763ca632522f2e1c7a66e4ff7f52cc68ba05a582a894ffd02402` |
| `CHECKIT.OVL` | `ac9e11e77693500dd092dcf54bb68c7206ccd5cecc6a7130ae049f669b933be0` |

From this Windows checkout, using the installed WSL tools:

```powershell
wsl -d Ubuntu-24.04 -- python3 /mnt/d/GitHub/PCAT-286_MiSTer/SW/CHECKNUM/build_checknum.py /mnt/d/ISOs/MiSTer/APPS/CHECKIT /mnt/d/GitHub/PCAT-286_MiSTer/build/checknum/CHECKNUM.EXE
wsl -d Ubuntu-24.04 -- python3 /mnt/d/GitHub/PCAT-286_MiSTer/SW/CHECKNUM/verify_checknum.py /mnt/d/ISOs/MiSTer/APPS/CHECKIT /mnt/d/GitHub/PCAT-286_MiSTer/build/checknum/CHECKNUM.EXE
```

Output: `D:\GitHub\PCAT-286_MiSTer\build\checknum\CHECKNUM.EXE`, **318,272 bytes**,
SHA256 `38324ad68abe13f143ff76dfcdee45f424ff25ce78f67883214ce6b82fa637e6`.
The adjacent `.manifest.json` records the extraction, patches, retained code
hashes and DOS relocations. Generated binaries and supplied CheckIt files are
outside version control; the frontend and reproducible builder are tracked.

## Why these numbers are comparable

This is a new numeric frontend around the supplied compiled routines. It is
not a separately compiled Dhrystone/Whetstone implementation.

- Phoenix overlay 19, containing both benchmark routines, is retained **byte
  for byte**, at its original relative segment addresses.
- The Microsoft runtime, software floating-point library, allocations,
  constants, calibration, measured loops and BIOS-tick reader are retained.
- The original CRT initializes and cleans up the program. The numeric main
  calls Dhrystone at relative `0EC1:000C` and Whetstone at `0F2E:000C`.
- Formatting uses the original `sprintf` and the same Whetstone division by
  1000. Only labels/spacing are removed from the two format strings.
- GUI progress updates and GUI abort-dialog polling outside the timed loops
  are disabled. Runtime NPU detection is bypassed to select software FP.
- DOS MZ relocation entries are rebuilt for the retained resident modules;
  frontend far-call relocations come from NASM labels. No overlay file is
  opened during the measurements.

The focused verifier rebuilds twice, rejects modified inputs, checks MZ
layout and relocations at two load segments, and checks benchmark/timer byte
identity. It does not run a CPU regression suite.

See [the acceptance and performance record](../../docs/CHECKNUM_REFERENCE_20261001.md)
for original CheckIt, native 86Box and MiSTer results. Performance attribution
continues under PERF01; this tool does not change CPU or motherboard RTL.
