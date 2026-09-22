# Code-buffer capacity experiment — 2026-09-22

Historical evaluation, before production adoption. The subsequent
[512-byte production implementation](CODE_BUFFER_512B_50MHZ.md) incorporates
the corrections below and records its own RTL validation and fitted artifact.
The JSON receipts here preserve the original experiment and source hashes.

Baseline: `266f5b49c4c63b25bb5d7e857a77084bcb9511a7`, including the immediate
execution import. This is a simulation evaluation of additional instruction
buffer lines. Production RTL, CPU microcode, clock configuration and the tested
RBF remain unchanged. It does not implement a data cache.

## Method

The experiment replaces only the code-buffer module in the existing directed
whole-machine harness. The CPU, bridge, memory port, SDRAM owner, KFSDRAM and
SDRAM pin model remain in the path. The project enables P01/P02/P05/P06, at
50 MHz. All runs use the physical owner (`IDEAL_OWNER=0`). The four workloads
are deterministic synthetic firmware, including a Dhrystone 2.1 fixture;
they are not the DOS CheckIt executable.

The simulation-only model evaluates 1, 2, 4, 8, 16, 32, 64 and 128 lines of
eight bytes, direct mapping or two-way LRU, and zero or one extra clock per
hit. There are 30 enabled configurations and two disabled controls, each
running all four workloads. A separate fresh production reference runs both
enabled and disabled. The extra clock is a sensitivity test for an additional
lookup stage, not an assertion that a future BRAM implementation requires it.

Every miss retains the complete four-word physical fill. No critical-word
early response, write posting, data-read caching, CPU queue enlargement or
clock change is included. Tags retain full canonical physical addresses.
All writers invalidate matching physical lanes, and CPU cancellation flushes
the model while preserving DMA/loader completion and draining accepted fills.

The one-line/no-extra model must reproduce the production reference's complete
cycle, traffic and CPU-bucket counters exactly on every workload. Disabled
model controls must also match production bypass exactly. Every other run
must preserve all GPRs, FLAGS, a 64-bit FNV hash of the complete 2 MiB backing memory, retired
instruction count, logical writes and physical writes. Observer accounting
must partition the measured clocks and completed transfer latencies.

## Coherence findings and experimental boundary

The [production coherence audit](CODE_BUFFER_COHERENCE_AUDIT.md) reproduces a
stale-code read after an upper-byte write at an odd line-end address, through
both CPU and DMA ownership. It also reproduces failure to invalidate on CPU
cancellation while IDLE; that second finding violates the documented reset
contract without, by itself, proving corrupt returned data. Both are inherited
from the one-line production buffer and remain unfixed in production by this
evaluation. There is no demonstrated connection to the Windows boot failure.

The model uses aligned physical lane addresses, global cancellation invalidation,
a captured response word index, and the current miss's cycle class. The capacity
comparison uses these same rules at every size. Exact one-line performance
equivalence separates capacity effects from those robustness corrections for
the measured workloads; it is not a claim of equivalence on the known failing
production scenarios.

The model's dedicated independent byte scoreboard passes 120 runs across both
simulators, all capacities/ways/hit latencies and compile-time ENABLE 0/1. It
checks 38,400 logical requests and 2,093,074 assertions, including accepted
metadata, every cached slot, replacements, writers/lanes, cancellation during
all burst beats, reset and bypass. Six functional mutants are rejected. The
[validation receipt](code_buffer_model_validation.json) records each run and
mutation, including source/log hashes and the exact rejecting assertions.

## Results

The physical-SDRAM sweep passes all 128 experimental runs and eight fresh
production references. The one-line baseline and both bypass controls match
production exactly. All other configurations pass the state-signature,
instruction/write-count and observer-accounting checks described above. The
[measurement receipt](code_buffer_capacity_20260922.json) preserves every
configuration, result and source/log hash.

The recommended first production prototype is **64 lines of eight bytes,
direct mapped: 512 bytes of data plus tags and control**. It retains an
improvement in every workload even with one additional clock on each hit:

| Synthetic workload | Production clocks | 64-line clocks, no extra hit clock | Throughput gain | Gain with one extra hit clock |
| --- | ---: | ---: | ---: | ---: |
| Integer mix (`dhrystone`) | 1,140,987 | 1,019,306 | +11.94% | +10.88% |
| Fixed-point mix (`whetstone`) | 950,487 | 780,008 | +21.86% | +16.75% |
| Working set | 1,064,066 | 1,015,773 | +4.75% | +3.07% |
| Dhrystone 2.1 fixture | 1,246,833 | 1,004,796 | +24.09% | +17.50% |

Throughput gain is `100 * (production_clocks / variant_clocks - 1)`, not the
percentage reduction in clocks. With no extra hit clock, Dhrystone 2.1 code
misses fall from 33,190 to 1,626; the integer mix falls from 16,524 to 49.
The corresponding four hit rates are 99.906%, 99.930%, 76.937% and 98.484%.

Increasing to 128 lines and two ways adds only 0%, -0.043%, +2.310% and
+0.897% throughput relative to the 64-line direct-mapped candidate, in table
order. That offers little extra benefit here for twice the data capacity and
way selection. A 32-line/two-way design remains a useful later alternative:
it uses 256 data bytes and helps the working-set case more, but needs way
selection and yields less Dhrystone 2.1 improvement. Neither tradeoff has yet
been measured in synthesized FPGA resources or timing.

Production adoption should first incorporate the physical-lane invalidation
and cancellation corrections documented above. They are currently corrected
only in the experimental model. The proposed capacity is a measured candidate,
not a claim about its achievable clock rate or performance in DOS CheckIt.

One sensitivity result illustrates why total clocks must be measured rather
than estimated by adding standalone access latencies. In the integer mix,
one line with an extra hit clock improves total clocks from 1,140,987 to
1,129,341, despite increasing every hit from three to four clocks. Operand
service falls by 14,755 clocks while demanded code wait rises by 3,109;
internal execution, dispatch and retirement stay equal. These differences
sum exactly to the 11,646-clock reduction. Code fills fall from 16,524 to
16,013 and discarded prefetch bytes from 16,849 to 14,975. The observations
are consistent with a more favorable interleaving of prefetch and operand
traffic; they do not justify deliberately delaying hits as a general
optimization. The same extra clock worsens the other three one-line workloads.
Use `PROFILE_MISC.code_transfers` to count fetch transactions: the legacy
`CHECKIT_DIRECTED_PASS.code_fetches` field also accumulates waiting clocks.

## Limits and reproduction

This model is not synthesizable production RTL. There is no new resource,
BRAM-inference or timing-closure result, and no new RBF or hardware CheckIt
measurement. The baseline's unresolved timing at 50 MHz remains unresolved.
The fixed firmware layouts do not establish results for every program or ROM.
The performance harness does not generate DMA, HPS loader, interrupts or AT
refresh requests; physical KFSDRAM refresh remains active. The separate model
scoreboard exercises DMA and loader ownership and cancellation, but does not
replace whole-system integration coverage. The state signature is not an
exhaustive comparison of CPU internal state or a 16 MiB memory test.
Production adoption also needs integration checks for arbitration, DMA/refresh,
HPS loading, reset/map changes and instruction-stream coherence.

```sh
bash scripts/test_at_multiline_code_buffer.sh
python3 scripts/audit_code_buffer_model.py
bash scripts/test_code_buffer_coherence_audit.sh
PCAT_BUILD_DIR="$PWD/build/code-buffer-capacity" bash scripts/test_code_buffer_capacity.sh
```

At the time of this experiment the coherence audit deliberately expected the
documented production failures; success meant bug reproduction, not functional
acceptance. Its runner has since been converted to a positive production
regression and must now pass all assertions. Performance logs,
compiled source hashes, ROM hashes and observer results are retained under
`build/code-buffer-capacity/`. The performance runner checks that its compiled
inputs have not changed before producing its JSON report.
