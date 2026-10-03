# P06 provisional timing components

CPU-only timing components staged in PCAT for directed development. They are
not selected by the production QIP and introduce no OSD/config option. Keep
them separate from the existing functional engine until the stated milestone
contracts and instruction/board coverage are validated. This directory is
not a second CPU implementation.

`p06_clock.sv` emits 6 MHz processor boundaries and 12 MHz phase events from
the common 50 MHz clock. Its static MAX form has no state or historical delay.
Sample enables on the rising fabric edge; never use them as generated clocks.

See [the contract](../../docs/optimization/P06_TIMING_CONTRACT_20261003.md)
and [implementation progress](../../docs/optimization/P06_PILOT_PROGRESS_20261003.md).
Run the relevant stage from WSL/Linux with a fresh output directory:

```sh
python3 scripts/run_p06_pilot.py --stage clock --output build/p06-clock-repeat
```

The runner checks lint, Icarus/Verilator, a failing mutation and generic
Yosys synthesis. Generic cells/register bits are not Quartus ALMs or STA.
