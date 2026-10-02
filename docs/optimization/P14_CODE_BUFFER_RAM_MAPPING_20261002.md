# P14: preserve the 4 KiB buffer with RAM tags

Date: 2026-10-02. PERF01 resource-cost milestone following the user's
4911 / 94.4K CHECKNUM result on MiSTer. The capacity and observable bus
latencies of P13 remain unchanged.

## Cause and correction

The completed P13 fit used 38,741 physically placed ALMs (92%). Its
instruction-buffer data mapped to M10K, but the tags occupied registers.
The module used 7,456 dedicated registers after fitting. A synchronous read
and `ramstyle` attribute alone had not secured RAM inference.

The tag array was also referenced by asynchronous reads hidden behind
parameter conditions. Quartus 17 retained those references during memory
inference. Separate generate branches now declare the synchronous and
asynchronous arrays independently. The production 512-line branch has only
a synchronous tag read.

The production data and tag reads now share the local acceptance enable.
Write and bypass requests discard the extra data word. This simpler template
also resolves data RAM inference in the isolated Quartus check. Reads and
fill writes occur in different states, so no simultaneous read/write collision
is introduced. Small asynchronous-tag elaborations retain their hit enable.

The state machine, physical write completion, cancellation/draining,
invalidation, 512 eight-byte lines and 1 KiB data buffer are unchanged.
CPU options and the 50 MHz release configuration are unchanged.

## Analysis & Synthesis results

The [evidence record](../evidence/perf01-code4k-tags-20261002/README.md)
retains both map summaries, entity/RAM rows and full-report hashes. Both
columns below are **Analysis & Synthesis**, not Fitter occupancy.

| Resource | Previous 4 KiB map | Corrected 4 KiB map | Delta |
| --- | ---: | ---: | ---: |
| Whole PCAT registers | 42,403 | 35,680 | -6,723 |
| Whole PCAT estimated ALMs needed | 34,101 | 31,317 | -2,784 |
| Whole PCAT block memory bits | 3,293,851 | 3,300,507 | +6,656 |
| Code-buffer dedicated registers | 7,331 | 607 | -6,724 |
| Code-buffer combinational ALUTs | 5,223 | 3,227 | -1,996 |
| Code-buffer block memory bits | 32,768 | 39,424 | +6,656 |

The production tag RAM is 512 x 13 bits and the data RAM is 2048 x 16 bits.
Both are simple dual-port M10K memories. The tag storage should consume one
additional M10K; final whole-design block counts and packing require Fitter.
The isolated module also maps both arrays to RAM: 736 registers and 39,424
memory bits, including its exposed diagnostic outputs.

The full map completed with zero errors in 8:21. Its 1,202 input files were
frozen before execution. Afterwards 1,201 were byte-identical. Quartus appended
258 assignment commands to the copied QSF; every command matches an existing
assignment in the QSF or its sourced configuration files after tokenization.
The original QSF text was preserved. Before/after QSF files and the review
record are retained. Production RTL/top/config still match the frozen inputs.

The previous map comes from the completed user compilation preserved in P13;
its source identity was captured after that build. The new run has a pre-build
source manifest. These are the provenance limits of the comparison.

## Directed behavioral checks

| Check | Result |
| --- | --- |
| Production scoreboard: 1 / 64 / 512 lines, enabled/disabled, Icarus and Verilator | PASS |
| 512-line enabled scoreboard | 1,769 requests / 126,090 checks in each simulator |
| Memory-port/code/data chain, 64 and 512 code lines | PASS: CPU/DMA/loader coherence, refresh, burst, reset |
| Paired old/new buffer under the 512-line scoreboard traffic | PASS: 24,561 compared cycles |
| Isolated Quartus RAM inference check | PASS: both expected M10K dimensions, register bound |

The paired check compares acceptance, READY, data-valid, valid response data,
physical command metadata and diagnostic outputs each cycle. Inactive data
payloads are excluded. This demonstrates matching responses and latencies
for the exercised traffic; it is not formal equivalence or a full regression.

Reproduction from this milestone's sources:

```sh
bash scripts/test_at_code_buffer_equivalence.sh
bash scripts/test_at_code_buffer_production.sh
bash scripts/test_at_ram_read_buffer.sh
bash scripts/check_at_code_buffer_quartus.sh
# Full project mapping only, preferably in a frozen copy:
quartus_map PCAT-286
```

The paired script uses commit `0399806` as its baseline. The isolated script
requires the existing Quartus Docker image and does not run Fitter or emit RBF.

## Next physical acceptance

The RTL is ready for the user's final synthesis. No new Fitter, STA or RBF was
produced here. The last fitted percentages still describe the older P13 RBF:
78% equivalent ALMs, 92% physical ALMs and 75% M10K. The corrected design's
placed occupancy and 50 MHz setup/hold remain to be measured.

The in-progress CHECKNUM repeat uses the frozen P13 executable. Its result
will measure the 4 KiB control behavior in the private 86Box adapter; it is not
a hardware benchmark of this RAM-mapping correction. A new MiSTer RBF should
confirm retained throughput after fitting. Further PERF01 changes remain
separate from this resource correction.
