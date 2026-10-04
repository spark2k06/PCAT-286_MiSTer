# Read review and directed starvation preflight

## Why this review was bounded to these banks

`build/p06-ready-chain-regression-20261004-v2/regression.log:10752` records
the completed 8,184-case ADJUST instruction matrix stopping only at its final
`immediate_stalls > 0` coverage assertion. The last reported architectural
FLAGS already equal the expected value. The failure is not an accepted excuse
to remove the coverage assertion or weaken any architectural oracle.

`vendor/spk286/Makefile:94` invokes `scripts/test.sh`; `scripts/test.sh:11`
invokes `scripts/test_units.sh`. The explicit unit order in that runner leaves
52 banks after ADJUST instructions. This review inspected those subsequent
banks for starvation/READY coverage and exercised the three instruction
matrices with the same cumulative `immediate_stalls > 0` requirement.

The complete native snapshot contains 581 vendor files. Original test banks,
vector generators, CPU RTL and generated ROM are frozen byte-for-byte. The
previously authorized ADJUST stimulus fix is included in the snapshot but
does not modify any of the three preflight banks. No new test, oracle, expected
result, opcode exemption or production RTL change was introduced here.

## Three full matrices: both simulators pass without changes

| Bank | Cases | Checks per simulator | Immediate stalls per simulator |
| --- | ---: | ---: | ---: |
| STACK_FRAME_INSTRUCTIONS | 10,256 | 5,144,999 | 2,120 |
| FAR_INSTRUCTIONS | 6,760 | 634,450 | 216 |
| MULDIV_INSTRUCTIONS | 19,556 | 2,389,287 | 642 |

All six commands exit zero. Icarus and Verilator report exactly the same
case/check/stall counts. Both independently regenerate the original vectors.
The complete preflight runs from 2026-10-04 18:22:15 to 18:25:55 UTC (3:40).
Logs and the original 581 source files remain intact in this build directory.

Relevant source locations:

- Stack/frame counts immediate starvation at `spk286_stack_frame_instructions_tb.sv:38`,
  drives READY at line 67 and asserts positive coverage at line 129.
  `tools/stack_frame_vectors.py:69` supplies the original `seed % 3` waits.
- Far counts at `spk286_far_instructions_tb.sv:39`, drives READY at line 68
  and asserts positive coverage at line 136. `FarCase` inherits the same frame
  row/wait generator; the matrix includes immediate far targets and returns.
- Mul/div counts at `spk286_muldiv_instructions_tb.sv:38`, drives READY at
  line 73 and asserts positive coverage at line 144. Its generator reuses
  `tools/test_instruction_vectors.py:72` (`seed % 4` waits), including the
  immediate IMUL variants.

These banks retain real starvation even with the earlier fetch offer; no
additional delay is justified by the observed evidence.

## Other subsequent coverage inspected, without new test execution

- `spk286_string_instructions_tb.sv:40/:137` and
  `spk286_string_io_tb.sv:44/:141` require positive READY stalls while a string
  operand or I/O transfer is pending. Their service tasks (lines 67/71)
  enforce the vector waits on actual bus transfers; their coverage is not
  merely lack of an immediate CODE byte. Those explicit data/I/O waits are
  retained by the fetch change. Full broad execution still validates them.
- `spk286_xchg_hold_lock_tb.sv:50` explicitly holds the first WRITE for two
  services. Its line 129 check requires the locked collision and exact two
  data reads/writes. This WRITE/HOLD/LOCK stimulus is independent of CODE
  turnaround.
- Lifecycle banks pause at observed microcode/operand boundaries and explicitly
  withdraw READY/execution. They do not assert an incidental cumulative
  immediate-starvation count; their stage/architectural assertions remain.
- `spk286_register_execution_tb.sv:147` and
  `spk286_immediate_execution_tb.sv:249` subtract observed byte stalls from
  useful execution clocks. They do not require a positive number of stalls.
  Immediate partial-byte coverage at line 273 waits for `high_byte_q`, the
  retained serial acquisition state, rather than an assumed missing second
  byte. No expectation adjustment is proposed.
- `spk286_immediate_throughput_tb.sv:93` reports elapsed clocks and queue-empty
  counts; its oracle checks results and bus traffic, not a fixed elapsed
  cycle count or required queue starvation.

The positive starvation counts are aggregate matrix coverage, not a claim that
every individual form starves. This is an existing scope limit of those tests.

## Conditional stimulus proposal, not applied

If a future optimization removes incidental CODE starvation in a bank whose
coverage requires it, use bounded READY backpressure based solely on CODE
status `4'hD`. A conservative +16 clocks, consistent with the separate ADJUST
repair, can be limited to existing nonzero-wait cases to retain zero-wait
cases. Keep data/I/O delays, fixture bytes, architectural oracles and coverage
assertions unchanged. The smallest sufficient delay has not been measured.
The three banks above need no such change.

## Receipt and raw files

`receipt.json` records each independent command, status, elapsed time, raw log
SHA256 and all 581 source hashes. `manifest.json` records snapshot HEAD and
source identity. `evidence-manifest.json` binds the reader/runner metadata,
six raw logs and six generated vector files for the regression supplement.
No compiler objects are required to understand this coverage result.
