# Independent review of the actual null-segment/ascal fit

**Archive/source/report review: PASS. Physical timing: still open.**

The existing sealed packet remains unchanged. This review reads archived source,
Quartus/TimeQuest reports and the delivered RBF; it launches no tests, synthesis
or STA. It creates no compiler cache.

## Source and archive identity

- All 2,456 archived members were read back against their exact recorded hashes
  and sizes. Packet SHA-256:
  `54cfeec050d88fad8f061ffac8ebe35c06f9e6788cd4b84b9a3dd04d0ed9f1e5`.
- The fitted snapshot contains 2,062 sources. Its 1,241-entry canonical vendor
  ledger remains at upstream `3001de76db5e47612274b3d9473e524dba1654a3`.
  The later live `c9239dc3...` import does not replace any fitted active RTL.
- The initial manifest and final source receipt agree except for the exact
  recorded preflow build date. The requested and actual placement seed is 2.
- All production and original-SDC STA report inventories match their summary
  hashes. Parsed actual worst paths match reported tool slacks; four corners
  and unfiltered global report commands are preserved. Original-SDC manifest,
  source inventory and parent fit identify the same fitted candidate.
- Production constraints, the additional 0.500 ns palette route requirement
  and the common physical 50 MHz clocks remain intact. The original overlay is
  independently bound. The reviewed timing-health categories remain clear.

## Actual margins

| Global metric | Worst margin | Corner |
|---|---:|---|
| Setup | -0.337 ns | slow, 100 C |
| Hold | +0.036 ns | slow, -40 C |
| Recovery | +3.032 ns | slow, 100 C |
| Removal | +0.198 ns | fast, -40 C |

Setup remains negative in the CPU hot corner and the HDMI cold corner.
All reported hold groups are positive. The CPU/bridge, memory port, code/data
buffers and SDRAM owner setup groups are positive; their improvements do not
establish global closure. The original-SDC view also retains setup failures.

## Actual resources and memory

| Resource | Previous seed2 fit | This fit | Difference |
|---|---:|---:|---:|
| Equivalent ALMs | 31,633 | 31,609 | -24 |
| Placed ALMs | 36,854 | 36,896 | +42 |
| Registers | 38,333 | 38,374 | +41 |
| Memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K blocks | 416 | 416 | 0 |
| DSP blocks | 39 | 39 | 0 |
| PLLs | 3 | 3 | 0 |

CPU inclusive ALMs decreased from 7,539.7 to 7,450.3 needed and from 8,295.1 to
8,191.4 placed. CPU registers remain 5,606 and its microcode memory remains one
9,216-bit M10K. Whole-project placement is 88.04% of 41,910 ALMs.

The actual mapped microcode MIF was checked across all 1,024 addresses: 743
valid words match the independent fixture and 281 invalid words are zero.
The compiled M10K output/address-reset parameters retain the required read
alignment. The actual RBF size and SHA match the sealed delivery identity.

## Acceptance

No timing-closure, complete-regression or MiSTer validation claim is made.
The full-regression gate remains
`AUTHORIZED_AFTER_TIMING_CLOSURE_NOT_RUN`; these setup failures do not satisfy
its entry condition. `review.json` records the exact source, resource, report,
microcode and RBF values for this independent review.
