# P06/P12: native original-286 controls for all historical frequencies

Date: 2026-10-05. All seven actual native CPU frequencies now have Automatic
and visible-zero controls using the unchanged `T286REF2` program. Fourteen
selected controls have **guest exit 0 and host exit 0**, 588 validated samples
and 84 independently recomputed summaries. Twelve controls were executed in
this session; the strong visible-zero 6/12.5 MHz receipts were reused from
2026-10-04. Automatic 6/12.5 MHz were repeated because the older Automatic
runner had not sampled the cache flags.

## Native results

Elapsed **PIT input ticks**, medians of seven samples per case/kind with 256
iterations. Gross includes instrumentation, setup, LOOP and signature stores;
no baseline is subtracted. Lower ticks mean less elapsed time for this work.
All CSV samples report binary PIT mode 2. Each selected run's runtime receipts
observe disabled internal/external caches.

| Actual CPU MHz | Selection | Stored config | Prefetch/read/write service cycles | ISA Hz / ISA cycles | Baselines R0/B0/M0 | R0 gross | B0 gross | M0 gross | Receipt |
| --- | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 6 | Automatic | 0 | 2/2/2 | 6,000,000 / 1 | 728/728/728 | 1339 | 1899 | 2154 | New 2026-10-05 |
| 6 | Visible 0 waits | 1 | 2/2/2 | 6,000,000 / 1 | 728/728/728 | 1339 | 1899 | 2154 | Archived 2026-10-04 |
| 8 | Automatic | 0 | 2/2/2 | 8,000,000 / 1 | 546/546/546 | 1004 | 1424 | 1615 | New 2026-10-05 |
| 8 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 1 | 546/546/546 | 1004 | 1424 | 1615 | New 2026-10-05 |
| 10 | Automatic | 0 | 2/2/2 | 8,000,000 / 1 | 437/437/437 | 803 | 1139 | 1292 | New 2026-10-05 |
| 10 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 1 | 437/437/437 | 803 | 1139 | 1292 | New 2026-10-05 |
| 12.5 | Automatic | 0 | 3/3/3 | 8,000,000 / 2 | 382/381/382 | 1017 | 1066 | 1383 | New 2026-10-05 |
| 12.5 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 2 | 349/349/349 | 643 | 911 | 1034 | Archived 2026-10-04 |
| 16 | Automatic | 0 | 3/3/3 | 8,000,000 / 2 | 298/298/298 | 794 | 833 | 1081 | New 2026-10-05 |
| 16 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 2 | 273/273/273 | 502 | 712 | 807 | New 2026-10-05 |
| 20 | Automatic | 0 | 4/4/4 | 8,000,000 / 3 | 259/259/259 | 748 | 794 | 1053 | New 2026-10-05 |
| 20 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 3 | 219/218/218 | 402 | 570 | 646 | New 2026-10-05 |
| 25 | Automatic | 0 | 4/4/4 | 8,000,000 / 3 | 207/208/207 | 598 | 635 | 843 | New 2026-10-05 |
| 25 | Visible 0 waits | 1 | 2/2/2 | 8,000,000 / 3 | 175/175/175 | 321 | 456 | 517 | New 2026-10-05 |

`cpu_waitstates=0` is **Automatic**. The visible zero-wait override stores 1
and selects service costs 2/2/2. Automatic selects 2/2/2 at 6/8/10 MHz,
3/3/3 at 12.5/16 MHz and 4/4/4 at 20/25 MHz. These are native model service
costs, not the number of extra READY waits on physical pins. Intrinsic
instruction and prefetch timing remain active. The ordinary table entry
labelled `12` runs at **12,500,000 Hz**; this report does not call it 12 MHz.

The visible-zero controls provide a consistent memory-service comparison
across CPU clocks. Automatic changes the service cost at two frequency
boundaries, so its elapsed-time curve is not a pure frequency scaling curve.
Full min/median/max and every raw repetition remain in the evidence bundle.

## Direct comparison with the new MiSTer captures

The [2026-10-05 MiSTer analysis](../evidence/p06-mister-ready-chain-20261005/analysis.json)
associates the captures with the ready-chain candidate RBF. Its independently
loaded RBF identity remains unobserved, the clocks remain uncalibrated, and
the candidate's recorded fixed-50-MHz fit timing remains failed. The following
descriptive comparison pairs matching profile labels and identical fixed
work; it does not prove equal measured oscillators or identical board waits.
Native 12.5 MHz is compared directly with the MiSTer 12.5 profile; no physical
12 MHz scaling is used here.

Percentages are `100 * (MiSTer ticks / native ticks - 1)` for gross medians.
A positive value means MiSTer takes more elapsed time. Triplets are R0/B0/M0.
Each native reference retains its recorded service cost and ISA cadence.

| Profile MHz | MiSTer gross ticks R0/B0/M0 | Relative to native visible zero R0/B0/M0 | Relative to native Automatic R0/B0/M0 |
| --- | --- | --- | --- |
| 6 | 971/1429/1894 | -27.48% / -24.75% / -12.07% | -27.48% / -24.75% / -12.07% |
| 8 | 729/1073/1424 | -27.39% / -24.65% / -11.83% | -27.39% / -24.65% / -11.83% |
| 10 | 585/859/1141 | -27.15% / -24.58% / -11.69% | -27.15% / -24.58% / -11.69% |
| 12.5 | 468/688/913 | -27.22% / -24.48% / -11.70% | -53.98% / -35.46% / -33.98% |
| 16 | 369/540/753 | -26.49% / -24.16% / -6.69% | -53.53% / -35.17% / -30.34% |
| 20 | 300/435/666 | -25.37% / -23.68% / +3.10% | -59.89% / -45.21% / -36.75% |
| 25 | 253/376/561 | -21.18% / -17.54% / +8.51% | -57.69% / -40.79% / -33.45% |

Relative to the common two-service-cycle native controls, R0 and B0 take
less elapsed time in every MiSTer profile. M0 also takes less through 16 MHz,
then takes more at 20 and 25 MHz. This is workload-specific disagreement;
matching one headline throughput value would leave the other cases different.
Automatic's extra service costs at higher frequencies make its elapsed times
larger and therefore change the descriptive percentage comparison.

All 84 case/kind/selection comparisons, baseline medians, spreads, CSV hashes
and the MiSTer analysis hash are recorded in
[comparison.json](../evidence/p06-native-allprofiles-20261005/comparison.json).
The percentages use raw fixed-work gross values, with no baseline subtraction
or conversion into isolated CPU instruction cycles.

## Identity, environment and execution

Runtime samples verify the native `exec386_2386` dispatcher, actual CPU Hz,
wait-state config, all three service fields, both disabled cache flags,
`timing_rr=2`, ISA speed and ISA cycles. Each new run cloned the input VHD
into its own private image under `build/p06-native-allprofiles-20261005`,
booted plain DOS with `FILES=20, BUFFERS=10`, and ran the program from AUTOEXEC
without the source image's memory managers or TSRs. The board was
`[ISA] MR BIOS 286 clone` (`mr286`), 2 MiB RAM and IBM EGA.

The 2,840-byte DOS program SHA-256 is
`006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643`.
The original native executable SHA-256 is
`2d87185ff14842a20a2bd0fed1713820dd64eabaa049b08a9827b48948de4dd3`.
Its existing unused 50 MHz test entry remains part of that binary. Source base
is `fa3343da5b551bc937114c1e3ab3a8e16aed9e79`; all frozen backend-source and
selected ROM hashes match the 2026-10-03 archive before and after these runs.
The readonly input DOS VHD SHA-256 remained
`cc544775154d8f6093bb6075a21a00e3d391b979bd954ad811709d291555145f`.

Only a private diagnostic runner copy was extended to accept all seven Hz
values, record the initial config immediately, and accept archived initial
CMOS directories. The unchanged validator recomputes every CSV. Each owned
emulator was paused after guest completion and exited; process absence and
host code 0 were checked after every new run. No user VHD, unrelated emulator
instance, production CPU/RTL, historical policy, clock or Quartus output was
changed. No commits were made.

The 20/25 MHz controls required the observed MR BIOS oscillator-change
acknowledgment followed by F10 in setup before DOS boot. Each corresponding
receipt records those keyboard events; the native screenshots remain archived.
Both the selected guest CSV and host teardown subsequently passed. A first
8 MHz preparation attempt pointed at an archive containing `nvr-initial`
rather than `nvr`, and stopped before any emulator was launched; its receipt
and configs are preserved without the temporary disk. No measured control in this session failed
guest validation or host teardown.

## Evidence and limits

The [native evidence bundle](../evidence/p06-native-allprofiles-20261005/README.md)
contains raw CSVs, guest status, runtime/start/measurement receipts, hashes,
logs, initial/final configs, initial CMOS, new-run final CMOS, frozen source
and private runner. Its [manifest](../evidence/p06-native-allprofiles-20261005/manifest.json)
and [verification](../evidence/p06-native-allprofiles-20261005/verification.json)
identify reused versus newly executed controls. Executable/VHD copies were
temporary in the private build workspace and are excluded from this archive.
The temporary workspace is removed after archive verification; the original
native binary is retained outside it at
`D:/GitHub/86Box_dev/build/spk286/native-50mhz-reference/86Box-native`.

The PIT/crystal and reload are not independently calibrated: nominal input
1,193,182 Hz and divisor 65536 are recorded assumptions. Endpoints cannot
exclude whole-period stalls. No MHz inference, isolated instruction-cycle
claim, physical-board READY model or historical-profile certification is
made from these fixed-work measurements. The existing native BIOS diagnostic
at F000:C3D4 and host library warnings remain visible in the logs; clean guest
and host exits do not imply warning-free logs. The physical 6/12 MHz anchors
remain separately qualified in the prior physical report.
