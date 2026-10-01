# P05: registered entry to the physical SDRAM owner

Date: 2026-10-01. Scope: the AT owner admission/launch boundary. KFSDRAM
refresh policy, command sequencing, clock phase and physical address mapping
are unchanged.

## Boundary and latency

The owner stores the request payload at admission and launches KFSDRAM from
that record on a later edge. Address, data, burst length and byte lanes are
sampled whenever the entry is idle, avoiding the long combinational admission
enable on payload registers. `active_q` then freezes the record; `issued_q`
distinguishes an admitted request from physical work already launched.

Admission conditions are unchanged. A write may complete only after launch;
reads forward the same ordered beats and signal ready on the last beat. An
upstream request withdrawn after admission cannot change the accepted record.
A physical reset clears both stages, including a request admitted before it
has launched. An AT refresh acknowledgement still waits for physical idle;
KFSDRAM's periodic refresh remains enabled independently.

The usual physical launch costs one extra 50 MHz cycle. A periodic refresh
which wins the controller between admission and launch may add further wait.
This is a timing pipeline with a measured cost, not a performance speedup.

## Directed validation

`scripts/test_at_sdram_entry.sh` runs strict owner lint with only the recorded
legacy KFSDRAM timescale, width, unused-signal and unused-parameter warning
classes waived. The CPU lint remains strict without these waivers.

The new pin-model bench runs in Icarus and Verilator at a 20 ns clock with
CL2, a finite 6 ns read-data arrival and 3 ns read-data hold, and frequent
periodic refresh. Both report:

```text
SDRAM_ENTRY_PASS checks=79 beats=6 refresh=1 stable_payload=1 burst=1 reset=1
```

It corrupts and withdraws every live request field after admission, checks
ordered four-beat reads and ready only on the final beat, low/high byte masks
on MiSTer A11/A12 wiring, reset between admission and launch, retained RAM
contents across reset, and rejection of a zero-lane request.

The existing owner bank passes 22 writes / 20 reads in both simulators. The
RAM-buffer and CPU/DMA/loader pipeline banks pass their coherence, refresh,
burst and reset cases. That pipeline bank has an ideal backend; physical
owner evidence comes from the pin-model bench and workloads below.

## Workload A/B measurement

Only the owner RTL differs between the independently compiled baseline and
candidate in `build/owner-entry-baseline-20261001` and
`build/owner-entry-candidate-20261001`. Both retain the same CPU and cache
options. Each of the four fixed workloads passes with P03 both off and on.
The production P03-on comparison is:

| Workload | Baseline cycles | Entry cycles | Extra cycles |
| --- | ---: | ---: | ---: |
| CheckIT Dhrystone | 826081 | 845438 | 2.343% |
| CheckIT Whetstone | 682866 | 701469 | 2.724% |
| Working set | 913639 | 956222 | 4.661% |
| Dhrystone 2.1 | 897746 | 917710 | 2.224% |

Architectural result signatures, retired instructions, completed bus reads/
writes and physical SDRAM read/write counts match in all four production
P03-on pairs above. With P03 off, signatures, retired instructions and writes
still match; total reads can differ because the counter includes speculative
code reads. Three P03-off physical read counts differ by 13, 622 and 152,
respectively. Speculative fetch counts can change with the extra latency.
These fixed-work cycle counts are not DOS benchmark scores or measurements
on MiSTer.

## Fitted evidence

The new Quartus run `build/protected-data-sdram-entry-fit-20261001` contains
this boundary and the formally equivalent CPU protected-data bypass. It uses
the inherited external SDRAM constraints, before the separately documented
hold-budget correction. Its pin hold results therefore cannot certify the
corrected external budget. Full CPU regression and MiSTer validation remain
outside this directed milestone.

Fitted results (ns), with the inherited SDRAM budget:

| Corner | Global setup | Global hold | Owner setup | SDRAM output setup |
| --- | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -4.229 | +0.107 | +1.741 | +8.904 |
| 7_slow_1100mv_-40c | -4.053 | +0.003 | +1.848 | +9.154 |
| MIN_fast_1100mv_100c | +2.124 | +0.120 | +8.805 | +12.754 |
| MIN_fast_1100mv_-40c | +2.379 | +0.053 | +9.334 | +13.572 |

RBF SHA-256: `379d280aa429761828722e3ff72509c692e51ae3ec2d24da03a0efed6f6d8beb`. Owner incoming setup is now positive
in both slow corners, from -1.819/-2.047 ns previously to +1.741/+1.848 ns.
The remaining CPU critical path still has 23/21 logic levels through
operand completion, descriptor form validation and error-word capture.
All constrained recovery/removal checks remain positive.
