# LOADALL validation receipt — 2026-09-16

This receipt closes the implementation work for the current Milestone 7
functional slice. It does not close the milestone itself: the target silicon,
hardware-derived unreal-mode vectors, revision-specific corner cases and exact
bus timing remain open evidence gates.

## Results

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p 'test_microcode*.py'` | 88 tests passed |
| `bash ./scripts/test_units.sh both spk286_decoder` | Passed under Icarus and Verilator; 263 opcode checks |
| `bash ./scripts/test_units.sh both spk286_loadall_service` | Passed under Icarus and Verilator; 186 image/privilege/atomicity checks |
| `bash ./scripts/test_units.sh both spk286_loadall_integration` | Passed under Icarus and Verilator; atomic 102-byte commit, hidden-cache access above 1 MiB, READY/reset/HOLD/NMI boundaries |
| `bash ./scripts/test_units.sh both spk286_loadall_protected` | Passed under Icarus and Verilator; CPL=1 `#GP(0)` delivery and frame checks |
| `bash ./scripts/lint.sh` | Passed |
| `bash ./scripts/synth_check.sh` | Passed; Yosys hierarchy includes `spk286_loadall_service` |
| `research/loadall_emulator_differential.py` | `PASS_WITH_RECORDED_DIFFERENCES`; 86Box and PCem agree on all five controlled cases |

The focused RTL commands were executed from WSL so that both simulators and
the repository's POSIX scripts used the same environment. Verilator's repeated
`constant selects in always_*` messages are informational warnings from
Icarus/Verilator and did not produce a failed check.

## Regression boundary

The complete Python discovery run reached 319 tests with one pre-existing
repository-state error: `tests/test_ci_status_capture.py` expects
`.github/workflows/ci.yml`, which is absent in the checked-out tree. This was
not changed as part of LOADALL. The broad `test_units.sh both` battery was also
started, and the unrelated protected/control blocks observed before it was
stopped passed; the acceptance gate for this change is the dedicated LOADALL
and decoder/integration/protected battery listed above, not an unqualified
claim that the full repository battery is green.

The emulator differential remains bounded source-function evidence. Its two
recorded disagreements with SPK286—reserved FLAGS normalization and clearing
PE from a protected-mode image—are deliberately not resolved by emulator
majority voting; they remain subject to Intel/silicon evidence.

## Scope confirmation

No 80386 behavior was added. `LOADALLD` (`0F 07`), `STOREALL`, ICE/test forms
and unrelated undocumented aliases remain outside the 80286 milestone.
