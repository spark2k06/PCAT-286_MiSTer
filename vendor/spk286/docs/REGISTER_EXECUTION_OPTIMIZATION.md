# Register execution optimization — 2026-09-22

This increment reduces functional execution work in the standalone CPU. It
does not add historical delays, T-states, wait-state policy or machine logic.
The comparison baseline is `ec5605b` (`test(cpu): add physical LOADALL probe`).

## Scheduling change

Eight format-22 controls replace the first `DECODE_MODRM` in the byte/word,
both-direction ALU and MOV register/memory entries. When ModR/M selects a
register, the executor captures both operands on its accepted byte, then
executes and commits on the next enabled clock. ALU results and masked FLAGS
commit together; CMP/TEST only commit FLAGS. MOV preserves FLAGS. The existing
ALU and opcode semantics decoder are shared with sequential execution.

The microsequencer accepts a generic `operation_retire` qualifier alongside
`operation_done`. It still owns retirement and its single-cycle pulse. It does
not decode x86 instructions. Debug micro-PC at early retirement identifies the
new functional control, rather than a separately executed `END`.

Memory ModR/M forms fall through to exactly the original operand acquisition,
protection, writeback and FLAGS sequence. The compiler requires that this
fallback match the optimized direction, width, operands and write disposition;
an inconsistent source is rejected. All entry addresses, labels, branch
targets and the 723-word ROM layout are preserved. The eight replaced words
are checked independently against the frozen format-21 contract.

Only the accepted first ModR/M byte may capture registers. Displacement bytes
cannot trigger the shortcut. Execution pause holds both operands. Reset,
valid redirect and instruction cancellation clear the pending commit;
malformed control prevents progress. No architectural state changes during
capture. Pending events see the completed result and FLAGS at retirement.

## Measured improvement

Both Verilator and Icarus produce the same results. These are physical RTL
clock counts under the specified CPU-only memory models, not calibrated
historical 80286 instruction times.

| Register-direct operation | Previous useful execution clocks | Optimized |
| --- | ---: | ---: |
| ALU, including CMP/TEST, byte or word | 8 | 2 |
| MOV, byte or word | 5 | 2 |

The execution interval starts after opcode dispatch. Real instruction-byte
starvation and paused clocks are excluded from the two useful clocks. The
dedicated lifecycle test checks both this count and exact architectural state.

The stream benchmark executes 64 two-byte instructions and includes fetch,
dispatch and intervening retirement boundaries. It measures from first opcode
dispatch to final retirement, excluding initial reset/setup and the first
opcode fetch. `delayed=1` only asserts external READY every fifth clock.

| Stream | READY | Previous clocks | Optimized clocks | Throughput gain |
| --- | --- | ---: | ---: | ---: |
| ADD registers | Immediate | 638 | 254 | 2.512x |
| MOV registers | Immediate | 446 | 254 | 1.756x |
| Alternating ADD/MOV | Immediate | 542 | 254 | 2.134x |
| ADD registers | Delayed | 638 | 317 | 2.013x |
| MOV registers | Delayed | 446 | 317 | 1.407x |
| Alternating ADD/MOV | Delayed | 542 | 317 | 1.710x |

The optimized immediate-READY stream therefore sustains approximately four
clocks per instruction, including boundaries; it is not a two-clock sustained
throughput claim. The smaller gain with delayed READY exposes the remaining
instruction-fetch bottleneck. These CPU-only streams are not CheckIt and do
not predict the speedup of the MiSTer machine or SDRAM integration.

The existing Phase 9B bank confirms `ADD AX,BX` drops from 8 to 2 clocks while
both measured memory MOVs remain at 9 clocks. At the shorter ADD endpoint the
next code request is active, and no BIU acceptance occurs inside its interval.
The calibration validator admits this observation as well as the preserved
historical idle endpoint. Counter bounds, the BIU partition, exact FLAGS and
all memory-service requirements remain enforced.

## Reproduction

```sh
export SPK286_BUILD_DIR="$PWD/build/register-opt/current"
export SPK286_BUILD_JOBS=4
make microcode-check microcode-test microcode-audit lint
bash scripts/test_units.sh both spk286_register_execution
bash scripts/test_units.sh both spk286_microsequencer
bash scripts/test_units.sh both spk286_timing_calibration
SPK286_BUILD_DIR="$PWD/build/register-opt/throughput" \
  bash scripts/test_register_throughput.sh ec5605b
make regression
python3 -m tools.audit_scalar
```

The expanded affected SingleStep run uses the normal smoke executable and the
pinned `.cache/singlestep-80286` corpus:

```sh
bash scripts/build_verilator.sh
opcodes=(00 01 02 03 08 09 0A 0B 10 11 12 13 18 19 1A 1B
         20 21 22 23 28 29 2A 2B 30 31 32 33 38 39 3A 3B
         84 85 88 89 8A 8B)
args=()
for opcode in "${opcodes[@]}"; do args+=(--opcode "$opcode"); done
python3 -m tools.run_singlestep "${args[@]}" --full --include-prefixes --include-exceptions
```

The comparison script archives the named baseline into an ignored build
directory, copies the same benchmark to it, executes both simulators on each
implementation and requires identical simulator observations and a speedup
for each checked stream. It does not change the active checkout or reference
instruction results. Its receipt is `comparison.json` in the selected output
directory.

Focused validation includes 78 lifecycle cases (3,879 checks per simulator),
the eight schedule controls and compiler rejection cases, and full SingleStep
coverage of the 38 affected ALU/TEST/MOV opcode files. The ordinary admission
policy passes 150,351 cases. The expanded run with `--include-prefixes
--include-exceptions --full` passes all 190,000 cases in those files, with zero
failures, revocations or skips. The full Python run passes 325 tests, including
93 microcode/compiler tests. The complete `bash scripts/test.sh` regression
finishes with `TEST PASS` and exit status 0. This includes all configured RTL
banks, both CPU reset smoke tests, the Python suite, state vectors and the four
SingleStep smoke groups (970 selected cases, zero failures). The existing
expand-down protected-mode matrix runs in Icarus only, as specified by the
suite; the other configured banks retain their normal simulator coverage.

Yosys 0.33 (`2584903a060`) passes both hierarchy/process checks and mapped
synthesis. The mapped report contains no failed checks; its SHA-256 is
`4c1a31da8fefc52195be348631c0520154dcf051b4a3dc77b1eabdb871319b52`.
Local receipts are retained under the ignored `build/register-opt/` directory:
`regression.log`, `synthesis.log`, `python.log`, `scalar-audit.log`,
`singlestep-prefix-exceptions.log`, `throughput/comparison.json`, and the
`current/reports/yosys_*.log` reports. Current calibration CSVs were validated
directly from both simulators; they are working-tree observations, not a clean
revision capture manifest.

The scalar mutation audit passes both pristine banks and rejects eight
functional mutants, including independent undefined-AF corruption of both
execution paths. Compiler and ROM tests now check the format-22 controls;
operand lifecycle tests cover before capture, before atomic commit and after
retirement instead of waiting for removed register writeback/END stages.

The broad Python run also exposed a pre-existing missing-workflow dependency:
`9c269a6` intentionally deleted `.github/workflows/ci.yml`. Its original
three-line status-capture shell contract is now retained in a test fixture and
still executed against a failing validator. A restored live workflow would
also be checked. No workflow is recreated and no failure test is skipped.
The scalar mutation compiler now orders protected-mode packages before their
users, matching the main RTL source manifest.
The byte-operand bench also explicitly ties the four unused LOADALL register
ports inactive; they were previously omitted and stopped strict Verilator
compilation. Missing-pin warnings remain errors.

## Remaining work

Immediate arithmetic/MOV, unary operations, shifts, branches and other
microprograms still use their previous schedules. Dispatch/retirement
boundaries and instruction-fetch throughput remain separate optimization
targets. No downstream sources or RBFs are updated by this increment.

Yosys synthesis sanity establishes synthesizability, not FPGA timing closure.
The new commit path must be placed, routed and checked with the intended FPGA
clock before claiming a board frequency or a CheckIt gain.
