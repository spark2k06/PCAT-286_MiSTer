# Incremental Phase 8 preparation - 2026-09-10

Status: 8A and 8B implementation, independent review, whole-core validation
and downstream transfer are complete; the user-owned Quartus/RBF checkpoint
remains pending. Phase 7 milestones 1–9 have complete functional validation
and independent approval under D-037. Phase 8 may start from the delivered
functional baseline; its implementation is separate work. This incremental next phase is distinct
from the original specification's long-term numbered system/protected-mode
milestones. The 2026-09-10 scope now authorizes two CPU-only workstreams: the
verified BIU HOLD/LOCK race correction and a separate investigation/fix for the
coprocessor ESC opcode blocking at D8–DF. This does not authorize a complete
80287, Protected Mode, LOADALL or a historical timing profile. The existing BIOS
is expected to be retested unchanged after the D8–DF fix; BIOS adaptation is not
planned unless an independent firmware defect remains.

## Entry and independent preparation

Phase 8 entry requires the complete integrated Phase 7 functional gate,
independent functional approval bound to executed sources/policy, and verified
Git delivery under D-037. The additional CPU work is scoped by D-038. The three inherited Phase 6 questions, the selected
REP CX=0 completion policy and the exact E7 NOT EVALUABLE capture remain open
nonblocking evidence notes. Physical closure of those notes is not an entry
prerequisite. Historical timing remains uncertified. No Phase 8 implementation
is part of the Phase 7 closure task.

Planning program scenarios, specifying transaction ownership and examining the
named consumer read-only are independent preparation. The Phase 7 gate wiring and
INS verification repairs are delivered with the accepted Phase 7 baseline. The
new workstreams below are CPU-repository work; PCAT/XT bus overlays, BIOS changes
and MiSTer machine integration remain downstream work. Review, executable
validation, physical instruction evidence, integration, Git delivery and
architectural release approval must continue to be reported separately.

The current implementation record is split into
[PHASE8_8A_MANIFEST.md](PHASE8_8A_MANIFEST.md),
[PHASE8_8B_MANIFEST.md](PHASE8_8B_MANIFEST.md) and
[PHASE8_WHOLE_CORE_VALIDATION.md](PHASE8_WHOLE_CORE_VALIDATION.md). These
records intentionally distinguish CPU evidence from the downstream transfer
and the later physical hardware checkpoint.

## Newly authorized Phase 8 workstreams

These two workstreams were added after the downstream PC/AT consumer exposed
concrete integration behavior. They must be implemented and verified in SPK286,
not hidden in the consumer overlay. They are separate defects with separate
tests, commits or commit sections, review findings and acceptance evidence.

### 8A — BIU HOLD/LOCK race during memory XCHG

The downstream candidate `D:/GitHub/PCAT-286_MiSTer` records a Quartus-built
diagnostic at commit `409292dcb06ea507099e4e68cf6d691d9b7294e8`, titled
`fix: release SPK286 DMA lock race diagnostics`. Its reported functional change
in the copied SPK286 BIU is:

```systemverilog
if (!hold_request || lock_request) hlda <= 1'b0;
```

Treat this line as a hypothesis and provenance lead, not as proof that a blind
copy is correct. Inspect the current SPK286 `rtl/spk286_biu.sv`, the PCAT copy,
the surrounding ownership state and the trace that demonstrated the failure.
Reproduce the race in the original repository before changing RTL. The likely
boundary is a HOLD request arriving while the implicit LOCK interval of a memory
`XCHG` (`opcode 87`) is active: HLDA must not remain asserted in a way that
prevents the locked data transaction from completing.

Add a focused SPK286 BIU/integration test that:

1. starts a memory `XCHG` through the normal CPU path, so the implicit
   `lock_request` is exercised;
2. raises `hold_request` at the documented collision boundary, including a
   READY wait variant;
3. proves that HLDA is released/does not steal the locked operation;
4. proves that the retained memory transaction completes once, with correct
   data, address and lock ownership; and
5. proves that HOLD is granted at a later legal boundary and that no stale
   response or duplicate write is produced.

The BIU unit test may drive `lock_request` directly to isolate the arbitration
contract, but a separate CPU-level case must execute `XCHG` so the implicit-lock
producer remains covered. Keep reset, odd-word, READY, redirect/cancel, INTA and
existing HOLD/HLDA tests. Do not resolve the race by removing LOCK, ignoring
HOLD, adding arbitrary idle cycles or changing the external protocol. Preserve
the ownership rule for odd words and interrupt acknowledge chains.

The copied PCAT BUS overlay, DMA/DACK wiring, `debug_detail` ports and XT
serializer are not to be moved into SPK286. Only the general CPU/BIU correction
and its CPU-only verification belong here. Record the source candidate hash,
comparison and reason for any difference between the two trees.

### 8B — D8–DF coprocessor/ESC decoder and microcode blocking

The downstream PC/AT bring-up reports that an ESC/coprocessor opcode in
`D8–DF` (for example `DB`) blocks the CPU. Treat this as a separate
decoder/microcode defect. First reproduce it in SPK286 from a small program and
trace the opcode fetch, decode decision, micro-entry, retirement/event state,
bus activity and any halt/shutdown indication. Determine whether the block is
caused by an unsupported decode, a missing terminal microprogram, an invalid
microcode entry, an executor wait or an erroneous event path.

Before selecting behavior, read the applicable Intel 80286/80287 primary
documentation and the current SPK286 contracts. The initial Phase 8 target is
**deterministic 286 no-coprocessor/XT-profile behavior with no deadlock**. Do
not silently claim full 80287 execution. If the documented profile treats an
ESC as an ignored/pass-through operation when no coprocessor is present, encode
and verify that general rule; if it requires an exception or a defined external
coprocessor request, implement that contract instead. The agent must record the
chosen semantics and evidence before changing expected results.

The correction must cover the complete D8–DF opcode range, ModR/M forms and
prefix/stream boundaries that the current Phase 8 scope admits. At minimum,
every legal byte sequence must either complete with the documented architectural
effect or deliver the documented event; none may loop forever, leave the
microsequencer active indefinitely, silently consume unrelated bytes, or corrupt
CS:IP/prefetch. Invalid forms must follow the existing invalid-instruction
policy. `WAIT`/`FWAIT` behavior remains a separately named dependency if it is
not part of the chosen no-coprocessor contract; do not implement an 80287 by
accident while fixing the decoder.

Use project-owned microcode source as authoritative. If the correction needs a
new terminal operation or decode entry, update the source, regenerate all
artifacts and run compiler/ROM consistency checks. Never hand-edit generated
ROM or add a test-index/opcode special case to production RTL. Add directed
cases for representative D8, D9, DA, DB, DC, DD, DE and DF encodings, register
and memory ModR/M forms, required byte consumption, follow-on instruction
execution, READY waits and the selected no-coprocessor/event behavior. Include
`DB` because the downstream failure specifically reported it, but do not limit
the fix to `DB`.

Keep the complete 80287, NPX state, WAIT timing, task switching and Protected
Mode semantics outside this work unless the primary contract proves a smaller
dependency is required for the no-deadlock behavior. Any such dependency must
be separately scoped, reviewed and reported rather than smuggled into this
workstream.

The intended consumer outcome is that the existing PCXT/PCAT BIOS can execute
through these instructions without a firmware patch. After 8B passes, rerun the
original BIOS unchanged (with its image hash recorded) and classify the result.
Do not modify BIOS source or ROM bytes to hide the D8–DF failure. If an
independent BIOS incompatibility remains after the CPU fix, open a later,
separately reviewed firmware task; it is not part of Phase 8.

### Workstream independence

8A must pass with 8B reverted, and 8B must pass with 8A reverted, except for
shared build/test infrastructure. Keep separate focused tests and manifests so
a future consumer can identify which CPU revision supplied each fix. The final
Phase 8 review may combine them only after both isolated proofs pass.

## Downstream transfer and user RBF checkpoint

Phase 8 now has an explicit four-point delivery sequence:

1. Complete and verify workstream 8A in SPK286.
2. Complete and verify workstream 8B in SPK286.
3. Transfer the verified CPU changes from SPK286 into the downstream
   `PCAT-286_MiSTer` project, preserve its consumer-specific overlay, and create
   a commit there. The transfer must carry the general `rtl/spk286_biu.sv`
   correction, the D8–DF decoder/microcode correction and their required
   generated/test artifacts; it must not carry a PCAT BUS overlay as a CPU
   source. Record source/destination commits, file hashes and the PCAT commit
   created by the agent. Do not modify the production BIOS.
4. Hand the PCAT commit to the user. The user performs the Quartus synthesis and
   tests the generated RBF on the target board. The agent must not claim fit,
   timing or hardware success without the user's actual result. The user’s
   explicit **OK** is the acceptance of this checkpoint; after that OK, Phase 8
   may be marked complete and no BIOS-adaptation task is required. If the user
   reports a failure, classify it and fix the relevant CPU/consumer defect
   before closure; do not silently proceed to BIOS changes.

The agent may prepare portable/Yosys checks and a Quartus project in SPK286 or
the consumer where appropriate, but the user-owned synthesis/RBF execution is
the authoritative hardware checkpoint after the transfer step. A queued, missing or inferred build
result is not an OK. Phase 8’s final report must distinguish the SPK286
implementation/review, the PCAT transfer commit and the user’s later RBF result.

The previous optional BIOS observation remains useful only as confirmation after
8B. It is not a fifth implementation milestone. A successful unchanged BIOS
run confirms the D8–DF diagnosis; Phase 8 does not require BIOS source changes.

## Proposed whole-core interaction programs

These are proposed CPU-only simulations, not executed programs or additional
physical SingleStep cases. Use independent expected signatures, a bounded
completion marker and a trace of accepted transactions; halt/timeout alone is
not a pass. Include dependency stalls and event injection in each relevant run.

| Program | Interactions | Observable completion criterion |
| --- | --- | --- |
| Reset-to-signature | Native FFFFF0 fetch, far jump, segment/stack initialization, dependent ALU code | Exact signature, CS:IP and first-fetch trace; no fetch from stale reset cache |
| String transform | MOVS/LODS/STOS, arithmetic, comparison termination, DF, segment overrides | Exact complete buffer and guard regions, remaining CX/SI/DI, one macro completion per instruction |
| Restart/resume | REP plus controlled eligible event, handler register save, IRET | Complete frames and resumed elements, no duplicate memory or port effects; zero-count scenarios follow the explicit D-037 completion policy |
| Port stream | Accepted-access-dependent INS data and OUTS sequence, scalar port checks | Exact ordered port direction/address/lanes/payloads and memory; 16-bit FFFF port carry preserved at CPU boundary |
| Nested frames and aliases | ENTER/LEAVE, near/far CALL/RET, PUSHA/POPA, LDS/LES with aliases | Exact return chain, selectors/caches and stack image; accepted writes survive documented faults |
| Bus ownership | READY waits, HOLD/HLDA, LOCK, odd words, reset/redirect | Stable outstanding requests, exact accepted counts, correct drain/cancel behavior and no ownership overlap |
| Fault recovery | Invalid encoding, word-limit and arithmetic faults followed by valid handler return | Correct vector/frame and documented partial effects; no synthetic protected-mode semantics |
| HOLD/LOCK regression | Memory XCHG with a colliding HOLD request and READY wait | HLDA cannot strand the implicit LOCK transaction; one complete memory exchange and later legal HOLD |
| Coprocessor decode | D8–DF representative ESC/ModR/M programs, including DB, with no coprocessor | Deterministic documented completion/event, correct byte/IP/prefetch progress and no decoder/microcode deadlock |

Firmware-sized programs should follow these deterministic interactions. A BIOS
boot after 8B is a useful unchanged-firmware integration observation, not a
replacement for instruction evidence, a timing certificate or proof of complete
80286 support. BIOS adaptation is not a Phase 8 deliverable.

## Contract for a future XT consumer

The inspected consumer is
[PCXT-EGA_MiSTer at 7bbdbbbe5ba1c2737da88943bbc668f5520faa31](https://github.com/spark2k06/PCXT-EGA_MiSTer/tree/7bbdbbbe5ba1c2737da88943bbc668f5520faa31).
Read-only HEAD inspection confirmed this exact source on 2026-09-09. In
`PCXT-EGA.sv:1361`, `i8088 B1` currently receives CORE_CLK and CLK, uses 20-bit
address and 8-bit data paths plus a private word path, and connects INTR while
tying NMI low. Its interface is not interchangeable with SPK286's normalized
24-bit/16-bit transaction boundary. Source hashes are retained in the closure
package's `consumer-reference/source-manifest.json`. No consumer file was edited.

| Requirement | CPU boundary and future consumer obligation |
| --- | --- |
| Width and lanes | SPK286 exposes address[23:0], 16-bit data, A0 and active-low BHE. Even byte uses D7:0, odd byte D15:8, even word both; odd word is two retained transfers. Consumer must steer into XT devices without inventing extra side effects. |
| Request retention | Hold address, status, direction, lane mask and driven data while bus_valid and not ready. Accept one physical transfer on its READY edge; no response from stale or idle READY. Retain read response for its CPU consumer. |
| Side-effect ownership | SPK286 BIU owns CPU physical-cycle sequencing. Consumer owns actual memory/device effects exactly once on accepted transfers, including each half of an odd word. Expected test results cannot drive devices. |
| Reset and redirects | Retain architectural reset CS=F000, hidden base=FF0000, IP=FFF0 and first physical address FFFFF0. Reset can abort unaccepted work but cannot undo accepted writes. Redirect drains accepted transactions and discards stale responses according to the existing CPU contract. |
| Address adaptation | Any 24-to-20-bit XT mapping, ROM alias and wrap policy belongs in the consumer. Do not mask A20 or replace the SPK286 reset vector internally to accommodate the XT BIOS. |
| INTA | Two independently READY-qualified acknowledgements; vector only from the second D7:0. Preserve the recorded B-2 LOCK chain through the first complete frame push. A consumer adapter must translate status/polarity for its interrupt controller. |
| HOLD/HLDA | Grant only at an allowed boundary and block new CPU transactions during the grant. Do not split retained odd words or a LOCK chain. The current i8088 interface offers no drop-in HOLD/HLDA mapping; specify the consumer adapter explicitly. |
| LOCK | Preserve ownership across each documented CPU atomic interval and INTA chain. Translate active-high normalized bus_lock into consumer polarity; no chipset owner may interleave. |
| Clocks and asynchronous pins | SPK286's normalized inputs are synchronous to clk. Consumer owns clock-domain crossings and synchronization of READY/event/arbitration inputs. Specify a bundled request/response handshake or single-domain clock-enable design; do not independently synchronize multibit payloads. Record reset release and event latency. |
| Timing | Real dependencies remain mandatory. Existing consumer speed controls and nominal MHz do not define SPK286 Accurate/Fast/Max or validate historical Ts/Tc/Ti timing. |

All XT address mapping, byte/word steering into its chipset, PIC/PIT/DMA/video/
storage behavior, BIOS packaging, SDRAM arbitration and MiSTer top-level changes
belong in the consumer repository. SPK286 remains reusable CPU RTL and CPU-only
verification infrastructure. No boot or combined FPGA fit has been established.

## Firmware prerequisites

The inspected [Micro8088 cpu.inc](https://github.com/spark2k06/PCXT-EGA_MiSTer/blob/7bbdbbbe5ba1c2737da88943bbc668f5520faa31/SW/8088_bios/src/cpu.inc)
states its detector targets 8088/80C88/V20 and may misidentify other processors.
`detect_cpu` uses nondecimal AAD and TF/segment-register stepping probes
(lines 42-79). A 286 implementation should preserve 286 behavior even if this
routine's label is unsuitable; a firmware adaptation belongs downstream.
`detect_fpu` issues FNINIT and FNSTCW (lines 173-181) and deliberately avoids
FWAIT for the no-coprocessor case. These ESC instructions are outside Phase 7.

The Phase 8 8B workstream now specifically covers the D8–DF ESC decode/blocking
problem. After it passes, test this existing BIOS unchanged before considering
any firmware adaptation. A successful unchanged BIOS run is evidence that the
CPU fix addressed the observed blocker; it is not a timing certificate or proof
of complete AT compatibility. If the BIOS still fails for an independently
reproduced reason, inventory its instructions and device assumptions and open a
separate firmware task. Arbitrary NOP substitution remains invalid. This note
does not authorize modifying BIOS source or ROM bytes in Phase 8.

As of 2026-09-10, steps 1–3 are complete. The source review snapshot is
`87b597ea97c859e0240155d0c6905b255266f962`; the PCAT transfer commit is
`b6c3035e716fcd640523c7189480e59941067472`. The unchanged BIOS boundary smoke
also passed, but no Quartus/RBF or board result is implied.
