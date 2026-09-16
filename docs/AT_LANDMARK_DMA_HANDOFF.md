# AT Landmark DMA investigation — 2026-09-12

## Preserved hardware checkpoint

Commit `6f07770` preserves the source state reported by the user to boot on
MiSTer, its prior audit evidence and the existing latest local RBF. No synthesis
or new RBF generation was performed in this investigation. The user will build
and test the next revision. The archived RBF and its hash are described in
`AT_BOOT_HARDWARE_CHECKPOINT.md`.

The next changes target the DMA diagnostics and improve observation of the
separate persistent `B:1` report. They do not claim a complete AT POST pass.
The user-selected SKIP_PM ROM is unchanged:
`SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_64K.BIN`, SHA-256
`E9A3F0605996FF6802F44AD1744675C01DF9B5832273BB7472C878A6AAD03EC6`.

## Reproduced page-register stop

The exact instruction at `F000:8D85` is `OUT DX,AL`. While waiting for its
completion SPK286 exposes `IP=8D86`. Landmark writes ports 81h through 8Fh and
then reads them back, repeating this for all 256 byte values.

Before the fix, `spk286_at_machine.is_dma_port` routes the complete 80h–8Fh
window to DMA, but `spk286_at_dma.is_page_port` recognizes only eight ports.
The fourth write, to **0084h**, has no accepting target. The bridge remains
in COMMAND (state 4), so no peripheral completion reaches the CPU. This is
an I/O decode deadlock; the instruction is fetched and decoded correctly.

Measured with the production CPU, bridge, arbiter, HPS loader, KFSDRAM and
physical SDRAM pin model:

| Measurement | Before | After |
| --- | --- | --- |
| Last completed page writes before 84h | 81h, 82h, 83h | 81h, 82h, 83h |
| Request at 84h | address 000084, byte enable 01 | accepted and completed |
| Accept / ready while stuck | 0 / 0 | no permanent wait |
| CPU at old stop | F000:8D86, opcode EE | routine continues |
| Whole original page routine | watchdog at 84h | 7,680 I/O completions, success branch |

The fix implements independent byte latches at every port 80h–8Fh. It also
corrects their connection to DMA channels: channel 0 uses 87h, channels 1/2/3
use 83h/81h/82h, and channels 5/6/7 use 8Bh/89h/8Ah. Port 80h no longer changes
channel 0's page. Port 8Fh is retained independently; connecting its historical
refresh address role to the functional refresh generator remains outside this
change. The physical SDRAM refresh commands are unaffected.

## Reproduced DMA2 diagnostic failure

DMA2 address/count decoding incorrectly included control ports D0h–DFh.
For example D0h was treated as channel 4 address, D8h as channel 6 address,
and DAh as channel 6 count. Consequently status reads at D0h returned FFh
from the programmed address register instead of status 00h. Landmark takes
its failure path after 356 I/O transactions.

The decode now limits address/count accesses to C0h–CFh. D0h and the other
control ports reach their intended handlers. The original routine now reads
00h at D0h twice and takes its success branch, after the same 356 transactions.
The following related register errors have direct regression coverage:

- One low/high byte pointer per controller toggles on reads and writes; clear
  pointer and master clear act on the selected controller only.
- Mask, request, clear-mask and master-clear state are independent for DMA1/2.
- Status returns per-controller request bits and latched terminal counts;
  reading status clears that controller's terminal-count flags.
- Controller-disable bit 2 gates DMA requests.
- DMA2's counter drives physical address bits 16:1; page bits 7:1 drive 23:17.
  The old expression discarded counter bit 0 instead of shifting the counter.
  Tests include 7FFFh→8000h, producing 2EFFFEh→2F0000h for page 2Fh.

No CPU fetch, SDRAM owner, loader, XT chipset or functional reset change is
part of this iteration. No claim of complete 8237A emulation is made: cascade
arbitration fidelity, memory-to-memory operation and all DMA modes still need
separate coverage. Odd DMA1 payload/lane handling at the memory boundary is
also a separate integration item; these DMA1 tests validate the existing
logical byte-transfer contract, not the electrical ISA byte lanes.

## B:1 is a separate unresolved observation

The user clarified that B:1 is present from startup, unlike XT's B:0. On AT,
`bridge_error` in the overlay is actually driven by `machine_protocol_error`,
which is the OR of CPU and peripheral errors. On XT it denotes the XT bridge
error. The existing indicators therefore do not have identical scope.

The page-register stop is reproduced with no protocol-error flag, so B:1 is
not required to cause it. Simulation holds the CPU while devices run for
1,024 cycles, then runs each DMA routine, with no unexpected error. An
additional original-reset-entry probe did not see a protocol error in its
20,000,000-cycle budget, but stopped at its watchdog in the initial display/
beep code around F000:9C11. It did **not** reach the later POST phases and is
recorded as an inconclusive investigation, not a passing full-BIOS test.
That probe also inherits the short first-fetch bench's limited PIT clock
stimulus, so it is not a faithful timer or full-boot measurement.

For any later stop, use the four live pages of **SPK286 Debug**: CPU, Registers,
Bus and Trace. They expose the current machine state and the rolling bus
activity without adding a retained diagnostic recorder to the production
design.

## Remaining visible diagnostic errors

The ROM checksum routine at F000:89D4 and F000:89FF sums every other byte of
F8000h–FFFFFh, separately for the two EPROM lanes. The original ROM has sums
00h/00h. The selected SKIP_PM ROM has **29h/D7h**. Its overall byte sum remains
zero, which explains why the existing patch script's combined checksum check
passes while Landmark reports ROM A/B failures. This evidence is from the
actual binaries and disassembly; it is not evidence of a new SDRAM read error.
The patch script and ROM are not altered in this iteration.

PIT channels 1/2 are loaded but never decremented by the present AT PIT.
Only channel 0 is in the decrement block. Latch/readback and clock-rate issues
also remain (the top supplies a 25 MHz counter clock). These are separate
functional limitations and have not been presented as repaired by the DMA
change. The next hardware run can reveal subsequent POST failures once the
page-register deadlock is removed.

## Timing of the user's existing booting build

From the new `output_files_pcat286_at_fast/PCAT-286_AT_FAST.sta.*` reports:

- Worst global setup: -21.537 ns (VCLK_SDIO); worst global hold: +0.054 ns.
- Slow 1100mV 100C SDRAM_CLK: setup +2.536 ns, hold +0.256 ns.
- FPGA_CLK2_50 setup summary: -7.569 ns. Its same-clock Fmax is 39.36 MHz,
  below the configured 50 MHz. The summary is not an individual CPU path
  report, so no exact CPU-path slack is inferred from it.

SDRAM timing constraints are now present, but this build still lacks whole-
project timing closure. Hardware boot success does not close that issue.
These numbers describe the user's previous fit, not the unsynthesized changes.

## Reproduction and hardware handoff

Run under WSL from the repository:

```sh
bash scripts/test_at_dma_registers.sh
bash scripts/test_at_landmark_dma.sh
bash scripts/test_at_bios_first_fetch.sh
bash scripts/test_debug_overlay.sh
bash scripts/test_at_profile_elab.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_a4_dma_refresh_pit.sh
bash scripts/test_a5_at_devices.sh
```

`test_at_landmark_dma.sh` defaults to the exact user-selected ROM. It executes
its two DMA routines independently by changing only the reset-jump entry in
the testbench's private ROM buffer (8C4Bh and 8D74h). Routine bytes and their
success/failure conditions are not changed. HPS loads the fixture through the
real owner and the SDRAM pin model. This is not a full POST or a modified ROM
for deployment. Outcome checks observe the MOV DX on the chosen result branch,
not a transient fall-through IP while a conditional jump is still executing.

The pin model and KFSDRAM addressing convention are unchanged from the boot
audit: row/bank/column decode, finite DQ validity and lane comparisons remain
active. External device accesses and complete board electrical timing are not
modeled. The direct register test adds distinct values at every page port to
catch aliasing that Landmark's same-value pattern alone would not detect.

Use a separate `PCAT_BUILD_DIR` when comparing alternative DMA implementations;
case 1 is the negative control and `AT_LANDMARK_CASES=2` exercises the 84h path.
The optional `AT_LANDMARK_CASES=3` is the bounded original-entry investigation,
not part of the default passing regression; its watchdog limitation is above.

For the next hardware run:

1. Build the usual AT_FAST profile. Give the new RBF a distinct name, for example
    `PCAT-286_20260912_dma_registers_AT_FAST.rbf`.
2. Load the same SKIP_PM ROM, then perform a core reset. Expect DMA2 and DMA
   page-register diagnostics to continue; this expectation needs board validation.
3. Capture the diagnostic screen showing the next stopping point or errors.
4. If execution stops, choose Debug Page **Bus** and take one additional photo.
   Include **CPU**, **Registers** and **Trace** if the machine state has changed
   from the current stop.

Final default regressions pass: DMA registers (8,311 I/O accesses, seven
channels and 14 transfer beats) in Icarus/Verilator; Landmark DMA2 and page
routines; first-fetch checks for four ROMs; XT/AT overlay
in both simulators; full AT profile elaboration; production-machine lint;
machine boundary; A4 and A5 device regressions. The existing A4/A5 machine
benches still warn about an unavailable splash ROM in their working directory;
those benches do not validate the raster image. The physical first-fetch and
Landmark benches resolve the production video ROM path.

No new RBF is generated or claimed validated here.

## Primary technical references

- IBM Personal Computer AT Technical Reference, system-board DMA description,
  address generation and page-register table, sections 1-9 through 1-11;
  [IBM 5170 Technical Reference scan](https://www.minuszerodegrees.net/manuals/IBM_5170_Technical_Reference_1502243_MAR84.pdf).
- Intel 8237A, register and software-command descriptions and Figure 6;
  [Intel 8237A data sheet](https://www.pcjs.org/documents/datasheets/intel/INTEL_8237A_DMA.pdf).
