# Frozen P06 M6c full CPU aligned READ evidence

Accepted private 6 MHz virtual pilot for prefix-free Real Mode A1,
`MOV AX,[moffs16]`, using actual microcode, DATA service and original TMP0.
Production CPU selection, config and selected MiSTer RBF remain unchanged.

- `receipt.json`: source and generated CPU hashes, tools, exact counts,
  eleven MAX units, seven negative controls and partial cost scope.
- `private-rtl/`: seven exact selected CPU modules. Only this CPU is compiled
  in the timed tests; `shared-source/` and `frozen-iu-source/` retain ancestor
  reconstruction provenance.
- `memory/`: 267 warm + 267 cold A1 inputs and 1,248 lifecycle/scope/mixed
  cases. Each summary and compressed edge trace has both simulator versions.
- `original-memory-max/`, `private-memory-max/`: identical 267-case original
  and private MAX A1 traces, including original MOVE/END separation.
- `original-register-max/`, `private-register-max/`: identical 208-case
  original/private MAX register traces, with private input controls toggled.
- `frozen-iu/`, `memory-iu/`: exact warm/cold preservation of 688 M5 streams
  and 1,448 RR/RI instructions in each run.
- Eleven affected unit directories: original unit assertions retained with
  private port adaptation, executed by both Icarus and Verilator.
- `max-*-equivalence.*`, `max-*-gold.sv`: BIU/fetch sequential MAX proofs,
  keeping private inputs arbitrary on both interfaces. Generic MAX netlists
  additionally require those private controls to have no functional cone.
- `generic-*`, `p06_memory_commit_cost.sv`: isolated BIU/fetch mappings and
  actual new executor pending/retire assignments. Not complete FPGA cost.
- `negative-*-run.log`: specified failures for timing bypass, minimum6,
  dropped READ waits, inverted TMP0 pending and three invalid configurations.
- Five `ancestral-*-acceptance.json` files: preservation audits of earlier
  immutable M3/M4/M5/M6a/M6b evidence.
- `freeze.json`, `audit.py`, `acceptance.json`: raw/compressed SHA checks,
  CPU reconstruction, exact vector/ID coverage and acceptance result.

`*.csv.gz` are lossless edge traces. Their original uncompressed hashes stay
in the receipt. All **48 dual CPU trace pairs** match byte for byte; there
are 1,698 off-boundary captures in the aligned matrix.

## Directed modes

Each mode is run both warm and cold.

| Mode | Scope | Cases per run |
| --- | --- | ---: |
| 1 | Pause at retained TMP0 | 38 |
| 2 | Controller error at retained TMP0 | 38 |
| 3 / 4 / 5 | Redirect / reset / HOLD at retained result | 38 each |
| 6 | Unsupported HLT suffix after successful A1 | 38 |
| 7 / 8 / 9 / 10 | Pause / redirect / reset / HOLD after DATA acceptance | 38 each |
| 12 | Odd-word scope guard, excluding segment-limit crossing | 26 |
| 13 / 14 | Unsupported prefix / write instruction | 38 each |
| 15 | READ wait accounting while EU paused | 21 |
| 16 | READY/Tc exactly on 5+wait deadline; commit at next boundary | 3 |
| 17 | HOLD on first waited Tc; accepted wait versus publication guard | 21 |
| 18 | Redirect/cancel on first waited Tc; physical drain | 21 |
| 20 / 21 | Real RR to A1 / A1 to RR dependency streams | 38 each |

The independent commit oracle derives readiness from original TMP0/MOVE,
not the new pending export or DUT permit. DATA admission, logical completion,
address/lane/payload, consumed bytes, queue reservations, architectural state
and the budget `5 + qualified READ waits` are separately checked.

```sh
python3 docs/evidence/p06-core-memory-20261004/audit.py --output build/p06-memory-audit
```

See [the milestone report](../../optimization/P06_CORE_MEMORY_CPU_PILOT_20261004.md).
This evidence does not accept exact Intel issue phasing, odd-word beats,
writes, I/O, events, complete historical speeds, public profile integration,
physical AT calibration, a complete regression, FPGA fit, STA or a new RBF.
