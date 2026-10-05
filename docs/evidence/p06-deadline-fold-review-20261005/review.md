# Deadline fold and idle payload fit review — 2026-10-05

## Scope and bindings

Read-only comparison of `p06-deadline-fold-allfeatures-20261005-v1` (HEAD `f2ea538cb98ed0f98c6f7fb645b94dc2845b6039`) against `p06-live-speed-allfeatures-20261005-v1` (HEAD `a5d18f88ea871ffe42d037271c029faafa71c99c`). Both are under `build/`; the input summaries, manifests, fitter reports and selector script are SHA-256-bound in the companion JSON. No new timing, synthesis or simulation was run and no production source was edited. Full regression remains **USER_DEFERRED**. The summaries cover bounded top-N reports, not a complete path census. Complete closure is not claimed.

New summary SHA-256: `77849a0cf3e248ea4da2f0a8e85a7c18660119bb3f75c2cf1cdb76e622f65273`.
New manifest SHA-256: `a713bcdad1a7060b4989e7fa1fb75d63b25acc89b3bcb7e5a07b71f345bd2796`.

## Worst reported margins across four corners

All values are nanoseconds. Each entry is the minimum across the four corners; old and new minima can have different endpoints and corners.

| Selector | Old setup | New setup | Change | Old hold | New hold |
|---|---:|---:|---:|---:|---:|
| global | -6.051 | -0.288 | +5.763 | -0.065 | -0.047 |
| clk50_internal | -6.051 | -0.054 | +5.997 | +0.118 | +0.119 |
| cpu | -6.051 | -0.054 | +5.997 | +0.119 | +0.121 |
| cpu_bridge | -1.984 | +1.595 | +3.579 | +0.387 | +0.270 |
| bridge_cpu | +2.885 | +4.596 | +1.711 | +0.331 | +0.223 |
| memory_port | -1.762 | +2.530 | +4.292 | +0.173 | +0.172 |
| code_buffer | -2.832 | +0.243 | +3.075 | +0.149 | +0.167 |
| data_buffer | -2.628 | +1.355 | +3.983 | +0.168 | +0.168 |
| data_buffer_outputs | +1.622 | +3.799 | +2.177 | +0.168 | +0.168 |
| sdram_owner | -2.442 | +1.361 | +3.803 | +0.168 | +0.172 |
| sdram_owner_internal | +8.444 | +7.889 | -0.555 | +0.168 | +0.172 |
| keyboard | +7.569 | +6.253 | -1.316 | +0.167 | +0.170 |
| prebios_stage2 | +33.778 | +32.032 | -1.746 | +0.250 | +0.555 |
| video | +2.217 | +1.735 | -0.482 | -0.065 | -0.047 |
| sdram_input | +5.185 | +5.189 | +0.004 | +5.000 | +5.000 |
| sdram_output | +4.910 | +4.601 | -0.309 | +0.245 | +0.269 |

All bridge, memory-port, code/data-buffer and SDRAM-owner setup and hold groups are positive in every supplied corner. The tightest backend setup is code buffer **+0.243 ns**, cold slow. SDRAM input/output checks also remain positive.

There is no dedicated posted-write register selector in the supplied report script. Posted logic is visible in the backend cones and data-buffer output paths; cold slow hold into posted address registers is +0.442 ns or better among the reported paths. This does not establish a standalone posted-write WNS or a census of all its paths.

## Actual placed resources

| Metric | Old fit | New fit | Change |
|---|---:|---:|---:|
| ALMs used in final placement | 37,054 | 36,913 | -141 |
| Equivalent ALMs needed | 31,895 | 31,602 | -293 |
| Combinational ALUTs for logic | 47,892 | 47,556 | -336 |
| Total registers | 38,207 | 38,384 | +177 |
| Design implementation registers | 35,404 | 35,404 | 0 |
| Routing optimization registers | 2,754 | 2,931 | +177 |
| Partially/completely used LABs | 4,049 | 4,063 | +14 |
| M10K | 416 | 416 | 0 |
| Block memory bits | 3,301,019 | 3,301,019 | 0 |
| DSP | 39 | 39 | 0 |
| PLL | 3 | 3 | 0 |

Placed ALM occupancy is **88.08%** of 41,910, previously 88.41%; equivalent ALMs are 75.40%. All added registers are fitter routing duplicates; design state is unchanged. LAB usage is approximately 97%, so equivalent ALMs and actual packing should remain separate measures. These are combined-fit costs, not isolated attribution to one refactor.

## Feature and structural verification

The two source manifests have identical `config.tcl`, `PCAT-286.qsf`, `PCAT-286.sv` and `SYSTEM.sdc` hashes, and identical PLL source/QIP hashes. The new compiled `timing/collections.txt` explicitly retains `ENABLE_SB=1`, `ENABLE_OPL2=1`, `ENABLE_CMS=1`, `ENABLE_TANDY_AUDIO=1`, `ENABLE_MIDI=1`, `SPK286_AT_CDC` and `AT_PROFILE`. CPU and SDRAM periods remain **20.000 ns**; HDMI remains 6.732 ns. No feature was disabled.

The three buffer hashes match the earlier source-bound induction/directed-test packet at `docs/evidence/p06-buffer-idle-payload-20261005`. The production synchronous code buffer, data buffer and posted buffer now select raw IDLE payload independently of admission/classification. Valid, command, acceptance, READY, retained state, memory interface and cycle latency stay unchanged under that earlier proof. The code buffer still preserves its explicit asynchronous-tag miss line-base override in the non-production parameter mode.

Old cold-slow critical trunk: `owner → word capability → backend owner → code cache candidate → code payload mux → data candidate → data payload mux → posted RAM-address classification → posted accept → endpoint`.

New memory/owner trunk: `owner → bus-valid/code-ready → word capability/native-word request → mapped address/memory cycle → backend owner → data candidate → posted presented → owner accept → endpoint`.

The chained classifications no longer control the intermediate raw payload muxes. Required valid/accept classifications remain. The new code-buffer worst endpoint is `line_valid_q[203]` (19 logic levels, 19.055 ns data); owner worst endpoint is `sdram_address[4]` (19 levels, 17.945 ns). Bridge worst moved to device/UART admission (16 levels, 17.706 ns), rather than the cache chain. This is consistent with structural removal of the payload dependency; exact timing gains cannot be assigned solely to buffers because CPU changes and placement are also present in the combined fit.

## Residuals and next decision

- **CPU setup -0.054 ns hot slow / -0.033 ns cold slow.** Path: `prefetch head → consume data/prefix → service_start → call_parameter_write → stack range → operand.done → GPR80`. It has 18 levels, 12.095 ns route plus 7.206 ns cells, and -0.573 ns skew. Concrete high-fanout nodes include `call_parameter_write` (97) and the transfer from the operand completion region near X65 to GPR-data logic near X80. A physical placement/packing attempt with identical RTL is the cheapest next step. Further range comparison before a late stack-offset mux is a possible fallback, with exact equivalence and hidden-limit/LOADALL/expand-down/protected-stack checks required; do not add broad comparator replication solely to recover 54 ps.
- **Palette hold -0.047 ns, fast cold, six reported violations.** Path: `write_index[1]~DUPLICATE → encoded_write_index[1] → port_blue RAM addressregout1`. The XOR physically exists: one LUT at 0.173 ns, route 0.499 ns, total 0.700 ns, skew +0.187 ns, relationship 0.500 ns. Its output fanout is 288. Old path had zero LUTs and -0.065 ns. Root is separately auditing original SDC and running the identical-RTL seed comparison. Measure that first. If a physical-only fit cannot meet the extra minimum route, a retained physical LCELL would be a concrete later option; an algebraically deeper XOR may collapse into one LUT. Any later change must retain same-cycle writes and consistent addresses for all six copies, and be checked after placement from every write-index source without relaxing the constraint.
- **HDMI scaler setup -0.288 ns cold slow / -0.096 ns hot slow.** Path: `o_hcpt[6] → Add175 → LessThan37 → vertical counter enable`. Delay is 2.434 ns route plus 3.908 ns cells, skew -0.478 ns, period 6.732 ns. Source is the line-end decision `o_hcpt+1 < o_htotal` at `sys/ascal.vhd:3013`. If placement alone remains insufficient, a widened exact `hcount < htotal-1` terminal comparison could move arithmetic off the horizontal-count input path without extra state. It must preserve total=0/count=4095, reset/CE priority, same-cycle dynamic timing and VRR behavior under a complete combinational/transition proof; no source edit has been made here.

Recovery/removal remain positive: worst new recovery **+3.025 ns**, removal **+0.223 ns**. CPU/50 MHz and backend hold are already positive. The current evidence supports trying physical options first with unchanged clocks, constraints and features. Root owns the original-SDC audit, source-bound fit archive and next fit decision; no additional tests are required by this read-only review.
