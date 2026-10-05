# P06/P12 target-length candidate — 2026-10-05

## Delivered behavior

Taken Jcond/JMP and the documented CALL/RET forms now retain their source
retirement until the next executed instruction's encoded length is known.
Intel's one-clock-per-byte allowance includes prefixes, ModR/M, displacement
and immediate bytes. LOOP/LOOPE/LOOPNE and IRET do not acquire that allowance.
JCXZ uses its documented 7/4 taken/not-taken base.

A shared syntax classifier previews the target without changing architectural
IP, registers, FLAGS or memory. Up to ten captured bytes are replayed once
through ordinary execution. Actual READY, queue availability, source operand
completion, events, faults, HOLD and redirect ownership remain dependencies.
Invalid/unavailable successors use an explicitly estimated historical fault
duration; ordinary execution retains the architectural fault and fault IP.

This also fixes a separate functional defect: a completed legal ten-byte
instruction could demand byte eleven through stale completion context and
raise #GP. A genuine eleven-byte encoding still faults at its first prefix.
MAX bypasses historical handoff delays; comparisons use the corrected raw CPU.

The OSD retains MAX, 6, 8, 10, 12.5, 16, 20 and 25 MHz. No frequency divisor or
memory-clock relationship was changed. Select the profile and use
**Reset & apply settings** before measuring.

## Validation scope

The user explicitly deferred the full regression. Its partial record is
`USER_DEFERRED`; no complete-regression PASS is claimed.

| Directed gate | Result |
| --- | --- |
| Preview vectors / default decoder equivalence, each simulator | 3,110 / 49,152 PASS |
| Source timing, retained handoff, replay and metadata | PASS, with negative mutation controls |
| Full CPU handoff integration, each simulator | 777 cases across all eight profiles PASS |
| Legal-ten/invalid-eleven public CPU unit, each simulator | 10 cases / 1,097 checks PASS; old CPU fails negative control |
| Corrected raw CPU | Strict lint, dual reset/state smoke, 470 SingleStep stack/control samples and Yosys PASS |
| Composed AT machine | All eight directed profile runs PASS |
| Completed compatibility runs | 177 Icarus + 56 Verilator records; 22 exact MAX raw-stream pairs and 56 canonical dual pairs |
| IOPL at 6 MHz | 2,772 cases / 49,334 checks PASS in Verilator |

The 26-bank compatibility driver hit its external 300-second wall limit during
the large IOPL Icarus fixture. A bounded observer demonstrated normal temporal
progress; the exact fixture then passed in Verilator with unchanged assertions
and stimulus. The completed records were reconstructed from logs and complete
stream digests. They are not represented as a complete 26-bank receipt; the
unfinished remaining matrix is explicitly recorded.

The original B0 executable and kernels remain unchanged. Its net interval is
now exactly **23 clocks/iteration at 6, 12.5 and 20 MHz**, matching the Intel
no-added-wait lower bound. At 25 MHz it is **24 clocks/iteration**: target
availability still adds an implementation/dependency extension. This does not
justify changing the nominal MHz. The existing passive extension flag does not
account for this late qualification, as documented in the detailed validation.

## Fit cost

Fresh all-features compile, seed 1, physical 50 MHz. Adlib/OPL2 stays enabled.
Baseline: `build/p06-ready-chain-allfeatures-20261004-v1`.

| FPGA resource | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 30,881 | 31,018 | +137 |
| ALMs used in placement | 36,395 | 36,489 | +94 |
| Placed device occupancy | 86.841% | 87.065% | +0.224 percentage points |
| Registers | 37,994 | 38,024 | +30 |
| Block memory bits | 3,301,019 | 3,301,099 | +80 |
| M10K | 416 | 417 | +1 |
| DSP / PLL | 39 / 3 | 39 / 3 | 0 / 0 |

The inclusive CPU hierarchy needs 7,385.8 equivalent ALMs and occupies 8,177.8
placed ALMs (+157.6 / +152.3), with 5,417 registers (+67) and two M10Ks (+1).
Whole-design deltas include sharing, optimization and packing; they are not a
sum of standalone module costs. The replay's 80 stored bits infer a M10K.

## Timing and artifact

| Worst reported slack | Candidate |
| --- | ---: |
| Global / CPU setup | **−19.145 ns** |
| Global hold | **+0.002 ns** |
| CPU hold | +0.119 ns |
| SDRAM input setup / hold | +5.185 / +5.000 ns |
| SDRAM output setup / hold | +5.002 / +0.108 ns |

Setup remains open and is worse than the prior −15.190 ns baseline. The worst
path starts at the target replay RAM output and returns to its read pointer
through 31 logic levels. The detailed hierarchy identifies the replay's own
80-bit storage, rather than the machine DATA read buffer. Positive hold is only
the measured margin in the reported corners, not a general hardware-stability qualification. No
timing constraints were relaxed to obtain a pass. Closing these paths remains
a separate task.

RBF:
`build/p06-target-handoff-allfeatures-20261005-v2/work/output_files/PCAT-286.rbf`

SHA-256:
`88f1075046876d13acafde4834a6ed2a0b385e7ec1de51a3d5646342dc1140b1`

Size: 4,113,440 bytes. Compile: 35 min 23 s; detailed STA: 3 min 25 s.
This is a newly generated hardware-test candidate, not a timing-closed release
or a MiSTer-tested result. Hardware measurements should confirm MAX preservation
and the new B0 intervals before further calibration.

## Evidence and cleanup

The [candidate packet](../evidence/p06-target-candidate-20261005/manifest.json)
retains complete effective compile inputs, reports, source identities and
bounded directed results. The standard compile flow regenerates `build_id.v`;
its build-date-only before/after hashes are declared rather than hidden.

Focused CPU, preview, length, handoff, integration and timeout packets are
separate and independently reviewed. The RBF/SOF and compact fit reports remain
under the fit run. Owned compiler databases, simulator objects and temporary
snapshots are removed after archive verification. All three agents completed
their assigned checks and have no active processes.

SPK286 receives the portable raw-CPU correction, canonical syntax metadata,
preview and new unit registration. Its copied CPU inputs match the directed
validated vendor inputs, with regeneration/syntax/lint checked in the standalone
checkout. Motherboard timing and OSD stay in PCAT-286.
