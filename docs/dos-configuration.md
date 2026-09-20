# DOS configuration reference

The files in [`hdd/`](../hdd/) are a working reference for a DOS installation
that uses the PCAT-286 core's current memory and audio layout. They are not
required by the RTL, but they keep the DOS drivers, the OSD and software
detection in agreement.

## Matching OSD settings

The supplied configuration expects these core options:

- **Hardware → UMB E000-EFFF: Enabled** exposes 64 KiB at
  `E0000h-EFFFFh`.
- **Hardware → 2MB EMS D000-DFFF: Enabled** exposes the four 16 KiB EMS
  page-frame banks at `D0000h-DFFFFh`. The backing store is up to 2 MiB and
  the Lo-tech-compatible page registers are at port `260h`.
- **Audio & Video → C/MS Audio: Enabled** exposes the C/MS pair at `220h`.
- **Audio & Video → OPL2: Adlib 388h** exposes the OPL2 at `388h`; the second
  OSD choice also enables its `228h` FM alias.
- **Audio & Video → Tandy Sound: Enabled** exposes the SN76489 at `0C0h-0CFh`.
- **Hardware → MPU-401: Enabled** exposes the UART-mode MPU-401 at `330h/331h`
  and routes its interrupt through AT IRQ9 (the IRQ2 cascade remains reserved
  for the slave PIC).
  Reset and UART-entry `FEh` acknowledgements are polled through `331h/330h`;
  the adapted AT BIOS leaves IRQ9 masked until a MIDI driver installs its
  handler, and IRQ9 is then reserved for received MIDI bytes.
  With **USER I/O → MIDI**, it connects to an external MT32-pi; **COM2** uses
  the same USER I/O connector for the standard UART at `2F8h-2FFh`.
- The MT32-pi page keeps the source choices for MT-32/General MIDI mode,
  ROM, SoundFont, reset and the optional external bridge.

Sound Blaster DSP, DMA, IRQ and its OSD selection are intentionally not part
of this AT profile. C/MS, OPL2 and Tandy are core hardware and require no DOS
driver or environment variable. MPU-401 UART mode is the MIDI transport; the
MT32-pi itself remains external hardware connected through USER I/O.

The core reserves `C8000h-C9FFFh` for the AT XTIDE option ROM. The rest of
`C4000h-CFFFFh` is option-ROM space, while `D0000h-DFFFFh` belongs to the EMS
page frame when enabled. `E0000h-EFFFFh` is the separate, optional UMB window.

## CONFIG.SYS

The checked-in [`hdd/CONFIG.SYS`](../hdd/CONFIG.SYS) is:

```dos
FILES=40
BUFFERS = 30
DOS = HIGH, UMB
DEVICE=C:\UTIL\USE!UMBS.SYS E000-F000
DEVICE=C:\UTIL\DOSMAX\DOSMAX.EXE /R+ /N+ /P-
DEVICEHIGH=C:\UTIL\LTEMM.EXE /p:D000 /x /n
SHELL=C:\UTIL\DOSMAX\SHELLMAX.COM C:\COMMAND.COM C:\ /E:256 /P
```

`USE!UMBS.SYS` uses an end-exclusive upper segment: `E000-F000` registers
exactly `E0000h-EFFFFh`. This is independent of the EMS page frame at
`D0000h-DFFFFh`.

`DOSMAX.EXE` and `SHELLMAX.COM` move DOS data and the command interpreter's
overhead into that UMB. `LTEMM.EXE /p:D000` registers the core's fixed EMS
page frame; no `/i:` argument is needed because `260h` is already LTEMM's
default I/O port.

If UMB or EMS is disabled in the OSD or temporarily with AT286CTL, remove or
comment the matching driver line for that boot. A DOS driver cannot create a
memory device that the core has taken off the bus.

## AUTOEXEC.BAT and built-in audio

[`hdd/AUTOEXEC.BAT`](../hdd/AUTOEXEC.BAT) provides this starting point:

```bat
@ECHO OFF
SET PATH=C:\UTIL;%PATH%
C:\UTIL\CTMOUSE\CTMOUSE.EXE
```

The built-in devices are selected by their OSD options or by the per-program
`AT286CTL` overrides; no `BLASTER`, `SOUND` or `MIDI` variable configures them.

The final line in the supplied example starts CuteMouse. It probes PS/2 first
and then the serial ports, so the core's COM1 mouse normally needs no command
line switches. See [`hdd/CTMOUSE/CTMOUSE.TXT`](../hdd/CTMOUSE/CTMOUSE.TXT)
for explicit port, IRQ and protocol options.

## Per-program profiles

AT286CTL rewrites its complete override register set on every invocation. A
batch file should therefore name every override that program needs, then use
`AT286CTL reset` on exit:

```bat
@ECHO OFF
AT286CTL 4.77 adlib cms tandy joy1=digital
GAME.EXE
AT286CTL reset
```

Anything not named remains under OSD control. These overrides apply
immediately and do not require a matching machine reset. CPU Type, the EGA
monitor profile and the second SD-card mapping remain OSD-only because the core
samples them during reset.

## MiSTer.ini example for a 31 kHz analogue display

For a VGA monitor that should receive scaler output rather than the core's
native 15 kHz EGA raster, add a core-specific section to `MiSTer.ini`:

```ini
[PCXT-EGA]
vga_scaler=1
video_mode=6
vsync_adjust=2
```

MiSTer matches `[PCXT-EGA]` against the name embedded in the core, so the
settings do not affect other cores. Mode 6 is the built-in 640×480,
25.175 MHz preset. `vsync_adjust=2` follows the core's approximately 59.917 Hz
refresh and avoids periodic repeated frames, but the result is non-standard;
use `vsync_adjust=1` if a flat panel rejects it. Do not enable `vga_scaler`
when the intention is to use the core's direct 15 kHz CRT output.
