# P06: reproduced R0 slowdown at 25 MHz

The general follow-up correction and its separately measured results are
recorded in [P06_READY_CHAIN_CORRECTION_20261004.md](P06_READY_CHAIN_CORRECTION_20261004.md).
The evidence below remains the unchanged-RTL baseline.

## Result

The original T286REF R0 workload reproduces the user's 25/20 MHz inversion
on unchanged production CPU and PCAT RTL. With the actual memory chain, 256
iterations take **11,530 physical clocks at 20 MHz** and **12,300 at 25 MHz**:
25 MHz is **6.68% slower**. The user's repeated CSV shows **6.04%** slower
gross elapsed time. The measurement boundaries differ, so these are close
corresponding observations, not identical measurements.

The inversion appears with warm code-buffer hits and **no physical SDRAM
reads, AT refresh grants or HOLD** in the measured steady interval. The
identified cause is fetch turnaround interacting with the historical bridge
admission window. A wrong MHz selection or a slow physical SDRAM response is
not needed to explain this local behavior.

This milestone changes diagnostic benches, scripts and evidence only. It
does not change RTL, the instruction timing table, MAX, config, OSD or RBF.
The floppy RBF separately received the user's hardware confirmation.

## Exact workload and measurement

NASM assembles the unchanged `SW/CPUTIME/t286ref.asm`. The harness retains
the complete COM and the original kernel locations:

- CS `106E` is the CSV's **4206 decimal**, physical segment base `0106E0`.
- Baseline IP `0488`: `E2 FE C3`.
- R0 IP `048B`: `01 D8 31 FA 83 C3 01 81 F7 AA 55 E2 F3 C3`.
- The R0 loop body is 13 bytes; the fourteenth byte is RET.
- AX/BX/DX/DI start at `1234/5678/9ABC/DEF0`; CX is 32 or 256.

A real reset-vector jump and executable setup replace DOS initialization.
The count spans admission of the first kernel opcode to retirement of the
last LOOP. It excludes initial fetch before that opcode, CALL/RET and PIT
instrumentation. Each run checks architectural results and fixed work; the
composed bench additionally checks restored SP and exact instruction count.

Both use a physical 50 MHz clock. The production selector applies profile 6
(20 MHz) or 7 (25 MHz) through reset. No divided physical clock is introduced.

### CPU with immediate RAM

The production wrapper, profiled CPU and scheduler run against an immediate
READY peer. Icarus and Verilator agree on all eight measurements and the
applicable passive trace values. Three initial rows contain four derived
values that depend on an invalid empty queue; their simulator X/zero
differences are recorded explicitly in the receipt. Raw traces are preserved.

### Composed PCAT

The production AT machine and serialized memory port are followed by literal
instances extracted from `PCAT-286.sv`: P03 with 512 lines, data buffer, posted
write buffer and owner/KFSDRAM. Posted-write fencing is connected. A guarded
fixture uses the existing behavioral SDRAM command/data peer and shortens
only owner initialization. It models each READ command of a logical fill;
it does not validate SDRAM electrical margins, read DQM, MRS or tAC/tOH.

The CLI workload leaves PIT/DMA refresh unprogrammed and disables AT refresh
requests; owner SDRAM maintenance stays active. The PIC model is a fixture
substitution; no interrupt is taken. This is directed CPU/memory diagnosis,
not a DOS, BIOS, OS or complete peripheral regression.

## Measurements: 256 iterations

| Path | Nominal profile | Baseline fabric clocks | R0 fabric clocks | R0 elapsed | Conditional R0 minus baseline clocks/iteration |
| --- | ---: | ---: | ---: | ---: | ---: |
| Immediate RAM | 20 MHz | 5,109 | 11,509 | 230.18 us | 10.000 |
| Immediate RAM | 25 MHz | 4,087 | 9,719 | 194.38 us | 11.000 |
| Composed PCAT | 20 MHz | 5,110 | 11,530 | 230.60 us | 10.031 |
| Composed PCAT | 25 MHz | 4,088 | 12,300 | 246.00 us | 16.039 |
| MiSTer CSV | 20 MHz | 142 PIT ticks | 298 PIT ticks | gross instrumented sample | 10.214 |
| MiSTer repeated CSV | 25 MHz | 118 PIT ticks | 316 PIT ticks | gross instrumented sample | 16.205 |

The final column converts subtracted counts using the nominal frequency.
It includes fetch/admission and implementation effects; it does not isolate
EU execution clocks. The published EU minima remain ADD reg 2, XOR reg 2,
ADD immediate 3, XOR immediate 3, taken LOOP 8, final LOOP 4.

Immediate RAM does not reproduce the inversion: R0 elapsed time at 25 MHz
is 15.55% lower. It does expose one implementation extension per iteration at 25 MHz,
on XOR DI,55AA. Its functional completion reaches the deadline too late for
the same boundary. This is a separate smaller implementation cost.

With PCAT, 32-iteration retirement traces report two extensions per iteration
at 25 MHz: ADD BX,1 and XOR DI,55AA. At 20 MHz only four cold extensions
appear. The code queue's refill schedule, rather than changed metadata,
accounts for the sustained extra cost.

## Confirmed bridge/fetch sequence

The following are pre-update values at physical edges from the synchronized
CPU/backend traces. Tc begins as a result of the listed edge update.

| Event | 20 MHz example | 25 MHz example |
| --- | ---: | ---: |
| Previous CODE READY | 310 | 322 |
| Previous fetch response consumed | 311 | 323 |
| Next request admitted | 312: window, no boundary | 324: window and boundary |
| P03 response ready | 313 | 325 |
| First following boundary starts Tc | 313 | 326 |
| Next CODE READY | 315 | 328 |
| Service interval | 5 fabric clocks | 6 fabric clocks |

Fetch registers the previous response at READY. On the next edge it consumes
that response and registers a new request. The bridge sees the request two
physical edges after READY. At 25 MHz this is exactly a new CPU boundary;
the newly admitted transaction is not yet active when Tc is evaluated.
Tc starts on the following boundary, and terminal READY on the next.
At 20 MHz the request can enter through the admission window before the
next boundary, which starts Tc sooner in physical time. No Tc tick is lost.

In the common warm edge window 350–1400:

| Profile | CODE READY intervals | R0 iteration interval | Physical READ / HOLD / AT refresh |
| --- | --- | ---: | --- |
| 20 MHz | 140 intervals of 5, 23 of 7, 23 of 8 clocks | 45 fabric clocks | 0 / 0 / 0 |
| 25 MHz | 174 intervals of 6 clocks | 48 fabric clocks | 0 / 0 / 0 |

The longer 20 MHz gaps include redirect/refill at LOOP. R0 returns to an odd
IP, requiring a single-byte initial fetch, then two-byte beats. This makes
the 13-byte body sensitive to CODE throughput even with all hot P03 hits.

## Interpretation and next implementation boundary

The bridge implements its current admission/Tc/terminal sequence. Its window
can nevertheless credit an implicit earlier virtual Ts epoch for a request
that becomes physically visible between boundaries. If admission itself is
treated as literal Ts start, the 20 MHz example finishes less than two full
nominal periods later. The present trace therefore does not establish that
the favorable 20 MHz phase is historically correct. P12 still needs an
explicit Ts epoch/admission contract. `timing_deadline_miss` alone does not
count this delay before admission.

Do not compensate 25 MHz with a multiplier, shorten Intel budgets, or mark Tc
complete retroactively. The general optimization to investigate is reducing
fetch turnaround so the next request becomes visible earlier, preserving
the response slot, queue capacity/reservation, single outstanding request,
redirect/cancellation priority, limits/wrap, byte lanes and real dependencies.
That CPU change needs affected BIU/prefetch tests and the required regression
before a production RTL commit. Its timing/resource cost must be measured;
this diagnostic has not implemented or synthesized such a change.

CHECKNUM's mixed workload can still improve at 25 MHz: 4,361 to 5,023
Dhrystones (+15.18%) and 84.1K to 91.9K Whetstones (+9.27%). The repeated R0
sequence exposes a localized throughput penalty, not a general wrong clock.

## Reproduction and archived evidence

Run under WSL from the repository root:

```sh
python3 scripts/trace_p06_r0_ideal.py --output build/p06-r0-ideal-new
python3 scripts/trace_p06_r0_pcat.py --output build/p06-r0-pcat-new
python3 scripts/analyze_p06_r0_trace.py --ideal-dir build/p06-r0-ideal-new --pcat-dir build/p06-r0-pcat-new --output build/p06-r0-pcat-new/analysis.json
```

The runners require fresh output directories and enforce hard process-group
timeouts. Successful receipts bind compiled inputs, workload and raw traces.
The composed observer samples CPU and backend signals in the same process,
with one counter. The final LOOP's `in_kernel` flag is cleared before writing
that row; analysis includes the receipt's final edge and checks every retire.

`docs/evidence/p06-r0-phase-20261004` preserves the successful v3 receipts,
raw traces/logs as deterministic gzip, exact program images/listings, generated
composed bench, analysis and a hash manifest. Recompute archived results:

```sh
python3 scripts/analyze_p06_r0_trace.py --ideal-dir docs/evidence/p06-r0-phase-20261004/ideal --pcat-dir docs/evidence/p06-r0-phase-20261004/pcat --output build/p06-r0-archived-analysis.json
```
