# Standalone SPK286 READY chaining synchronization

The standalone CPU milestone passes composed validation and independent
source/coverage review. It shares 40 exact functional RTL inputs, 20 literal
microcode inputs and both selected generated profiles with the vendor candidate.
Historical baseline contracts, receipts and modern standalone fixtures remain
unchanged.

Standalone ran 33 fresh stages including 355 Python tests, nine dual simulator
banks, profile generation/lint, 45 schedule checks, eight prefix cases and
43,878 metadata cases per simulator, reset/state smoke and four additional
Yosys checks. The 120 remaining common banks are credited from the vendor v3
gate by source, TB, vector and driver identity. Composed bank coverage is
129 Icarus and 128 Verilator. No literal full standalone `make regression`
execution is claimed.

[The fresh historical packet](../evidence/spk286-ready-chain-20261004/fresh-archive-manifest.json)
has manifest SHA256
`d1cd7f0b7341b1042e55335a52dc5d515fc148e7fbfc5820ca53eafa70b567b0`.
It preserves 133 artifacts, 1,079 source inputs, 33 stages and four first
sentinel probes. Its preliminary composed receipt remains historical;
`verify_fresh.py` verifies this packet without altering it.

[The final acceptance supplement](../evidence/p06-ready-chain-regression-20261004-composed/archive-manifest.json)
preserves the composed/native receipts and independent reviews alongside the
completed vendor regression, including the separate portable archive audit.

The final portable closure is stored in the SPK286 repository at
`docs/READY_CHAINING_20261004.md` and
`docs/evidence/ready-chaining-20261004/manifest.json`. Its manifest SHA256 is
`139077d1548db94560f95e5084481829cdb3bdeb66ff417de5d434e7ee569268`.
That packet stores 151 artifacts, complete standalone/vendor source bundles,
actual shared results and independent review receipts/helpers. Its verifier
needs only that directory. Composed receipt SHA256:
`9ca991145b1dcf55a0d7f2ee5603472286de8d653a9610c426de1cb296d27da7`.

The source, generated profile, required adapters and portable evidence were
committed in SPK286 as `4b4ec6ad99e936c5912a59f1f25cad3641730a12`.
All 168 staged files passed exact source/artifact SHA checks before the commit;
the standalone working tree is clean.

This CPU validation does not certify MiSTer/OS hardware, native 286 pin timing,
cycle accuracy or the five distinct historical release auditors. P06/P12
instruction profiles remain provisional.
