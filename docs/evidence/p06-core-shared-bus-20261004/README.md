# Frozen P06 M6b shared CODE/READ evidence

Private real-fetch/queue/operand/BIU component acceptance. Production CPU,
MAX configuration and selected MiSTer RBF remain unchanged.

- `receipt.json`: source/generated hashes, tools, 972/8/107 directed case
  counts, eight MAX unit benches, 208-case full CPU MAX equivalence and scope.
- `shared/`: three dual-simulator summaries, logs and compressed edge traces.
- `original-max/`, `private-max/`: identical 208-case full CPU edge traces.
- Eight unit directories: affected fetch/queue/BIU/operand MAX compatibility
  under both Icarus and Verilator.
- `private-rtl/`: exact generated BIU/fetch and default-MAX CPU source.
- `max-*-gold.sv`, `max-*-equivalence.*`: golden original components expose
  ignored private inputs; formal gate inputs remain arbitrary. MAX generic
  netlists additionally require all private control cones to be absent.
- `generic-*.json`, Yosys scripts/logs: isolated cost calculation.
- `negative-owner-run.log`: physical-READY owner release is rejected by
  `shared logical owner oracle failed`.
- `negative-scope-run.log`: invalidated CODE publication is rejected by
  `CODE publication oracle failed`.
- `ancestral-*-acceptance.json`: preservation audits of M3/M4/M5/M6a evidence.
- `audit.py`, `freeze.json`, `acceptance.json`: reproducibility and byte checks.
  `*.csv.gz` are lossless edge traces; original uncompressed hashes remain in
  the receipt. Frozen CSV summaries retain explicit case/phase/guard labels.

Summary kinds:

| Kind | Meaning |
| --- | --- |
| 0 | 972 CODE→DATA / DATA→CODE combinations; each requires same-Tc handoff |
| 1 | Paused CODE publication permits DATA progress |
| 2 | Held accepted DATA and occupied result slot permit CODE progress |
| 3 | Real operand caller pause retains DATA while CODE progresses |
| 4 | Caller/fetch metadata poisoned after acceptance, both directions |
| 5 | Selected-client cancellation in six phases, both clients |
| 6 | Six prohibited services in six phases, both clients |
| 7 | Queue full/near-full, DATA progress, then CODE resume, both alignments |
| 8 | Four-packet CODE stream interleaved with DATA |
| 9 | Fresh pair after resetting the scope context |
| 10 | Opposite-client cancellation in five phases, including PUBLISHED |
| 11 | Reset in six phases, both clients |

`direction=0` starts CODE; `direction=1` starts DATA. Lifecycle phases are
0=before admission, 1=late physical service, 2=before early READY,
3=after early capture, 4=exact Tc/READY, 5=PUBLISHED with paused consumer.
Guards are 0=ACK, 1=HOLD, 2=LOCK, 3=write, 4=I/O, 5=odd-word DATA.

```sh
python3 docs/evidence/p06-core-shared-bus-20261004/audit.py --output build/p06-shared-audit
```

See [the milestone report](../../optimization/P06_CORE_SHARED_BUS_PILOT_20261004.md).
This evidence establishes component shared logical ownership, not full CPU
memory instruction timing, consecutive DATA reuse, odd words, writes, I/O,
bus/events, full speed profiles, complete FPGA cost, fit or STA.
