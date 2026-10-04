# P06 M6g frozen bounded XOR word RMW checkpoint

Directed full-CPU acceptance and independent raw/frozen audits: PASS.
Private 6 MHz virtual Real Mode, prefix-free `81 36 disp16 imm16`.
The original READ/ALU/WRITE/COMMIT_FLAGS dependency is retained; FLAGS and
retirement share the first qualified boundary after the physical store.

- 858 matrix cases warm/cold, 784 lifecycle controls and three final-Tc cases.
- 2,503 timed cases; 67 byte-identical Icarus/Verilator trace pairs.
- Original/private MAX: 858 cases each, exact trace equality.
- Frozen A1/A3: 834 cases each per temperature, exact trace preservation.
- Register streams: 688 programs/1,448 instructions per temperature preserved.
- Nine exact rejected mutants; four MAX units; lint and microcode PASS.
- Component bypass proofs and private-input cones PASS. Executor formal
  coverage is the extracted real commit fragment, not the full executor/CPU.
- BIU byte-identical to M6f; measured isolated increment +20 generic cells,
  +0 register bits. No new payload/queue/PLL. Not FPGA ALMs/full CPU cost.

The retained ModR/M level adds four clocks once to the three-clock RI
admission. Each odd READ/WRITE adds two; only READ waits charge the EU budget.
The fastest observed serialized paths take eight/twelve clocks, so the
seven/eleven-clock minimum is nonbinding there. The permit mutant detects
boundary bypass, not removal of only that minimum check.

Trace lanes/events/commit intent are PREedge; architecture, scope and form-count
are POSTedge. A first invalid HOLD edge may show a pre-edge form diagnostic
with post-edge scope and zero accepted form-count. Neither FLAGS nor retirement
is accepted on it. Cancel drains accepted work; reset may leave partial writes.

`receipt.json` pins source/generated/caller/artifact bytes. SHA256:
`bea128ff050368abccd6572d588b04db7faa156e3f7ff50d11f350fa6d64d7d1`.
`freeze.json` pins encodings and the final auditor. Edge traces are lossless
gzip; uncompressed hashes remain in the receipt. The independent frozen result
is retained in `acceptance.json`.

```sh
python3 docs/evidence/p06-core-rmw-20261004/audit.py --output build/p06-rmw-audit
```

[Specification and limits](../../optimization/P06_CORE_RMW_CPU_PILOT_20261004.md).
Production config, source selection and selected RBF are unchanged. Historical
write-buffer overlap, arbitrary forms/events, public speeds, full regression,
fit, STA and physical calibration remain outside this milestone.
