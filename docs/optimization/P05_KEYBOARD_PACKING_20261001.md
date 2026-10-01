# P05 keyboard packing at 50 MHz

## Scope

The [50 MHz audit](P05_50MHZ_AUDIT_20261001.md) identified a 15-level path
from the keyboard FIFO to `sequence_q`: -2.954 ns at slow 100 C and
-4.479 ns at slow -40 C. `build_sequence` used a running integer index,
variable part selects and conditional increments to append at most eight
bytes. Each byte depended on the previous append decisions.

The rewrite expresses the existing navigation make/break layouts as fixed
concatenations and constant lengths. It preserves Set 1 and raw Set 2,
NumLock, both Shift states, Pause/PrintScreen, overflow and backpressure.
There is no new register, state or cycle. All RTL outside `build_sequence`
is identical to commit `20cf243ee4df684e6cfeca3b0cf7c1fa3f6db60d`, after
normalizing line endings.

## Directed evidence

`scripts/test_at_keyboard_packing.sh` freezes the committed reference and
extracts both actual packing blocks. It checks the complete 64-bit sequence
and length for all 16,384 two-state input combinations, including unused
bytes. Every sequence length 0 through 8 occurs. Icarus and Verilator agree.

| Check | Result |
| --- | --- |
| Strict Verilator RTL lint (`-Wall`) | Passed, no warning waiver |
| Exhaustive packing equivalence | 16,384 cases, both simulators |
| Whole-module cycle equivalence | 23,150 cycles, both simulators |
| Emitted bytes / held cycles | 3,257 / 9,241 |
| Simultaneous enqueue/load / at full FIFO | 950 / 821 |
| Resets / byte trace | 23 / `03451987` |
| Existing keyboard/8042 integration bank | Passed, 147 reads, both simulators |

The cycle comparison observes output bytes, validity, the full sequence,
remaining length, FIFO pointers/count and Shift/toggle state. It includes
exact-full overflow, reset without replay, deterministic randomized arrivals
and backpressure, and a final complete drain.

Local evidence is preserved in `build/keyboard-packing-tests-20261001/` and
`build/keyboard-packing-controller-20261001/`. Source guards and hashes are
part of `sources.json`; simulator-specific finish messages are excluded
when comparing result lines.

## Fitted evidence

The fresh frozen run is `build/keyboard-packing-fit-20261001/`, using the
production NO_DEBUG profile, the actual 20 ns clock, the same seed and SDC.
The build uses `AT_DETAILED_TIMING=1` to retain all four corners and all
audit groups. No clock exception or frequency change accompanies this RTL.

| Corner | Keyboard setup | Keyboard hold | Global setup | Global hold |
| --- | ---: | ---: | ---: | ---: |
| Slow 100 C | +6.584 ns | +0.423 ns | -4.782 ns | +0.128 ns |
| Slow -40 C | +6.388 ns | +0.463 ns | -4.153 ns | +0.018 ns |
| Fast 100 C | +13.104 ns | +0.179 ns | +2.140 ns | +0.093 ns |
| Fast -40 C | +13.996 ns | +0.163 ns | +2.410 ns | +0.067 ns |

The worst keyboard path is now 11 levels, with at least +6.388 ns setup
and +0.163 ns hold. Global recovery/removal are positive in all four corners.
The keyboard milestone is accepted for this scope. **50 MHz closure remains
open:** the new placement exposes a 22-level CPU path from prefetch `head_q`
to `event_error_code`, and the CPU-to-bridge and incoming SDRAM-owner paths
also remain negative. Unchanged RTL can move to a different critical route
when the fitter places the whole design again.

Compilation took 26:21 (fitter 17:42), followed by the detailed extraction.
The new RBF is 4,085,456 bytes, SHA-256
`182a3d22be1dfd7b8df0a7f008cf8708e0243b7247d89f0e1e56408f0c567e7f`.
It remains in the frozen build's `work/output_files/`; the previous root RBF,
STA and flow reports retain their original hashes.

Committed evidence is in
[the candidate receipt](../evidence/keyboard-packing-20261001/receipt.json)
and [the fitted audit](../evidence/keyboard-packing-20261001/audit.json).
The existing SDRAM budget and coverage limitations remain as documented in
the original audit; this milestone does not claim external-board sign-off.

### Fmax metadata parser correction

The original summary parser omitted Fmax rows whose trailing `Note` cell
was empty. Raw fitted reports and all setup/hold/path metrics were retained
correctly. The focused parser check now covers both empty and populated
notes, including integer frequencies. Re-parsing the exact same fitted
reports leaves every path metric unchanged and recovers the main clock's
Fmax. The committed original receipt is preserved; corrected local metadata
is `build/keyboard-packing-fmax-corrected-summary.json`. Subsequent summaries
use the corrected parser. Slack at the real clock remains the acceptance
criterion, rather than Fmax alone.

## Reproduction

```sh
bash scripts/test_at_keyboard_packing.sh build/keyboard-packing-new-tests
PCAT_BUILD_DIR="$PWD/build/keyboard-controller-new" bash scripts/test_at_keyboard.sh
AT_DETAILED_TIMING=1 bash scripts/build_at_no_debug.sh build/keyboard-packing-new-fit
python3 scripts/summarize_at_50mhz_timing.py build/keyboard-packing-new-fit --fresh-build
```

These checks are directed. No full CPU regression or hardware test is claimed.
