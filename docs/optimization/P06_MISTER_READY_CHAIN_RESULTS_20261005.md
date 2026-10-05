# P06/P12: eight-profile MiSTer READY-chain follow-up

## Scope and result

The user supplied new T286REF captures for all eight OSD selections after
testing the READY-chain candidate. The first 20/25/MAX batch was followed by
6/8/10/12.5/16 measurements requested on that same RBF with reset applied.
The association is user-reported; the loaded FPGA image is not independently
read back. Candidate identity is preserved in the
[fit report](P06_READY_CHAIN_FIT_20261004.md):
`6b0b1dd42f756908298b076a12210630e6a1b0d314950635b391ba0c87ec37f1`.

All **336 samples and 48 summaries** pass the unchanged raw validator,
including fixed work, seven repetitions, timer arithmetic and register
signatures. All 21 adjacent-profile case comparisons are strictly faster:
even each faster profile's maximum gross time is below the preceding one's
minimum. The local 20/25 MHz R0 inversion is removed in hardware.

These are elapsed PIT input ticks conditional on the stated timer assumptions.
They do not establish isolated CPU cycles, calibrated physical clock rates,
pin-exact bus phases or complete historical-profile accuracy. No RTL,
configuration, workload, expected signature or synthesized image changes
belong to this measurement milestone.

## Current measurements

R0 exercises register arithmetic; B0 branches and prefetch; M0 aligned RAM
reads/writes/RMW. Gross includes the common LOOP and measurement setup.
CHECKNUM is a separate benchmark execution, transcribed from the supplied
screenshots. Smaller gross ticks mean less elapsed time.

| Profile | CHECKNUM Dhrystones | Whetstones K | R0 gross | B0 gross | M0 gross |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6 MHz |1629 |32.0 |971 |1429 |1894 |
| 8 MHz |2181 |41.7 |729 |1073 |1424 |
| 10 MHz |2631 |49.6 |585 |859 |1141 |
| 12.5 MHz |3234 |61.6 |468 |688 |913 |
| 16 MHz |3854 |74.3 |369 |540 |753 |
| 20 MHz |4250 |82.9 |300 |435 |666 |
| 25 MHz |5139 |95.1 |253 |376 |561 |
| MAX |6906 |121.6 |204 |247 |415 |

## Difference from the previous OSD RBF

The [previous capture](P06_MISTER_REFERENCE_RESULTS_20261004.md) is retained
unchanged. Percentages below are `100*(new_gross/old_gross-1)`; negative means
less elapsed time, not the same percentage of throughput gain.

| Profile | R0 elapsed | B0 elapsed | M0 elapsed | CHECKNUM Dhrystones | Whetstones |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6 MHz |0.00% |0.00% |+6.05% |-2.69% |-0.62% |
| 8 MHz |0.00% |+0.09% |+2.67% |0.00% |-0.24% |
| 10 MHz |+0.17% |0.00% |+0.80% |-2.37% |-4.62% |
| 12.5 MHz |-0.21% |0.00% |+0.22% |0.00% |+0.33% |
| 16 MHz |+0.27% |+0.19% |+0.53% |0.00% |-0.40% |
| 20 MHz |+0.67% |0.00% |-3.06% |-2.55% |-1.43% |
| 25 MHz |-19.94% |-3.59% |-6.19% |+2.31% |+3.48% |
| MAX |-5.99% |-9.19% |-2.81% |0.00% |0.00% |

The 25 MHz R0 median changes 316 to 253 ticks. Its 253 maximum is below the 299
minimum at 20 MHz; the new 25 MHz median needs 15.67% less time than20MHz.
R0/B0 at 6..16 are almost unchanged. The new 6 MHz M0 range 1888..1897 is entirely
above the previous 1785..1787; at 8 MHz 1423..1425 is above 1387..1390. This
penalty exceeds the within-capture variation. Its cause remains unassigned
until an unchanged-workload CPU/PCAT trace distinguishes CODE, READ, WRITE
and RMW effects. One seven-repetition capture is not an independent series
of cold/warm reboots.

The 10 MHz Whetstone drop is not reproduced at similar magnitude by these
three directed kernels. At 20 MHz M0 improves while CHECKNUM decreases.
Neither observation identifies RAM waits as the unique mixed-workload cause.

## Historical references

The analyzer revalidates archived native/physical raw inputs and their bound
CSV hashes before comparing them. Against native 286 visible zero waits:

| MiSTer profile | R0 elapsed difference | B0 elapsed difference | M0 elapsed difference |
| --- | ---: | ---: | ---: |
| 6 MHz versus native6 |-27.48% |-24.75% |-12.07% |
| 12.5 MHz versus native12.5 |-27.22% |-24.48% |-11.70% |

Against the physical nominal 6 MHz capture, differences are -30.34%/-32.94%/
-12.72%. The nominal 12 MHz physical capture remains a separate reference:
scaling its ticks illustratively by 12/12.5 gives -30.95%/-35.49%/-39.88%.
That assumes equal CPU cycles and does not independently rescale fixed board,
ISA, timer-port or refresh delays. Actual physical clocks and the board's
READY policy are still uncalibrated.

Native T286REF measurements at 8/10/16/20/25 MHz remain separate pending work
at this milestone. The analyzer includes archived Automatic and visible 0/1/2
controls for 6/12.5 rather than treating config zero as zero extra waits.

R0 gross minus its LOOP baseline conditionally normalizes to approximately
10 nominal clocks per iteration at 6..12.5 MHz, consistent with Intel's
`2+2+3+3` arithmetic forms. This is a consistency check, not an isolated EU
measurement. Native LOOP and immediate-form charges differ from Intel;
gross emulator disagreement alone is not a reason to alter those CPU minima.
See the [Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md).

## Decision and remaining work

Preserve nominal frequency generation and MAX. First trace the 6/8 MHz M0
penalty against the previous and current frozen CPU with identical initial
state, first ideal RAM and then the actual PCAT memory chain. Qualify the
taken-target/prefetch and bridge admission epoch contracts separately; select
board READ waits only from an identified causal model. No global benchmark
multiplier or workload-specific instruction exception follows from these CSVs.

Subsequent source-bound checks now provide the
[6 MHz M0 causal diagnosis](P06_M0_PHASE_DIAGNOSIS_20261005.md), the
[Intel branch/target and bus-epoch audit](P06_HISTORICAL_TIMING_AUDIT_20261005.md),
and [all fourteen native reference controls](P06_NATIVE_ALL_PROFILES_20261005.md).
The composed PCAT fixture reproduces the 6 MHz memory penalty; its bounded
8 MHz phase controls do not reproduce that hardware observation. Taken
branch target-length timing is a demonstrated gap that needs a general
handoff protocol, while R0 and LOOP minima remain supported by Intel.
These findings do not justify changing the nominal frequency generator or
selecting a universal motherboard READ-wait count.

The existing physical 50 MHz fit still fails setup, worst -15.190 ns with minimum
hold +0.058 ns. Hardware fixed-work acceptance does not close that separate gate.
This archive runs data analysis only; no new CPU regression or fit is claimed.

## Evidence and reproduction

The [manifest](../evidence/p06-mister-ready-chain-20261005/manifest.json)
preserves byte-exact raw inputs, both screenshots, complete validator receipts,
statistics, comparisons and the three analyzer/validator source snapshots.
The [analysis](../evidence/p06-mister-ready-chain-20261005/analysis.json)
records all measured ranges and limits. Original USB inputs are unchanged.

```powershell
python -B scripts/analyze_p06_mister_ready_chain.py --input-dir docs/evidence/p06-mister-ready-chain-20261005/raw --output docs/evidence/p06-mister-ready-chain-20261005
```

This recomputes derived files, revalidates every sample and checks immutable
input hashes before/after output writing. Existing source snapshots cannot be replaced by
changed bytes. Native 0-wait and physical primary inputs are validated again;
their independent runtime/board qualification stays with the earlier reports.
