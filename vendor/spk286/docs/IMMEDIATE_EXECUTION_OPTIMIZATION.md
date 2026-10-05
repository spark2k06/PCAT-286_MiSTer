# Immediate execution optimization — 2026-09-22

This CPU-only increment builds on `bab0f67d44c4afda414d583a6948df213453e452`.
It optimizes ALU/TEST and MOV immediate forms with register destinations.
Physical bus timing, historical timing policy and the PCAT project are unchanged.

Architectural compatibility and historical timing are distinct validation
targets. The affected SingleStepTests corpus was captured on a physical Harris
80C286 ([corpus provenance](https://github.com/SingleStepTests/80286#about-the-tests));
this run compares architectural state, not the captured cycle traces. Removing
internal serialization changes instruction duration and may change prefetch
overlap even though the BIU's per-transfer protocol is unchanged. Matching an
86Box or CheckIt aggregate score would not establish cycle accuracy. This
increment does not close the inherited compatibility/evidence items or certify
an Accurate timing mode.

## Implementation and boundaries

Nine format-23 controls fetch the constant and capture the original register
on the last accepted byte. The following enabled clock uses the existing
register execution stage to write the result and masked FLAGS and retire
atomically. The operand values use existing temporaries; no separate ALU or
wide immediate datapath register is added. CMP/TEST do not write a register;
MOV preserves FLAGS. ADC/SBB retain the existing carry/borrow and flag logic.
Byte destinations include the high-byte register aliases. Signed `83h` constants
are extended before arithmetic.

ModR/M forms still decode their full addressing context first. Memory forms
fall through from the new fetch control exactly as the old fetch did, using
the same temporary, protection checks, memory requests and sequential tail.
The compiler rejects inconsistent width, destination, commit order, duplicate
controls or incomplete fallback. The ROM changes exactly nine controls, with
all 122 entries, labels, branches and 723-word layout unchanged. Frozen earlier
fixtures remain executable; the new contract is derived from their words and
literal replacement values, rather than from the newly emitted image.

READY and instruction-byte availability remain real waits. A pending register
commit stops byte consumption, so it cannot eat the next opcode. Pause holds
the partial immediate or pending commit. Reset, valid redirect and cancellation
clear it. Malformed control prevents execution, and a pending NMI sees the
completed result/FLAGS/IP at the retirement boundary.

## Measured complete-stream comparison

Both simulators run the same 64-instruction streams on the baseline and
candidate. Counts start at first opcode dispatch and end at last retirement;
they include subsequent fetch, dispatch and retirement boundaries. Delayed
READY is asserted every fifth clock. These are implementation clocks, not
historical 80286 cycles or predicted CheckIt scores.

| Instruction stream | Immediate READY: old → new | Throughput gain | Delayed READY: old → new |
| --- | ---: | ---: | ---: |
| ADD AX, imm16 (`05h`) | 574 → 319 | +79.9% | 576 → 477 |
| ADD AX, sign-extended imm8 (`83h`) | 638 → 382 | +67.0% | 640 → 478 |
| MOV DX, imm16 (`BAh`) | 383 → 319 | +20.1% | 478 → 477 |
| ADD AL, imm8 (`04h`) | 510 → 254 | +100.8% | 510 → 317 |
| MOV AH, imm8 (`B4h`) | 318 → 254 | +25.2% | 318 → 317 |
| ADD AX, imm16 (`81h`) | 702 → 446 | +57.4% | 704 → 637 |
| MOV BH, imm8 (`C6h`) | 446 → 382 | +16.8% | 479 → 478 |
| MOV BX, imm16 (`C7h`) | 510 → 446 | +14.3% | 638 → 637 |

All 16 register streams improve. The ten matching memory streams retain
identical elapsed clocks, fetches, queue-empty observations and operand read/
write counts. Every stream also checks exact GPR/FLAGS/IP and memory results.
The comparison receipt is [immediate_execution_comparison.json](immediate_execution_comparison.json).
The near-zero MOV gain with delayed READY demonstrates the remaining instruction
supply limit; the register-only gain is not a whole-machine speedup estimate.

The focused lifecycle bank measures useful execution clocks after dispatch:
two for byte accumulator/MOV immediates, three for word accumulator/MOV
immediates, four for byte or sign-extended ModR/M register forms and five for
word ModR/M register forms. Actual byte starvation and pause are excluded from
those counts and tested separately. Sustained stream intervals are longer.

### Physical-machine observation, not a timing acceptance target

During validation the user supplied CheckIt photographs from a friend's real
286, selectable between 6 and 12 MHz, alongside 86Box 5.3 build 8200:

| Source | CheckIt frequency estimate | Dhrystones | Whetstones |
| --- | ---: | ---: | ---: |
| Physical 286 | 12.01 MHz | 2,181 | 45.2K |
| 86Box, two memory waits reported by the user | 12.50 MHz | 2,072 | 35.4K |
| 86Box, zero memory waits reported by the user | 6.01 MHz | 1,493 | 29.5K |

The first emulator comparison is 5.0% lower in Dhrystones and 21.7% lower in
Whetstones despite the higher displayed frequency. Both supplied photographs
of the real machine show its 12.01 MHz result; the user reports a closer match
at 6 MHz with zero emulator waits, but the physical 6 MHz scores and motherboard
identity have not yet been supplied. Do not infer the real board's wait count
from these aggregate scores. These observations are independent of the new
RTL stream measurements above, and no delay or opcode behavior was adjusted
to fit them.

## Validation

The subsequent PCAT import was tested by the user at the same physical 50 MHz
clock without DEBUG. CheckIt remained at 3,400 Dhrystones and changed from
67.1K to 69.8K Whetstones (+4.0%). This is one reported hardware comparison,
not a whole-machine speedup guarantee or historical timing acceptance. The
PCAT repository records its build, import, timing and hardware-test receipt
in `docs/optimization/IMMEDIATE_EXECUTION_50MHZ.md`.

- All 95 compiler tests and 328 Python tests pass, along with generated
  consistency, the independent ROM/round-trip audit and strict Verilator lint.
- The new lifecycle bank passes 184 cases / 9,952 checks in each simulator,
  including high bytes, signed constants, ADC/SBB, CMP/TEST, preserved FLAGS,
  pause, malformed control, cancellation/reset and pending NMI frames. Forty
  cases specifically pause/cancel/reset between the two immediate bytes,
  including ModR/M forms, and check replacement instructions for stale bytes.
- Existing MOV and ALU lifecycle banks retain cancellation before the first
  byte, between immediate bytes and before atomic commit. Removed separate
  write/FLAGS/END stages are replaced by this atomic boundary; architectural
  expected values and protection checks are unchanged. Immediate starvation
  observers include the new controls.
- The 10,240-vector ALU bank and prior register execution bank pass both
  simulators. The 26 stream profiles agree between simulators and with their
  independent architectural expectations.
- Full SingleStep coverage of 62 affected opcode files passes 309,998 cases
  with prefixes and exceptions included. The corpus's two existing C6/C7
  revocations remain in force; there are no executable failures or other skips.
- The scalar audit passes both pristine banks and rejects all eight functional
  mutants, including incorrect undefined-AF writes through either execution path.
- The I/O audit passes all three pristine banks and rejects all 19 functional
  mutants, including premature completion of port transfers. Its completion
  mutation anchor follows the extended assignment, and its compilation puts
  both RTL packages before their users, as the standard build already does.
  Neither compile failures nor unrelated assertion failures count as rejection.
- Baseline Phase 9B calibration passes in both simulators and the live CSV
  passes its validator. The shorter second MOV may end with a code request
  active; historical captures and all prior counter/state checks remain valid.
- Yosys hierarchy/process and mapped synthesis checks pass. This establishes
  synthesizability, not FPGA timing closure. The Yosys 0.33 mapped report SHA-256
  is `6871a323969673c056341b4aea98af0d09199044f78d49c54ade92320f10b89f`.
- The complete `bash scripts/test.sh` regression finishes with `TEST PASS` and
  exit status 0. This includes every configured RTL bank, CPU reset smoke in
  both simulators, all 328 Python tests, state vectors and the four SingleStep
  smoke groups (970 selected cases, zero failures). The inherited expand-down
  protected-mode matrix runs in Icarus only, as the suite specifies; the other
  banks retain their normal simulator coverage. The new 184-case bank and all
  26 throughput profiles pass again within the complete regression.
- Both mutation audits' production-source SHA-256 manifests match the final
  RTL and generated image. No production RTL was changed during the complete
  regression.

## Reproduction and scope

```sh
export SPK286_BUILD_DIR="$PWD/build/immediate-opt/current"
export SPK286_BUILD_JOBS=4
make microcode-check microcode-test microcode-audit lint
bash scripts/test_units.sh both spk286_immediate_execution
SPK286_BUILD_DIR="$PWD/build/immediate-opt/throughput" \
  bash scripts/test_immediate_throughput.sh bab0f67
bash scripts/test.sh
bash scripts/synth_check.sh
python3 -m tools.audit_scalar --build-dir "$SPK286_BUILD_DIR"
python3 -m tools.audit_io --build-dir "$SPK286_BUILD_DIR"
```

For full SingleStep, build `scripts/build_verilator.sh` once and pass `--full
--include-prefixes --include-exceptions`, selecting `04/05`, `0C/0D`, `14/15`,
`1C/1D`, `24/25`, `2C/2D`, `34/35`, `3C/3D`, `A8/A9`, `B0..BF`, `C6/C7`,
`80.0..80.7`, `81.0..81.7`, `83.0..83.7`, `F6.0` and `F7.0` through repeated
`--opcode` arguments. The corpus's other opcode aliases are outside the existing
runner's admitted instruction set; this increment does not add new encodings.

Local receipts are under ignored `build/immediate-opt/`: `compiler.log`,
`lint.log`, `singlestep-full.log`, `singlestep-test-full.log`, `synthesis.log`,
`scalar-audit.log`, `io-audit.log`, focused unit logs, `regression.log` and
`throughput/comparison.json`. Production source hashes are also recorded by the
mutation audit. This standalone increment contains no PCAT source or clock
constraint changes; downstream integration is recorded separately.
