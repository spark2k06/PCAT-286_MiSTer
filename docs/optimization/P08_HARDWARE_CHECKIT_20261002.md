# 50 MHz timing-closed build: MiSTer hardware observations

On 2026-10-02 the user explicitly confirmed the tested file was
`build/50mhz-closed-20261002/PCAT-286.rbf`, at maximum CPU speed.
Its SHA-256 is `22b6ee1e7384d9db43c8b241b5fdc6ca75e6e48c4d6847a5dae153f7964ea34b`.
These observations supplement the timing-closure evidence; that earlier
document describes the validation available when the bitstream was selected.

| Measurement | Earlier hardware observation | Timing-closed hardware | Change |
|---|---:|---:|---:|
| CheckIT Dhrystones | 4042 | 3946 | -2.38% |
| CheckIT Whetstones, thousands | 78.7 | 76.7 | -2.54% |
| CHECKNUM Dhrystones | 4143 | 3946 | -4.75% |
| CHECKNUM Whetstones, thousands | 78.1 | 76.7 | -1.79% |

Both programs agree on the current result. Against the initial hardware
CHECKNUM observation of 3584 / 72.2K, it remains +10.10% / +6.23%.
CheckIT displays 35.02 MHz as its software estimate; the fitted CPU clock
remains 50 MHz. Do not substitute the benchmark estimate for the PLL period.

The user also reports Windows 3.1, OS/2, games and other applications continue
to operate normally with this build. Game titles and additional workloads were
not specified. This is useful hardware compatibility evidence for those runs,
not a complete workload or CPU regression certificate.

The decrease is recorded without assigning a cause. Matching workload,
startup state and peripheral settings, repeated measurements and an exact
earlier RBF identity are needed before attributing it to an implementation
change. Positive setup/hold establishes the constrained timing margins;
it does not promise a higher aggregate benchmark score.

Evidence: [receipt and original screenshots](../evidence/hardware-checkit-20261002/receipt.json).
No RTL, project configuration or selected RBF was changed for this record.
