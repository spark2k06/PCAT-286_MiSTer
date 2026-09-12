# AT RTC/CMOS and 1 MiB memory profile

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
completed without modifying SDRAM. The reset-vector alias `FFF000h–FFFFFFh`
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

The memory fields are fixed to the physical profile:

| CMOS | Value | Meaning |
|---|---:|---|
| `15h/16h` | `80h/02h` | 640 KiB base memory (`0280h`) |
| `17h/18h` | `80h/01h` | 384 KiB extended memory (`0180h`) |
| `30h/31h` | `80h/01h` | duplicate extended-memory field |
| `34h/35h` | `00h/00h` | no memory above 16 MiB |

Other CMOS bytes remain writable by the BIOS and by `hps_ext`; each write in
the checksummed range updates the stored checksum. Writes attempting to change
the fixed RAM fields are ignored so software cannot advertise memory that the
decoder does not provide.

## Simulation evidence

The dedicated RTC test runs in both Icarus and Verilator and covers host-time
import, full year rollover, the 2024 leap day, SET freeze, alarm/update IRQ8,
status-C clearing, fixed memory fields and checksum maintenance:

```text
AT_RTC_CMOS_PASS host_time=1 calendar=1 irq=1 memory_kib=1024 checksum=0104
```

The integrated device test confirms that an `F400h` write passes through the
AT router and becomes visible through ports `70h/71h`. The memory-decoder test
checks both ends of `100000h–15FFFFh` and rejects `160000h` and `FFEFFFh` as
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
