# DMA hardware confirmation — 2026-09-12

The user reports that the previously failing DMA2 and DMA page-register
Landmark diagnostics now pass on MiSTer. The supplied screenshots are retained
here. Source commit: `98690c0`; all prior source-manifest hashes are unchanged.
No new RTL modifications or synthesis are part of this checkpoint.

The latest local AT_FAST RBF is archived as
`releases/PCAT-286_20260912_dma_hardware_checkpoint_AT_FAST.rbf` (SHA-256 `28B6712A7D13EC4D44DBB81E3486D1A1C9CDBF01F123BA826483550D60B530A9`).
The exact flashed-file hash was not independently supplied by the user.

Remaining displayed failures include timer channels 1/2, parity and the 16K
critical memory region. Checksum failures are excluded from the next fixes
at the user's request. The first-fault photograph is evidence for the next
investigation, not yet a diagnosis.
