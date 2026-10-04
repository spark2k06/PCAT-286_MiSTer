# P06/P12 first public speed-selector candidate

## Objective and release contract

Prepare a newly synthesized PCAT-286 RBF with one OSD choice:
`MAX / 6 / 8 / 10 / 12.5 / 16 / 20 / 25 MHz`.
The first implementation applies the choice through **Reset & apply settings**.
New status bits `77:75` preserve MAX for older configurations. No public
T-state switch, extra CPU PLL or second synthesized CPU is introduced.

All logic keeps the common 50 MHz physical clock. Rational clock enables
describe virtual processor boundaries; peripherals keep their original
PIT, RTC, DMA/refresh, video and audio clocks. Lower nominal CPU speeds do
not relax any 20 ns physical timing requirement.

Historical scheduling is provisional. Intel instruction minima, original
functional dependencies and retained logical bus timing are separate.
Complex forms explicitly marked estimated, target-instruction length,
internal EU milestones and board-specific calibration still need further
qualification. This release must not be described as cycle accurate or as
a completed calibration to every physical 286 motherboard.

The [physical 6/12 MHz anchors](P06_PHYSICAL_REFERENCE_RESULTS_20261004.md)
and native visible-zero/automatic/wait controls remain the basis for
comparison. A global benchmark multiplier is not used. The physical
machine's board identity and actual clocks remain unverified; 86Box's
nominal 12 profile is 12.5 MHz.

## Resource fallback

The first fit starts with the existing feature configuration. If resource
pressure prevents a fit, first set `ENABLE_OPL2=0` in `config.tcl`. Keep the
Adlib/OPL2 implementation and all other configuration choices available.
Measure complete fitted resources against the selected fixed-50 MHz build,
not isolated generic synthesis cell counts.

## M1: selector and retained bus components

The reset-applied generator uses ten register bits: three selector bits,
a six-bit phase accumulator and one parity bit. Its increments are
12/16/20/25/32/40/50 modulo 50. Every second phase is a processor boundary;
MAX supplies a boundary on every fabric edge. This generator alone is not
an instruction timing implementation.

The bridge reuses its existing request, lane and response payload storage.
Historical requests start Ts at a processor boundary, begin Tc on the
following boundary and can finish at the next boundary. Physical READY/data
is captured on the fabric clock, even between virtual boundaries. The
bridge remains occupied, with LOCK retained, until logical publication.
Odd-word halves and the two INTA requests therefore retain their original
functional ownership and sequencing. Actual backend lateness is an
implementation deadline miss, not an inferred motherboard READY wait.

Directed acceptance:

- Generator: 1,512 cases and 2,583,001 checks in each simulator, identical
  dual traces and summaries; 64 reset-applied transitions, randomized
  frequency windows, eight four-state cases and four rejected mutants.
- Bridge: 1,512 transfers, 8,745 checks, 2,016 accepted/captured physical
  beats and 1,512 logical publications in each simulator. CODE, READ, WRITE,
  split targets, odd lanes, INTA, LOCK and backend latencies 0 through 20
  are exercised for every profile, including MAX.
- Existing bridge response tests pass in both simulators.
- Yosys proves every original bridge output and matching original state
  equivalent to the immutable selected build in MAX for both completion
  modes. A changed READY negative control fails. No protocol assumptions
  or output masks are used.

Generator-only synthesis reports 114 generic cells / 10 register bits.
These are not FPGA ALMs and exclude the CPU schedule and complete project.

M1 qualifies components only. Production OSD/CPU integration, broader
functional validation and a new fit/RBF are subsequent milestones of this
same objective.

## M2: production CPU and machine integration

The production wrapper selects one generated `spk286_profiled` CPU. Its
functional source, microcode and private pilot ancestors are unchanged.
Instruction timing is a separate combinational form table and interval
controller, driven by the selected virtual processor boundary. Real fetch,
operand, bus, protection and event dependencies still extend completion.
MAX follows the original operation/retirement/event paths.

The table covers legal ordinary/extended decoder entries and named microcode
entries. It separates ModR/M effective-address costs, branch/count outcomes,
REP setup/iteration intervals, READ-wait eligibility and estimated forms.
Odd corrections are charged once for each original word reference before
the BIU splits it; an odd RMW can therefore charge both READ and WRITE.
LOCK has no extra prefix clock, and REP setup includes one REP prefix;
other accumulated prefix costs use an explicitly provisional native fallback.

The controller times new instruction bodies, repetition checkpoints and
observable retirement. Existing internal GPR/FLAGS/protection commits can
occur before the interval ends; a following opcode or asynchronous boundary
cannot observe them until the interval permits it. This is not a fully timed
internal EU or speculative architectural model. Event services keep their
original functional sequencing and receive an interval budget at dispatch.
Idle asynchronous selection/capture runs on the fabric clock; instruction
boundaries, event completion and logical bus timing are qualified separately.
Exact native pin recognition offsets are outside this first release.

Both the CPU and bridge open a retained admission window after completion.
The following head/request can be accepted on the next fabric edge within
that virtual interval, after old ownership clears. This prevents an invented
extra processor clock while preserving adjacent identical transfers, event
priority and the original payload storage.

The actual OSD entry uses bits `77:75` and **Reset & apply settings**. A pending
change displays the existing reset notice. CPU-local warm reset does not
recapture a pending OSD choice. Peripherals continue on their existing clocks.

### Validation findings and declared fixture scope

Directed validation found and corrected timing-admission defects in INTO
condition qualification and NMI arbitration. No original architectural
assertion was changed to accept them.

One protected-system fixture patched address `0197` from HLT to IRET after
prefetch had already captured it in a slower profile. The historical build-only
fixture initializes that same IRET byte before the stream starts, retaining
the original later patch and all architectural assertions. MAX retains its
original stimulus and per-edge trace. This is a fixture initialization
correction, not CPU instruction-cache invalidation or altered HLT behavior.

Cross-simulator comparison declares four-state versus two-state observation
differences: pre-edge address/status/HLDA while reset is asserted and unknown bits
of uninitialized memory input. Architectural output differences remain
failures. Raw MAX comparisons within Icarus require identical complete traces;
cross-simulator results identify their passive representation explicitly.

Active microcode generation/roundtrip checks pass. One old vendor predecessor
fixture has LOADALL/SALC numbers swapped relative to its own frozen derivation;
its failure is retained separately and does not alter the active compiled-ROM
contract. The corresponding standalone committed fixture is consistent.

A separate pause probe verifies the boundary contract after functional RAW
completion: the existing instruction can publish its delayed retirement while
virtual boundaries continue and `execute_enable` is paused. No following opcode,
new register/flag/IP change or accepted WRITE is permitted. It passes 195 checks
across seven paused virtual boundaries with exactly one retirement.

### Standalone SPK286 synchronization

The standalone `SPK286` project is synchronized and clean at `86a76ce`:

- `f980047`: align mutation audits with the complete optimized RTL closure.
- `6033d3a`: observe the first protected RETF stack fault before double fault.
- `b27fb51`: synchronize the established PCAT functional CPU baseline.
- `86a76ce`: add the reproducible provisional CPU interval profile package.

The portable package contains the same generated CPU and event logic as PCAT,
with its functional dependency hashes, builder, metadata table, schedule and
directed component checks. It does not include PCAT's OSD, bridge or chipset.
Both hosts reproduce the generated bytes; neither repository claims completed
physical calibration, hardware acceptance or a full regression from this work.

### M2 directed acceptance

The [validation manifest](../evidence/p06-osd-candidate-20261004/validation-manifest.json)
binds source hashes, receipts, result logs, generated fixtures and trace digests.

- All 26 full-CPU banks cover all eight profiles in at least one simulator:
  202 Icarus runs, 64 Verilator runs and 26 original/profiled MAX comparisons.
- The 26 MAX comparisons match complete RAW stream hashes, byte counts and
  row counts. The independent MAX auditor passes 130 negative integrity checks.
- 58 paired simulator runs match the explicitly declared canonical observation.
  Six remaining IOPL profiles run the original architectural assertions in
  Verilator without a paired Icarus trace. They are not counted as dual matches.
- Passive stream checks compare complete streamed hashes against complete CSV
  hashes and test chunk boundaries and changed architectural fields. Bounded
  first/last samples are retained for inspection, not used as comparison input.
- Instruction metadata passes 43,878 identical dual observations, seven
  negative controls and strict lint. The independent interval controller and
  passive CPU prefix probes pass in both simulators.
- The final retained bridge passes 1,576 cases, 9,024 checks, 2,087 physical
  command/captures and 1,576 publications in each simulator. It includes
  adjacent identical requests, retained capture/reset and posted-write drain.
  All original MAX bridge outputs/state remain formally equivalent without
  protocol assumptions or output masks.
- The composed AT machine passes its diagnostic ROM for every profile, with
  memory/I/O, interrupts, refresh and the expected final port-80 landmark.
  Production OSD elaboration and the actual eight-entry selector pass.

Failed exploratory runs remain recorded separately; a host timeout in the
initial exhaustive IOPL Icarus shard is not accepted as a completed run. The
final coverage above uses the completed shards and the explicitly split IOPL
receipt. None of these checks is a hardware, complete OS or full-regression
acceptance. Full-project fitted cost and physical timing are a separate M3
measurement of the newly generated RBF.

## M3: newly synthesized candidate

The [complete measured fit](P06_OSD_FIT_20261004.md) is now available with a new
RBF and all existing features enabled, including Adlib/OPL2. It fits at
30,751 equivalent / 36,363 placed ALMs, with unchanged M10K/DSP/PLL counts.
Directed functionality passes, but physical setup fails at -17.001 ns;
minimum reported hold is +0.076 ns. The metadata/deadline and bridge/cache
admission cones require a separate P21 follow-up. The generated artifact is
an experimental candidate, not a timing-closed or hardware-accepted release.

## M4 hardware profile observations

The user has now tested this RBF on MiSTer with reset applied for each
selection. The [hardware results](P06_MISTER_REFERENCE_RESULTS_20261004.md)
preserve eight CSVs, three CHECKNUM screenshots and 336 validated fixed-work
samples. BIOS/CheckIT reportedly detect the intended nominal MHz. MAX
CHECKNUM retains 6906 / 121.6K; historical profile results differ from the
retained physical/native anchors. R0 takes 316 median ticks at 25 MHz versus
298 at 20 MHz, requiring a directed timing trace before assigning a cause.

This provides hardware evidence for the first selector candidate, while
historical calibration, broad OS acceptance and physical timing closure
remain open. The frozen M3 fit receipt retains its original pre-hardware
status; no RTL, config or RBF changes are made by the measurement analysis.
