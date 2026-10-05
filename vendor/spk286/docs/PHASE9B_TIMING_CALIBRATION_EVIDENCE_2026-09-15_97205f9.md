# Phase 9B calibration evidence — 2026-09-15

This is an immutable summary of the normalized functional calibration capture
produced from commit `97205f9d03ba43823134a2aa69c536c99ba1178a`. It preserves
the result independently of the ignored `build/` directory; it is not a
historical 80286 timing claim or a physical trace.

## Capture provenance

| Item | Value |
| --- | --- |
| Source revision | `97205f9d03ba43823134a2aa69c536c99ba1178a` |
| Branch | `codex/phase9-timing-tstates` |
| Policy | `0`, normalized-functional-baseline |
| Simulators | Verilator 5.020; Icarus Verilog 12.0 |
| Records | 12 |
| CSV SHA-256 | `04d1ceee15296dd628b4de1c897c71bc902c5f0258f1dfad11172e1d7ec50c6a` |
| Verilator baseline/extra SHA-256 | `164a8623a41322377ff5cbec8d24ab871743f098bf214270bceed67f342bc864` / `cb2c175f7378bbd08800244ce0a1fdf4a7ecb9226635d562fe9d8c9746a243b6` |
| Icarus baseline/extra SHA-256 | `164a8623a41322377ff5cbec8d24ab871743f098bf214270bceed67f342bc864` / `cb2c175f7378bbd08800244ce0a1fdf4a7ecb9226635d562fe9d8c9746a243b6` |

The capture was generated with `python3 -m tools.capture_timing_calibration
--simulator both`. The validator checked every simulator independently before
accepting equality. The source-hash set includes both calibration banks, and
the schema-2 manifest retains the complete normalized rows in addition to the
CSV and raw-output hashes.

## Preserved normalized rows

The `final_flags` column is architectural observation for the deterministic
workload. In particular, `ADD AX,BX` produces `AX=68AC` and `FLAGS=0006`.

| Case | Start | End | FLAGS | Cycles | BIU | Accepted | READY | Prefetch req/resp | Queue | Operand | Phase/status/owner |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `mov_ax_imm` | 0100 | 0103 | 0002 | 5 | 2 | 2 | 0 | 2/2 | 2 | 0 | 0/15/0 |
| `mov_bx_imm` | 0103 | 0106 | 0002 | 4 | 1 | 1 | 0 | 1/2 | 2 | 0 | 0/15/0 |
| `alu_reg` | 0106 | 0108 | 0006 | 8 | 1 | 1 | 0 | 1/2 | 1 | 0 | 0/15/0 |
| `mov_mem_read` | 0108 | 010C | 0006 | 9 | 3 | 3 | 0 | 2/2 | 3 | 1 | 0/15/0 |
| `mov_mem_write` | 010C | 0110 | 0006 | 9 | 3 | 3 | 0 | 2/2 | 3 | 1 | 0/15/0 |
| `branch_short` | 0110 | 0114 | 0006 | 4 | 1 | 1 | 0 | 1/0 | 1 | 0 | 1/13/1 |
| `odd_word_read` | 0100 | 0104 | 0002 | 11 | 5 | 5 | 0 | 3/3 | 3 | 2 | 1/13/1 |
| `near_call` | 0100 | 0106 | 0002 | 11 | 5 | 5 | 0 | 3/3 | 2 | 2 | 1/13/1 |
| `near_ret` | 0109 | 0103 | 0002 | 7 | 3 | 3 | 0 | 1/2 | 0 | 2 | 1/13/1 |
| `rep_movsb` | 0100 | 0102 | 0002 | 22 | 6 | 6 | 0 | 2/3 | 0 | 4 | 0/15/0 |
| `int3` | 0100 | 0200 | 0002 | 31 | 6 | 6 | 0 | 1/1 | 0 | 5 | 0/15/0 |
| `divide_fault` | 0100 | 0200 | 0002 | 73 | 8 | 8 | 0 | 3/3 | 1 | 5 | 0/15/0 |

`saw_lock` and `ready_wait_cycles` are zero for all twelve rows. The three
negative fixtures under `tests/fixtures/phase9b/` remain validator evidence,
not CPU captures: they prove rejection of wrong ADD FLAGS, incoherent terminal
bus metadata and a counter beyond the elapsed interval, including when both
simulator inputs are identical.

## Scope boundary

H4 remains closed and the twelve classes are unchanged. This artifact closes
the B2/B3 evidence and CSV-validation increment only. Historical instruction
timing, native T-state calibration, physical-reference comparison and the
remaining Phase 9 work packages remain open.
