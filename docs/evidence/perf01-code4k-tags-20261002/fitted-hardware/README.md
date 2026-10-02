# Completed P14 fit and supplied MiSTer observations

Implementation: `84dbf17`. The supplied images show CheckIT 4911 / 95.1K and
CHECKNUM 4911 / 99.1K. CheckIT matches the previous observation. CHECKNUM math
is 4.98% higher than its previous 94.4K observation; no cause or repeat
distribution is established. Integer throughput is retained.

`fit-observation.json` identifies the full reports and locally generated RBF,
records fitted resources and the complete STA summary's negative row.
Original map/fit/STA summaries and selected entity/RAM/coverage tables are
retained here. Full reports and RBF are preserved locally under
`D:/GitHub/PCAT-286_MiSTer/build/perf01-code4k-tags-user-fit-20261002/`.

`hardware-observation.json` records screenshot hashes and the association with
that local RBF. The loaded MiSTer hash and OSD settings were not independently
read. Current production source/config/SDC hashes match the P14 map snapshot;
the user fit's source identity was captured after compilation.

CPU/system 50 MHz setup/hold is positive in all four models. Whole-design
closure remains pending: the HDMI PLL clock has setup -0.104 ns at Slow -40 C.
The user explicitly retains P14 and defers HDMI while prioritizing PERF01.
The coverage table has no unconstrained clocks, but platform I/O exclusions
remain; this report-level review is not a renewed complete constraint audit.
