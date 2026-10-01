# RTC conversion timing optimization

The P07 fitted CPU passes setup and hold in every corner, but the cold
machine setup path still traverses hour decode, division/modulo by ten,
BCD conversion and RTC alarm checking (-0.101 ns with seed 2, -0.469 ns
with seed 3). Replace only the binary-to-BCD function with a complete
combinational byte lookup. No clock stage, state or I/O behavior changes.

The lookup preserves the original 8-bit quotient's low four bits for
every input, including invalid CMOS values from 100 to 255. In particular,
160 encodes as 00, matching the original arithmetic rather than a decimal
hundreds-digit truncation rule. Unknown input bits produce the original
unknown result in four-state simulation.

## Verification

`scripts/test_rtc_bcd_lookup.sh` extracts the actual old function from
commit 5198af1 and the candidate from the current RTL. A whole-module guard
rejects changes outside that function. Yosys proves equality for all
256 concrete byte values; a deliberately incorrect entry at input 10 is
rejected. Icarus compares 4354 concrete/X/Z cases; Verilator compares all
256 concrete cases. The candidate conversion passes strict Wall lint.

The complete RTC retains five existing unused-bit warnings. An explicit
comparison against baseline Wall diagnostics rejects new or changed
warnings and permits only the two eliminated quotient/remainder warnings.
No warning class is disabled for this check.

All four existing RTC banks pass with both simulators: CMOS/calendar and
MR BIOS date/reset handling, reset flag retention/clearing, all 16 periodic
rate codes including OS/2's 32 Hz mode and read collisions, and the clock
divider. The compiled clock-only test covers one complete physical second
at 50 MHz (50,000,000 cycles, 32768 base ticks, one second tick). Source
hashes match after the tests. Expected results are unchanged.

Evidence: `docs/evidence/rtc-bcd-lookup-20261002`. No complete CPU regression
or hardware test was performed. The physical improvement requires a new
frozen-source fit; functional proof alone does not establish timing closure.
