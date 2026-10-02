# P08: selected 50 MHz timing closure - 2026-10-02

## Selected result

The statistics-only sparse placement fit closes the constrained FPGA
design at the real 20 ns / 50 MHz system and SDRAM clock. The four models
have positive complete-design setup, hold, recovery and removal. The
original SDRAM device/flight budget and held-payload requirements are
retained. The complete-design reports include the HDMI clock domains.

| Model | Global setup | Global hold | CPU setup | CPU hold | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Slow 100 C | +0.184 ns | +0.159 ns | +0.270 ns | +0.260 ns | +5.010 ns | +2.970 ns |
| Slow -40 C | +0.154 ns | +0.014 ns | +0.679 ns | +0.251 ns | +5.946 ns | +2.472 ns |
| Fast 100 C | +2.184 ns | +0.133 ns | +9.178 ns | +0.140 ns | +9.120 ns | +0.896 ns |
| Fast -40 C | +2.514 ns | +0.069 ns | +10.859 ns | +0.120 ns | +10.796 ns | +0.250 ns |

The minimum global hold is **+0.014 ns**. It meets the positive acceptance
criterion but is a narrow residual margin. All 60 minimum-pulse-width
groups in the actual STA summary are positive; their minimum is +0.793 ns.

This result applies to the constrained fabric and the conditional W9825
SDRAM device/board-flight model documented in
`P05_SDRAM_BUDGET_20261001.md`. The inherited platform I/O and HPS hard-block
coverage qualifications in `P05_TIMING_COVERAGE_20261001.md` still apply.
The source audit checks the previously reviewed coverage counts and node
families; it rejects unexpected coverage changes. This does not certify
unmeasured board flight times or an obscured SDRAM speed grade.

## Physical change and selection

`PCAT-286.qsf` selects 326 exact FF locations for the 163 source/capture
statistics pairs, one pair per ALM across 17 LABs. Every requested endpoint
is present and matches its fitted FF site. Seed 2, the production macros,
the 50 MHz clock, and the no-debug profile are retained. No RTL, CPU state,
instruction cycle, bus handshake, clock divider or timing budget changes
in this selection.

The previous stack-offset seed-2 checkpoint had global setup
-0.255/-0.033 ns in the slow models, although CPU timing already passed.
The selected fit has +0.184/+0.154 ns. Warm statistics interconnect in the
worst reported path falls from 0.910 ns to 0.414 ns; the actual paired FF
sites and complete paths are retained as evidence. Global placement also
affects unrelated paths, so the measured fit is the acceptance evidence.

The alternative with the same 326 locations plus two HDMI FF assignments
binds all 328 requests and compiles successfully, but is rejected:

| Model | Alternative global setup | Alternative global hold |
| --- | ---: | ---: |
| Slow 100 C | -0.182 ns | +0.147 ns |
| Slow -40 C | -0.011 ns | +0.028 ns |
| Fast 100 C | +2.272 ns | +0.112 ns |
| Fast -40 C | +2.604 ns | +0.055 ns |

Its warm critical path moves to scaled HDMI bit 23 and its cold minimum
is a CPU fetch-storage-to-GPR path. Those two extra locations are not
selected. The earlier four-register-per-ALM trials were unroutable and
produced no RBF; see `P08_VIDEO_REGISTER_PLACEMENT_20261002.md`.

The selected QSF bytes equal the successful compiled snapshot, including
its historical experiment comment. Selection is recorded here and in
`production-selection.json`. The QSF checkout uses LF to preserve those
bytes. A later synthesis, source change, placement change or regenerated
build date requires a fresh timing audit; this result belongs to the
identified compiled artifact.

## FPGA resources

These are actual fitted counts for the whole PCAT/standard MiSTer
infrastructure design, not the isolated CPU:

| Resource | Used / available | Quartus utilization |
| --- | ---: | ---: |
| Equivalent logic ALMs | 28,852 / 41,910 | 69% |
| ALMs physically used in placement | 34,724 / 41,910 | 83% |
| M10K RAM blocks | 414 / 553 | 75% |
| Useful block-memory bits | 3,267,227 / 5,662,720 | 58% |
| DSP blocks | 39 / 112 | 35% |
| PLLs | 3 / 6 | 50% |

There are 37,132 fitted registers. Quartus distinguishes physically used
ALMs from its equivalent logic estimate, which includes estimated dense
packing recoverability. The 69% estimate does not mean that 31% of physical
ALM sites are vacant in this placement. M10K utilization is 75% even though
useful bit utilization is 58%, because allocation is in whole RAM blocks.

Compared with the preceding stack-offset seed-2 fit, equivalent logic
increases by 162 ALMs and fitted registers by 14. RAM bits, M10K blocks,
DSPs and PLL counts are unchanged. Both fitter summaries and the selected
resource-usage section are retained in the evidence.

## Source and functional validation

The completion auditor verifies the frozen 1192-file snapshot, all 144
timing path-count groups, every original timing report hash and actual
unfiltered global reports. It rechecks the unchanged SDCs, actual clock
periods, required production macros, successful compilation, newly
generated bitstreams, CPU/RTC proof source identities and 59 directed
cycle-fixture inputs. Its final rerun after selection returns
`MEASURED_TIMING_PASS_UNDER_DECLARED_SCOPE` with no failures.

The original pre-flow hook regenerates only `BUILD_DATE` from 261001 to
261002. Both source identities, the unchanged generator and its actual
compilation log are retained. The frozen manifest is not rewritten.
All 850 current relevant compiled inputs, including QSF and the generated
build date, match the successful work directory at selection.

The actual compiled M10K microcode image has all 743 valid and 281 invalid
words checked, together with its mapped address/read-alignment parameters.
The exactly proven stack-offset executor, synchronous microcode CPU and
RTC lookup sources match this compiled design. Their prior formal and
affected CPU-bank evidence remains in the corresponding evidence folders.

Fresh checks use the selected fit's actual frozen sources:

- Statistics CDC: 172 accepted transactions pass.
- Video-calculation CDC: two coherent queries pass.
- Native/direct/scaled video: all three clock/phase configurations pass,
  with empty compiler logs.
- Eight directed CPU/physical-SDRAM-owner fixtures pass, covering four
  workloads with P03 disabled and enabled. With the same PROFILE=1 option,
  the complete logs are byte-identical to the stack-offset checkpoint,
  including cycles, stalls, registers, memory signatures and bus counters.
  PROFILE=0 omits profiling lines; its common measurement lines also match.

The CDC tests retain the existing Icarus warnings from `sys/osd.v` and
`sys/hps_io.sv`. The fresh Quartus full compilation completes with zero
errors and 851 warnings; its complete log is retained. No full CPU
regression, new MiSTer hardware test or new DOS CheckIT measurement was
performed. Directed fixture comparison does not supply new CheckIT scores.

## Artifacts and reproduction

Selected run: `build/sparse-pair-placement-stats-seed2-fit-20261002`.
Quartus Lite 17.0.2 Build 602, device 5CSEBA6U23I7, frozen container image
`sha256:1fba8b9347973365e9f7851d73f7cb035e38fefb827cbf0ed2ea291b48bdf6dd`.

Ready bitstream: `build/50mhz-closed-20261002/PCAT-286.rbf`,
**4,076,700 bytes**, SHA-256:

```text
22b6ee1e7384d9db43c8b241b5fdc6ca75e6e48c4d6847a5dae153f7964ea34b
```

The ready RBF/SOF are byte-identical to the newly compiled winning output.
The old root output/database is not the source of this result.
`build/50mhz-closed-20261002/selection.json` records the selection and hashes.

Tracked evidence is in `docs/evidence/50mhz-closed-placement-20261002`.
Both variants retain compile logs, source manifests, QSF/config/SDC/date,
STA summaries, completion and binding receipts, actual compiled-ROM checks
and directly readable critical global/CPU reports. Each variant also
archives all 166 original timing/coverage files and all 19 register
location/diagnostic files. Every archive member was compared byte-for-byte
with its original report before packaging. `files.sha256` identifies all
packaged files; the ready RBF itself remains in the ignored build folder.

For a new frozen build, run the existing detailed timing flow and then:

```text
python3 scripts/check_at_timing_closure.py build/RUN --output build/RUN/completion-audit.json
python3 scripts/check_at_video_register_placement.py build/RUN --expect-count 326 --output build/RUN/placement-bindings.json
```

The placement checker requires a fresh read-only extraction made with
`scripts/report_at_video_register_placement.tcl` against that fit. Positive
CPU-only reports or a matching location list alone do not establish closure.
