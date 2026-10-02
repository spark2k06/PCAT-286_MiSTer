# P16: measure overlapping write admission and launch

Date: 2026-10-02. PERF01 private candidate, authorized by the user.
Status: directed physical/control checks pass; unchanged 86Box CHECKNUM running.
No production RTL change, new synthesis or full regression at this milestone.
The user requested simulation in 86Box before measuring another FPGA fit.

## Control and motivation

[P15](P15_DATA_BUFFER_ASSOCIATIVITY_PLAN_20261002.md) has completed at
5525 / 102.4K in the private PCAT model and 5023 / 96.4K in the user-confirmed
MiSTer CHECKNUM observation. P15 mean data-read waits are 2.00059 / 2.10415 clocks,
while physical write waits are 7.24954 / 7.26504. Writes number 2,765,295 /
8,852,056 in its Dhrystone/Whetstone phases. Counts overlap internal execution;
one saved service clock is not a promised score increase.

The normal SDRAM owner accepts/captures a transaction, then launches KFSDRAM
on a later edge. This private prototype launches an ordinary write on its
accepting edge. It keeps one serialized retained transaction, the complete
physical write/recovery/precharge sequence and completion after KFSDRAM becomes
idle. Reads, code bursts and abstract refresh retain their original launch.
The controller, CAS/row timings, byte mapping, refresh parameters, CPU options,
4 KiB code and 1 KiB two-way data buffers remain unchanged.

The first write ACTIVE command must use the incoming accepted address;
subsequent column/data commands use the retained transaction. The prototype
therefore muxes the incoming canonical address only on write admission and
marks that physical command issued on the accepting edge. It does not report
completion before physical recovery. The new acceptance-to-ACT address path
has not been fitted or checked for FPGA/board timing.

## Completed directed evidence

[Evidence and reproduction patch](../evidence/perf01-write-admission-20261002/README.md)
retain the two private roots and their 15-file identity manifest. Only
`spk286_at_mister_sdram_owner.sv` differs between these roots; production
sources remain unchanged. Creation used commit `9d46e34`; subsequent P15
documentation/comparison-tool commits do not alter these input sources.

| Check | Control | Write-admission prototype |
| --- | ---: | ---: |
| Icarus physical byte/address scoreboard | PASS, 22 writes / 20 reads | PASS, same counts/values |
| Verilator physical byte/address scoreboard | PASS | PASS |
| Icarus bench finish time | 3,436,000 ps | 3,216,000 ps |
| Private adapter ordinary byte write | 7 wait clocks | 6 |
| Private adapter nonallocating write | 7 | 6 |
| Cached code/data hit | 2 / 2 | 2 / 2 |
| Code miss / data miss | 12 / 13 | 12 / 13 |
| Alias/update/invalidate/nonallocation/cancel smoke | PASS | PASS |

The bench uses a 10 ns clock: its 220,000 ps reduction is 22 clocks, one per
physical write. Physical reads, values and masks remain the acceptance checks;
the timing/control adapter itself leaves guest memory values in 86Box.
All private sources stayed unchanged through checking/building. Compiled CPU
objects exactly match the completed P15 control. The original 86Box/release
CPU objects and binaries were reused without modification.

## Current real-guest measurement and decision

Candidate binary: `build/perf01-write-admission-20261002/probe/86Box-memory-probe`.
Arm: `build/perf01-write-admission-20261002/pcat-write-admission/spk50`.
CPU 50 MHz, ISA 8 MHz, same initial disk/CHECKNUM/configuration/CMOS as P15.
CHECKNUM began at 2026-10-02 14:02:39 Europe/Madrid. Its complete scores are
pending; no partial score or FPGA cost is claimed.

1. Require guest RC0/ALL_DONE/final profile and retain any classified host teardown.
2. Compare rates and per-transfer waits against the completed 5525 / 102.4K P15
   control with CPU object/configuration identities enforced.
3. If the measured gain justifies continuation, promote a reviewable candidate,
   repeat the bounded composed coherence/cancellation checks, then freeze and
   synthesize it to report resources and all timing corners.
4. Commit each completed milestone. A full regression is a separate task.

Open-row SDRAM policy, refresh-cadence evaluation and a faster common-hit path
are later investigations. No such controller-policy change is in this prototype.
