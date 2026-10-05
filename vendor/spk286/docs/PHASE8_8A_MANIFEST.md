# Phase 8A manifest — BIU HOLD/LOCK race

Date: 2026-09-10

Status: focused validation, commit-isolation review and downstream transfer
passed; the user-owned Quartus/RBF hardware checkpoint remains pending.

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
| `make phase8-audit` | `PHASE8_AUDIT PASS: 2 rejected RTL mutants; 3 pristine controls; production bytes unchanged` |

The CPU-level test proves the implicit `LOCK` producer, exact accepted odd-word
traffic, no duplicate exchange, and a subsequent HOLD grant. The direct test
proves the arbitration rule without depending on decoder timing.

## Isolation requirement

The isolated review was completed from the 8A-only snapshot with 8B reverted.
The complementary 8B-only review was also completed. The verified CPU payload
was transferred to `PCAT-286_MiSTer` at commit
`b6c3035e716fcd640523c7189480e59941067472`; see
[the downstream transfer record](PHASE8_DOWNSTREAM_TRANSFER_20260910.md).
The Phase 8 mutation audit was then transferred in follow-up commit
`af74c70108db8ede90a62a4f6bcff6d8da86057d`.
The transfer and portable checks do not constitute a Quartus fit, RBF load or
physical-board result.
