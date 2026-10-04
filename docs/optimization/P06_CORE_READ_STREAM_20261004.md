# P06 M6d — consecutive aligned A1 qualification

Date: 2026-10-04. Status: directed acceptance PASS; frozen audit PASS.
This extends the evidence for the [M6c CPU](P06_CORE_MEMORY_CPU_PILOT_20261004.md),
without changing its generated RTL, storage, timing policy, production config
or selected RBF. It qualifies the existing serialized handoff, not removal
of the DATA IDLE/empty-slot gap or exact Intel IU issue phasing.

## Scope and independent inputs

Programs contain two, four or eight consecutive prefix-free Real Mode A1
aligned word reads. Caller inputs independently define CS/DS/IP, initial
registers/FLAGS, each offset/value, abstract CODE waits, and each READ's waits
and physical response class. Repeated addresses retain one stable memory
value. Cases include AX already equal to the first loaded value, repeated
identical reads, alternating addresses, both code alignments, segment carry,
and early, exact-Tc or deliberately late responses.

Each READ must accept, capture and publish exactly once, at its own address,
and write its own value to AX. Original TMP0/MOVE defines functional readiness.
The independent oracle requires the first eligible commit, preserved FLAGS
and other GPRs, IP advancing three bytes per retirement, and an independent
budget `5 + this READ's actual extra waits`. The previous READ's value, wait
budget, raw slot or canceled response cannot satisfy the next instruction.
CODE/DATA ownership, mandatory DATA admission, first eligible Tc, queue
capacity/reservations and byte order remain checked every observed edge.

## Pauses, cancellation and recovery

Directed controls pause before/after DATA capture and between retirements,
redirect/reset at accepted DATA or retained TMP0, and stop on HOLD scope.
Redirect recovery first drains the canceled physical work, consumes the
original automatic redirect fetch through its external response interface,
and requires no old owner, pending response or raw slot. It then changes
CS/IP and memory values and seeds the next program through original external
ports **without reset**. Reset and HOLD-scope recovery use explicit reset.
All recovered sequences must complete in full with the new memory values.

This is a sparse normalized backend fixture, not DMA/volatile-memory timing
or a measured physical AT. The observed serialized A1-to-A1 gap is preserved
and is not promoted to an Intel-required delay.

## Acceptance gates

All gates below pass. The 23 dual trace pairs contain 825 timed programs and
3,794 per-instruction retirement records. The CPU's seven generated modules
are byte-identical to the frozen M6c selection. No production RTL is changed.

- 240 programs / 1,120 instructions, both warm and cold.
- 19 selected programs in nine control modes, both warm and cold; 1,548
  per-read retirement records after normal continuation or full recovery.
- Three two-read programs with READY/final Tc on the first instruction's
  deadline; six retirements and next-boundary retained-result commit.
- Original/private MAX executes all 240 programs with identical edge traces.
- Both simulators must produce byte-identical traces and summaries for all
  23 CPU trace pairs. Summary GPR/FLAGS/IP is recorded at each actual retirement.
- Timing bypass, dropped wait accounting and corrupted retained payload must
  fail three distinct independent oracles.
- Strict CPU lint, microcode consistency, source guards and exact generation
  against the frozen M6c receipt must pass.

No new RTL is introduced: **incremental hardware cost is zero**. This is an
additional qualification of the existing implementation, not a new Quartus
measurement. The [production cost baseline](PCAT_RESOURCE_BREAKDOWN_20261004.md)
and the separate odd-word candidate remain unchanged by this milestone.

```sh
python3 scripts/run_p06_read_stream.py --output build/p06-read-stream-reproduce
python3 docs/evidence/p06-core-read-stream-20261004/audit.py --output build/p06-read-stream-audit
```

[Frozen evidence](../evidence/p06-core-read-stream-20261004/README.md) binds
sources, generated CPU, exact vector coverage, dual traces and negative controls.
No full regression, fit, STA, DOS wrapper or new RBF is part of this milestone.
Next qualify the odd-word candidate's two physical/logical READ phases and
alignment correction before advancing to writes and read/modify/write.
