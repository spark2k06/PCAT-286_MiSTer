# PCAT-286 AT machine integration

`PCAT-286.sv` is the sole machine top and defines `emu_at`. `sys/sys_top.v`
instantiates it when `AT_PROFILE` is enabled; there is no alternate XT top in
the project.

The active hardware path is:

```text
SPK286 CPU/BIU
  -> AT bus bridge and memory decoder
  -> AT machine arbitration
  -> PIC/PIT/DMA/refresh/8042/RTC/CMOS
  -> FDC/XTIDE/EGA and the MiSTer SDRAM/HPS owners
```

The source closure is described by `files.qip` and
`rtl/spk286_integration/spk286_integration.qip`. It retains only the SPK286
CPU, AT integration, EGA, SDRAM, PIC/PIT support and the common floppy/IDE/
debug blocks used by the profile.

ROM images are loaded through the AT HPS ROM loader. The main PCAT BIOS is
mapped at `F0000h`, the EGA BIOS at `C0000h` and the XTIDE image at `EC000h`.
The canonical AT timing file is `SYSTEM.sdc`; the common MiSTer constraints
remain in `sys/sys_top.sdc`.
