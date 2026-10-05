# P06 opcode-local executor permission

## Critical path and change

The event-selection fit improves global setup to -6.989 ns. Its critical
CPU cone starts at retained instruction metadata, crosses the deadline,
then reaches stack/operand selection and register write data. The budget
compressor fit remains negative at -7.300 ns. The deadline currently gates
every executor operation even though its REP permission can differ from raw
operation permission only at `MC_BRANCH_REPEAT_EMPTY` (121) and
`MC_BRANCH_REPEAT_CONTINUE` (128).

Generate a profiled executor from the pinned portable executor. Add the raw
operation-valid input and derive an implementation permission with the same
reset, cancellation, start and task-skip qualifiers. Replace the permission
only in 128 opcode-qualified strobes whose expanded logical guard is provably
false at both REP words, for arbitrary state and other context. At all other
words, the actual top-level REP permission equals raw permission.

REP strobes, state-only register completion, all sequential update expressions
and all three subservice enables retain their existing expressions. The
portable executor remains byte-identical. This transformation adds no retained
state, fabric stage or virtual clock, and does not alter instruction minima,
profiles, divisors, functionality settings or timing constraints. The wrapper
includes the generated module; the generator records its input/output hashes
and the exact per-strobe source changes in `repeat-local-contract.json`.

## Directed qualification

| Check | Result |
| --- | --- |
| Actual top-level REP permission outside its two words | Symbolic proof PASS |
| All 128 changed strobes, arbitrary opcode/state/context | Symbolic equality PASS |
| Undo every declared generated edit | Exact original source bytes recovered |
| Unsafe global permission bypass | Counterexample; rejected |
| Strict full CPU lint | PASS |
| Scheduler and full TOP prefix oracles | Both simulators PASS; 54 / 8 cases |
| Full CPU handoff, all eight profiles | Both simulators PASS |
| Comparison to budget-compressor directed receipt | Entire 17-entry results list identical, including clocks, events/faults, cancellation/HOLD and raw MAX stream |
| REP zero-count/event, string I/O lifecycle, stack-frame lifecycle | 24 cases per simulator PASS; complete MAX raw streams equal to portable CPU in all three fixtures |

The strobe proof preserves logical operators and exact eight-bit opcode
comparisons. Other atoms are independent arbitrary Boolean inputs. Alias
expansion uses original expressions as simultaneous equivalence cutpoints;
the source audit and strict full-CPU elaboration accompany this contract.
It assumes only the separately proved top-level permission property, and
uses no executor lifecycle or reachable-state restrictions. This is a
combinational contract plus directed CPU checks, not a whole-CPU sequential
formal proof or full regression.

The [sealed packet](../evidence/p06-repeat-local-20261005/manifest.json)
contains proofs, negative control, source/fixture snapshots, both simulator
logs, stream identities and baseline comparison. Every member was read back
byte for byte before deleting 843,183,783 logical bytes of owned simulator
temporaries. Full regression remains **USER_DEFERRED**; hardware is **NOT_RUN**.

## Physical acceptance

Fit all features, including Adlib/OPL2, at the unchanged physical 50 MHz.
Use the existing stricter 0.500 ns palette minimum-route constraint. Measure
all four corners for global/CPU setup and hold, recovery/removal, SDRAM,
actual physical ALMs and registers. Verify original-SDC hold independently
on the same completed fitted netlist. No physical timing or ALM improvement
is claimed until those measurements finish.
