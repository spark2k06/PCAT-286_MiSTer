# P06 provisional component evidence

The [progress document](../../optimization/P06_PILOT_PROGRESS_20261003.md)
defines tested scope and omissions. This is directed component/abstract-caller
evidence, not historical CPU, physical-board or FPGA fit acceptance.

- `clock`: initial verified milestone, sources and runner at commit `905a786`.
- `bus`: initial verified milestone, sources and runner at commit `dcb6f38`.
- `duration` and `fixture`: third milestone, final source/runner hashes in receipts.
- `acceptance/clock` and `acceptance/bus`: reruns with the third milestone runner;
  the original milestone receipts/logs above remain frozen.
- `acceptance.json`: aggregate receipt hashes, source/log integrity and unchanged
  production-source checks for the final four stages.

Each receipt pins source SHA-256, tool versions, generic synthesis, failing
mutation, logs and scope. Exact Yosys generic counts can vary with source
elaboration scope; `generic_synthesis_top` identifies the measured component.
In particular, the coupled test synthesizes only the duration component, not
the testbench, mocked caller/backend or a full CPU. These are not Cyclone V
ALMs or STA. Production components and current fixed50 RBF are not modified.

Reproduce with the runner in the relevant commit and a **fresh** output path:

```sh
python3 scripts/run_p06_pilot.py --stage clock --output build/p06-clock-new
python3 scripts/run_p06_pilot.py --stage bus --output build/p06-bus-new
python3 scripts/run_p06_pilot.py --stage duration --output build/p06-duration-new
python3 scripts/run_p06_pilot.py --stage fixture --output build/p06-fixture-new
```

Stages require WSL/Linux Icarus Verilog, Verilator, Yosys and Python. Strict
RTL lint, dual-simulator directed runs, intended failing mutations, generic
synthesis and source-stability guards must all pass before a receipt exists.
No Quartus fit, full project regression or historical DOS boot was run here.

`audit.py` verifies the final receipts, preserved initial logs, production
source hashes, unchanged DOS COM and this milestone's local documentation
links. Unrelated links already absent at the preceding `dcb6f38` baseline are
recorded separately in `acceptance.json`; they are not counted as valid links.
The aggregate can be reproduced in this milestone's checkout with
`python3 docs/evidence/p06-pilot-20261003/audit.py` (verification only) or with
`--output` naming a new file. Later production/fixture changes intentionally
invalidate this checkout-bound audit; use its commit to reproduce the result.
