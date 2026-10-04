# P06-M3: full CPU register timing pilot

Date: 2026-10-04. Physical 6/12 MHz calibration remains `NOT_MEASURED`.
This follows the [component pilot](P06_PILOT_PROGRESS_20261003.md) and
[Intel timing contract](P06_TIMING_CONTRACT_20261003.md).

## M3a: observe the existing functional engine

`scripts/run_p06_core_register.py` executes the actual full SPK286, with its
decoder, microsequencer, executor, BIU and prefetch queue. An independent
Python oracle supplies instruction bytes and expected GPR/defined FLAGS.
The 208 cases cover 13 encodings of 16-bit ADD/XOR/CMP register forms and
ADD/XOR immediate forms, four register seeds, even/odd code placement and
two normalized READY policies: continuous completion or a pulse every five
fabric edges, with varied phase. Each case starts with an empty queue.

| Form | Continuous READY: dispatch to retirement, 50 MHz edges | Periodic READY: edges |
| --- | ---: | ---: |
| ADD/XOR/CMP register/register | 2–3 | 2–6 |
| ADD/XOR register/immediate | 3–6 | 6–11 |

These are **functional service intervals**, not Intel instruction clocks.
The tested functional dependencies fit within the 6 MHz table minima of
2/3 processor clocks respectively. This does not prove that arbitrary
backends meet those deadlines, or certify bus/fetch timing.

Both simulators produce identical per-edge and final-state traces. Strict
full CPU `-Wall` lint and microcode freshness pass. A negative control flips
one expected result bit and is rejected by the architectural comparison.
Evidence is frozen in
[`observation`](../evidence/p06-core-register-20261004/observation/receipt.json).
All text artifacts from the run are retained; generated simulator executables
are omitted and can be rebuilt. The receipt also records their original hashes.

### Actual architectural milestones

The optimized register and immediate paths already capture operands into
existing executor state and fuse GPR/FLAGS updates with retirement. There
is no earlier GPR/FLAGS write in these tested forms. Retaining that state
until an authorized commit can avoid a second result buffer.

The current register IP is a decode cursor: it advances as opcode, ModRM
and immediate bytes are consumed, before retirement. A timed pilot must
distinguish that internal cursor from the instruction's architectural IP.
The event unit already retains the instruction start IP. This may serve as
the published IP while the instruction is pending, without a second 16-bit
register. Exception/event consumers must continue using the correct cursor
and saved instruction context.

## M3b scope

Connect start, retained result and architectural commit in one private
full-CPU pilot, preserving an independently checked MAX path. Qualify only
the register forms above in Real Mode without prefixes. Unknown opcode,
ModRM, mode or event coverage must stop explicitly before architectural
side effects; it must not silently run with zero timing cost.

The pilot will validate instruction minima and commit ordering. Historical
Ts/Tc fetch publication, decoded-instruction lookahead (P06-IU01), complete
event timing, memory/branch forms and the complete T286REF wrapper remain
later gates. No production speed profile or new RBF is implied by M3a.

## M3b: private connection validated

`scripts/build_p06_register_cpu.py` checks the frozen production CPU hashes
and applies exact, single-match hooks to **one selected CPU source list** in
an ignored build directory. There is no committed functional CPU clone.
The existing decoder/microcode/datapath still own instruction semantics.
The production QIP, vendored CPU, 86Box integration and RBF remain unchanged.
Reproduce the directed acceptance under WSL with:

```sh
python3 scripts/run_p06_timed_register.py --output build/p06-register-fresh
```

The private parameter `P06_REGISTER_PILOT` defaults to MAX bypass. In the
pilot, opcode admission occurs at a 6 MHz virtual boundary. The retained
executor `register_pending_q` is exposed independently of execution enables:
it is set only after accepted register ModRM or the final immediate byte.
Gate actual executor progress and micro-operation completion while that
record waits for its 2/3-clock deadline. The real ALU, original completion
checks and existing GPR/FLAGS write paths execute at the permitted commit.
No second result slot, functional engine, queue or clock domain is added.

The published `debug_ip` holds the event unit's saved start IP while the
timed instruction is active, then publishes the final byte cursor with
GPR/FLAGS/retirement. All internal cursor consumers, including event context,
retain the original byte cursor semantics. Redirect/reset cancels both the
retained functional candidate and temporal ownership.

Scope tags classify already available opcode bytes only for temporal
qualification. 81/83 ADD and XOR share the three-clock cost class; the existing
functional decode chooses the actual ALU operation. Register ModRM and group
0/6 are checked before consumption. Other opcodes, byte forms, prefixes,
memory operands, groups, PM and event entry stop with an explicit development
diagnostic. They do not receive a zero-cost historical fallback.

### Directed acceptance

| Evidence | Result |
| --- | --- |
| 208 ordinary cases in the full CPU | Exactly 2 clocks for register/register and 3 for register/immediate; correct GPR/defined FLAGS/IP |
| 13 deliberately slow dependency cases | 6 still fit because their bytes are present at dispatch; 7 immediate cases extend by 9/10 clocks until the real bytes arrive |
| 65 lifecycle cases | Pause, malformed controller transaction, redirect, reset and pending NMI retain/cancel state correctly |
| 7 scope stops | Unknown opcode, prefix, byte form, memory ModRM, non-ADD/XOR groups and forced PM stop before architectural writes |
| Four consecutive ADD AX,BX | Correct dependent results and flags; each instruction's minimum is 2 clocks; one additional dispatch clock between instructions is exposed |
| Original MAX versus hooked MAX | Identical per-edge and final-state traces for all 208 cases |
| Existing MAX banks using the hooked CPU | Register execution 78 cases; immediate execution 184 cases; timing-policy equivalence 63 checks |
| Timing-gate bypass mutation | Rejected before the first premature write, even though the functional result would be correct |
| Lint and microcode freshness | Strict full CPU `-Wall` in MAX/pilot, and current microcode, pass |

Icarus and Verilator traces match in every pilot scenario. The normal pilot
run records 1,175 physical bus completions outside CPU boundaries: READY
capture/fetch service remain on fabric edges rather than being clock-divided.
Deliberately late dependencies are **implementation extensions**, not board
wait corrections. No physical-board policy is inferred from the test READY
pulses. Event tests demonstrate pending NMI and the completed saved IP,
then stop before untimed event entry; they do not certify interrupt latency.
The PM test forces PE as a qualification fixture, not a timed LMSW execution.

The additional dispatch clock in the repeated ADD stream is a real coverage
gap. The current decoder has no three-entry decoded-instruction queue and
does not admit the next instruction on the retirement edge. This belongs to
**P06-IU01**; M3b proves isolated instruction minima and commit ordering,
not Intel steady-state stream throughput.

### Cost and limits

The exact connection included by `p06_register_policy_cost` maps in generic
Yosys synthesis to **22 register bits / 284 generic cells**, including the
clock generator and three diagnostic reason bits. MAX maps to **zero bits /
zero cells** for this control fixture. Full CPU MAX elaboration also prunes
the entire temporal generate branch. This is not whole-CPU synthesis or an
ALM/placement/STA estimate; the fixture exposes normalized dependency/control
inputs and preserves diagnostic outputs. Adoption still requires actual
FPGA resource/timing measurements.

Additional nominal profiles share this execution/timing logic. The planned
upper named profile is **25 MHz**, followed by **MAX** for the current
dependency-driven maximum throughput. A common denominator of 50 can emit
the required 2x phase events from the existing 50 MHz fabric using a slightly
wider accumulator and speed selector. That is a small incremental logic
proposal, not a measured ALM cost. No new PLL/domain is needed. Faster profiles
still require directed deadline checks: selector reuse cannot prove their
functional/backend work fits the shorter virtual periods.

Frozen evidence:
[`timed receipt`](../evidence/p06-core-register-20261004/timed/receipt.json),
[`audit`](../evidence/p06-core-register-20261004/audit.py).
The audit verifies all frozen text/netlist artifacts, reconstructs the private
CPU from unchanged production sources and checks actual minima/MAX equality.

M3b is complete for this private register subset. Historical BIU/fetch Ts/Tc,
IU lookahead, branches/memory, complete event/PM coverage, the DOS timer/setup/
return wrapper, physical collaborator calibration and full FPGA cost/STA
remain open. No long global regression or Quartus fit was run for this milestone.
