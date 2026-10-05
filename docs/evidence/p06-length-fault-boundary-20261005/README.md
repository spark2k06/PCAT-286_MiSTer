# Legal ten-byte RAW-completion boundary proof

Date: 2026-10-05. Frozen production dependencies are bound to commit `b155891`; the only corrected functional CPU difference excludes RAW/event completion from an eleven-byte demand.

The old CPU reproducibly raises an unintended #GP for four DS prefixes plus `C7 06 20 07 34 12` (ten bytes). The corrected CPU passes 76 normal encoding/transfer/stall probes and five event probes in both Icarus and Verilator. An eleven-byte prefix/opcode target still raises #GP at target IP 0501; invalid 0F FF raises #UD, a pending source trap wins before that invalid target, and NMI/INTR retain target boundary frames. All stimulus uses public CPU ports. This proof is separate from the broader regression and new historical handoff acceptance.

The compact packet retains every frozen functional SV input, unchanged public signal header, exact bench/scripts, raw compressed old/new streams, bounded context diagnostics, logs and receipts. It contains no compiler objects.

From the project root under WSL/Linux:

```sh
mkdir -p build/p06-length-boundary-replay
tar -xzf docs/evidence/p06-length-fault-boundary-20261005/p06-length-fault-boundary-20261005.tar.gz -C build/p06-length-boundary-replay
python3 -B build/p06-length-boundary-replay/p06-length-fault-boundary-20261005/reproduce.py --output build/p06-length-boundary-replay/run
```

The frozen replayer compares all Icarus result/trace identities to the sealed receipt. It requires Icarus installed and uses no current production RTL. The receipt also retains original Verilator acceptance; complete CPU regression remains required before committing the functional patch.
