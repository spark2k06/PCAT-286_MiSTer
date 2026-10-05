# P06/P12: M0 memory penalty after READY chaining

The exact 256-iteration T286REF M0 kernel reproduces the 6 MHz slowdown on
the composed production CPU/PCAT memory chain: **72,531 to 76,773 fabric
clocks (+5.85%)**. The reported MiSTer gross medians change from 1,786 to
1,894 PIT ticks (+6.05%). Their measurement boundaries differ; the simulation
isolates the kernel and does not reproduce DOS/PIT instrumentation.

Immediate RAM gives identical previous/current timings at 6, 8 and 12.5 MHz.
The observed 6 MHz change is a prefetch refill/admission phase effect in the
composed bus, with architectural signatures and memory results preserved.
It does not establish a functional priority violation. The reported 8 MHz
hardware penalty does **not** reproduce in the bounded cold-start phase and
legal-prelude searches below. It remains unexplained by this fixture.

This milestone adds diagnosis and evidence only. Production CPU, bridge,
instruction timing, SDRAM timing, config and OSD sources are unchanged.
No Quartus run, compensating multiplier, shortened timing budget or new
wait-state policy is part of this diagnosis.

## Source and workload boundary

The accepted snapshot is repository HEAD `6b94275`. The previous CPU uses
`6441d8d`, the parent of READY-chain correction `719de5a`. Exactly three
compiled source files differ: functional CPU, fetch unit and generated
profiled CPU. Every motherboard source and workload byte is shared. Inputs
are frozen before compilation and verified afterward. The compact source
archive stores the complete current snapshot and three previous overrides;
the source binding records full hashes for both versions.

NASM assembles unchanged `SW/CPUTIME/t286ref.asm`. The COM remains complete
at its original segment locations, with an executable reset/bootstrap:

| Item | Value |
| --- | --- |
| CS and DS | `106E` (4206 decimal), segment base `0106E0` |
| Baseline | IP `0488`, bytes `E2 FE C3` |
| M0 | IP `04A6`, 19 bytes including RET |
| M0 bytes | `A1 10 0B 03 06 12 0B A3 14 0B 81 36 16 0B 5A 5A E2 EE C3` |
| Data | offset `0B10` (2832 decimal), physical `0111F0` |
| Initial words | `1234 5678 0000 3C3C` |
| Final words after 256 | `1234 5678 68AC 3C3C` |
| Final AX/BX/CX/DX/DI | `68AC/5678/0000/9ABC/DEF0` |
| Final SP after kernel return / FLAGS | `FF00` / `0006` |
| Work | 256 iterations, 1,280 retired M0 instructions |

Baseline checks its own 256 retirements, unchanged initial words, GPR
signature, SP and FLAGS `0002`. Each measured interval begins with admission
of the first kernel opcode and ends at retirement of the final LOOP.
CALL/RET and startup are excluded. The clock is physical 50 MHz throughout.
The `FF00` SP guard is checked after RET; SP is `FEFE` at the measured final
LOOP because CALL's return address is still on the stack.

The ideal peer uses the production CPU/profile wrapper with immediate
READY. The composed peer derives the production AT machine and literal
PCAT P03(512 lines), data buffer, posted-write buffer and owner/KFSDRAM
instances from the existing R0 diagnostic. Only SDRAM initialization is
shortened. Steady timings remain the RTL defaults. The existing behavioral
SDRAM command/data peer does not validate electrical SDRAM margins.
AT refresh is unprogrammed/disabled; owner SDRAM maintenance remains active.
No BIOS, DOS, interrupts or PIT measurement code runs.

## Exact 256-iteration measurements

All 24 Verilator runs pass work, GPR, SP, FLAGS and memory checks. These are
directed diagnostic runs; this packet does not claim a CPU regression or
paired Icarus execution.

| Path | MHz | Baseline, both versions | Previous M0 | Current M0 | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Immediate RAM | 6 | 17,033 | 63,966 | 63,966 | 0 |
| Immediate RAM | 8 | 12,774 | 47,974 | 47,974 | 0 |
| Immediate RAM | 12.5 | 8,175 | 30,703 | 30,703 | 0 |
| Composed PCAT | 6 | 17,031 | 72,531 | 76,773 | +4,242 / +5.85% |
| Composed PCAT | 8 | 12,773 | 57,580 | 57,585 | +5 / +0.0087% |
| Composed PCAT | 12.5 | 8,174 | 36,878 | 36,874 | -4 / -0.0108% |

At 6 MHz the steady taken LOOP-to-LOOP interval changes from 283/284 fabric
clocks (34 nominal CPU clocks) to 300 (36 nominal clocks). Immediate RAM
remains 250 (30 nominal clocks). Conditional M0-minus-baseline averages are
26.015625 previous and 28.0040625 current nominal clocks per iteration.
This subtraction includes code delivery and memory implementation effects;
it is not an isolated EU timing measurement.

In all six composed M0 runs, after the first LOOP retirement there are zero
physical SDRAM READ commands, bridge deadline misses, HOLD edges or AT
refresh grants. The full measured intervals have 15 physical READ commands
and 512 physical write acceptances in each version. The data accesses are
three READs and two WRITEs per iteration, including the XOR read/write pair.
The warm penalty therefore occurs with buffered reads and normal posted
writes. Physical RAM latency is not needed to explain the steady 6 MHz cost.

## Warm 6 MHz causal sequence

The samples below are before each fabric edge updates sequential state.
They describe the second iteration's `MOV AX,[0B10]` in the current CPU:

| Edge | Observed event |
| ---: | --- |
| 793 | MOV opcode admitted; queue has six bytes; no outstanding CODE |
| 794 | First address byte consumed |
| 795 | Final address byte consumed; queue count four; ordinary fetch grant asserted |
| 796 | CODE `010B8C` becomes bus-visible; DATA request absent; BIU captures CODE ownership |
| 797 | DATA request and its acceptance asserted; existing BIU owner remains CODE |
| 798 | DATA active and waiting behind CODE |
| 800 | Bridge admits CODE Ts on a CPU boundary |
| 809 | Following boundary begins Tc (first sampled Tc state at edge 810) |
| 817 | CODE READY on terminal boundary |
| 818 | DATA READ `0111F0` becomes visible and is admitted |
| 825 | Following boundary begins DATA Tc (sampled at edge 826) |
| 834 | DATA READY |
| 842 | MOV retires with an implementation extension |

The previous CPU starts the corresponding MOV at edge 785 with six queued
bytes and CODE `010B8C` already outstanding from edge 777. That CODE finishes
at 792, DATA READ runs 793–809, and MOV retires at 825. Its start-to-retire
interval is 40 clocks; current takes 49. READY chaining's accompanying
reservation accounts for staged responses and active beats, shifting when
another ordinary request can launch. The shifted refill then misses the
bridge admission window and competes with operand delivery.

DATA does not exist on the edge when CODE acquires BIU ownership. It exists
before bridge Ts, but CPU-side ownership has already been retained. This
trace does not justify cancelling an offered or accepted CODE transfer, or
changing bridge timing to credit it retrospectively. The earliest genuine
instruction-owned demand established here is opcode admission at 793 and
address-byte consumption at 794/795. Historical EU demand lookahead needs
its own explicit contract and verification before a production change.

| Warm instruction | Previous start-to-retire fabric clocks | Current | Approximate nominal change |
| --- | ---: | ---: | ---: |
| MOV read | 40/41 | 49 | +1 clock |
| ADD read | 57/58 | 57 | 0 |
| MOV store | 49 | 41 | -1 clock |
| XOR RMW | 65/66 | 82 | +2 clocks |
| Taken LOOP | 65/66 | 66 | 0 |

The net change is two nominal clocks per steady iteration. CODE transfer
count barely changes: 2,816 previous versus 2,815 current fully enclosed
transfers. CODE occupies 47,026 versus 48,883 measured fabric edges, while
CODE overlapping an active DATA request increases from 11,782 to 19,187
edges. These occupancy counts describe overlap; they are not additive EU
costs or a separate wait-state budget.

## Bounded 8 MHz phase and startup controls

The unchanged profile generator uses increment 16 modulo 50 and toggles
phase parity on carry. Its full natural period is 25 fabric edges. The
bench instantiates that same production module with reset released N edges
before CPU/memory reset. Its boundary drives the machine's combinational
timing boundary wire. No CPU/profile register is forced. Per-edge assertions
verify the active 8 MHz profile and actual boundary wiring; raw analysis
verifies natural accumulator/parity progression and every initial epoch.

All 25 offsets run both frozen CPUs for 32 iterations. Extreme offsets
0, 6, 7 and 13 then run 256 iterations. Confirmed ranges are 57,579–57,586
current and 57,573–57,591 previous fabric clocks. Kernel admission naturally
collapses to three current and two previous epoch states despite full
initial-epoch coverage. That limitation is explicitly recorded.

An additional legal startup prelude executes 0–24 NOPs before CALL, retaining
the exact original M0 bytes, IP, data and signatures. Both versions run each
prelude for 32 iterations; preludes 0, 3, 7, 8, 12 and 22 confirm extrema
with 256. Confirmed ranges are 57,579–57,586 current and 57,573–57,592
previous. Admission covers three current and four previous epoch states.
These bounded variations do not reproduce a sustained 8 MHz penalty.
They do not cover arbitrary DOS/PIT prehistory, warmed machine state or
AT refresh. The MiSTer 8 MHz observation remains a separate open result.

An earlier execute-enable delay of 0–24 edges was ineffective: the initial
cold fetch completed later, leaving every kernel start unchanged. It is
preserved as an ineffective control, not accepted admission-phase coverage.
The first byte-guard attempt stopped before CPU compilation because the
harness guard mistakenly used LOOP displacement `ED` instead of unchanged
NASM `EE`. Two phase-wiring attempts also stop before any kernel result:
Verilator rejects forcing an input reset, and a static wire force does not
track the changing boundary. Their logs/fixtures remain separate evidence.

## Reproduction and compact evidence

```sh
python3 scripts/replay_p06_m0_archive.py \
  --archive docs/evidence/p06-m0-diagnosis-20261005 \
  --output /tmp/p06-m0-replay
```

This command restores both full source views, verifies every bound hash and
prepares all eight original build recipes and 144 accepted run recipes at
the new location. It does not compile or simulate. Adding `--execute` to a
fresh preparation explicitly compiles and runs the archived workloads.
No original build directory or old `/tmp` directory is required. The helper
is self-contained and reads production sources exclusively from the frozen
archive. The [replay README](../evidence/p06-m0-diagnosis-20261005/README.md)
also documents analysis reproduction directly from the archived gzip traces.

Preparation was verified without further simulation: both 366-file source
views match, every source operand and generated bench remains byte-identical,
compile flags and operand order are unchanged, and all run scalar arguments
and program images are bound. Only source, fixture, object and output paths
are relocated. The portable receipt records `executed: false`; preparation
does not claim a new execution result. The live-tree diagnosis producer can
create a new comparison, but that new snapshot is not the archived experiment.

The [compact archive](../evidence/p06-m0-diagnosis-20261005/manifest.json)
preserves complete raw traces as deterministic gzip, program images/listing,
generated benches, build/run logs, receipts, analysis, frozen source hashes
and a deduplicated source tar. The packet verifies every archived raw stream
against its receipt and round-trips every source member. Full original and
previous snapshots can be reconstructed without consulting the changing
working tree. Accepted and failed/ineffective attempts are named separately.
The portable helper, prepared recipes and contract comparison have a separate
supplemental manifest bound to the unchanged core manifest.

The four accepted comparison builds take 19.549/40.197 seconds current
ideal/PCAT and 18.707/35.162 seconds previous ideal/PCAT. Individual runs take
0.167–2.824 seconds. Natural epoch builds take 30.825/21.262 seconds;
NOP-prelude builds take 22.908/19.672 seconds. All simulations run in WSL
Ubuntu 24.04 with bounded process-group timeouts. Temporary build trees,
uncompressed traces and duplicated snapshots were removed after independent
review: 587,452,135 bytes in the exact owned build subtree and 26,708 bytes
in its Python cache. The five recorded owned `/tmp` roots were already
absent. The [cleanup receipt](../evidence/p06-m0-diagnosis-20261005/cleanup-receipt.json)
records path boundaries, reparse/process checks and preservation of the user
landmark script. The [independent review](../evidence/p06-m0-diagnosis-20261005/independent-review.json)
passes the raw packet, all accepted runs and portable restoration contracts.
