# Active-options regression evidence

The complete run is retained under
`build/full-regression-posted-pit-active-20261002`. It freezes the PCAT sources
and uses only P01/P02/P05/P06/P07 enabled from `config.tcl`. Initial failures
and later replays are separate records; no initial result is overwritten.
The complete regression is still running when this first receipt is recorded.

## Restored verification package

`restored-unit-package.json` records 23 upstream unit banks missing from the
vendored package despite registration in `scripts/test_units.sh`. Every bank
passed Verilator and Icarus against the frozen PCAT CPU and generated microcode
with active options. The receipt identifies upstream revision, exact test
bytes, unchanged CPU hashes, commands and original log hashes. The validated
test files are restored under `vendor/spk286/sim/unit`; existing files and
architectural assertions are preserved. No production RTL is changed.

The full suite also finds historical compiler fixtures and diagnostic-script
issues. The package restoration is a verified coverage repair, not an overall
regression PASS or hardware acceptance. Those results are recorded separately
when the complete run finishes.
