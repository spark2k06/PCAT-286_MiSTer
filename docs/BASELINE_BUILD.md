# PCAT-286 project build

The checkout is intentionally scoped to the single PCAT-286 AT profile. The
project files are `PCAT-286.qpf`, `PCAT-286.qsf`, `SYSTEM.sdc`, `config.tcl`
and `files.qip`; inherited PCXT project revisions are not part of this tree.

With Quartus Prime 17.0.2 Lite installed, build with:

```sh
quartus_sh --flow compile PCAT-286.qsf
```

Artifacts are emitted under `output_files/`. The AT-specific source manifest
and constraints are kept separate from the common `sys/` framework so the
project retains the original organizational layout while targeting only the
current AT machine.
