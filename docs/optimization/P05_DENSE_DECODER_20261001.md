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

## Isolated fresh fit

The compiled input manifests differ from the preceding predicate fit in the
decoder RTL only. This is a fitted A/B checkpoint, with the same real 20 ns
clock and corrected SDRAM input/output budget.

| Corner | Global setup | CPU setup | Global hold | SDRAM output setup |
| --- | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -2.484 | -2.484 | -3.086 | +3.898 |
| 7_slow_1100mv_-40c | -2.169 | -2.169 | -3.071 | +4.585 |
| MIN_fast_1100mv_100c | +1.993 | +7.741 | -2.515 | +9.040 |
| MIN_fast_1100mv_-40c | +2.335 | +9.686 | -2.590 | +10.555 |

The slow setup improves from -4.341/-3.878 ns to -2.484/-2.169 ns.
The worst CPU paths now originate in SP/allocation arithmetic and travel
through the outer-return range predicate and ordinary operand completion.
The code-buffer setup is positive (+0.118/+0.105 ns), but has little margin.
The direct forwarded-clock SDRAM hold failure remains. No 50 MHz closure
or hardware validation is claimed. All eight CheckIT physical-owner fixtures
retain exactly the preceding owner-entry cycle/stall/signature counters; see
the predicate evidence cycle receipt.
