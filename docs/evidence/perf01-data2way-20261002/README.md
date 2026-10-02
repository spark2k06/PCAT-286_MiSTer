# P15 two-way data-buffer implementation evidence

The buffer retains 512 physical words / 1 KiB, organized as 256 sets and two
ways. Both tag/data arrays are read synchronously in parallel. Valid bits and
one replacement bit per set are separate. Read hits/fills update recency;
physical write updates retain recency and do not allocate on a miss.

The directed tests retain alias coexistence, invalid-way filling, LRU victim
rereads, CPU/DMA/loader byte writes to both ways, CPU flush of both resident
ways and the existing cancellation/drain/burst/exclusion cases. Direct hits
are explicitly checked at the original response boundary. Icarus/Verilator
unit checks and both composed code/data pipelines pass, including 4 KiB code.
The minimum two-word, one-set elaboration also passes in Icarus.

`perf01-data2way-directed-20261002/` records the source hashes and check results.
`perf01-data2way-isolated-map-20261002/` records independent Quartus mapping:
two 256 x 32-bit simple dual-port M10K memories, 16,384 block memory bits and
957 registers with diagnostics exposed. These are isolated map counts,
not whole-design fitted resource occupancy.

`adapter-build.json` identifies the private 86Box probe, unchanged CPU model
objects, CPU backend and profiler, production inputs and data-buffer ways.
`adapter-smoke.log` checks its READY/control path and preserves sampled hit
latency (two CPU clocks) with canonical aliases and write/cancel behavior.

`fitted/` retains the completed whole-design fit, source manifest and unchanged
post-build source verification. Net cost versus P14 is +35 equivalent ALMs,
+85 placement ALMs, +289 registers and no extra M10Ks. The data entity itself
adds 342.8 equivalent ALMs and 355 registers; changes in physical synthesis
elsewhere compensate most of this in the whole-fit totals. Source-identical
code-buffer logic has a different fitted cost, so the net +35 is not a portable
standalone logic-cost claim.

CPU/system 50 MHz has -0.194 ns setup in slow 100 C; hold is positive. HDMI
has the separately deferred -0.188 ns setup in slow -40 C. The design is not
fully timing-closed. Report review does not constitute a new constraint audit.

`hardware/` preserves the user's screenshots and explicit exact-RBF/maximum-CPU
attestation. CheckIT gives 5023 / 95.6K; CHECKNUM gives 5023 / 96.4K. Both show
+2.28% integer versus 4911. CheckIT math is +0.53% versus 95.1K, whereas CHECKNUM
math is -2.72% versus the last 99.1K observation. No math repeat distribution
or established math gain is claimed.

`measurement/` retains the completed private-model CHECKNUM comparison,
receipts, phase/final profiles, coherent samples, frozen runner/sampler and
adapter manifests. P15 completed guest RC0/ALL_DONE at **5525 / 102.4K** versus
**5390 / 101.4K**, or **+2.50% / +0.99%**. Identical compiled CPU objects are
now also enforced by the comparison tool. Both hosts have explicitly classified
SIGTERM teardown after completed guests; the tool was run with
`--allow-host-teardown-issue`. No clean host exit is claimed.

`actual-vs-shadow.json` records exact matching actual/shadow data misses in both
complete function phases: 421 / 190,051 for P15 versus 378,345 / 1,931,287 for
direct data. Mean data-read waits fall from 2.54574 / 3.06706 to 2.00059 /
2.10415 clocks. The real P15 model's source uses P14's synchronous tag mapping;
the control binary is the older P13 mapping. P14's paired directed evidence
establishes matching exercised responses, not byte-identical code sources.

`trace-footprint.json` identifies both 250,000-operation bounded traces;
full CSVs and private binaries/source snapshots remain under
`build/perf01-data2way-20261002/`. 86Box owns values/peripherals and the adapter
omits DMA/loader/abstract AT-refresh arbitration and electrical board effects.
Adaptive work and single observations limit direct score/absolute-work claims.
The completed FPGA build/RBF is under `build/perf01-data2way-fit-20261002/`.
No full regression is part of P15.
