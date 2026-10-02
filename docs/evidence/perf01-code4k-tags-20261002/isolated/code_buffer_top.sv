module code_buffer_top (

    input  logic        clk,
    input  logic        reset,
    input  logic        cancel_cpu,
    input  logic        enable,

    input  logic        in_valid,
    input  logic        in_command_valid,
    input  logic [1:0]  in_owner,
    input  logic        in_write,
    input  logic        in_refresh,
    input  logic        in_code_fetch,
    input  logic [3:0]  in_cycle_class,
    input  logic [24:0] in_address,
    input  logic [1:0]  in_byte_enable,
    input  logic [15:0] in_data_out,
    output logic        in_accept,
    output logic        in_ready,
    output logic [15:0] in_read_data,
    output logic        in_read_data_valid,

    output logic        out_valid,
    output logic        out_command_valid,
    output logic [1:0]  out_owner,
    output logic        out_write,
    output logic        out_refresh,
    output logic        out_code_fetch,
    output logic        out_burst,
    output logic [3:0]  out_cycle_class,
    output logic [24:0] out_address,
    output logic [1:0]  out_byte_enable,
    output logic [15:0] out_data_out,
    input  logic        out_accept,
    input  logic        out_ready,
    input  logic [15:0] out_read_data,
    input  logic        out_read_data_valid,

    output logic [31:0] debug_hit_count,
    output logic [31:0] debug_miss_count,
    output logic [31:0] debug_fill_count,
    output logic [31:0] debug_physical_read_count,
    output logic [31:0] debug_invalidation_count,
    output logic [4:0]  debug_state
);
spk286_at_sdram_read_buffer #(.LINE_COUNT(512), .SYNC_TAGS(1'b1)) dut (.*);
endmodule
