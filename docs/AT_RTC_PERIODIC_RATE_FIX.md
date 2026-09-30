# AT RTC programmable periodic interrupt correction

Date: 2026-09-30.

This corrects the PCAT RTC frequency defect identified in the
[OS/2 hardware video analysis](OS2_RTC_IRQ8_VIDEO_20260930.md).
OS/2 programs register A to `2Bh` for 32 Hz, but the previous top-level
generator supplied approximately 12.2 kHz regardless of that setting.
The correction is in PCAT's chipset integration; SPK286 CPU RTL is unchanged.

## Implementation

- `spk286_at_rtc_clock.sv` supplies a 32768 Hz enable from the fixed 50 MHz
  AT clock. A fractional accumulator uses the exact ratio `256/390625`,
  with intervals of 1525 or 1526 clocks. The independent one-second enable
  retains the previous 50,000,000-cycle period and also feeds the splash.
- The existing `periodic_tick` port at the machine/router/RTC boundary now
  means a **32768 Hz reference enable**, not an already divided IRQ event.
  The top-level instance supplies that enable and the QIP includes the new
  generator. External fixtures must supply the new reference frequency.
- The RTC divides these enables using register A's RS field. All 16 settings
  are handled: zero disables periodic events, 1/2 alias 8/9, and 3..15
  select 8192..2 Hz. OS/2's `RS=Bh` divides by 1024 for 32 Hz; the BIOS
  default `RS=6` divides by 32 for 1024 Hz.
- CPU and HPS writes to register A restart the selected periodic interval.
  DV=`010` selects the supported 32.768 kHz oscillator mode; other DV
  settings inhibit the divider/calendar, including the `11x` divider-reset
  encodings. This does not implement alternative physical oscillator inputs.
- PF latches independently of PIE. IRQ8 is derived from `(PF & PIE) |
  (AF & AIE) | (UF & UIE)`, so enabling a pending source asserts IRQ and
  masking it drops IRQ without discarding the event flag.
- CPU reads of status C acknowledge its flags. A coincident new event remains
  pending; HPS reads remain side-effect free. SET continues to inhibit calendar
  updates while periodic events remain active. RS=0 leaves calendar updates on.

This change does not attempt to add UIP transfer timing or the exact first
calendar-update phase after a divider reset; the existing external one-second
calendar enable is retained.

## Focused validation

`scripts/test_at_rtc_cmos.sh` passes in Icarus and Verilator, covering:

- Existing MRBIOS date/checksum, HPS upload, CMOS retention, calendar,
  alarm/update interrupt and reset checks.
- All 16 rate settings, checking both the first and subsequent event boundaries.
- OS/2's A=`2Bh`, B=`52h`: 32 periodic events per 32768 reference ticks, plus
  a simultaneous one-second update and status-C acknowledgement.
- PF with PIE disabled, later enable/disable of a pending interrupt,
  side-effect-free HPS status reads, SET behavior, CPU/HPS rate changes,
  DV stop/reset, and a new periodic event coincident with a status-C read.
- The physical generator's full 390625-cycle repeating pattern in Icarus
  (256 reference pulses), and 50,000,000 clocks in Verilator (32768 reference
  pulses, one second pulse). Inter-pulse spacing is also checked.

Local logs: `build/at-rtc-rate-20260930/`. The new periodic and clock benches
compile without Verilator warnings; the existing minimal reset fixture retains
its unused-output PINMISSING warnings.

The existing integrated device fixture now supplies 32 reference ticks to
exercise the default 1024 Hz IRQ8 event, asserting that the first 31 do not
fire early. It passes in both Icarus and Verilator
(`A5_AT_DEVICES_TEST_PASS`); its result is recorded separately in
`build/at-rtc-router-20260930/`.

## Hardware configuration and confirmation

The committed default in `config.tcl` enables `SPK286_AT_NO_DEBUG` and leaves
`SPK286_AT_DEBUG_CPU_DIV2` commented. CPU and chipset run at **50 MHz** and
the hardware observer is omitted. P01/P02/P05/P06 settings are preserved.

On 2026-09-30, after testing the correction on MiSTer, the user confirmed that
the RTC fix worked and requested this commit. This supplements the focused
simulation results above with user-reported hardware confirmation.
