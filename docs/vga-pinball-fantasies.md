# Pinball Fantasies VGA+ modes

`PINBALL.EXE` is only a loader: it runs `INTRO.PRG` and then the selected
`TABLEn.PRG`, and serves their `INT 65h` calls. `INT 65h` AX=0200h copies the
six `PINBALL.CFG` bytes into the program; byte 4 selects the table resolution
(00h normal, 01h high).

## Table view (TABLEn.PRG)

Both resolutions start from BIOS mode `13h` and then go unchained (Sequencer
04h bits 3 and 0 cleared, CRTC 14h bit 6 cleared, CRTC 17h = `E3h`). CRTC 01h
is `4Fh` (320 pixels) and Offset 13h is `2Ah`: an 84-byte, 336-pixel virtual
row. The playfield scrolls by rewriting Start Address in multiples of 84; its
first `21h` (33) rows hold the score panel, which Line Compare shows at the
bottom of the screen.

| | Normal (`TABLE1.PRG` 6A5Fh + 6AB4h) | High (`66F0h`) |
|---|---|---|
| Misc Output | `E3h` | `A7h` |
| CRTC 06h / 07h | `0Dh` / `3Eh` | `BFh` / `1Fh` |
| CRTC 09h | `C0h`, then bit 6 cleared: `80h` | `40h`, then `00h` |
| CRTC 12h | `DFh`: 480 scanlines | `5Dh`: 350 scanlines |
| Line Compare | `19Dh` (413) | `13Ch` (316) |
| Logical picture | 320×240, Scan Doubling | 320×350, one scanline per row |

Before this change the renderer ignored CRTC 09h bit 7 (Scan Doubling) and had
no 350-line profile. The normal view was therefore read as 480 distinct rows
and the high view as the 400-line 320×200 profile; both showed roughly twice
the playfield, vertically squashed, and a misplaced score panel.

VGA+ now:

* exports CRTC 09h bit 7 from `UM6845R` and divides the physical scanline by
  two before applying Maximum Scan Line, so R9 = `80h` gives 240 rows;
* selects profile 4, 320×350, for 80 characters and 350 displayed scanlines.
  Native emits VGA's 350-line 70 Hz frame (912×449: 350 + 37 + 2 + 60 lines)
  and shows every scanline. The 15 kHz TV raster carries 175 lines, each the
  first of a physical pair, centred in the usual 262-line field;
* takes the physical scanline from the timing generator (`scan_y`) instead of
  assuming two per output line, so Line Compare is exact on Native profiles
  that show every scanline. The 15 kHz results are unchanged.

On a 15 kHz TV the normal resolution keeps every row; the high resolution
necessarily drops every second one. Native shows both completely.
The score panel is a dot matrix of single scanlines with dark rows between
them, so the high view's panel can look empty on the 15 kHz raster; this is
the accepted limitation of that combination, and the normal view shows it.

## Intro (INTRO.PRG)

The first part, the 21st Century eagle, is the same 320×240 unchained
256-colour mode with R9 = `C0h` (Scan Doubling, Line Compare bit 9 set, so no
split) and is covered by the change above.

The Digital Illusions logo and the menu use VGA mode 12h geometry instead.
After `INT 10h` AX=0012h, or from the mode 13h state when returning from a
table (`36AE0h`), the program keeps 80 characters and 80-byte rows, clears
GC 05h (no 256-colour shift), writes Attribute Mode Control `25h`, loads the 16
Attribute palette registers, and uses R9 = `40h` (640×480×16, `37317h`) or
`C0h` (640×240×16, `373F2h`). The menu later sets Mode Control bit 7 (P5,P4
Select).

VGA+ now:

* routes 80 characters, 480 displayed scanlines, Chain-4 off, Shift256 off
  and the A000h graphics aperture to a 640-pixel planar profile, while either
  private marker (mode 12h or 13h) is active. Shift256 is what keeps unchained
  320×240 apart;
* renders it in `vga_planar16_renderer` (`wide_640`): one source pixel per
  output pixel, Offset 40–47, Start Address, pel panning, Line Compare, Scan
  Doubling and Maximum Scan Line 0/1/3/7. The bit select follows the VRAM's
  two-clock latency, since a Native pixel is a single clock. Native is the
  60 Hz 912×525 frame; the TV raster carries 240 lines, one per physical
  pair, so 640×240 is exact and 640×480 shows every second line;
* implements Attribute Mode Control bit 7 and Color Select bits 1:0 when VGA
  is enabled. Color Select bits 3:2 (DAC index bits 7:6) are not carried;
* makes `VGATSR` load the IBM VGA mode 12h registers (Misc `E3h`, Sequencer,
  Graphics Controller, 25 CRTC and 21 Attribute registers) over the EGA BIOS's
  mode `0Dh` state and clear 38400 bytes per plane unless AL bit 7 is set.
  Dyna Blaster, which starts from this mode and loads its own unchained table,
  still selects its 256×232 profile.

`TESTBENCH/vga_pinball_fantasies_route_tb.v` replays the TSR's and the game's
register writes through `ega_top`.

## Timing dependence

The game's sound driver (`SB16.SDR` and siblings) emulates Amiga raster
interrupts with the PIT. When a table loads it counts Input Status #1 bit 0
transitions between two vertical retraces to measure the visible scanlines,
then calibrates PIT delays so that one event fires at retrace (frame handler,
`TABLE1.PRG` 41C1h) and one at a given scanline: 108h (264) in the normal view,
AEh (174) in the high one. The mid-frame handler (`55D6h`) sets the scroll
Start Address and draws the ball. Each frame the chain resynchronises on the
rising edge of bit 3.

The calibration is taken once, when the table loads, so the VGA output option
must not change while a table is running.

Two core defects broke this:

* **Bit 0 counted output lines, not VGA scanlines.** On the 15 kHz raster
  each output line stands for two physical scanlines, so the driver measured
  175 lines in the high view (real VGA: 350) and 240 in the normal view (480).
  Line 264 then did not exist and the event landed in the following frame:
  no scroll, a frozen attract mode and an unstable picture. The timing now
  raises two display-enable windows per output line wherever that line stands
  for two scanlines (`status_blank`), and Input Status #1 uses that.
  `vga_mode13_timing_tb` counts 400/480/350/480 per frame on both rasters.
* **Native ran from the wrong clock.** The PCAT adapter has only the
  28.636 MHz video clock, but the Native profiles inherited the PCXT core's
  800-clock line for a 25.2 MHz dot clock: 35.8 kHz, so 79.7 Hz at 449 lines
  and 68.2 Hz at 525. A 60 Hz HDMI output judders against that. Every Native
  profile now uses a 912-clock line (31.40 kHz): 69.9 Hz at 449 lines, 59.8 Hz
  at 525. Native 320×240 also became the 525-line 60 Hz frame with each row
  doubled, as Mode X really is, instead of 240 lines of a 70 Hz frame.

* **HDMI sampled VGA+ with the EGA dot clock.** The AT video adapter left
  `vga_mode13_pixel_toggle_out` unconnected and always passed the EGA dot
  toggle to the HDMI pipeline, where it becomes CE_PIXEL. Under every private
  VGA raster the scaler therefore took 14.318 or 16.257 MHz samples of a
  picture whose pixels follow the 28.636 MHz raster: the OSD reported 363×350
  and 726×175 for 640-dot lines, and the sampling phase wandered from line to
  line and frame to frame. This shimmer affected all VGA+ modes on HDMI and
  never the analog output, which does not use CE. `spk286_at_video_adapter`
  now passes the VGA raster's own pixel toggle while a private VGA route is
  active.

The high-resolution view is a 70 Hz mode on real VGA as well. On a 60 Hz HDMI
output it is smooth only with `vsync_adjust` set in `MiSTer.ini`; the normal
view is a 60 Hz mode.
