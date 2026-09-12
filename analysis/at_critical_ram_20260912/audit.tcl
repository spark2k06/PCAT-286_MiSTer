package require ::quartus::project
package require ::quartus::sta
project_open /build/PCAT-286_AT_FAST -revision PCAT-286_AT_FAST
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set machine_clock [get_clocks FPGA_CLK2_50]
set cpu [get_registers -nowarn {*u_at_machine|u_cpu|*}]
puts "CPU_REGISTERS=[get_collection_size $cpu]"
report_timing -setup -from_clock $machine_clock -to_clock $machine_clock -npaths 30 -detail full_path -file /build/analysis/at_critical_ram_20260912/clk50_setup.rpt
report_timing -setup -to $cpu -npaths 30 -detail full_path -file /build/analysis/at_critical_ram_20260912/cpu_setup.rpt
report_timing -setup -from_clock $machine_clock -to_clock [get_clocks SDRAM_CLK] -npaths 10 -detail full_path -file /build/analysis/at_critical_ram_20260912/sdram_output_setup.rpt
report_timing -setup -from_clock [get_clocks SDRAM_CLK] -to_clock $machine_clock -npaths 10 -detail full_path -file /build/analysis/at_critical_ram_20260912/sdram_input_setup.rpt
delete_timing_netlist
project_close
