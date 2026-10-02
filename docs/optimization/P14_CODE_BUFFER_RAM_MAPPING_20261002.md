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

## Completed user fit and hardware observation

Implementation commit: `84dbf17`. The user has synthesized and tested the
correction. The [fit/hardware evidence](../evidence/perf01-code4k-tags-20261002/fitted-hardware/README.md)
retains the reports, source identities and supplied screenshots.

| Fitted resource | Previous 4 KiB RBF | P14 RBF | Delta |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 32,609 (78%) | 30,552 (73%) | -2,057 |
| ALMs used in final placement | 38,741 (92%) | 36,043 (86%) | -2,698 |
| Total registers | 44,251 | 37,733 | -6,518 |
| M10K blocks | 415 (75%) | 416 (75%) | +1 |

The instruction-buffer entity uses 830 dedicated registers and five M10Ks,
versus 7,456 registers and four M10Ks before. Its estimated ALMs fall from
4,127.9 to 2,001.3. These entity estimates and whole-design placement totals
have different packing and duplication effects.

The supplied CheckIT observation remains **4911 / 95.1K**. CHECKNUM reports
**4911 / 99.1K**, versus 4911 / 94.4K before. Its math value is 4.98% higher,
but CheckIT is unchanged and neither has a repeat distribution. This supports
retained benchmark throughput; it does not establish a math speedup caused by
the inference rewrite or new general-software/full-regression acceptance.

### Existing STA report review

| Model | CPU/system 50 MHz setup | CPU/system 50 MHz hold |
| --- | ---: | ---: |
| Slow 100 C | +0.167 ns | +0.249 ns |
| Slow -40 C | +0.369 ns | +0.239 ns |
| Fast 100 C | +2.561 ns | +0.134 ns |
| Fast -40 C | +2.733 ns | +0.118 ns |

The complete summary has one negative row: HDMI PLL clock setup **-0.104 ns**
at Slow -40 C, TNS -0.231 ns. Other summary rows, including all hold,
recovery/removal and pulse-width rows, are positive. Thus CPU/system 50 MHz
meets its reported setup/hold constraints, while whole-design closure remains
pending. The user elects to keep P14 and defer HDMI while pursuing PERF01.

The unconstrained-path summary reports no illegal/unconstrained clocks and
retains platform input/output exclusions. Current production sources/config/SDC
match the frozen P14 map inputs, but the user fit was captured post-build.
This is a review of existing reports, not a renewed full constraint audit.
No compilation or regression was launched for this observation update.

### Initial milestone boundary

At the initial P14 commit the RTL was ready for the user's final synthesis;
only mapping and directed checks had been run. The later user fit above now
supplies placed occupancy and STA results for that correction.

The CHECKNUM repeat uses the frozen P13 executable and measures the 4 KiB
control behavior in the private 86Box adapter. It has now completed at
5390 / 101.4K; [P15](P15_DATA_BUFFER_ASSOCIATIVITY_PLAN_20261002.md) retains
the measurements and proposes addressing data-buffer conflicts next.
It is separate from the hardware
observation of this RAM-mapping correction. Further PERF01 changes remain
separate from P14.
