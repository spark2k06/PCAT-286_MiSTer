# Protected-mode targeted milestones — 2026-09-30

The user authorized H04, H14, H01 and H02's CLI/STI and I/O subset, with a
separate commit per verified milestone. Whole-project regression is explicitly
deferred to a later task. Expectations derive from Intel 210498-005, with the
native 86Box 286 paths as supporting evidence; no 386 facilities are imported.

## H04 — Ordinary gate entry clears NT

Intel section 10.1 requires saving old FLAGS before clearing NT on an interrupt
without a task switch. Native `x86seg.c::pmodeint` likewise clears TF/NT for
interrupt/trap gates, and only interrupt gates clear IF. The RTL change is
limited to the ordinary event FLAGS mask; microcode is unchanged.

Before correction, the directed bank fails with live FLAGS=7002 on an
interrupt gate entered with NT=1. After correction:

| Check | Actual result |
|---|---|
| New `spk286_event_nt`, Verilator and Icarus | 158 cases / 944 checks in each |
| Existing `spk286_protected_event_outer`, both | 6 checks in each |
| Existing `spk286_protected_task_gate`, both | 9 checks in each; nested NT preserved |
| Verilator RTL lint | Pass |
| Generated microcode consistency | Pass, unchanged 122 entries / 723 words |
| Physical SingleStep CD sample | 100 passed / 0 failed; real mode only |

The new bank executes real instructions from an independent LOADALL fixture,
with READY stalls, NT=0/1, interrupt/trap gates, software INT and #GP sources,
same/inward privilege transfers, all three timing policies and real-mode
controls. It checks saved FLAGS, live FLAGS, frame size, destination context and
ordinary handler IRET. H03's restoration of NT/IOPL from return FLAGS remains
open; it is not asserted as fixed by this milestone.

Reproduction:

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_event_nt
```

Local before/after, affected-bank, lint and SingleStep logs are retained under
`build/h04-*.log` and `build/pm-targeted-*.log`. No full regression, new OS boot,
Quartus synthesis or physical protected-mode measurement was performed.

## H14 — Valid unaligned protected stacks

Intel section 2.2 explicitly permits unaligned words, including stacks. Native
286 gate/return paths check byte ranges without imposing general SP alignment.
Removed only `return_stack_pointer[0]` from the outer-return range predicate
and `call_stack_sp_q[0]` from the inward-frame predicate. The low-SP/FFFF
overrun checks remain; these check complete accesses, not general alignment.

Before correction, RETF with valid source SP=F001 raises #GP instead of
returning. After correction:

| Check | Actual result |
|---|---|
| New `spk286_odd_protected_stack`, both simulators | 216 cases / 951 checks in each |
| Existing `spk286_call_stack_precheck`, both | 9 checks in each; SP=3 rejected before writes |
| Existing `spk286_outer_return_sp`, both | 216 cases / 693 checks in each |
| Verilator lint / generated consistency | Pass |
| Physical SingleStep CB/CA/CF samples | 300 passed / 0 failed; real mode only |

The directed bank covers RETF, RETF-immediate, IRET, inward CALL with two
parameters, interrupt and trap gates, their return frames, odd/even SP,
ordinary/expand-down stacks, all timing policies and READY stalls. It verifies
exact frame words, transfer counts and paired high/low byte lanes. Invalid
limits, frame underflow and FFFF crossing must still fault before publishing
the return or writing the gate frame.

The invalid outer-return controls expose an existing H12 discrepancy: the
micro-executor range signal routes to #GP(0) where Intel requires #SS(0).
Those controls assert rejection and preserved restart state; they deliberately
do not assert the incorrect vector as an architectural expectation. Inward
gate range controls additionally assert #SS. H12 remains open; H14 changes
only alignment acceptance. Local logs: `build/h14-*.log`.

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_odd_protected_stack
```

Whole-project regression and hardware/synthesis checks remain deferred as
requested; no new OS boot was run for this milestone.

## H01 — System instruction mode and privilege matrix

Intel chapter 10 and the instruction appendices distinguish protected-only
instructions from instructions restricted to CPL0. Native 86Box's 286
`op0F00_common` and `NOTRM` paths support the same matrix. The new generic
microcode checks precede operand reads; the executor also suppresses table
transactions and null-LDTR publication on privilege denial. SLDT/STR are
unprivileged when PE=1. LLDT/LTR denial reports #GP(0), before selector checks.
LAR/LSL/VERR/VERW reject real mode without an operand transaction.

The reproducer initially fails on real-mode SLDT, which incorrectly writes its
destination instead of requesting #UD. The completed matrix uses valid system
descriptors so wrong privilege checks cannot hide behind invalid types.

| Check | Actual result |
|---|---|
| New `spk286_system_access`, both simulators | 2112 cases / 9144 checks in each |
| Existing `spk286_protected_system`, both | 538 checks in each |
| Existing `spk286_protected_ltr`, both | 23 checks in each |
| Existing `spk286_clts_privilege`, both | 13 checks in each |
| Microcode ROM / decoder, both | 304 / 263 checks in each |
| All focused microcode/compiler tests | 101 passed, including six new H01 tests |
| Independent active literal and canonical round-trip audit | Pass |
| Verilator RTL lint / generated consistency | Pass |

The bank covers all rows of the H01 matrix at CPL0..3, PE=0/1, all supported
register/memory forms, optional DS prefix, READY stalls and all timing policies.
Invalid memory operands and valid/null/TI LLDT/LTR selectors check fault
priority. Denied operations preserve GPRs, FLAGS, MSW, descriptor caches,
selectors and BUSY, with no operand or descriptor side effect. Allowed stores
and loads are checked for their exact values, including LTR's BUSY write.

Format 24 adds two generic controls and exactly eight microcode words. The old
format-23 literal remains frozen; its historical immediate-execution test now
reconstructs that literal, while the new H01 test independently verifies the
entire H01 image as that literal plus the eight specified insertions. H02 now
checks the next delta separately, retaining this format-24 fixture frozen.
The H01 audit fixture was constructed from that independent delta, not by
changing instruction expectations to fit RTL. No compatible protected-mode
physical SingleStep corpus is available for this matrix; native source and
Intel remain supporting/primary references respectively.

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_system_access
python3 -m unittest discover -s tests -p 'test_microcode*.py'
```

Logs: `build/h01-*.log`. Whole-project RTL regression, OS boot, Quartus synthesis
and physical protected-mode measurements remain outside this milestone.

## H02 subset — CLI/STI and scalar/string I/O privilege

Intel section 10.1 and the instruction appendices require CPL <= IOPL for
CLI/STI, IN/OUT and INS/OUTS when PE=1. Native 86Box's flag and I/O permission
paths support that rule. The 286 has no I/O permission bitmap. The new check
produces restartable #GP(0); real-mode execution remains allowed.

Before correction, a CPL1/IOPL0 CLI case retires instead of faulting. The
executor now suppresses IF and port controls on privilege denial. Eight
semantic ROM checks run after port capture and before any count/index, memory
or port side effect, including OUTS source reads. String iteration labels
follow the check; the existing protected REP-zero ambiguity is not resolved.

| Check | Actual result |
|---|---|
| New `spk286_iopl_access`, both simulators | 2772 cases / 49334 checks in each |
| Existing `spk286_scalar_io`, both | 452 cases / 24943 checks in each |
| Existing `spk286_string_io_lifecycle`, both | 424 cases / 38100 checks in each |
| Existing `spk286_string_io_zero_events`, both | 56 cases / 3665 checks in each |
| Existing `spk286_hlt_privilege`, both | 104 cases / 208 checks in each |
| Focused microcode/compiler tests | 105 passed, including four new H02 tests |
| Independent literal, canonical round-trip / generated consistency / RTL lint | Pass |
| Physical SingleStep FA/FB, E4..E7, EC..EF, 6C..6F samples | 1400 passed / 0 failed; real mode only |

The new bank covers all 16 CPL/IOPL combinations, all timing policies, READY
stalls, scalar immediate/DX byte/word I/O, CLI/STI with old IF=0/1, single/REP
INS/OUTS with DF=0/1, optional DS prefix, odd/even ports and allowed word-port
wrap at FFFF. Denied invalid string-memory controls additionally require
privilege denial before any operand access. It checks full GPRs, FLAGS,
restart IP, exact port counts/data/byte lanes and string destination bytes.
Denied operations cannot request a port cycle, modify IF, create STI shadow,
touch string memory or change CX/SI/DI.

The existing lifecycle fixture used an eight-word layout. Its reach helper now
uses nine words and starts repeated iterations after the one-time privilege
check. Adding pause/cancel/reset controls at that operation increases its
total from 400 to 424 cases; architectural register, memory, port and event
expectations are unchanged. The zero-event helper uses the same new length.

Format 25 adds exactly eight words (122 entries / 739 words). Its independent
fixture derives from the frozen format-24 literal, including label and branch
address shifts. Compiler checks reject missing, late, duplicate and
iteration-local privilege checks. Logs: `build/h02-*.log`.

```sh
SPK286_BUILD_DIR="$PWD/build/pm-targeted-20260930" SPK286_BUILD_JOBS=4 \
  bash scripts/test_units.sh both spk286_iopl_access
python3 -m unittest discover -s tests -p 'test_microcode*.py'
python3 -m tools.microcode.audit_microcode
```

The agreed H02 subset is complete. HLT was closed earlier; explicit LOCK and
protected zero-count REP privilege precedence remain open. Whole-project
regression, OS boots, new Quartus synthesis and physical protected-mode
measurements remain deferred.

## Final cumulative PCAT CPU-option check

After all four changes, RTL lint and the four new banks also pass with
`SPK286_P02_FETCH_CHAIN` and `SPK286_P05_PARALLEL_LIMIT_CHECK`, matching the
PCAT / 86Box integration options. Icarus results are respectively 158 / 216 /
2112 / 2772 cases, with the same check counts listed above. Logs are under
`build/pm-targeted-20260930/pcat-options/` and
`build/pm-targeted-pcat-lint.log`. This is a directed cumulative check, not a
whole-project regression or cycle-accurate hardware certification. H12's
outer-return range exception-vector discrepancy remains open as recorded above.

The four banks and lint also pass on the exact PCAT vendor RTL with the same
P02/P05 options and identical case/check totals. That variant retains PCAT's
pre-existing real-mode IP-wrap correction (`75a307d`), which is not introduced
or changed by these milestones. Its LOADALL/SALC source filenames and comments
were aligned to the standalone sources so generated source hashes and listing
locations pass `compile_microcode --check`; this changes no ROM words. Vendor
logs: `build/pm-targeted-20260930/vendor-options/`.

The existing Release 86Box/SPK286 backend was rebuilt against the PCAT vendor
source with `SPK286_PCAT_CPU_OPTIMIZATIONS=ON`. Its actual linker output was
installed at `D:/GitHub/86Box_dev/build/spk286/86Box-linux`, used by the existing
launchers. SHA-256:
`664de0fbd6223551e71dbe4eb6a029c12d8e90d6f889b79c705d5fa5ac16d365`.
Previous binary: `86Box-linux.pre-pm-targeted-20260930`. Build log:
`D:/GitHub/86Box_dev/build/spk286/targeted-fixes-build.log`.
No emulator session or OS boot was launched for this final preparation.
