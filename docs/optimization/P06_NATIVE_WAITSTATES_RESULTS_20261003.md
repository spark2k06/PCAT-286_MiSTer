# P06/P12: native 286 controls with 1 and 2 memory wait states

Date: 2026-10-03. The user requested repetition of the
[automatic native reference](P06_NATIVE_REFERENCE_RESULTS_20261003.md) at actual
6 and 12.5 MHz with the visible 86Box wait-state options set to 1 and 2.
This is an additional emulator reference, not physical 286 timing validation.
There are no CPU/PCAT RTL, clock, RBF or historical-policy changes in this work.

## Setting interpretation verified in source and runtime

Local `D:/GitHub/86Box_dev/src/qt/qt_settingsmachine.cpp:91-101` stores
Default as `cpu_waitstates=0`; visible N wait states as N+1.
`src/cpu/cpu.c:4502-4508` uses config + 1 for native prefetch/read/write service
cycles when that override is active and cache overrides are absent.

| Selection | Stored `cpu_waitstates` | Prefetch/read/write service cycles |
| --- | ---: | --- |
| Automatic, 6 MHz | 0 | 2 / 2 / 2 (existing reference) |
| Automatic, 12.5 MHz | 0 | 3 / 3 / 3 (existing reference) |
| Visible 1 wait state | 2 | 3 / 3 / 3 (new controls) |
| Visible 2 wait states | 3 | 4 / 4 / 4 (new controls) |

The automatic 12.5 MHz setting therefore already has the same effective
memory/prefetch service costs as the visible 1-wait override. A raw config
value of 1 would select the visible **0-wait** option, not the requested 1 wait.
These costs are model service cycles; the override does not replace intrinsic
instruction timing or certify physical READY waveforms.

Runtime samples verified native `exec386_2386`, actual CPU speed, the config and
all three service costs. Both internal and external cache flags were observed
disabled. ISA remained 6 MHz at the 6 MHz CPU setting and 8 MHz at 12.5 MHz;
`timing_rr` remained 2. The same executable, source DOS disk and per-frequency
initial CMOS from the automatic bundle were used in fresh private images.

## Results

All four selected new controls have **guest exit 0 and host exit 0**, 42
validated samples and six recomputed summaries. The same frozen
`T286REF.COM` has SHA-256
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.
The native executable is unchanged, SHA-256
`2d87185ff14842a20a2bd0fed1713820dd64eabaa049b08a9827b48948de4dd3`.

Median gross elapsed **PIT input ticks**, fixed 256 iterations, seven samples
per case. Lower means less elapsed time for the same work. Gross includes
instrumentation/setup/loop/signature-store overhead; no baseline is subtracted.

| Actual CPU speed | Memory setting | R0 registers | B0 branches | M0 aligned RAM |
| --- | --- | ---: | ---: | ---: |
| 6 MHz | Automatic (previous) | 1339 | 1899 | 2153 |
| 6 MHz | 1 wait state | 2119 | 2221 | 2882 |
| 6 MHz | 2 wait states | 2492 | 2645 | 3510 |
| 12.5 MHz | Automatic (previous) | 1017 | 1066 | 1384 |
| 12.5 MHz | 1 wait state | 1017 | 1066 | 1384 |
| 12.5 MHz | 2 wait states | 1196 | 1270 | 1685 |

Median baselines R0/B0/M0 are 795/795/795 ticks at 6 MHz with 1 wait,
863/863/863 with 2 waits, 382/382/382 at 12.5 MHz with 1 wait and
414/414/414 with 2 waits. Full min/median/max and all raw repetitions are in
the [evidence bundle](../evidence/p06-waitstates-reference-20261003/README.md).
Gross spread is at most one tick for each new case/setting.

The 12.5 MHz 1-wait medians reproduce the automatic values exactly. With the
same override at both frequencies, these fixed-work times scale close to the
12.5/6 frequency ratio (for example, R0 with 1 wait is 2119/1017).
This explains why the earlier automatic controls did not share a simple
frequency ratio: their effective memory costs differed. Even R0 depends on
instruction fetch/prefetch and instrumentation stores; a register workload
does not isolate the execution unit from memory timing. This remains a native
86Box observation, not a rule imposed on the collaborator's board.

## Runner changes, unsuccessful attempts and limits

The runner now accepts the visible `--memory-wait-states` count, validates its
stored config/effective service costs and records cache flags. During bounded
startup it retries a null dispatcher with no CPU execution; a wrong initialized
backend is still rejected. The DOS program and validator are unchanged.

An initial concurrent batch contained two probes before native dispatch was
initialized, one complete host/guest-successful 6 MHz 1-wait control, and a
12.5 MHz 2-wait control with valid guest output but host exit −6. A further
6 MHz 1-wait repeat also produced valid guest output but host exit −6 and
`corrupted double-linked list` during teardown. Those receipts are retained
as unsuccessful/earlier controls, not selected full-run PASS results.
No root cause of the host heap corruption is claimed.

The four selected runs used the same final runner and paused the emulator via
its monitor **after guest measurement completion**, then requested exit.
All four then exited with code 0. This observation does not prove that pausing
repairs the underlying native-host bug. The original BIOS diagnostic at
F000:C3D4 and host library warnings remain visible in the archived logs.

All selected controls observed binary PIT mode 2 and retain NOT_CALIBRATED:
nominal input 1,193,182 Hz and assumed BIOS divisor 65536. The timer/crystal is
not independently calibrated and whole-period stalls are not excluded. Mode 3
still has only source/host arithmetic/synthetic-parser coverage in this series.
Physical 6/12 MHz results and historical-profile validation remain pending.
