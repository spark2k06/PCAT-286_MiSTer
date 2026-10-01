# P05: conditional external SDRAM timing budget

Date: 2026-10-01. Clock period remains 20 ns (50 MHz), with the existing
same-phase forwarded `SDRAM_CLK`. No path is excluded by this change.

## Device evidence and assumptions

The supplied photo shows a Winbond W9825-family SDRAM. The wires obscure the
complete suffix and the board revision. It is insufficient to identify the
speed grade or measure board delays. This budget is conditional on a
W9825G6KH/JH-compatible module, not a certification of that unidentified board.

The Winbond-authored [KH datasheet, A05, section 9.5](https://docs.rs-online.com/eb6b/0900766b817040a8.pdf)
and [JH datasheet, A02, section 9.5](https://media.digikey.com/pdf/Data%20Sheets/Winbond%20PDFs/W9825G6JH.pdf)
give the same conservative envelope for the grades in their tables at CL2:

| Parameter | Budget |
| --- | ---: |
| Chip clock to valid read data, maximum `tAC` | 6 ns |
| Chip read data hold, minimum `tOH` | 3 ns |
| Data/address/command/CKE setup, maximum required | 1.5 ns |
| Data/address/command/CKE hold, maximum required | 1 ns |

The chip specifications assume their stated voltage, temperature, loading and
signal-transition conditions. A slower edge needs the datasheet compensation;
neither edge shape nor load is proven by the photo. The four FPGA timing
corners do not certify operation of a commercial-temperature SDRAM at -40 C
or 100 C.

For the PCB part of the timing model, independently bound one-way clock and
data flight from the FPGA pins to the chip pins to **0 through 1 ns** each.
This is an engineering assumption with deliberately independent worst-case
skew. It is not a measured flight time. A different module, longer wiring or
signal-integrity issue requires new bounds and a fresh timing analysis.

## Constraint derivation

Let `C` be external forwarded-clock flight and `D` be external data flight.
The generated clock already includes the fitted FPGA clock-output path; do
not double-count that internal latency in these external delays.

| Delay | Equation | Previous | Corrected |
| --- | --- | ---: | ---: |
| Input maximum | `max(C) + tAC + max(D)` | 6 ns | 8 ns |
| Input minimum | `min(C) + tOH + min(D)` | 3 ns | 3 ns |
| Output maximum | `tSU + max(D) - min(C)` | 2 ns | 2.5 ns |
| Output minimum | `min(D) - max(C) - tH` | **+1.5 ns** | **-2 ns** |

For zero external skew, positive chip hold requires a negative minimum output
delay. The inherited positive minimum relaxed the check instead. The
corrected value tightens hold by **3.5 ns**, and is expected to expose
violations in old fits. The minimum/maximum roles are documented in Intel's
[set_output_delay help](https://resources.altera.com/quartushelp/16.1/analyze/sta/sta_db_set_output_delay.htm).

Apply the output constraints to DQ, DQM, address, command, bank address and
CKE pins, including A11/A12 used as byte masks by MiSTer SDRAM modules. The
read constraint applies to all sixteen DQ pins. The SDRAM clock output is the
timing reference, not a data output requiring an output-delay constraint.

## Validation status

The constraint-only analysis of the preceding frozen fit and the subsequent
fresh fit will be recorded with their source and bitstream identities. A
constraint-only report is not evidence that the fitter repaired hold. Closure
requires the stricter constraints to be present during a new fit, with setup
and hold positive in every corner.

Physical validation of the user's module remains pending. This change does
not change SDRAM phase, CPU frequency, CAS latency or controller sequencing.

## Constraint-only experiment on the preceding fit

The frozen arithmetic fit was reanalysed with only `SYSTEM.sdc` replaced.
There was no synthesis, placement, routing or bitstream change. All 96
selected internal setup/hold and global recovery/removal group minima are
identical. External-pin groups and selectors which also include those pins
show the stricter budget. The read setup remains positive:

| Corner | SDRAM input setup | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: |
| 7_slow_1100mv_100c | +3.472 | -0.435 | -3.070 |
| 7_slow_1100mv_-40c | +3.851 | -0.726 | -3.057 |
| MIN_fast_1100mv_100c | +6.819 | +8.187 | -2.504 |
| MIN_fast_1100mv_-40c | +7.336 | +9.498 | -2.583 |

This is an expected failure of the old fit under corrected requirements,
not successful closure. The registered owner entry adds substantial output
setup margin; a fresh fit with this corrected SDC must spend part of that
margin repairing external hold. The [receipt](../evidence/sdram-budget-20261001/receipt.json)
and [full audit](../evidence/sdram-budget-20261001/audit.json) retain identities.
