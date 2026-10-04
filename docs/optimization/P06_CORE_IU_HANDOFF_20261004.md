# P06-IU01: bounded register handoff pilot

Date: 2026-10-04. Status: **private directed acceptance passed; work paused at the user's request**.

The private M5 source selection extends the frozen M4 CPU. It retires a qualified
register instruction and admits the next unprefixed opcode on the same virtual
CPU boundary. The production CPU, MAX RBF, QIP and configuration are unchanged.
This is the first slice of P06-IU01, **not completion of the three-entry decoded
instruction queue or the historical speed profiles**.

## Contract and implementation

The [Intel extraction](P06_INTEL_TIMING_REFERENCE_20261003.md) identifies ADD,
XOR and CMP register forms at two processor clocks, and ADD/XOR immediate forms
at three. Native 86Box charges two clocks to the register forms and also two to
the immediate forms; that recorded approximation remains explicit. There is no
new native 86Box measurement in this milestone. Intel's separate three-entry
decoded queue remains an open part of [P06-IU01](P06_TIMING_CONTRACT_20261003.md).

M4 met each individual minimum but inserted an additional virtual dispatch
clock between instructions. M5 removes that handoff clock when the old retained
result, required operand bytes, duration deadline and execution permission are
ready. It uses the existing synchronous microcode ROM and functional engine.
Old GPR/FLAGS commit and new opcode admission share an edge; the next instruction
captures operands after the updated architectural registers are visible.

The qualifier uses retained state, not combinational feedback from the new
START or event-request/fault calculation. Only old operand DONE survives a
qualified service restart. Old byte acceptance does not survive START. The
instruction context replaces its old byte count with one new opcode byte and
the event owner saves the new start IP. The old registered retirement pulse
cannot clear the new active context on the following fabric edge.

NMI pending/current, enabled INTR, TF, STI/SS shadows, active events,
cancellation and execution refusal serialize the handoff. Existing event
arbitration remains authoritative; the private scope guard stops before timed
event entry, data, INTA, HOLD or LOCK work. Prefix, memory and unsupported opcode
suffixes stop explicitly. This is not event-timing acceptance.

`scripts/build_p06_iu_cpu.py` generates the selected private sources from the
unchanged hash-pinned M3/M4 builders. New parameters default to zero. No extra
queue, functional execution engine, PLL or state register is declared.

## Accepted directed results

Evidence build: `build/p06-iu-final1-20261004`. Icarus and Verilator agree on every
paired edge trace and summary. No total regression or Quartus fit was run.

| Experiment | Result |
| --- | --- |
| All 13 supported encodings paired with each other, four arithmetic seeds, aligned/odd starts, plus longer dependent streams | 688 sequences / 1,448 instructions |
| Warm handoff | 760 same-edge retire/start events |
| Same vectors with overlap disabled | Identical GPR/FLAGS; all 688 first handoffs save exactly one processor clock with overlap enabled |
| Cold fetch | 1,448 instructions with independent architectural results and qualified minimum durations |
| Deliberately late physical bytes | 40 instructions; dependency delays are not reclassified as board waits |
| Pause, controller error, redirect/reset before and after a handoff, NMI before/on/after a handoff, enabled/disabled INTR, TF, prefix/memory/unknown suffix | 15 modes × 11 sequences |
| Single-instruction compatibility | 208 warm exact 2/3-clock cases and 208 cold functional cases |
| Original versus private MAX | 208 per-edge cases identical in both simulators |
| Existing units | Register 78, immediate 184, policy 63, fetch 32 checks plus waits/lifecycle/limits |
| Strict CPU lint | MAX, M4 enabled/IU disabled, M5 enabled all pass |
| Microcode consistency | Pass |
| Sequential equivalence with overlap disabled | Sequencer, operand decoder and instruction context proven by Yosys |
| Negative architectural oracle | Altered expected GPR is rejected |
| Frozen M3/M4 preservation | 120 and 168 artifacts respectively pass their unchanged auditors |

Warm ADD-to-ADD illustrates the removed gap: start-to-start spacing changes
from three to two processor clocks, while each ADD still executes for two.
Immediate execution retains Intel's three-clock minimum. Mixed arithmetic
streams check both register directions, compare-without-write, overflow, carry,
parity, sign and preservation of unaffected/undefined flag bits.

## Partial resource measurement

Generic Yosys mapping is **not Cyclone V ALMs, whole CPU overhead or STA**.
The sequencer uses the actual 10-bit address / 743-word configuration.

| Isolated component | Original cells | Timed cells | Cell delta | Original/timed register bits |
| --- | ---: | ---: | ---: | ---: |
| Microsequencer | 326 | 365 | +39 | 23 / 23 |
| Operand decoder, including its EA logic | 756 | 757 | +1 | 47 / 47 |
| Instruction context | 69 | 76 | +7 | 12 / 12 |
| Sum of these measured components | 1,151 | 1,198 | +47 | 82 / 82 |

MAX mappings can differ by one or two generic gates after expression rewriting;
register counts match and sequential equivalence is proven. The additional
top/executor qualification logic is outside this isolated measurement. The
complete P06/P12 cost cannot be extrapolated from these numbers. Shared timing
control and tables keep the design economical, but subsequent instruction,
event, bus and integration stages still require cost and timing checks.

## Pause checkpoint and remaining work

User requested a progress summary and a pause on 2026-10-04. The final directed
run had completed successfully before process cleanup inspected it; no runner
remained to stop. No further development or synthesis starts until the user
asks to continue.

Remaining: full IU/lookahead model, memory and odd-word/data transactions,
I/O/INTA and ownership timing, instruction/event/PM coverage, complete DOS
timer/setup/return wrapper, all historical speeds and the public selector,
machine integration, complete FPGA cost/STA and later physical calibration.
The existing native 86Box 6 MHz and 12.5 MHz reference measurements with automatic
and overridden waits remain available. Physical collaborator results remain
pending and do not block provisional development against qualified references.

Reproduce only after resuming:

```sh
python3 scripts/run_p06_iu.py --output build/p06-iu-reproduce
python3 docs/evidence/p06-core-iu-20261004/audit.py --output build/p06-iu-audit
```

See [frozen evidence](../evidence/p06-core-iu-20261004/README.md).
