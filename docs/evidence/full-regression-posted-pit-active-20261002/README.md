# Active-options regression evidence

The complete run is retained under
`build/full-regression-posted-pit-active-20261002`. It freezes the PCAT sources
and uses only P01/P02/P05/P06/P07 enabled from `config.tcl`. Initial failures
and later replays are separate records; no initial result is overwritten.
The complete regression is still running when this first receipt is recorded.

## Restored verification package

`restored-unit-package.json` records 23 upstream unit banks missing from the
vendored package despite registration in `scripts/test_units.sh`. Every bank
passed Verilator and Icarus against the frozen PCAT CPU and generated microcode
with active options. The receipt identifies upstream revision, exact test
bytes, unchanged CPU hashes, commands and original log hashes. The validated
test files are restored under `vendor/spk286/sim/unit`; existing files and
architectural assertions are preserved. No production RTL is changed.

The full suite also finds historical compiler fixtures and diagnostic-script
issues. The package restoration is a verified coverage repair, not an overall
regression PASS or hardware acceptance. Those results are recorded separately
when the complete run finishes.

## Completed verification repairs

`verification-repairs/receipt.json` retains the original and corrected logs
for all 20 CPU mutation families, the canonical source-manifest tests, event
arbitration, architectural memory-work comparison, SDRAM admission/phase checks,
XTIDE and code-capacity manifests, and active-profile stack-offset validation.
The RTL, generated microcode and configuration byte hashes remain unchanged.

The event arbitration bank independently rejects the owed-TF-priority mutant
without depending on a real-mode instruction fetch that wraps correctly at
FFFFh. Unary, segment and ESC mutants remain rejected by exact functional
assertions that now execute before the old expected messages; compile failures
and arbitrary nonzero exits are not accepted as functional rejection.

The memory workload retains all data traffic, retired work, GPRs, FLAGS, CS/IP
and a complete initialized memory signature. Only speculative code-read counts
may vary with the native prefetch path. Dedicated negative controls reject
changes to each architectural field or to the required physical-store count.

The SDRAM bank now explicitly requires writes to enter KFSDRAM on the accepting
edge, while reads/refresh retain their entry stage. It still corrupts upstream
payload after acceptance, checks all read data/byte writes/burst order, and
asserts reset before registered pin commands cannot leak a write. Both
simulators pass 90 checks at the common phase and at a 3 ns chip advance.

The stack-offset replay supplies the already committed proof omitted by the
runner's initial snapshot, verifies its source/artifact hashes and runs only
the requested active profile with both simulators. These successful repairs
do not waive the separate unresolved MRBIOS restart or compiler-fixture checks.
