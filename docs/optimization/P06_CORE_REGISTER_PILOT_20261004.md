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
