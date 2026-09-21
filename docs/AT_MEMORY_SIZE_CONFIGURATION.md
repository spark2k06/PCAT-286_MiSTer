# Selectable PC/AT RAM size

The 80286 has a 24-bit physical address bus in protected mode, so its physical
address ceiling is 16 MiB (`000000h–FFFFFFh`). Its 1 GiB figure is the maximum
virtual address space per task, not physical RAM.

The Hardware OSD's **Installed RAM** selector offers 1, 2, 4, 8 and 16 MiB.
The value is sampled when **Reset & apply settings** resets the machine; the
memory decoder and CMOS then use the same applied profile. The fixed base is
640 KiB at `000000h–09FFFFh`. Extended RAM starts at `100000h`, preserving the
existing 384 KiB offset between the selected total and the high-memory limit.

| OSD profile | Extended RAM range | CMOS extended RAM |
|---:|---:|---:|
| 1 MiB | `100000h–15FFFFh` | 384 KiB |
| 2 MiB | `100000h–25FFFFh` | 1,408 KiB |
| 4 MiB | `100000h–45FFFFh` | 3,456 KiB |
| 8 MiB | `100000h–85FFFFh` | 7,552 KiB |
| 16 MiB | `100000h–FFEFFFh` | 15,356 KiB |

The 16 MiB profile uses the full 286 physical range while leaving
`FFF000h–FFFFFFh` mapped to the reset-vector BIOS alias. The low video, option
ROM and system BIOS windows keep their existing owners. As a result the 16 MiB
profile reports 15,356 KiB extended plus 640 KiB conventional RAM; the reserved
address-map holes are not counted as installed memory. CMOS fields `17h/18h`
and `30h/31h` track that extended size. The standard checksum is adjusted when
the applied size changes; BIOS CPU writes to CMOS remain possible afterward.

EMS pages keep their existing private SDRAM backing at backend addresses
`200000h–3FFFFFh`. To prevent expanded CPU-visible RAM from aliasing that store,
backend accesses at 2 MiB and above (except the reset-vector alias) are shifted
up by 2 MiB. This changes only the SDRAM backing address; the CPU still sees
the selected physical address and contiguous extended RAM.

The previous fixed 1 MiB baseline and its original verification record are
documented in [AT_RTC_CMOS_1M_HANDOFF.md](AT_RTC_CMOS_1M_HANDOFF.md).
