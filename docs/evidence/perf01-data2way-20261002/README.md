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

Full CHECKNUM and FPGA fit results are pending at this implementation milestone.
Their frozen runs are under `build/perf01-data2way-20261002/` and
`build/perf01-data2way-fit-20261002/`. No full regression is part of P15.
