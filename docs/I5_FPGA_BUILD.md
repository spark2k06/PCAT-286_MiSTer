# PCAT-286 AT FPGA build

The repository contains one Quartus project and one output directory:

```text
PCAT-286.qpf / PCAT-286.qsf
SYSTEM.sdc
files.qip
output_files/
```

Compile it directly with Quartus Prime 17.0.2 Lite:

```sh
quartus_sh --flow compile PCAT-286.qsf
```

The generated RBF and SOF are written to `output_files/`. The AT profile uses
`AT_PROFILE`, `SPK286_AT_CDC`, `SPK286_P05_PARALLEL_LIMIT_CHECK` and
`SPK286_AT_NO_DEBUG`; the latter three are kept in the organizational
`config.tcl` include.

Before a Quartus run, the repository checks can be run with:

```sh
python scripts/check_pcat_project.py
wsl bash -lc 'cd /mnt/d/GitHub/PCAT-286_MiSTer && bash scripts/test_at_profile_elab.sh'
wsl bash -lc 'cd /mnt/d/GitHub/PCAT-286_MiSTer && bash scripts/test_at_machine_boundary.sh'
```

`SYSTEM.sdc` contains the AT-specific constraints. Common MiSTer clocks and
I/O constraints remain in `sys/sys_top.sdc` and the imported `sys/` framework.
