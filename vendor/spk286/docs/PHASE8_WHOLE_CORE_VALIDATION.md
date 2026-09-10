# Phase 8 whole-core program validation

Date: 2026-09-10

These are CPU-only whole-core interaction programs already present in the
SPK286 verification suite. Each uses a bounded completion condition and checks
architectural state, accepted transactions or event/frame state; a timeout by
itself is not a pass. The table records the executed Icarus results for the
Phase 8 validation pass.

| Interaction program | Executed benches | Result |
| --- | --- | --- |
| Reset-to-signature, native fetch and redirect | `spk286_core`, `spk286_fetch`, `spk286_prefetch_queue` | PASS: 7 + 26 + 19 checks |
| Prefix/segment stream boundaries | `spk286_prefix` | PASS: 51 scenarios; 3068 checks |
| Restart/resume and event ordering | `spk286_event_lifecycle`, `spk286_event_streams` | PASS: 468 scenarios/46520 checks; 96 streams/4670 completions/379341 checks |
| Fault recovery and far control flow | `spk286_far_lifecycle` | PASS: 247 cases; 15629 checks |
| Nested frames and aliases | `spk286_stack_frame_lifecycle` | PASS: 339 cases; 39513 checks |
| String transform, DF, bounds and resume | `spk286_string_lifecycle`, `spk286_string_boundaries` | PASS: 500 cases/38095 checks; 148 cases/17823 checks |
| Port stream and zero-count event policy | `spk286_string_io_lifecycle`, `spk286_string_zero_events`, `spk286_string_io_zero_events` | PASS: 400 cases/35477 checks; 70 cases/4231 checks; 56 cases/3385 checks |
| HOLD/LOCK, READY, odd word and redirect ownership | `spk286_biu_hold_lock`, `spk286_xchg_hold_lock` | PASS; see [8A manifest](PHASE8_8A_MANIFEST.md) |
| D8–DF coprocessor decode and stream progress | `spk286_esc_instructions` | PASS; see [8B manifest](PHASE8_8B_MANIFEST.md) |

The existing suite remains the functional proof for the previously delivered
CPU behaviors. The Phase 8 additions are deliberately narrow: they add the
HOLD/LOCK race and the deterministic ESC profile without moving PCAT machine
logic into SPK286. The full dual-simulator `make unit`, Yosys sanity check and
repository `make regression` all passed before downstream transfer.
