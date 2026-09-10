# Exploratory production-BIOS boot evidence

This note records the first successful user-side run of the SPK286 XT core
with a production BIOS. It is exploratory evidence and does not replace the
formal I6 diagnostic procedure.

## Recorded result

With splash disabled from core start, the valid EGA option ROM loaded, and the
patched Sergey XT BIOS `xtsergey_mod_spk286_nofpu.rom`, the machine reached:

- CPU identification and the normal XT POST summary;
- `Mathematics Co-processor: Absent` without stopping at the 8087 probe;
- EGA/VGA BIOS detection and 640 KiB conventional memory;
- XTIDE option-ROM initialization at `EC00h`;
- floppy boot of an auto-starting Alley Cat disk, including its video screen.

This confirms the practical CPU/XT bridge, ROM, EGA video and floppy paths are
alive far enough to execute a real game. The FPU workaround is BIOS-side: it
does not claim that SPK286 contains an 8087.

## Remaining limitation

The same setup reaches `Starting MS-DOS...` when booting the configured hard
disk image but does not complete that operating-system load. Since the floppy
game boots, this is now isolated to the DOS/XTIDE hard-disk path or the image
contents, not the initial CPU/FPU bring-up. It remains a later compatibility
investigation.

The board model, exact RBF hash and complete I6 diagnostic/LED evidence were
not captured in these screenshots, so I6 remains formally pending.
