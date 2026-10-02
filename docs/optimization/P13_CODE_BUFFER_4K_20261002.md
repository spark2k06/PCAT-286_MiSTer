# P13: 4 KiB instruction buffer with synchronous tags

Date: 2026-10-02. PERF01 implementation milestone; measured performance,
full FPGA timing and hardware acceptance are separate results.

The real, unchanged CHECKNUM Dhrystone phase on the PCAT memory-control path
has 2,473,075 instruction-line misses and 9,537,146 hits with the old 512-byte
buffer. This differs sharply from the synthetic kernel's 99.91% hit rate.
On exactly that accepted traffic, the 4 KiB direct-mapped shadow model has
1,399 misses. Shadow tags identify an opportunity; they do not predict an
FPGA speedup. The complete workload attribution is retained under
`build/perf01-real-memory-20261002/pcat-v3/`.

## Implementation

PCAT now instantiates 512 eight-byte instruction lines, or 4 KiB. Its RAM data
buffer remains 512 words / 1 KiB so the instruction-capacity change can be
measured separately. SPK286 CPU RTL, options and clock are unchanged.

Large instruction buffers read the tag RAM and the selected data word on local
acceptance. A hit responds in the existing registered response state. A miss
uses that state to submit one four-word physical fill and therefore adds one
lookup clock to miss admission. Writes retain their physical completion and
invalidate a matching tag at completion. This avoids a combinational lookup
across 512 full tags. Small elaborations retain the old asynchronous tag path
for controlled comparisons.

Valid bits remain resettable; tag/data arrays are not reset. CPU cancellation
can complete an unlaunched lookup without issuing a physical command. An
already accepted burst drains its four words before releasing ownership. DMA,
loader, refresh, byte enables, ROM guard and canonical physical addresses retain
the same contracts.

## Directed checks

The retained [evidence bundle](../evidence/perf01-code4k-20261002/README.md)
contains exact source identities and results.

| Check | Result |
| --- | --- |
| Production code-buffer scoreboard, 1 / 64 / 512 lines, enabled and disabled, Icarus and Verilator | PASS |
| 512-line scoreboard including cancellation before physical acceptance | PASS, 1,769 requests / 126,090 checks in each simulator |
| Memory-port/code/data chain with 512 instruction lines | PASS, CPU/DMA/loader coherence, refresh, burst, reset |
| Private adapter with production bridge, buffers, SDRAM owner/controller | PASS, alias, hit/miss, partial write, invalidation, no write allocation, cancellation |

The adapter's code hit waits two CPU clocks, as before. Its sampled code miss
waits twelve, versus eleven in the old capacity. Refresh phase can extend
physical service; these isolated values are not universal miss latencies.

Reproduction:

```sh
bash scripts/test_at_code_buffer_production.sh
bash scripts/test_at_ram_read_buffer.sh
python3 tools/perf01/build_86box_memory_probe.py \
  --build-dir /mnt/d/GitHub/86Box_dev/build/spk286 \
  --output "$PWD/build/memory-probe/probe-code4k"
```

The private adapter follows the production instance's capacity by default;
`--code-lines 64` selects the old-capacity control explicitly. CPU model objects
are reused unchanged. The frozen candidate executable and source/build hashes
are under `build/perf01-real-memory-20261002/probe-code4k/`.

## FPGA resource reference and completed candidate fit

The completed P10 fitted design is preserved in
[resources-before](../evidence/perf01-code4k-20261002/resources-before/resources.json),
with original map/fit summaries, the Fitter resource table and SHA256 identities
of the full report, frozen source manifest and delivered RBF. This is the
predecessor with 512 bytes of instruction payload and 1 KiB of data payload.
The candidate production RTL is commit `0399806`.

| Fitted resource | P10 reference | P13 candidate | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 28,873 / 41,910 (69%) | 32,609 (78%) | +3,736 |
| ALMs used in final placement | 34,740 / 41,910 (83%) | 38,741 (92%) | +4,001 |
| Total registers | 37,171 | 44,251 | +7,080 |
| M10K blocks | 414 / 553 (75%) | 415 (75%) | +1 |
| Block memory bits | 3,267,227 / 5,662,720 (58%) | 3,293,851 (58%) | +26,624 |
| Allocated block memory implementation bits | 4,239,360 (75%) | 4,249,600 (75%) | +10,240 |
| DSP blocks | 39 / 112 (35%) | 39 (35%) | 0 |
| PLLs | 3 / 6 (50%) | 3 (50%) | 0 |

The instruction payload increases by 3.5 KiB. Tag mapping and logic change as
well, so that byte difference is not an estimate of additional M10K/ALM usage.
The completed user compilation uses the same device and Quartus version;
its frozen outputs, source identities and entity rows are retained in
[resources-after](../evidence/perf01-code4k-20261002/resources-after/README.md).
Mutable reports initially mixed an old fit and the ongoing candidate map;
the table now uses the completed fit rather than that intermediate state.

The instruction-buffer entity rises from 332.0 to 4,127.9 estimated ALMs and
from 277 to 7,456 dedicated registers. Data uses four M10Ks, versus one in P10;
the two old tag RAM copies disappear and the 512-entry tags map to logic.
Synchronous source and a `ramstyle` attribute did not guarantee tag RAM
inference. Whole-design deltas also include packing/duplication changes.
The user requests reducing this cost while retaining the measured improvement.

### User-reported hardware improvement

[The supplied screenshots](../evidence/perf01-code4k-20261002/hardware/README.md)
report 4911 / 94.4K in CHECKNUM, versus 4361 / 83.7K with P10: +12.612% /
+12.784%. CheckIT reports 4911 / 95.1K, versus 4361 / 84.1K. Math observations
are retained separately. Against standalone SPK286 at 50 MHz, hardware now
achieves 63.70% of its integer rate and 70.82% of its math rate. Loaded RBF
identity follows the conversation; no repeat distribution or general software
acceptance is claimed.

The STA summary gives `FPGA_CLK2_50` setup/hold of -1.052/+0.250 ns at Slow
100 C, -0.888/+0.210 ns at Slow -40 C, +2.557/+0.134 ns at Fast 100 C and
+2.726/+0.107 ns at Fast -40 C. These are existing summary values, not a renewed
full timing/constraint audit. This candidate does not establish 50 MHz closure.

## Measurement and physical acceptance

The candidate is executing the unchanged CHECKNUM executable on the same
initial disk and calibrated CMOS as the old-capacity arm, at actual 50 MHz
CPU / 8 MHz ISA. At this implementation commit, complete candidate scores are
pending. No full CPU regression, FPGA fitter, timing closure or new RBF was
run for this milestone. Synchronous arrays are intended for block-RAM inference;
their actual mapping and 50 MHz timing still require Quartus evidence.

The first candidate measurement (`pcat-code4k`) was interrupted by the host
runner's thread-stop timeout during Whetstone. Its guest did not reach RC0 or
`ALL_DONE`, so it is not an accepted two-score result. Its original failed-run
receipt is retained under `build/perf01-real-memory-20261002/pcat-code4k/`.
The sampler now takes CPU and RTL values in one coherent stop and records a
transient stop timeout as a skipped sample, without accepting incoherent data.
A fresh image/CMOS repeat (`pcat-code4k-repeat1`) uses the identical frozen
candidate binary; only the host measurement script differs.
