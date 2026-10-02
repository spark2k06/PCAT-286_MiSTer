# Completed 4 KiB CHECKNUM memory-control comparison

See [P15 measurement and proposal](../../optimization/P15_DATA_BUFFER_ASSOCIATIVITY_PLAN_20261002.md).

`comparison.json` was produced by `tools/perf01/compare_memory_candidates.py`
after the candidate reached guest RC0, `ALL_DONE` and a final profile. It
verifies matched disk, CHECKNUM/configuration/CMOS, CPU backend, profiler,
actual 50 MHz CPU and 8 MHz 86Box ISA. Baseline is 4804 / 88.6K, candidate
5390 / 101.4K. The candidate's code capacity is 4 KiB; data remains 1 KiB.

`baseline/` and `candidate/` preserve original measurement/configuration
receipts, coherent samples, final/phase profiles and adapter build manifests.
The candidate's runner/sampler are retained. Binary/full source snapshots and
bounded CSV traces remain under
`D:/GitHub/PCAT-286_MiSTer/build/perf01-real-memory-20261002/`.
`trace-footprint.json` identifies both 250,000-operation traces by hash and
records the bounded working-set observations; it does not predict scores.

The candidate host exit was SIGTERM (-15) after monitor-exit timeout following
successful guest completion. The baseline has the earlier explicitly
classified/reconstructed host teardown receipt. The comparison was run with
`--allow-host-teardown-issue`; these host outcomes are not hidden or treated
as clean exits. Complete guest scores are distinct from host cleanup.

No new guest execution, regression, synthesis or RTL modification was launched
for this evidence update. The run used the frozen P13 executable; P14's
RAM-mapping rewrite and user hardware observation have separate evidence.
