# Bounded emulator reference — 2026-09-09

The reproducible CPU-only experiment in `research/phase7_emulator_reference.py`
executes original functions from 86Box revision
`3a8953d0fee171a98500ca69d5b4e9905c07272d`. The sources and GPL-2.0 license remain
in an ignored reference cache; selected function extracts and the complete
license remain in the ignored experiment directory. No reference implementation
is imported into synthesizable CPU sources.

The [CPU selection](https://github.com/86Box/86Box/blob/3a8953d0fee171a98500ca69d5b4e9905c07272d/src/cpu/cpu.c)
chooses `exec386_2386` and the 2386 286 opcode tables. Its
[execution loop](https://github.com/86Box/86Box/blob/3a8953d0fee171a98500ca69d5b4e9905c07272d/src/cpu/386.c)
defines `OP_TABLE(name)` as `ops_2386_##name`; the
[tables](https://github.com/86Box/86Box/blob/3a8953d0fee171a98500ca69d5b4e9905c07272d/src/cpu/386_ops.h)
select the original 286 REP MOVS functions and immediate word OUT handler.
This selection was checked before extracting the functions.

The fresh original-function run passed 24 byte/word MOVS cases (CX=0/1/3,
both directions, ordinary completion and trap-limited chunks) and four logical
word OUT cases, including AX=F6CA, IP=3848, port 02. A separate actual SPK286
batch passed 16 matching ordinary complete-instruction cases: twelve MOVS
and four OUT cases. Architectural state and independently specified memory
effects agree; logical word outputs are compared with corresponding CPU lane
transactions. The 28 reference cases and 16 differential cases are synthetic,
not physical captures or additional hardware-derived passes.

The harness uses simple valid-memory and logical-port services. Segment checks,
address translation and prefetch timing are stubs. The original loop's post-
execution event order was inspected statically, but that event loop is not
executed here. Trap-limited nonzero chunks demonstrate the original function's
rewind behavior; they do not establish physical TF/NMI/INTR sampling or priority.
SPK286's separately retained event benches test the D-037 engineering policy.
No event differential PASS or historical timing equivalence is claimed.

Reproduce from the repository root using the ordinary simulator executable:

```bash
python3 research/phase7_emulator_reference.py \
  --build-dir build/phase7-emulator-fresh \
  --executable build/phase7-complete/phase6/verilator/obj_dir/spk286_smoke
```

The output contains fetched source URLs/digests, extracted-harness digest,
compile log, original-function output, simulator batch/log and exact result.
An unavailable emulator build is not a functional closure prerequisite.
The delivery recovery package preserves the actual executed artifacts.
