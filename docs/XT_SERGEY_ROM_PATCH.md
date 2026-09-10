# Sergey XT BIOS SPK286 test patch

`SW/ROMs/test/xtsergey_mod.rom` is the user-supplied 64 KiB XT Sergey BIOS.
It is preserved unchanged.  The reproducible patch script creates
`SW/ROMs/test/xtsergey_mod_spk286.rom` for a warning-free SPK286 bring-up test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/patch_xtsergey_spk286.ps1
```

The patch changes only ROM offset `0xD721`, `75 06` (`JNZ +6`), to `EB 06`
(`JMP +6`).  In the original code this branch selects the warning text
“This CPU does not disable interrupts after loading segment registers!” when
the BIOS probe returns `AX=0001h`.  The patched image skips that print and
leaves the probe, CPU classification, FPU test and the rest of the BIOS
unchanged.

The FPU probe can be bypassed for the current SPK286 build, which does not
implement the 8087 ESC instructions used by this BIOS.  This creates the
candidate to use for the blocked-coprocessor case:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/patch_xtsergey_spk286.ps1 -BypassFpu
```

That variant is written as `SW/ROMs/test/xtsergey_mod_spk286_nofpu.rom`.
It additionally replaces `FNINIT` at `0xD752` (`DB E3`) and `FNSTCW
word [03FEh]` at `0xD763` (`D9 3E FE 03`) with same-length NOPs.  The BIOS
then takes its normal “no coprocessor” path, prints `Not Present`, and
continues booting without claiming that an 8087 is installed.

This is a BIOS-side compatibility workaround, not an implementation of an
8087 and not an RTL correction.  A future FPU task can replace it with an
actual ESC/FPU path.

This warning is expected for this BIOS/core combination: the Sergey detector
only distinguishes 8088/V20-family behaviour and does not identify a 286.
Suppressing it is therefore a cosmetic compatibility patch, not a correction
to SPK286 interrupt semantics.  It is not a BIOS adaptation or an RTL change.

The script verifies the original SHA-256 before patching and refuses to
overwrite a different output image.  The generated candidate remains in the
local test-ROM folder, alongside the preserved originals.
