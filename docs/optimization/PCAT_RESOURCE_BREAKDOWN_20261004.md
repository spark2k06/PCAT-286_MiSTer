# PCAT-286 resource breakdown — selected production fit

Date: 2026-10-04. Source: selected fixed50 admission/retained-FDC seed 1 fit,
completed 2026-10-03 12:40:21, Quartus 17.0.2, Cyclone V 5CSEBA6U23I7.
The RBF SHA-256 matches the [selection receipt](../evidence/fixed50-timing-20261003/admission-retained-fdc-selection.json):
`6f0aff676531ce165e94bdcb35057e3f060245c40ec4b374b93e53ec92c7c3cb`.
Its fitter summary matches the frozen original byte for byte.

## Main result

SPK286 accounts for **7,184.2 placed ALMs**, **20.12% of the placed design**
and **17.14% of the device's ALM capacity**. It uses **5,362 registers**,
**one M10K** and **zero DSPs**. Its ALMs-needed attribution is 6,284.3,
20.95% of the design's estimated logic requirement. These are complete CPU
figures, including protected mode, task switching, LOADALL, execution and BIU.
They exclude the machine-side RAM buffers, bridge, peripherals and video.

| Global metric | Used | Device capacity | Utilization |
| --- | ---: | ---: | ---: |
| ALMs needed, fitter estimate | 29,993 | 41,910 | 71.57% |
| ALMs used in placement | 35,698 | 41,910 | 85.18% |
| Registers | 38,119 | Reported as logic + I/O registers | — |
| M10K | 416 | 553 | 75.23% |
| Block memory bits | 3,301,019 | 5,662,720 | 58.29% |
| DSP | 39 | 112 | 34.82% |
| PLL | 3 | 6 | 50.00% |

ALMs needed and placed ALMs are different quantities. The fitter estimates
6,020 ALMs recoverable through denser packing, but this is not a guaranteed
reserve at unchanged timing. 4,021/4,191 LABs have some occupied resources;
that 96% LAB statistic does not mean 96% of ALM logic is used. Routing, packing
and timing matter in addition to aggregate counts.

## Accounting method

The report's first number includes descendants; parentheses give own logic
where provided. We assign each hierarchy node's own contribution to exactly
one functional block. This avoids adding a CPU/peripheral parent to its
children. All 553 hierarchy rows are retained in the evidence JSON.

Fractional ALMs are fitter hierarchy attribution of shared resources, not
fractional physical cells that can be removed independently. The hierarchy
totals 35,697.0 placed ALMs versus 35,698 globally; the one-ALM difference is
shown explicitly. Registers include 38,070 dedicated logic and 49 I/O registers.
Rows sum to the global totals for ALMs, registers, RAM and DSPs.

The table covers the **selected production RBF**. Private P06 register/CODE
pilots are excluded, since they have not been integrated or fitted. Their
generic cell counts cannot be added to these ALM figures. The selected fit
still has global setup -0.022 ns and hold +0.073 ns; resource accounting does
not change its timing acceptance.

## Block table

| Block | ALMs needed | ALMs placed | % of placed design | Registers | M10K | DSP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU SPK286 | 6,284.3 | 7,184.2 | 20.12% | 5,362 | 1 | 0 |
| EGA/VGA+ adapter and VRAM | 4,001.3 | 4,272.2 | 11.97% | 3,340 | 320 | 0 |
| RAM read buffers and posted writes | 2,438.5 | 2,525.8 | 7.08% | 1,747 | 7 | 0 |
| PC sound devices and MT32-Pi | 2,227.3 | 2,994.5 | 8.39% | 3,917 | 3 | 6 |
| RTC/CMOS and clock | 1,369.8 | 1,528.1 | 4.28% | 1,146 | 0 | 0 |
| DMA | 538.7 | 633.2 | 1.77% | 760 | 0 | 0 |
| PIC | 406.8 | 426.7 | 1.20% | 283 | 0 | 0 |
| PIT and clock | 496.5 | 516.3 | 1.45% | 318 | 0 | 0 |
| Keyboard, 8042 and serial mouse | 442.4 | 455.0 | 1.27% | 361 | 1 | 0 |
| IDE and floppy | 835.8 | 891.4 | 2.50% | 904 | 17 | 0 |
| Serial ports and MPU401 | 525.4 | 578.8 | 1.62% | 937 | 6 | 0 |
| Core framebuffer and video output | 577.8 | 717.9 | 2.01% | 905 | 10 | 0 |
| MiSTer scaler and HDMI/VGA output | 4,003.0 | 5,894.4 | 16.51% | 9,366 | 43 | 25 |
| MiSTer OSD | 1,233.4 | 1,413.8 | 3.96% | 1,956 | 8 | 0 |
| MiSTer audio output and ALSA | 1,314.1 | 1,478.2 | 4.14% | 1,648 | 0 | 8 |
| HPS I/O, ROM loading and control | 1,185.2 | 1,614.8 | 4.52% | 2,487 | 0 | 0 |
| Memory bridge, SDRAM and arbitration | 596.9 | 698.0 | 1.96% | 757 | 0 | 0 |
| Other integration and peripherals | 1,515.7 | 1,873.7 | 5.25% | 1,925 | 0 | 0 |
| Global/hierarchy rounding and unattributed placement | 0.1 | 1.0 | 0.00% | 0 | 0 | 0 |
| TOTAL | 29,993.0 | 35,698.0 | 100.00% | 38,119 | 416 | 39 |

## Inside SPK286

| Block | ALMs needed | ALMs placed | % of CPU placed ALMs | Registers | M10K | DSP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| spk286_micro_executor | 2,700.3 | 2,860.3 | 39.81% | 1,353 | 0 | 0 |
| spk286_task_switch_service | 768.2 | 1,107.5 | 15.42% | 1,879 | 0 | 0 |
| CPU top-level glue | 899.7 | 924.4 | 12.87% | 22 | 0 | 0 |
| spk286_protected_state | 427.7 | 454.8 | 6.33% | 553 | 0 | 0 |
| spk286_biu | 352.2 | 377.0 | 5.25% | 97 | 0 | 0 |
| spk286_loadall_service | 49.3 | 323.3 | 4.50% | 645 | 0 | 0 |
| spk286_registers | 181.0 | 190.5 | 2.65% | 198 | 0 | 0 |
| spk286_decoder | 163.7 | 166.8 | 2.32% | 0 | 0 | 0 |
| spk286_segments | 152.7 | 162.5 | 2.26% | 233 | 0 | 0 |
| spk286_events | 141.0 | 144.2 | 2.01% | 134 | 0 | 0 |
| spk286_operand_decode | 100.2 | 101.8 | 1.42% | 71 | 0 | 0 |
| spk286_fetch | 91.3 | 96.0 | 1.34% | 83 | 0 | 0 |
| spk286_microsequencer | 76.5 | 82.2 | 1.14% | 16 | 0 | 0 |
| spk286_prefetch_queue | 69.8 | 72.7 | 1.01% | 61 | 0 | 0 |
| spk286_operand | 44.0 | 50.3 | 0.70% | 3 | 0 | 0 |
| spk286_control_decode | 27.7 | 29.3 | 0.41% | 0 | 0 | 0 |
| spk286_instruction_context | 19.2 | 20.3 | 0.28% | 14 | 0 | 0 |
| spk286_alu_decode | 14.8 | 14.8 | 0.21% | 0 | 0 | 0 |
| spk286_flags_decode | 3.0 | 3.5 | 0.05% | 0 | 0 | 0 |
| spk286_condition | 2.0 | 2.0 | 0.03% | 0 | 0 | 0 |
| spk286_microcode_sync_rom | 0.0 | 0.0 | 0.00% | 0 | 1 | 0 |

The execution engine accounts for 39.81% of CPU placed ALMs; task-switch
service accounts for 15.42%. Protection also uses the protected-state,
segment, execution and top-level logic: task-switch rows are not the cost
of all protected mode. The microcode ROM is the CPU's single M10K.

The EGA/VGA+ adapter's 320 M10Ks split into 256 for EGA VRAM and 64 for
its framebuffer; the separate core capture/readout path adds ten. Together
these video memories use 330/416 M10Ks (79.33% of used blocks), whereas CPU
microcode uses 1/416 (0.24%). Main system RAM lives in external SDRAM.

Evidence: [resource analysis](../evidence/pcat-resources-20261004/README.md).

## MiSTer scaler versus the complete HDMI/VGA group

The group above includes the Avalon Scaler (`ascal`, TEMLIB), output geometry
and CDC, HDMI PLL control, synchronization, scanlines/shadowmask and VGA/YC
output. It is not the scaler's standalone resource attribution.

| Subset | ALMs needed | ALMs placed | Registers | M10K | DSP |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ascal`, including its descendants | 2,028.5 | 3,009.6 | 4,697 | 42 | 23 |
| Remaining members of HDMI/VGA group | 1,974.5 | 2,884.8 | 4,669 | 1 | 2 |
| Complete HDMI/VGA group | 4,003.0 | 5,894.4 | 9,366 | 43 | 25 |

`ascal` receives the core's RGB/sync/active-area stream, resizes and frames it
for the selected HDMI timing and crosses input/output clocks through an
external framebuffer. Nearest/polyphase and buffering selection remain
variable in this core. VGA can select native or scaled output. The scaler's
3,009.6 placed ALMs are 8.43% of the placed design / 7.18% of device capacity.
This is separate from the emulated EGA/VGA+ adapter.

References: [scaler source](../../sys/ascal.vhd),
[instantiation and output routing](../../sys/sys_top.v),
[inclusive scaler hierarchy](../evidence/pcat-resources-20261004/hierarchy.rpt).

## Dedicated 350-line to 240p/480i TV conversion

The native 350-line EGA conversion has its own capture/readout path. The
current identifiable attribution is a subset of the core framebuffer/output
group; it must not be added to that group again.

| TV conversion member | ALMs placed | Registers | M10K | DSP |
| --- | ---: | ---: | ---: | ---: |
| `ega_fb_capture` | 203.8 | 285 | 4 | 0 |
| `ega_fb_readout` | 329.3 | 313 | 6 | 0 |
| `ega_ddr_arbiter` | 53.7 | 63 | 0 | 0 |
| CRT350 configuration CDC and source selector | 11.0 | 29 | 0 | 0 |
| Identifiable TV conversion total | 597.8 | 690 | 10 | 0 |

This is 1.67% of placed design ALMs / 1.43% of device capacity (497.0 ALMs
needed). Both 240p and 480i share this pipeline and memory. Full frames reside
in external DDR; the ten M10Ks are capture FIFO and readout line buffers,
81,920 useful bits. The reserved three DDR frame slots total 6 MiB. Conversion
is enabled only for the core's qualifying 350-line raster; 200-line modes use
their native path.

These numbers describe **present attributed occupancy**, not an isolated
historical development delta or guaranteed savings on removal. No comparable
pre/post fit with only TV support changed was identified. The imported source
already contains both modes; the 2026-09-25 fit reports compare CDC/HDMI changes
with TV support present in both. Shared native-TV timing/OSD glue inside other
entities is not separately attributable here. The complete 717.9-ALM core
video-output group also includes mixer, monochrome and shared options.

References: [conversion selection](../../PCAT-286.sv),
[capture and DDR reservation](../../rtl/video/ega_fb_capture.v),
[240p/480i readout](../../rtl/video/ega_fb_readout.v),
[frozen hierarchy](../evidence/pcat-resources-20261004/hierarchy.rpt).

## Configurable fallback if a future fit cannot place the design

User decision, 2026-10-04: prioritize a working design. If a future fit fails
for resources, first disable an existing optional function **only through
`config.tcl`**, retaining its RTL and reactivation path. Optimize that function
later. This is a fallback policy, not a configuration change made here.

The present configuration enables SB, OPL2, C/MS, Tandy audio and MIDI; boot
splash is already omitted. Among the directly identified optional sound
engines, OPL2 has the largest ALM/register footprint:

| Existing config option | Engine placed ALMs | Registers | M10K | DSP |
| --- | ---: | ---: | ---: | ---: |
| `ENABLE_OPL2=1` | 1,149.8 | 2,026 | 3 | 1 |
| `ENABLE_CMS=1`, both SAA1099 chips | 826.8 | 807 | 0 | 4 |
| `ENABLE_SB=1`, Sound Blaster DSP/PCM | 586.9 | 582 | 0 | 1 |
| `ENABLE_TANDY_AUDIO=1` | 153.7 | 184 | 0 | 0 |

`ENABLE_OPL2=0` selects the existing `GEN_NO_OPL2` branch. It removes AdLib/FM,
including FM used by Sound Blaster; SB's digital PCM remains enabled. OPL2's
placed footprint is 3.22% of the placed design / 2.74% of FPGA capacity.
C/MS is the largest of these options by DSP count instead. Shared decode,
clocking and mixing contributions are outside the engine rows; the exact net
resource/timing gain still requires a new fit with that option changed.

MIDI combines serial/MPU-401, MT32-Pi and shared routing, so its isolated
option delta is not measured by these engine rows. The framework also has
`MISTER_DEBUG_NOHDMI` and video-filter/YC switches, but they are not among the
options currently exposed in this project's `config.tcl`. Do not substitute
an HDMI feature reduction for the present sound fallback without an explicit
decision about output requirements.

References: [current options](../../config.tcl),
[conditional sound instances](../../rtl/spk286_integration/spk286_at_sound.sv),
[frozen engine hierarchy](../evidence/pcat-resources-20261004/hierarchy.rpt).
