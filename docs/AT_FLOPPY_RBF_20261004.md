# Floppy DMA correction: new MiSTer candidate

## Delivered build

The newly generated bitstream includes these separate milestones:

- `a2853d5`: retain the normalized RAM-to-FDC DMA payload until the registered
  completion is consumed, with composed sector-write/readback tests.
- `f7587e6`: qualify the existing OSD/host write protection with a 32-case
  matrix in Icarus and Verilator. The menu already existed, so no duplicate
  option or new status bits were added.

RBF: `build/at-floppy-fix-wp-allfeatures-20261004/work/output_files/PCAT-286.rbf`

- Source snapshot HEAD: `f7587e6`, 1,344 preserved input files.
- Size: **4,134,436 bytes**.
- SHA-256: `3f3b12883c261068b582c1a7dc2c2037677a25bb02463d8974ffe88cf2c8eab3`.
- Generated: **2026-10-04 17:51:16 Europe/Madrid**.
- Quartus 17.0.2 Lite: **0 errors, 858 warnings; 30:16 full compilation**.
- All five configurable audio features remain enabled: SB, OPL2, C/MS,
  Tandy audio and MIDI. All eight CPU profiles remain available.

The snapshot includes the user's preexisting pending change to
`scripts/test_at_landmark_dma.sh`. That test-only change was preserved and
not included in our commits. Current CPU, profile, clock, configuration and
vendor files match the previous OSD build in all 588 compared inputs.
The compiled 1,024-word microcode ROM also matches its independent contract.

## Resources

| Resource | Previous OSD build | Floppy candidate | Difference |
| --- | ---: | ---: | ---: |
| Equivalent ALMs | 30,751 | 31,278 | +527 |
| Placed ALMs | 36,363 | 36,619 | +256 |
| Placed capacity | 86.76% | 87.38% | +0.61 percentage points |
| Fitted registers | 37,930 | 38,073 | +143 |
| Block-memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K blocks | 416 | 416 | 0 |
| DSP blocks | 39 | 39 | 0 |
| PLLs | 3 | 3 | 0 |

The new payload register maps to eight bits; synthesis register totals rise
from 36,075 to 36,082 (+7 net). The larger differences after fitting include
physical synthesis and placement choices across the complete design; they
are not a count of registers directly added by the source patch. CPU sources
and speed policy are unchanged. No resource fallback was required.

## Physical timing

The common physical CPU/bridge clock remains 50 MHz. Nominal historical
profiles do not relax this clock's timing constraints.

| Corner | Global setup | Global hold | CPU setup | CPU hold |
| --- | ---: | ---: | ---: | ---: |
| Slow 100 °C | -16.181 ns | +0.128 ns | -16.181 ns | +0.250 ns |
| Slow -40 °C | -16.531 ns | +0.024 ns | -16.531 ns | +0.240 ns |
| Fast 100 °C | +1.409 ns | +0.133 ns | +1.409 ns | +0.134 ns |
| Fast -40 °C | +2.747 ns | +0.074 ns | +3.995 ns | +0.117 ns |

Worst setup improves by 0.470 ns relative to -17.001 ns, while minimum hold
falls from +0.076 to +0.024 ns. Recovery and removal are positive at all four
corners. **This candidate does not close setup timing.** Timing closure was
not part of this floppy milestone and remains pending.

## Validation and hardware acceptance

The source-bound directed checks pass: five complete DMA sector writes,
four complete readbacks, original-wiring negative controls, DMA registers,
Sound Blaster component/detection, device-sector reading, all eight CPU
profile diagnostics, and the 32-case write-protection matrix. These are not
a full CPU/OS regression or physical SD-card persistence test.

On MiSTer, use a disposable copy of an image containing existing files:

1. Select **Write Protect: None**. COPY a new file, eject/remount and verify
   the old and new files and their contents.
2. Select **A:** or **B:** for the tested drive. COPY and FORMAT must report
   write protection; directory listing and reading must still work.
3. Repeat on the other drive and with **A: & B:**. OSD **None** must not
   override a host-readonly image.

The complete source identities, directed-receipt bindings, resource report,
compiled ROM and raw TimeQuest reports are archived in
`docs/evidence/at-floppy-rbf-20261004`.
The compile and TimeQuest containers completed and were removed automatically.

### MiSTer confirmation, 2026-10-04

The user confirmed correct floppy operation with this RBF and authorized
continuing the separate 25 MHz investigation. This accepts the reported
floppy correction in hardware. The confirmation does not specify each
write-protection combination; their coverage remains the directed simulation
matrix described above. Physical setup timing remains open.
