# SALC compatibility

This core implements the undocumented 80286 `SALC` instruction (`D6h`) for
real-mode software such as AT XTIDE Universal BIOS.

The architectural contract is `AL = CF ? FFh : 00h`; `AH`, the other
registers, and all FLAGS are preserved. The decoder dispatches `D6h` to the
append-only `LOAD_CARRY_BYTE` microcode entry. Its `CARRY_FILL8` operation is
encoded as operation 172, after the existing `LOADALL` operation 171, so this
extension does not relocate the existing microcode entries.

The authoritative source is
`microcode/source/zzzzzzzzzzzzzzzzzzzzz_salc.mc`; generated files must be
regenerated with:

```sh
python3 -m tools.microcode.compile_microcode
```

Verification includes the dedicated microcode round-trip test, decoder tests,
and direct scalar vectors covering both carry states, preserved `AH`/FLAGS,
prefixes, and READY stalls.
