# MRBIOS CMOS warning after FreeDOS startup

## Cause

The RTC incorrectly aliased CMOS byte `37h` to the century byte at `32h`.
Reads of `37h` returned `32h`, and CPU or host writes to `37h` also replaced
`32h`. These are independent battery-backed bytes in an AT RTC. The local
86Box implementation (`src/nvr_at.c`, `nvr_reg_common_write`) preserves that
independence.

FreeDOS initializes its clock during kernel startup, before CONFIG.SYS:

1. `kernel/main.c` calls `Init_clk_driver()`.
2. `kernel/initclk.c` reads BIOS time/date and calls DOS SetDate/SetTime.
3. `kernel/sysclk.c` writes the AT clock through `WriteATClock()`.
4. `drivers/wratclk.asm` calls INT 1Ah, including AH=05h to set the date.

Sources inspected:
[FreeDOS kernel, revision d6791add](https://github.com/FDOS/kernel/tree/d6791add2043c9d7b584d840a8ffaf8829fd2bdc).
The clock-initialization source identifies its existing 2008 revision.

MRBIOS writes the century to `32h` for this service. On the affected core,
this also changes the value returned for `37h`. MRBIOS includes `37h` in a
private configuration checksum, while deliberately excluding century `32h`.
Consequently a normal date write can corrupt the BIOS's configuration check.
FreeDOS exercising this BIOS service explains an OS-dependent trigger;
the service itself is valid. Other software setting the date can expose the
same RTC defect.

The saved snapshots also explain the observed `00h`/`19h` century values.
Restoring `37h=00h` on the old core overwrote century `32h` with zero.
FreeDOS rejects a resulting date before 1980; its subsequent SetTime uses
the initial `DaysSinceEpoch=0` and writes 1980-01-01, with century `19h`.
That adds 25 to the private checksum input. A century value of `20h`
contributes zero modulo 32, so a date-write test using only modern dates
could miss the warning despite the alias still being incorrect.

## Evidence from the supplied ROM

ROM: `MR_BIOS_1.65_286_64K.ROM`, 65,536 bytes.

SHA-256: `6f936ee53ba58663d1ccc7b80b1f5caba841f3f816c4dca15477ca540f9f252f`.

| ROM address | Operation |
| --- | --- |
| `F000:E36E` | INT 1Ah/AH=05h date setter; writes month, year, century at `32h`, day and status B |
| `F000:E9B6` | Copies CMOS `0Eh..3Fh` to a RAM snapshot |
| `F000:E9CE` | Standard sum of `10h..2Dh`, compared with `2Eh/2Fh` |
| `F000:E9EC` | Private checksum selected by masks at `E9E6h..E9EBh` |
| `F000:EA16` | Computes both checksums and writes the snapshot back to CMOS |
| `F000:A847` | Calls the private checksum check and sets error flag `20h` on mismatch |
| `F000:A85B` | Tests the CMOS error flags and selects the corruption message at `8012h` |

The private checksum is:

```text
(1Fh + sum(CMOS[11h], CMOS[13h], CMOS[1Bh..2Dh], CMOS[33h..3Eh])) & 1Fh
```

It is stored in the low five bits of `CMOS[3Fh]`; the upper three bits have
other BIOS uses. A valid standard AT checksum alone therefore cannot rule
out this warning.

The supplied ROM's date setter and checksum routines were executed in a
small Unicorn harness using a copy of the user's CMOS snapshot. Setting
the date to 1980-01-01 produced these results:

| RTC behavior | Standard checksum | MRBIOS private checksum | Read `32h` / `37h` |
| --- | --- | --- | --- |
| Previous core alias | Valid | Invalid | `19h` / `19h` |
| Independent bytes | Valid | Valid | `19h` / `00h` |

For this snapshot the standard checksum stayed `0B33h`. The stored private
checksum stayed `1Bh`; the alias changed the calculated result to `14h`.
The unmodified ROM routines were used, without changing the disk image or
emulating a complete machine boot.

BIOS checksum repair followed by another FreeDOS date write can recreate
the warning on later resets. Whether FreeDOS has run between two resets
matters; the precise sequence of alternating boots still needs confirmation
on the FPGA.

## Correction and validation

`spk286_at_rtc_cmos.sv` keeps `32h` and `37h` independent for CPU accesses,
host uploads and host snapshots. Calendar century rollover updates only
`32h`. Main requires no change for this defect: it had been persisting the
already-altered value exposed by the core.

The RTC regression reproduces the MRBIOS date-write sequence, checks the
private checksum, and repeats HPS snapshot/reset/restore four times. It also
checks writes in the opposite direction and century rollover isolation.
It fails on the previous RTL and passes with the correction.

Run:

```sh
bash scripts/test_at_rtc_cmos.sh
```

Both Icarus and Verilator passed the corrected RTC/calendar suite and the
reset suite, including:

```text
AT_RTC_MRBIOS_DATE_PASS resets=4 independent_32_37=1
AT_RTC_RESET_PASS cold_and_sticky_clear
AT_RTC_CMOS_TEST_PASS
```

The existing memory-profile test is returned explicitly to its 1 MiB
fixture after exercising every OSD choice. Its subsequent checksum
expectations already assumed that profile; the previous test stopped
at 2 MiB after the OSD reordering.

The fix must be compiled into a new core for hardware confirmation. A
previously invalid `cmos.dat` may require one BIOS save to rebuild the
private checksum. Changing BIOS or reinstalling FreeDOS is unnecessary
for this correction.
