# P06/P12 Intel extraction and contract receipt

Date: 2026-10-03. Documentation/source-review milestone, not an RTL test run.

The [manifest](manifest.json) freezes the identified primary manual revisions,
page numbering, actual T286REF kernel bytes, current PCAT boundary sources,
native 86Box sources and the selected FPGA baseline. Numeric instruction
facts and their conditions are explained in the
[Intel extraction](../../optimization/P06_INTEL_TIMING_REFERENCE_20261003.md).
The [pilot contract](../../optimization/P06_TIMING_CONTRACT_20261003.md)
contains the clock/capture/publication design and prepared directed checks.

Manuals were read from the existing local Intel reference cache. Selected
pages were rendered with Poppler to the ignored
`build/p06-intel-contract-20261003` directory and inspected visually. Full
manuals and rendered scans are not redistributed in this bundle. The
manifest pins each PDF's original bytes and one-based page numbers.

Actual COM byte ranges were read from the existing frozen executable and
checked against its NASM listing and source. The program and all previous
native measurements remain unchanged. Native source-to-handler dispatch was
reviewed for the accepted `exec386_2386` backend.

Checks at this milestone: source/artifact SHA-256 binding, instruction byte
ranges/branch targets, documentation link/page consistency and Git whitespace.
Prepared C01-C16 cases are `NOT_RUN`; historical RTL is `NOT_IMPLEMENTED`,
physical results `NOT_MEASURED`, and the DOS timer `NOT_CALIBRATED`.
No new synthesis, full regression or hardware validation is claimed.
