# P06 M6f frozen A3 WRITE checkpoint

Directed full-CPU acceptance and independent frozen audit: PASS.
This is private 6 MHz virtual Real Mode, prefix-free A3, retaining serialized
WRITE response and END. Historical write-buffer EU overlap remains open.

- 834 matrix cases warm/cold; 556 lifecycle cases; three final-Tc cases.
- 2,227 timed cases, 47 byte-identical Icarus/Verilator trace pairs.
- Original/private MAX: 834 cases each, exact trace equality.
- M6e READ: 834 cases per temperature, exact frozen trace preservation.
- Eight rejected mutants; four affected MAX units; lint, microcode,
  sequential component bypass proofs and private-input cones: PASS.
- Isolated BIU/duration delta: +13 generic cells, +1 control bit. No new
  payload/queue/PLL. Not Quartus ALMs or complete CPU/FPGA cost.
- Cancellation preserves accepted WRITE effects and drains remaining halves;
  reset interrupts the original backend and can leave a partial word.

`receipt.json` pins caller/source/generated/artifact bytes. Its SHA256 is
`89e91b391a0ef829290594099cf9ce03a9fd666ba1028c4b7f160e356eacbb65`.
`freeze.json` pins frozen artifact encodings and the final auditor. Edge
traces are lossless gzip; the receipt retains their uncompressed hashes.
`acceptance.json` records the independent audit result.

```sh
python3 docs/evidence/p06-core-write-20261004/audit.py --output build/p06-write-audit
```

[Specification and limits](../../optimization/P06_CORE_WRITE_CPU_PILOT_20261004.md).
Production config, source selection and selected RBF are unchanged. No total
regression, fit, STA, public-speed acceptance or physical calibration here.
