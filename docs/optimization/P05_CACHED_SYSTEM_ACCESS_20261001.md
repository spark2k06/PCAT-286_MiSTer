# P05: cached system bounds and shared protected ranges

Fresh fitted paths exposed a serial selected-limit comparison feeding
system-table faults and ordinary protected access. P05 now compares the
six-byte table span with all four real/protected hidden cache limits before
selecting a one-bit result. The default micro-executor parameter retains
the old expression. No cache validity, equal-limit or ordinary-real-mode
limit assumption is made.

For expand-down segments the entire span must stay above the limit and
must not overflow FFFF: the first offset may not exceed FFFA. Normal
segments retain the full 17-bit offset-plus-five comparison. Ordinary
protected access shares the already equivalent operand-range predicate;
the complete access-fault qualification retains its existing priority,
permissions, special-service exclusions and PE-loaded gating.

The exact proof extracts actual RTL against a1bc502, guards all unrelated
RTL, and covers arbitrary two-state hidden caches, selectors, mode bits,
request/width/permission states and overlapping service qualifiers. It
proves complete protected_access_fault and system_limit_fault equality.
Removing the expand-down overflow bound or substituting the stack offset
for the ordinary offset is rejected by separate negative controls.

Strict CPU Wall lint is empty in base and P01/P02/P05/P06 profiles. Four
focused banks pass with Icarus and Verilator in both profiles: protected
system operations (538 checks), odd protected stacks (951 checks / 216
cases), call-gate/accessed (420 / 144), and LOADALL integration, including
hidden-cache access above 1 MiB. The LOADALL bus counts remain 131 base
and 133 production. Evidence: docs/evidence/cached-system-access-20261001.

This change adds no sequential state, cycles or handshake stages. The
fresh downstream physical fit is pending; functional equivalence does
not establish 50 MHz closure. No full CPU regression or hardware run was
performed.

## PCAT integration

Upstream commit: `c5545857bf3f450d54b9e73b56b4a65e159babe3`. Actual vendor strict production lint and
call-gate/accessed and double-fault banks pass with both simulators. The
sole real-mode `wrap_ip(!protected_msw[0])` binding is retained. All metrics
of the eight physical-owner CheckIT fixtures are identical to the prior
CPU checkpoint; no cycles, waits or bus operations are added.
