# P06 replay head timing work — 2026-10-05

## Purpose and unchanged behavior

The previous all-features candidate's worst setup path starts in the target
replay's 80-bit M10K storage and returns to its read pointer through decoder,
timing policy and exception backpressure. Its setup slack is −19.145 ns at a
physical 50 MHz. This is an internal timing problem independent of outstanding
MiSTer measurements of the historical speed profiles.

Store the next replay byte directly at slot zero. An accepted consume shifts
the unread bytes; an accepted capture appends after that shift. The total
capture counter still rejects an eleventh byte, even after earlier consumption.
Reset, cancellation and new-epoch priority are unchanged. No additional edge,
historical clock, wait state or public handshake was introduced.

The active CPU generator records the new helper hash. Generated CPU and event
RTL bytes remain identical. No PLL, profile divisor, SDRAM relationship, timing
constraint, OSD setting or architectural decoder was changed. The earlier RBF
remains the hardware measurement reference.

## Directed verification

| Gate | Result |
| --- | --- |
| Existing unchanged replay unit | 246 checks in both Icarus and Verilator PASS |
| Strict Verilator helper lint | PASS |
| Formal state relation / output equivalence | Induction PASS for arbitrary control and byte inputs after reset |
| Corrupted capture and broken pop negative controls | Both rejected with counterexamples |
| Full CPU handoff integration | 777 cases per simulator, all eight profiles PASS |
| Comparison with the prior accepted directed receipt | Every result record, clock, budget, event frame, fault, cancellation, HOLD and MAX full raw-stream digest identical |
| Generic Yosys synthesis and structural check | PASS |

The formal instrumentation only adds observation ports to unchanged sequential
bodies. The invariant equates the total write count, read offset and ordered
unread bytes. Initialized state is zero and step one resets both implementations.
The first 24-step bounded SAT attempt timed out at 60 seconds; that record is
preserved. Adding explicit state invariants allows a successful induction proof,
without changing the implementation or output assertions.

Generic Yosys logic changes from 243 to 251 cells and from 92 to 88 register bits.
These are generic mapped cells, **not Cyclone V resource estimates**. Quartus
placement, setup and hold must be measured before assessing the physical benefit.

No new instruction behavior was added. The earlier raw CPU/SingleStep evidence
still applies to the unchanged CPU inputs. The complete compatibility regression
remains **USER_DEFERRED** as requested; these results are directed qualification.

## Evidence and fitted result

The [sealed packet](../evidence/p06-replay-head-20261005/manifest.json) preserves
tested sources, unchanged benches, exact baseline comparison, proof scripts,
negative controls and simulator logs. Compiler objects and executables are not
archived.

Verified implementation commit: `c90f7b5`. A fresh all-features fit started at
2026-10-05 07:50:06 UTC under
`build/p06-replay-head-allfeatures-20261005-v1`, at the existing physical 50 MHz.
Compilation completed in 30 min 45 s, followed by 3 min 22 s of detailed STA.
All features, including Adlib/OPL2, remain enabled.

| Metric | Previous target-handoff fit | Registered-head fit | Delta |
| --- | ---: | ---: | ---: |
| Worst global / CPU setup | −19.145 ns | −16.044 ns | +3.101 ns |
| Worst global hold | +0.002 ns | +0.055 ns | +0.053 ns |
| Worst global recovery | +1.680 ns | +1.981 ns | +0.301 ns |
| Worst global removal | +0.198 ns | +0.160 ns | −0.038 ns |
| Equivalent ALMs | 31,018 | 31,108 | +90 |
| Physical ALMs used in final placement | 36,490 | 36,490 | 0 |
| Physical placed device occupancy | 87.068% | 87.068% | 0 |
| Total registers | 38,024 | 38,127 | +103 |
| Block memory bits | 3,301,099 | 3,301,019 | −80 |
| M10K | 417 | 416 | −1 |
| DSP / PLL | 39 / 3 | 39 / 3 | 0 / 0 |

The replay now uses no M10K and stores its bytes in registers, as intended.
The inclusive CPU hierarchy changes from 7,385.8 to 7,357.3 equivalent ALMs,
8,177.8 to 8,156.3 placed ALMs, and 5,417 to 5,492 registers. Whole-design
packing and sharing change beyond this hierarchy; these are measured fitted
attributions, not additive standalone module costs.

Correction recorded during the next fit review: both original Fitter reports
give a whole-device final-placement count of 36,490. The earlier table used
36,489.0 from hierarchy attribution. The physical totals above now consistently
use the global Fitter count; the original sealed evidence remains unchanged.

The worst path now starts at the ordinary prefetch queue's `head_q[2]` and
ends at the microsequencer's `micro_entry[1]`, with 31 logic levels and 35.332 ns
data delay at the slow −40°C corner. The replay RAM path is no longer the
reported worst path. Setup remains negative: **this fit does not close at
50 MHz**. There are also setup violations in CPU integration, memory/cache,
SDRAM ownership and video paths.

The reported SDRAM input setup/hold minima remain +5.185 / +5.000 ns;
output setup/hold minima are +4.260 / +0.340 ns. No constraint/configuration,
PLL or source clock relationship was changed. The four-corner issue counts
retain the inherited platform limitations, with no reported timing loops or
latches. Positive constrained hold/recovery/removal does not certify general
hardware stability.

RBF: `build/p06-replay-head-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`

SHA-256: `c073f834304a7c16c64c071888ea11e23b7788db80175ce3f27d68e29939dd87`

Size: 4,145,652 bytes. Hardware testing is still pending. Directed cycle and
functional equivalence provide no expected benchmark change; this is a physical
timing implementation change. The earlier RBF remains available for consistent
profile measurements.

The [fit packet](../evidence/p06-replay-head-fit-20261005/manifest.json) retains
all 1,374 effective frozen source files, original reports, artifact identities
and comparisons. Every directed CPU/generator proof input matches the fitted
source. `build_id.v` has the sole declared compile-generated BUILD_DATE update.
All baseline SDC, QSF, QIP, QPF and TCL hashes remain unchanged. Snapshot deltas
also retain verification files added before this fit; they are not additional
production RTL changes.

After archive byte verification and confirmation that simulator processes had
finished, the four owned proof/integration work directories and temporary
collector were removed: 609,533,055 logical bytes. The active frozen fit and
earlier measurement RBF were retained. The cleanup receipt is in the packet's
directory. After the fit packet's byte verification, the compiler databases,
duplicate work sources and collector were removed: another 322,675,791 logical
bytes. RBF/SOF and compact reports remain available, the RBF hash was checked
again after cleanup, and no Docker container remains active. Free host space
after cleanup was approximately 25.20 GiB on C: and 150.09 GiB on D:.
