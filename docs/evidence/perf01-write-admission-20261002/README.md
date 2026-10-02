# P16 write-admission evidence

See [P16 scope and measured directed checks](../../optimization/P16_WRITE_ADMISSION_PROTOTYPE_20261002.md).

`source-manifest.json` records the 15 copied input files in each private root,
their original/variant hashes and the one changed owner. `owner-write-admission.patch`
reproduces the logical RTL difference against the P15 owner. These files retain
the first private milestone (`d90c168`), when production sources were unchanged.
The later `promoted/` record belongs to commit `95f5b21`: the user authorized
creating an RBF after the provisional integer result, while math continues.

The two simulator logs for each variant retain matching physical reads/writes,
values and byte-mask/address scoreboards. `directed-results.json` retains exact
commands and successful final source guards. The private adapter's manifest,
smoke and `smoke-results.json` retain six-clock writes versus seven, with
two-clock hits and unchanged read-miss behavior. `control-adapter-build.json`
identifies the completed P15 control; CPU object hashes match the candidate.

Frozen sources, executables and the running real guest remain under
`D:/GitHub/PCAT-286_MiSTer/build/perf01-write-admission-20261002/`.
`source-guards.json` describes the initial directed/build milestone. `promoted/`
retains 5666 provisional Dhrystones from stable output-buffer bytes and PASS
physical refresh/byte/burst, finite read-window and composed cancellation checks.
`measurement/` now retains complete CHECKNUM RC0/ALL_DONE/final-profile evidence:
**5666 / 102.9K**, versus **5525 / 102.4K** (+2.55% / +0.49%). The matched
CPU/configuration/disk/CMOS comparison also retains each classified host
monitor-exit timeout and SIGTERM after successful guest completion. No clean
host exit or hardware speedup is claimed. `fitted/` retains the completed frozen
full fit and artifact identities: +465 net equivalent ALMs, +149 registers,
no extra M10Ks; worst CPU setup -0.450 ns and all CPU hold positive. This fit's
HDMI setup/hold are positive. No whole-design closure or full regression is claimed.
The candidate RBF is at
`D:/GitHub/PCAT-286_MiSTer/build/perf01-write-admission-fit-20261002/work/output_files/PCAT-286.rbf`.
Only the owner differs in the common P15/P16 inputs; the +465 is a full-design
fit delta, while the owner including KFSDRAM increases by 11.2 equivalent ALMs.
The owner introduces an incoming-address launch path for ordinary writes.
86Box owns guest values/peripherals in the control co-simulation.
