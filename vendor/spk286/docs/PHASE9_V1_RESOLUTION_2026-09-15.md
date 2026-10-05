# Phase 9 V1 focused resolution

This document closes the focused `call-stack-precheck` mutation item on
`codex/phase9-timing-tstates`. It does not approve the complete Phase 9 gate:
the global regression and historical timing validation remain separate pending
work.

## Finding and root cause

The inherited far mutation audit used the text anchor
`stack_pointer<16'd4`, which targeted the older `CHECK_PUSH2` range predicate.
That operation is not emitted by the current generated `CALL_FAR` microcode,
so the mutation did not exercise the live call-frame precheck. The old far
bench therefore could not distinguish the weakened mutant from the RTL under
test. This was a verification gap, not evidence that the two implementations
were architecturally equivalent.

The probe now mutates the live predicate in `call_stack_range_fault`:

```text
stack_pointer[0] && stack_pointer < 16'd4
```

to the intentionally defective:

```text
stack_pointer[0] && stack_pointer < 16'd2
```

No production RTL or generated microcode was changed.

## Focused discriminating bench

`sim/unit/spk286_call_stack_precheck_tb.sv` enters protected mode, loads a
same-level call gate, and uses a ring-0 expand-down stack with limit zero.

| Case | Contract | RTL result |
|---|---|---|
| `SP=0003` | Reject before the first frame transfer; the first word is legal but the second would wrap past `FFFF` | `#SS` vector `0C`, zero stack writes, `SP` preserved |
| `SP=0005` | Positive control: both frame words are valid | reaches target `HLT`, four lane transfers for the two odd-address words, final `SP=0001` |

The expand-down descriptor makes `SP=0003` discriminating: a weakened
precheck can perform the first physical word transfer before the later stack
fault. The mutant run did exactly that and was rejected by the independent
write-count assertion (`writes=2` before `#SS`).

## Validation performed

All commands below were run from the repository root without launching the
global Phase 9 regression:

```text
python3 -m unittest -v tests.test_mutation_anchors
python3 -m tools.microcode.compile_microcode --check
bash scripts/test_units.sh iverilog spk286_call_stack_precheck
bash scripts/test_units.sh verilator spk286_call_stack_precheck
bash scripts/test_units.sh verilator spk286_far_instructions
SPK286_BUILD_DIR=build/v1-audit-focal2 python3 -m tools.audit_far --build-dir build/v1-audit-focal2
```

Observed results:

- mutation-anchor unit test: `1` test passed;
- microcode consistency: `120 entries, 717 words, 10-bit addresses, 8-bit control`;
- focused bench: `CALL_STACK_PRECHECK PASS: 9 checks` in Icarus and Verilator;
- original far-instruction bank: `FAR_INSTRUCTIONS PASS: 6760 cases; 650606 checks; 1296 immediate stalls` in Verilator;
- far audit: `12 rejected RTL mutants; 3 pristine benches; source bytes unchanged`.

The audit's original and focused pristine benches both pass. The intended
`call-stack-precheck` mutant is rejected by the new focused bench; no compile
failure is counted as rejection.

## Reproducible evidence

The focused audit outputs are retained in the ignored build directory:

- `build/v1-audit-focal2/far-audit/call-stack-precheck/run.log`
  (`d9dbee65d9bb8259e0fe8da872fdb2e4310ac3ccdf244957399f27e08483e12d`);
- `build/v1-audit-focal2/far-audit/data.txt`
  (`30a9a8d8ff045f3ce0889541d548ae1bc092bb1338bc2fb9d37f439adcfac3f3`);
- `build/v1-audit-focal2/far-audit/source.sha256`
  (`7926d578183362e4144f9f39a2d482478ea49bbe0239fd061cf81f6f2e732bc2`).

The focused bench source hash at validation time was
`bb58b0d38b6ce96ad14005f6301c84370da31c9400c54d732fa87213839fe9ab`.

## Status

V1's focused mutation and functional coverage gap is closed. The earlier audit
documents remain historical records of the open state. The final Phase 9
global regression, V1's inclusion in that final gate, and historical timing
validation remain pending as planned; no historical cycle-accuracy claim is
made here.
