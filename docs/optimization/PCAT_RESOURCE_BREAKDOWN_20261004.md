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
