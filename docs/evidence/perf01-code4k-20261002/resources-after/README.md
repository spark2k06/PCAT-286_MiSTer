# Completed user fit of the 4 KiB candidate

`comparison.json` links the completed user fit, its report/RBF identities,
the frozen P10 reference, post-build current source hashes and entity mapping.
Full reports/RBF remain frozen locally in
`D:/GitHub/PCAT-286_MiSTer/build/perf01-code4k-user-fit-20261002/`.
This post-build capture is not a pre-build frozen-source attestation.

Original map/fit/STA summaries have a `.txt` suffix. Resource sections,
code-buffer RAM rows and entity estimates retain the cost comparison.
The code buffer rises from 277 to 7,456 dedicated registers. Its data uses
four M10Ks; tags have no RAM row. All 512 tag indices appear in clock-enable
logic; representative rows are retained. Controlled inference checks and
the correction have separate evidence.

Clock setup/hold values come from the existing STA summary; this is not a
fresh full path/constraint audit. Slow-corner setup remains negative.
