# Historical microcode regression adapters repaired

## Scope and baseline

The unmodified `make regression` on the READY-chaining candidate stopped at
the Python microcode suite: **114 tests, three failures and five errors**.
These failures already existed at `1a4f2ec` and were recorded in
[the previous regression](P18_P19_FULL_REGRESSION_20261002.md). Microcode,
compiler and test inputs had no differences from that commit before this
repair. The failed run remains evidence; it is not reported as passing.

This repair changes six Python test adapters and one compiler validation
guard. It changes no architectural RTL, `.mc` source, generated ROM, encoding
allocation or historical JSON fixture. The broad RTL regression runs separately
against frozen source copies; its results are recorded in
[the fetch correction report](P06_READY_CHAIN_CORRECTION_20261004.md).

## Explicit historical catalog migration

The phase-9/register/immediate fixtures preserve the older PCAT allocation
`CARRY_FILL8=171`, `LOADALL=172`. The accepted standalone compiler and independent
audit use `LOADALL=171`, `CARRY_FILL8=172`. The compatibility helper asserts both
old protocols, `[172, 3]` and `[30, 171, 54, 3]`, and the exact two affected
positions before translating them. Every other word, entry, label and branch
remains independent frozen evidence; expectations are not generated from the
candidate compiler.

| Test adapter | Repair |
| --- | --- |
| `test_microcode_loadall.py` | Use the accepted `zzzzzzzzzzzzzzzzzzzz_loadall.mc` source name and literal `[171, 3]`; retain atomic sequencing, all rejection cases and complete-image roundtrip. |
| `test_microcode_salc.py` | Use `zzzzzzzzzzzzzzzzzzzzz_salc.mc` and literal `[30, 172, 54, 3]`; retain append-only checks and FLAGS-preserving protocol rejection cases. |
| `test_microcode_register_execution.py` | Retain all frozen register-control deltas; explicitly translate only the two historical catalog positions before current decoding. Hosts the shared compatibility helper. |
| `test_microcode_immediate_execution.py` | Retain all nine frozen immediate-control deltas and translate the same two historical positions. |
| `test_microcode_system_access.py` | Derive the eight H01 checks after the explicit catalog translation; also compare the complete independently shifted label and branch maps. The format-24 fixture already uses the standalone catalog. |
| `test_microcode_io.py` | Recover the intended pre-SALC 719-word image from the frozen 723-word phase-9 fixture by asserting/removing only its four-word SALC suffix and entry at 719. Retain literal branches, complete words and roundtrip/emit checks. No missing `*_sources.json` is invented. |

## Restored negative exposed a compiler defect

The old LOADALL test already required deleting the LOADALL token to fail, but
its obsolete filename prevented execution of that check. After restoring the
adapter, `instruction LOADALL: END` was incorrectly accepted: validation was
selected only when the token was present. The guard now checks
`entry == 'LOADALL' or 'LOADALL' in names`. The exact atomic validator is unchanged;
the existing negative is retained and passes. This affects source validation,
not the accepted generated image.

## Validation and evidence

- **114/114 Python microcode tests pass.**
- All **155 existing negative rejections** in the six adapters pass: immediate
  70, IO 60, LOADALL 5, register 9, SALC 7, H01 4; no rejection is removed or skipped.
- `compile_microcode --check` and the existing `emit(..., check=True)` tests pass:
  **123 entries, 743 words, 10-bit addresses, 8-bit controls**.
- Historical fixture and microcode source/generated hashes match the failed
  baseline byte for byte. No ROM regeneration was performed.

[The evidence receipt](../evidence/spk286-microcode-repair-20261004/receipt.json)
binds before/after source, all baseline fixture/microcode hashes, the exact
diff, original failure, exposed LOADALL negative, final test/check logs and
the instrumented preserved-negative count. It does not substitute for the
separate broad RTL regression or historical timing/hardware validation.
