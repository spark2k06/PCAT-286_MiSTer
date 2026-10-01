# P05: compare protected access ranges before offset selection

The downstream fitted carry-save checkpoint exposed a 23-level CPU path:
micro-PC decoding, late stack/address selection, the selected offset's range
comparison, operand completion and GPR writeback. The production P05 profile
now compares the stack, address-override and ordinary operand offsets in
parallel before selecting the resulting one-bit fault predicate.

Both the selected segment cache and the temporary call-stack cache preserve
their original limits and expand-down behavior. The shared fault qualifier
already excludes I/O and vector accesses. Stack selection still takes
priority over address override, including arbitrary overlapping qualifiers.
Validity, presence, read/write permissions, stack-segment checks, exception
ordering and the baseline profile are unchanged. No registers, handshakes
or CPU cycles are added or removed.

`prove_protected_access_range.py` extracts the actual old service-offset and
old/new fault expressions against `f029491`. All offsets, limits, widths,
access permissions and overlapping request flags are arbitrary two-state
inputs. A source guard proves that the remaining top-level RTL, including
all sequential logic and the baseline fault expression, is unchanged. A
mutation that removes stack priority is rejected.

Strict CPU `-Wall` lint and six focused banks pass in both base and
P01/P02/P05/P06 profiles with Icarus and Verilator: odd protected stacks,
call-gate accessed bits, double faults, protected system operations, task
LDT handling and outer-event frames. Expected results were not edited.
The broader segment matrix additionally passed 2,183 checks in Icarus;
its Verilator compilation was stopped for resource cost and is not counted
as a dual-simulator pass.

Evidence is retained in `docs/evidence/protected-access-range-20261001`.
No full CPU regression or MiSTer run is included. A fresh downstream fit
must determine the physical timing improvement and remaining 50 MHz margins.

## PCAT integration

Upstream commit: `c4a076171730bf33ae4502deabb24d979d4811f4`. The vendor top retains the PCAT real-mode
`wrap_ip(!protected_msw[0])` binding. Actual vendor strict production lint
and the call-gate/accessed and double-fault banks pass in both simulators.
All metrics of eight CheckIT physical-owner fixtures are identical to the
previous CPU checkpoint; no cycles, stalls or bus transactions are added.
Fresh placement/routing results are reported separately.
