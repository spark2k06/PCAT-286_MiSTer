# Detected Environment

Date: 2026-09-05

## Repository

- Windows working tree: `D:\GitHub\SPK286`
- WSL path to the same tree: `/mnt/d/GitHub/SPK286`
- WSL distribution: Ubuntu 24.04.4 LTS, WSL2
- WSL kernel: `6.6.87.2-microsoft-standard-WSL2`
- Git branch at discovery: `main`, clean, tracking `origin/main`
- Git remote: `https://github.com/spark2k06/SPK286.git`
- Git `core.autocrlf`: `true` in the existing configuration; repository
  attributes now force LF for source/scripts

## Tools

| Tool | Version / result |
| --- | --- |
| Windows Python | 3.14.6 Microsoft Store shim |
| Windows Icarus | 12.0 development build from `C:\iverilog` |
| WSL Git | 2.43.0 |
| WSL Python / pip | 3.12.3 / pip 24.0 |
| GCC / G++ | 13.3.0 |
| Make | 4.3 |
| CMake | 3.28.3 |
| Ninja | 1.11.1 |
| Verilator | 5.020 |
| Icarus / VVP | 12.0 stable |
| Yosys | 0.33 |
| GTKWave | 3.3.116 |
| Docker client/server | 29.1.3 |
| Quartus | not installed in WSL; available in Docker |

The WSL packages installed for this project were `verilator`, `iverilog`,
`yosys`, `cmake`, `ninja-build`, and `gtkwave` plus their package dependencies.

## Docker and Quartus

Docker is reachable from WSL. The local image is:

```text
raetro/quartus:mister -> Quartus Prime Shell 17.0.2 Build 602 (Lite)
image size: approximately 10.8 GB
```

The image was sanity-checked with `quartus_sh --version`; no full FPGA compile
was run during Phase 0.

## Reference data

No `SingleStepTests/80286` checkout was found under `D:\GitHub`. The loader
accepts a configured external path and the checked-in tests use a tiny fixture.
No MCL86/z386/S80186 checkout was added to the SPK286 tree.
