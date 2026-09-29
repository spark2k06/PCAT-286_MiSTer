# SPK286 protected return restart import — 2026-09-29

Upstream: `1635b379ba279605978d4f4d002759aeb2891192` on SPK286 branch
`codex/protected-mode-windows31`.

Windows 3.1 deliberately returns from its exception handler to a privileged
DOSX selector. The resulting #GP must preserve the client return frame so
DOSX can replace the selector and retry. The captured `043F:9F31` RETF
incorrectly advanced SP from 0FEC to 0FF0 before reporting #GP(00E0).

The imported executor change stages protected RETF and non-task IRET stack
reads until context commit. Outer-frame checks use the tentative cursor.
The accompanying synthetic CPU test covers 27 combinations of return form,
fault type and timing policy, including a ring-0 exception handler and retry.
The downstream fetch-wrap correction remains intact.

The directed test passes 81 checks in both Icarus and Verilator using this
vendor source. Verilator lint and generated microcode consistency pass.
86Box's WSL Release build also completes using this tree. Full regression
and synthesis were not run, following the user's bounded-validation request.
Windows desktop startup remains pending the next manual integration run.

Evidence: `vendor/spk286/build/return-restart-*.log` and
`86box_dev/build/spk286/return-restart-build.log`. The upstream diagnosis
documents the Intel restart contract and the corresponding 86Box behavior.

Upstream additionally passes protected RETF (62 checks), outer event/IRET
(6), direct CALL and absent-segment retry (300 checks / 144 cases), and
nested-task IRET (10), all in both simulators. The older vendor suite does
not contain the upstream protected RETF bank; its corrected negative
expectations are documented and validated upstream.
