# P06-M3 frozen full-CPU evidence

`observation/` is the M3a production-CPU run: 208 cases, dual identical
edge/state traces, strict lint, microcode freshness and a wrong-result
negative control. Its source scripts are preserved in commit `732df7f`;
the CSV artifacts were explicitly included in `033ceea` despite the general
repository CSV ignore rule. The generated `test.vvp` executable is omitted.

`timed/` is M3b directed acceptance of one selected private CPU source list:
original/hooked MAX equivalence, qualified 6 MHz register minima, dependency
extensions, lifecycle, scope stops, sequential ADD and existing MAX banks.
Logs/vectors/traces/receipts are unchanged copies from the completed run.
Generic Yosys netlists and scripts refer to `p06_register_policy_cost` only;
they are not full-CPU/FPGA fit results.

`freeze.json` checksums the evidence. `audit.py` validates receipts, artifacts,
current guarded inputs, MAX/minimum traces, generic netlists and reconstruction
of the private CPU. From the project root, using Python 3:

```sh
python docs/evidence/p06-core-register-20261004/audit.py --output build/p06-m3-audit-fresh
```

Use a fresh output directory. The audit itself does not rerun simulators or
synthesis. To rerun directed acceptance, use `scripts/run_p06_timed_register.py`
under WSL with Icarus, Verilator and Yosys. No production historical profile,
DOS benchmark, physical calibration or full regression is certified here.
Scope and findings: [M3 report](../../optimization/P06_CORE_REGISTER_PILOT_20261004.md).
