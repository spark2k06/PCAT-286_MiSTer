# Validated compilation reuse in the third broad attempt

This attempt invokes the existing `make regression` in a complete frozen vendor
snapshot. Every Python/compiler test, vector generator and functional simulation
runs again. Icarus compiles again. Strict lint, simulator/state smoke, inherited
SingleStep smoke and Yosys run through the real tools. It is not a full fresh
Verilator compilation.

The only intercepted operation is the existing unit script's Verilator
`--binary` compilation. Eligible binaries came from dual-completed units in the
second attempt. Each has adjacent simulator PASS/finish lines, unchanged source
receipts and a previously recorded binary/compile-log SHA in a completed-unit
cleanup receipt. Six otherwise completed units without that historic hash are
compiled again. The changed adjust bank is explicitly never reusable.

Validation compares the original `__verFiles.dat` command with all current
arguments in order, normalizing only the absolute `--Mdir` output value. Both
output paths and the current frozen cwd are separately constrained. Every actual
RTL, testbench and include in the original DAT `S` closure must match its
original snapshot SHA. Build/compiler/vector-generator scripts are also pinned.
Original external Verilator input metadata, current version, toolchain/header
metadata and SHA, prior source/run receipts, original compile DAT, binary and
compile log must remain exact. Toolchain/header ctime must predate the second
attempt, so a later installation or edit causes fresh compilation.

A mismatch emits `COMPILE_CACHE_MISS` and executes the real unmodified Verilator
command. A valid hit copies only the compiled binary and its historic compile
log. The new `build.log` explicitly records `COMPILE_CACHE_HIT`; the older log is
separately labelled `historical-build.log`. The unchanged caller immediately
executes the binary with the newly generated vector paths. No PASS or simulation
output is copied as a new result.

Seventeen non-mutating controls validate one exact command and reject sixteen
alterations of flags/order/path/cwd, RTL/TB/include, binary/log/DAT/provenance,
runner script, tool version and eligibility. `cache-controls.json` binds them to
the exact wrapper and manifest. Non-binary forwarding was checked by executing
the real Verilator version command; the same literal exec branch forwards lint
and simulator/state compile calls in the actual final make run.

Final acceptance requires the actual make process to exit zero, a newly produced
`REGRESSION PASS`, unchanged origin/snapshot/corpus/cache hashes and unchanged
reused output binary hashes. The existing explicit expand-down simulator policy
is reported, rather than hidden. This is functional standalone regression, not
a complete physical-hardware/PCAT OS test, full external corpus, STA or fit.
