# Frozen P06 M6d consecutive aligned READ evidence

Directed acceptance PASS for the exact seven-module M6c private CPU. No new
RTL or hardware is introduced; production selection/config/RBF is unchanged.

- 240 programs of two/four/eight A1 reads, 1,120 instructions per warm/cold run.
- Nine lifecycle controls, warm/cold, including redirect recovery without
  reset and full sequences using changed CS/IP and memory values.
- Three deadline programs; original/private MAX traces identical.
- 23 byte-identical dual trace pairs; 825 timed programs/3,794 retirements.
- Three specified negative failures for permission, wait and payload errors.
- Lint, microcode, source guards and exact M6c reconstruction pass.

`receipt.json` pins caller inputs, sources, generated CPU and raw artifacts.
`freeze.json` pins the losslessly compressed traces and auditor. `audit.py`
checks every retirement/architectural trace, exact coverage and mutant source;
`acceptance.json` records its result. The initial unaccepted freeze preceded
the auditor's final log-parser adjustment; this checkpoint was regenerated
from the same accepted build after the auditor was frozen.

```sh
python3 docs/evidence/p06-core-read-stream-20261004/audit.py --output build/p06-read-stream-audit
```

This preserves the existing serialized DATA handoff. It does not accept
exact Intel issue phasing, odd words, writes/RMW, events, complete public
profiles, physical calibration, FPGA fit/STA, a total regression or a new RBF.
See [the report](../../optimization/P06_CORE_READ_STREAM_20261004.md).
