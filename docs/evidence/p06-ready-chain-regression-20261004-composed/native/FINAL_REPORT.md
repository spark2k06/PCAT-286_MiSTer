# Standalone READY chaining port and validation composition

2026-10-04. Standalone base `86a76ce`, `codex/protected-mode-windows31`.
Approved changes are applied to `D:/GitHub/SPK286`; no commit was made by the
subagent. Historical baseline and profile receipts remain byte-identical.

## Changes

* Copy the selected CPU caller and fetch RTL exactly from the tested vendor
  milestone. The caller reserves queue space for outstanding CODE and response
  bytes; fetch can prepare its next request on READY, preserving backpressure,
  cancel and restart behavior.
* Add only the missing declarations for existing debug outputs in wildcard
  bench adapters: one shared header and three BIU benches. No native pin, board
  or additional CPU interface is introduced.
* Preserve post-MOV sentinel progression in the two execution banks by replacing
  the obsolete F1 local unsupported-latch expectation with actual `0F FF` #UD
  acceptance. Stop before stack entry; verify retained fault CS:IP/FLAGS, full
  signatures, no extra retirement or store. All 48 microcode MOV cases resume
  and reach that fault; the original pause/cancel/reset/stream assertions remain.
* Add generic CODE READY delay to the adjust bank so faster prefetch still
  exercises its existing positive radix-starvation assertion. Architectural
  operands and expected outputs are unchanged.
* Fix compiler LOADALL validation for its named entry even if the instruction
  token was removed. No microcode source, control catalog or emitted ROM changes.
* Add a separate selected CPU generation contract and regenerate the profiled
  CPU. Keep the old baseline contract/receipt unchanged; explicitly bind the two
  new functional files, generated identities and the changed probe header.

No modern standalone microcode fixture, Makefile, supported MAX core probe or
extra Yosys check was replaced. Five legacy release auditors were neither
copied nor certified by this work.

## Exact source scope

The 40 ordered standalone functional RTL files are byte-identical to the v3
frozen vendor sources after the two-file update. All 20 literal `.mc` sources
and all three generated ROM/package sources are identical. The standalone
schedule and timing metadata modules match the PCAT modules byte for byte.

Regenerated profile identities:

| File | SHA-256 |
|---|---|
| `spk286_profiled.sv` | `847a6930469e67d7345847e39f57ab51a5fe3556c73f8741d5e9c7d69c6038c7` |
| `spk286_profiled_events.sv` | `a158e55b5b0a66060784c4901576fb717842cc9a009e3656d5feaaf76b51fbef` |

Both are byte-identical to the selected vendor profile. The generation manifest
uses standalone paths and tool hashes; it is not copied from PCAT evidence.

The standalone unit registry contains 129 banks. The vendor v3 registry contains
130, with only `spk286_event_arbitration` additional. Of the 129 standalone bank
sources, 125 are byte-identical and four differ: core, execution,
microcode_execution and event_lifecycle. All four were executed fresh in both
simulators. The fresh set also repeats fetch, three BIU banks and adjust: nine
dual banks in total. This leaves 120 common-only banks for shared evidence reuse.

All 24 independent vector generator modules invoked by the unit runner match
the v3 snapshot byte for byte. Modern microcode/CI/Phase9B fixtures that differ
were exercised by the fresh full standalone Python suite; their own identities
are preserved in the fixture inventory.

The shared header differs in formatting/grouping from vendor. Its proposed
content and vendor content contain only the same 136 declarations, with equal
types, net/variable kinds, widths and initializers. The static header bridge
records that semantic equality explicitly; it does not call different byte
strings identical. The vendor wildcard also includes an unused
`spk286_system_0f.sv`, absent from the standalone active closure. Fresh standalone
lint validates its actual source list without copying that module.

## Fresh standalone results

| Scope | Result |
|---|---|
| Strict full CPU and component lint | PASS |
| Complete standalone Python suite | PASS, 355 tests |
| Microcode generation consistency and native audit | PASS, 123 entries, 743 words |
| Profile deterministic generation, installed identity and strict lint | PASS |
| Independent schedule oracle | PASS, 45 checks in each simulator |
| Full TOP prefix probes | PASS, eight cases in each simulator |
| Metadata oracle | PASS, 43,878 cases in each simulator |
| Reset/fetch profile probes | PASS, both modes in Icarus |
| Nine affected or distinct banks | PASS in both simulators |
| Extra core MAX selection | PASS in both simulators |
| Extra selector/descriptor/protected-state/LOADALL Yosys checks | PASS, all four |
| Normal native reset smoke | PASS in Icarus and fresh Verilator driver |
| Native state/fetch initialization | PASS, one default plus three fixture cases; zero instructions executed |

This is 28 main commands plus five native smoke/state/audit stages, all fresh.
The complete 1,079-file source inventory was checked unchanged after each run.
No timeout, omitted failed stage or architectural oracle correction occurred.

Useful directed results agree between simulators:

* Fetch: 32 bus/response checks plus wait, cancel, backpressure and limit cases.
* BIU: 110 cases/2,419 checks; HOLD/LOCK: 13 checks/two writes; width/IO:
  140 cases/2,851 checks.
* Adjust: 8,184 cases, 1,764,540 checks and 16,352 immediate stalls.
* Event lifecycle with wrap explicitly enabled: 468 scenarios/49,087 checks.
* Microcode execution: 48 MOV vectors, eight-MOV stream, three cancellation,
  reset and resume boundaries, 5,512 checks and 382 underfill cycles. All 48
  sentinel acceptances preserve the MOV signature and retire count one, with
  retained origins 0103/0104. The first focused trace accepted them after two or
  three real service cycles. Execution-bank #UD retains origin 0200.

## Shared gate status and acceptance limits

The vendor v3 general regression finished with PASS and exit code zero. Its
independent passive audit passed with 581 source inputs and 98 corpus identities
unchanged. `composed-receipt.json` now reports `STANDALONE_COMPOSED_GATES_PASS`;
independent composition review has passed; parent publication and commits remain pending. The composer
requires the shared driver status
`SPK286_READY_CHAIN_REGRESSION_PASS`, exit code zero and all six drift/error
fields explicitly empty, not a marker from another run.

The composition credits the actual shared gate's reported scope for
the 120 common-only banks and shared simulator/corpus/synthesis stages, with the
nine fresh banks and distinct standalone stages above. The native registry
coverage remains 129 Icarus/128 Verilator banks, preserving the existing
Icarus-only full expand-down matrix; the vendor-only arbitration bank is not
reported as a standalone execution. Source inventory counts and fresh execution
counts are separate.

No full standalone `make regression` was executed. No hardware, host, board,
native pin timing or cycle accuracy acceptance follows from these CPU-only
checks. Provisional instruction profiles remain provisional. The five distinct
legacy auditors belong to other release targets and are outside this composed
gate.

## Evidence

* `manifest.json`: applied source snapshot and functional/generated identities.
* `receipt.json`: 28 fresh main results, commands, hard timeouts and raw log hashes.
* `smoke-state-receipt.json`: five native stages and raw log hashes.
* `regression-scope-audit.json`: all 129 TB sources, 24 vector modules and every
  differing standalone fixture, explicitly compared against v3.
* `composed-receipt.json`: scoped fresh/shared composition with source identities.
* `snapshot/build/profile-focused/receipt.json`: deterministic profile generation
  and independent schedule/prefix/metadata/reset results.
* `../spk286-ready-chain-port-plan-20261004/`: approved preimage/selected hashes,
  patches, apply receipt, 40-file source bridge and header declaration bridge.
* `../spk286-ready-chain-port-probes-20261004-v1/`: four focused execution adapter
  runs and all 48 matching sentinel trace records, independently reviewed.

Parent owns the final acceptance review, portable evidence publication and git
commit. Independent source and composition reviews have passed; no subagent commit or evidence publication to standalone was performed.
