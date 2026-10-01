# Protected-mode follow-up block: H03, H10, H12, H13

Baseline: `b5a82d8`, 2026-10-01. The user authorized this four-story block,
directed validation and separate milestone commits in SPK286 and PCAT.
The whole-project regression will run after the block.

## H03 — POPF and ordinary IRET FLAGS privilege masks

**Implemented and directed validation passed.** Intel 80286 PRM 210498-005,
section 10.1, permits POPF/IRET to restore NT, restricts IOPL writes to CPL0,
and restricts IF writes to executing CPL <= old IOPL. The decision must use
the pre-return context, not the destination CPL or the popped IOPL.
Real-mode POPF/IRET preserve NT/IOPL under the existing 286 compatibility
contract, corroborated by native 86Box `opPOPF_286` and physical real-mode data.
Native protected `pmodeiret` computes its flag mask before publishing CS/CPL.

Before correction the new bank fails on ordinary CPL0 IRET: old FLAGS `00D7`,
popped `9DD5`, expected `1DD7`, actual `0DD7`. A shared instruction FLAGS mask
now implements those rules for POPF and ordinary IRET. Task-return FLAGS use
their existing separate path. No microcode or timing policy changed.

| Directed validation | Result |
|---|---|
| `spk286_return_flags`, Icarus and Verilator | 5892 cases / 20280 checks each |
| Same bank with PCAT P01/P02/P05 options, both simulators | Same totals, passed |
| Existing ordinary-gate NT bank, both | 158 cases / 944 checks each |
| Existing protected return/retry bank, both | 27 cases / 81 checks each |
| Existing nested-task IRET bank, both | 10 checks each, passed |
| Existing stack/control bank, both | 9128 cases / 1944134 checks each |
| Complete physical real-mode 9D and CF files | 10000 passed, zero failures/skips |
| RTL lint, compiler tests and reset smoke | Passed; 105 compiler tests |

The new bank covers all CPL/IOPL pairs, opposite old/new IF, incoming NT and
IOPL combinations, same/outer IRET, real-mode controls, failed returns,
READY stalls and all three timing policies. Failed IRET preserves source
FLAGS/CPL/SP. Physical files establish real-mode compatibility; they are not
a silicon oracle for protected-mode gates.

Reproduce with `bash scripts/test_units.sh both spk286_return_flags`.
Logs and the failing baseline are retained in `build/pm-block-20261001/h03-*`.
