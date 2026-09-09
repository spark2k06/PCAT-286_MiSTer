# Byte IDIV overflow compatibility investigation

Status: the corrected candidate passes all 50000 unchanged arithmetic physical
records, including all four previous byte-IDIV discrepancies. Full integrated
regression passed on all 295 unchanged inputs; this is not release approval.

The pinned F6.7 corpus contains four normal results where mathematical signed
8-bit division would overflow. All produce AL=80; the remainder is also
observable. Original source bytes, exception metadata and expected values are
unchanged. These observations were independently reported in upstream issue 1.

A 2026-03-24 discussion proposes that an eight-step finite division result can
reach the minimum signed quotient despite overflow. The linked emulator is
reference evidence only. No external implementation is imported. A project
research model, expressed as a finite 16-bit recurrence, agrees with all 5,000
physical F6.7 records (3,057 faults), including all four previous discrepancies.

Exhaustive examination of 16,777,216 byte-operand/dividend pairs shows agreement
with integer arithmetic for every one of the 4,210,433 mathematically legal
results. It also exposes 128 positive-overflow predictions in the reference
algorithm that are not established by these physical observations. They must
not become CPU behavior merely because an emulator implements them.

The bounded implementation therefore preserves mathematical division for legal
results, unsigned division and word division, and preserves zero-divisor and
positive-overflow faults. Only negative signed-byte overflow consults the finite
candidate; a corrected quotient of the minimum signed value is accepted with
its finite remainder. This is a general arithmetic condition, with no test
identity, address, byte stream or expected register value in the CPU.

The ordinary quotient calculation remains an independent real computation.
The finite candidate can be computed during its first eight steps using storage
otherwise reserved for multiplication. No idle timing states are required.
Fresh checks of pause, cancellation, captured inputs and result ownership passed.

The expected-value generator may adopt this physically supported overflow rule
only alongside the independent original corpus checks. Its agreement with RTL
alone cannot establish historical behavior. Capture evidence concerns the tested
chip; broader revision equivalence and architectural release remain review work.

References:
- https://github.com/SingleStepTests/80286/issues/1
- https://github.com/SingleStepTests/80286/issues/1#issuecomment-4121587450
- https://github.com/a-mcego/granite/blob/58a1c5a0edba10a63124359a85ad2cb77eee7b35/include/80286.h
- Intel 210498-005 IDIV instruction: quotient limits and divide-error contract.

See phase7_idiv_compatibility_research.json for exact observations and source
fingerprints. The earlier arithmetic FAIL logs remain valid historical records.

The actual delivered gate is recorded in phase7_arithmetic_validation.json.
