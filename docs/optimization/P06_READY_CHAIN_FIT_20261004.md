# P06 READY-chain candidate: measured FPGA cost and timing

## Scope and source identity

The general fetch turnaround correction is described in
[the functional report](P06_READY_CHAIN_CORRECTION_20261004.md). This report
records its all-features Quartus candidate; it does not close physical timing.

The frozen snapshot contains 1,350 files. Its base revision is
`1a4f2ecbd90b7fc5b024b2051fe1e3bf1ba4e4e7`. The functional correction and
selected generated CPU are now committed as
`719de5ac508fe55a0bfc4503a2a00cf213924dc6`. That commit also includes tests and
evidence completed after measurement; the complete compiled snapshot remains
the authority for all 1,350 build inputs.
The snapshot manifest SHA256 is
`44893f894cdb5bba6a87c63fc1c3b5f2c261731cf270b36d5eb410fea8fc4c05`.
The manifest, dirty-source patch and complete compiled source archive preserve
the actual candidate independently of that base revision.

The final [functional binding](../evidence/p06-ready-chain-20261004/functional-sources.json)
binds 331 frozen inputs to directed fetch, original R0 ideal/composed PCAT,
all-profile CPU compatibility and AT diagnostic receipts. The final
[fit audit](../evidence/p06-ready-chain-fit-20261004/run/fixed50-fit-audit.json)
verifies those inputs against the compiled snapshot. CPU regression was still
running at measurement time. Its later [source-frozen final run](../evidence/p06-ready-chain-regression-20261004/v3/receipt.json)
passes, as does the separate composed standalone acceptance; see the functional
report for their exact scope. Hardware confirmation is pending.

Physical clocks remain 50 MHz, placement seed remains 1, and config/SDC are
byte-identical to the accepted floppy build. SB, OPL2, CMS, Tandy audio and MIDI
remain enabled. The same Quartus Docker image was used:
`sha256:1fba8b9347973365e9f7851d73f7cb035e38fefb827cbf0ed2ea291b48bdf6dd`.
Compilation plus detailed four-corner STA took 37 minutes 46 seconds. Both
owned containers exited; no Docker container remained active at audit time.

## Resource result

| Fitted resource | Accepted floppy build | READY-chain candidate | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 31,278 | 30,881 | -397 |
| Placed ALMs | 36,619 | 36,395 | -224 |
| Placed device utilization | 87.38% | 86.84% | -0.53 percentage points |
| Registers | 38,073 | 37,994 | -79 |
| Block memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K / DSP / PLL | 416 / 39 / 3 | 416 / 39 / 3 | 0 |
| Inclusive CPU equivalent ALMs | 7,280.9 | 7,228.2 | -52.7 |
| Inclusive CPU placed ALMs | 8,101 | 8,025.5 | -75.5 |
| Inclusive CPU registers | 5,351 | 5,350 | -1 |

The candidate therefore adds no measured full-machine resource cost in this
fit. Global packing and placement can change these totals; the reduction is
not a guaranteed isolated saving from the new logic. Inclusive CPU hierarchy
figures are not additive standalone synthesis costs. The
[block breakdown](../evidence/p06-ready-chain-fit-20261004/blocks.md) and
[CPU record](../evidence/p06-ready-chain-fit-20261004/cpu.json) preserve the
fitted attribution.

## Timing result

Worst margins across slow/fast, -40/100 C corners, in ns:

| Group | Previous setup | Candidate setup | Candidate hold |
| --- | ---: | ---: | ---: |
| Global | -16.531 | -15.190 | +0.058 |
| CPU | -16.531 | -15.190 | +0.121 |
| CPU to bridge | -5.899 | -8.014 | +0.327 |
| Bridge to CPU | +1.542 | +0.331 | +0.276 |
| SDRAM input | +5.185 | +5.185 | +5.000 |
| SDRAM output | +4.492 | +4.626 | +0.221 |

The CPU/global setup improves by 1.341 ns. CPU-to-bridge setup worsens by
2.115 ns. There is also a -0.009 ns HDMI setup entry in the native STA summary.
The audit therefore reports **MEASURED_FIXED50_TIMING_FAIL**. Positive hold
margins and a successfully generated RBF do not establish 50 MHz timing closure.

The worst CPU path runs from prefetch queue `head_q[2]` to `gpr_q[80]`, with
34.469 ns data delay. The worst CPU-to-bridge path runs from queue `count_q[1]`
to bridge `STATE_WAIT`, with 27.296 ns data delay. Full-path reports and all
four corners are preserved in the archive for the separate closure task.

The audit retains inherited platform I/O coverage and the existing conditional
SDRAM device/flight-time budget. No timing exception, clock, PLL or resource
feature was changed to improve the report. Quartus Fmax for FPGA_CLK2_50 is
28.42 MHz in its worst reported corner; that STA figure is not a measurement
of the user's selected virtual CPU profile or CheckIT throughput.

## ROM, archive and RBF

The actual compiled M10K image verifies all 1,024 words: 743 valid and 281
invalid, with the unchanged 1024 x 9 dimensions and read alignment parameters.
The raw `.hdl.mif`, golden contract, compile log, reports, generated-source
identity and auditors are retained. Deterministic gzip archives record both
compressed and original SHA256 values; the complete source tar records each
frozen and compiled hash. See the
[measurement receipt](../evidence/p06-ready-chain-fit-20261004/receipt.json) and
[archive manifest](../evidence/p06-ready-chain-fit-20261004/archive-manifest.json).

RBF candidate:

`build/p06-ready-chain-allfeatures-20261004-v1/work/output_files/PCAT-286.rbf`

Size: 4,124,316 bytes. Generated: 2026-10-04 19:37:43 Europe/Madrid.
SHA256: `6b0b1dd42f756908298b076a12210630e6a1b0d314950635b391ba0c87ec37f1`.
The RBF and SOF remain in the build directory; their identities are archived.

Hardware follow-up uses the unchanged `T286REF` executable at 20 and 25 MHz,
with **Reset & apply settings** after each OSD selection. Retain both complete
CSV files. R0 monotonicity is the first target; CHECKNUM at 20/25/MAX adds mixed
workload evidence. This candidate preserves the hardware-confirmed floppy fix
and write protection. P06/P12 historical calibration and native cycle accuracy
remain separate from this pipeline correction.
