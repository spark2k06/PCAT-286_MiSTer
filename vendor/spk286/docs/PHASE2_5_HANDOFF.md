# Phase 2.5 Handoff

## Status

- Branch: `codex/phase2.5-singlestep`
- Base commit: `829489dfb9b54054114dbd77af2875213cbae6ee`
- Integration commit: `caa53b4` (`Add SingleStep 80286 validation runner`)
- Validation date: `2026-09-05`
- Upstream repository: `SingleStepTests/80286`
- Upstream commit/version: `37c73caf53dcd22d3dd369ff09305d13d117a4fe` / `1.1.0`
- Upstream license: MIT

## Runner architecture

`tools/fetch_singlestep.py` obtains a shallow, blob-filtered sparse checkout
under `.cache/singlestep-80286/`. `tools/singlestep.py` directly parses the
MOO 1.1 chunks and normalizes them to `SingleStepCase`. The Python runner then
filters revocations, expands sparse expected state, adjusts the HALT-inclusive
published `IP`, and writes a compact ignored batch.

The existing Verilator executable is extended through
`sim/verilator/singlestep.cpp`. It initializes the existing architectural
ports, supplies sparse RAM to the existing fetch bus, waits for
`instruction_retired`, and compares the final register/memory state. One
Verilator process consumes one batch per opcode; it is not rebuilt or relaunched
for every vector.

## Corpus results

| Opcode set | Discovered | Revoked | Selection-skipped | Executed | Passed | Failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `B8..BF` smoke | 40,000 | 0 | 39,920 | 80 | 80 | 0 |
| `B8..BF` full | 40,000 | 0 | 0 | 40,000 | 40,000 | 0 |

The full run completed in approximately `5.584 s`, or `7,162.7 tests/s`, on
the validation environment. The smoke run completed in approximately
`2.235 s`, or `35.8 tests/s`; its lower rate includes the per-opcode simulator
startup overhead. All valid B8..BF cases pass.

## Commands used

```text
make singlestep-fetch
make regression
make singlestep-smoke
make singlestep-mov
```

The normal regression includes lint, directed Verilator units, Verilator and
Icarus smoke tests, Python tests, state-vector checks, and the SingleStep smoke
path when the ignored cache is present. The explicit `make singlestep-mov`
command runs the complete B8..BF suite.

## Validation status

- Verilator lint: pass (`LINT PASS`)
- Verilator directed units: pass, including execution and prefetch tests
- Verilator reset/state smoke: pass
- Icarus reset smoke: pass
- Python tests: `11` passed
- Yosys structural checks: pass with `0` reported problems
- SingleStep smoke: `80/80` passed
- SingleStep full B8..BF: `40,000/40,000` passed
- External corpus/cache: ignored and untracked

## RTL findings

No SPK286 architectural bug was exposed by the B8..BF hardware vectors. The
integration adds the explicit `instruction_retired` boundary used by the
runner and preserves the existing `MOV r16, imm16` implementation. The MOO
cycle-status name for status `0` was aligned with upstream `moo2json.py`
(`IRQA`). No expected vector values were changed.

## Known limitations

- Only `MOV r16, imm16` (`B8..BF`) is implemented and validated.
- Exact 80286 cycle, bus wait-state, prefetch-overlap, and queue-state
  comparison is deferred; the current acceptance contract is architectural
  register and sparse-RAM state.
- The current sparse-memory adapter returns zero for unspecified reads and has
  no data-operand transaction path yet.
- Unsupported opcodes remain a development trap rather than full 80286
  invalid-opcode exception behavior.
- Quartus and MiSTer integration are outside this standalone CPU validation.

## Recommended Phase 3 Starting Point

The Phase 3 recommendation remains correct: add a `ModR/M decoder`, then
`effective-address generation`, then the `register/memory operand path`.
Begin with register-direct forms, preserve the existing six-byte prefetch and
retirement contracts, and add a separate data transaction path before enabling
real-mode memory operands.

## Finalization

After this handoff is committed, keep the branch separate from `main`. Push it
without force-updating any remote ref when authentication is available.
