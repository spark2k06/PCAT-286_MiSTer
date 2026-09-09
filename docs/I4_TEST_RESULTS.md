# I4 verification results

Date: 2026-09-09. Branch: `codex/spk286-xt-integration`.

## Reproduction

Run the complete portable I4 set from WSL:

```sh
bash scripts/test_i4_machine_events.sh
```

Run the adapter regression, including all seven failure-detection controls:

```sh
bash scripts/test_i2_bridge.sh
```

## Actual results

The I4 command completed successfully with these independent observations:

| Check | Simulator/boundary | Actual result |
| --- | --- | --- |
| Event diagnostic | Icarus, complete CPU/bridge with narrow documented PIC model | `beats=281`, PIC writes `5`, PIT writes `3`, INTA `2`, vector `20h`, max wait `5` |
| Event diagnostic | Verilator, complete CPU/bridge and unchanged production KF8259 | Same counts and vector; IRQ handler, IRET, HLT wake and controlled NMI/IRET passed |
| Withdrawn/spurious request | Icarus and Verilator, unchanged KF8259 | Masked IRQ1 stayed quiet; withdrawn IRQ0 returned spurious vector `27h` on second INTA |
| KF8288/PIC frontend | Icarus with narrow PIC model; Verilator with unchanged KF8288 and KF8259 | `beats=5`, `commands=5`; code, word serialization, two READY-delayed INTA commands, vector `20h` and address latch passed |
| HOLD/HLDA ownership | Icarus and Verilator, copied production arbiter with pin observers | `checks=12`; reset loader, runtime loader, DMA, disappearing request and reset recovery passed |
| Diagnostic signature monitor | Icarus and Verilator | `checks=5`; exact pass sequence, wrong marker, failure latch and reset passed |
| Production ROM loader | Icarus and Verilator | All 65,536 main bytes written from `F0000h` through `FFFFFh`; EGA mapping/presence and reset-hold release passed |
| Inherited focused regressions | Icarus | READY, EGA ROM presence and refresh/write collision: `3 passed, 0 failed` |

The same working state also completed the entire inherited chipset suite:
`17 passed, 0 failed, 0 did not build`. The I2 adapter control passed in both
simulators with `beats=20`, port writes `3`, INTA `2`; all seven deliberate
mutations were detected: wrong CODE status, swapped high byte, early word ACK,
duplicated port write, stale input, merged INTA and premature DMA grant.

The full event program reached these independent architectural effects:

- reset at native `FFFFF0h`, followed by the ROM far jump;
- PIC program sequence `20h:13h`, `21h:20h`, `21h:01h`, `21h:FEh`;
- PIT writes `43h:34h`, `40h:20h`, `40h:00h`;
- exact port-80 pass markers `70h,72h,71h,86h`;
- IRQ memory word `A55Ah` at physical `10600h`;
- main-line word `2864h` at physical `10604h`;
- controlled-simulation NMI word `2BADh` at physical `10606h`;
- interrupt frame `CS=F000h`, return `IP=005Ah`, saved IF set;
- unchanged guard bytes around data and interrupt-stack regions.

## Diagnostic artifact

- ROM: `tests/firmware/pcat286_event_diag.rom`
- Size: 65,536 bytes
- SHA-256: `2a562fc1a1624cd0f4425b0f943d9372f21ae5acb1838b115b5d76986993873e`
- Source: `tests/firmware/pcat286_event_diag.asm`
- Deterministic check: `python3 scripts/build_event_diag_rom.py --check`

## Evidence boundary

These are subsystem and machine-integration simulations. They instantiate the
real SPK286 CPU, generated microcode, bridge, and the named real peripheral
blocks, but model RAM/ROM/READY and do not instantiate vendor PLL, HPS or SDRAM
primitives. They are not claimed as complete MiSTer simulation or physical
validation.

The unchanged KF8259 plus the full SPK286 event program or 8288 composition is prohibitively slow
under `vvp` (a 600-second bounded attempt reached programmed HLT/IRQ assertion
but not INTA). Icarus therefore uses the checked narrow PIC model for the full
program and 8288 composition while the production KF8259 paths run under
Verilator. The short real KF8259 spurious-request test runs and passes in both
simulators. This division is explicit and does not replace the production component.
