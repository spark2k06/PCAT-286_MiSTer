# P16 private write-admission prototype evidence

See [P16 scope and measured directed checks](../../optimization/P16_WRITE_ADMISSION_PROTOTYPE_20261002.md).

`source-manifest.json` records the 15 copied input files in each private root,
their original/variant hashes and the one changed owner. `owner-write-admission.patch`
reproduces the logical RTL difference against the P15 owner. All production
sources are unchanged; this patch is an experiment, not a production selection.

The two simulator logs for each variant retain matching physical reads/writes,
values and byte-mask/address scoreboards. `directed-results.json` retains exact
commands and successful final source guards. The private adapter's manifest,
smoke and `smoke-results.json` retain six-clock writes versus seven, with
two-clock hits and unchanged read-miss behavior. `control-adapter-build.json`
identifies the completed P15 control; CPU object hashes match the candidate.

Frozen sources, executables and the running real guest remain under
`D:/GitHub/PCAT-286_MiSTer/build/perf01-write-admission-20261002/`.
`source-guards.json` describes this directed/build milestone. Full CHECKNUM is
pending; no score, new resource fit, FPGA timing closure or full regression is
claimed here. The owner introduces an incoming-address launch path for ordinary
writes; its fitted timing must be measured if real-guest performance justifies
promoting it. 86Box owns guest values/peripherals in the control co-simulation.
