# P06 bounded raw-CPU validation — 2026-10-05

The user explicitly deferred the full CPU regression. The interrupted run is
recorded as **USER_DEFERRED**, with partial results preserved in
[its evidence manifest](../evidence/p06-target-handoff-regression-deferred-20261005/manifest.json).
There is no full-regression PASS claim.

The replacement scope uses the existing standard raw SPK286 tests, a fresh
source snapshot, fresh simulator builds and the unchanged external SingleStep
corpus. All eight bounded stages passed in 236.161 seconds.

| Check | Result |
| --- | --- |
| Canonical generated consistency and strict full raw-CPU Verilator lint | PASS |
| Standard reset smoke, Verilator and Icarus | PASS in both |
| `spk286_core` state/fetch/redirect bank | PASS in both: 7 bus checks plus architectural cases |
| Standard initialization/first-fetch fixtures | PASS: 1 + 3 cases, no instructions executed |
| Existing stack/control SingleStep smoke | PASS: 470 cases across 47 opcode/group files |
| Existing Yosys proc/opt/check and fully mapped raw-CPU sanity | PASS |
| Compiled source, snapshot and read-only corpus identity before/after | PASS |

The SingleStep selector retains its existing exclusions. The log counts 235,000
discovered cases, 8,052 prefix exclusions and 354 exception exclusions; only the
470 selected samples were executed. This is sampled architectural coverage,
not the full corpus or a historical timing proof. Yosys reports its existing
warnings, but all `check -assert` stages and the standard synthesis script pass.

The snapshot contains 585 vendor files and binds 98 external corpus/revocation
files by SHA-256. Its live after-guard excludes only the new, unused
`spk286_length_boundary_tb.sv` bench that another agent was finalizing. No stage
here compiles that bench. The separate portable length-boundary packet binds
its final bytes and proves its ten cases in both simulators. The registry now
contains 132 Icarus banks and 131 Verilator banks; the existing expand-down skip
remains unchanged.

Two setup failures are retained: an unused bench changed before the first
source precheck, and the copied Verilator proxy initially pointed to the
previous, already deleted temporary directory. Both occurred before any CPU
build. The successful rerun uses a relative proxy path and unchanged standard
Verilator flags. It removes only completed, owned PCH files (272,493,857 bytes
in total) and does not reuse an old simulator binary.

The accepted packet is
[the bounded CPU evidence manifest](../evidence/p06-target-handoff-cpu-focused-20261005/manifest.json).
Its 739 archive members include frozen source, exact CLI/build logs, simulator
compile manifests, emitted state expectations/results, all 47 SingleStep
batches, and Yosys logs. Every archived member was read back and hashed before
cleanup. Archive SHA-256:
`99824ae2358e5cef3d2e3939f66907be55962a3b5e654195eb870814372ae0ed`.

After completion, no process remained in the owned snapshot. The full owned
temporary directory was removed; the compact 2,360,575-byte archive and its
manifest remain. This packet does not certify the complete regression,
machine-level historical scheduler, Quartus timing closure or hardware behavior.
