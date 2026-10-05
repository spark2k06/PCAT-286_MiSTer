# P05: operand range comparison without a late increment

The operand service compared a 17-bit `offset + !request_byte` with the
segment limit. The same normal-segment result is `offset < limit`, or
`request_byte && offset == limit`. For expand-down segments, `offset > limit`
still applies; the no-wrap condition is `request_byte || offset != FFFF`.
Both comparisons now run without an incrementer in front of them.

`prove_operand_limit.py` checks the actual old/new expressions against
`7797942` for all 2^34 two-state offset/limit/width/expand-down combinations.
It guards the rest of the operand module, including all sequential state and
all other outputs. Accepting a word at FFFF is rejected by the negative
control. This includes boundary, invalid-range and arbitrary-state cases;
the optimization does not assume a valid or cached descriptor.

Strict CPU `-Wall` lint in base and P01/P02/P05/P06 configurations and the
operand-service (209 checks) and operand-byte (130 cases / 413 checks) banks
pass in Icarus and Verilator. Check counts and simulated cycles are unchanged.
Formal and directed receipts are retained in `docs/evidence/operand-limit-20261001`.
No full regression or hardware run is included. The downstream fit records
physical timing separately; this proof does not establish 50 MHz closure.
