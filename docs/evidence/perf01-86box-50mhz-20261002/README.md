# PERF01: 86Box 50 MHz comparison evidence

See [the measurement report](../../optimization/P11_86BOX_50MHZ_COMPARISON_20261002.md)
and [numeric summary](summary.json).

The bundle retains completed native 25/50 MHz controls, one SPK286 50 MHz run
and a native 50 MHz repeat: exact guest outputs/status, commands, hashes,
runtime CPU-clock/dispatcher samples, logs and final screenshots. Initial
profile hashes and build identities prove the paired configuration and CPU
source/options match. Disk/program/executable binaries stay in the local build
workspace. Original source-disk hashes agree before and after every run.

Native 50 MHz first-run host teardown RC -6 is retained separately from DOS
RC0; the repeat has identical scores/ticks and a normal host exit. Whole-program
BIOS-tick duration includes adaptive iteration calibration. Use the numerical
rates for workload performance and the receipts for acceptance/provenance.

The MiSTer row is the earlier user-reported candidate measurement, with its
own [hardware observation evidence](../perf01-bridge-hardware-20261002/README.md).

[PCAT clock/enable/policy](pcat-clock-policy.json) retains the relevant source
hashes matched against the fitted candidate. Raw console logs retain terminal
output, including trailing spaces and blank lines.
