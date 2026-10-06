# Dyna Blaster VGA+ mode

The supplied `DYNA.EXE` is LZEXE packed. Its unpacked entry point calls the
routine at code offset `1235h`. That routine requests `INT 10h` mode `12h`,
loads 24 CRTC registers and 20 Attribute Controller registers, clears
Sequencer 04h bit 3 (Chain-4), clears CRTC 14h bit 6 (doubleword addressing),
sets CRTC 17h bit 6 (byte addressing), and sets Graphics Controller 05h to
`40h` (256-colour shift). It then changes CRTC 01h to `3Fh`, 12h to `CFh`,
and 13h to `40h`. The CRTC overflow and maximum-scan-line registers are
`3Eh` and `41h`, yielding 512×464 physical VGA dots, or a 256×232 logical
image with each source line scanned twice. Other game paths set Offset 13h
to `20h` for a direct-width page.

The resulting planar address is `Start Address + row × (2 × Offset) + x / 4`;
the plane is `x mod 4`. Thus Offset `40h` selects 128 bytes per plane row
(512 virtual pixels), and Offset `20h` selects 64 bytes per row (256 pixels).
The game also changes Start Address, pel panning, and Line Compare during play.

`VGATSR.COM` lets the EGA BIOS establish planar mode `0Dh` for a mode `12h`
request, loads the IBM VGA mode `12h` registers over it, reports mode `12h` in
the BIOS Data Area, and writes `12h` to VGA+'s private control port. VGA+
displays that baseline through its 640×480 planar profile (see
`vga-pinball-fantasies.md`) until it sees the 256×232 timing, one of those two
offsets, byte addressing, 256-colour shift, and unchained A000h planar memory.
It then renders the game's four VGA planes. The existing packed mode `13h`,
planar `0Dh`, and other unchained profiles retain their original selectors.

The TV output emits 256×232 logical pixels in an 1824-clock × 262-line
15.7 kHz / 59.9 Hz frame. Native doubles pixels and lines to 512×464 output
pixels in an 800-clock × 525-line 31.5 kHz / 60 Hz frame. Both keep the same
planar memory addresses and pixel colours.
