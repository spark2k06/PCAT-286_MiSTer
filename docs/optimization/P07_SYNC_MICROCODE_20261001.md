# P07: synchronous microcode ROM with unchanged CPU cycles

## Motivation and implementation

Fresh PCAT fits repeatedly start limiting CPU paths at micro_pc, followed
by three microcode-ROM LUT levels and operation decoding. P07 replaces
that combinational case-ROM implementation with a synchronous embedded
ROM. The compiler emits a separate portable initialized array module;
the asynchronous module remains the default. No generated file is hand
edited. Compiler 27.1 changes the implementation artifacts, retaining
encoding/format 27, every entry, branch target and control word.

The sequencer exposes next_micro_pc, the exact address its existing PC
register takes at the next edge. The new ROM samples that address at the
same edge. After the edge, its word and valid bit therefore equal the
old asynchronous ROM at the committed PC. Stalls retain the same address;
reset/cancel, start, completion, retirement, conditional branches and
invalid addresses retain their original priorities. The sequencer's
existing state updates and output qualifications are unchanged.

This adds ROM read state but no CPU idle state, speculative execution,
extra micro-operation or cycle. CPU dependency and admission/completion
handshakes remain unchanged. The initial CPU reset edge samples address
zero, establishing alignment; outputs before the first clock are not
claimed equivalent to the asynchronous ROM's power-up outputs.

The initialized array is requested as M10K through ramstyle. See the
[Quartus RAM/ROM style guide](https://docs.altera.com/r/docs/683283/18.1/quartus-prime-standard-edition-user-guide/ram-style-and-rom-style-for-inferred-memory).
Actual primitive inference, memory initialization and physical timing
must be checked in the downstream compiled project.

## Exact proof and directed validation

The proof uses actual RTL against c554585. It guards all unrelated CPU
RTL and all original sequencer state updates, microcode constants,
branches and asynchronous ROM contents. It proves the predicted PC
equals the previous committed next-state function for every two-state
control/state combination at the actual 10-bit/743-word sequencer depth,
as well as 10-bit/1024 and 4-bit/10 generic dimensions. A
second proof compares the actual initialized synchronous ROM with the
committed asynchronous contents after one clock, for arbitrary addresses.
Cancel omission and a changed first ROM word are rejected as negative
controls. The first unconstrained pre-clock state is skipped explicitly.

These properties compose inductively: once both CPUs are reset and
aligned, unchanged CPU logic observes identical control words, produces
identical next state, and the next ROM sample preserves alignment.

Both simulators pass the direct ROM/sequencer comparison: 107169 checks,
all 743 valid and 281 invalid words, and 100000 deterministic arbitrary
control cycles. Existing sequencer and asynchronous-ROM units also pass.
The 112 compiler tests and independent encoding/entry/branch/source
round-trip audit pass. Strict CPU Wall lint is empty in base and
P01/P02/P05/P06/P07 profiles. Five CPU banks pass in both profiles with
Icarus and Verilator: microcode execution, 96 event streams, call gates,
LOADALL integration above 1 MiB and CPU double faults. Their expected
results are unchanged. Evidence: docs/evidence/sync-microcode-20261001.

No full CPU regression or MiSTer test was run. The first downstream fit
is pending, so this is a functionally verified implementation checkpoint,
not a claim of physical 50 MHz closure or higher CheckIT scores.

## Proof depth clarification

The original formal evidence checked a full 1024-address sequencer and
the 4-bit/10-word generic case. The physical ROM has 1024 storage addresses,
but the real sequencer's MC_DEPTH is 743. The checker now derives that
depth from the actual generated package and proves 10-bit/743 as well.
The additional actual-depth-formal evidence preserves the original logs
and repeats both negative controls. This is a verification-scope correction;
no CPU, ROM image, control transition or cycle behavior changed.

## PCAT integration

Upstream commit: `88f9fef18bca1b7354a88596ebcb17a813cf1fb5`. P07 is enabled in config.tcl and discovered
by the simulation profile's existing performance-macro reader. The new
generated module is listed in the CPU QIP. Generator, portable source
list, lint list, sequencer unit and generated artifacts are synchronized;
the vendor compiler's byte consistency check passes. The sole real-mode
wrap_ip binding is retained.

Actual vendor production Wall lint is empty. Call-gate/accessed and CPU
double-fault banks pass with both simulators. Every metric in the eight
physical-owner CheckIT fixtures is identical to the previous CPU. The
first preparation attempt lacked the new generated vendor file and failed
before Quartus compilation; it supplies no timing evidence. The corrected
fresh snapshot is sync-microcode-real-core-output-fit-02-20261001.

## Compiled ROM check

The mapped primitive is a 1024x9 M10K ROM, with no additional registered
data output. Its actual initialization file matches all 743 valid control
words and all 281 invalid addresses against the frozen independent CPU
encoding contract. The checker rejects a changed first word and an added
output register. Evidence includes the losslessly compressed original MIF
and primitive-parameter receipt in compiled-rom. This checks mapping and
contents; the full physical setup/hold audit is still pending.

The additional proof at the real 743-word sequencer depth is recorded in
upstream 792f652 and copied under actual-depth-formal. The initial generic
1024/10-word proofs remain preserved. No RTL changed in that audit update.
