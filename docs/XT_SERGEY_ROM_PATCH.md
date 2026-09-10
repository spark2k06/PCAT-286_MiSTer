# Sergey XT BIOS SPK286 test patch

`SW/ROMs/test/xtsergey_mod.rom` is the user-supplied 64 KiB XT Sergey BIOS.
It is preserved unchanged.  The reproducible patch script creates
`SW/ROMs/test/xtsergey_mod_spk286.rom` for a SPK286 bring-up test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/patch_xtsergey_spk286.ps1
```

The patch changes only ROM offset `0xD721`, `75 06` (`JNZ +6`), to `EB 06`
(`JMP +6`).  In the original code this branch selects the warning text
“This CPU does not disable interrupts after loading segment registers!” when
the BIOS probe returns `AX=0001h`.  The patched image skips that print and
leaves the probe, CPU classification, FPU test and the rest of the BIOS
unchanged.

This warning is expected for this BIOS/core combination: the Sergey detector
only distinguishes 8088/V20-family behaviour and does not identify a 286.
Suppressing it is therefore a cosmetic compatibility patch, not a correction
to SPK286 interrupt semantics.  It is not a BIOS adaptation or an RTL change.

The script verifies the original SHA-256 before patching and refuses to
overwrite a different output image.  The generated candidate remains in the
local test-ROM folder, alongside the preserved originals.
