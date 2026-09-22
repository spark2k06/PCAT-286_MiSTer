# AT RTC/CMOS and 1 MiB memory profile

> Historical baseline: this document records the original fixed 1 MiB
> implementation. The current selectable 1/2/4/8/16 MiB profiles are described
> in [AT_MEMORY_SIZE_CONFIGURATION.md](AT_MEMORY_SIZE_CONFIGURATION.md).

## Cause found

The AT RTC previously had no connection to MiSTer's management transport.
Although `hps_ext` already existed for the floppy controller, management writes
in the standard RTC window `F4xx` reached only the storage block. The local RTC
also incremented only register `00h`; minutes, hours, date, month, year and
century remained unchanged. This explains the zero/invalid date and time shown
by Supersoft Landmark even though ports `70h/71h` and the basic IRQ8 diagnostic
were present.

The memory decoder exposed SDRAM at nearly every address from `100000h` to
`FFEFFFh`, while CMOS base and expansion fields reset to zero. Therefore the
diagnostic BIOS could neither describe the installed memory nor relate its
display to a finite hardware profile.

## Reference comparison

Both local reference cores route management address prefix `F4h` to their RTC:

- `D:/GitHub/ao486_MiSTer/rtl/system.v` selects
  `mgmt_address[15:8] == 8'hF4` and passes the low address/data byte to
  `rtl/soc/rtc.v`.
- `D:/GitHub/z486_MiSTer/src/soc/rtc.v` uses the same RTC management convention
  and overrides CMOS memory-size fields so they agree with its RAM option.

The AT keeps this established MiSTer protocol. It does not add an OSD clock or
an independent timestamp format.

For a 1 MiB IBM AT-style configuration, the implemented geometry is:

| Region | Range | Size |
|---|---:|---:|
| Conventional RAM | `000000h–09FFFFh` | 640 KiB |
| Video/option/BIOS hole | `0A0000h–0FFFFFh` | 384 KiB, not RAM |
| Remapped extended RAM | `100000h–15FFFFh` | 384 KiB |
| Total installed RAM | | 1024 KiB |

This matches the 384 KiB top-memory remap used by the local 86Box IBM AT/286
machine reference. CPU reads above the installed range return `FFh`; writes are
completed without modifying SDRAM. The high BIOS alias `FF0000h–FFFFFFh`
continues to select the system BIOS.

## CMOS behavior

The RTC now supports:

- MiSTer host date/time writes at `F400h–F47Fh`;
- seconds, minutes, hours, weekday, day, month, year and century;
- BCD or binary data and 12- or 24-hour mode;
- Gregorian month length and leap years, including century years;
- status-B SET freeze;
- periodic, alarm and update-ended status-C flags and IRQ8;
- status-C read-to-clear and status-D valid-RAM bit;
- the standard CMOS checksum over `10h–2Dh`.

CMOS and its checksum are initialized at FPGA configuration, not on each
machine reset. HPS writes are accepted while reset is asserted; CPU port
accesses remain inhibited. Subsequent machine resets retain CMOS contents.
This models retention within the loaded core, not persistence to an SD-card
file or a physical battery across FPGA reconfiguration.

The memory fields are fixed to the physical profile:

| CMOS | Value | Meaning |
|---|---:|---|
| `15h/16h` | `80h/02h` | 640 KiB base memory (`0280h`) |
| `17h/18h` | `80h/01h` | 384 KiB extended memory (`0180h`) |
| `30h/31h` | `80h/01h` | duplicate extended-memory field |
| `34h/35h` | `00h/00h` | no memory above 16 MiB |

The RAM fields are protected from `hps_ext` replacement so the initial profile
always matches the decoder. They remain ordinary CPU-writable CMOS RAM because
the Landmark CMOS test saves `10h–3Fh`, writes and verifies `55h` and `AAh`
throughout that range, then restores the saved values. This also requires
checksum bytes `2Eh/2Fh` to accept direct CPU writes. Each CPU write in the
checksummed range updates the stored checksum until software explicitly writes
`2Eh/2Fh`. Other CMOS bytes remain writable by the BIOS and by `hps_ext`.

## Simulation evidence

The dedicated RTC test runs in both Icarus and Verilator and covers host-time
import, full year rollover, the 2024 leap day, SET freeze, alarm/update IRQ8,
status-C clearing, default memory fields, the exact Landmark `10h–3Fh`
save/55h/AAh/restore sequence and checksum maintenance:

```text
AT_RTC_CMOS_PASS host_time=1 calendar=1 irq=1 memory_kib=1024 checksum=0104
```

The CPU-level integration test enters the unmodified Landmark routine at
`F000:91F6`. It executes the original save, `55h`, `AAh`, verify and restore
operations through ports `70h/71h`, and observes its real pass/fail calls:

```text
AT_LANDMARK_CMOS_RAM_PASS bytes_10_3f=48 patterns=55_AA_restore
AT_LANDMARK_CMOS_TEST_PASS
```

The integrated device test confirms that an `F400h` write passes through the
AT router and becomes visible through ports `70h/71h`. The memory-decoder test
checks both ends of `100000h–15FFFFh` and rejects `160000h` and `FEFFFFh` as
RAM. The full machine boundary still elaborates, lints and executes its BIOS
fixture.

Commands used:

```text
bash scripts/test_at_pit_ports.sh
bash scripts/test_a2_memory_arbiter.sh
bash scripts/test_a5_at_devices.sh
bash scripts/test_at_machine_boundary.sh
```

## Hardware check after synthesis

Use the unmodified Supersoft Landmark ROM first. On the CMOS RAM configuration
panel, verify:

1. the date and time contain the current MiSTer values and seconds advance;
2. `BASE` shows `640K`;
3. `EXPANSION` shows `00384K` (formatting may omit leading zeros);
4. `CMOS RAM CHECKSUM` remains `VALID`;
5. `REAL TIME CLOCK INTERRUPT` and `CMOS RAM TEST` still pass.

Also perform a soft core reset and confirm that the host date/time is supplied
again. No new RBF was generated in this change set.

## Phoenix boot follow-up: host upload was discarded during reset

The Phoenix A286 v1.01 hardware state probe reported `CMOS10=00` instead of
the drive types supplied by MiSTer. Before INT13 reset, BDA `48B..496` was
`00 00 00 FD 01 93 00 00 00 00 08 00`. After reset it began with `80`,
and the directory read returned `AX=0200`, Carry set, with FDC result bytes
`44 05 00 00 01 02 02` at BDA `442..448`.

The local `Main_MiSTer/support/x86/x86.cpp::x86_init()` holds status bit 0
high while writing the complete CMOS through `F400..F47F`, then releases it.
`PCAT-286.sv::at_boot_reset` includes that bit and reaches the RTC through the
AT machine/router. The previous RTC reset branch cleared the CMOS array on
every clock and skipped the HPS management writes altogether. Earlier RTC
tests uploaded configuration only AFTER reset, so they missed this ordering.

The correction retains configuration/time/checksum across machine reset and
accepts the host upload during reset. It does not force a particular floppy
type, patch Phoenix, change A20 or alter the memory map. The existing FDC
rate-validation change remains in place.

The RTC regression now covers host uploads during initial and later resets,
CPU-written configuration/time/shutdown/checksum retention, CPU I/O exclusion
during reset, ignored out-of-range management writes, hardware RAM-size
protection and checksum maintenance. Before the fix it fails with
`host floppy types were lost during reset`. Run it with:

```sh
bash scripts/test_at_rtc_cmos.sh
```

The existing integrated device fixture now explicitly programs 500 kbit/s
for its 1.2 MB medium; it previously relied on the FDC ignoring data rate.

The local diagnostic in `build/phoenix-boot-probe` can inject the captured
BDA state into the original Phoenix INT13 handler connected to the real FDC
RTL. `phoenix_fdc_cosim.py --state --hardware-state` reproduces the directory
read error: the BIOS sends READ DATA at 250 kbit/s with EOT=9; ST1=05 becomes
AH=02. With BDA drive types 44 and correctly detected media, `--state` passes
the directory and IO.SYS-sector reads. These tests substitute the CPU and
DMA/IRQ/timer adapters and do NOT execute POST or a full FPGA/DOS boot.

Hardware now confirms the complete expected state with two 1.44 MB units:
`CMOS10=44`, `CMOS0E=00`, valid `0311/0311` checksum, `BDA48F=44`, successful
R/D/1 calls and 500 kbit/s media state. DOS advances to `Iniciando MS-DOS...`
from floppy, but then stops at the same stage observed when booting the HDD.
That common DOS initialization hang remains separate and unresolved.
