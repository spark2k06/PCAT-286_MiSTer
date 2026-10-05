# PCAT-286 — remaining work

Updated: **2026-10-05**. This is a current backlog, not authorization to start
additional implementation or tests. ATF and H identifiers retain the existing
stories; delivery labels below organize their machine-level follow-up.

The first functional P06/P12 product is accepted. Its profiles, main-menu OSD
selection and safe live switching are excluded from this backlog. Further
historical precision is a separate future story. Previously accepted MAX,
CPU configuration and floppy work, and the closed NSSI report, are not reopened.

Priorities: **P0** current closure work; **P1** next concrete qualification or
correction; **P2** subsequent coverage/documentation; **P3** future precision.
A deferred item stays deferred regardless of its priority.

## 1. Current delivery and verification

| Story | Priority / status | Acceptance condition |
| --- | --- | --- |
| **P05/P21 — remaining HDMI setup closure** | P0, **PAUSED_AFTER_CURRENT_FIT** | The common 50 MHz CPU/bridge/SDRAM paths now close setup and hold. On resumption, address only the measured cold HDMI scaler path at -0.063 ns; retain positive hold, recovery/removal and constraint coverage at all four corners. Preserve behavior, clocks and enabled features; bind reports, sources and RBF/SOF identities. |
| **HW01 — new timing candidate on MiSTer** | P1, when the user has board access | Confirm that the selected physical candidate preserves the accepted boot, applications and profile behavior. Bind observations to its RBF and configuration; this does not reopen the OSD/profile implementation. |
| **QA01 — full current-source regression** | P1, **PAUSED_BY_LATEST_USER_INSTRUCTION** | The earlier authorization after global timing closure is retained for future resumption. The newer instruction pauses after the current result; no full regression is run now. On resumption, use the same frozen candidate sources and actual registered banks, with performance options active. Keep CPU, machine and tooling outcomes distinct; bounded checks are not a complete-regression PASS. |

The selected stack DATA / scaler HACC candidate is the best equivalent fit
with positive hold. CPU setup/hold minima are **+0.486 / +0.120 ns**; the
entire common 50 MHz domain, including incoming paths, has **+0.164 /
+0.110 ns**. Recovery/removal minima are **+1.710 / +0.197 ns**. Global hold
is positive at all four corners, with a minimum of **+0.027 ns**. The sole
remaining negative setup is cold HDMI `ascal|o_ihsize[3]` to
`ascal|o_hacc_next[12]`, **-0.063 ns**. Placed ALMs are **36,701 / 41,910
(87.57%)**, 195 fewer than the null-segment parent, with unchanged RAM,
DSP and PLL totals. All features remain enabled. Complete source-bound
evidence and the best RBF are retained; the latest requested pause applies
to further fits and full regression.
Closure must retain the constraints rather than replace a failing requirement
with a sign-off claim.

If placement fails for resources, the user-approved first fallback is to
disable OPL2 **only in config.tcl**, preserving its RTL and reactivation path.
This is a contingency; the current candidate retains all enabled features.

Sources: [selected physical candidate](../docs/optimization/P06_STACK_DATA_HACC_20261005.md),
[preceding deadline-fold candidate](../docs/optimization/P06_DEADLINE_FOLD_20261005.md),
[preceding fit](../docs/optimization/P06_LIVE_SPEED_20261005.md),
[bounded CPU checks and deferral](../docs/optimization/P06_CPU_FOCUSED_VALIDATION_20261005.md),
[resource attribution/fallback](../docs/optimization/PCAT_RESOURCE_BREAKDOWN_20261004.md).

### Dated fixture follow-up within the deferred regression

The [2026-10-02 regression record](../docs/optimization/P18_P19_FULL_REGRESSION_20261002.md)
retains two unresolved qualification boundaries:

- The second MRBIOS restart **fixture** invocation times out. Its CPU, cache
  or fixture cause is unclassified; reduce it without weakening the original
  checks. The user's working MRBIOS reboot is accepted. This is not a renewed
  hardware/BIOS bug or the closed NSSI issue.
- Four Landmark workload entry points require exact ROM inputs that were
  absent. Supply those identities if those gates are to run; retain
  NOT_EXECUTED where unavailable rather than substituting a different ROM.

The historical compiler adapters have since been
[repaired](../docs/optimization/SPK286_MICROCODE_REGRESSION_REPAIR_20261004.md).
Retired IDEAL_OWNER counterfactual modes are not current release gates.

## 2. Open functional chipset stories

The 2026-10-03 manufacturer/86Box audit records seven concrete source
contradictions. Their relevant paths remain present in the inspected RTL.
None has a newly accepted directed reproduction/correction yet. Each story
starts with an independent expectation and minimal executable reproducer;
only then is a correction selected and its resource cost measured.

| Story | Priority | Finding and acceptance condition |
| --- | --- | --- |
| **ATF01 — DMA terminal address/count** | P1 | The non-autoinit terminal branch masks the channel without the documented final address advance/count underflow. Execute count=0 and read back address/count; cover increment/decrement, byte/word channels, page behavior, TC and autoinit. |
| **ATF02 — RTC SET clears UIE** | P1 | Apply the MC146818A SET side effect. B=12h followed by B=92h must read as 82h; preserve periodic interrupt behavior and resume updates when SET clears. |
| **ATF03 — PIC special mask** | P1 | OCW3 ESMM authorizes that command to change SMM; OCW1 must still update IMR. Cover68h entry, IMR writes/readback, 0Ah/0Bh reads preserving SMM, 48h exit, masked-ISR priority, EOI and cascade using production KF8259. |
| **ATF04 — RTC UIP/update window** | P2 | Replace hardwired UIP=0 with the documented observable update window and completion UF/IRQ8. Define the transition contract first; cover rollover, SET during update, C acknowledgement and periodic interrupts during SET. |
| **ATF05 — DMA request lifetime** | P2 | Single must reservice held DREQ, block must retain service after initial DACK, and demand must suspend/resume. Verify mode-specific traces without losing LOCK or accepted-operation draining. |
| **ATF06 — DMA cascade/priority** | P2 | Make low-controller service depend on master channel 4 mask/mode/enable and hierarchical selection. Cover suppression/restoration without changing address/count, simultaneous requests and programmed priority; preserve data oracles when correcting bench setup. |
| **ATF07 — speaker with GATE2 low** | P1 | Speaker data bit 1 and GATE2 have separate roles. Check mode 3 OUT2 with GATE2 low and bit 1 modulation at the digital output; preserve ordinary tone and mode 0/PWM before considering audio filtering. |

Complete source/manual references and proposed cases are in the
[AT functional audit](../docs/AT_FUNCTIONAL_REFERENCE_AUDIT_20261003.md) and
[PIC follow-up](../docs/HARDWARE_FOLLOWUPS_20260930.md#1-pic-special-mask-mode-pending-functional-review).
For DMA cascade and the ATREF01 word-decrement discrepancy, the inspected
86Box paths are comparison evidence, not a sufficient hardware oracle.

## 3. CPU-only remaining work

Protected-mode and CPU evidence follow-ups belong to SPK286 and are maintained
in its [current remaining-work record](../vendor/spk286/docs/REMAINING_WORK.md).
That record owns the partial H02 scope, H05, H17, the remaining H19 matrix and
H20; their detailed matrices are not duplicated here. Future CPU changes must
be validated upstream and synchronized into PCAT with matching sources and
receipts. Working Windows/OS2 is integration evidence, not closure of every
protected-mode combination.

The existing [global CPU review](../vendor/spk286/docs/PROTECTED_MODE_GLOBAL_REVIEW_20260929.md#5-coverage-map-and-future-work-packages)
retains the dated findings and later scoped closures. Its original work-package
order must not reopen completed H stories.

## 4. Future historical precision — separate from accepted P06/P12

| Future story | Priority | Acceptance condition |
| --- | --- | --- |
| **PREC01 — detailed processor timing** | P3 | Extend the declared timing coverage of estimated instruction/event/prefix forms and internal EU/IU/BIU overlap with Intel-derived milestone checks. Keep this CPU scope in the SPK286 timing backlog; the target-length preview is not a complete three-entry decoded IU. |
| **PREC02 — board bus/wait policy** | P3 | Specify actual versus normalized Ts/Tc/address/status/READY milestones, board READ/WRITE waits, ISA cadence and HOLD/HLDA opportunities. Distinguish physical SDRAM service from historical waits; preserve independent peripheral clocks. |
| **PREC03 — physical-reference refinement** | P3 | If more identified captures arrive, refine a coherent common policy using Intel, explicitly configured native 86Box and the physical 6/12 MHz anchors. Identify unmeasured profiles and board/clock/wait assumptions. Do not tune all workloads to one board or change nominal MHz to fit a score. |

These stories do not block or reopen functional product acceptance. Waits
remain part of the profile; a second public T-States control is not planned.
The implemented branch target-length rule is retained, not scheduled again.

Sources: [P06 scope](../docs/optimization/P06_CPU_SPEED_PROFILES.md),
[target-handoff qualification](../docs/optimization/P06_TARGET_HANDOFF_VALIDATION_20261005.md),
[MiSTer measurements](../docs/optimization/P06_MISTER_TARGET_HANDOFF_RESULTS_20261005.md),
[physical anchors](../docs/optimization/P06_PHYSICAL_REFERENCE_RESULTS_20261004.md).

## 5. Known bounded coverage work — P2

These are specific inventories retained by prior audits, not newly asserted
bugs or a requirement to audit every conceivable peripheral combination.

| Area | Remaining bounded work |
| --- | --- |
| **PIT/8254** | Directed mode-edge/BCD/read-back inventory. All six mode branches, AT read-back and PIT OUT1 refresh already exist. |
| **RTC beyond ATF02/04** | Divider-reset phase, first update after release, DSE and non-010 DV settings. Matching periodic rates does not close these specific modes. |
| **PIC beyond ATF03** | SFNM, specific/nonspecific EOI and spurious-cascade trace inventory. IRQ7 fallback is already present. |
| **DMA beyond ATF01/05/06** | External EOP, remaining command bits and complete per-mode ownership qualification. Byte/word lanes and AT page wiring are already present. |
| **8042** | Remaining command coverage, input-port board straps and held-reset electrical behavior through identified AT firmware cases. Do not reopen completed HPS make/break/extended and 101-key navigation support. |
| **Composed Sound Blaster playback** | Count actual backend RAM reads per delivered PCM byte through memory-port/DMA/SB. The existing audit identifies possible request recapture between acceptance and completion; reproduce it before changing the path. Component and detection banks do not qualify that composition. This is not demonstrated corruption. |

Sources: [retained chipset coverage questions](../docs/AT_FUNCTIONAL_REFERENCE_AUDIT_20261003.md#coverage-and-questions-retained-for-later-work),
[known SB composition boundary](../docs/AT_FLOPPY_WRITE_CORRUPTION_20261004.md#follow-up-static-audit).
Sound Blaster, OPL2, C/MS, Tandy and MIDI are enabled in the actual config;
their existing implementation is outside this bounded coverage backlog.

## 6. Parked proposals

Further PERF01 throughput hardware is parked under the user's resource and
fidelity priority. Existing proposals include early/consecutive code hits,
larger code/data buffers, open-row SDRAM and deeper posted writes; they need
a private measured/equivalent prototype before any adoption. There is no
obligation to match immediate-memory 86Box scores.
[P07](../docs/optimization/P07_EGA_BYTE_PRESERVING_PATH.md) remains a conditional
EGA frontend proposal, preserving 8-bit byte ordering; resume only if graphical
traces or STA demonstrate relevance. These proposals are not active acceptance
tasks. See [the retained performance proposals](../docs/optimization/P18_P19_COMBINED_RBF_20261002.md#next-performance-experiment).

## Updating this backlog

Initial I/A milestones and BIOS_BACKLOG retain their historical scope; old
“not started”, XT-profile or “no board boot” statements are not current blockers.
Update this list with the fit outcome and subsequent actual evidence or user
decisions. Current work and full regression remain paused until the user
resumes them.
