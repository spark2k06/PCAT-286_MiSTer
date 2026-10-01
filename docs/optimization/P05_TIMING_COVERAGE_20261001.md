# P05: timing coverage and platform qualifications

Date: 2026-10-01. Inventory reference:
`build/protected-data-sdram-entry-fit-20261001/timing`, all four corners.
The new candidates retain the same platform RTL and clock/CDC definitions;
each fresh fit still requires its own `check_timing` and unconstrained report.

## What the timing claim covers

The 20 ns CPU/system clock is real `FPGA_CLK2_50`, not a multicycle CPU
exception or a /2 clock. Global setup/hold and recovery/removal reports cover
the constrained clocked netlist, including the related video PLL outputs,
HDMI transmitter modes, memory port, caches and physical SDRAM owner.
The SDRAM pin delays additionally use the conditional module budget in
[P05_SDRAM_BUDGET_20261001.md](P05_SDRAM_BUDGET_20261001.md).

Positive global reports do **not** mean every platform pin or every HPS
hard-block model has an external timing specification. Retain the coverage
qualifications below alongside any closure table.

## Inventory

| Check | Count | Classification |
| --- | ---: | --- |
| No clock | 3713 | HPS hard-block model families; none are SPK286 or AT owner soft registers |
| Multiple clock | 32 | Two legal modes of the same HDMI clock mux |
| No input delay | 20 | Asynchronous controls / slow external platform interfaces |
| No output delay | 85 | Platform display/audio/control pins and the SDRAM clock reference |
| Partial min/max | 24 | Held CDC payload bounds / controlled HDMI mode selection |
| Loops, latches, partial I/O delays, illegal generated clocks | 0 | Required to remain zero |

The unconstrained-path report is a different inventory: **10 unconstrained
input ports / 126 input paths**, **52 unconstrained output ports / 82 output
paths**, and **zero unconstrained or illegal clocks**. It does not count
explicitly excluded paths in the same way as `check_timing`. A zero count of
unconstrained clocks must never be reported as zero unconstrained I/O.

### HPS model registers

The unclocked families are `sysmem_lite:sysmem` (1239), `h2f_gp` (617), `uart`
(619), `spi` (621) and `hdmi_i2c` (617). The first family consists of the
generated HPS interface model, including `f2sdram~FF_*` nodes. These are not
unclocked CPU pipeline registers. The existing narrowly scoped HPS DDR clock
exceptions do not exclude direct FPGA logic between those domains. This is
fabric timing analysis, not timing verification of the ARM/HPS hard subsystem.

### HDMI clock modes

The 32 nodes comprise `u_at_hdmi_output` pixel/reset registers (including a
duplicated pixel bit) and the `hdmiclk_ddr` output cells. The SDC defines
`AT_HDMI_TX_SCALED` and `AT_HDMI_TX_DIRECT` at the same physical mux output
with the correct master clocks and logical exclusivity. Both selected data
branches are timed. Only the unselected data branch in each mode is excluded.
The mode selector changes while reset is held; its 10 ns payload bound and
hold exception concern that controlled reconfiguration, not ordinary pixels.

### Twenty-four payload bounds

Three bounds cover EGA I/O request, reply and VRAM configuration. Eighteen
cover `at_cdc_snapshot` transfers: video/time statistics, the two OSDs, input/
output/video geometry, CRT350, video options, scanline status, scaler geometry/
frame/aspect, capture bank/frame, shadowmask, adaptive filter and video-output
configuration. The common mailbox holds `payload_q` until the synchronized
acknowledgement returns; capture follows two request synchronizer stages.

One bound covers the reset-controlled HDMI mode selector. The two remaining
bounds cover scaler Avalon read/write command bundles. Reads keep the address
and base frozen until acceptance acknowledgement; writes retain their bundle
for at least six source clocks. The SDC keeps their 10 ns maximum propagation
bounds and cuts phase-dependent hold only on the held bundle. These are
protocol-based constraints. They are not grounds for excluding arbitrary
CPU/video crossings or receiver logic after capture. Source references:
`sys/at_cdc_snapshot.sv`, `sys/at_scaler_config.sv`, `sys/ascal.vhd` and
`SYSTEM.sdc`.

### Platform pins

Buttons, keys, switches and `VGA_EN` have no external phase relationship to a
fabric clock. USER_IO, I2C/interrupt inputs and SDCD/SPDIF need their platform
protocol/CDC assumptions, not invented synchronous input delays. VGA analog,
audio DAC/SPDIF and LED outputs are not an SDR-style data bus sampled by an
external copy of the 50 MHz CPU clock.

HDMI parallel data/clock/audio, I2C, ADC, SD SPI and USER_IO still lack a
complete external receiver/board-delay budget in the inherited platform
constraints. Internal transmitter timing does not certify those pin
interfaces. `SDRAM_CLK` itself is deliberately a generated clock reference,
so its no-output-delay warning is different from missing data-pin delays.

This audit adds no false paths for the uncovered platform pins. Exact module
identification, board flight/load/edge verification and external display/
audio/peripheral sign-off remain physical/platform work. A positive 50 MHz
fabric/SDRAM result must be described with that scope and the SDRAM device
assumptions, without claiming universal board-level sign-off.
