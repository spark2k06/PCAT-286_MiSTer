# P06/P12: MiSTer target-handoff measurements

## Scope and acceptance

The user identifies these measurements as the first target-handoff RBF before
the subsequent timing adjustments:
`build/p06-target-handoff-allfeatures-20261005-v2/work/output_files/PCAT-286.rbf`,
SHA-256 `88f1075046876d13acafde4834a6ed2a0b385e7ec1de51a3d5646342dc1140b1`.
This association is user-reported; FPGA image identity is not independently
read back. The later replay-head and execution-deadline fits have separately
proved directed cycle equivalence, but these captures are not hardware tests
of those later RBFs.

All eight CSVs pass the unchanged T286REF2 raw validator: **336 samples and
48 recomputed summaries**, seven repetitions per case/kind and 256 iterations.
Timer arithmetic, register signatures and fixed work all pass. All 21 adjacent
profile comparisons are strictly faster, including nonoverlapping gross ranges.
MAX preserves every gross median and both CHECKNUM results from the preceding
READY-chain capture. These observations qualify this directed hardware gate;
historical calibration and physical 50 MHz timing closure remain open.

Original CSVs are preserved under their supplied names. `REF125.CSV` is the
12.5 MHz capture and contains the matching nominal metadata. CHECKNUM values
below are transcribed from the two user screenshots and belong to separate
benchmark executions, rather than the fixed-work CSV kernels.

## Current results

Gross is elapsed PIT input ticks and includes LOOP and instrumentation.
Lower gross is faster for the same work. CHECKNUM is a throughput measure;
higher values are faster. Percentages compare with the previous READY-chain
RBF and use `100 * (new / previous - 1)`.

| Profile | Dhrystones | Whetstones K | Dhrystone change | Whetstone change | R0 gross | B0 gross | M0 gross |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 MHz | 1586 | 30.2 | −2.64% | −5.63% | 975 | 1636 | 1892 |
| 8 MHz | 2125 | 39.8 | −2.57% | −4.56% | 731 | 1227 | 1426 |
| 10 MHz | 2560 | 48.3 | −2.70% | −2.62% | 586 | 983 | 1142 |
| 12.5 MHz | 3157 | 58.9 | −2.38% | −4.38% | 470 | 787 | 915 |
| 16 MHz | 3683 | 70.5 | −4.44% | −5.11% | 371 | 618 | 755 |
| 20 MHz | 4143 | 81.1 | −2.52% | −2.17% | 301 | 498 | 667 |
| 25 MHz | 5023 | 91.9 | −2.26% | −3.36% | 254 | 414 | 561 |
| MAX | 6906 | 121.6 | 0.00% | 0.00% | 204 | 247 | 415 |

R0 gross changes +0.17%..+0.54% in the historical profiles. M0 changes
−0.11%..+0.27%. These small aggregate changes do not establish zero effect
on every instruction or exceedance of reboot variation, which was not measured.
B0 changes +14.35%..+14.49% at 6..20 MHz and +10.11% at 25 MHz. Every new
historical B0 sample is slower than every preceding sample at that frequency.
The correction is selective and does not lower MAX.

## Why B0 takes longer

The [Intel timing extraction](P06_INTEL_TIMING_REFERENCE_20261003.md) documents
the taken Jcond/JMP allowance for the next executed instruction's length. B0
executes CMP (2), untaken JNE (3), taken JE (7 plus two target bytes), and
short JMP (7 plus two target bytes), before the common LOOP. The intended
body minimum is therefore **23 nominal processor clocks**, instead of the
old 19-clock body that omitted the two allowances.

Subtracting the baseline median from the gross median and normalizing by
256 iterations, nominal CPU MHz and the assumed PIT input gives approximately
23.00 clocks at 6/8/10/12.5, 23.05 at 16, 23.11 at 20 and 24.31 at 25 MHz.
This matches the directed implementation's 23-clock floor, with additional
dependency/implementation cost at high profiles. At 25 MHz the prior directed
fixture already observed a 24-clock body. Different instrumentation, memory
phase and full-machine dependencies prevent equating that fixture exactly
with the whole DOS measurement.

These normalized differences are conditional consistency checks, **not
isolated EU-cycle measurements**. The gross benchmark includes CALL/RET,
timer I/O and stores, and independent baseline/gross medians are not paired
per-instruction observations. The selective B0 change supports the intended
target-length correction. CHECKNUM's 2.26%..4.44% integer and 2.17%..5.63%
floating-point drops are consistent with a mixed workload paying additional
branch costs; those two aggregate rates cannot uniquely attribute each cycle.

## Native and physical references

All fourteen archived native controls and four physical raw captures are
revalidated, with their original CSV hashes checked. Percentages below compare
gross ticks with native **visible zero waits**; negative means MiSTer takes
less elapsed time. Native Automatic retains its distinct frequency-dependent
memory service costs in the detailed analysis rather than being called zero.

| Profile | R0 versus native | B0 versus native | M0 versus native |
| --- | ---: | ---: | ---: |
| 6 MHz | −27.18% | −13.85% | −12.16% |
| 8 MHz | −27.19% | −13.83% | −11.70% |
| 10 MHz | −27.02% | −13.70% | −11.61% |
| 12.5 MHz | −26.91% | −13.61% | −11.51% |
| 16 MHz | −26.10% | −13.20% | −6.44% |
| 20 MHz | −25.12% | −12.63% | +3.25% |
| 25 MHz | −20.87% | −9.21% | +8.51% |

The B0 gap has narrowed. R0 still has documented native LOOP/immediate-form
timing differences, so matching its native gross rate is not a reason to
replace Intel instruction minima. M0 remains faster through 16 MHz and slower
at 20/25, preserving the earlier workload-dependent memory-service divergence.
This target correction does not resolve the earlier 6/8 MHz M0 phase penalty.

Against physical nominal 6 MHz, current R0/B0/M0 gross differences are
−30.06% / −23.23% / −12.81%. The physical nominal 12 MHz and MiSTer 12.5 MHz
profiles are different frequencies. Their raw differences are −33.43% /
−29.16% / −42.16%; illustrative same-cycle scaling by 12/12.5 gives −30.65% /
−26.21% / −39.75%. Neither comparison calibrates the physical oscillator or
independently rescales fixed board/ISA/refresh delays. A universal multiplier
or inferred motherboard READY count does not follow from these measurements.

## Decision, evidence and reproduction

The hardware results are acceptable for the targeted change: correct fixed
work, ordered profiles, preserved MAX and the expected branch body interval.
Keep the correction and resume physical timing work with no benchmark retune.
P06/P12 historical calibration remains open; complete regression stays
**USER_DEFERRED**. This analysis does not run a new emulator, CPU regression
or synthesis and does not change RTL, profiles, OSD or constraints.

The [evidence manifest](../evidence/p06-mister-target-handoff-20261005/manifest.json)
preserves all eight byte-exact CSVs, both screenshots, validator receipts,
statistics, comparison inputs and analyzer source snapshots. Original F:
files are unchanged. Analysis uses the bundled Python with bytecode disabled;
no VHD, simulator objects or temporary synthesis databases are created.

```powershell
python -B scripts/analyze_p06_mister_target_handoff.py --output docs/evidence/p06-mister-target-handoff-20261005
```

Seven repetitions within one capture per profile do not measure independent
boot variability. Nominal PIT input and reload remain assumptions; timer
endpoints cannot exclude whole-period stalls. The result proves neither
cycle-exact physical AT behavior nor timing closure of the fitted FPGA.
