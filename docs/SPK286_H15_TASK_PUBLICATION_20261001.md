# SPK286 H15: staged incoming task publication

Date: 2026-10-01. Baseline upstream `4dab80c`, vendor `9e3905f`.

The CPU vendor now invalidates outgoing hidden segment caches when publishing
the incoming task selectors, waits for that publication before late LDTR faults,
and publishes SS/CS/data caches individually after validation and Accessed writes.
Late task exceptions use incoming CS:IP and the already validated incoming stack.

The original native 86Box task interpreter also differs from Intel's documented
late-fault context. The CPU correction follows the documented sequence; the
before/after reference conflicts and directed test evidence are explicit in the
[contract](../vendor/spk286/docs/PROTECTED_MODE_H15_TASK_PUBLICATION_20261001.md)
and [receipt](../vendor/spk286/docs/REGRESSION_H15_TASK_PUBLICATION_20261001.json).

Both simulators pass the 80 executable reset-ROM cases and five other affected
vendor banks with P01/P02/P05. Lint and portable synthesis pass. Standalone
validation includes 20 other affected banks, five rejected mutations and
15,000 real-mode physical captures. No full regression or hardware boot is
claimed for this milestone.

The normal 50 MHz, observer-free configuration and downstream real-mode IP
wrap adaptation are preserved. The existing 86Box executable was rebuilt with
P02/P05. H16 remains separate; PERF01 records the future whole-machine benchmark
investigation without introducing a performance change.
