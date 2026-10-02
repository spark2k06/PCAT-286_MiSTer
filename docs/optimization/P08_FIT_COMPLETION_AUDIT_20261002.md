# Source-linked fitted timing audit - 2026-10-02

`scripts/check_at_timing_closure.py` checks a completed frozen-input fit.
It does not infer closure from a selected CPU path or an optimistic summary.

```text
python3 scripts/check_at_timing_closure.py build/RUN --output build/RUN/completion-audit.json
```

The audit requires all four operating models, exactly the 144 expected
path-count groups, an unchanged report inventory and hashes, and agreement
between each parsed raw report and its summary. Global reports must have
no endpoint or clock filters. Global setup, hold, recovery and removal
must be strictly positive in every model.

The actual system and SDRAM clocks must be 20 ns, the release/P07 macros
must be active, the debug divider must be absent, and full compilation
must have zero errors and a newly generated bitstream. Every frozen input
is checked against its recorded identity. Both SDC inputs must match
`45e95b4`, except for an explicitly checked additional video-statistics
net bound when requested. An added bound must also pass its complete
163-edge/four-model audit; it cannot conceal the original requirement.

The CPU next-PC/actual-depth ROM proof sources and exactly proven executor
are matched to the fitted inputs. All 59 CPU/integration/fixture inputs
from the relevant directed cycle validation are also matched. The RTC
must be the proven conversion source. The actual mapped M10K image is
rechecked, including all 743 valid/281 invalid words and read parameters.
The ROM checker retains its checks with Python optimization enabled.

The inherited coverage qualifications remain explicit. The HPS model's
five unclocked families and their exact counts must match the documented
3713 nodes. The five reviewed issue categories must retain their counts;
unexpected nonzero issues, missing mandatory checks, illegal clocks and
unconstrained clocks are rejected. This does not certify inherited
external platform I/O or the undocumented physical SDRAM board margins.
The declared conditional W9825 timing/flight budget remains unchanged.

## Controlled generated build date

Quartus's existing pre-flow `sys/build_id.tcl` regenerates `build_id.v`.
The first October-2 fits therefore change `BUILD_DATE` from `261001`
to `261002`. The original frozen manifest is retained. The auditor
accepts only the exact date macro for the recorded UTC compile-start
date, emitted by the unchanged generator and recorded in the compilation
log, with a file timestamp after compile start. Both the frozen and
compiled hashes are retained in the completion receipt. No other source
change is permitted through this rule. A build crossing midnight needs
an explicit provenance review if it does not satisfy this strict check.

## Bounded verifier controls

`scripts/test_at_timing_closure_audit.py RUN NEW_OUTPUT` passes seven
checks against the actual RTC seed-2 fit: its real negative timing is
retained, and optimistic setup/hold summaries, a missing model, missing
global path counts, duplicated counts and filtered global reports are
rejected. Mutation inputs live in separate build directories; the actual
fit and its reports are untouched. The added 1 ns experiment is also
rejected by its original setup and full-edge requirements. The first
stack-offset fit passes the source/ROM/budget checks while retaining its
two measured video-statistics setup failures.

Evidence: `docs/evidence/fit-completion-audit-20261002`. No complete CPU
regression or hardware measurement was performed. These are validation
tools; a passing closure result still requires the actual completed fit
and review of the stated scope.
