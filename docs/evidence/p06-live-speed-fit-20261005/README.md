# P06 live speed — fitted candidate, 2026-10-05

Status: **SETUP_OPEN_ORIGINAL_SDC_HOLD_POSITIVE; MISTER_NOT_RUN**.
Full regression: **USER_DEFERRED**.

The [manifest](manifest.json) binds the sealed archive, all 1,384 frozen inputs
at commit `a5d18f8`, the compiled ROM and the available RBF. Every archive
member was read back and compared before removing owned compiler temporaries.
The [cleanup receipt](cleanup.json) records the completed cleanup and retained
RBF hash. RBF/SOF are retained in the build output directory rather than Git.

The [result](result.json) and [resource hierarchy](hierarchy.json) record the
all-features seed-1 fit. The archive contains effective sources, compiler and
four-corner STA reports, launch scripts and directed functional receipts.
Three generated fixture source paths are explicitly bound to identical frozen
production files under `vendor/spk286/rtl/timed`; their hashes are checked.

Worst reported setup is **-6.051 ns**, an improvement of **0.938 ns** over the
preceding best completed fit. Hold is **+0.015 ns** with all original SDC
constraints on the identical fitted artifacts. The current additional
0.500 ns palette route requirement still misses by **0.065 ns**. Recovery and
removal are **+1.826 ns** and **+0.198 ns**. Setup and the extra palette
requirement remain open; this packet does not claim full timing closure.
The independent SDC audit verifies eleven fitted artifacts, including the
RBF, unchanged before and after analysis. Top-path reports are bounded;
tool-reported global worst slacks determine the margin summary.

The design uses **37,054 placed ALMs (88.4%)**, 38,207 registers, 416 M10Ks,
39 DSPs and three PLLs. All configured features, including OPL2, are enabled.
The physical resource comparison includes both intervening permission
localization and live profile switching, so it does not isolate the live
feature's fitted cost.

RBF: `build/p06-live-speed-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`.
SHA256: `cf554560dd1e125655da8876d58653fe1f27e4f26a3e406ae2a9870e15aab41d`.
Size: 4,102,344 bytes. The bitstream was delivered immediately after assembly,
before the container finished STA.

The [functional record](../../optimization/P06_LIVE_SPEED_20261005.md) describes
main-menu selection, safe application without reset, directed tests and the
remaining MiSTer validation.
