# Keyboard path bring-up (SPK286 frontend)

This note records the focused diagnosis of a DOS 3.20 boot that stops at the
`Enter new date` prompt. It intentionally does not change BIOS code or the
keyboard datapath.

## Reproduction input

`SW/ROMs/test/disk01.img` is a valid 360 KiB DOS 3.20 floppy image (OEM
`MSDOS3.2`). The stop occurs after the floppy has booted and DOS has printed
the date prompt.

## RTL evidence

`sim/keyboard_path/keyboard_path_tb.sv` drives a Set-2 Enter frame through the
current `KFPS2KB`, 8255 and 8259 blocks. It verifies:

1. Set-2 Enter (`5A`) is translated to XT scan code `1C`.
2. IRQ1 is asserted and reaches the PIC as INT.
3. The BIOS-style port-B bit-7 pulse clears the pending key and IRQ1.

This is a focused simulation only; it is not a claim that the complete CPU,
BIU and legacy bus timing have passed the physical test.

## Hardware observation

With `SPK286 Debug=On`, select the **BUS** page and keep the key pressed while
the date prompt is visible. The additional row is:

```
KBD:00 I:0 PB:00 P:0
```

* `KBD` is the current translated XT scan code.
* `I` is the keyboard controller IRQ1 output.
* `PB` is the live 8255 port-B value (`bit 6` enables the keyboard clock,
  `bit 7` is the BIOS clear pulse).
* `P` is the raw PIC interrupt output before the CPU-facing phase sample.

The CPU page retains the last accepted event (`EVT:09/4` means vector 09h,
external interrupt). The row is diagnostic only and does not feed execution.

Interpretation while holding a key:

| Observation | Likely boundary |
| --- | --- |
| `KBD` stays `00`, `I=0` | PS/2/HPS input or Set-2 receiver |
| `KBD=1C`, `I=1`, `P=0` | keyboard-to-PIC synchronisation/mask |
| `KBD=1C`, `I=1`, `P=1`, no `EVT:09/4` | CPU-facing INTR/event acceptance |
| `EVT:09/4` appears, but DOS remains waiting | BIOS/DOS read or subsequent port-61 acknowledgement |

The candidate RBF containing this instrumentation must therefore be tested on
the target MiSTer before a functional fix is selected.

## Candidate build

The focused candidate built with Quartus Prime 17.0.2 Lite (Cyclone V
`5CSEBA6U23I7`) is:

* `releases/PCAT-286_20260910_keyboard_path_debug.rbf`
* SHA-256: `0094F82214DA4F550AA860F4095C0F1E540CBEDCDE4D21DD5FA2BC0493BC6176`

The complete Quartus flow, fitter and assembler finished with zero tool
errors. The standard TimeQuest report still contains the inherited
whole-machine setup exceptions; this RBF is a bring-up instrument, not a new
claim of global timing closure. Physical MiSTer validation is pending.
