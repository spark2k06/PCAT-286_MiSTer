# Imported PCXT baseline build

The I0 baseline is the clean PCXT commit identified in
`SOURCE_PROVENANCE.md`, imported without its historical release artifacts. The
original Quartus project remains `PCXT-EGA.qpf` / `PCXT-EGA.qsf` and uses
`sys_top`, `PCXT-EGA.sv`, `files.qip`, `config.tcl` and the imported `sys/`
framework.

The upstream project records Quartus 17.0.2 Lite and targets the MiSTer Cyclone
V device through the standard `sys` assignments. On a host with that compatible
Quartus installation:

```sh
quartus_sh --flow compile PCXT-EGA
```

No Quartus executable was found on PATH during I0. Consequently, the imported
baseline was inventory- and hash-verified, but no new baseline synthesis, fit,
timing result or RBF is claimed at I0. Portable integration simulations do not
depend on Quartus.
