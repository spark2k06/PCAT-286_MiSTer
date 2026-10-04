# Frozen P06 M6e private A1 odd-word CPU evidence

Directed acceptance of the private 6 MHz virtual CPU. Production source
selection, config and RBF remain unchanged; there is no full regression or fit.

- 834 vectors (741 odd/93 aligned) run warm/cold: 1,668 cases.
- 472 pause/cancel/reset/scope cases and three independent deadline cases:
  **2,143 timed cases** in total.
- Original/private MAX each executes 834 vectors with identical traces.
- Four preserved warm/cold pairs match frozen M6c/M6d: 267 aligned A1 cases
  and 240 consecutive programs/1,120 instructions per temperature.
- **43 byte-identical dual full-CPU trace pairs** and eight specified
  negative failures, including immediate and retained assembly separately.
- Four affected MAX units, three strict CPU lint configurations, microcode
  consistency, three sequential component proofs and private-input cone checks.

`receipt.json` pins sources, eight generated modules, caller inputs, traces,
mutants, tool versions and isolated costs. `freeze.json` pins raw artifacts
and losslessly compressed traces. `audit.py` reconstructs the CPU, checks
all architecture/coverage and negative source mutations, compares preserved
traces against ancestor hashes, and checks netlists/proof/lint/unit logs.
`acceptance.json` records that audit's result.

`first_tc`/`final_tc` trace columns are post-edge diagnostic levels, not
pre-edge event pulses. Completion counters and phase oracles are sampled
before the edge. The auditor independently derives earliest first Tc from
DATA admission, first physical READY, waits and observed virtual boundaries.

The isolated BIU/duration delta is +30 generic cells/+4 register bits. Existing
payload storage is reused. This is not Quartus ALMs or complete CPU/FPGA cost.
Cancel drains accepted halves; reset aborts the original backend. HOLD is an
invalid scope guard here and requires reset to recover, not accepted historical
HOLD/HLDA service. Native pin accuracy and complete public speeds remain open.

```sh
python3 docs/evidence/p06-core-odd-read-20261004/audit.py --output build/p06-odd-read-audit
```

See [the report](../../optimization/P06_CORE_ODD_READ_CPU_PILOT_20261004.md).
