# Register execution import at 50 MHz — 2026-09-22

Imports the validated SPK286 register ALU/MOV optimization into PCAT on top of
`13ea501`. The upstream working increment is based on `ec5605b547802e19109362878756f7032ac96a7d`
in `codex/register-execution-optimization`; it was not committed when imported.
The upstream increment is now committed as
`bab0f67d44c4afda414d583a6948df213453e452`.
The three changed CPU RTL files are byte-identical to that tested increment.

## Integration and clock

Production remains on `FPGA_CLK2_50` / `CLK_50M`, with a 20 ns constraint.
`SPK286_AT_NO_DEBUG` is enabled and `SPK286_AT_DEBUG_CPU_DIV2` remains disabled.
No PLL, SDC, top-level, memory-map or chipset RTL changes accompany this import.
The 16 MiB RAM/BIOS collision fixes remain in place.

The downstream compiler retains `CARRY_FILL8=171` and `LOADALL=172`, which
differs from upstream. Format 22 adds controls 173..180 without renumbering
those existing controls. Generated files are produced by this downstream
compiler. An independent test requires exactly eight changed control words
and unchanged entries, labels, branch targets and memory fallback sequences.
Original frozen fixtures remain unchanged.

The [import manifest](../imports/spk286-register-execution-20260922.json)
records old, imported and upstream SHA-256 values and identifies local
adaptations. Register capture, execution and retirement retain the upstream
semantics; memory forms retain their existing execution sequence.

## Measured machine-side comparison

These are directed synthetic firmware workloads, not the DOS CheckIt program.
Subsequent profiling found that this runner hard-coded P01/P02 although the
shipped RBF enabled only P05. The A/B comparison applies to that faster simulated
profile; its absolute access times do not represent the original RBF. The later
bus-latency work corrects the runners to read the project configuration.
Both versions use the same CPU/AT bridge/memory-port/SDRAM-owner/pin-model
harness at 50 MHz. P03=1 matches the production read-buffer configuration.

| Workload | Previous clocks | Optimized clocks | Throughput increase |
| --- | ---: | ---: | ---: |
| Integer mix | 1,220,887 | 1,215,988 | 0.403% |
| Fixed-point mix | 1,026,205 | 1,018,477 | 0.759% |
| Working set | 1,162,323 | 1,140,571 | 1.907% |
| Dhrystone 2.1 fixture | 1,350,819 | 1,347,223 | 0.267% |

All eight runs, with P03 both enabled and disabled, pass their architectural
checks. Retirement and write counts match the corresponding old run.
[Raw comparison](register_execution_50mhz_comparison.json) includes both modes.
The larger CPU-only register-stream improvements do not carry directly into
these mixed workloads: their measured external-wait counters account for
approximately 71–79% of elapsed clocks with P03 enabled. Physical CheckIt
performance for this original RBF was subsequently reported unchanged by the
user. The later [bus-latency increment](BUS_LATENCY_50MHZ.md) records the improved
hardware result after P01/P02/P06 were enabled in the fitted project.

The original directed harness failed even on the unchanged `13ea501` CPU:
the new physical SDRAM owner correctly rejected the reset address above its
small explicit backing store. This harness bypasses `spk286_at_machine`, so
it must explicitly supply that machine's FF0000 BIOS alias mapping. The bench
now maps that alias and carries 25-bit backend addresses. The same corrected
bench was used for both old and new CPUs; the pin model's bounds assertion
and all workload expected results remain unchanged. No production mapping
was modified to accommodate the benchmark.

## Validation

- 95 compiler tests, generated consistency, independent ROM audit and strict
  CPU Verilator lint pass.
- The imported register lifecycle bank passes 78 cases / 3,879 checks in
  each simulator; the complete-stream bank also agrees between simulators.
- CPU package elaboration and integration lint pass.
- Physical SDRAM first-fetch tests pass, including the 16 MiB profile's 238
  block isolation checks and all 65,536 BIOS bytes.
- The integrated LOADALL/XMS fixture passes three repeated LOADALL operations,
  a 32-byte extended-memory copy, A20 aliasing and byte-lane checks.
- The full-machine diagnostic passes with 104 memory beats, 12 I/O writes,
  33 IRQ0 observations, 32 refresh observations and four port-80 writes.
- The affected-unit suite passes all eight banks in both simulators, including
  MOV's 128 register / 480 memory cases, operand cancellation, ALU instruction
  execution and protected LOADALL rejection. It ends with
  `AT_REGISTER_EXECUTION_TEST_PASS` and exit status 0.
- Fresh Quartus 17.0.2 compilation passes with 0 errors / 694 warnings;
  the subsequent four-corner TimeQuest report generation also completes.
  This is a successful artifact build, not timing closure.

Focused reproduction from WSL:

```sh
bash scripts/test_at_register_execution.sh
bash scripts/test_i1_cpu_package.sh
bash scripts/test_at_loadall_xms.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_checkit_directed.sh
bash scripts/build_at_no_debug.sh
```

The isolated old benchmark checkout is under
`build/register-opt-import/baseline/`; current logs and simulator products are
under `build/register-opt-import/`. The old fixture failure is preserved in
`checkit-before-original-harness.log`. Build inputs are frozen under
`build/at-no-debug/20260922-register-execution-50mhz/` with no reused Quartus
database or bitstream. The Windows 3.1 restart is not considered resolved by
this performance change; the user's 25 MHz experiment also reproduced it.

## Artifact and timing

The new bitstream is
[`PCAT-286_REGISTER_OPT_50MHz.RBF`](../../output_files/PCAT-286_REGISTER_OPT_50MHz.RBF)
(4,051,452 bytes), with SHA-256
`fc2a21b444c7df08b23d57692c6e968ff8693d4984cabe97230657dc155b9339`.
Adjacent JSON and SHA-256 receipts identify the frozen build and timing reports.
All 342 selected production inputs match the frozen snapshot; the output copy
matches the newly generated bitstream. Existing output bitstreams were preserved.

TimeQuest's fitted-netlist inventory confirms `no_debug=1 observers=0` and
`FPGA_CLK2_50 period=20.000`. Fit utilization is 28,547 ALMs (68%), 34,269
registers and 3,152,832 block-memory bits (56%). Compilation took 33m43s;
the additional timing report pass took 2m04s.

| Operating corner | CLK2 Fmax (MHz) | CPU setup slack (ns) | CPU hold slack (ns) |
| --- | ---: | ---: | ---: |
| Slow 1100 mV, 100 C | 38.43 | -6.018 | +0.253 |
| Slow 1100 mV, -40 C | 39.07 | -5.596 | +0.244 |
| Fast 1100 mV, 100 C | 73.04 | +6.309 | +0.135 |
| Fast 1100 mV, -40 C | 86.36 | +8.421 | +0.118 |

**Timing does not close at 50 MHz.** The worst CPU path runs from prefetch
queue `storage_q[2][6]` to `events.event_vector[1]`. Fmax describes the
same-clock constraint result, not the actual configured CPU frequency.
The complete design also has violations outside the CPU: global setup reaches
-21.387 ns in the video group, global hold reaches -1.743 ns in the HDMI group,
and SDRAM-owner setup reaches -3.874 ns. CPU-only Fmax is therefore not a
whole-system operating guarantee. The clock is retained at 50 MHz as requested
for the physical CheckIt comparison; hardware stability remains unverified.

The raw reports are under
`build/at-no-debug/20260922-register-execution-50mhz/timing/`, including
`collections.txt`, `path_counts.txt` and per-corner detailed paths.
