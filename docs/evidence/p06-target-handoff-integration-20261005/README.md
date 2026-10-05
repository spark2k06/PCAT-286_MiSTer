# Historical target handoff full-CPU integration probes

Date: 2026-10-05. The immutable fixture uses only public CPU stimulus. Both Icarus and Verilator pass **777 cases per simulator** across MAX and all seven historical profiles: 608 normal encoding/transfer cases, 124 event cases, 24 protected source/target fault cases, 14 cancellation cases and seven HOLD cases. Every accepted metric and architectural assertion agrees. The complete **recorded** MAX per-edge stream equals the corrected functional CPU without normalization; this observer covers the native transaction, GPR/FLAGS/CS/IP, events and microsequencer/public retirement state, rather than every exposed debug port. Broader compatibility/regression is separate.

Targets have independently declared lengths 1..10 and both address parities, including repeated prefixes and ModRM/displacement/immediate acquisition. JE/JMP source deadlines charge 7 + target length; JCXZ uses 7 taken, LOOP uses8 with no target allowance and not-taken Jcond3. Relative/indirect near CALL/JMP, near/far RET and immediate far transfers retain original stack/return effects. The following MOV DX,BEEF discriminates trailing-byte replay and duplicate decode.

NMI/INTR injection reaches seven milestones from source body through delayed retirement. Source TF wins before an invalid target's #UD. An eleven-byte target raises #GP at its own IP. LOADALL enters PE using actual memory, valid cache records, GDT and IDT: an invalid far source selector saves source IP0480 with error18 and never retires, while targets truncated after1/2bytes save targetIP0501 with error0 after source retirement. External redirect during a READY-low offered CODE preserves the old owner until READY and discards its data; reset clears all tokens. HOLD during incomplete preview cannot execute a successor or bypass its missing bytes, then release completes source/target once.

This CPU-only fixture uses an ideal memory peer with explicit READY stalls. It is not literal Intel pin timing, complete event/fault coverage, motherboard-wait calibration, fitted resource cost or 50MHz closure.

The compact packet contains complete frozen source inputs, the generator's original pinned receipt, generated top/events, exact scripts/bench, result logs, compressed MAX observations and receipts. It excludes compiler objects and executables. From the project root under WSL/Linux:

```sh
mkdir -p build/p06-target-handoff-integration-replay
tar -xzf docs/evidence/p06-target-handoff-integration-20261005/p06-target-handoff-integration-20261005.tar.gz -C build/p06-target-handoff-integration-replay
python3 -B build/p06-target-handoff-integration-replay/p06-target-handoff-integration-20261005/source/scripts/test_p06_target_handoff_integration.py --output build/p06-target-handoff-integration-replay/p06-target-handoff-integration-20261005/source/build/replay --profiles 0,1,2,3,4,5,6,7 --dual
```

Omitting `--dual` replays Icarus only. Current production RTL is never read by the frozen fixture.
