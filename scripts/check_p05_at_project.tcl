# Read-only project selection check; run in an isolated copy of project files.
package require ::quartus::project
set revisions $quartus(args)
if {![llength $revisions]} { set revisions {PCAT-286_AT PCAT-286_AT_FAST} }
foreach revision $revisions {
    project_open $revision -revision $revision
    set sdc_files {}
    foreach_in_collection a [get_all_global_assignments -name SDC_FILE] {
        lappend sdc_files [file tail [lindex $a 2]]
    }
    if {[lsearch -exact $sdc_files PCAT-286_AT.sdc] < 0 ||
        [lsearch -exact $sdc_files PCAT-286.sdc] >= 0 ||
        [lsearch -exact $sdc_files sys_top.sdc] < 0} {
        error "$revision selected wrong SDC set: $sdc_files"
    }
    set macros {}
    foreach_in_collection a [get_all_global_assignments -name VERILOG_MACRO] {
        lappend macros [lindex $a 2]
    }
    foreach required {AT_PROFILE SPK286_P05_PARALLEL_LIMIT_CHECK SPK286_AT_NO_DEBUG} {
        if {[lsearch -exact $macros $required] < 0} {
            error "$revision missing macro: $required ($macros)"
        }
    }
    if {$revision eq "PCAT-286_AT"} {
        foreach {name expected} {
            SMART_RECOMPILE OFF
            OPTIMIZE_HOLD_TIMING ALL_PATHS
            SEED 2
            GENERATE_RBF_FILE ON
            PROJECT_OUTPUT_DIRECTORY output_files_pcat286_at
        } {
            set actual [get_global_assignment -name $name]
            if {![string equal -nocase $actual $expected]} {
                error "$revision: $name is '$actual', expected '$expected'"
            }
            puts "AT_PRODUCTION_SETTING $name=$actual"
        }
    }
    puts "P05_AT_PROJECT_PASS revision=$revision sdc=$sdc_files macros=$macros"
    project_close -dont_export_assignments
}
