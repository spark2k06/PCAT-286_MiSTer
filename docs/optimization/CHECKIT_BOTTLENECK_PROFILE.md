# CheckIt investigation: bus latency and CPU demand — 2026-09-22

**Configuration correction discovered during the subsequent optimization:**
the runner hard-coded P01/P02, while the previously shipped NO_DEBUG RBF enabled
only P05. P03=1 matches the hardware read-buffer setting, but these measurements
use faster bridge/fetch settings than that RBF. They remain valid for the stated
simulated profile; they must not be quoted as the old bitstream's access times.
The follow-up baseline with the actual project flags measures approximately
11-clock data reads. Simulation runners now obtain these switches from config.tcl.

The user reports unchanged physical CheckIt results after the register-execution
import: 2,695 Dhrystones and 53.3K Whetstones. The simulation below profiles four
directed synthetic workloads, not the commercial DOS CheckIt executable. It
identifies limits in those workloads; it does not establish their exact shares
in CheckIt or explain the Windows 3.1 restart.

## Findings

The measured limit includes substantial operand-memory service time, instruction
supply time and internal sequencing. A pending bus transaction is not equivalent
to a stopped CPU, and a naturally empty queue is not always a demanded byte.

The measured configuration uses P03=1, native 16-bit memory accesses,
P01/P02/P05 options and a 50 MHz clock. These mutually exclusive
categories account for every simulated CPU edge:

| Workload | Operand service | Missing instruction bytes | Internal microcode | Dispatch/prefix and retirement |
| --- | ---: | ---: | ---: | ---: |
| Integer mix | 58.00% | 9.41% | 26.14% | 6.44% |
| Fixed-point mix | 47.50% | 16.96% | 26.81% | 8.74% |
| Working set | 43.53% | 17.40% | 29.10% | 9.97% |
| Dhrystone 2.1 fixture | 39.11% | 22.34% | 29.73% | 8.83% |

Minor row-sum discrepancies are rounding. Operand service includes its admission
edge and the wait for its response, excluding the response-consumption edge.
Internal microcode includes byte-consumption and operand-completion edges,
decoding, arithmetic, string bookkeeping and END; it does not mean only ALU work.
The residual `other` category is zero in all four P03-enabled runs.

Only 1,538 of 38,656 instructions in the integer mix use the new register fast
path (3.98%). Across the four workloads the share is 2.27–7.65%. In the integer
mix, MOVSW and CMPSW together account for approximately 41% of elapsed clocks
while active, including their memory waits. In the Dhrystone 2.1 fixture,
opcode 83h executes 13,440 times and its immediate-operand path retains the
longer microcode sequence. Register-only ALU/MOV gains therefore have limited
coverage of these workloads.

## Actual access latency

Latency below is the difference between the edge first observing a CPU bus
request and the edge observing READY. The terminal READY edge is excluded from
the wait-clock count. This is distinct from a sustained bus transfer interval.

| Access | Mean wait clocks, across workloads | At 50 MHz |
| --- | ---: | ---: |
| Code hit in existing 8-byte P03 buffer | 4.000 | 80 ns |
| Code miss, four-word physical fill | 12.186–12.291 | 244–246 ns |
| Data read | 9.117–9.386 | 182–188 ns |
| Data write | 8.159–8.284 | 163–166 ns |

A typical data read has two front-end clocks, six accepted-owner service clocks
and one return clock. Physical-owner availability/refresh raises some requests
above this minimum. An existing code-buffer hit takes two front-end clocks,
one hit-response clock and one return clock. The AT memory port captures its
record during the bridge's ADDRESS interval: its occupancy must not be added
again as an independent extra delay. These values were timestamped across each
completed transaction, not inferred by summing overlapping module busy counters.

`spk286_at_bus_bridge` serializes IDLE capture, ADDRESS, COMMAND, WAIT and
COMPLETE. `spk286_at_mister_sdram_owner` uses KFSDRAM and registers its read
response. KFSDRAM activates/reads/precharges its physical transactions. The
present front-end and controller sequence, together with instruction/data
competition at the BIU, matters more than the SDRAM chip's headline capability.
In the integer mix, 85,580 operand-service clocks occur while the bus still
belongs to code; in the fixed-point mix that overlap is 123,397 clocks.

Intel specifies a peak transfer rate of one word every two processor clocks
and overlaps the next address presentation with the preceding bus operation.
That corresponds to an ideal 80 ns transfer interval for a 25 MHz processor;
it is not a guarantee for every contemporary DRAM/chipset combination. The
chip's external clock is twice its processor clock. These FPGA implementation
clocks must not be equated with historical processor cycles without a timing
model. Source: [Intel 80286 datasheet, Bus States / Pipelined Addressing](https://datasheets.chipdb.org/Intel/x86/286/datashts/intel-80286.pdf).

Thus the results do not demonstrate that modern SDRAM is intrinsically slower
than period DRAM. They demonstrate the cost of this implementation's access
path. Optimizing command/response scheduling and overlap is a justified next
step; historical wait-state insertion would not remove this cost.

## Controlled sensitivity experiments

The diagnostic owner replaces selected SDRAM transactions with one word per
clock, starting one edge after acceptance. The CPU, AT bridge, memory port,
P03 behavior and final architectural scoreboards remain. It is a simulation
counterfactual, not a proposed physical SDRAM timing configuration.

| Workload | All owner accesses ideal | Only code ideal | Only data reads ideal | Only writes ideal | Simulated 1 KiB data cache |
| --- | ---: | ---: | ---: | ---: | ---: |
| Integer mix | +41.6% | +6.5% | +18.7% | +7.7% | +18.4% |
| Fixed-point mix | +38.5% | +12.6% | +10.1% | +7.7% | +10.0% |
| Working set | +36.1% | +11.5% | +9.7% | +8.1% | +9.7% |
| Dhrystone 2.1 fixture | +33.5% | +12.2% | +8.7% | +6.6% | +8.6% |

Values are throughput gains; they are not additive. Removing physical-owner
latency alone does not double these workloads. The separate experiment making
both data reads and writes ideal yields +16.7–30.1%; it overstates what a
simple cache with writes forwarded to SDRAM would accomplish.

The cache experiment uses 512 direct-mapped words (1 KiB data plus tags), a
single-clock response on a hit, physical reads on misses, physical writes with
updates to already cached words, and no allocation on write misses. Its hits
return the cached data, not a fresh peek at backing memory. Data-read hit rates
are approximately 98% for these small fixtures. This estimates workload locality;
BRAM inference, clock closure and DMA/HPS coherence have not been implemented
or validated. No cache was added to production RTL. A cache remains useful, but
the current four-clock path even on a buffer hit also warrants attention.

## Verification and reproduction

- 32 runs pass: eight physical runs (four workloads, P03 off/on) and 24
  counterfactual/cache runs with P03 on.
- All eight physical runs reproduce every pre-instrumentation result counter
  exactly, including elapsed clocks, retirements, writes and physical accesses.
- CPU category sums, bus-overlap sums, completed-transfer counts and latency
  decompositions are checked independently. Demand categories may not overlap.
- Within each workload, P03 off/on and all six experimental modes agree on
  complete GPR/FLAGS state and a hash over the full explicit backing memory.
  Original memory-pattern checks and protocol-error checks remain in place.
- Instruction retirement/write counts and fast-register instruction counts
  agree between the physical and experimental runs.
- The new profiling/ideal-owner sources introduce no Verilator warnings.
- All 342 selected production inputs match the previously synthesized snapshot.
  Production RTL, clocks, constraints and RBF files are unchanged by this work.

```sh
PCAT_BUILD_DIR="$PWD/build/checkit-profile-final" bash scripts/test_checkit_profile.sh
python3 scripts/report_checkit_profile.py build/checkit-profile-final \
  --reference-build-dir build/register-opt-import/checkit-after
```

The optional reference directory is the archived pre-instrumentation run from
the register optimization import. A fresh checkout can run the first command
without those historical artifacts. Profiling is off by default in the original
directed runner; the diagnostic owner defaults to the physical path.

[Compact results and provenance](checkit_bottleneck_profile_20260922.json) retain
the category counts, access latencies, instruction mix and experiment gains.
Full logs, hashes and per-microcode counts are in
`build/checkit-profile-final/profile.json`. The legacy `code_fetches` field is
retained only for historical comparisons: it mixes request occupancy with
transfer counting. `PROFILE_MISC code_transfers` counts completed code transfers
using CPU bus status at READY.
