# DOS configuration reference

The files in [`hdd/`](../hdd/) are a working reference for a DOS installation
that uses the PCAT-286 core's current memory and audio layout. They are not
required by the RTL, but they keep the DOS drivers, the OSD and software
detection in agreement.

## Matching OSD settings

The supplied configuration expects these fixed memory windows:

- UMB RAM is always mapped at `C8000h-DFFFFh` (96 KiB).
- The EMS page frame is always present at `E0000h-EFFFFh`, split into four
  16 KiB windows. The backing store is 2 MiB and the Lo-tech-compatible page
  registers are at port `260h`.
- **Audio & Video → Audio 220h: C/MS** exposes the C/MS pair at `220h`.
  Select **Sound Blaster** instead to use the SB Pro DSP and mixer at that
  address. The two devices share ports and are mutually exclusive.
- **Hardware → Sound Blaster IRQ: 5** selects IRQ5 (the default); IRQ7 is
  also available. Sound Blaster uses 8-bit DMA channel 1.
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
- The MiSTer mouse appears as a Microsoft-compatible serial mouse on **COM1**
  (`3F8h-3FFh`, IRQ4). Its PS/2 link is internal to the core; DOS should load
  a serial mouse driver such as the supplied CuteMouse.
- The MT32-pi page keeps the source choices for MT-32/General MIDI mode,
  ROM, SoundFont, reset and the optional external bridge.

The AT profile builds Sound Blaster Pro support with `ENABLE_SB=1` in
`config.tcl`. Select it through Audio 220h before using a Sound Blaster driver.
C/MS, OPL2 and Tandy require no DOS driver or environment variable.
MPU-401 UART mode is the MIDI transport; the
MT32-pi itself remains external hardware connected through USER I/O.

The EGA BIOS remains in `C0000h-C7FFFh`. The AT profile has no XTIDE ROM slot;
`C8000h-DFFFFh` is always UMB RAM and `E0000h-EFFFFh` is always the EMS page
frame. The UMB and EMS windows cannot be disabled through the OSD or AT286CTL.

## CONFIG.SYS example with UMB and EMS drivers

The checked-in [`hdd/CONFIG.SYS`](../hdd/CONFIG.SYS) stays minimal. For a DOS
installation with UMB and EMS managers, a suitable configuration is:

```dos
FILES=40
BUFFERS = 30
DOS = HIGH, UMB
DEVICE=C:\UTIL\USE!UMBS.SYS C800-E000
DEVICE=C:\UTIL\DOSMAX\DOSMAX.EXE /R+ /N+ /P-
DEVICEHIGH=C:\UTIL\LTEMM.EXE /p:E000 /x /n
SHELL=C:\UTIL\DOSMAX\SHELLMAX.COM C:\COMMAND.COM C:\ /E:256 /P
```

`USE!UMBS.SYS` uses an end-exclusive upper segment: `C800-E000` registers
exactly `C8000h-DFFFFh`. This is independent of the EMS page frame at
`E0000h-EFFFFh`.

`DOSMAX.EXE` and `SHELLMAX.COM` move DOS data and the command interpreter's
overhead into that UMB. `LTEMM.EXE /p:E000` registers the core's fixed EMS
page frame; no `/i:` argument is needed because `260h` is already LTEMM's
default I/O port. These driver paths are an example and are not part of the
minimal files under `hdd/`.

## AUTOEXEC.BAT and built-in audio

[`hdd/AUTOEXEC.BAT`](../hdd/AUTOEXEC.BAT) provides this starting point:

```bat
@ECHO OFF
SET PATH=C:\UTIL;%PATH%
C:\UTIL\CTMOUSE\CTMOUSE.EXE /S14 /Y
```

The built-in devices are selected by their OSD options or by the per-program
`AT286CTL` overrides. For Sound Blaster programs, add this line to AUTOEXEC.BAT
when using the default IRQ5:

```bat
SET BLASTER=A220 I5 D1 T4
```

Use `I7` if the effective Sound Blaster IRQ is 7. `T4` identifies Sound
Blaster Pro. The variable tells DOS software where to find the device; it
does not change the core's OSD or AT286CTL settings.

The final line in the supplied example starts CuteMouse. Install the supplied
[`CTMOUSE`](../hdd/CTMOUSE/) directory at `C:\UTIL\CTMOUSE` or adjust the
path. `/S14` selects BIOS COM1 with IRQ4, while `/Y` prevents CuteMouse from
installing in Mouse Systems mode without detecting a mouse, which would show
a cursor even though movement is unavailable. The BIOS must enumerate COM1
at `03F8h`; the corrected AT machine decoder exposes that address. See
[`hdd/CTMOUSE/CTMOUSE.TXT`](../hdd/CTMOUSE/CTMOUSE.TXT) for explicit port, IRQ
and protocol options.

### Sound Blaster detection check

With **Audio 220h: Sound Blaster** selected, start DOS `DEBUG` and enter
these commands individually (numbers are hexadecimal):

```text
o 226 1
o 226 0
i 22e
i 22a
i 22e
i 22c
q
```

The four reads should return **FF, AA, 7F, 7F**: a pending DSP reset reply,
the `AA` reply itself, an empty response buffer, and a ready command port.
This check does not depend on `BLASTER`, IRQ routing or DMA transfers.
Four `FF` values indicate that the expected DSP response is absent; the
SB migration originally left its ports out of the machine's I/O decoder.

`bash scripts/test_at_soundblaster.sh` exercises the DSP and DMA adapter,
then repeats detection through the production CPU bus bridge, machine
decoder and device router using a simulated CPU bus driver. It also checks
IRQ5/IRQ7 routing and the mutually exclusive SB/C/MS port selection.

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
