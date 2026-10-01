# P05: dedicated DDR forwarding for the SDRAM clock

The corrected external budget exposed genuine output hold failures around
-3.1 ns in every new fit. The worst warm slow path uses +5.044 ns clock skew.
Its SDRAM clock traverses the global clock network as ordinary output data,
including a 4.935 ns global-to-output route, and reaches the pin substantially
later than the address-register clock-to-output path.

`PCAT-286.sv` now forwards `CLK_50M` through `altddio_out`, with constant high
data on rising edges and constant low data on falling edges. This uses the
dedicated output DDR cells, retaining a 20 ns period, zero nominal phase,
continuous clocking and no CPU or SDRAM /2 divider. It adds no PLL phase
change. `SYSTEM.sdc` retains its generated-clock relationship and all the
corrected input/output delays. A new fit must account for the actual clock
path through the DDR cell rather than treating the pin as an ideal clock.

`scripts/test_at_sdram_clock.py` extracts the actual source instance and
simulates it with the official Quartus `eda/sim_lib/altera_mf.v` primitive.
It checks equality to the input after all 2,000 transitions and stable pulses
between edges. `test_at_profile_elab.sh` also passes; its explicitly named
elaboration-only stub checks configuration connectivity and is not physical
timing evidence. No vendor simulation library is committed.

Example waveform check from WSL after extracting the library from the fixed
Quartus container image:

```sh
python3 scripts/test_at_sdram_clock.py build/sdram-ddio-waveform-20261001 \
  build/sdram-ddio-waveform-20261001/altera_mf.v
```

The source/primitive waveform receipt is retained in
`docs/evidence/sdram-clock-forwarding-20261001`. The isolated fresh fit is
`build/sdram-ddio-clock-fit-20261001`; subsequent CPU variants use the same
forwarding implementation. Functional clock forwarding alone does not prove
positive pin setup/hold, SDRAM board sign-off, or hardware boot success.
Retain the conditional chip/flight/load qualifications from
[P05_SDRAM_BUDGET_20261001.md](P05_SDRAM_BUDGET_20261001.md) and the platform
coverage qualifications from
[P05_TIMING_COVERAGE_20261001.md](P05_TIMING_COVERAGE_20261001.md).

Primary primitive reference: the official installed Quartus 17.0.2
`altera_mf.v`, `altddio_out` module and device-family feature model. Also see
Intel's [ALTDDIO IP guide](https://www.intel.com/programmable/technical-pdfs/683148.pdf).

## Isolated fitted results

| Corner | CPU setup | Global hold | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -3.765 | -2.019 | +5.470 | -2.019 |
| 7_slow_1100mv_-40c | -3.632 | -2.072 | +6.191 | -2.072 |
| MIN_fast_1100mv_100c | +7.475 | -2.006 | +9.726 | -2.006 |
| MIN_fast_1100mv_-40c | +9.259 | -2.098 | +11.182 | -2.098 |

The output clock path contains the physical DDR cell at DDIOOUTCELL_X70_Y0_N27,
including 1.716 ns mux-to-output and 2.454 ns pad delay in the warm slow hold
path. That path has +3.967 ns skew, down from +5.044 ns, so hold improves by
about 1 ns but remains negative in all corners. A further real interface
clock phase correction is required; changing only SDC phase would be invalid.
CPU setup and some bridge/cache paths vary adversely in this new placement,
which does not include the newer CPU completion/range/frame rewrites. This is
a failing checkpoint, not global timing closure.
