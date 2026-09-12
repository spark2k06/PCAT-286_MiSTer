# Original-entry investigation: inconclusive

Command: `AT_LANDMARK_CASES=15 AT_LANDMARK_TIMEOUT=600s bash scripts/test_at_landmark_ram.sh`
with PCAT_BUILD_DIR selecting build/at-landmark-full-ram.

The ROM buffer is unchanged and its native reset vector is F000:8065.
The pin-level loader and initial fetch checks passed. The run did not reach
RAM_CONTEXT at 8DF6/9F14 or a RAM result marker within the 600-second wall
budget; the invoking PowerShell tool returned failure. The captured stdout
ends with the ninth logged I/O, at 9C23. Only the first nine I/Os and port D0
are printed: this is NOT a claim that the CPU stopped at that address.
No complete-POST PASS is claimed. See original-post-ram.log. No firmware delay
or test was bypassed to manufacture a full-POST result. The directed, complete
five-pattern RAM cases and hardware first-failure observer are validated
independently; the physical failure remains the next evidence needed.
