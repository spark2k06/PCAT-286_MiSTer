# Scaler horizontal accumulator reorder — 2026-10-05

## Applied change

The cold setup report from `p06-null-segment-allfeatures-20261005-v1` identified
`o_hsize[4] → o_hacc_next[13]` at **−0.197 ns**. Its data path crossed two
successive arithmetic carry chains (`Add91`, then `Add93`) and the result
selector. The earlier OSWEEP terminal comparison change had already removed
the previous terminal path.

One assignment in `sys/ascal.vhd` now computes the positive-branch accumulator
from the original accumulator and both sizes:

```vhdl
-- Previous:
o_hacc_next<=(dif_v + 2*o_ihsize + (4*OHRESH)) MOD (4*OHRESH);
-- Applied:
o_hacc_next<=(o_hacc_next + 2*o_ihsize - 2*o_hsize + (8*OHRESH)) MOD (4*OHRESH);
```

The difference variable, branch predicate, `o_hacc`, carry decision, negative
branch, surrounding control priorities and all state remain identical. No
register, cycle, clock, PLL, timing constraint or CPU speed-profile change was
added.

Reference SHA256: `412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186`.
Applied SHA256: `8a8382913f007cf7405aad235d6df9558ec14fc493251e31783ddb00031fd687`.
The full source reverses byte-exactly by undoing only that assignment.

## Arithmetic and proof scope

Let `M = 4*OHRESH`, `a = o_hacc_next`, `h = o_hsize`, `i = o_ihsize` and
`D = (a − 2h + 2M) mod 2M`. The previous positive result
`(D + 2i + M) mod M` equals `(a + 2i − 2h + 2M) mod M` for every input.
The original decision `D >= M` and its negative result `a + 2i` are unchanged.

The helper extracts the actual complete horizontal arithmetic block and proves
`dif_v`, `o_hacc`, `o_hacc_next` and `hcarry_v` together. It covers all binary
inputs at their source-declared widths for all possible `OHRESH` values
**1024, 2048 and 4096**, without assumptions or reachable-state restrictions.
The source types, resolution-mapping function and complete block are guarded
exactly. Both full source variants are pinned.

Proof outputs preserve the complete integer results. For arbitrary states at
the smaller resolutions, the unchanged negative branch can exceed the
original accumulator subtype; these values are compared without truncation,
without assuming those states cannot occur. For `OHRESH=4096`, all selected
results fit the actual subtype. The smallest subtraction numerator is 2;
integer-base subtraction and the final modulo cannot overflow.

This proves the arithmetic cone. It is not a whole-scaler transition proof,
a full PCAT regression or a hardware timing result.

## Installed checks

The installed source passed:

- Three GHDL-generated Verilog SAT equivalence miters, one per resolution.
- Nine genuine SAT counterexamples for wrong coefficient, off-by-one and
  branch-boundary mutants.
- **135,168** native VHDL boundary and deterministic random cases.
- Full old/new VHDL analysis with standards 93 and 08. The ten existing
  `Whide` diagnostics are identical; there are no new diagnostics.
- The existing complete OSWEEP transition proof, with arbitrary seeded state
  and context, plus **16,777,216** terminal predicate pairs and
  **10,000** native transition cases / **40,000** edges. Its unchanged wrong
  predicate control still fails natively and formally.

The terminal helper retains the original historical source pin
`966157e71f22a94123597188cbba91e28943c71368670d0a13a5bd8b0baf61e4`.
It reverses only the independently proved HACC assignment for that historical
file guard, while analyzing and proving the actual current full files and
OSWEEP processes. The installed HACC variant requires an explicit PASS receipt
whose helper, full sources, all proof artifacts and results are verified.
Unknown source changes are rejected.

Run from WSL with the existing local GHDL image and Yosys:

```sh
python3 -B scripts/test_ascal_hacc_equivalence.py --output build/<fresh-hacc>
python3 -B scripts/test_ascal_terminal_equivalence.py --output build/<fresh-terminal> --hacc-proof-receipt build/<fresh-hacc>/receipt.json
```

Both output directories must be fresh. No tool download is needed. The GHDL
image is pinned to the reviewed local image identity.

## Cost and remaining measurement

Generic ABC mapping of the actual `OHRESH=4096` arithmetic cone gives:

| Metric | Reference | Applied |
| --- | ---: | ---: |
| Generic logic gates | 215 | 307 |
| `o_hsize → next` logic depth | 29 | 17 |
| `o_hacc_next → next` logic depth | 29 | 20 |
| `o_ihsize → next` logic depth | 13 | 20 |
| Added registers / cycles | 0 / 0 | 0 / 0 |

The **+92 generic gates** are accepted for a measured fit because the rewritten
path is the current scaler bottleneck. These are not Cyclone V ALM counts or
physical delay measurements. The input-size path becomes deeper, so the next
Quartus fit must check all paths, corners, setup, hold and actual resources.
No timing-closure claim is made here.

Explicit wide/low common sums mapped identically to the selected rewrite;
an experimental carry-save form required 340 generic gates. These screens
were not applied and do not claim functional proof PASS. The simplest,
independently proved one-assignment rewrite was selected.

## Evidence and cleanup

[Evidence manifest](evidence/p06-scaler-hacc-reorder-20261005/manifest.json)
and [sealed archive](evidence/p06-scaler-hacc-reorder-20261005/p06-scaler-hacc-reorder-20261005.tar.gz)
contain exact proof sources, installed receipts, native/formal/full-file logs,
generic mapping, independent review bindings and rejected private screens.
All original receipt artifacts were verified before sealing; every archive
member was read back and hashed. Installed HACC and terminal runs retain their
complete artifact sets. Duplicate private compiler outputs are explicitly
omitted with their hashes recorded.

Earlier wrapper subtype errors and the initial CRLF-normalizing patch attempt
are recorded as failures with no PASS claim. The exact reviewed CRLF source
was restored before the installed proofs. Owned temporary directories are
removed after verified sealing; permanent evidence remains available.
