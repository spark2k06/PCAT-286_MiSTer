# SPK286 H11: exception-delivery and double-fault support

Date: 2026-10-01. Baseline upstream `5791657`, PCAT `3516454`.

The vendor now delivers a second exception or #DF using the 286's first-vector
classification, pushes a zero error code for protected #DF, retains restart
context and EXT across replacements, and handles shutdown/NMI/RESET recovery.
Task-gate error pushes now await the memory response and SP commit. The
CPU's board interface and PCAT real-mode fetch-wrap customization are intact.

The inherited lifecycle test has an explicit downstream fixture profile:
set `SPK286_TEST_REAL_MODE_FETCH_WRAP=1` when running it in this vendor.
All 468 cases execute, with a successful wrapped immediate required at FFFE.
The old no-wrap assertion fails at case 463 on pre-H11 `3516454` as well.
The previously absent task-IRET/error fixtures are included for future checks.

Both simulators validate the new controller/CPU banks and affected task/event
paths with P01/P02/P05. The upstream check also passes 33,000 real-mode physical
event captures and all 10,000 D8/WAIT captures. Portable synthesis and lint
pass; FPGA timing and new hardware boot have not been checked in this milestone.

The existing 86Box executable is rebuilt from this vendor with P02/P05.
The profiles remain ready for the user's OS and hardware checks.

[Specification](../vendor/spk286/docs/PROTECTED_MODE_H11_DOUBLE_FAULT_20261001.md),
[receipt](../vendor/spk286/docs/REGRESSION_H11_DOUBLE_FAULT_20261001.json).
H11 is closed; H19's remaining boundary matrix, H15 and H20 remain separate.
