# 512-byte instruction buffer at 50 MHz — 2026-09-22

The PCAT physical memory path now uses 64 direct-mapped lines of eight bytes.
This implements the candidate selected in the [capacity experiment](CODE_BUFFER_CAPACITY.md),
on top of `266f5b49c4c63b25bb5d7e857a77084bcb9511a7`. Standalone SPK286,
vendored CPU RTL/microcode, the 50 MHz clock, NO_DEBUG, P01/P02/P05/P06 and
the 16 MiB memory map are unchanged. This is a PCAT chipset optimization,
not a claim of historical 286 cycle accuracy.

## Implementation

The 256x16 data array has a synchronous read and no reset. A hit reads the
array on its accepting edge and returns the registered word in the existing
HIT state, retaining the measured no-extra-clock behavior. A miss writes the
four physical burst words into the selected slot and separately captures the
requested word for its final response. The line becomes valid only on the
last physical beat with READY; cancellation drains an accepted burst fully.

For 64 lines, index bits are physical address 8:3 and tag bits are 24:9.
Together they retain the complete canonical physical line address. Data reads,
writes, DMA, HPS loader and AT refresh still bypass the buffer. There is no
data cache, dirty state, write posting, early miss response or larger CPU queue.
`LINE_COUNT=1` remains available for verification; production defaults to 64.

Two inherited coherence defects are corrected:

- Invalidation uses the physical word and enabled lanes. An upper-byte write
  supplied at an odd line-end address invalidates that line, not its neighbor.
- CPU cancellation flushes every valid line, including in IDLE and while
  another owner completes. DMA and loader completion are not cancelled.

The response also uses accepted metadata rather than a live upstream word
index, and the first miss command presents the current request's cycle class.
The [original audit](CODE_BUFFER_COHERENCE_AUDIT.md) records the old failures;
the current audit runner requires successful completion in both simulators.
No causal connection to the Windows 3.1 reboot has been established.

## Measured behavior

The eight fresh production workload/control runs exactly match the selected
experimental model or the old disabled-buffer reference: result counters,
CPU accounting, transfer latencies, GPR/FLAGS and the 64-bit FNV hash of all
2 MiB of backing memory. Retired instructions and logical/physical writes
also equal the previous production buffer. This is synthetic firmware with
the physical SDRAM owner and pin model, not DOS CheckIt.

| Workload | Previous one-line clocks | New clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Integer mix | 1,140,987 | 1,019,306 | +11.94% |
| Fixed-point mix | 950,487 | 780,008 | +21.86% |
| Working set | 1,064,066 | 1,015,773 | +4.75% |
| Dhrystone 2.1 fixture | 1,246,833 | 1,004,796 | +24.09% |

Gain is `100 * (previous_clocks / new_clocks - 1)`. Source hashes are checked
against the frozen synthesis snapshot. The comparison is recorded in
[the production receipt](code_buffer_512b_50mhz_comparison.json).

## Verification

The independent byte scoreboard passes one and 64 lines, ENABLE 0/1, in
Icarus and Verilator: eight executions, 2,532 requests and 137,814 assertions.
It covers every slot, replacements, all writers/lanes, full physical tags,
changing input metadata after acceptance, enable/bypass, global reset and CPU
cancellation at each burst beat. Hit response latency remains one clock from
buffer acceptance. A separate mutation audit rejects six functional defects;
compilation errors and timeouts do not count as successful rejections.
The three historical coherence cases also pass in both simulators.
The [validation receipt](code_buffer_512b_validation.json) includes source/log
hashes, exact results, the six rejecting mutation assertions and integration
evidence.

The integrated warm-reset fixture executes conflicting cached instruction
lines, odd data accesses, a real IRQ0 handler/IRET and AT refresh. Before each
reset it verifies one serviced IRQ, 253 refreshes, 225 hits and 78 misses.
Resets at IDLE, COMMAND, WAIT and COMPLETE each produce one new reset-vector
fetch and at least 16 post-reset CPU fetches, with no stale response delivered.
The same physical harness verifies the 16 MiB profile and RAM/BIOS isolation.

All eight integration banks pass: memory port, physical SDRAM owner, HPS ROM
loader, CDC, machine boundary, LOADALL/XMS, memory workload and warm resets.
The machine diagnostic completes 107 memory beats, 12 I/O writes, 32 IRQ0
observations and 27 refresh observations. The physical LOADALL fixture completes
three LOADALL operations and 32 extended-memory copy bytes, including A20
aliasing and byte lanes. The RAM16 probe checks 238 backend blocks and 65,536
BIOS bytes. These are bounded fixtures, not a Windows boot test.

The legacy memory-performance bench needed its
missing CPU BIOS alias adapter and 25-bit backend wiring updated; it previously
failed at the reset vector even with the buffer disabled. Production mapping
is unchanged. The optional Phoenix PM87 test was unavailable because its
version-specific ROM is absent; it is not reported as passed.

## Synthesis and artifact

Quartus 17.0.2 analysis/synthesis passes. Its RAM report identifies the data
array as a 256x16 simple-dual-port M10K, plus two 64x16 tag-memory instances
for the independent lookup addresses. The fit uses three M10Ks for the buffer
in total. The first attempt stopped because Quartus 17 does not
synthesize `$countones`; the diagnostic count now uses an equivalent fixed
loop. The second attempt uses a fresh frozen workspace with no reused database.

The clean full compilation completes successfully in 29 minutes 56 seconds;
the standard four-corner timing report takes another 1 minute 58 seconds.
The fitted inventory confirms `no_debug=1 observers=0`, 64 enabled lines and
`FPGA_CLK2_50 period=20.000`. All 760 checked production-tree input files still
match the frozen manifest. Later changes to verification harnesses have their
own compilation hashes and do not change the fitted production inputs.

| Whole-project resource | Previous RBF | New RBF |
| --- | ---: | ---: |
| ALMs | 27,827 / 41,910 (66%) | 28,790 / 41,910 (69%) |
| Registers | 34,260 | 34,365 |
| RAM bits | 3,152,832 | 3,158,976 |
| RAM blocks | 395 / 553 | 398 / 553 |
| DSP blocks | 38 / 112 | 38 / 112 |
| PLLs | 3 / 6 | 3 / 6 |

The new [PCAT-286_CODE_BUFFER_512B_50MHz.RBF](../../output_files/PCAT-286_CODE_BUFFER_512B_50MHz.RBF)
is 4,067,460 bytes. SHA-256:
`dcb8733e12608a2308498fdb26535414fc79830dc41152f4b81a342f3a783bea`.
The copied binary matches the fresh Quartus output. JSON and SHA-256 sidecars
identify its sources and validation; the [build receipt](code_buffer_512b_build.json)
also records the fitted resources and timing-report locations.

| Timing corner | CLK2 Fmax (MHz) | CPU setup (ns) | CPU hold (ns) | Global setup (ns) | Global hold (ns) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow, 1100 mV, 100 C | 39.32 | -5.435 | +0.242 | -20.334 | -2.167 |
| Slow, 1100 mV, -40 C | 39.65 | -5.220 | +0.236 | -20.420 | -1.884 |
| Fast, 1100 mV, 100 C | 73.36 | +6.368 | +0.131 | -10.354 | -0.943 |
| Fast, 1100 mV, -40 C | 86.52 | +8.442 | +0.116 | -8.657 | -0.900 |

**The build does not close timing at 50 MHz.** Slow/100 C CLK2 Fmax decreases
from 41.14 to 39.32 MHz and CPU setup slack changes from -4.306 to -5.435 ns.
Placement/routing changed with the larger design; unchanged CPU RTL does not
imply unchanged physical timing. Fmax describes same-clock paths, not complete
system timing closure. No clock constraint or timing exception was changed.

The dedicated buffer report finds 327 fitted registers. Paths from CLK2 into
the buffer and all reported paths from the buffer have positive setup/hold
margins in every corner. Their worst setup margins are +1.459 ns and +2.508 ns,
respectively. Incoming paths from other domains still fail: the worst buffer
setup slack is -5.580 ns, from `sysmem|init_reset_n` to a valid bit. This prevents
claiming complete buffer timing closure. CPU, reset, video/HDMI and other
global failures remain in the full reports. This is a test RBF at the requested
frequency; Windows 3.1 startup remains unverified by this change. The hardware
CheckIt observation below does not establish timing closure or general stability.

## User-reported hardware CheckIt measurement

On 2026-09-22 the user supplied a hardware CheckIt screenshot after testing
the new buffer. Compared with the preceding immediate-execution build:

| CheckIt result | Previous build | 512-byte buffer | Observed change |
| --- | ---: | ---: | ---: |
| Dhrystones | 3,400 | 3,489 | +2.62% |
| Whetstones | 69.8K | 71.9K | +3.01% |
| Estimated CPU frequency | 34.89 MHz | 34.96 MHz | Diagnostic estimate only |

These are individual user-reported screenshots, not repeated-run averages or
an independently reproduced hardware benchmark. The configured clock remains
50 MHz; neither CheckIt's estimate nor the fitted Fmax changes that clock.

The synthetic workload gains above are specific to those fixtures and are not
predictions for DOS CheckIt. This buffer only accelerates instruction fetches;
the actual CheckIt instruction/data mix and cache conflicts have not been
profiled. Other programs may benefit more or less, but that is not yet measured.
The observed roughly 3% gain must be weighed against 963 additional ALMs,
three additional RAM blocks and the lower fitted slow-corner CLK2 Fmax.

## Reproduction

```sh
bash scripts/test_at_code_buffer_production.sh
python3 scripts/audit_code_buffer_model.py --production --build-dir build/code-buffer-production-mutants
bash scripts/test_code_buffer_coherence_audit.sh
bash scripts/test_at_sdram_read_buffer.sh
bash scripts/test_at_code_buffer_integration.sh
PCAT_PROFILE=1 PCAT_BUILD_DIR="$PWD/build/code-buffer-512b-performance-final" bash scripts/test_checkit_directed.sh
python3 scripts/report_code_buffer_production.py build/code-buffer-512b-performance-final build/at-no-debug/20260922-code-buffer-512b-50mhz-r2/manifest.json
python3 scripts/record_code_buffer_validation.py
bash scripts/build_at_no_debug.sh build/at-no-debug/NEW_RUN_DIRECTORY
```

Local compile/timing outputs remain under
`build/at-no-debug/20260922-code-buffer-512b-50mhz-r2/`. Functional logs remain
under `build/code-buffer-*`; the failed initial attempts are retained separately.
The additional `scripts/report_code_buffer_timing.tcl` script runs against the
fitted workspace and requires a new output directory. Its final reports are
under `code-buffer-timing-final/` within the build directory.
