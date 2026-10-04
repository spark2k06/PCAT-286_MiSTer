# Frozen P06 M6a READ timing evidence

Private real-BIU/real-operand byte and aligned-word READ pilot, CODE=0.
Production RTL, MAX configuration and selected RBF are unchanged.

- `receipt.json`: source/generated hashes, tool versions, scope, 432/33/42
  directed case counts, MAX compatibility and restricted generic cost.
- `data/`: three dual-simulator summaries, execution logs and compressed edge
  traces. The summaries retain independent expected-case classification.
- `original-max/`, `private-max/`: 208-case full CPU per-edge equivalence.
- Six MAX unit directories: focused BIU/operand compatibility in both tools.
- `max-biu-equivalence.log`: sequential equivalence proof; generic JSON
  netlists and Yosys scripts/logs preserve the cost calculation.
- `negative-run.log`: early publication mutant rejected by the specific
  `independent logical publication oracle failed` assertion.
- `private-rtl/`: exact generated BIU and full MAX top-level source.
- `freeze.json`: frozen byte hashes; `*.csv.gz` are lossless CSV traces.
  Uncompressed hashes remain in the receipt.
- `audit.py`: checks source/evidence hashes, reconstructs private sources and
  vectors, checks paired traces, case matrix, lifecycle coverage, proofs,
  cost and production guards. It performs no new simulation or fitting.

Lifecycle kinds: 1=direct backpressure, 2=identical requests, 3=cancel,
4=reset, 6=held READY, 7=request-field poison, 8=recovery after cancel without
reset, 9=real operand caller pause. Guard kind 5 covers seven prohibited
services in six lifecycle phases. Matrix kind 0 covers 0/1/2 abstract board
waits and 48 physical READY patterns for each of three lane forms.

```sh
python3 docs/evidence/p06-core-data-20261004/audit.py --output build/p06-data-audit
```

See [the milestone report](../../optimization/P06_CORE_DATA_READ_PILOT_20261004.md)
for deliberately excluded full CPU memory timing, shared CODE/DATA ownership,
odd words, writes, I/O, events and complete speed profiles. Net +2 FF/+54
generic cells is only the restricted BIU subset, not complete FPGA overhead.
