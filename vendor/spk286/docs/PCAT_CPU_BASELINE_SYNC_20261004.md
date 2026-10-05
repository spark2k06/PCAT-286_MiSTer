# CPU baseline synchronization with PCAT, 2026-10-04

This CPU-only checkpoint brings the independent SPK286 repository into line
with the functional CPU baseline already used by PCAT-286_MiSTer. It does not
add the AT chipset, MiSTer clock selector, OSD, SDRAM controller or bus bridge.

## Changes

- P02 fetch chaining, P05 parallel operand/system bounds and P07 synchronous
  microcode selection are now the established implementation. The top no
  longer retains the obsolete alternative branches for those defines.
- Real-mode instruction fetch wraps its logical IP after offset FFFF.
  Protected-mode fetch retains the overflow bit and rejects an exhausted
  segment. The top supplies `wrap_ip` from the actual protection-mode state.
- The six-byte prefetch queue selects its existing head byte with a parallel
  six-position mask. Capacity, ordering, reservation and pointer updates are
  unchanged.
- The fetch unit fixture explicitly supplies `wrap_ip` and checks real-mode
  wrap separately from protected-mode segment-end rejection.

The three synchronized RTL files are byte-identical to the PCAT vendor files
as present after PCAT commit `b14e54b6a9752994d9f989019713535be8b1edae`:

| File | SHA-256 |
| --- | --- |
| `rtl/spk286.sv` | `10273776b109037657ecb9cbf21dc7256343a20c1dfe53188b9826fdb30cb483` |
| `rtl/spk286_fetch.sv` | `9879ff7f0db97412f47d0be085674bc0851bf44d1916d1262bc1972a5c8f0cbe` |
| `rtl/spk286_prefetch_queue.sv` | `7a53a407df6114214a7d3861d7fb94c7f35b094d9e0162ab6789cb46a6bc2e29` |

The other 34 shared flat RTL files and all three generated microcode SV
files already matched. The portable CPU closure has no instance of PCAT's
legacy `spk286_system_0f.sv` file.

## Directed acceptance

- Strict Verilator `--Wall` lint: passed.
- Independent microcode Python suite: 112 tests passed. Active microcode
  generation remains consistent; no generated microcode was edited.
- Package-first RTL manifest: three tests passed.
- Fully mapped Yosys synthesis and `check -assert`: fetch and prefetch queue
  passed. This is a component synthesis check, not a Quartus fit measurement.
- Eleven existing unit banks passed in both Icarus and Verilator: fetch,
  prefetch queue, prefetch fidelity, core startup, microcode execution,
  operand service, protected system, protected RETF, BIU HOLD/LOCK, ESC
  boundaries and NPX traps. Original functional assertions were retained.
- A freshly built Verilator CPU passed the existing SingleStepTests smoke:
  80 MOV immediate-register cases (B8..BF) and 20 MOV register/memory cases
  (89/8B), with their original architectural comparison and revocation rules.

Build receipts and complete logs were produced in
`PCAT-286_MiSTer/build/spk-standalone-sync-20261004`; source SHA-256 values
before and after the checks match. The unit commands can be repeated with
`SPK286_BUILD_DIR` set to a fresh output directory and
`bash scripts/test_units.sh both <unit>`.

This is directed verification of the synchronization, not a complete CPU
regression. Historical source-pinned optimization proof scripts and their
old evidence retain their original milestone scope; they are not a proof
of every subsequent whole-CPU change.

## Timing scope

These established implementation choices do not establish historical
cycle accuracy. The general instruction metadata, interval schedule and
CPU-only profiled top/events package are a separate provisional checkpoint.
Maximum execution preserves real dependencies; a frequency label alone
does not prove an Intel 80286 instruction or pin timing profile.
