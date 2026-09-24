# Read-only post-fit audit. Run after compiling PCAT-286, never against an
# old netlist with candidate SDC. The output directory must be new.
# quartus_sta -t scripts/report_at_video_avalon_timing.tcl PCAT-286 OUTPUT
# Optional third argument "baseline" selects the old endpoint families.
package require ::quartus::project
package require ::quartus::sta
if {[llength $quartus(args)] < 2 || [llength $quartus(args)] > 3} {
    error "Usage: report_at_video_avalon_timing.tcl REVISION OUTPUT ?baseline?"
}
lassign $quartus(args) revision output mode
if {$mode ne "" && $mode ne "baseline"} { error "Unknown audit mode: $mode" }
if {[file exists $output]} { error "Output already exists: $output" }
file mkdir $output
project_open $revision -revision $revision
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set inventory [open "$output/collections.txt" w]
proc regs {label patterns} {
    global inventory
    set c [get_registers -nowarn $patterns]
    set n [get_collection_size $c]
    puts $inventory "$label=$n"
    flush $inventory
    if {!$n} { error "Required CDC audit collection empty: $label" }
    return $c
}
set groups [list global {}]
set payload_groups {}
if {$mode eq "baseline"} {
    foreach {label src dst} {
        capture_bank0 {*ascal|o_ibuf0[*]} {*ascal|avl_i_offset0[*]}
        capture_bank1 {*ascal|o_ibuf1[*]} {*ascal|avl_i_offset1[*]}
        read_address {*ascal|o_adrs[*]} {*ascal|avl_radrs[*]}
        packed_mode {*u_video|u_ega|ega_gfx|misc_reg[*]} {*u_video|vga_packed_memory_sync1_q}
    } {
        lappend groups $label [list -from [regs ${label}_src $src] -to [regs ${label}_dst $dst]]
    }
} else {
    foreach {label src dst} {
        read_payload {*ascal|o_read_address_q[*] *ascal|o_read_base_q[*]} {*ascal|avl_radrs[*] *ascal|avl_rbase[*]}
        write_payload {*ascal|i_wadrs[*] *ascal|i_wbase[*] *ascal|i_walt} {*ascal|avl_wadrs[*] *ascal|avl_wbase[*] *ascal|avl_walt}
        read_avalon {*ascal|avl_radrs[*] *ascal|avl_rbase[*]} {*ascal|avl_address[*]}
        write_avalon {*ascal|avl_wadrs[*] *ascal|avl_wbase[*]} {*ascal|avl_address[*]}
        packed_decode {*u_video|u_ega|ega_gfx|misc_reg[*]} {*u_video|vga_packed_memory_video_q}
        packed_sync {*u_video|vga_packed_memory_sync1_q} {*u_video|vga_packed_memory_sync2_q}
        read_request_sync {*ascal|avl_read_sync} {*ascal|avl_read_sync2}
        write_request_sync {*ascal|avl_write_sync} {*ascal|avl_write_sync2}
        read_ack_sync {*ascal|o_readack_sync} {*ascal|o_readack_sync2}
        read_data_ack_sync {*ascal|o_readdataack_sync} {*ascal|o_readdataack_sync2}
        input_frame_sync {*ascal|o_iendframe0 *ascal|o_iendframe1} {*ascal|o_iendframe02 *ascal|o_iendframe12}
        output_frame_sync {*ascal|avl_o_vs_sync} {*ascal|avl_o_vs}
    } {
        lappend groups $label [list -from [regs ${label}_src $src] -to [regs ${label}_dst $dst]]
    }
    set payload_groups {read_payload write_payload}
    foreach instance {capture_bank_config capture_field_history framebuffer_out_config} {
        set src [regs ${instance}_src "*${instance}|payload_q\[*\]"]
        set dst [regs ${instance}_dst "*${instance}|dst_data\[*\]"]
        lappend groups $instance [list -from $src -to $dst]
        lappend payload_groups $instance
        foreach {src_name dst_name} {req_meta req_sync ack_meta ack_sync} {
            set src [regs ${instance}_${src_name} "*${instance}|${src_name}"]
            set dst [regs ${instance}_${dst_name} "*${instance}|${dst_name}"]
            lappend groups ${instance}_${src_name} [list -from $src -to $dst]
        }
    }
    set old [get_registers -nowarn {*ascal|avl_i_offset0[*] *ascal|avl_i_offset1[*] *ascal|avl_o_offset0[*] *ascal|avl_o_offset1[*]}]
    puts $inventory "legacy_async_offsets=[get_collection_size $old]"
    if {[get_collection_size $old]} { error "Old asynchronous bank offsets still present" }
}
close $inventory
set counts [open "$output/path_counts.txt" w]
set open_timing 0
foreach condition [get_available_operating_conditions] {
    set_operating_conditions $condition
    update_timing_netlist
    set corner [string map {" " "_" "/" "_"} $condition]
    set dir "$output/$corner"
    file mkdir $dir
    report_clock_fmax_summary -file "$dir/fmax.rpt"
    report_exceptions -file "$dir/exceptions.rpt"
    report_ucp -file "$dir/unconstrained.rpt"
    check_timing -file "$dir/check_timing.rpt"
    foreach {label selectors} $groups {
        foreach kind {setup hold} {
            # Held asynchronous payloads have a setup/max-delay budget, with
            # hold excluded. Their two synchronizer stages must pass both.
            if {$kind eq "hold" && [lsearch -exact $payload_groups $label] >= 0} { continue }
            set result [eval report_timing -$kind $selectors -npaths 20 -detail full_path -file "$dir/${label}_${kind}.rpt"]
            puts $counts "$corner $label $kind $result"
            flush $counts
            if {[lindex $result 0] == 0 || [lindex $result 1] < 0} { set open_timing 1 }
        }
    }
    foreach kind {recovery removal} {
        set result [report_timing -$kind -npaths 20 -detail full_path -file "$dir/global_${kind}.rpt"]
        puts $counts "$corner global $kind $result"
        if {[lindex $result 0] && [lindex $result 1] < 0} { set open_timing 1 }
    }
    report_min_pulse_width -nworst 20 -file "$dir/pulse_width.rpt"
}
puts $counts "timing_open=$open_timing"
close $counts
delete_timing_netlist
project_close -dont_export_assignments
post_message "CDC audit written to $output; timing_open=$open_timing (inspect reports before accepting closure)"
