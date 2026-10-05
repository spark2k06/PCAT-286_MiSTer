# P06: general fetch turnaround correction

## Result and measurement boundary

The reproduced T286REF R0 inversion is removed in the composed production CPU
and PCAT memory simulation. The original workload bytes, logical 20/25 MHz
profiles, Intel instruction minima, bridge Ts/Tc policy and physical 50 MHz
clock are unchanged. Only the general fetch pipeline and its queue reservations
change. This is a simulation result; the new hardware measurement is pending.

The previous baseline is [the frozen unchanged-RTL diagnosis](P06_R0_PHASE_DIAGNOSIS_20261004.md),
commit `1a4f2ec`. Counts below span opcode admission to final LOOP retirement
for 256 iterations; they exclude DOS/PIT measurement instrumentation.

| Composed PCAT path | Previous fabric clocks | Corrected fabric clocks | Elapsed change |
| --- | ---: | ---: | ---: |
| 20 MHz baseline LOOP | 5,110 | 5,110 | 0 |
| 25 MHz baseline LOOP | 4,088 | 4,088 | 0 |
| 20 MHz R0 | 11,530 | 11,525 | -0.043% |
| 25 MHz R0 | 12,300 | 9,734 | -20.862% |

Corrected R0 at 25 MHz takes 15.54% less elapsed time than 20 MHz. Its own
throughput improves by 26.36%; this does not predict the same gain in CHECKNUM
or every workload. The ideal RAM reference is unchanged: R0 takes 11,509 clocks
at 20 MHz and 9,719 clocks at 25 MHz. PCAT is now only 15 clocks above the
ideal 25 MHz case instead of 2,581.

Both 32- and 256-iteration workloads check instruction counts, register/FLAGS
signatures, stack preservation and byte mapping. In the warm fabric-edge window
350–1400, the corrected PCAT traces have no physical SDRAM READ command, HOLD
edge or AT refresh grant. The 25 MHz R0 iteration takes 38 fabric clocks instead
of 48; 20 MHz retains 45. Corrected CODE completion intervals are 4/6 clocks at
25 MHz and 5 at 20 MHz.

## General mechanism and safety contract

On the current fetch's READY edge, the fetch unit may prepare the following
address in its existing transaction registers. It offers that request to the
bus only when the previous response can leave its single staging slot. Thus
the bridge can observe the next request one physical edge earlier without
anticipating READY, adding another response slot, or overlapping uncompleted
bus transactions.

This is a synchronous internal offer: acceptance is sampled at the fabric
posedge. Once that edge sees a visible request, the preceding response has
left the slot and the request remains stable until READY. A manual component
caller can change the combinational offer before sampling by withdrawing its
response grant; this is explicitly exercised by the backpressure fixture.
Production `response_ready` comes from the registered queue occupancy/count,
and the reservation guarantees capacity for that preceding response. The
optimization does not change the CPU's native external bus interface.

The CPU grants a request only when the six-byte queue can reserve its current
contents, staged response, outstanding maximum two-byte beat and proposed
maximum two-byte beat. Reservation is conservative for odd/last-byte fetches.
A prepared but invisible request is discarded on redirect; an already visible
request is drained and its stale response discarded. Reset/redirect retain
priority. Byte lanes, protected limits, real-mode IP wrap and suspend admission
retain their existing meaning.

The static component parameter `READY_CHAINING` preserves the default component
fixture contract; the standalone CPU explicitly enables it. It is not a new
user configuration or OSD option. Production profiled CPU RTL is regenerated
from that same functional CPU. The generator records the two explicit updated
functional source hashes and preserves every other accepted dependency hash;
historical private-pilot receipts remain unchanged.

## Validation

- Strict original and production profiled Verilator lint.
- Existing fetch unit in both simulators: 32 bus/response checks.
- New enabled-path bank in Icarus and Verilator: 16 cases, 3,609 checks, 802
  cycles, 231 completed requests, 230 delivered responses, one stale drained
  request and 411 ordered bytes through the actual six-byte queue. Includes
  READY held high during backpressure, visible/invisible redirects, lane/limit/
  wrap cases, reset, suspend and reservations. The disabled-chain negative
  control fails the intended early-admission assertion. Only five uninitialized
  fields in the first pre-reset row differ between simulators; the other 801
  raw rows compare exactly.
- Existing integrated dual-simulator prefetch fidelity: 1,190 records, 45 CODE
  completions/responses, 61 consumes, six-byte maximum, stale response and HLT
  resume checks.
- Original R0 bytes: 16 ideal dual-simulator runs and eight composed PCAT runs,
  plus raw CPU/backend trace analysis and source identity checks.
- Integrated PCAT diagnostic passes at MAX, 6, 8, 10, 12.5, 16, 20 and 25 MHz.
- Full profile compatibility: all 26 CPU banks cover all eight profiles, with
  202 Icarus runs, 64 Verilator runs and 26 original/profiled MAX comparisons.
  The 26 MAX pairs match complete raw streams; 58 paired simulator runs match
  the declared canonical streams. Six exhaustive IOPL profiles run in Verilator
  without a paired Icarus trace. IOPL Icarus MAX/25 and all eight Verilator runs
  retain all 2,772 cases/49,334 assertions. An independent unchanged M2 auditor
  verifies the 26 MAX pairs and 130 negative integrity checks.
- The first complete-matrix attempt hit a 300-second host timeout in IOPL at
  6 MHz; it is preserved as incomplete, not accepted. Completed source-frozen
  banks are recovered from their full stream digests, normal terminal PASS logs
  and byte-identical generated fixtures. Remaining banks finish in fresh shards;
  the IOPL host limit is 900 seconds with architectural assertions unchanged.
- The frozen vendor CPU's unchanged `make regression` completes with exit code
  zero and `REGRESSION PASS` in 66 minutes 54 seconds. All 130 Icarus and 129
  Verilator banks pass; the existing full expand-down matrix remains Icarus-only.
  The 297 Python tests include the 114 microcode tests, rather than adding them
  to the unique count. Reset/state smoke, four external SingleStep smoke groups
  (80 + 20 + 400 + 470 = 970 cases), strict lint, microcode consistency and Yosys
  sanity pass. This is not the exhaustive external SingleStep corpus or an OS
  regression.
- Only 70 exact, source-bound Verilator compilations are reused from the failed
  previous run; 59 are compiled fresh. All functional simulations, vector
  generation, Icarus compilation and final stages execute again. The compile
  cache has one positive and 16 rejection controls. All 581 frozen CPU files,
  98 original corpus inputs, cache tools and reused binaries match before/after
  hashes, with every drift/error list empty. An independent final auditor
  rechecks source/corpus identity, every stage and all 70 cache hits/59 misses.

[Directed evidence](../evidence/p06-ready-chain-20261004/manifest.json) preserves
1,898 artifacts and 331 source identities. Raw R0/fetch traces and logs are
compressed with deterministic gzip. Full profile streams are represented by
their complete raw/canonical hashes and byte/row counts plus bounded prefix/tail
samples, as explicitly declared by the runner; those samples are not used as
comparison inputs. The final fit binding includes the source identities actually
frozen in the candidate snapshot.

The first `make regression` stopped in pre-existing microcode Python failures
before any RTL test. Those stale fixture contracts were already recorded in
[the October 2 regression report](P18_P19_FULL_REGRESSION_20261002.md). Their
separate repair preserves historical fixtures byte-for-byte, translates only
the explicitly asserted old LOADALL/SALC controls, and retains the negative
protocol checks. It also exposed a compiler validation hole for a LOADALL entry
with its service token removed. The entry-name guard is repaired separately;
generated microcode/ROM bytes do not change.

The next broad attempt passed all 8,184 AAM/AAD architectural comparisons,
then stopped at the bank's final radix-byte starvation coverage assertion.
Earlier fetch completion meant its original zero-to-three-clock CODE READY
delay no longer exercised that condition. Only the memory stimulus now adds
16 clocks to CODE READY (`bus_status=4'hD`); DATA/INTA waits, all vector
expectations and the starvation assertion remain intact. The focused rerun
passes in both simulators with 1,764,540 checks and 16,352 immediate stalls.
All architectural comparisons and the starvation assertion remain exercised.

The [broad regression supplement](../evidence/p06-ready-chain-regression-20261004/archive-manifest.json)
preserves both failed attempts, the successful frozen run, generated vectors
and ROMs, cache provenance/controls and independent final review. It supplements
the sealed directed and fit packets without rewriting their earlier receipts.

The standalone SPK286 project receives the same CPU/fetch correction and
regenerated profile RTL, preserving its historical baseline contract. Its 33
fresh native gates pass, including all 355 Python tests and nine affected or
distinct banks in both simulators. Independent review accepts a source-bound
composition covering its 129 Icarus/128 Verilator bank registry: 120 common
banks use the completed vendor run, and the nine selected banks execute again.
No literal full `make regression` run in the separate repository is claimed.
The small native execution adapters now check actual #UD acceptance and saved
fault context after their MOV vectors, rather than an obsolete local sentinel
latch. No ROM, CPU pin interface or historical receipt is replaced.
The [standalone synchronization report](SPK286_READY_CHAIN_SYNC_20261004.md)
records its source commit and separate fresh/portable evidence boundaries.

## Cost and remaining limits

Isolated fetch synthesis with the same Yosys frontend and mapping retains
98 flip-flop bits. Generic mapped cells change from 508 to 670 (+162). This
does not include the caller's reservation sum and is not a Cyclone V ALM count.

The full all-features fit preserves the accepted floppy build's config, SDC,
PLLs and seed. The ROM audit confirms the same 743 valid/281 invalid words in
one 1024 x 9 M10K. Docker compilation and detailed four-corner STA finish in
37:46; both owned containers are gone. The source-bound preliminary fit audit
passes integrity and reports `MEASURED_FIXED50_TIMING_FAIL`, as expected from
the existing timing debt. The final fit audit binds the 331 directed validation
inputs and reports the same physical margins. Standalone regression acceptance
remains separate from measured timing failure.

| Full fitted machine | Accepted floppy build | READY-chain candidate | Difference |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 31,278 | 30,881 | -397 |
| Placed ALMs | 36,619 | 36,395 | -224 |
| Placed device utilization | 87.38% | 86.84% | -0.53 percentage points |
| Registers | 38,073 | 37,994 | -79 |
| Block memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K / DSP / PLL | 416 / 39 / 3 | 416 / 39 / 3 | 0 |
| Inclusive CPU equivalent ALMs | 7,280.9 | 7,228.2 | -52.7 |
| Inclusive CPU placed ALMs | 8,101 | 8,025.5 | -75.5 |
| Inclusive CPU registers / M10K | 5,351 / 1 | 5,350 / 1 | -1 / 0 |

These are actual fitted results, not a guaranteed portable saving from the
new gates. Placement, packing and optimization change the global totals; the
isolated generic cell count and fitted ALM attribution measure different things.

Worst margins across the four corners, in ns:

| Group | Setup | Hold |
| --- | ---: | ---: |
| Global | -15.190 | +0.058 |
| CPU | -15.190 | +0.121 |
| CPU to bridge | -8.014 | +0.327 |
| Bridge to CPU | +0.331 | +0.276 |
| SDRAM input | +5.185 | +5.000 |
| SDRAM output | +4.626 | +0.221 |

Global/CPU setup improves from -16.531 ns, but CPU-to-bridge setup worsens from
-5.899 ns. There is also a -0.009 ns HDMI setup summary entry. **This candidate
does not close physical 50 MHz timing.** SDRAM margins retain their inherited
conditional device/flight-time scope. The worst CPU path is queue `head_q[2]`
to `gpr_q[80]` (34.469 ns data delay); the worst CPU-to-bridge path is queue
`count_q[1]` to bridge `STATE_WAIT` (27.296 ns). Raw full-path reports remain
available for the separate closure work.

Candidate RBF:
`build/p06-ready-chain-allfeatures-20261004-v1/work/output_files/PCAT-286.rbf`,
4,124,316 bytes, generated 2026-10-04 19:37:43 Europe/Madrid, SHA256
`6b0b1dd42f756908298b076a12210630e6a1b0d314950635b391ba0c87ec37f1`.

The residual R0-minus-baseline average is 10.0234375 nominal clocks per
iteration at 20 MHz and 11.02734375 at 25 MHz, close to ideal 10/11. The extra
XOR-immediate implementation interval at 25 MHz remains. These subtractions
are not isolated EU execution cycles. P06/P12 remain provisional historical
timing profiles; the explicit Ts epoch/admission contract and broader physical
286 comparisons are still separate work. No frequency multiplier, shortened
instruction minimum, retroactive Tc credit or new timing exception is added.

Physical 6/12 MHz captures describe one motherboard, including its memory and
READY policy. They are useful coherence checks alongside Intel's CPU/bus
contract and explicitly configured 86Box references. Future profile work must
not tune every benchmark to that board's exact result: even the register-only
R0 kernel depends on instruction delivery. After hardware confirmation, check
profile coherence and prioritize the outstanding physical timing closure.

## MiSTer follow-up

Select 20 MHz and apply **Reset & apply settings**, then run the unchanged
`T286REF 20 > NEW20.CSV`. Repeat at 25 MHz with `T286REF 25 > NEW25.CSV`.
The first target is the gross R0 median, previously 298 ticks at 20 MHz and
316 at 25 MHz; retain the whole CSV so B0/M0/signatures are checked too.
CHECKNUM at 20/25/MAX is complementary mixed-workload evidence, not a substitute
for the local R0 check. No new DOS executable is required. This candidate also
retains the hardware-confirmed floppy fix and existing write protection.

The [all-profile hardware follow-up](P06_MISTER_READY_CHAIN_RESULTS_20261005.md)
now validates336 new MiSTer samples with strict adjacent-profile ordering.
It confirms the25MHz R0 correction and preserves MAX CHECKNUM. The recorded
6/8MHz M0 penalties remain investigation items; no calibrated board wait or
pin-exact historical timing is inferred from those aggregate measurements.
