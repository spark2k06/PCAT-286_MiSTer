# Stack data selection and scaler accumulator timing candidate

## Objective and parent

Close the remaining physical setup paths while preserving the common 50 MHz
CPU/bridge/SDRAM clock, the existing HDMI clock and all enabled functions.
The parent is the sealed `p06-null-segment-fit-20261005` result: global setup
is -0.337 ns at slow 100 C and -0.197 ns at slow -40 C; all four hold corners
are positive, with a minimum of +0.036 ns. These are measured parent results,
not predicted margins for the new candidate.

## CPU change

Four opcode/state selectors choose the stack data before late permission
signals arrive. Permissions remain in the real request, fault and write
controls. No registers, clocks, microcode words or execution cycles are added.
The raw executor changes from SHA-256 `325f51e6a91ae9c309786c17da8c22aa3264b3084314008b43b7cc41fd44f6db`
to `8d41e0187bef3081728780e4683c9e312b1f4beb1f3c40a6244d465c32799710`.
PCAT's generated executor changes from `19882c7b14c1dd8dde73ff97ead3e47a66ba394ef474713085b468d1ad735af4`
to `2b5ca85c5939dcce3984439f8d5d9c67d590f70ad99faaa08cf139d65a33a123`.

The private source-extracted proof compares the actual producer, top address,
protection and fault consumers, every operand output, and the next-state
equations of its two state bits for arbitrary binary inputs and states.
Actual request signals qualify only the two address payloads. Requests and
other observable outputs are compared unconditionally. Eight functional
mutants are rejected. Idle internal payloads intentionally differ: the
historical flat checker remains unchanged, and genuine flat counterexamples
are retained alongside the new consumed-address contract. No full CPU
inductive equivalence claim is made.

Strict raw/timed candidate lint and five affected banks passed in Icarus and
Verilator, with original expectations and one compilation job:

| Bank | Checks / cases |
|---|---|
| Call stack precheck | 9 checks |
| Call gate accessed | 420 checks, 144 cases |
| Protected outer event | 6 checks, 499 stalls |
| Protected return restart | 81 checks, 27 cases |
| Stack frame lifecycle | 39,296 checks, 339 cases |

## Scaler change

Reassociate the positive horizontal-accumulator expression so the late
horizontal-size value reaches a shorter arithmetic chain. The branch, carry,
other results and state remain unchanged. The complete source changes from
`412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186`
to `8a8382913f007cf7405aad235d6df9558ec14fc493251e31783ddb00031fd687`.

Source-extracted proofs cover all three OHRESH values (1024, 2048, 4096), with
nine rejected mutants and 135,168 native boundary/random cases. Whole-file
VHDL 93/08 analysis preserves the ten inherited hiding diagnostics and adds
none. The existing terminal-comparison proof also runs against the installed
file, retaining its historical reference and binding the separate HACC proof.

## Cost, fit and regression

Generic mapping of the isolated CPU consumer cone is 3,577 to 3,580 gates;
the isolated HACC arithmetic cone is 215 to 307 gates. These are not Quartus
ALMs, FPGA occupancy or physical slack. Actual FPGA cost must be measured by
the new fit; parent occupancy is 36,896 / 41,910 placed ALMs (88.04%).

The intended fresh fit is
`build/p06-stack-data-hacc-allfeatures-20261005-v1`, with placement seed 2
changed only inside the frozen snapshot. Timing constraints and features
remain identical to the parent. Status: **preparing the source-bound fit;
no new RBF or timing closure result yet**.

Full regression was authorized after positive setup and hold in all four
corners and review of the remaining reported margins and coverage. The newer
user instruction is to pause after this candidate's result, regardless of
closure. No additional fit or full regression will start before resumption.
It has not been run for this candidate. Retain bitstreams and sealed,
read-back evidence when removing owned temporary build files; the effective
fitted sources must remain recoverable for the future same-source regression.

Installed raw/timed consumed-contract and full timed CPU lint passed. The
generated top, events and repeat contract remain byte-identical. SPK286 is
committed at `8862139` and its complete canonical vendor mirror is synchronized
(1,249 imported files, five PCAT overlay files, nine retained extras).
See [installed evidence](../evidence/p06-stack-data-applied-20261005/manifest.json)
and [scaler evidence](../evidence/p06-scaler-hacc-reorder-20261005/manifest.json).
