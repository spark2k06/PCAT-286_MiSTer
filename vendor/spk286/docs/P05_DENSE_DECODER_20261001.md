# P05: dense opcode support map

Date: 2026-10-01. The fitted CPU critical path starts at the prefetch queue
and crosses the decoder's support decision before dispatch and memory/fault
qualification. This decision previously merged all implemented instruction
families, although the normal opcode map is almost full.

The new expression recognizes its exact complement:

```text
0F, 26, 2E, 36, 3E, 64, 65, 66, 67, 82, F0, F1, F2, F3
```

This list describes the existing decoder output, not architectural validity.
Some bytes are prefixes handled by instruction context. The normal map still
supports 242 bytes; the extended map still supports 00, 01, 02, 03, 05 and 06.
No instruction, invalid-opcode classification, entry address, source index,
destination index, register or cycle is added or changed.

`prove_decoder_support.py` proves equality of the actual old and new support
expressions over all 512 opcode/map pairs with Yosys SAT. A guard checks all
other decoder metadata is unchanged; only three unused support-only helper
signals are removed. A mutant accepting 82 is rejected.

`test_decoder_support.sh` performs strict whole-CPU `-Wall` lint with the base
and PCAT production options. It also compares the complete old/new decoder
metadata, including invalid-opcode classification and microcode entry, in
both Icarus and Verilator. Both pass 512 checks with the 242/6 census intact.
PCAT's actual vendor decoder is then checked by strict lint and call-gate and
CPU-double-fault execution banks in both simulators under production options.

The source and validation receipts are in
`docs/evidence/dense-decoder-20261001/`. The downstream fit
`build/dense-decoder-sdram-budget-fit-20261001` differs from the preceding
predicate/SDRAM-budget fit by this decoder RTL only. Its timing results are
recorded separately when complete. No full regression or MiSTer run is
claimed, and two-state equivalence does not claim arbitrary X equivalence.
