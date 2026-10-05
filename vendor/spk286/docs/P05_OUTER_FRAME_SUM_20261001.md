# P05: one carry chain for the outer-return frame extent

The fitted decoder checkpoint exposed an outer-return path through two
consecutive adders: SP + allocation, then + 3, before range comparison and
operand completion. The frame extent now uses carry-save bitwise reduction
of those three operands, followed by one 17-bit carry-propagating addition.
The calculation and comparison remain combinational; no cycles or registers
are added and no return/frame control or fault priority changes.

`prove_outer_frame_sum.py` uses the actual old/new range expressions against
`93e2aa2`, guarding the rest of the executor including all sequential logic.
All SP, allocation, limit, access, enable and phase values are arbitrary.
The original 17-bit modulo sum is retained even for unreachable or invalid
state combinations. An 18-bit nonwrapping sum is rejected by the negative
control. This milestone preserves behavior rather than revising any
architectural range policy.

Strict CPU `-Wall` lint in base and P01/P02/P05/P06 configurations and the
call-stack-precheck (9 checks), protected outer-event (6 checks, 503/499 READY
stalls) and outer-return-SP (693 checks / 216 cases) banks pass in Icarus and
Verilator. Cycle/check counts remain unchanged. Evidence is retained under
`docs/evidence/outer-frame-sum-20261001`. No full CPU regression or MiSTer run
is included. Quartus must still confirm the intended physical carry-chain
reduction and the remaining 50 MHz setup/hold margins downstream.
