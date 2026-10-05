# Phase 9D prefetch/instruction-unit focused evidence — 2026-09-15

This is the first focused increment after the Phase 9B/9C audit resolution.
It does not claim completion of 9D or historical 80286 prefetch timing.

## Banks executed

Each bank was run separately with an explicit simulator and an isolated build
directory on WSL `Ubuntu-24.04`:

| Bank | Verilator | Icarus | Scope |
| --- | --- | --- | --- |
| `spk286_fetch` | PASS; 26 checks | PASS; 26 checks | word/odd-byte fetch, response backpressure, redirects, cancellation, limits and reset |
| `spk286_prefetch_queue` | PASS; 19 checks | PASS; 19 checks | six-byte capacity/order, simultaneous consume/refill, pointer wrap, flush and reset |
| `spk286_core` | PASS; 7 checks | PASS; 7 checks | integrated fetch/queue path, architectural commits, redirects and reset recovery |

Representative commands were:

```text
SPK286_BUILD_DIR=build/phase9d-verilator-spk286_fetch bash scripts/test_units.sh verilator spk286_fetch
SPK286_BUILD_DIR=build/phase9d-verilator-spk286_prefetch_queue bash scripts/test_units.sh verilator spk286_prefetch_queue
SPK286_BUILD_DIR=build/phase9d-verilator-spk286_core bash scripts/test_units.sh verilator spk286_core
SPK286_BUILD_DIR=build/phase9d-iverilog-spk286_fetch bash scripts/test_units.sh iverilog spk286_fetch
SPK286_BUILD_DIR=build/phase9d-iverilog-spk286_prefetch_queue bash scripts/test_units.sh iverilog spk286_prefetch_queue
SPK286_BUILD_DIR=build/phase9d-iverilog-spk286_core bash scripts/test_units.sh iverilog spk286_core
```

The full regression was not used for this increment. A shell-expansion error
briefly started the default all-unit path before it was stopped; that partial
attempt is not included in the evidence above.

## Remaining 9D scope

The focused banks establish functional queue/refill and redirect dependencies,
but do not close the complete 9D matrix. Still pending are a reproducible
real-CPU prefetch trace covering refill thresholds and starvation under data
traffic, interaction with the timing policy layer, and any historical hardware
comparison. No arbitrary idle states or historical delays were introduced.

V1 (`call-stack-precheck`), the final global regression and all historical
timing claims remain independent open items.
