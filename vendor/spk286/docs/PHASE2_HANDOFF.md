# SPK286 Phase 2 Handoff

Date: 2026-09-05
Branch: `codex/phase2-prefetch-execution`
Base commit: `5fb70f1` (`codex/phase1-architectural-state`)
Implementation commit: `b7023c7` (`Add six-byte prefetch and MOV execution path`)
Final documentation commit: this handoff commit

## Outcome and scope

Phase 2 adds the first real instruction execution path while preserving the
verified Phase 1 architectural state and fetch service. SPK286 now consumes a
stream from synthetic memory, buffers it in a six-byte instruction queue,
decodes `MOV r16, imm16` (`B8..BF`), assembles a little-endian immediate and
writes the selected 16-bit GPR.

The end-to-end directed test executes all eight register encodings and checks
the final architectural state. It also exercises READY stalls, queue flush on
redirect, stale-stream rejection and an unsupported opcode. FLAGS remain
unchanged by MOV.

## Architecture added

### Prefetch queue

`rtl/spk286_prefetch_queue.sv` is a six-byte FIFO with explicit six-entry
storage, modulo-six head/tail pointers and a four-bit count. Fetch response
bytes enter in instruction-stream order: for a two-byte response the low byte
of `fill_data` is inserted first, followed by the high byte. The queue supports
simultaneous consume/refill and updates its count by `fill_count - 1` in that
case.

`spk286_fetch` remains responsible for physical address generation, odd/even
lane selection, one outstanding READY-gated bus transaction, response holding
and obsolete-response cancellation. The integrated prefetch controller only
requests refill while at least two queue slots are free. This deliberately
keeps the current one-response fetch service lossless; it is functionally
correct stream behavior, not a claim of exact historical refill timing.

On reset the queue is empty. On `redirect`, the queue and frontend are flushed
and the existing fetch service drains any obsolete outstanding transaction
before issuing the new stream. No stale response can enter the new stream.

### Instruction frontend

The frontend is the smallest hardwired control path needed for this milestone:

```text
FRONTEND_OPCODE
    -> FRONTEND_IMMEDIATE_LOW
    -> FRONTEND_IMMEDIATE_HIGH
    -> FRONTEND_OPCODE
```

The opcode low three bits select the existing x86 register encoding:

```text
0 AX   1 CX   2 DX   3 BX   4 SP   5 BP   6 SI   7 DI
```

Each consumed opcode/immediate byte advances architectural IP by one. The
fetch cursor is independent and can run ahead while the queue is filled. On
the high immediate byte, the writeback value is `{immediate_high,
immediate_low}` and the normal GPR commit port is used. No FLAGS write is
generated.

`execute_enable` selects autonomous execution. With it low, the Phase 1
datapath commit ports remain available for state-vector setup and the original
fetch tests. `unsupported_opcode` is a development-only latched indication;
the opcode remains in the queue and no architectural exception is claimed.

The frontend is intentionally not generated microcode. It preserves the future
decoder/microcode boundary but avoids freezing a microinstruction encoding for
the three-state MOV path. This follows the deferred decisions in
`SPK286_MICROCODE_FORMAT.md`.

## Important interfaces

- `execute_enable`: enables internal instruction consumption and writeback.
- `fetch_valid`, `fetch_data`, `fetch_ip`, `fetch_count`: existing fetch
  response observation remains available.
- `debug_ip`: architectural next instruction byte.
- `debug_fetch_cursor`: next code byte requested by the bus fetch service.
- `debug_prefetch_count`: current number of buffered instruction bytes, 0..6.
- `unsupported_opcode` and `debug_opcode`: development trap observability.
- Existing GPR, FLAGS, segment, redirect and native bus interfaces are retained.

## State-machine and stream decisions

1. IP is architectural progress. Prefetch activity never advances IP.
2. The fetch cursor is bus progress and is allowed to lead IP.
3. Queue order is FIFO byte order, independent of READY stall duration.
4. Refill is accepted only when the response fits; the integrated controller
   keeps two free slots so the current word response is never split.
5. Redirect has priority over queue fill and frontend progress. The queue is
   invalidated even if old bytes were already buffered.
6. Unsupported opcodes stop the development execution path without silently
   executing a different instruction or modifying GPR/FLAGS state.
7. The frontend boundary is hardwired for this milestone; later decoder and
   microcode work must keep queue storage ownership in the instruction/BIU
   layer.

## Tests and exact results

The final clean build used:

```text
SPK286_BUILD_DIR=/mnt/d/GitHub/SPK286/build/phase2-final make regression
```

Results:

| Check | Result |
| --- | --- |
| Verilator `--Wall` lint | PASS; no relevant warnings |
| `spk286_registers_tb` | PASS in Verilator and Icarus; 200 checks |
| `spk286_segments_tb` | PASS in Verilator and Icarus; 262,202 checks |
| `spk286_fetch_tb` | PASS in Verilator and Icarus; 26 checks |
| `spk286_core_tb` | PASS in Verilator and Icarus; 7 bus checks plus state/redirect cases |
| `spk286_prefetch_queue_tb` | PASS in Verilator and Icarus; 19 queue checks |
| `spk286_execution_tb` | PASS in Verilator and Icarus; 8 MOVs, stalls, redirect/flush and unsupported opcode; 16 bus transactions |
| Original reset smoke | PASS in Verilator and Icarus; first fetch `0xFFFFF0` |
| Python unit tests | PASS; 8 tests |
| State vectors | PASS; 1 checked-in + 3 directed initialization/fetch cases, `instructions_executed=0` for this legacy adapter |
| Yosys integrated hierarchy | PASS; `check -assert`, 0 structural problems |
| Yosys prefetch queue hierarchy | PASS; `check -assert`, 0 structural problems |
| Negative failure path | PASS; both simulators reject the intentionally wrong fetch address |
| Verilator waveform smoke | PASS; `build/phase2-final/traces/reset_verilator.vcd` generated |
| Complete regression | PASS; exit status 0 |

The project does not yet define a separate coverage target; no coverage result
is claimed beyond the directed tests listed above. Quartus and MiSTer were not
run because they are outside the normal Phase 2 loop.

## Known limitations

- Only `MOV r16, imm16` (`B8..BF`) executes. No NOP, ModR/M, memory operands,
  ALU operation, branch, HLT, exception delivery or microcode engine exists.
- Unsupported opcode behavior is a development trap, not 80286 invalid-opcode
  architectural exception behavior.
- The bus service still permits one outstanding fetch and one response slot;
  exact native Ts/Tc/Ti timing and full BIU arbitration are deferred.
- The current refill policy is intentionally conservative and preserves all
  bytes; it does not claim exact historical prefetch overlap timing.
- The legacy state-vector adapter still validates initialization and first
  fetch only. The new execution test is a directed synthetic-memory test, not
  a SingleStep instruction adapter.
- No external SingleStep 80286 corpus is configured in this checkout.

## Recommended Phase 3 Starting Point

### Objective

Add the first operand path: ModR/M decoding, effective-address generation and
register/memory operand handling. Start with register-direct forms so the
decoder contract is proven without a data bus, then add real-mode memory reads
and writes through a separate data transaction path.

### Dependencies

- Preserve the six-byte queue and byte-consumption/IP contract.
- Add decoder state for ModR/M, displacement and resolved `REG`/`RM` metadata.
- Add a reusable 16-bit effective-address unit with default segment selection
  and later segment-override input.
- Add a BIU data request/response interface; `spk286_fetch` currently models
  code reads only.
- Extend the writeback path without changing MOV's explicit FLAGS-none policy.

### Expected interfaces

- Queue consumer byte `valid/data/ready` into the decoder.
- Decoder output: instruction form, direction/width, `mod`, `reg`, `r/m`,
  displacement metadata and segment selection.
- Effective-address output: logical segment plus 16-bit offset and validity.
- BIU data request: valid, read/write, width, physical address and write data;
  response: valid, read data and completion, with READY retained in the BIU.
- Execution/writeback request: destination selector, result and explicit FLAGS
  policy.

### Required tests

- All register-direct ModR/M encodings and register preservation.
- Every 16-bit addressing combination, displacement width and BP/SS default.
- Memory read/write byte lanes, READY stalls and bus backpressure.
- Queue refill while ModR/M/displacement bytes are consumed.
- Redirect/flush must not allow old ModR/M or displacement bytes to execute.
- Verilator and Icarus cross-checks, Yosys structural checks and full Phase 2
  regression.

### Relevant references

- `SPK286_SPEC.md`, sections 12, 14, 15, 18–23 and 38.
- `SPK286_REALMODE_MVP.md`, sections 10–16 and RM1 in section 39.
- `SPK286_MICROCODE_FORMAT.md`, sections 12–18 and 34–37.
- Intel 80286 Hardware Reference Manual, chapter 3 (six-byte prefetch and bus
  behavior) and the Intel 80286/80287 Programmer's Reference Manual opcode
  tables.

### Definition of Done

- Decoder and effective-address unit are synthesizable, lint-clean and
  independently tested.
- Register-direct and memory operand MOV vectors pass in both simulators with
  READY stalls.
- Architectural state, FLAGS preservation and IP progression are checked
  end-to-end.
- Queue flush, stale read/displacement rejection and data bus lanes are tested.
- Yosys reports 0 structural problems and the complete Phase 2 regression stays
  green.
- New architecture decisions and unsupported behavior are documented before
  committing.
