# Retained FDC on the admission baseline

Status: **PASS** for the complete portable proof, all six directed cases and actual CPU/machine smoke before/after.

The overlay starts from the exact seven files in fixed50-active-address-seed1-fit-20261003/work. Only the six intrinsic retained-FDC transformations are applied. The bridge retains the original at_valid/at_io/at_inta admission expressions and adds the retained combinational record. FIFO bytes are unchanged. CPU, data buffer, queue and config remain the original best snapshot in the machine comparison.

Formal proof covers active1 and default0 in both COMPLETE modes, 104 actual registers/784 bits, all original public outputs and full next state, full memory geometry and the stated FIFO interface composition. All four actual write-address mutants are rejected. In default0 the six newly added inputs remain arbitrary shared primary inputs, disconnected from bridge outputs; no protocol assumption is imposed. Common initial unreset registers and memories are the equivalence relation.

The six Icarus/Verilator directed runs preserve all observed public outputs without masks, including warm reset, split beats, memory/IDE exclusions, malformed lanes and FIFO writes during reset. Actual raw source models are copied from this proof with no formal state cuts. Traces are identical before/after within each simulator.

Machine Icarus elaboration, production lint and Verilator runtime pass with the unchanged bench/ROM. Runtime signatures remain identical: 114 memory beats, 15 I/O writes, 35 IRQ0 events, two refresh events and four port80 checkpoints. The existing modeled PIC is used. These bounded checks are not a full regression, historical timing measurement, global machine equivalence, resource fit or hardware validation. No synthesis, production, Git, config or documentation change was made by this work.
