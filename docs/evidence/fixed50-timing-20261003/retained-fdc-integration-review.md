# Retained FDC integration review

**PASS; no blocking finding.** Independent read-only review; no recompilation or production changes.

- The original A5 IBM5170 FDC command, management, DMA and result-assertion block is retained exactly. Actual CPU bridge, grant qualification, router/storage/FDC, DMA controller and bus arbiter are connected. Candidate retained-write parameter 1 is confirmed in compiler metadata and Icarus parameters.
- Every one of the 512 accepted sector byte has exact address, lane and payload checks. Four IV/VLT runs each complete 49 CPU commands and one terminal count. Full event traces and runtime logs match before/after; IV/VLT event traces also agree. Source manifests, binaries, build logs, fixture, driver and frozen hashes were rechecked.
- Machine smoke uses the frozen one-hot CPU before and precisely six ready FDC files after. Original bench expectations and ROM are unchanged; the runner adds only assertions and two build jobs. Icarus elaboration, production lint and Verilator runtime pass. Identical logs report 114 memory beats,15 I/O writes,35 IRQ0 events,2 refresh events and4 port 80 checkpoints.
- All source-origin, copied-input and receipt hashes agree. The recorded fit build_id.v update is shared operational metadata. Ready differs from the A5 prototype only in the two approved comments; its full portable proof was repeated separately.

## Limits

A5 uses an explicit CPU bus driver, inherited 10 ns functional clock and original DMA sink handshake; it does not execute SPK286 instructions or model physical SDRAM pins. Only the original FDC initial bank runs. Machine smoke executes the real CPU with its existing modeled PIC and memory testbench; Icarus is elaboration-only there. This is bounded directed evidence, not global machine equivalence, full regression, STA or hardware validation. The JSON companion records verified hashes. The comparison boundary is frozen before/prototype/ready snapshots, before promotion of the six root RTL files.
