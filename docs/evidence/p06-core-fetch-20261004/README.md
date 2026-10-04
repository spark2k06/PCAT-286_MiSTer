# Frozen P06 M4 evidence

Directed private full CPU register/CODE acceptance; production sources, QIP,
MAX RBF and frozen M3 are unchanged.

- `receipt.json`: source/artifact hashes and measured scope.
- `private-rtl/`: deterministic real CPU/executor/fetch selection.
- `fetch/`: 297 scenarios, paired Icarus/Verilator edge traces.
- `historical/`: warm/cold, late dependencies, lifecycle, scope and stream runs.
- `bus-guards/`: 52 injected unsupported demands; guards, not historical timing.
- `original-max/`, `private-max/`: identical 208-case per-edge traces.
- `generic-*.json`: isolated fetch mapping, not FPGA ALMs or STA.
- `max-fetch-equivalence.log`: 170 sequential equivalence cells proven.
- `negative-run.log`: early raw publication fails the timing oracle.
- `freeze.json`, `audit.py`, `acceptance.json`: integrity/reconstruction checks.

Reproduce in a fresh output directory:

```sh
python3 scripts/run_p06_timed_fetch.py --output build/p06-fetch-reproduce
python3 docs/evidence/p06-core-fetch-20261004/audit.py --output build/p06-fetch-audit
```

See [the M4 report](../../optimization/P06_CORE_FETCH_PILOT_20261004.md).
No total regression, production adoption, RBF or hardware fit is claimed.
