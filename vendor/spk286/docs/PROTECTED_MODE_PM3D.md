# Protected Mode PM3d — Outer-Level IRET

Status: implemented as a bounded PM3d slice. This increment extends the
protected same-level `IRET` path with a return from the current privilege
level to a less-privileged non-conforming code segment.

## Implemented contract

For a protected `IRET`, the CPU now handles both same-level conforming-code
returns and the bounded outer-level non-conforming return. A conforming target
is validated with `DPL <= CPL`, ignores the saved selector RPL, retains the
current CPL/SS and consumes only the ordinary `IP:CS:FLAGS` frame. For the
outer-level non-conforming case, the CPU:

1. pops and holds saved `IP`, `CS` and `FLAGS`;
2. validates a present, non-conforming code descriptor whose `DPL` equals the
   saved selector `RPL`, with `RPL` no less privileged than the current level;
3. checks the saved `IP` against the candidate code-segment limit;
4. pops and holds the saved `SP` and `SS` words;
5. validates a present writable data descriptor whose `DPL` and `RPL` equal
   the target code privilege level; and
6. commits the candidate CS/SS hidden caches, `IP`, `FLAGS` and restored `SP`
   together.

Descriptor accessed bits are written before the corresponding hidden-cache
commit. Stack reads remain BIU-owned word transfers and retain READY,
alignment and segment-limit dependencies. A failed validation does not
install either candidate cache or the saved `SP`.

This slice does not implement privilege-changing event entry, task gates, full
protected fault classification or #DF escalation.

## Verification

`sim/unit/spk286_protected_system_tb.sv` covers coherent outer return of
`IP/CS/SS/FLAGS/SP`, execution in the restored ring-3 context, and a
conforming-code `IRET` with a deliberately different selector RPL followed by
a return to the ring-3 code segment. The protected system bench passes 100
checks in Icarus.
The protected system bench passes 100 checks in Icarus, including the inherited
PM3a/PM3b/PM3c coverage.

Microcode format 18 adds explicit `VALIDATE_IRET_CS`, `IRET_OUTER_FRAME` and
`VALIDATE_IRET_SS` operations. The authoritative source and generated ROM are
consistent at 117 entries and 668 words.

Historical timing remains separate from the functional BIU, READY and queue
dependencies exercised by this slice.
