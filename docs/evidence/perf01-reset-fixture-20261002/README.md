# 286 warm-reset fixture correction — 2026-10-02

The old stress ROM contained a 386 near conditional jump. At `F000:010A`,
NASM encoded `jne failure` as `0F 85 08 02`: the target exceeded the short-jump
range and the source had no CPU restriction. An 80286 must reject that opcode,
even when the branch condition is false.

Both the frozen original bridge and the PERF01 response candidate executed the
first IRQ0 handler and IRET correctly, then wrote and read the odd word `A55A`
correctly. CMP left ZF set. The next instruction raised #UD (vector 06); its
uninitialized vector sent execution to `0000:0000`.

The old test only required one IRQ entry and some cache/refresh activity before
forcing reset. It could therefore report PASS while the CPU was executing
zero-filled RAM. The original bridge reached COMPLETE there, whereas the
candidate's direct memory response used WAIT and never reached the requested
COMPLETE trigger. A prolonged original-bridge run also escaped into RAM. This
was a faulty fixture and an insufficient test oracle, not a CPU defect or a
new bridge data-corruption regression. The original observations are retained
under `original/`.

## Correction and checks

- Declare `cpu 286`, compile with NASM `-Wall -Werror`, and express the long
  error branch as JE short followed by JMP near. The deliberate #UD at the
  failure target remains explicit bytes.
- Initialize the loop counter. Require at least two IRQ entries and two loop
  iterations, alongside the existing refresh and cache hit/miss evidence.
- Fail immediately if execution leaves the fixture's ROM segment, halts, or
  completes any exception/event other than IRQ0 vector 20h.
- Keep reset states 0/4/5/6, and add trigger 8 for the memory READY protocol
  boundary. This checks either a registered COMPLETE response or a direct
  response in WAIT without prescribing the implementation latency.

Both original and candidate RTL pass all five reset cases with identical
corrected tests and firmware. The original records four IRQ handlers and 38
loop iterations before each reset; the candidate records four handlers and
43 iterations, or 49 for state 6. In trigger 8, the candidate is in WAIT with
an accepted memory transaction and READY asserted; the original is in COMPLETE.
Both resume at the reset vector and return at least 16 post-reset fetches.

The strengthened test also rejects the **unchanged old ROM** on both bridges
with `CODE_BUFFER_RESET_STRESS execution escaped fixture`. Those negative logs
and the executable/ROM hashes are under `negative/`.

## Evidence and reproduction

`baseline/` and `candidate/` contain the five case logs, runner output, frozen
source manifests, effective compiler flags, configuration hashes, and successful
source-integrity checks. `branch-disassembly.txt` shows the old and corrected
instruction bytes; `rom-hashes.json` identifies the executed ROMs.
`receipt.json` records the verified observations and source identities.
`files.sha256` covers every other file in this directory.

Run the corrected fixture from the desired source tree with:

```sh
PCAT_CODE_BUFFER_RESET_DIR="$PWD/build/code-buffer-warm-reset" \
  bash scripts/test_at_code_buffer_warm_reset.sh
```

The baseline validation used the original frozen RTL plus these four test-only
changes. The candidate used the same inputs with the bridge response change.
No production CPU, device, or SDRAM RTL was changed to repair this fixture.
This evidence is a directed functional reset check; it does not establish FPGA
timing closure or replace the separately deferred full regression.
