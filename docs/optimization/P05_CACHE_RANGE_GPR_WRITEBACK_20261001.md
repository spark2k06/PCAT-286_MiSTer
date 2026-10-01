# P05: early generic cache ranges and GPR data priority

Two late stages exposed by fresh downstream fits are restructured without
changing sequential RTL, admission/completion handshakes or CPU cycles.

## Generic operand ranges

In P05, the top compares each cache's real/protected hidden limit with the
ordinary, stack, address, I/O and vector offset sources before choosing the
cache and source. Only a one-bit range result crosses the late selection.
Kept predicate vectors prevent merging that boundary back into a wide mux.

The source priority exactly retains special protected services, vector
requests, I/O, address override and stack selection. The proof includes
arbitrary overlapping qualifiers, all four distinct cache limits/access
bytes, expand-down segments, FFFF word boundaries, PE transitions and
arbitrary LOADALL hidden state. No cache validity or equal-limit assumption
is made. Real mode still observes its existing hidden limits.

The operand service's default parameter preserves the old range expression.
The P05 top selects the precomputed predicate. Its remaining outputs and
sequential logic are source guarded. Direct operand benches add only the
unused default input binding; no expected result changes.

## GPR data priority

The complete 20-source data priority is represented as a priority-masked
one-hot vector and a masked 16-bit data reduction. Selection order includes
task, outer/same-stack returns, segment pops, descriptor results, strings,
allocation/frame operations, ordinary results and the default operand data.
Arithmetic, flags, task slices, enables, indices and sequential state are
unchanged. Overlapping requests retain the original priority.

Both proofs extract actual RTL against `c4a0761` and cover arbitrary
two-state inputs. I/O-priority and overlapping-GPR-priority mutations are
rejected. The generate loop uses the explicit declaration syntax accepted
by the project's Quartus 17 compiler.

## Validation

Strict CPU `-Wall` lint passes in base and P01/P02/P05/P06 profiles. Seven
focused banks pass with Icarus and Verilator in both profiles: operand
service, operand bytes, protected system operations, LOADALL integration,
register execution, stack frames and outer-return SP. This includes the
post-LOADALL hidden-cache access above 1 MiB and preserves existing READY
stall counts. Evidence is `docs/evidence/cache-range-gpr-20261001`.

Fresh downstream fits separately measure GPR priority and its combination
with early cache ranges. Functional equivalence is not a claim of physical
50 MHz closure or a new hardware benchmark result. No full CPU regression
or MiSTer run is included in this checkpoint.

## PCAT integration

Upstream commit: `a1bc5023803f614486e0c190f29aab92066fb90f`. Actual vendor strict production lint and
call-gate/accessed and double-fault banks pass with both simulators. The
sole real-mode `wrap_ip(!protected_msw[0])` binding is retained. All metrics
of the eight physical-owner CheckIT fixtures are identical to the prior
CPU checkpoint; no cycles, waits or bus operations are added.
