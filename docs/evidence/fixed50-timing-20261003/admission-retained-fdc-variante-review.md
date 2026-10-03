# Independent review: admission baseline with retained FDC writes

**PASS within the declared functional scope.** Sources and existing results were read only. No new proof, compilation, simulation, synthesis, test, production or Git change was performed.

## Variant binding

The reference is fixed50-active-address-seed1-fit-20261003/work, the previous best admission snapshot. The candidate overlay contains exactly seven files: six retained FDC transformations and the unchanged FIFO. All seven source hashes were checked. The current proof tool's pure string transformations reproduce the exact candidate text. Original admission statements remain intact. The new bridge view adds no registers; grant-qualified transport reaches the FDC write path, while the general read address and read pipeline remain unchanged.

## Existing results checked

- All 212 formal artifacts match. Active1 and default0 each cover COMPLETE0/1: 104 actual state groups, 784 bits, all 46 original public outputs without masks, full next state, matching full memory descriptors and actual 1024 by 8 FIFOs. Reset and transition proofs pass; four real write-address mutations produce next-state mismatches. Default0's six added inputs are arbitrary primary inputs disconnected from bridge outputs.
- All six portable directed cases and 240 recorded inputs were rehashed, including raw models, binaries, logs and paired CSVs. Fixture hashes are current: 9f407ddd... and 0478b4db....
- The CPU and machine snapshot contains 1,239 source and fixture files per tree, based on the previous best admission snapshot. Exactly the six retained RTL files differ between before and after. Queue, CPU, data buffer, SDRAM port, SDRAM owner and config match that best snapshot byte for byte. Queue SHA7a53a407... remains the binary-head implementation; data buffer SHAe6724ac5... remains the original capture implementation. No onehot, eager or factored additions are present.
- The machine test and ROM expectations remain unchanged. Its driver only adds assertions and two compile jobs; the optional real PIC bank is disabled. Runtime logs are byte-identical: 114 memory beats, 15 I/O writes, 35 IRQ0 events, two refresh events and four port80 checkpoints.

## Decision

The candidate and its existing evidence are correctly tied to the previous best source. No unexpected accumulated optimization was found. This is suitable as the last candidate for the pending physical comparison. Timing closure, resource cost and hardware behavior are not established by this review. Preserve the best completed physical result and align final code to the selected result after that comparison; do not expand candidates or tests.
