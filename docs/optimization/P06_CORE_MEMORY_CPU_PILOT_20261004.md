# P06 M6c — real aligned A1 READ in a private full CPU

Date: 2026-10-04. Status: private directed acceptance passed; public profiles
and physical AT calibration remain pending.
This connects the [M5 register handoff](P06_CORE_IU_HANDOFF_20261004.md)
and [M6b shared CODE/READ ownership](P06_CORE_SHARED_BUS_PILOT_20261004.md)
to an actual memory instruction. Production RTL selection, `config.tcl`,
MAX operation and the selected MiSTer RBF remain unchanged.

## Functional path and temporal scope

The only new qualified instruction is **prefix-free Real Mode A1**,
`MOV AX,[moffs16]`, with an aligned word in DS. The private builder composes
hash-pinned ancestors and selects one functional CPU. It does not replace
the instruction with a synthetic dependency or instantiate a second CPU.

The existing microcode fetches the immediate offset into TMP1, calculates
the DS address, performs the real READ into TMP0 and reaches `MC_MOVE`.
The original retained TMP0 supplies AX. The final MOVE writes AX and retires
at the first permitted virtual boundary; there is no new payload buffer.
This private shortcut skips the original functional END after MOVE.
With all pilot parameters zero, MOVE/END and every MAX dependency retain
their original behavior.

The [identified Intel MOV row](P06_INTEL_TIMING_REFERENCE_20261003.md)
provides the five-processor-clock minimum. The duration budget is
`5 + actual qualified extra READ waits`. CODE starvation and late physical
memory responses remain functional dependencies; they are not counted again
as external board waits. A response captured exactly on the deadline cannot
retroactively supply TMP0 before that edge: commit occurs at the next eligible
boundary. This establishes a lower bound and explicit dependency behavior,
**not exact Intel EU issue phasing or a complete historical speed profile**.

The physical clock stays at 50 MHz and the private virtual clock remains
6 MHz through the existing 3/25 enable. Physical READY can be captured at
any fabric edge. Publication and bus ownership follow the qualified Ts/Tc
lifetime, independent of the timing of the physical response.

### READ waits without a combinational enable loop

Full CPU integration initially exposed a feedback path from executor enable,
through request-derived bus scope, back through READ waits to duration permit.
The new duration export therefore observes **already accepted DATA in Tc**,
cancel/reset state, sticky scope and board READY. It does not depend on a
new request-derived combinational scope condition. Top-level qualification
also requires the retained A1 instruction context.

On the exact edge of a new HOLD scope violation, that accepted context may
export one wait while the stricter BIU publication diagnostic exports zero.
Publication and architectural commit are suppressed, and the invalid context
is never accepted as a temporal measurement. Sticky scope suppresses later
waits. A redirect/cancel suppresses both exports and drains any accepted
physical transaction. Directed cases explicitly distinguish these situations.

`P06_MEMORY_PILOT` requires REGISTER and FETCH timing. Invalid combinations
are rejected. The accepted connection also enables IU handoff; other mixed
pilot selections do not gain acceptance from these results.
No public config option or OSD entry is added.

## Directed acceptance

The runner requires two simulators and byte-identical edge traces and summaries.
Its sparse physical memory comes from independent caller CS/DS/moffs/value
inputs, including segment carry above 1 MiB, both instruction alignments,
offset FFFEh, zero/FF/byte-lane payloads and varied registers/FLAGS.
State is seeded through existing external ports; no internal force or queue
prefill hook is used.

- 267 aligned A1 inputs, both warm and cold: abstract CODE/DATA waits 0/1/2,
  early READY, off-boundary capture, READY at Tc and deliberately late service.
- Paused EU, controller error, redirect, reset and HOLD before or after the
  real DATA acceptance or retained TMP0 result.
- Waits while EU is paused; READY/Tc exactly on each 5+wait deadline;
  HOLD and cancellation on the first waited Tc.
- Explicit unsupported prefix, write and odd-word guards. Odd-word guard
  inputs exclude FFFFh, which would first cross the Real Mode segment limit
  and enter the separately unqualified event path. FFFEh remains in aligned
  acceptance; this exclusion does not waive a functional fault.
- Actual `ADD BX,AX` to A1 and A1 to `ADD BX,AX` streams. Warm RR to A1 reuses
  M5's same-edge handoff; A1 to RR remains serialized and consumes the newly
  loaded AX. That gap is not certified as an Intel timing property.
- 267 original/private full CPU MAX A1 traces; 208 register MAX traces;
  eleven affected MAX unit benches; 688 M5 RR/RI streams and 1,448 instructions
  in both warm and cold modes, compared byte for byte with the frozen CPU.

Independent oracles require exact DATA address, lane, retained payload,
instruction bytes, logical first eligible DATA admission/Tc, queue reservations,
and first eligible AX commit. Commit readiness is derived from original
`MC_MOVE` and valid TMP0, not from the new pending export or duration permit.
GPRs, FLAGS and architectural IP must remain unchanged until the qualified
commit. The budget is checked against `5 + observed READ waits` every legal
edge. CODE issue and ownership retain M6b's qualified component contract.

Negative controls remove commit timing, change the minimum to six clocks,
drop READ wait accounting, invert the TMP0 pending export, and instantiate
three invalid parameter combinations. Each must fail its specified assertion;
simulator agreement or a final correct AX alone cannot pass acceptance.

Strict MAX/timed full CPU lint, generated microcode consistency and MAX
BIU/fetch sequential equivalence are required. Private inputs remain arbitrary
in the component proofs, and their synthesized MAX cones must be absent.

### Accepted results

Both simulators pass **1,782 timed CPU cases**: 534 aligned warm/cold cases
and 1,248 directed cases. All 48 CPU trace pairs are byte-identical. The
aligned matrix captures 1,698 responses outside virtual boundaries. Warm
A1 duration ranges from 5 to 12 processor clocks; cold duration from 6 to 30,
including explicit fetch and physical dependency delays. These ranges describe
the controlled fixture, not benchmark rates or universal instruction timing.

All seven negative controls fail their required markers. Original/private
MAX memory and register traces match, all eleven MAX unit benches pass,
and both warm/cold M5 preservation comparisons match. Strict lint,
microcode consistency and component sequential equivalence pass.
Preservation audits of M3/M4/M5/M6a/M6b also pass and are stored with the
accepted receipt. Production config/source selection and the user's existing
dirty test script remain unchanged.

## Isolated cost, not whole FPGA overhead

| Isolated component | Original/MAX generic cells | Original/MAX register bits | Timed generic cells | Timed register bits |
| --- | ---: | ---: | ---: | ---: |
| BIU | 504 | 88 | 546 | 78 |
| Fetch | 508 | 98 | 605 | 102 |
| New executor pending/retire assignments | 0 | 0 | 11 | 0 |

The last row maps the actual new assignments, not an estimated model. It
excludes complete top-level A1 decode/scope, clock/duration, context wiring and
sharing. The new READ wait export adds six generic cells to M6b's isolated
BIU, with no additional register bits. Unsupported services are still pruned;
net register reductions do not establish FPGA savings. These are Yosys
generic mappings, **not Quartus ALMs, a complete CPU delta, fit or STA**.
No new RAM depth, response slot, owner bank, queue or PLL is introduced.

The [production cost baseline](PCAT_RESOURCE_BREAKDOWN_20261004.md) remains
the selected previous fit. OPL2 remains enabled; the user's config-only
resource fallback is reserved for a future fit that needs it.

## Reproduction and remaining gates

```sh
python3 scripts/run_p06_memory_cpu.py --output build/p06-memory-reproduce
python3 docs/evidence/p06-core-memory-20261004/audit.py --output build/p06-memory-audit
```

The final [frozen evidence](../evidence/p06-core-memory-20261004/README.md)
binds sources, generated CPU, dual traces, negative controls and isolated
netlists. Earlier M3/M4/M5/M6a/M6b evidence remains immutable.

Consecutive DATA reuse, odd-word beats, writes and buffered-write overlap,
read/modify/write, I/O, INTA/HOLD/LOCK/refresher service, branches, PM/events,
decoded IU lookahead, the full DOS wrapper and all public historical speeds
remain separate milestones. There is no new DOS benchmark, total regression,
Quartus fit, STA or RBF here. Native 86Box remains an identified contrast to
the Intel contract; physical 6/12 MHz collaborator calibration is still pending.
