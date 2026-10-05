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

Strict raw/timed candidate lint passed. Five affected banks passed against
the raw executor in Icarus and Verilator, with original expectations and one
compilation job. The timed consumer change is covered by the source-extracted
proof; these ten simulation runs do not claim timed-executor simulation:

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

## Actual fit and cost

Generic mapping of the isolated CPU consumer cone is 3,577 to 3,580 gates;
the isolated HACC arithmetic cone is 215 to 307 gates. These are not Quartus
ALMs, FPGA occupancy or physical slack. The completed joint fit measures the
actual cost below; its deltas cannot be attributed to either isolated change.

The completed fit is `build/p06-stack-data-hacc-allfeatures-20261005-v1`.
Its 2,073 source files were frozen at PCAT commit `8273c48`; placement seed 2
is the sole settings change inside that snapshot. Features, clocks, production
SDC and the additional 0.500 ns palette route requirement match the parent.
Before/after source and proof bindings passed. A second STA audit used the
same fitted database and original SDC; all eleven DB/RBF/SOF artifacts were
verified unchanged. No second compilation was performed for that audit.

| Corner | Global setup (ns) | Global hold (ns) | CPU setup (ns) | CPU hold (ns) |
| --- | ---: | ---: | ---: | ---: |
| Slow 100 C | +0.072 | +0.140 | +0.486 | +0.254 |
| Slow -40 C | -0.063 | +0.027 | +0.531 | +0.242 |
| Fast 100 C | +2.273 | +0.133 | +9.299 | +0.138 |
| Fast -40 C | +2.583 | +0.071 | +10.849 | +0.120 |

**The CPU closes physical 50 MHz setup and hold:** minima +0.486 / +0.120 ns.
The entire common 50 MHz clock domain, including incoming paths, has minima
+0.164 / +0.110 ns. Recovery and removal are positive in all four corners,
with minima +1.710 / +0.197 ns. Constraint coverage matches the sealed parent.

**Global timing remains open.** The cold slow HDMI path is
`ascal|o_ihsize[3]` to `ascal|o_hacc_next[12]`, at -0.063 ns. Its clock
relationship is 6.732 ns, skew -0.496 ns and reported data delay 6.099 ns.
All global hold corners are positive, with a minimum of +0.027 ns.

| Measured resource | Parent | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Placed ALMs | 36,896 | 36,701 / 41,910 (87.57%) | -195 |
| Equivalent ALMs | 31,609 | 31,445 | -164 |
| Registers | 38,374 | 38,376 | +2 |
| RAM bits | 3,301,019 | 3,301,019 | 0 |
| M10K blocks | 416 | 416 | 0 |
| DSP blocks | 39 | 39 | 0 |
| PLLs | 3 | 3 | 0 |

The inclusive CPU hierarchy uses 7,281.9 required / 8,071.8 placed ALMs,
5,598 registers and one M10K. Required/placed CPU ALMs decrease by 168.4 /
119.6 respectively. Register-count differences arise from physical mapping;
the RTL changes add no state. All audio features remain enabled.

## Selected candidate and pause

This is the best measured equivalent fit with positive hold:

| Equivalent candidate | Worst global setup (ns) | Worst global hold (ns) | Worst CPU setup (ns) |
| --- | ---: | ---: | ---: |
| Deadline-fold seed 2 | -0.312 | +0.034 | -0.312 |
| Null-segment / terminal | -0.337 | +0.036 | -0.337 |
| Stack DATA / HACC | **-0.063** | **+0.027** | **+0.486** |

The prior seed-1 fold has setup -0.288 ns but hold -0.047 ns, so it is not
selected. Original-SDC overlays and older OSD/configuration variants are
excluded from ranking. Exact comparisons are retained in the fit archive.

Compilation began at 20:35:39 UTC and completed at 21:08:18 UTC on
2026-10-05. Quartus reports 32 min 28 s, including its own automatic retry
after a placement conflict. Custom four-corner STA completed at 21:12:04 UTC.
The stable RBF was observed at 21:06:27 UTC and announced before STA ended.

RBF: `build/p06-stack-data-hacc-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`,
4,156,532 bytes, SHA-256
`d83a6d9494f69e68d9236bf7555c05f2fa344c3f1ab46208c8225a727fef40de`.
The [sealed fit manifest](../evidence/p06-stack-data-hacc-fit-20261005/manifest.json)
binds the complete effective sources, original reports, hierarchy, compiled
microcode, launchers, comparison and source/proof receipts. Every one of its
2,475 archived members was read back before temporary files were removed.
The independent final review also verified every member, all four original
and production timing corners, the eleven unchanged fitted artifacts, ROM
parameters and hierarchy/resources. Its initial live-QSF comparison stopped
on the intended seed overlay; the preserved v2 accepts only the exact literal
seed 1 to 2 line, with all other QSF bytes identical. No unknown source
exceptions were introduced. Review files and their hashes are attached to
the manifest without modifying the sealed archive.

Full regression was authorized after positive setup and hold in all four
corners and review of the remaining reported margins and coverage. The newer
user instruction is to pause after this candidate's result, regardless of
closure. **Work is paused after this result.** No additional fit or full
regression will start before resumption. Full regression and MiSTer validation
have not been run for this candidate. No new performance score is claimed.
Retain bitstreams and sealed,
read-back evidence when removing owned temporary build files; the effective
fitted sources must remain recoverable for the future same-source regression.

Installed raw/timed consumed-contract and full timed CPU lint passed. The
generated top, events and repeat contract remain byte-identical. SPK286 is
committed at `8862139` and its complete canonical vendor mirror is synchronized
(1,249 imported files, five PCAT overlay files, nine retained extras).
See [installed evidence](../evidence/p06-stack-data-applied-20261005/manifest.json)
and [scaler evidence](../evidence/p06-scaler-hacc-reorder-20261005/manifest.json).
