# Phase 8A manifest — BIU HOLD/LOCK race

Date: 2026-09-10

Status: focused implementation validation passed; independent commit-isolation
and downstream transfer remain open.

## Scope

8A fixes the stale `HLDA` grant that can be accepted at a free boundary just
before the CPU raises implicit `LOCK` for a memory `XCHG`. The correction is
limited to the general CPU BIU. PCAT BUS overlays, DMA/DACK wiring, debug ports,
XT serialization and MiSTer integration are not part of this workstream.

Provenance lead: downstream diagnostic candidate
`PCAT-286_MiSTer@409292dcb06ea507099e4e68cf6d691d9b7294e8`.
The candidate was treated as a hypothesis and reproduced with CPU-only tests
before integration.

## Implementation

- `rtl/spk286_biu.sv`: release an already asserted `HLDA` when a new
  `lock_request` appears, while retaining the existing HOLD boundary and bus
  ownership rules.
- `sim/unit/spk286_biu_hold_lock_tb.sv`: direct arbitration contract, including
  an odd-word locked write and READY waits.
- `sim/unit/spk286_xchg_hold_lock_tb.sv`: normal-core memory `XCHG`, collision
  at the implicit-lock boundary, retained odd-word traffic, follow-on fetch and
  later legal HOLD grant.

## Executed evidence

All commands were run from the repository root and began with the generated
microcode consistency check (`101 entries`, `614 words`).

| Check | Result |
| --- | --- |
| `bash scripts/test_units.sh iverilog spk286_biu_hold_lock` | `BIU_HOLD_LOCK PASS: 13 checks; 2 physical writes` |
| `bash scripts/test_units.sh verilator spk286_biu_hold_lock` | PASS, `13 checks; 2 physical writes` |
| `bash scripts/test_units.sh iverilog spk286_xchg_hold_lock` | `XCHG_HOLD_LOCK PASS: 47 checks; 2 data reads/2 writes` |
| `bash scripts/test_units.sh verilator spk286_xchg_hold_lock` | PASS, `47 checks; 2 data reads/2 writes` |
| Existing `spk286_biu` baseline | PASS, `2419 checks` before the 8A change |

The CPU-level test proves the implicit `LOCK` producer, exact accepted odd-word
traffic, no duplicate exchange, and a subsequent HOLD grant. The direct test
proves the arbitration rule without depending on decoder timing.

## Isolation requirement

The final review must run this manifest from the 8A-only commit with 8B
reverted, then run the 8B manifest from the complementary isolated commit.
Shared microcode/test infrastructure is permitted; decoder behavior and ESC
source are not.
