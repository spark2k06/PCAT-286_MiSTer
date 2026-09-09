# Incremental Phase 8 preparation - 2026-09-09

Status: design/preparation only. No Phase 8 RTL, integration harness or machine
port has been implemented. Phase 7 remains incomplete; its missing strings/I/O
delivery is not renamed as Phase 8 work. This incremental next phase is distinct
from the original specification's long-term numbered system/protected-mode
milestones. No protected mode, LOADALL, WAIT/ESC/NPX or timing profile is authorized.

## Entry and independent preparation

Phase 8 entry requires the complete integrated Phase 7 functional gate,
independent functional approval bound to executed sources/policy, and verified
Git delivery under D-037. The three inherited Phase 6 questions, the selected
REP CX=0 completion policy and the exact E7 NOT EVALUABLE capture remain open
nonblocking evidence notes. Physical closure of those notes is not an entry
prerequisite. Historical timing remains uncertified. No Phase 8 implementation
is part of the Phase 7 closure task.

Planning program scenarios, specifying transaction ownership and examining the
named consumer read-only are independent preparation. Gate wiring repair and
INS verification repair remain Phase 7 work. Review, executable validation,
physical instruction evidence, integration, Git delivery and architectural
release approval must continue to be reported separately.

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

Firmware-sized programs should follow these deterministic interactions. A BIOS
boot is a separate machine-integration result, not a replacement for instruction
evidence, a timing certificate or proof of complete 80286 support.

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

Before claiming that firmware path runnable, separately scope and validate the
required CPU WAIT/ESC/NPX semantics, including the no-coprocessor/error/busy policy
and relevant evidence, or explicitly choose an appropriate downstream firmware
configuration. Arbitrary NOP substitution is not a valid CPU compatibility fix.
Inventory actual firmware instructions and device assumptions before any future
boot experiment. This note neither implements that inventory harness nor grants
an implementation extension.
