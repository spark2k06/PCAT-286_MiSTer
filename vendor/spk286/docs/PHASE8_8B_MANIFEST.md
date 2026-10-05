# Phase 8B manifest — D8–DF ESC no-coprocessor profile

Date: 2026-09-10

Status: focused validation, commit-isolation review, unchanged-BIOS boundary
smoke and downstream transfer passed; the user-owned Quartus/RBF hardware
checkpoint remains pending.

## Scope and contract

The complete `D8`–`DF` range is accepted by the decoder and dispatched to the
project-owned `ESC_NO_COPROCESSOR` terminal microprogram. Prefixes, ModR/M and
displacement bytes are consumed through the ordinary instruction-stream
service. The selected standalone profile performs no 80287 operation, no ESC
operand memory transaction and no architectural register/FLAGS/segment change;
it retires exactly once and allows the next instruction to execute. This
contract is recorded as D-040 and is not a claim of complete 80287, `WAIT` or
MSW/TS exception support.

## Implementation

- `rtl/spk286_decoder.sv`: recognize all `D8`–`DF` opcodes and select the
  terminal entry.
- `microcode/source/zzzzzzzzzzzzzzzz_esc.mc`: authoritative source containing
  `DECODE_MODRM` followed by `END`.
- Generated package, ROM, listing, symbols, validation and Phase 8 fixture:
  regenerated with the project compiler; no generated file was hand-edited.
- `sim/unit/spk286_esc_instructions_tb.sv`: all eight opcodes, register and
  memory ModR/M forms, displacement widths, segment prefix, READY waits,
  follow-on `MOV`, exact IP and no data operand access.
- `sim/unit/spk286_decoder_tb.sv`: opcode coverage and entry contract.

## Executed evidence

| Check | Result |
| --- | --- |
| `bash scripts/test_units.sh iverilog spk286_esc_instructions` | `ESC_INSTRUCTIONS PASS: 24 cases; 1463 checks` |
| `bash scripts/test_units.sh verilator spk286_esc_instructions` | PASS, `24 cases; 1463 checks`, no warning-as-error diagnostics |
| `bash scripts/test_units.sh iverilog spk286_decoder` | `DECODER PASS: 256 opcode checks` |
| `bash scripts/test_units.sh verilator spk286_decoder` | PASS, `256 opcode checks` |
| `python3 -m unittest discover -s tests -p 'test_microcode*.py' -v` | PASS, `88 tests` |
| `python3 -m tools.microcode.audit_microcode --output build/microcode-audit` | `MICROCODE AUDIT PASS` |
| `python3 -m tools.microcode.compile_microcode --check` | `MICROCODE CHECK PASS: 101 entries, 614 words` |
| `make phase8-audit` | `PHASE8_AUDIT PASS: 2 rejected RTL mutants; 3 pristine controls; production bytes unchanged` |

The 24 directed cases are three forms for each opcode in `D8`–`DF`; `DB` is
therefore covered explicitly as the reported downstream trigger.

## Isolation requirement

The isolated review was completed from the 8B-only snapshot with 8A reverted.
The complementary 8A-only review was also completed. The verified CPU payload
was transferred to `PCAT-286_MiSTer` at commit
`b6c3035e716fcd640523c7189480e59941067472`; see
[the downstream transfer record](PHASE8_DOWNSTREAM_TRANSFER_20260910.md).
The Phase 8 mutation audit was then transferred in follow-up commit
`af74c70108db8ede90a62a4f6bcff6d8da86057d`.
The unchanged `xtsergey_mod.rom` boundary smoke reached the reset vector and
128 accepted beats; this is not a full BIOS boot or a physical-board result.
The existing invalid-instruction policy remains unchanged outside the admitted
ESC range.
