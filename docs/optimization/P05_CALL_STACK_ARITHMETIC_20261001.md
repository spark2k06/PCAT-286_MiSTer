# P05 call-stack range arithmetic

## Contract

The PCAT 50 MHz fitted audit found a critical path from SP and call-gate
parameter count, through call-stack range checking and operand/control
qualification, to the IP/prefetch enables. This milestone changes only the
combinational call-stack arithmetic in `spk286_micro_executor.sv`.

The frame contains 4 base words, 0..31 parameter words and 0..2 event words.
Compute that count at 6 bits before converting to a 17-bit byte count:
the maximum is 37 words / 74 bytes. For nonzero N, the last parameter byte
is `SP + {N-1, 1'b1}`, computed at 17 bits, instead of two serial additions.
The existing N!=0 guard remains authoritative; the wrapped N=0 delta is
never used for a parameter-range decision.

The new stack retains the explicit `SP < frame_bytes` underflow check.
With that check, `SP-frame_bytes <= limit` is equivalent to
`SP <= limit+frame_bytes`. The sum cannot overflow 17 bits. The separate
`SP-frame_bytes > FFFF` check only detects underflow already covered by
`SP < frame_bytes`. Normal-stack `SP-2 > limit` similarly becomes
`SP > limit+2` under the retained underflow guard.

No register, microcode word, request handshake, fault priority or instruction
cycle is changed. This is a structural implementation change, independent
of the historical 80286 timing policy. It does not close an additional H story.

## Formal and directed validation

`scripts/prove_call_stack_arithmetic.py` extracts the actual assignments
from committed reference `2073e967cb7828f5c60dff57b5d15138848a1362` and the
candidate. It rejects changes outside the three new helpers and the two
proven assignments, including any sequential change.

Yosys SAT proves exact frame-byte and call-stack-fault equivalence for all
two-state inputs, without constraining parameter count, SP, limits, access
bits, readiness, event flags or mode. A deliberately incorrect last-byte
calculation is rejected by the same proof.

The bounded runner additionally checks the CPU with strict Verilator lint
and these existing executable banks in both Icarus and Verilator:

| Bank | Result per simulator/profile |
| --- | --- |
| Call stack precheck | 9 checks, passed |
| Protected outer event | 6 checks, passed |
| Call-gate accessed/transfer | 420 checks / 144 cases, passed |

Profiles are the default CPU and the exact PCAT P01 fast memory start,
P02 fetch chaining, P05 parallel limit checks and P06 early memory address
switches. Generated microcode consistency passes. Evidence is retained in
`build/call-stack-p05-production-20261001/`; this is not a global regression.

```sh
bash scripts/test_call_stack_arithmetic.sh build/call-stack-arithmetic-new
```

## Physical status

The executor was synchronized byte-for-byte into PCAT and compiled in the
fresh frozen `build/call-stack-arithmetic-fit-20261001/` run, with the actual
NO_DEBUG 20 ns profile, unchanged constraints and seed. Compilation completed
with 0 errors / 775 warnings; the all-corner extraction completed with 0
errors / 51 warnings. Those tool statuses are not a timing PASS.

| Corner | Global setup | Global hold | 50 MHz-domain Fmax |
| --- | ---: | ---: | ---: |
| Slow 100 C | -4.598 ns | +0.107 ns | 40.65 MHz |
| Slow -40 C | -4.057 ns | +0.006 ns | 41.57 MHz |
| Fast 100 C | +2.078 ns | +0.132 ns | 75.43 MHz |
| Fast -40 C | +2.350 ns | +0.076 ns | 89.11 MHz |

Recovery/removal are positive in all corners. The arithmetic change is a
verified structural milestone, **not completed CPU timing closure**. Compared
with the preceding keyboard fit, worst setup improves by 0.184 / 0.096 ns
in the two slow corners. Placement changes prevent attributing those small
differences solely to the arithmetic. A remaining 23-level path traverses
prefetch/decode, the operand register/memory mux, descriptor validation and
event error capture. That data-path qualification is the next CPU experiment.

The isolated RBF SHA-256 is
`3d7f20165453822f9eba0814c886e988f31d58337455162e3752f11c7f4754e6`.
The original root RBF is preserved. The downstream PCAT receipt retains the
complete fitted audit, source snapshot identity and directed proof hashes;
the standalone formal receipt is
[retained here](../evidence/call-stack-arithmetic-20261001/formal-receipt.json).

