# Selectable PC/AT RAM size

The 80286 has a 24-bit physical address bus in protected mode, so its physical
address ceiling is 16 MiB (`000000h–FFFFFFh`). Its 1 GiB figure is the maximum
virtual address space per task, not physical RAM.

The Hardware OSD's **Installed RAM** selector offers 4, 8, 16, 1 and 2 MiB, in
that order. Its first option, 4 MiB, is the default (`000` in status bits
`74:72`). The value is sampled when **Reset & apply settings** resets the
machine; the memory decoder and CMOS then use the same applied profile. The fixed base is
640 KiB at `000000h–09FFFFh`. Extended RAM starts at `100000h`, preserving the
existing 384 KiB offset between the selected total and the high-memory limit.

| OSD bits `74:72` | OSD profile | Extended RAM range | CMOS extended RAM |
|---:|---:|---:|---:|
| `000` | 4 MiB (default) | `100000h–45FFFFh` | 3,456 KiB |
| `001` | 8 MiB | `100000h–85FFFFh` | 7,552 KiB |
| `010` | 16 MiB | `100000h–FDFFFFh` | 15,232 KiB |
| `011` | 1 MiB | `100000h–15FFFFh` | 384 KiB |
| `100` | 2 MiB | `100000h–25FFFFh` | 1,408 KiB |

The 16 MiB selection represents installed memory. Following the 86Box
16-bit-bus AT map, CPU-visible extended RAM ends at `FDFFFFh`:
`FE0000h–FEFFFFh` is reserved and `FF0000h–FFFFFFh` maps the 64 KiB system-BIOS
alias. The low video, EGA BIOS (`C0000h–C7FFFh`), UMB RAM
(`C8000h–DFFFFh`) and EMS page frame (`E0000h–EFFFFh`) retain distinct owners.
UMB and EMS are always enabled in this profile. The profile reports
15,232 KiB extended plus 640 KiB conventional RAM, or 15,872 KiB visible in
total. The 384 KiB low-memory hole and 128 KiB high reserved area account for
the difference from the installed 16 MiB. CMOS fields `17h/18h` and `30h/31h`
track that extended size. The
standard checksum is adjusted when the applied size changes; BIOS CPU writes
to CMOS remain possible afterward.

EMS pages keep their existing private SDRAM backing at backend addresses
`200000h–3FFFFFh`. To prevent expanded CPU-visible RAM from aliasing that store,
backend accesses at 2 MiB through `FDFFFFh` are shifted
up by 2 MiB. This changes only the SDRAM backing address; the CPU still sees
the selected physical address and contiguous extended RAM.

The machine resolves the CPU BIOS alias `FF0000h–FFFFFFh` to
`0F0000h–0FFFFFh` before handing addresses to the backend. The read buffer and
SDRAM owner must use those backend addresses unchanged: backend
`FF0000h–FFFFFFh` stores CPU RAM at `DF0000h–DFFFFFh` after the 2 MiB shift.
Applying the CPU alias again in either backend component makes that RAM
collide with the BIOS. This explains the reported POST stop at 13,888 KiB:
`DF0000h / 1024 - 384 = 13,888`, accounting for the low-memory hole.

Regression coverage includes independent high-RAM/BIOS reads and writes in
the SDRAM owner and read buffer, plus `+RAM16` in the BIOS first-fetch test.
That integrated test writes and reads one word per 64 KiB extended-RAM block
through the production mapper, memory port, buffer and SDRAM pins, checks
the collision boundaries and final RAM word, verifies all 64 KiB of BIOS
remain intact, and then executes the reset fetch. The user also confirmed
correct operation on MiSTer after this fix. This is not an exhaustive RAM test.

The previous fixed 1 MiB baseline and its original verification record are
documented in [AT_RTC_CMOS_1M_HANDOFF.md](AT_RTC_CMOS_1M_HANDOFF.md).
