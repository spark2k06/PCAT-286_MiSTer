# MR BIOS warm reboot through Ctrl+Alt+Del

## Hardware-validated fix (2026-09-28)

The user confirmed that the PIC software-reinitialization correction resolves
the reported failure on FPGA hardware: Ctrl+Alt+Del now restarts MR BIOS
successfully on every attempt in their testing. The number of attempts was
not specified. The earlier 8042-only correction had not resolved the failure.

The project contains the validated PIC correction and its regression tests.
Open `D:\GitHub\PCAT-286_MiSTer\PCAT-286.qpf` in Quartus and run
**Processing > Start Compilation**. The existing configuration selects the
normal 50 MHz, no-debug profile. No macro changes are needed. The resulting
bitstream will be `D:\GitHub\PCAT-286_MiSTer\output_files\PCAT-286.rbf`.
Hardware validation was reported by the user after the project was prepared
for manual synthesis; no new fitting or timing report was collected here.

The imported KF8259 cleared pending request latches on ICW1, but retained its
in-service register (ISR). MR BIOS jumps out of its Ctrl+Alt+Del IRQ1 handler
without EOI. In the integrated IRQ restart fixture, the first warm POST reaches
`0Bh`, but a subsequent PIC initialization leaves IRQ1 in service. IRQ0 still
runs, while the next Ctrl scan code remains in the 8042 output buffer and
IRQ1 is blocked. This is reproducible in RTL simulation without FPGA timing
effects. The local 86Box `pic.c` clears ISR on ICW1.

`KF8259_Control_Logic.sv` now clears all ISR bits on ICW1 and suppresses any
simultaneous service latch. This uses the existing clear path and applies to
both master and slave. The regression reads ISR through OCW3, reinitializes
without EOI, verifies ISR is zero and verifies fresh IRQ delivery. Before
the fix it fails with `port=0020 data=0002 expected=00`; after the fix it
passes for both IRQ1 and cascaded IRQ8.

The simulation establishes the PIC defect, and the user's hardware test
confirms that the correction resolves the reported reboot failure. The exact
instruction sequence leading to the earlier photograph at `F000:EC0A`, POST
`0Ah`, was not reproduced in simulation; that diagnostic detail remains open.

Phoenix A286 1.01 (SHA-256
`306ac7c3a0ee713385de53f5dd0625ee040f3ea6606b09e9d5fce3c6a00b273e`)
also writes `1234h` to `0000:0472` at `F000:8C75` and jumps directly to
`F000:E05B` / `F000:611D`. Consequently, the difference cannot be explained
simply by claiming that Phoenix performs a hardware reset while MR BIOS
jumps. The PIC defect is demonstrated independently; its role in the
observed difference between these BIOSes remains unproven.

The Intel [8259A datasheet](https://pdos.csail.mit.edu/6.828/2010/readings/hardware/8259A.pdf)
describes initialization and IRQ priority/service behavior; the explicit ISR
clearing comparison above is with the inspected local 86Box implementation.

## ROM path

The 64 KiB `MR_BIOS_1.65_286_64K.ROM` supplied for this investigation has
SHA-256 `6f936ee53ba58663d1ccc7b80b1f5caba841f3f816c4dca15477ca540f9f252f`.
Its Ctrl+Alt+Del keyboard handler does not issue an 8042 `FEh` reset pulse.
At `F000:F47E`, scan code `53h` selects the conventional `1234h` warm-boot
marker at `0040:0072` and jumps to POST entry `F000:C2E6`. Scan codes `01h`
and `1Ch` select `1235h` and `1236h` for other keyboard shortcuts. The POST
entry checks the 8042 system flag and CMOS shutdown byte before continuing.
Later POST issues the 8042 `AAh` self-test and expects `55h` at `F000:A550`
onward.

## Core discrepancies

The 8042 previously handled `AAh` by setting only the system flag and posting
`55h`. It retained the pre-reboot command byte, keyboard-enable state and
output port. Thus its reply could still assert IRQ1, and key releases could
resume delivery under the pre-reboot configuration. The local 86Box AT
keyboard-controller implementation (`src/device/kbc_at.c`) reinitializes the
command byte to `10h`, inhibits keyboard input and sets output port `CFh`
during this self-test. It also stores the status system flag separately from
the command byte, so the flag survives the `10h` reinitialization. The core
now models these effects.

The existing AT286CTL warm-boot event already recognizes the `1234h` marker
used by Ctrl+Alt+Del. It only clears the optional VGA13 setting; it does not
reset the CPU. The 8042 correction improves controller fidelity, but a user
test of the resulting RBF showed the original black-screen hang still occurred.
The controller self-test correction alone was insufficient to resolve it.

An initial black-screen photograph was taken with an older debug RBF. It
showed POST `03h`, `CX=08C9`, a completed memory read at physical `FA4AEh`,
and `HLDA=1` with refresh granted. The subsequent diagnostic RBF used the
same source as the failed production RBF. Its first Ctrl+Alt+Del succeeded;
the second left a black screen. The photograph at that point showed
`F000:A4A8`, opcode `E2h`, micro-PC `055h`, `CX=28A5`, POST `0Ah`, CPU
`VLD=1`, bridge state `6` (COMPLETE), and `SNAP=45`. The user observed that
*all* fields, including `SNAP`, remained unchanged until `Reset & Apply`.

`SNAP` counts transfers from the 50 MHz observation domain to the video
domain and should update dozens of times per second. The visible frozen
value does not prove that the CPU, bridge, or system clock stopped: the
overlay uses EGA-derived pixel enable and sync, so a stopped or invalid EGA
raster can freeze the last frame while its internal counters continue. The
bridge COMPLETE state is ordinarily transient and cannot be diagnosed from
a single frozen frame. A diagnostic raster independent of the EGA CRTC is
needed to distinguish a CPU stall from a video-output stall.

Two subsequent diagnostic RBFs were built. A 25 MHz CPU-only version
(`build/at-debug/20260927-mrbios-div2`) still produced a frozen black frame
on hardware, with `F000:8FEE`, POST `0Ah`, bridge state `6`, and `SNAP=FE`.
That build retained the EGA-dependent diagnostic raster, so the captured
frame could be stale. Its CPU-internal timing passed, but several CPU-to-bridge
and memory-port paths still failed setup. It cannot exclude a timing cause.
The second
version (`build/at-debug/20260927-mrbios-stable-raster`) leaves the CPU at
50 MHz and, only when the debug display is enabled, generates its own
640-by-400 diagnostic raster at about 71 Hz. It drives the MiSTer pixel
enable and sync from that raster, and renders the overlay on black so it
remains readable if the EGA raster stops. Four photographs of one failed
restart show `SNAP` advancing (`F2`, `D7`, `79`, `A3`) while the CPU remains
at `F000:EC0A`, opcode `F4h`, `HLT=1`, POST `0Ah`, `CX=0000`. The system and
diagnostic video clocks remain live. The processor has executed a HLT.

Disassembly of this exact ROM identifies POST `0Ah` at `F000:A63D`, followed
by the first-64-KiB memory routine at `F000:8FD0`. The routine has two paths.
The warm marker `1234h` makes POST write `20h` to scratch port `8Ch`; this
port is implemented by the DMA page-latch register file, including scratch
latches. In that warm path, the routine only clears 64 KiB with `XOR AX,AX`
and `REP STOSW`, then returns. It skips the cold-boot pattern comparisons.
Both paths should return to `F000:A64B` with carry clear and emit POST `0Bh`
at `F000:A69B`. A carry-set return dispatches to an error message, then
`F000:EC04`, whose `HLT` at `F000:EC09` leaves IP `EC0A`.

The photographs establish the final HLT and last observed POST code. They
do not establish whether the warm marker was recognized, which path ran,
or whether carry/return state was corrupted. In particular, the halt alone
is insufficient to claim a physical RAM-cell failure. Capturing the memory
routine's branch and return state is necessary to distinguish these cases.
The user reports that only a few Ctrl+Alt+Del attempts succeed, while core
startup and Reset & Apply always succeed.

The diagnostic 50 MHz fit has a -3.148 ns CPU-to-CPU setup path from the
prefetch queue through segment checking to GPR writeback. CPU-to-bridge,
memory-port and owner paths are also close to or beyond their limits in
diagnostic builds. This is a plausible source of hardware-only corruption,
not a demonstrated cause. A parallel per-segment comparison experiment passed
SAT equivalence and simulation but did not close timing: its no-debug fit
has -3.492 ns CPU setup, versus -3.722 ns in the preceding no-debug build.
The experiment is archived in
`build/at-no-debug/20260927-mrbios-parallel-limits2`; its source changes were
removed from the working tree because it does not establish a reboot fix.

## Verification

- `scripts/test_a5_at_devices.sh`: Icarus and Verilator pass; the test checks
  command-byte `10h`, output-port `CFh` and keyboard inhibition after `AAh`.
- `scripts/test_at_keyboard.sh`: Icarus and Verilator pass, including queued
  events across a controller self-test and subsequent BIOS reconfiguration.
- `scripts/test_at_machine_boundary.sh`: production lint and machine-boundary
  simulation pass.
- The actual MR BIOS ROM passes three consecutive POST `0Ah` to `0Bh` tests
  in the machine/SDRAM simulation when RAM is preserved and only the CPU is
  reset. It also passes three direct jumps to the POST entry `F000:C2E6`,
  without resetting CPU or chipset, and the ROM's native jump at `F000:F49A`.
  This initial machine fixture bypasses the production SDRAM read buffer.
- The separate first-fetch fixture includes the production 512-byte code
  buffer, real PIC and SDRAM pin model. Three native jumps also pass there:
  `MRBIOS_P03_RESTART_PASS restarts=3 hits=610068 misses=566 refresh=29605`.
  Every warm memory return has `FLAGS=0046`, `CX=0000`, scratch port `8Ch=20`.
  These tests still enter the restart directly rather than via an IRQ1.
- `scripts/test_a3_interrupts.sh`: production Verilator regression now also
  checks ICW1 after abandoned IRQ1 and cascaded IRQ8 service; both pass. The
  Icarus PIC run uses its simpler model and does not cover the new ISR test.
- `scripts/test_at_pic_init_probe.sh`: the BIOS PIC programming probe passes.
- `scripts/test_at_profile_elab.sh`: the current no-debug AT profile passes.
- `scripts/test_at_mrbios_restart.sh` builds a RAM-only environment with real
  IRQ0/IRQ1 delivery and invokes the original ROM's Ctrl+Alt+Del handler.
  It uses the production PIC, code buffer and SDRAM pin model. The second
  variant interrupts `REP MOVSW`; the test checks that the copy actually ran.
  Each variant checks three warm returns through POST `0Bh`, not a full DOS
  boot. The ROM is hash-checked and never patched. Logs are saved in the
  selected `PCAT_BUILD_DIR` (`build/at-mrbios-p03-restart` for this run).
  Both variants pass with the PIC correction: three restarts each, nine
  timer interrupts per variant. The REP variant completes 75 copy writes
  across the interrupted workloads. All warm returns have `FLAGS=0046`
  and scratch `8Ch=20h`. Summary: `build/mrbios-restart-after.log`;
  detailed traces: `irq.log` and `irq-rep.log` in that build directory.
- `scripts/test_at_phoenix_pm87.sh`: the original Phoenix protected-mode
  continuation still passes with A20 closed after its warm reset.
  The fixture was rerun with the PIC correction and the same
  first-fetch simulator: `PHOENIX_PM87_PASS resets=2 destination=a55a
  PE_reset=1 A20_closed=1 cycles=5802` (log
  `build/mrbios-pic-phoenix-pm87.log`).
- `scripts/test_at_phoenix_fdc_post.sh`: the full Phoenix POST regression
  passes.
- `scripts/build_at_no_debug.sh`: Quartus completed and generated an RBF. The
  slow-corner global setup report still has negative slack (`-5.263 ns`);
  the preceding `20260924-framebuffer-cdc-r9` build had `-7.007 ns` on that
  report. The worst current paths are video synchronization and CPU reset,
  outside the changed 8042 logic.

The earlier non-debug RBF at
`build/at-no-debug/20260927-mrbios-cad/work/output_files/PCAT-286.rbf`
predates the PIC correction and still failed on hardware. It is retained as
an investigation artifact, not the validated result. On 2026-09-28 the user
confirmed that the subsequent PIC correction makes Ctrl+Alt+Del restart
MR BIOS reliably.
