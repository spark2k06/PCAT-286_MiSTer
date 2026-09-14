# AT-only constraints. Root clocks and common MiSTer constraints are loaded
# by sys/sys_top.sdc. This file replaces PCAT-286.sdc in the AT revisions.
# Do not group the whole CPU and video domains as asynchronous: unchecked
# direct crossings must remain visible to TimeQuest.
derive_pll_clocks
derive_clock_uncertainty

proc at_clock {name} {
    set c [get_clocks -nowarn $name]
    if {[get_collection_size $c] != 1} { error "AT clock missing/ambiguous: $name" }
    return $c
}
proc at_regs {label patterns {required 1}} {
    set r [get_registers -nowarn $patterns]
    set n [get_collection_size $r]
    post_message "AT SDC collection $label: $n registers"
    if {$required && !$n} { error "AT SDC required collection empty: $label" }
    return $r
}
proc at_sync {label source_clock patterns {required 1}} {
    set r [at_regs $label $patterns $required]
    if {[get_collection_size $r]} {
        # Only the asynchronous arrival at the first stage is cut. The
        # first-to-second stage remains a normal single-cycle path.
        set_false_path -from $source_clock -to $r
    }
}
proc at_mailbox {label source_clock patterns budget} {
    set r [at_regs $label $patterns]
    # The source holds the complete payload until the acknowledged toggle
    # returns. This bound is shorter than one destination clock period;
    # the receiver waits at least two synchronizer stages before using it.
    set_max_delay -from $source_clock -to $r $budget
    set_false_path -hold -from $source_clock -to $r
}

set AT_CPU [at_clock FPGA_CLK2_50]
set AT_VIDEO [at_clock {emu|u_at_video_pll|pll_system_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}]
set AT_VIDEO_X2 [at_clock {emu|u_at_video_pll|pll_system_inst|altera_pll_i|general[1].gpll~PLL_OUTPUT_COUNTER|divclk}]
set AT_VIDEO_OUT [at_clock {emu|u_at_video_pll|pll_system_inst|altera_pll_i|general[2].gpll~PLL_OUTPUT_COUNTER|divclk}]
set AT_HDMI [at_clock {pll_hdmi|pll_hdmi_inst|altera_pll_i|cyclonev_pll|counter[0].output_counter|divclk}]

create_generated_clock -name SDRAM_CLK -source [get_ports FPGA_CLK2_50] -divide_by 1 [get_ports SDRAM_CLK]
create_clock -name VCLK_SDIO -period 20.000
set_input_delay -clock SDRAM_CLK -max 6 [get_ports {SDRAM_DQ[*]}]
set_input_delay -clock SDRAM_CLK -min 3 [get_ports {SDRAM_DQ[*]}]
# Preserve the inherited external budget pending identification of the SDRAM
# module. Do not change phase, delay signs or target frequency to obtain PASS.
set_output_delay -clock SDRAM_CLK -max 2 [get_ports {SDRAM_DQ[*] SDRAM_DQM* SDRAM_A[*] SDRAM_n* SDRAM_BA[*] SDRAM_CKE}]
set_output_delay -clock SDRAM_CLK -min 1.5 [get_ports {SDRAM_DQ[*] SDRAM_DQM* SDRAM_A[*] SDRAM_n* SDRAM_BA[*] SDRAM_CKE}]
set_input_delay -clock VCLK_SDIO -max 10 [get_ports {SDIO_DAT[*] SDIO_CMD}]
set_input_delay -clock VCLK_SDIO -min 5 [get_ports {SDIO_DAT[*] SDIO_CMD}]
set_output_delay -clock VCLK_SDIO -max 5 [get_ports {SDIO_DAT[*] SDIO_CMD SDIO_CLK}]
set_output_delay -clock VCLK_SDIO -min 0 [get_ports {SDIO_DAT[*] SDIO_CMD SDIO_CLK}]
# The pins also carry analog video. A virtual SDIO receiver does not sample
# those video paths; FPGA internal paths are not affected by these exclusions.
foreach c [list $AT_VIDEO_OUT $AT_HDMI] {
    set_false_path -from $c -to [get_clocks VCLK_SDIO]
}

# CPU <-> EGA I/O: one outstanding request, stable payload, toggle handshake.
at_sync ega_request $AT_CPU {*u_video|video_io_req_sync1_q}
at_sync ega_ack $AT_VIDEO {*u_video|io_ack_sync1_q}
at_mailbox ega_request_payload $AT_CPU {*u_video|video_bus_address_q[*] *u_video|video_bus_data_q[*] *u_video|video_bus_ior_q *u_video|video_bus_iow_q} 10.0
at_mailbox ega_reply_payload $AT_VIDEO {*u_video|io_read_data_sync1_q[*]} 10.0
at_sync ega_memory_select $AT_CPU {*u_video|memory_select_video1_q *u_video|memory_write_video1_q}

# VRAM mode registers are held by the acknowledged EGA I/O transaction.
# The frontend samples the payload only on its synchronized cfg_toggle edge.
at_sync ega_config_toggle $AT_VIDEO {*u_video|u_vram|cfg_toggle_sync1}
at_mailbox ega_config_payload $AT_VIDEO {
    *u_video|u_vram|plane_write_mask_sync1[*] *u_video|u_vram|odd_even_mode_sync1
    *u_video|u_vram|chain2_write_sync1 *u_video|u_vram|chain2_read_sync1
    *u_video|u_vram|extended_memory_sync1 *u_video|u_vram|mem_map_sel_sync1[*]
    *u_video|u_vram|page_select_sync1 *u_video|u_vram|write_mode_sync1[*]
    *u_video|u_vram|read_mode_sync1[*] *u_video|u_vram|read_plane_sel_sync1[*]
    *u_video|u_vram|color_compare_sync1[*] *u_video|u_vram|color_dont_care_sync1[*]
    *u_video|u_vram|bit_mask_sync1[*] *u_video|u_vram|set_reset_sync1[*]
    *u_video|u_vram|enable_set_reset_sync1[*] *u_video|u_vram|rop_select_sync1[*]
    *u_video|u_vram|rotate_count_sync1[*]
} 10.0

# Only an explicitly labelled reanalysis may lack the newly added stages.
# A normal candidate compile must fail if either synchronizer is absent.
set at_require_new [expr {![info exists ::env(P05_REFERENCE_FIT)] || $::env(P05_REFERENCE_FIT) ne "1"}]
at_sync splash $AT_CPU {*u_video|splash_video_sync1_q} $at_require_new

# These registers asynchronously assert reset, then release on their local
# clock. Cut only the async control pin, not their synchronous D paths.
set reset_release [at_regs reset_release {
    *u_video|video_reset_sync1_q *u_video|video_reset_sync2_q
    emu|at_video_pipe_reset_57_q1 emu|at_video_pipe_reset_57_q2
    emu|at_video_pipe_reset_57_ps_q1 emu|at_video_pipe_reset_57_ps_q2
}]
set reset_pins [get_pins -nowarn -compatibility_mode {*u_video|video_reset_sync*_q|clrn *u_video|video_reset_sync*_q|prn *emu|at_video_pipe_reset*|clrn *emu|at_video_pipe_reset*|prn}]
if {[get_collection_size $reset_pins]} { set_false_path -to $reset_pins }
post_message "AT SDC reset asynchronous pins: [get_collection_size $reset_pins]"

# Common MiSTer exceptions which also apply to the AT output pipeline.
set pll_frame [get_registers -nowarn {pll_hdmi_adj:pll_hdmi_adj|ivss}]
if {[get_collection_size $pll_frame]} {
    set_false_path -from [get_registers {pll_hdmi_adj:pll_hdmi_adj|i_vss_delay}] -to $pll_frame
}
set scaler_reset [get_registers -nowarn {ascal:ascal|i_reset_na ascal:ascal|o_reset_na ascal:ascal|avl_reset_na}]
if {[get_collection_size $scaler_reset]} { set_false_path -to $scaler_reset }

# No extra retiming exception between the three related video PLL outputs.
# STA must analyze the real base/X2/+90 degree phase relationships.
