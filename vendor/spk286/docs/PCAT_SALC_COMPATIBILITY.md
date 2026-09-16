# Downstream PCAT compatibility extension: SALC D6

The PCAT integration's AT XUB r631 executes D6 when building the fixed-disk
parameter tables after detection. The former Phase 7 exclusion of undocumented
SALC is historical; this integrated CPU copy now implements it. No 386 behavior
or chipset-specific dispatch has been introduced.

Contract: `AL = CF ? FFh : 00h`; AH, other registers and all FLAGS are preserved.
The four-step `LOAD_CARRY_BYTE` entry captures FLAGS, fills the low byte from
the captured CF, writes AL through the existing register owner, and retires.
It does not decode a BIOS address or add timing padding. Exact historical
cycle timing is not claimed.

The authoritative source is `microcode/source/zzzzzzzzzzzzzzzzzz_salc.mc`.
Format/compiler 21 adds operation 171, `CARRY_FILL8 TMP0`. It appends four
words without relocating any existing entry or branch. Generated files must
continue to be regenerated with `python3 -m tools.microcode.compile_microcode`.

Verification commands (from this CPU directory):

```sh
python3 -m unittest tests.test_microcode_salc -v
bash scripts/test_units.sh both spk286_decoder
bash scripts/test_units.sh both spk286_scalar_direct
bash scripts/lint.sh
bash scripts/build_verilator.sh
python3 -m tools.run_singlestep --repo /path/to/singlestep-80286 --opcode D6 --full --include-prefixes --include-exceptions
```

The complete D6 physical file passes (1,000 cases, zero exclusions). The
direct-scalar test now has 2,272 cases, including carry=0/1, preserved AH and
FLAGS, prefixes and READY stalls. CBW/CWD/LAHF physical families also pass.
The baseline-wide regression still has eight failures that predate this
extension; it is not represented as passing. See the downstream machine
[bring-up record](../../../docs/at-xtide-bringup.md) for reproduction, logs and
the synthetic boot-sector test's boundaries.
