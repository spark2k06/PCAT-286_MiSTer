# Protected Expand-Down Validation Strategy

## Decision

`spk286_protected_expand_down_tb` is the authoritative full protected-mode
matrix for expand-down segments and the related PM1--PM4 privilege paths. It
remains unchanged and is executed completely with Icarus.

The matrix is deliberately excluded from the Verilator unit loop. Verilator
elaborates the complete `spk286` top level before running any checks, and this
particular testbench produces an exceptionally large generated C++ model. The
unit runner reports the exclusion explicitly as a skip; it must not be read as
a Verilator pass.

The existing `spk286_protected_system` and
`spk286_protected_event_outer` banks continue to run in both simulators and
provide the Verilator cross-check for the affected descriptor, segment, event,
and outer-privilege services. No RTL behavior or expected result was changed.

## Measurements

The full matrix was run on 2026-09-15 with Icarus 12.0 and VVP 12.0:

```text
PROTECTED_EXPAND_DOWN PASS: 2183 checks, READY stalls=3005372
elapsed=1:53.42 maxrss=32256KB
```

The command used a separate output directory:

```text
SPK286_BUILD_DIR=build/phase9-alt-iverilog \
  bash scripts/test_units.sh iverilog spk286_protected_expand_down
```

The earlier Verilator attempt generated 235 C++ dependency units and was
cancelled during compilation before the test executable existed. The largest
generated source was over 220 MB and the intermediate directory reached about
1.7 GB. Splitting only the stimulus into several wrappers did not remove the
large units because they are dominated by the elaborated `spk286` top level;
using `-O0` likewise did not materially improve generation time. Those
experiments are not validation results.

## Regression policy

When `scripts/test_units.sh` is invoked with `both` or `verilator`, the full
expand-down matrix prints an explicit `VERILATOR SKIP` line and does not claim
success for that simulator. An explicit Icarus invocation remains required
for the complete 2,183-check matrix. The remaining dual-simulator protected
banks are still run normally.

This is an environment-aware validation split, not a relaxation of the
architectural checks. A future Verilator optimization or a genuinely smaller
integration harness may restore full dual-simulator execution, but it must
first produce the same matrix coverage and a reproducible executable result.
