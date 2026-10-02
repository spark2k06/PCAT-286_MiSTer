# Real CHECKNUM memory attribution

These tools create a **private timing/control co-simulation adapter**. The
standalone SPK286 CPU model objects from the 86Box build are reused unchanged.
The production PCAT bridge, common memory port, instruction buffer, 1 KiB data
buffer and SDRAM owner/KFSDRAM controller generate memory READY in the `pcat`
arm. The `ideal` arm keeps immediate READY. Both execute the unchanged accepted
CHECKNUM executable on separate, initially identical DOS images at 50 MHz.
The builder follows the production instruction capacity by default (currently
4 KiB with synchronous tags). Use `--code-lines 64` for the old 512 B control.
The completed old-capacity attribution uses its frozen earlier source build.

Guest memory values remain in 86Box. SDRAM DQ is constant in the timing model;
its data is discarded, and the existing host memory operation executes exactly
once when the CPU samples READY. Data values do not select any controller or
buffer timing state. This adapter measures control/service timing; it does not
validate cached data, SDRAM electrical margins, or a complete PCAT machine.
Those have separate RTL/hardware tests.

## Scope

- Conventional RAM, extended RAM through 25FFFFh and system BIOS are routed.
- A20 and the reset BIOS alias are resolved before the buffer tags.
- ISA I/O, INTA, video, option ROM, chipset devices and guest memory values use
  86Box. DMA/loader requests and abstract AT refresh requests are absent from
  the reduced memory chain. KFSDRAM's own periodic refresh remains enabled.
- The reduced adapter does not implement PCAT's EMS reservation/physical RAM
  shift above CPU address 2 MiB. This DOS application and the bounded benchmark
  traces use conventional RAM and HMA; extended-memory platform testing needs
  the complete decoder. Hardware disk/load segment and repeat variation also
  need matching before treating the reduced result as an exact hardware score.
- CPU reset cancels CPU-side ownership; accepted physical operations drain.
- BIOS startup uses a shortened SDRAM initialization wait, outside CHECKNUM.
- Counters include overlapping CPU/bus activity. READY wait cycles are not
  all additional execution time and must not be added to CPU internal cycles.
- Phase recognition matches the unmodified frontend bytes and relative far-call
  segments. It derives the DOS load segment at runtime, without guest markers.
- All code/data counters come from actual RTL. `shadow_code`/`shadow_data` are
  explicit counterfactual tag models on the accepted bus stream, including
  write invalidation/update, no write allocation and LRU replacement for two
  ways. They do not predict a speedup or the timing of an FPGA implementation.
  Aborted fills and CPU-reset flushing during boot are not modeled by these
  shadow tags; compare the recognized benchmark phases and retain this limit.
- CSV traces retain the first 250,000 accepted bus operations in each benchmark
  phase, including interrupts/calibration. They are bounded diagnostic samples.

## Build and run (Ubuntu WSL)

Use fresh output directories. Paths below are examples; provide an existing
prepared 50 MHz comparison root from `tools/spk286_cpu/prepare_checknum.py`.
The runner validates the prepared disk hash and the CHECKNUM bytes inside it,
uses calibrated SPK286 CMOS, checks actual CPU/ISA clocks and dispatcher, and
requires both scores plus DOS RC0 and `ALL_DONE`. It preserves failed runs.

```sh
python3 tools/perf01/build_86box_memory_probe.py \
  --build-dir /mnt/d/GitHub/86Box_dev/build/spk286 \
  --output "$PWD/build/memory-probe/probe"

python3 tools/perf01/run_86box_memory_probe.py \
  --reference-root "$PWD/build/perf01-86box-50-20261002" \
  --probe-root "$PWD/build/memory-probe" \
  --86box-root /mnt/d/GitHub/86Box_dev \
  --roms /mnt/d/Desktop/86Box/roms --mode pcat
```

Repeat with `--mode ideal`. `--probe-binary` and `--arm-name` allow explicitly
named frozen builds/repeats. Do not overwrite a binary used by a running arm.
Create `<arm>/stop` to stop only the owned measurement. An interrupted run is
recorded as incomplete and cannot supply a benchmark score.

The existing 86Box runner writes `measurement.json`, periodic coherent CPU
samples, screenshots and guest output. Additional `memory-profile.json` is
published atomically every million CPU clocks. Phase boundary snapshots are
appended to `.phases.jsonl`; subtract consecutive snapshots for phase totals.
The code/data shadow models retain warmed tags across phases.
The launcher saves a private copy of that runner and drains its PTY during host
cleanup. A cleanup timeout is recorded explicitly; complete guest RC0 and host
exit status remain separate evidence. No upstream 86Box tool is modified.
The frozen sampler reads CPU configuration and RTL ports in one coherent stop.
A five-second host thread-stop timeout records a skipped sample and resumes
the owned process; it does not accept incoherent values or abort the guest.
Clock/dispatcher mismatches and other errors remain fatal. The sampler's hash
is retained alongside the private runner's hash.

After both arms complete, `summarize_memory_probe.py --ideal-arm <ideal>
--pcat-arm <pcat> --output <summary.json>` computes separate Dhrystone and
Whetstone totals and links all input receipts by SHA256. It rejects incomplete
guest runs, unsuccessful host exits, incorrect clocks and missing phase edges.
`--allow-host-teardown-issue` permits a classified host cleanup problem after
complete guest output; its return code and any reconstructed receipt remain in
the summary. This is an explicit exception, not a clean host-exit claim.

`compare_memory_candidates.py --baseline-arm <old-pcat> --candidate-arm <new-pcat>
--output <comparison.json>` checks matching guest input, configuration, initial
CMOS, profiler and CPU backend identity, then compares completed scores.
`analyze_memory_trace.py --arm <arm> --output <footprint.json>` describes both
bounded traces, including physical-address conflicts. Their unique footprint
does not establish simultaneous cache occupancy.

## Directed adapter checks

```sh
obj="$PWD/build/memory-probe/probe/memory-obj"
g++ -O2 -I/usr/share/verilator/include -I"$obj" \
  tools/perf01/memory_probe_smoke.cpp "$obj/Vpcat_memory__ALL.a" \
  "$obj/libverilated.a" -lpthread -latomic -o "$obj/smoke"
"$obj/smoke"
```

This checks BIOS-alias tag identity, read hit/miss behavior, a partial write
update, code invalidation, no write allocation and cancellation of an active
fill. Reads/writes retain production command/control sequencing. Refresh phase
can increase miss latency; the check asserts relative miss/hit behavior, not a
universal fixed miss latency.

The build never modifies the 86Box sources or replaces normal build products.
The generated top reuses the directed bench's wiring with explicit physical
response connections. Build receipts record source/macros, reused CPU object
hashes, exact compile/link commands and the private binary identity.
