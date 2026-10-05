# Phase 9C BIU contract follow-up — 2026-09-15

Follow-up evidence for the normalized 9C increment at source commit
`eb6f2d0`. These are focused banks only; the Phase 9 full regression remains
deferred as agreed.

| Bank | Verilator | Icarus |
| --- | --- | --- |
| `spk286_biu_width_io` | PASS; 140 cases, 2,851 checks | PASS; 140 cases, 2,851 checks |
| `spk286_biu_hold_lock` | PASS; 13 checks, 2 physical writes | PASS; 13 checks, 2 physical writes |
| `spk286_scalar_io` | PASS; 452 cases, 24,633 checks | PASS; 452 cases, 24,633 checks |
| `spk286_event_lifecycle` | PASS; 468 scenarios, 48,927 checks | PASS; 468 scenarios, 48,927 checks |

Together with the real-CPU timing capture, these banks cover normalized memory
and I/O ownership, odd-word splitting, READY waits, cancellation, response
retention, implicit LOCK, HOLD/HLDA boundaries and the two-cycle INTA chain.
They do not establish physical `T1/T2/T3/Tw/T4` timing or a historical MHz
profile.

The separate 9C capture comparison still records the simulator-only
`operand_wait_cycles` discrepancy described in
`PHASE9C_BIU_CONTRACT_EVIDENCE_2026-09-15_eb6f2d0.md`; it has not been hidden
by changing RTL or expected results.
