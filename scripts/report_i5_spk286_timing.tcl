package require ::quartus::project
package require ::quartus::sta

set project_name "PCAT-286"
set output_dir "output_files_pcat286"

project_open $project_name -revision $project_name
create_timing_netlist
read_sdc
update_timing_netlist

file mkdir $output_dir

set spk_registers [get_registers -nowarn {*spk286_machine_cpu:u_SPK286|*}]
set bridge_registers [get_registers -nowarn {*spk286_xt_bridge:u_SPK286_XT_BRIDGE|*}]
set spk_count [get_collection_size $spk_registers]
set bridge_count [get_collection_size $bridge_registers]

set summary_path "$output_dir/PCAT-286.spk286_timing_summary.txt"
set summary_file [open $summary_path w]
puts $summary_file "SPK286 timing collections"
puts $summary_file "spk_registers=$spk_count"
puts $summary_file "bridge_registers=$bridge_count"
close $summary_file

if {$spk_count == 0} {
    post_message -type error "No SPK286 registers matched the timing hierarchy"
    delete_timing_netlist
    project_close
    qexit -error
}

report_timing -setup -from $spk_registers -to $spk_registers \
    -npaths 20 -detail full_path \
    -file "$output_dir/PCAT-286.spk286_internal_setup.rpt"
report_timing -hold -from $spk_registers -to $spk_registers \
    -npaths 20 -detail full_path \
    -file "$output_dir/PCAT-286.spk286_internal_hold.rpt"

if {$bridge_count != 0} {
    report_timing -setup -from $spk_registers -to $bridge_registers \
        -npaths 20 -detail full_path \
        -file "$output_dir/PCAT-286.spk286_to_bridge_setup.rpt"
    report_timing -setup -from $bridge_registers -to $spk_registers \
        -npaths 20 -detail full_path \
        -file "$output_dir/PCAT-286.bridge_to_spk286_setup.rpt"
} else {
    post_message -type error "No SPK286 XT bridge registers matched the timing hierarchy"
    delete_timing_netlist
    project_close
    qexit -error
}

report_clock_fmax_summary \
    -file "$output_dir/PCAT-286.clock_fmax_summary.rpt"

set chipset_clock [get_clocks -nowarn {emu|pll|pll_inst|altera_pll_i|cyclonev_pll|counter[1].output_counter|divclk}]
if {[get_collection_size $chipset_clock] != 0} {
    report_timing -setup -from $chipset_clock -to $chipset_clock \
        -npaths 50 -detail full_path \
        -file "$output_dir/PCAT-286.chipset_clock_setup.rpt"
    report_timing -hold -from $chipset_clock -to $chipset_clock \
        -npaths 50 -detail full_path \
        -file "$output_dir/PCAT-286.chipset_clock_hold.rpt"
}

foreach {clock_label clock_name} {
    video_base {emu|pll_system_inst|pll_system_inst|altera_pll_i|general[0].gpll~PLL_OUTPUT_COUNTER|divclk}
    video_x2   {emu|pll_system_inst|pll_system_inst|altera_pll_i|general[1].gpll~PLL_OUTPUT_COUNTER|divclk}
    video_vga  {emu|pll_system_inst|pll_system_inst|altera_pll_i|general[3].gpll~PLL_OUTPUT_COUNTER|divclk}
} {
    set inspected_clock [get_clocks -nowarn $clock_name]
    if {[get_collection_size $inspected_clock] != 0} {
        report_timing -setup -to $inspected_clock \
            -npaths 50 -detail full_path \
            -file "$output_dir/PCAT-286.${clock_label}_setup.rpt"
    }
}

set sdio_clock [get_clocks -nowarn VCLK_SDIO]
if {[get_collection_size $sdio_clock] != 0} {
    report_timing -setup -to $sdio_clock \
        -npaths 20 -detail full_path \
        -file "$output_dir/PCAT-286.sdio_setup.rpt"
}

set h2f_clock [get_clocks -nowarn {sysmem|fpga_interfaces|clocks_resets|h2f_user0_clk}]
if {[get_collection_size $h2f_clock] != 0} {
    report_timing -setup -to $h2f_clock \
        -npaths 20 -detail full_path \
        -file "$output_dir/PCAT-286.h2f_setup.rpt"
}

report_timing -setup -npaths 100 -detail full_path \
    -file "$output_dir/PCAT-286.global_setup.rpt"
report_timing -hold -npaths 100 -detail full_path \
    -file "$output_dir/PCAT-286.global_hold.rpt"
report_timing -recovery -npaths 100 -detail full_path \
    -file "$output_dir/PCAT-286.global_recovery.rpt"

report_ucp \
    -file "$output_dir/PCAT-286.unconstrained_paths.rpt"

delete_timing_netlist
project_close
